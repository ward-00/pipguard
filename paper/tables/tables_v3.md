### Coverage of OSV malicious PyPI names by period of the OSV report

| OSV report period | Names | Downloadable (%) | Reconstructed | Reconstructed (%) |
|---|---|---|---|---|
| 2022 H1 | 10 | 100.0 | 10 | 100.0 |
| 2022 H2 | 10 | 100.0 | 7 | 70.0 |
| 2023 H1 | 6399 | 100.0 | 5488 | 85.8 |
| 2023 H2 | 68 | 100.0 | 31 | 45.6 |
| 2024 H1 | 1737 | 99.9 | 1191 | 68.6 |
| 2024 H2 | 908 | 100.0 | 522 | 57.5 |
| 2025 H1 | 484 | 100.0 | 254 | 52.5 |
| 2025 H2 | 761 | 100.0 | 457 | 60.1 |
| 2026 H1 | 1033 | 100.0 | 492 | 47.6 |
| 2026 H2 | 390 | 100.0 | 136 | 34.9 |
| All | 11800 | 100.0 | 8588 | 72.8 |

Downloadable = at least one download in the ClickPy download log (independent of the metadata table). Reconstructed = per-version metadata available, which the evaluation requires.

### Time from the first malicious upload to the OSV report and to the last recorded download

| Period | n | Report: median (days) | Reported ≤ 1 d (%) | ≤ 7 d (%) | ≤ 30 d (%) | Last client download: median (days) | ≤ 7 d (%) | ≤ 30 d (%) |
|---|---|---|---|---|---|---|---|---|
| < 2025 | 7431 | 0.1 | 78.9 | 79.0 | 81.3 | 1 | 72.4 | 72.9 |
| 2025 | 611 | 0.1 | 75.0 | 80.4 | 88.1 | 1 | 90.6 | 94.7 |
| 2026 | 546 | 0.0 | 82.2 | 91.0 | 95.2 | 1 | 93.5 | 97.0 |
| All | 8588 | 0.1 | 78.8 | 79.9 | 82.7 | 1 | 75.1 | 76.0 |

Last client download = end of the last day (age bucket) with a download by pip, uv, poetry, pdm or pipenv; it approximates removal from PyPI. Packages without any client download are excluded from that column.

### Malicious packages grouped into campaigns

| Split | Packages | Campaigns | Single-package campaigns | Largest campaign | Largest share (%) |
|---|---|---|---|---|---|
| dev | 7431 | 1102 | 891 | 5407 | 72.8 |
| val | 611 | 387 | 276 | 12 | 2.0 |
| test | 546 | 339 | 258 | 22 | 4.0 |

### Percentage of packages for which each indicator fired, by period

| Group | Period | n | I-02 | I-04 | I-05 | I-07 | I-08 | I-09 |
|---|---|---|---|---|---|---|---|---|
| Malicious | < 2025 | 7431 | 99.7 | 90.2 | 2.4 | 87.7 | 16.1 | 6.4 |
| Malicious | 2025 | 611 | 98.5 | 53.8 | 3.8 | 12.1 | 56.6 | 36.3 |
| Malicious | 2026 | 546 | 94.1 | 46.5 | 2.4 | 20.3 | 43.0 | 37.0 |
| New legitimate | < 2025 | 2213 | 100.0 | 37.1 | 1.1 | 11.8 | 33.3 | 18.4 |
| New legitimate | 2025 | 1598 | 100.0 | 35.4 | 0.8 | 3.5 | 24.0 | 24.8 |
| New legitimate | 2026 | 1039 | 100.0 | 25.8 | 0.9 | 1.9 | 14.6 | 20.9 |

### Choice of the I-10 dormancy period on development and validation data

