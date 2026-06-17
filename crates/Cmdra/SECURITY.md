# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 0.1.x   | :white_check_mark: |
| < 0.1   | :x:                |

## Reporting a Vulnerability

We take the security of **Cmdra** seriously. If you discover a security vulnerability, please do NOT open a public issue. Instead, report it privately.

Please report any security concerns directly to the maintainers.

### What to include

- A detailed description of the vulnerability
- Steps to reproduce (proof of concept)
- Potential impact
- Any suggested fixes or mitigations

We will acknowledge your report within 48 hours and provide a timeline for resolution.

## Security Best Practices

When using Cmdra in your projects:

- **Input Validation**: Always validate user input before processing
- **Plugin Security**: Only load plugins from trusted sources
- **Secret Management**: Never hardcode secrets in CLI configurations
- **Permission Scope**: Follow the principle of least privilege

## Dependencies

Cmdra regularly scans dependencies for known vulnerabilities using:

- `cargo audit` in CI/CD
- Dependabot for automated dependency updates
- Security advisories from RustSec

---

Thank you for helping keep the community secure!
