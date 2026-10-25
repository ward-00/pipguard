# Install-time cooldowns compared (2026-10-24T11:22:27Z; pip 26.2.2; uv 0.13.5 (x86_64-unknown-linux-gnu))

| Case | Package | pip (default) | pip --uploaded-prior-to P30D | pip --uploaded-prior-to P2D | uv --exclude-newer (30 d) | pipguard | pipguard + I-10 (90 d) |
|---|---|---|---|---|---|---|---|
| Unregistered name | (made-up name) | fails (no matching distribution) | fails (no matching distribution) | fails (no matching distribution) | fails (no matching distribution) | prompts (DANGER); cancelled without a terminal | prompts (DANGER); cancelled without a terminal |
| Project first published < 1 day ago | obey-cli | installs latest | fails (no matching distribution) | fails (no matching distribution) | fails (no matching distribution) | prompts (DANGER); cancelled without a terminal | prompts (DANGER); cancelled without a terminal |
| Project first published 10-15 days ago | openrbac | installs latest | fails (no matching distribution) | installs latest | fails (no matching distribution) | prompts (WARNING); cancelled without a terminal | prompts (WARNING); cancelled without a terminal |
| Established project, regular release < 30 days ago | certifi | installs latest | installs older (2026.7.22) | installs older (2026.10.19) | installs older (2026.7.22) | passes silently | passes silently |
| Established project, release < 30 days ago after > 90 days without releases | pluggy | installs latest | installs older (1.6.0) | installs latest | installs older (1.6.0) | passes silently | prompts (WARNING); cancelled without a terminal |
| Established project, no release in the last 30 days | requests | installs latest | installs latest | installs latest | installs latest | passes silently | passes silently |
