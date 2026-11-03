# Issue #78 raw benchmark results

No semantic verdict or architecture recommendation is included. Human review is pending under [protocol.md](protocol.md).

- Model: `us.openai.gpt-6-luna` via Bedrock Runtime Converse in `us-east-1`.
- Paired executions: 12 conversations; 36 planned user turns across both arms.
- Provider requests observed, including preflight: 66 / 240 ceiling.
- AWS-rate estimated cost, including separate cache rates: US$0.02122740.
- Average cost per model interaction (one prompt plus response, including preflight): US$0.00032163 across 66 requests.
- Protocol-conservative estimate, pricing cache reads at the uncached input rate: US$0.04014324.
- Pre-transmission worst-case reservations summed to US$0.26700768 / US$1.00 approved cap; 0 requests had unknown usage and remain reserved.
- `capture.json` is preserved unchanged. Its provisional in-run input-token and cost fields are superseded by the post-run [cost reconciliation](cost-reconciliation.json), which accounts for cache tokens reported separately by Converse.
- Failed/not-completed conversation executions: 0.
- Not-executed conversation executions: 0.
- Missing required tool calls with arm-specific tool sets: RAG 1; embedded 0. RAG policy-scope mismatches: 0.

| Arm | Completed conversations | Planned | HTTP turns | Model calls incl. preflight | Total input tokens | Output tokens | AWS-rate cost (USD) | Average USD/call | Median turn latency (s) | Maximum (s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| rag | 12 | 12 | 18 | 39 | 99886 | 3289 | 0.00719744 | 0.00018455 | 4.804 | 11.772296 |
| embedded | 12 | 12 | 18 | 27 | 201681 | 3867 | 0.01402996 | 0.00051963 | 4.098 | 13.439175 |

Cache-read and cache-write usage are separate token categories. See [cost-reconciliation.json](cost-reconciliation.json) for the raw token totals, per-request bounds, official-rate estimate, and protocol-conservative estimate. Per-turn tool compliance is reconciled using each arm's available tools in [operational-reconciliation.json](operational-reconciliation.json).

Retrieval ranking metrics have 5 eligible actual general-scope query calls. The per-query metrics and returned-record coverage are in [retrieval-metrics.json](retrieval-metrics.json).

Manual Pass/Partial/Fail scores remain blank in [review-worksheet-primary.json](review-worksheet-primary.json). A second independent review is required for every Partial, Fail, or critical finding.
