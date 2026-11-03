# Amazon Nova 2 Lite holiday-policy smoke evaluation (#43)

## Scope and setup

On 2026-11-02, the owner approved one bounded Nova 2 Lite run with a US$1 total
spending cap for the existing two-turn holiday conversation. It used Bedrock
Runtime Converse in `us-east-1` through the US Geo inference profile
`us.amazon.nova-2-lite-v1:0`, with the local E5 policy index and current
context-aware persona. Model and route details, the frozen price assumptions and
their sources are in [`nova2-pricing.json`](nova2-pricing.json). The evaluation
used the existing application harness and did not change production code or
policy evidence.

The exact turns were:

1. `Qual é o horário normal de funcionamento da loja?`
2. `E nos feriados e no Natal, há atendimento?`

The initial attempt received HTTP 503 `AccessDeniedException` before a model
response was captured. The owner updated IAM permissions, then approved one
retry within the original cap. The retry completed both turns with three
provider requests. The first attempt's US$0.17864704 reservation was carried
forward. The retry reserved at most US$0.71458816, so the combined worst-case
reservation was US$0.89323520, below the US$1 cap.

## Results

Tool choice and answer faithfulness are separate outcomes. On turn one, Nova 2
Lite called `search_store_policies` and received record `policy-v2.1-s2` from
`store_policies.pdf`, section 2, page 2. The record includes both the general
holiday closure and the qualification that hours may be extended on special
dates, including Natal. The first answer represented these facts and cited the
source.

On turn two, Nova 2 Lite made no repeated policy call. That was appropriate:
the preceding answer retained the relevant policy text, which was sufficient to
explain the general rule and say that the specific Christmas schedule was not
confirmed. The final answer instead stated that the store does not operate in
person on holidays and at Natal, then repeated that Natal hours may be extended.
That is contradictory and overstates what the policy establishes. **Tool use
was appropriate; answer faithfulness failed.** The capture does not establish
why the model made that inference.

| Turn | Policy lookup | Latency | Faithfulness |
| --- | --- | ---: | --- |
| Normal hours | Called; returned section 2, p. 2 | 7.694 s | Pass: included normal hours, holiday closure and special-date qualification |
| Holidays / Natal | No repeat lookup | 1.545 s | **Fail:** asserted a definite in-person closure while also saying special hours may be extended |

The evidence was present in the initial RAG result, so this sample indicates a
conditional-policy interpretation failure rather than a retrieval-coverage
failure. It supports retaining context-aware tool use for this exchange, but it
does not demonstrate reliable policy interpretation or justify another search,
prompt change or new retrieval mechanism by itself.

## Cost and limits

The completed retry recorded 10,833 input tokens and 279 output tokens across
three provider requests. At the frozen rates, its usage estimate was
US$0.00434214. Including the conservative reservation carried from the denied
attempt, cumulative estimated-or-reserved cost is US$0.18298918. This is an
estimate, not invoice data; the price source and snapshot date are recorded in
the pricing manifest. The first denied request's provider-side charge is
unknown, so its reservation remains in the cumulative total.

This is one conversation on one model. It cannot establish general model
quality, reliability, cost or latency. No product-topic switch or missing-policy
scenario was tested. No further Bedrock inference was performed after the
successful retry.

## Evidence and reproduction

- [Retry preflight, no paid calls](nova2-preflight-retry-2026-11-02.json)
- [Initial attempt: IAM denial](nova2-capture-2026-11-02.json)
- [Completed retry trace](nova2-capture-2026-11-02-retry.json)
- [Initial and post-IAM preflights](nova2-preflight-2026-11-02.json), [final initial preflight](nova2-preflight-final-2026-11-02.json)
- [Price assumptions and sources](nova2-pricing.json)
- [Archived focused evaluation runner](../../../scripts/archive/evaluate_nova2_holiday.py)

Captures preserve the actual model answers, tool calls, retrieved source record,
latencies, source hashes and budget accounting. Historical Qwen and Nemotron
captures were not edited. Repeating this live evaluation requires separate
approval and refreshed price and retrieval preflight checks.
