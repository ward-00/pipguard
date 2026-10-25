# pipguard latency benchmark (N=200 per condition)

Generated 2026-10-24T11:20:22Z. Environment: `env.txt`.

| Condition | Mean (ms) | Median (ms) | p95 (ms) | p99 (ms) | Max (ms) |
|---|---:|---:|---:|---:|---:|
| Set 1: real pip, index versions | 541.1 | 533.4 | 598.9 | 614.8 | 646.9 |
| Set 1: through the pipguard shim (passthrough) | 546.1 | 539.2 | 597.8 | 618.2 | 633.1 |
| Set 2: stub pip, no pipguard | 5.7 | 5.6 | 6.9 | 8.2 | 8.5 |
| Set 2: pipguard, empty cache (PyPI request) | 124.2 | 123.1 | 133.4 | 145.2 | 173.0 |
| Set 2: pipguard, warm cache (1 entry) | 16.8 | 16.5 | 20.1 | 20.7 | 21.0 |
| Set 2: pipguard, warm cache (1,000 entries) | 22.2 | 22.0 | 26.0 | 29.5 | 33.1 |
| Set 2: pipguard, -r file with 20 cached packages | 17.6 | 17.3 | 20.8 | 22.2 | 23.5 |
| Reference: Python start-up + reading the cache | 31.9 | 31.2 | 36.1 | 44.8 | 46.5 |
