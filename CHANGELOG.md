# Changelog

## Unreleased

### Added
- explicit asynchronous handler registry and bounded sequential orchestration core
- per-agent timeout and output validation
- API task capacity and concurrency controls
- verification tests for ordering, timeout, validation, and capacity
- Ruff, pytest, dependency-audit, Docker build, and non-root CI gates
- explicit security and product-scope documentation

### Changed
- removed simulated LLM-call behavior from the original demo path
- replaced placeholder CI that only echoed a test message
- updated runtime dependencies and Python container baseline
- documented the repository as an engineering beta rather than an enterprise/production system
