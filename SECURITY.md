# Security Policy

## Supported versions

This is a pre-1.0 hackathon MVP. Only the `main` branch is supported.

## Reporting a vulnerability

Please report security issues **privately** — do not open a public issue for a
vulnerability.

1. Go to the repository's **Security** tab → **Report a vulnerability** to open a
   [GitHub private vulnerability report](https://docs.github.com/en/code-security/security-advisories/guidance-on-reporting-and-writing-information-about-vulnerabilities/privately-reporting-a-security-vulnerability).
2. Include a description, reproduction steps, and the impact you observed.

We aim to acknowledge reports within 7 days. Because this is a student project,
response times are best-effort.

## Scope and data handling

- The MVP processes **review text only**. Reviewer identity fields are dropped at
  ingestion (see `src/cri/loader.py`) and are never stored.
- No credentials are required to run the project. Configuration is via environment
  variables; never commit a real `.env` file (see `.env.example`).
- Do not submit real personal data, scraped content, or proprietary datasets in
  issues or pull requests.
