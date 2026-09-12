"""Injected-provider adapters. No module in this package is imported by the test suite's
default path -- the classifier and drafter accept any callable provider, and every existing test
uses a synthetic in-memory one (tests/test_classifier.py:Recorder and similar). A real adapter
here is instantiated only by tools/run_model_experiment.py, and only once a credential is
present, so importing this package must never require the vendor SDK to be installed.
"""
