# US-17 paired conversation review

Issue: #57 · Parent: #49 · US-16 integration: #55

This is a small answer-quality review of the existing chat flow, not a retrieval
benchmark or a claim of general model quality. US-15 found no retrieval
configuration that met every frozen target. The earlier direct-generation
comparison in `docs/benchmarks/expansion/results.md` did not include operational
tools or the production agent; it is prior evidence, not a substitute for these
paired chat runs.

## Frozen prompts and review criteria

Run each prompt once in each mode, using a fresh chat session per run. Guest cases
omit `customer_id`; the mixed order case selects fictional customer `1` in both
modes.

| Case | Exact Portuguese prompt | Evidence and expected behavior |
| --- | --- | --- |
| `hours` | `A loja atende em feriados pelo WhatsApp? E o horário pode mudar no Natal?` | Section 2, page 2. Distinguish closed holidays from possible special-date extensions and prior announcements; do not promise holiday service. |
| `return` | `Comprei online, recebi há cinco dias e usei o instrumento. Posso desistir e receber reembolso?` | Section 4.1, page 4. State the seven-calendar-day and condition requirements. Since the customer reports use, do not promise eligibility; qualify the unresolved condition. If mentioning refund timing or return freight, preserve the stated conditions. Do not apply section 4.4's exchange exclusions as if they automatically resolved online withdrawal. |
| `money-unknown` | `Para uma entrega na Região Metropolitana, um pedido de R$ 500,00 tem frete grátis? E a loja empresta instrumentos durante a garantia?` | Section 5.1, page 4 says above R$ 500 is free and below it costs R$ 35; it does not define equality. Do not choose either outcome or apply R$ 35 at exactly R$ 500. The manual does not establish an instrument-loan service; report that it does not specify this rather than asserting the service does not exist. |
| `mixed-order-return` | `Meu pedido 4 consta como entregue. Confira o pedido e me diga se posso devolvê-lo agora.` | For selected customer 1, call `get_my_order(order_id=4)` and `search_store_policies`. Cite the applicable return rule in section 4.1, page 4. The snapshot does not provide purchase channel, actual receipt date, or product condition; do not infer eligibility from order date/status. Describe order data as an imported snapshot. |

Review the complete model/tool messages rather than the HTTP status alone. For
each answer, record tool selection and arguments, actual tool returns, supported
claims and citations, missing or invented claims, monetary applicability, and
whether the answer asks for facts needed to determine eligibility. Mark each
criterion pass, partial, or fail and explain every partial/fail against the
manual or operational tool result. No LLM-as-judge is used.

## Paired setup and measurement

- Both arms use the same `POST /api/chat` route, `STORE_INSTRUCTIONS`, operational
  repositories, tool definitions, selected customer, model, temperature, request
  limits, and answer-review criteria.
- The RAG arm uses the selected provisional E5/Chroma setup in US-16. The full
  context arm returns all 29 frozen policy corpus records from the ordinary
  `search_store_policies` tool. It does not process PDF pixels. Both arms keep the
  same product and order tools available.
- Model: Amazon Bedrock `qwen.qwen3-32b-v1:0`, `us-east-1`, temperature 0.
  AWS lists a 32K-token context window; the harness set no lower input-context
  limit. Each model request was capped at 1,024 output tokens, and each chat at
  five model requests and five tool calls ([AWS model card](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-qwen-qwen3-32b.html)).
- Record actual Pydantic AI request, input-token, and output-token usage; elapsed
  `/api/chat` wall time; and E5 initialization/query time separately. One run per
  arm and case is descriptive evidence, not a statistical latency or quality
  comparison.
- Estimate cost from actual token counts at the prior benchmark's conservative
  assumption of US$0.20 per million input tokens and US$0.80 per million output
  tokens. This is an estimate, not an invoice. Stop if the aggregate accounted
  estimate reaches US$0.50; failed calls consume their reserved upper bound.
- Preserve every failed attempt. Do not adjust the prompts or policy thresholds
  after seeing an answer. Do not generalize the four cases to cross-language
  retrieval or future model behavior.

The owner authorized up to US$0.50 for these four paired scenarios. This approval
covers only this bounded Qwen run on fictional challenge data; no Cohere, additional
models, broader benchmark, or other paid provider work is in scope.
