# Security

Meta Ads tools are read-only: fixed Graph API GET endpoints, no campaign changes
or spending. OAuth login exchanges credentials with Meta; it is separate from ad
operations. Account access is controlled by Meta permissions, not the default
account setting. Prefer `ads_read` and grant only the accounts needed.

Never put tokens or App Secrets in chat, public issues or screenshots. Claude's
extension fields are marked sensitive; its storage is managed by Claude. Browser
login instead creates an **unencrypted** local JSON file with owner-only permissions
(0600; new directory 0700 on macOS/Linux). No blanket Keychain claim is made.
See [Privacy](PRIVACY.md) for storage paths, revocation and removal.

The Apple Silicon package includes an offline fallback and a pinned updater.
Updates use official PyPI, exclude pre-releases/yanked wheels, and stay in the 0.1
series with launcher 0.1.17. They are installed and tested without Meta credentials,
then activated atomically on the next extension start. Existing environments are
retained. Do not disable macOS protections: packages are not Developer ID signed
or notarized.

[Architecture and previous security review](docs/security-review.md) documents
network restrictions, update isolation, threat boundaries and historical checks.
That review is not an independent audit or proof of live account access.

Report vulnerabilities privately to repository maintainers via GitHub private
vulnerability reporting when available. If unavailable, ask your administrator for
a private maintainer contact. Do not include secrets in public issues.
