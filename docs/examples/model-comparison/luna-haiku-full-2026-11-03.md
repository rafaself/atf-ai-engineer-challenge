# GPT-6 Luna / Haiku 5.5 full benchmark readiness

Status: **completed under a fresh approved US$4.00 cap**. The
[full results](full-qwen-luna-haiku-2026-11-03.md) record all 60 HTTP turns,
reviewed outcomes and US$0.0660410225 estimated cost. AWS CLI account checks and the existing
runner's no-inference preflight used the explicit profile
`towelbooks-management-admin`. Both US system profiles are ACTIVE, and both base
models have AVAILABLE agreement/entitlement/region and AUTHORIZED access.

## Executed run plan

- Retain the current application, prompt and policy preparation unchanged.
- Run the frozen v7 full benchmark: 12 conversations / 20 HTTP turns per model.
- Models: Qwen3 32B control, `us.openai.gpt-6-luna`, and
  `us.anthropic.claude-haiku-5-5`, all through Bedrock Runtime Converse.
- Preserve 15-second provider timeout, six-request/five-tool limits and 1,024
  output-token cap. New models use provider-default reasoning. The installed SDK
  recognizes both and strips unsupported sampling parameters; temperature zero
  is therefore not asserted to take effect for these models.
- No dependency update, production-agent change, new provider or alternate API.
- Both new profiles completed live client-tool Converse roundtrips in the full
  benchmark; control-plane availability alone was not used as proof.
- Review answer correctness, tool use, false refusals, unnecessary questions,
  retries and end-to-end latency separately. Preserve all HTTP/provider failures.

## Verified pricing and reservation

USD per million tokens, Standard US geographic cross-region inference:

| Model | Input / output | Long-context threshold | Long input / output | Full HTTP-turn reservation |
| --- | ---: | ---: | ---: | ---: |
| Qwen3 32B | 0.15 / 0.60 | — | — | 0.0324864 |
| GPT-6 Luna | 0.11 / 0.55 | over 272,000 input tokens | 0.22 / 0.825 | 1.7375688 |
| Haiku 5.5 | 0.11 / 0.55 | over 100,000 input tokens | 0.55 / 2.75 | 3.316896 |

Luna's reservation also covers the documented implicit cache-write premium.
Observed cost uses the applicable context tier and includes that premium; cache
reads are conservatively charged at full input rates. Haiku implicit caching is
unsupported and explicit caching is not enabled. Original candidate rates remain
unchanged. These two models are absent from the legacy regional Bedrock bulk
offer; their rates were verified from the current model card / foundation-model
pricing feed rather than invented from the legacy offer.

Sources: [AWS Luna model card](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-openai-gpt-6-luna.html),
[AWS Haiku model card](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-anthropic-claude-haiku-5-5.html),
[AWS pricing page](https://aws.amazon.com/bedrock/pricing/) and its
[foundation-model pricing feed](https://b0.p.awsstatic.com/pricing/2.0/meteredUnitMaps/bedrockfoundationmodels/USD/current/bedrockfoundationmodels.json).
The local [readiness record](luna-haiku-readiness-2026-11-03.json) preserves exact
Haiku rate identifiers, feed hash and profile-check results.

## Budget boundary

At preflight, the preceding approved US$1.00 had US$0.61915675 remaining,
which could not satisfy the full-context reservations for either new model.
The owner then approved a **fresh US$4.00 cap**. The runner ceiling and its
rejection test were updated to that explicitly approved amount before inference;
full-context reservations were preserved. The run spent an estimated
US$0.0660410225, leaving US$3.9339589775 of the fresh cap. The initial US$0.05–0.15
normal-workload estimate was not used to bypass the conservative turn guard.

## Validation

The new-candidate regression failed before registration and passed after the
change. Tests cover exact US routes, long-context price thresholds/reservation,
Luna cache-write premium, rejection of incomplete tiers, explicit profile
precedence, and preserving stop-on-baseline-failure behavior for all seven
registered candidates. Final backend suite: **379 passed**. Ruff lint/formatting and
diff checks passed.

[No-inference full preflight](preflight-luna-haiku-full-2026-11-03.json):
`ready_no_paid_calls`, local retrieval ready, all three candidates available,
12 scenarios, 20 turns per model, zero paid calls. Use `--profile` on the runner
to preserve the explicitly requested profile rather than relying on dotenv.
