# Full Qwen / GPT-6 Luna / GPT-6.1 Sol benchmark

GPT-6.1 Sol had the strongest manually reviewed task result in this one-run
sample: **12 Pass, 0 Partial, 0 Fail**. Luna had **11 / 1 / 0** and remains
much faster and cheaper. Sol is promising when answer accuracy justifies its
roughly 20.5× observed cost over Luna, but this 12-conversation run is too small
to establish a new default.

## Run setup

The user approved a fresh **US$5.00 total cap** and the AWS CLI profile
`towelbooks-management-admin`. The runner used that profile explicitly and
skipped project `.env` loading. A corrected rerun used a US$4.99820135 cap after
an earlier harness bug had already sent three Qwen requests estimated at
US$0.00179865. The corrected run completed the unchanged
[v7 fixture](scenarios-current-v7.json): 12 conversations / 20 HTTP turns per
model.

| Model | Bedrock Runtime model ID |
| --- | --- |
| Qwen3 32B control | `qwen.qwen3-32b-v1:0` |
| GPT-6 Luna | `us.openai.gpt-6-luna` |
| GPT-6.1 Sol | `us.openai.gpt-6.1-sol` |

AWS CLI preflight found all three authorized and available; Luna and Sol
inference profiles were ACTIVE. The run then completed **120 Converse model
requests** (40 per model), with 60/60 HTTP turns successful, zero HTTP errors,
zero execution failures and no missing usage records. The live Sol run made 21
tool calls and completed tool-result round trips, establishing compatibility
with this application’s client-side tool loop. AWS documents Converse support
for GPT-6.1 Sol on `bedrock-runtime`; its model card also says Converse supports
implicit caching but not explicit `cachePoint` caching.

## Results

| Model | Pass / partial / fail | Critical errors | Tool calls | Median / max seconds | Input / output tokens | Estimated cost |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Qwen3 32B | **7 / 4 / 1** | 1 | 20 | 2.561 / 7.131 | 137,180 / 3,882 | US$0.02290620 |
| GPT-6 Luna | **11 / 1 / 0** | 0 | 22 | **2.096 / 7.008** | 101,184 / 3,356 | **US$0.01315078** |
| GPT-6.1 Sol | **12 / 0 / 0** | 0 | 21 | 3.984 / 6.403 | 101,484 / 2,743 | US$0.27023975 |

Verdicts are manual and use the v7 expected facts, critical-error definitions,
recorded tool arguments/results, and customer-facing answers. The raw run capture
is unchanged; the reviewed copy records the scenario verdicts and recomputes
aggregates. Qwen's single Fail is the wrong-ID PIX lookup that caused a false
unavailability claim. Luna's one Partial is an unnecessary repeat question
about signs of use after the customer had already said the guitar had no marks.

## Notable behavior

- **Sol:** Correctly resolved the ordinal product and promotion follow-ups,
  selected the right policy scopes, preserved Natal uncertainty, distinguished
  estimated delivery from actual receipt, and acknowledged the unresolved email
  spelling and undocumented return-label process. No unsupported operational
  claim or false refusal was observed.
- **Luna:** Also answered the product, order, freight and return cases reliably.
  Its main UX issue was asking the customer to repeat a physical-condition fact
  already supplied. It made one redundant policy lookup in the Natal follow-up.
- **Qwen:** Missed the fresh product-detail lookup in the ordinal follow-up and
  passed the wrong product ID to the alternatives tool. In the PIX case it
  queried product ID 2 instead of the listed Ohana ID 121, then incorrectly said
  the available item was unavailable. It also over-specified a general contact
  as a returns SAC contact and offered to contact the store on the user's behalf.
  The heading “Hotéis e feriados” is a minor Portuguese UX typo.

The recorded tool-call counts were 20 for Qwen, 22 for Luna and 21 for Sol.
Luna and Sol each repeated the general-policy lookup on the holiday follow-up;
that answer was correct, and the extra read is reflected in their tool counts.
The guest-order guard safely required customer selection for all three models.

## Cost and limits

Corrected-run estimates total **US$0.3062967250**. Including the three calls
from the harness-bug attempt, the session estimate is **US$0.3080953750**, leaving
approximately **US$4.6919046250** of the approved cap. These are token-based
estimates, not invoice amounts. The runner conservatively bills cache reads at
the full input rate and includes cache-write premiums; all request input bounds
were below Sol's 272K short-context threshold. AWS lists US CRIS short-context
rates of $2.20 / 1M uncached input tokens and $11.00 / 1M output tokens for Sol;
long-context rates are higher.

This was one run of 12 conversations per model. Latency and quality can vary
across runs, and model-specific effective sampling behavior was not independently
calibrated. The measured result supports **Sol for a quality-first choice** and
**Luna for the current cost/latency trade-off**; it does not establish that Sol
will retain a perfect score on a larger sample.

## Artifacts and sources

- [Reviewed capture](capture-full-qwen-luna-sol-reviewed-2026-11-03.json)
- [Raw run capture](capture-full-qwen-luna-sol-fixed-2026-11-03.json)
- [Preflight](preflight-full-qwen-luna-sol-ready-2026-11-03.json)
- [Frozen v7 scenarios](scenarios-current-v7.json)
- [Pricing manifest](pricing.json)
- [GPT-6.1 Sol model card and US CRIS pricing](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-openai-gpt-6-1-sol.html)
- [AWS client-side tool use with Converse](https://docs.aws.amazon.com/bedrock/latest/userguide/tool-use-client-side.html)
- [Bedrock API compatibility](https://docs.aws.amazon.com/bedrock/latest/userguide/models-api-compatibility.html)
