"""Append-only, single-writer USD spend reservations for bounded paid HTTP attempts.

Unknown billing keeps the full reservation. A crash leaves a request reserved, never permission
to rebill it. The caller supplies an approved cap; constructing this object is not authorization.
"""
import json
import os
from contextlib import contextmanager
from decimal import Decimal
from pathlib import Path


class BudgetStop(RuntimeError):
    """Stop the run, not a retryable transport failure."""


class SpendLedger:
    def __init__(self, path, cap_usd, input_per_million='0.30', output_per_million='1.20'):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.cap = Decimal(str(cap_usd))
        self.input_rate = Decimal(str(input_per_million))
        self.output_rate = Decimal(str(output_per_million))
        if any(not x.is_finite() or x <= 0 for x in (self.cap, self.input_rate, self.output_rate)):
            raise ValueError('Cap and rates must be finite and positive')
        self.header = {'kind': 'authorization', 'cap_usd': str(self.cap),
                       'input_per_million': str(self.input_rate),
                       'output_per_million': str(self.output_rate), 'currency': 'USD'}
        with self._lock():
            if not self.path.exists():
                self._append(self.header)
            if self._rows()[0] != self.header:
                raise BudgetStop('Existing budget cap/rates differ; authorization cannot be mutated')

    @contextmanager
    def _lock(self):
        lock = self.path.with_suffix('.lock')
        try:
            fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        except FileExistsError as error:
            raise BudgetStop('Budget is locked; inspect any interrupted writer before resuming') from error
        try:
            yield
        finally:
            os.close(fd)
            lock.unlink()

    def _rows(self):
        # Truncated/corrupt JSON stops before dispatch; never discard a partial reservation.
        return [json.loads(line) for line in self.path.read_text(encoding='utf-8').splitlines()]

    def _append(self, row):
        with self.path.open('a', encoding='utf-8', newline='\n') as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + '\n')
            handle.flush()
            os.fsync(handle.fileno())

    def _cost(self, input_tokens, output_tokens):
        return (Decimal(input_tokens) * self.input_rate +
                Decimal(output_tokens) * self.output_rate) / 1000000

    def _state(self):
        requests = {}
        for row in self._rows()[1:]:
            if row['kind'] == 'reserve':
                if row['request_id'] in requests:
                    raise BudgetStop('Duplicate reservation in ledger')
                requests[row['request_id']] = row
            elif row['kind'] == 'settle':
                previous = requests[row['request_id']]
                if previous['kind'] == 'settle':
                    raise BudgetStop('Duplicate settlement in ledger')
                requests[row['request_id']] = row
            else:
                raise BudgetStop('Unknown budget record')
        return requests

    def summary(self):
        state = self._state()
        charged = sum((Decimal(r['charged_usd']) for r in state.values()), Decimal(0))
        return {'cap_usd': str(self.cap), 'charged_usd': str(charged),
                'remaining_usd': str(self.cap - charged),
                'unsettled_requests': sum(r['kind'] == 'reserve' for r in state.values()),
                'unknown_usage_requests': sum(r.get('usage_unknown', False) for r in state.values()),
                'http_attempts': len(state)}

    def reserve(self, request_id, input_token_ceiling, output_token_ceiling):
        with self._lock():
            if request_id in self._state():
                raise BudgetStop('Request already dispatched/reserved; inspect saved response, do not rebill')
            charge = self._cost(input_token_ceiling, output_token_ceiling)
            if charge > Decimal(self.summary()['remaining_usd']):
                raise BudgetStop('Approved spending cap cannot cover the next request reservation')
            self._append({'kind': 'reserve', 'request_id': request_id,
                          'charged_usd': str(charge)})

    def settle(self, request_id, usage):
        with self._lock():
            previous = self._state()[request_id]
            if previous['kind'] != 'reserve':
                raise BudgetStop('Request was already settled')
            counts = [usage.get('prompt_tokens'), usage.get('completion_tokens')]
            known = all(type(n) is int and n >= 0 for n in counts)
            cost = self._cost(*counts) if known else Decimal(previous['charged_usd'])
            self._append({'kind': 'settle', 'request_id': request_id, 'charged_usd': str(cost),
                          'usage_unknown': not known, 'provider_usage': usage})
            if cost > Decimal(previous['charged_usd']):
                raise BudgetStop('Provider usage exceeded reservation; stop and reconcile before more calls')
