# Security

## Supported branch

Security fixes are accepted against the current default branch and active productization branch until the release is merged.

## Security model

The orchestration core executes only handlers registered by application code. Requests cannot provide Python module paths, shell commands, arbitrary URLs, or executable expressions. Objectives and stage lists are bounded, stages are allow-listed, handler output is size-bounded, and every agent has a configurable timeout.

The HTTP service additionally bounds total retained tasks and concurrent executions. Container packaging runs as a non-root UID. CI checks runtime dependencies with `pip-audit`.

## Not provided

This repository does not currently provide authentication, authorization, tenant isolation, durable audit logs, encrypted persistence, external-secret management, network egress controls, sandboxed tool execution, or protection suitable for accepting untrusted model/tool plugins. Put the service behind an authenticated gateway before exposing it outside a trusted environment.

## Reporting

Do not publish secrets, exploit payloads, or private data in a public issue. Use GitHub's private vulnerability reporting feature when enabled for this repository, or contact the repository owner through a private channel listed on the GitHub profile.
