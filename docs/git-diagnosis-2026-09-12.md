# Git diagnosis — 2026-09-12

## Findings

- Initial worktree clean; HEAD `15c11c7`; branch `codex/phase-1-editorial-spec`, 18 commits ahead
  of the locally recorded origin branch. Remote freshness could not be checked.
- Commit identity is configured and recent commits exist. No lock file was found. The user's
  original commit error was not supplied, so its exact cause cannot be reconstructed. There
  was nothing left to commit at the start of this review; new review documents are subsequent edits.
- `git fsck --full` reported one dangling tree, not missing/corrupt objects. A dangling tree is
  not evidence that the repository needs replacement.
- Sandbox `ls-remote` failed through environment proxies at localhost port 9. No Git proxy
  configuration was returned by the targeted config query. This sandbox result is distinct from
  the host's network behavior.
- Outside sandbox, `git ls-remote origin` failed with connection reset and `git push --dry-run
  origin HEAD` failed connecting to github.com:443. No remote ref was changed.
- Host DNS resolved github.com, but an independent TCP connection to port 443 timed out.
  ssh.github.com did not resolve during this check. Authentication and branch protection were
  not reached or tested successfully; do not diagnose them as the current cause.
- No proxy, DNS, firewall, credential, remote URL or network setting was changed.

Conclusion: **a reproducible GitHub connectivity failure, not demonstrated Git-history corruption**.
Deleting .git or creating another GitHub repository would still encounter the network failure and
would risk losing the local commits.

## Recovery order

1. Retry from the user's normal terminal on a known-working network. Check the existing approved
   VPN/proxy client's status and GitHub reachability. Changing proxy ports/settings requires the
   user's explicit choice; this diagnosis makes no such change.
2. Once connectivity returns, run `git ls-remote origin`, then `git fetch origin` and inspect
   divergence. Preview with `git push --dry-run origin HEAD`; perform the ordinary push only when
   intended. Do not force-push if the remote changed while offline.
3. If HTTPS is specifically restricted, SSH (including SSH over port 443) is a possible alternate
   transport only after its endpoint is reachable and authorized keys exist. It was not reachable
   here, so it is not presented as a verified workaround. GitHub Desktop also requires connectivity.
4. If OneDrive later causes locks/permissions, make a separate checkout outside OneDrive while
   retaining the original. Clone from the local bundle to preserve history; copy ignored work/
   separately and privately if needed. Moving does not itself fix GitHub connectivity.
5. Create a new remote repository only for an intentional ownership/visibility/history decision,
   not as a network fix. Preserve the existing history and backup first; do not delete .git.

## Backup made

`work/phase4-history-backup.bundle` was created with `git bundle create ... --all` and verified
successfully. It contains the committed history through `15c11c7` and current refs. It does not
contain ignored analyst/evidence files or the review documents written afterward. Keep it private;
do not force-add work/ to Git. A separate backup is needed for ignored evidence and any uncommitted
files before moving the workspace. No repository was deleted, recreated, reset or pushed.
