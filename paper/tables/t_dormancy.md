### Choice of the I-10 dormancy period on development and validation data

| Dormancy period G (days) | Old-project malicious releases caught (dev + val) | Established dev packages prompted (snapshot) | Install-client downloads prompted (%) |
|---|---|---|---|
| 30 | 21/35 (60.0) | 310/3000 (10.33) | 4.420 |
| 60 | 18/35 (51.4) | 200/3000 (6.67) | 2.856 |
| 90 | 18/35 (51.4) | 158/3000 (5.27) | 1.889 |
| 180 | 16/35 (45.7) | 71/3000 (2.37) | 1.496 |
| 365 | 13/35 (37.1) | 28/3000 (0.93) | 0.837 |

Decision rule fixed before the test data were scored: the smallest G whose download share does not exceed that of the 30-day project-level cooldown.
