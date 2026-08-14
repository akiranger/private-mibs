# Security Policy

## Supported Versions

This repository is a prototype/experimental project. Security support is limited:

| Version | Supported |
| ------- | --------- |
| main (current) | :white_check_mark: |
| previous experimental branches | :x: |

If you depend on this project in production, please contact the maintainers to arrange support or fork and maintain your own branch.

## Reporting a Vulnerability

Please report suspected vulnerabilities privately using GitHub's security
advisory flow (recommended) or by opening an issue labelled `security` if you
cannot use the private advisory channel.

What to include in a report:
- A clear description of the vulnerability and the affected versions/commits
- Proof-of-concept or reproduction steps (as minimal as possible)
- Suggested mitigations if available

Response expectations
- Acknowledgement within 5 business days
- Initial triage and risk assessment within 10 business days
- Fix timeline will depend on severity and maintainer availability

Responsible contacts
- Repository maintainers via the repository's Security Advisory flow (use GitHub Security)

Disclosure policy
- Coordinated disclosure is preferred: please give maintainers reasonable time to fix (typically 30 days) before public disclosure unless the vulnerability is being actively exploited.
- If you are not able to provide a private advisory, open an issue with the `security` label; maintainers will coordinate privately after initial triage.

## Security mitigations and notes
- This project is a prototype and not hardened for production use.
- For production deployments consider running behind hardened infrastructure and use well-supported SNMP stacks (net-snmp, pysnmp with up-to-date dependencies).

If you are a maintainer and want to update contacts or timelines, edit this file to add a valid security contact (email or a dedicated process).
