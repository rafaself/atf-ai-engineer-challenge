# Prompt and harness evaluation: Qwen3 32B and GPT-OSS 120B — 2026-11-03

## Result

Both models completed all nine conversations and 16 planned HTTP turns. Every
turn returned HTTP 200; the run recorded 77 model calls, no missing usage, and
an estimated **US$0.02442870** against the separately approved **US$1.00 cap**.
This is a token-rate estimate, not an AWS invoice. The reviewed
[capture](capture-prompt-harness-qwen32-gptoss120-2026-11-03.json) includes the
responses, tool traces, source freeze, token usage, costs, and per-conversation
review. The no-inference [v3 preflight](preflight-prompt-harness-qwen32-gptoss120-v3-2026-11-03.json)
confirmed current retrieval readiness and model availability after the runner
default was corrected.

| Model | Pass / partial / fail | Critical errors | Missed tools | Unsupported claims | HTTP errors | Model calls | Input / output tokens | Estimated cost | Median / max latency (s) |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Qwen3 32B | 5 / 3 / 1 | 0 | 3 | 2 | 0 | 37 | 75,249 / 2,199 | $0.01260675 | 1.483 / 5.056 |
| GPT-OSS 120B | 6 / 2 / 1 | 1 | 1 | 3 | 0 | 40 | 63,521 / 3,823 | $0.01182195 | 2.173 / 5.501 |

## Conversation review

- **Catalog grounding improved.** Both models returned specifications that were
  present in the new structured catalog `specs` field. GPT-OSS 120B found
  available alternatives after the customer asked. Qwen incorrectly filtered
  alternatives by the unavailable product name, received no matches, and said
  there were no alternatives. Qwen also answered the ordinal price/stock
  follow-up from history without the required fresh product lookup.
- **Policy retrieval remains inconsistent.** Qwen skipped the policy tool for
  both hours questions and claimed the store had no hours information. It
  correctly handled the later Takamine lookup. GPT-OSS gave the regular hours
  and Natal qualification, but repeated the policy search and described Natal
  as normally closed even though the specific schedule is unresolved.
- **Return handling is still the highest-risk failure.** Qwen asked about
  customer facts but omitted the seven-day request window and did not retrieve
  the policy. GPT-OSS 120B said a return could only be requested from day eight
  after a five-day receipt interval, reversing the policy. It also added a
  documents requirement and return-start process not established by the manual
  or available tools. This was its sole critical error.
- **Freight provenance held.** Both models applied the approved inclusive
  R$500 threshold only in the Metropolitan Region of Campo Grande. The answer
  and application note kept the equality clarification separate from the
  original PDF.
- **HTTP reliability was clean in this sample.** There were no HTTP errors,
  unexecuted turns, or missing usage records.

The review counted safe customer-selection handling as Pass even when the guest
request made an unnecessary `list_my_orders` call. Redundant or mis-scoped calls
are described in the conversation notes and missed-tool totals; they are not
counted as HTTP failures.

## Prompt, data, and harness changes

The system prompt was reduced from about 1,276 to 598 whitespace-separated
words. It keeps the necessary evidence boundaries and tool routing, distinguishes
snapshot data, manual rules, and customer reports, requires explicit missing
return facts, prohibits unsupported product attributes, and lets the application
append source references. The catalog tools now expose only structured product
specifications, not free-form descriptions. Order-tool guidance states which
return facts are absent from the imported order record.

The candidate also included the six-request allowance, one retry for unknown
tool names, and Unicode dash normalization. The runner now defaults to the
active `scenarios-current-v3.json` fixture and includes it in the source freeze.
The live capture was created immediately before that default correction and
therefore records the legacy `scenarios.json` fixture. Its nine scenario IDs and
all 16 user prompts match v3 exactly. The capture preserves the original fixture
hash and expected objects; each conversation also records the v3 review
expectation used for its verdict. No additional model calls were needed to
correct the review criteria.

## Comparison with the preceding remediation run

The prior reviewed run scored Qwen 6 / 2 / 1 with one critical error and GPT-OSS
120B 5 / 4 / 0 with none. This run scored Qwen 5 / 3 / 1 with no critical
errors and GPT-OSS 120B 6 / 2 / 1 with one critical return-policy error. The
catalog evidence appears to have reduced unsupported guitar specifications,
but neither the shorter prompt nor the clearer data prevented the observed
tool-selection and return-window failures. A one-pass, nine-conversation sample
cannot establish that one model is generally more reliable or attribute score
changes to an individual edit.

The next targeted improvement should make the return window and unresolved
eligibility conditions harder to conflate, potentially by returning a small
structured rule record alongside the policy text. Alternative searches should
also omit the unavailable product name when the customer asks for substitutes.
These are follow-up candidates; this evaluation did not implement them.

## Research references

- [OpenAI reasoning-model prompting guidance](https://developers.openai.com/api/docs/guides/reasoning-best-practices)
  recommends brief, direct instructions with clear constraints. It does not
  show that shortening alone fixes a model's tool choices.
- [Qwen3 function-calling guide](https://github.com/QwenLM/Qwen3/blob/main/docs/source/framework/function_call.md)
  documents template-dependent tool calling. Its recommended format should not
  be transplanted blindly into Bedrock Converse.
- [Bedrock structured outputs](https://docs.aws.amazon.com/bedrock/latest/userguide/structured-output.html)
  can constrain shape; a schema alone does not guarantee that content is
  evidence-backed.
- [τ-bench](https://arxiv.org/abs/2406.12045) evaluates multi-turn tool use and
  policy adherence, supporting review of the full conversation rather than only
  the final turn.
