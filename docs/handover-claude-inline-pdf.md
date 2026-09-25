# Claude handover: direct in-page PDF reading

Timing: start after the user completes the ranking review. This is a prepared handover, not an instruction to start now.

The user requires English and Chinese reports to display directly inside the Reports tab. Existing object embeds produced blank panes in the connected Codex in-app browser; desktop Chrome/Edge was unavailable. HTTP success and matching PDF hashes were verified, but native embedding was not. Do not assume a cause before reproducing.

Read docs/release-2026-09-24.md and the current Reports implementation first. Work from current main, preserving scheduled news changes and any newer approved Chinese PDF version. You own Reports-specific public/app.js and public/index.html changes, any necessary local viewer assets, focused browser tests and report-viewer documentation. You are not alone in the codebase; do not revert others' work. Do not change news grouping, ranking, filters, pipeline, report content or public/data. Leave .claude/ untouched. Codex remains the integrator.

Diagnose the native application/pdf object in real desktop Chrome/Edge. Make direct in-page reading the primary experience. If browser-native support cannot meet the requirement reliably, use a locally hosted PDF renderer and document that it is an inline renderer rather than the browser's native plugin. Check current official documentation and maintenance/security status before choosing a dependency. Avoid unrelated frontend changes. Retain Open/Download as secondary controls, preserving existing features.

Acceptance: actually visible English and Chinese page content inside Reports; correct approved file per language; working scrolling and zoom; usable desktop/mobile layout; accessible controls; useful loading/error states; no blank pane presented as success. Preserve news navigation, page language behavior and existing tests. Verify PDF bytes remain unchanged. Use synthetic failures without modifying public/data.

Return exact code changes, dependency/version decision if applicable, tests and actual browsers exercised, visual evidence of both embedded reports, and remaining limitations. Do not publish independently or force-push.
