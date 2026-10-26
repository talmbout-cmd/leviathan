# Changelog

## 2026-10-26

- Minimal Python CLI reads now distinguish HTTP/transport/JSON-shape failures from successful empty results, with nonzero failure exits. Thread reads identify a returned page with continuation as partial.
- Added a bounded GET-only two-cursor history example, with consumption-before-checkpoint callbacks, terminal-page cursor handling, and explicit partial coverage. No posting, model calls, automatic scheduling or persistent logs are added.
