# Security

## Supported status

This repository is an engineering-beta orchestration primitive, not a production security boundary.

## Design boundaries

- Objectives and handler outputs are treated as data and are never evaluated as code.
- Agent count, objective size and per-agent timeout are bounded.
- Credentials and provider configuration are intentionally absent from the core engine.
- The container runs as a non-root user.

Integrators remain responsible for authentication, authorization, rate limiting, tenant isolation, provider credential storage, network policy, prompt-injection defenses and data-retention requirements.

## Reporting

Do not publish live credentials or exploit details in a public issue. Use GitHub's private vulnerability reporting when enabled for this repository, or contact the repository owner through an established private channel.
