# Offline benchmark results

These results measure CLI storage and retrieval behavior using generated records. No language-model inference was performed.

## Recovery after process restart

[CI run](https://github.com/nicetrykiddo/contextforge/actions/runs/39601201137) · commit `262823a3a37192496b86620faaed0fb9d8a44ef6` · 2026-10-21

| Metric | Python 3.10 | Python 3.12 |
| --- | ---: | ---: |
| Recovery cases passed | 11/11 | 11/11 |
| Distractor records | 48 | 48 |
| Restarts | 12 | 12 |
| Median retrieval | 78.88 ms | 59.23 ms |
| P95 retrieval | 88.50 ms | 60.54 ms |
| Ledger size | 25,247 B | 25,247 B |

Checks covered task-specific recovery at multiple context budgets, retrieval of specific evidence, corrupt optional reasoning storage, and snapshot content.

## Ledger growth

[CI run](https://github.com/nicetrykiddo/contextforge/actions/runs/39603160874) · 2026-10-21

| Records | Ledger | Python 3.10 lookup median | Python 3.12 lookup median | Python 3.10 snapshot | Python 3.12 snapshot |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 101 | 47.5 KB | 54.36 ms | 79.32 ms | 3.44 ms | 6.33 ms |
| 1,001 | 474 KB | 61.93 ms | 96.48 ms | 16.69 ms | 25.63 ms |
| 5,001 | 2.38 MB | 114.10 ms | 169.03 ms | 89.32 ms | 131.81 ms |
| 20,001 | 9.54 MB | 332.68 ms | 469.61 ms | 393.46 ms | 554.71 ms |

The snapshot ledger limit was raised to 64 MB after a 9.54 MB ledger exceeded the previous 8 MB limit. The current implementation retains eight snapshots. Lookup scans the JSONL ledger; processing time grows with record volume.

## Hypothesis retrieval

[Baseline CI](https://github.com/nicetrykiddo/contextforge/actions/runs/39608057560) · [Updated CI](https://github.com/nicetrykiddo/contextforge/actions/runs/39608648219) · 2026-10-21

| Seeded hypotheses | Baseline shown in hot context | Updated shown | Updated rejected shown |
| ---: | ---: | ---: | ---: |
| 0 | 0 | 0 | 0 |
| 10 | 8 | 2 | 0 |
| 100 | 8 | 2 | 0 |
| 1,000 | 8 | 2 | 0 |
| 5,000 | 8 | 2 | 0 |

Rejected records remain queryable. The test measures emitted context, not reasoning quality.

## Coverage

| Test category | Evidence |
| --- | --- |
| Offline recovery and CLI performance | Recorded above |
| Real-model task completion | Not measured |
| Real-model error or token reduction | Not measured |
| Native automatic compaction recovery | Not measured |

See [benchmark commands](../BENCHMARKS.md) for reproduction.
