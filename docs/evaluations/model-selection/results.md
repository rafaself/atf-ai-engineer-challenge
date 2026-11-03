# Standalone final model comparison

Status: **ai_review_complete**.

Selection: **gpt6_luna**. Runtime default unchanged.

Estimated total including preflight and unknown-usage reservations: **US$0.5954445075**.

Semantic verdicts are a user-authorized, unblinded AI assessment without independent human review. Human worksheets remain available.

| Model | Pass / Partial / Fail | Reviewed / completed / 16 | HTTP success / attempted / 26 | Main / preflight USD | Input / output tokens | Provider attempts / missing usage | Median / max latency (s) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| nova_micro | 6 / 5 / 4 | 15 / 15 / 16 | 25 / 26 / 26 | 0.009382380 / 0.000413350 | 220340 / 6585 | 61 / 1 | 2.5087865000000003 / 5.576448 |
| nova_lite | 7 / 1 / 5 | 13 / 13 / 16 | 23 / 26 / 26 | 0.01775856 / 0.00067110 | 246303 / 7327 | 67 / 1 | 3.6289095 / 7.44033 |
| nemotron_nano_3_30b | 2 / 5 / 9 | 16 / 16 / 16 | 26 / 26 / 26 | 0.01078050 / 0.00047280 | 156615 / 5765 | 43 / 0 | 2.5202999999999998 / 6.607463 |
| nemotron_super_3_120b | 12 / 2 / 2 | 16 / 16 / 16 | 26 / 26 / 26 | 0.03381415 / 0.00111445 | 197105 / 6536 | 52 / 0 | 3.2001939999999998 / 9.075601 |
| gpt_oss_20b | 11 / 1 / 4 | 16 / 16 / 16 | 26 / 26 / 26 | 0.01264563 / 0.00036444 | 144069 / 8536 | 56 / 0 | 4.6813555000000004 / 9.911643 |
| gpt_oss_120b | 9 / 2 / 4 | 15 / 15 / 16 | 25 / 26 / 26 | 0.02494935 / 0.00078765 | 130609 / 8930 | 52 / 0 | 3.205159 / 7.575956 |
| qwen3_32b | 7 / 4 / 5 | 16 / 16 / 16 | 26 / 26 / 26 | 0.02742675 / 0.00101745 | 165021 / 4456 | 49 / 0 | 2.7865955 / 4.618212 |
| claude_haiku_5_5 | 12 / 3 / 1 | 16 / 16 / 16 | 26 / 26 / 26 | 0.03857942 / 0.00121814 | 278687 / 14407 | 53 / 0 | 5.554346499999999 / 8.731618 |
| gpt6_luna | 16 / 0 / 0 | 16 / 16 / 16 | 26 / 26 / 26 | 0.0193957775 / 0.000631510 | 140704 / 4936 | 55 / 0 | 5.405984500000001 / 20.982316 |
| gpt6_1_sol | 16 / 0 / 0 | 16 / 16 / 16 | 26 / 26 / 26 | 0.38154490 / 0.0124762 | 142760 / 3906 | 55 / 0 | 4.8178465 / 10.057997 |

## Scenario matrix

| Scenario | nova_micro | nova_lite | nemotron_nano_3_30b | nemotron_super_3_120b | gpt_oss_20b | gpt_oss_120b | qwen3_32b | claude_haiku_5_5 | gpt6_luna | gpt6_1_sol |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| catalog-budget-ordinal | partial | fail | pass | pass | pass | fail | pass | pass | pass | pass |
| named-stock-alternative | partial | failed | partial | pass | pass | partial | fail | pass | pass | pass |
| promotion-pix | fail | failed | fail | pass | pass | pass | fail | pass | pass | pass |
| no-match | pass | pass | partial | pass | pass | pass | pass | pass | pass | pass |
| selected-orders-list-detail | pass | pass | fail | pass | pass | pass | pass | pass | pass | pass |
| guest-order-request | pass | pass | partial | pass | pass | pass | pass | pass | pass | pass |
| policy-hours-context-topic-change | partial | partial | partial | pass | pass | pass | pass | pass | pass | pass |
| mixed-order-return-followup | partial | fail | fail | fail | fail | fail | partial | partial | pass | pass |
| freight-exact-threshold | pass | pass | fail | pass | pass | pass | pass | pass | pass | pass |
| outside-online-window | pass | pass | fail | pass | pass | partial | partial | partial | pass | pass |
| used-without-marks-and-procedure | fail | fail | fail | partial | fail | fail | fail | pass | pass | pass |
| in-store-preference-scope | partial | fail | fail | pass | pass | pass | partial | pass | pass | pass |
| final-online-return-missing-accessory | fail | failed | fail | partial | fail | fail | partial | partial | pass | pass |
| final-bass-two-references | fail | pass | partial | pass | pass | pass | fail | pass | pass | pass |
| final-order-total-vs-unit | failed | fail | fail | fail | fail | failed | fail | fail | pass | pass |
| final-christmas-conditional-hours | pass | pass | pass | pass | partial | pass | pass | pass | pass | pass |

## Limits

One targeted regression pass, not a statistical superiority claim or a blind holdout. Fixed RAG and unchanged production agent; no prompt tuning or model substitution. Execution failures and unexecuted turns remain in reliability counts. Costs are conservative estimates, not invoices. The owner waived human/independent second review after capture. Semantic judgments and selection are provisional AI findings; the original blank human forms remain available for later review.