| Dormancy period G (days) | Old-project malicious releases caught (dev + val) | Established dev packages prompted (snapshot) | Install-client downloads prompted (%) |
|---|---|---|---|
| 30 | 21/35 (60.0) | 310/3000 (10.33) | 4.420 |
| 60 | 18/35 (51.4) | 200/3000 (6.67) | 2.856 |
| 90 | 18/35 (51.4) | 158/3000 (5.27) | 1.889 |
| 180 | 16/35 (45.7) | 71/3000 (2.37) | 1.496 |
| 365 | 13/35 (37.1) | 28/3000 (0.93) | 0.837 |

Decision rule fixed before the test data were scored: the smallest G whose download share does not exceed that of the 30-day project-level cooldown.

### Detection results on the 2026 test data, % [95% interval]

| Detector | Malicious (n = 546) | New legitimate (n = 1039) | Established (n = 2000) | Malicious, campaign bootstrap |
|---|---|---|---|---|
| pipguard (final design) | 94.1 [91.8–95.8] | 100.0 [99.6–100.0] | 0.1 [0.0–0.3] | [91.1–96.6] |
|   DANGER level only | 50.9 [46.7–55.1] | 16.3 [14.1–18.6] | 0.1 [0.0–0.3] | [44.2–57.4] |
|   with I-10, G = 90 d (opt-in) | 97.3 [95.5–98.3] | 100.0 [99.6–100.0] | 3.8 [3.0–4.7] | [95.7–98.5] |
|   with I-10, G = 365 d (opt-in) | 94.9 [92.7–96.4] | 100.0 [99.6–100.0] | 1.2 [0.8–1.8] | [91.8–97.2] |
| Initial design (iteration 1) | 94.1 [91.8–95.8] | 100.0 [99.6–100.0] | 4.5 [3.7–5.6] | [91.1–96.6] |
| Early calibration (rejected) | 14.5 [11.8–17.7] | 1.3 [0.7–2.1] | 0.00 [0.00–0.19] | [9.4–20.5] |
| Project-level cooldown, 30 d | 94.1 [91.8–95.8] | 100.0 [99.6–100.0] | 0.1 [0.0–0.3] | [91.1–96.6] |
| Release-level cooldown, 30 d | 100.0 [99.3–100.0] | 100.0 [99.6–100.0] | 26.2 [24.4–28.2] | [100.0–100.0] |
| Existence check only | 0.0 [0.0–0.7] | 0.00 [0.00–0.37] | 0.00 [0.00–0.19] | [0.0–0.0] |
| Name similarity only | 2.4 [1.4–4.0] | 0.9 [0.5–1.6] | 1.8 [1.3–2.4] | [0.9–4.4] |

Flagged = installation requires confirmation (or, for the release-level cooldown, the newest release is withheld). Wilson intervals treat packages as independent; the last column resamples campaigns.

### pipguard under each installation-time scenario (test data)

| Scenario | Malicious flagged | Malicious at DANGER | New legitimate flagged | New legitimate at DANGER |
|---|---|---|---|---|
| First malicious release (primary) | 94.1 (514/546) | 50.9 (278/546) | 100.0 (1039/1039) | 16.3 (169/1039) |
| Last release | 93.2 (509/546) | 50.9 (278/546) | 65.8 (684/1039) | 9.5 (99/1039) |
| At OSV report | 90.5 (494/546) | 49.5 (270/546) | – | – |

### Malicious releases in projects that were already at least 30 days old

| Year of the first malicious upload | Malicious packages | In projects ≥ 30 d old | Share (%) | Caught by I-10, G = 90 d | Caught by I-10, G = 365 d | Withheld by a 30-day release-level cooldown |
|---|---|---|---|---|---|---|
| ≤ 2020 | 78 | 5 | 6.4 | 0 | 0 | 5 |
| 2021 | 52 | 4 | 7.7 | 0 | 0 | 4 |
| 2022 | 164 | 2 | 1.2 | 1 | 1 | 2 |
| 2023 | 6255 | 7 | 0.1 | 5 | 3 | 7 |
| 2024 | 882 | 8 | 0.9 | 7 | 6 | 8 |
| 2025 | 611 | 9 | 1.5 | 5 | 3 | 9 |
| 2026 | 546 | 32 | 5.9 | 17 | 4 | 32 |

