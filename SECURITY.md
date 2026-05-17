# Security Policy

## Reporting

Report security issues privately via
[GitHub Security Advisories](https://github.com/therudywolf/DomainsResolver/security/advisories/new).
Do not open public issues for vulnerabilities.

## Secrets

- Git credentials for optional push features belong in environment variables or local config, not in the repository.
- Do not commit resolver input files that contain private infrastructure details if they must stay confidential.
