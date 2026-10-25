# pipguard interception test results

Generated 2026-10-25T09:42:02Z by `scripts/test_interception.sh`
System: Linux 6.6.87.2-microsoft-standard-WSL2 x86_64; bash 5.1.16(1)-release; zsh 5.8.1 (x86_64-ubuntu-linux-gnu); pip 22.0.2

Test package: `zzz-pipguard-selftest-unregistered` (deliberately unregistered). `intercepted` = pipguard assessed the package
(new line in activity.log); `blocked` = cancelled before the real pip ran; `forwarded` = passed to the
real pip; `not checked` = pipguard ran but deliberately skipped the check; `bypass` = pipguard not involved.

| ID | Shell | Scenario | Expected | Observed | Exit | Pass |
|---|---|---|---|---|---:|:---:|
| b1 | bash | 1 Interactive shell (TTY), answer N | prompt-no | intercepted, prompt, blocked | 3 | yes |
| b1y | bash | 1 Interactive shell (TTY), answer Y | prompt-yes | intercepted, forwarded | 1 | yes |
| b2 | bash | 2 Active virtual environment | blocked | intercepted, blocked | 3 | yes |
| b3 | bash | 3 pip3 | blocked | intercepted, blocked | 3 | yes |
| b4 | bash | 4 python -m pip (active venv) | blocked | intercepted, blocked | 3 | yes |
| b5 | bash | 5 python3 -m pip | blocked | intercepted, blocked | 3 | yes |
| b6 | bash | 6 Non-interactive script (bash t.sh) | blocked | intercepted, blocked | 3 | yes |
| b7 | bash | 7 Python subprocess | blocked | intercepted, blocked | 3 | yes |
| b8 | bash | 8 pip install -r requirements.txt | blocked | intercepted, blocked | 3 | yes |
| b9 | bash | 9 Absolute path to the real pip (limitation) | bypass | bypass | 1 | yes |
| z1 | zsh | 1 Interactive shell (TTY), answer N | prompt-no | intercepted, prompt, blocked | 3 | yes |
| z1y | zsh | 1 Interactive shell (TTY), answer Y | prompt-yes | intercepted, forwarded | 1 | yes |
| z2 | zsh | 2 Active virtual environment | blocked | intercepted, blocked | 3 | yes |
| z3 | zsh | 3 pip3 | blocked | intercepted, blocked | 3 | yes |
| z4 | zsh | 4 python -m pip (active venv) | blocked | intercepted, blocked | 3 | yes |
| z5 | zsh | 5 python3 -m pip | blocked | intercepted, blocked | 3 | yes |
| z6 | zsh | 6 Non-interactive script (bash t.sh) | blocked | intercepted, blocked | 3 | yes |
| z7 | zsh | 7 Python subprocess | blocked | intercepted, blocked | 3 | yes |
| z8 | zsh | 8 pip install -r requirements.txt | blocked | intercepted, blocked | 3 | yes |
| z9 | zsh | 9 Absolute path to the real pip (limitation) | bypass | bypass | 1 | yes |
| x1 | bash | Script that activates its own venv (limitation) | bypass | bypass | 1 | yes |
| x2 | bash | Absolute interpreter path, as IDEs run pip (limitation) | bypass | bypass | 1 | yes |
| x3 | bash | CI job, stdin not a TTY (/dev/null) | blocked | intercepted, blocked | 3 | yes |
| x4 | bash | AI agent: subprocess, no TTY, output captured | blocked | intercepted, blocked | 3 | yes |
| x5 | bash | pip download (builds sdists) | blocked | intercepted, blocked | 3 | yes |
| x6 | bash | pip wheel (builds sdists) | blocked | intercepted, blocked | 3 | yes |
| x7 | bash | pip install -c constraints.txt | blocked | intercepted, blocked | 3 | yes |
| x8 | bash | --extra-index-url (warning notes dependency confusion) | blocked | intercepted, blocked | 3 | yes |
| x9 | bash | Custom primary index -i (not checked by design) | skipped | not checked (non-PyPI index), forwarded | 1 | yes |
| x10 | bash | Direct URL/VCS requirement (not on PyPI; not checked) | bypass | bypass | 1 | yes |
| x11 | bash | Safe package (requests) passes without a warning | safe | intercepted, safe, forwarded | 1 | yes |
| x12 | bash | uv pip install (other installer; limitation) | bypass | bypass | 1 | yes |
| x13 | bash | sudo-style secure_path without ~/.local/bin (limitation) | bypass | bypass | 1 | yes |
| x14 | bash | CI runner or container image without pipguard on PATH | bypass | bypass | 1 | yes |
| x15 | bash | CI runner or container image with pipguard on PATH | blocked | intercepted, blocked | 3 | yes |
| x20 | bash | Non-interactive shell (CI step): pip | blocked | intercepted, blocked | 3 | yes |
| x21 | bash | Non-interactive shell (CI step): python3 -m pip (limitation) | bypass | bypass | 1 | yes |
| x22 | bash | Agent subprocess from a non-interactive shell: python3 -m pip (limitation) | bypass | bypass | 1 | yes |
| x23 | bash | Python subprocess [sys.executable, -m, pip] (limitation) | bypass | bypass | 1 | yes |
| x16 | bash | PIPGUARD_ASSUME_YES=1 ignored by default (agent-resistant) | blocked | intercepted, blocked | 3 | yes |
| x17 | bash | PIPGUARD_ASSUME_YES=1 with allow_env_override | forwarded | intercepted, forwarded | 1 | yes |
| x18 | bash | PIPGUARD_DISABLE=1 ignored by default (agent-resistant) | blocked | intercepted, blocked | 3 | yes |
| x19 | bash | Fail-open: PyPI unreachable | failopen | check failed, forwarded (fail-open) | 1 | yes |

**All cases behaved as expected.**

Raw output of every case: `logs/<ID>.txt`.