### Re-fitting the early model on development data without the 2023 mass campaign

| Development data | Points | WARNING threshold | Recall 2025 (%) | Recall 2026 (%) | FPR new legitimate 2026 (%) |
|---|---|---|---|---|---|
| All development data (as rejected) | I-02 39, I-04 18, I-05 18, I-07 35, I-08 2 | 76 | 10.3 | 14.5 | 1.3 |
| Without the largest campaign | I-02 34, I-04 7, I-05 19, I-07 22, I-08 12 | 42 | 60.4 | 50.9 | 15.9 |
| Each campaign weighted equally | I-02 31, I-04 5, I-05 17, I-07 26, I-08 9 | 58 | 10.3 | 14.5 | 1.3 |

### Sensitivity of campaign-level results to the campaign definition

| Definition (window, linkage) | Campaigns (all) | Largest campaign | Campaigns (2026) | Recall 2026, campaign bootstrap (%) | I-07 campaign-weighted, < 2025 (%) | I-07 campaign-weighted, 2026 (%) | Stopped, project 30 d, campaign-weighted 2026 (%) | Stopped, release 30 d, campaign-weighted 2026 (%) |
|---|---|---|---|---|---|---|---|---|
| 3 d, all keys | 1931 | 5323 | 354 | 91.2–96.7 | 63.5 | 16.1 | 92.0 | 98.5 |
| 7 d, all keys (main) | 1826 | 5407 | 339 | 91.1–96.6 | 64.8 | 16.5 | 91.6 | 98.4 |
| 14 d, all keys | 1753 | 5407 | 325 | 90.8–96.6 | 65.1 | 16.3 | 91.4 | 98.5 |
| 30 d, all keys | 1680 | 5407 | 311 | 91.1–96.7 | 66.3 | 16.2 | 91.1 | 98.5 |
| 7 d, e-mail only | 1898 | 5407 | 350 | 91.0–96.5 | 64.1 | 16.0 | 91.6 | 98.4 |
| 7 d, e-mail or description | 1873 | 5407 | 348 | 91.1–96.6 | 64.5 | 16.1 | 91.8 | 98.5 |

### Source-only distribution of malicious packages from the download log, by year of the first download

| Period | No built distribution downloaded: reconstructed, % (n) | Not reconstructed, % (n) | I-07, shortest-lived third (%) | I-07, middle third (%) | I-07, longest-lived third (%) |
|---|---|---|---|---|---|
| < 2025 | 86.8 (7,462) | 77.1 (1,943) | 78.4 | 99.7 | 84.9 |
| 2025 | 11.5 (611) | 26.3 (501) | 6.4 | 14.3 | 15.6 |
| 2026 | 20.0 (515) | 29.5 (767) | 14.8 | 28.6 | 17.6 |

### High-impact PyPI incidents and the cooldown policies

| Project | First malicious upload | Malicious versions | Project age (days) | Days since previous release | Client downloads of malicious versions | Last day with a client download | Stopped: project 30 d (%) | Stopped: release 1 d (%) | Stopped: release 30 d (%) | I-10 (G = 90 d) fires |
|---|---|---|---|---|---|---|---|---|---|---|
| ultralytics | ≈ 2024-12-04 | 4 | 1,386 | 1 | 91,745 | 1 | 0.0 | 52.5 | 100.0 | no |
| ctx | 2022-05-14 | 9 | 2,703 | 2703 | 290 | 9 | 0.0 | 19.0 | 100.0 | yes |
| num2words | 2025-07-28 | 2 | 4,444 | 223 | 12,207 | 1 | 0.0 | 100.0 | 100.0 | yes |
| lightning | 2026-04-30 | 2 | 1,415 | 89 | 3,319 | 46 | 0.0 | 99.7 | 99.9 | no |
| aiocpa | ≈ 2024-11-20 | 2 | 80 | – | 27 | 1 | 0.0 | 59.3 | 100.0 | no |
| torchtriton | 2022-12-17 | 2 | 0 | – | 2,162 | 9 | 100.0 | 3.2 | 100.0 | no |

