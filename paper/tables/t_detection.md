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