### Malicious install-client downloads stopped by 30-day cooldowns, by estimator and period

| Period | Estimator | Project-level 30 d (%) | Release-level 30 d (%) |
|---|---|---|---|
| 2026 (test) | Mean per package | 93.4 [90.1–96.0] | 98.9 [98.1–99.5] |
| 2026 (test) | Mean per campaign | 91.6 [88.7–94.4] | 98.4 [97.2–99.4] |
| 2026 (test) | Download-weighted | 59.4 [39.4–91.2] | 77.7 [55.0–98.6] |
| 2026 (test) | Download-weighted, top 1 excluded | 70.9 | 93.1 |
| 2026 (test) | Download-weighted, top 10 excluded | 87.8 | 96.6 |
| 2025 | Mean per package | 96.5 [95.1–97.7] | 97.7 [96.6–98.6] |
| 2025 | Mean per campaign | 95.2 [93.3–96.9] | 96.8 [95.3–98.1] |
| 2025 | Download-weighted | 54.7 [28.6–92.3] | 90.7 [81.9–95.8] |
| 2025 | Download-weighted, top 1 excluded | 85.6 | 87.3 |
| 2025 | Download-weighted, top 10 excluded | 94.2 | 96.2 |
| < 2025 | Mean per package | 92.2 [80.8–94.4] | 92.4 [81.6–94.5] |
| < 2025 | Mean per campaign | 79.1 [77.0–81.1] | 80.0 [78.0–82.0] |
| < 2025 | Download-weighted | 3.4 [1.0–41.3] | 4.0 [1.1–44.7] |
| < 2025 | Download-weighted, top 1 excluded | 21.2 | 25.2 |
| < 2025 | Download-weighted, top 10 excluded | 53.3 | 54.1 |
| All periods | Mean per package | 92.6 [86.3–94.4] | 93.2 [88.0–94.7] |
| All periods | Mean per campaign | 84.8 [83.4–86.2] | 86.9 [85.6–88.3] |
| All periods | Download-weighted | 4.6 [1.3–45.8] | 5.9 [1.8–54.2] |
| All periods | Download-weighted, top 1 excluded | 26.0 | 33.2 |
| All periods | Download-weighted, top 10 excluded | 55.5 | 58.8 |

95% intervals resample campaigns. Download-weighted = all stopped client downloads / all client downloads.

### Protection (2026 malicious packages) and cost (monthly share of client downloads) by threshold

| T (days) | Project: stopped per package (%) | Project: stopped, download-weighted (%) | Project: downloads affected, median [IQR] (%) | Release: stopped per package (%) | Release: stopped, download-weighted (%) | Release: downloads affected, median [IQR] (%) | Cost ratio release / project (median) |
|---|---|---|---|---|---|---|---|
| 1 | 84.4 | 35.9 | 0.0003 [0.0002–0.0004] | 89.3 | 51.2 | 0.28 [0.24–0.32] | 1,006 |
| 2 | 89.3 | 45.6 | 0.0005 [0.0004–0.0007] | 94.6 | 61.6 | 0.93 [0.77–1.04] | 1,568 |
| 7 | 92.1 | 56.9 | 0.0014 [0.0011–0.0024] | 97.6 | 74.2 | 3.31 [2.88–3.71] | 1,968 |
| 14 | 92.9 | 58.4 | 0.0038 [0.0026–0.0057] | 98.7 | 76.3 | 5.95 [5.45–6.54] | 1,554 |
| 30 | 93.4 | 59.4 | 0.0113 [0.0088–0.0176] | 98.9 | 77.7 | 11.08 [10.19–12.14] | 973 |
| 60 | 94.0 | 62.0 | 0.0338 [0.0245–0.0557] | 99.5 | 81.7 | 18.56 [17.06–19.98] | 555 |
| 90 | 94.5 | 66.8 | 0.0757 [0.0574–0.1123] | 99.6 | 85.3 | 24.29 [22.24–25.05] | 331 |
