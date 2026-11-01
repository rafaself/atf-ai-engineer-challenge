# US-17 paired conversation review: results

Run date: 2026-11-01. The owner approved four paired scenarios (eight real
`POST /api/chat` calls) using fictional challenge data. One RAG request returned
HTTP 500. All successful and failed model/tool messages are preserved in the
[sanitized capture file](captures.json); it omits transient session and provider
response identifiers. The frozen prompts and rubric are in [protocol.md](protocol.md).

## Setup and measurement

Both arms ran through the existing chat route with the same Amazon Bedrock Qwen3
32B generator (`qwen.qwen3-32b-v1:0`, `us-east-1`, temperature 0), persona,
tool schemas, operational data, output validator, prompts, and answer rubric.
AWS lists a 32K-token context window; the harness imposed no lower input-context
limit. Each conversation was limited to five model requests and five tool calls,
with 1,024 output tokens per request ([AWS model card](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-qwen-qwen3-32b.html)).
Three guest scenarios omitted `customer_id`; the mixed order scenario selected
fictional customer `1` in both arms.

The RAG arm used the current provisional E5/Chroma setup. The full-policy arm
used the same `search_store_policies` tool but returned all 29 corpus records for
each policy query; the exact returned records are in the captures and the
versioned [policy corpus](../../../data/policies/corpus.json). This is a
generation-context comparison, not a retrieval metric. The corpus, questions,
and chunks were frozen at SHA-256 `b7527f96896929f4ba929de117651c6717e25b7a3b92b34bc54d5ba32f6156f7`,
`936d946b94800b21822eccdb346cd6109db5501c9775c0d4ff08a6a334114a3c`, and
`6426725ac6f20628474ea4175814726ff968a08127491b239515ba6b8219303d` respectively.

Token counts and request counts are the actual Pydantic AI usage returned by
successful conversations. HTTP latency is the measured client wall time for
one route call. RAG warm-up is reported separately; it includes local model
initialization and a preflight query, not the `/api/chat` call. Estimated costs
use the frozen assumption of US$0.20 per million input tokens and US$0.80 per
million output tokens. They are estimates, not AWS invoice amounts.

| Case | Arm | HTTP | Requests; input/output tokens | `/api/chat` seconds | E5 preflight seconds | Estimated cost |
| --- | --- | ---: | ---: | ---: | ---: | ---: |
| hours | RAG | 200 | 3; 11,241 / 249 | 2.963 | 10.937 (3 records) | $0.0024474 |
| hours | Full policy | 200 | 3; 19,272 / 281 | 3.295 | — | $0.0040792 |
| return | RAG | 200 | 3; 11,854 / 452 | 3.492 | 11.905 (7 records) | $0.0027324 |
| return | Full policy | 200 | 2; 10,989 / 293 | 2.985 | — | $0.0024322 |
| money-unknown | RAG | 500 | Usage unavailable | 3.193 | 8.461 (3 records) | $0.036864 worst-case reserve |
| money-unknown | Full policy | 200 | 3; 28,829 / 312 | 3.854 | — | $0.0060154 |
| mixed-order-return | RAG | 200 | 2; 6,396 / 172 | 2.292 | 11.173 (4 records) | $0.0014168 |
| mixed-order-return | Full policy | 200 | 2; 6,396 / 55 | 1.751 | — | $0.0013232 |

Seven successful chats used 94,977 input and 1,814 output tokens in total. Their
usage-based estimated cost was $0.0204466. The failed RAG chat has no captured
agent usage; its five-request maximum was reserved at $0.036864, bringing total
budget accounting to $0.0573106 of the approved $0.50 cap. The failed call's
actual provider charge is unknown. On the three cases where both arms returned
answers, RAG used 29,491 versus 36,657 input tokens, with 873 versus 629 output
tokens. This small, uneven sample cannot establish a general cost or latency
advantage; notably, RAG had one extra request for the return case and its cold
E5 load took about 8.5–11.9 seconds in these fresh processes.

## Review outcomes

| Case | RAG | Full policy | Reason |
| --- | --- | --- | --- |
| hours | Pass | Partial | RAG cited section 2 and correctly said holiday WhatsApp service is closed while special-date hours may be extended. Full policy explained the special-date extension but omitted that Sundays and holidays are closed. |
| return | Partial | Partial | Both retrieved/cited section 4.1 and stated its seven-day and condition requirements, but treated the customer's word “used” as conclusive proof of visible signs of use and categorically denied eligibility. Full policy also added an unasked 30-day defect exchange and selected contact details despite source discrepancies. RAG added unrelated warranty claims. |
| money-unknown | Failed request | Fail | RAG returned HTTP 500 after two successful policy-tool calls, so there was no answer. Full context opened “Sim” for an exactly R$ 500,00 order although section 5.1 defines only amounts above and below R$ 500,00; it also asserted the store does not lend instruments based only on the manual's silence. |
| mixed-order-return | Fail | Fail | Both called `get_my_order(order_id=4)` for the selected customer but neither called the policy tool. Full context said it would search and stopped. RAG cited shipping section 5.1 for returns, treated `estimated_delivery` as actual receipt, invented the current date, and gave a definitive denial. |

Only one of eight outcomes fully met its case rubric; three were partial and
four failed or produced no answer. Both arms missed the mixed tool-selection
requirement, so the full policy did not fix this observed failure. The failures
also show that source membership and a syntactically valid citation do not
establish a correct or applicable claim.

## Actual final answers and tool evidence

Answers below are the actual final HTTP responses. The capture file also retains
initial model responses, validator retry feedback, ordered tool calls/results,
and complete returned policy records. Full-policy tool results are the entire
versioned 29-record corpus; RAG records are identified by corpus ID and preserve
their exact text in the capture.

### `hours`

RAG queried `atendimento em feriados pelo WhatsApp e horário no Natal` and
returned `policy-v2.1-s2` (section 2, p. 2), `s7.3` (7.3, p. 7), and `s7.1`
(7.1, p. 6). The relevant exact source is section 2, page 2. Full policy queried
`atendimento em feriados pelo WhatsApp` and returned all 29 records.

**RAG:**

> [política 2, p. 2] O atendimento via WhatsApp está fechado nos feriados, seguindo o mesmo horário do atendimento presencial. [política 2, p. 2] Em datas especiais como o Natal, o horário pode ser estendido, com comunicação prévia nas redes sociais e no atendimento via WhatsApp.

**Full policy:**

> O atendimento via WhatsApp da Empório da Música segue os mesmos horários de funcionamento da loja, com respostas automáticas fora do expediente. Em dias normais, o atendimento é de segunda a sexta-feira das 09:00 às 18:00, e aos sábados das 09:00 às 13:00. No Natal, o horário pode ser estendido, e as alterações são comunicadas com antecedência nas redes sociais e no atendimento via WhatsApp [política 2, p. 2].

Both initial answers lacked a required policy citation and triggered one output
validator retry. The RAG final answered the holiday question; the full-context
final did not.

### `return`

RAG queried `desistência e reembolso após uso do instrumento` and returned
`s4.1` (4.1, p. 4), `s4` (4, p. 4), `s4.2` (4.2, p. 4), `s4.4` (4.4, p. 4),
`s8.1`–`s8.3` (8.1–8.3, p. 7). Full policy queried the same topic and returned
all 29 records. Section 4.1 says a request may be made within seven calendar
days after receipt and requires original packaging, no signs of use, and all
accessories/manuals; it does not establish those last facts from “I used it.”

**RAG:**

> De acordo com a política da Empório da Música, você tem até 7 dias corridos após o recebimento do produto para exercer o direito de arrependimento, desde que o instrumento esteja em sua embalagem original, sem sinais de uso, com todos os acessórios e manuais [política 4.1, p. 4]. Como você já utilizou o instrumento, ele não atende a essas condições, e a devolução por arrependimento não será possível nesse caso.
>
> Se o instrumento estiver com algum defeito de fabricação, você pode solicitar uma troca em até 30 dias corridos após a compra [política 4.2, p. 4]. Caso contrário, danos causados por uso, quedas ou condições climáticas não são cobertos pela garantia [política 8.3, p. 7].
>
> Se quiser mais informações ou for possível descrever a situação do instrumento, posso ajudar a orientar melhor.

**Full policy:**

> De acordo com nossa política de trocas e devoluções, o direito de arrependimento para compras online permite que você solicite a devolução em até 7 (sete) dias corridos após o recebimento do produto, sem necessidade de justificativa. No entanto, para que a devolução seja aceita, o produto deve estar em sua embalagem original, sem sinais de uso, com todos os acessórios e manuais.
>
> Como você já utilizou o instrumento há cinco dias, ele não atende ao requisito de estar sem uso. Portanto, infelizmente, não será possível realizar a devolução nesse caso. Se houver algum defeito no instrumento, você poderá solicitar a troca ou a garantia, desde que esteja dentro do prazo de 30 dias corridos após a compra.
>
> Para mais informações, você pode consultar nossa política completa de trocas e devoluções [política 4.1, p. 4]. Se precisar de ajuda, entre em contato conosco pelo telefone (67) 3341-4444 ou e-mail contato@emporiodamusica.com.br.

The RAG first response omitted citations and received one validator retry. The
full-policy answer returned without a retry. The final answers are preserved
verbatim, including overconfident eligibility statements and extra claims.

### `money-unknown`

RAG's first policy search, `frete grátis para pedidos de R$ 500,00`, returned
`s5.1` (5.1, p. 4), `s5.2` (5.2, pp. 4–5), and `s5.3` (5.3, p. 5). Its second
search, `empresta instrumentos durante a garantia`, returned `s8.3` (8.3, p. 7),
`s4.4` (4.4, p. 4), `s4` (4, p. 4), `s4.2` (4.2, p. 4), `s8.1` (8.1, p. 7),
and `s8.2` (8.2, p. 7). Both full-policy searches returned all 29 records.
Section 5.1's exact threshold text is in the versioned corpus; it states free
shipping above R$ 500,00 and a fixed R$ 35,00 below it, leaving equality
unspecified. No record establishes an instrument-loan service.

**RAG:** HTTP 500 with `{"detail":"Conversation failed"}`. The two policy tool
calls returned evidence successfully; no final answer or Pydantic AI usage was
captured. The error was sanitized by the existing route, so its internal cause
is unknown. This failure was preserved and not retried.

**Full policy:**

> Sim, para a Região Metropolitana de Campo Grande, pedidos acima de R$ 500,00 têm frete grátis, conforme a política de frete da loja [política 5.1, p. 4]. Para pedidos abaixo desse valor, a taxa fixa é de R$ 35,00. No entanto, a loja **não oferece empréstimo de instrumentos durante a garantia** — não há menção a esse serviço nas políticas consultadas. Se precisar de mais detalhes, estou à disposição!

The full-context initial response lacked a citation and triggered one validator
retry. Its final still did not resolve threshold equality and inferred a
negative service claim from silence.

### `mixed-order-return`

Both arms selected customer `1` and called only
`get_my_order(order_id=4)`. The tool returned order date `2025-12-10`, status
`delivered`, `estimated_delivery` `2025-12-22`, total `R$ 799,90`, the Giannini
GF-3D Dreadnought Sunburst, and `data_basis: imported_snapshot`. Neither arm
called `search_store_policies`; consequently neither returned a policy excerpt
or valid policy evidence. The live calls were made on 2026-11-01.

**RAG:**

> Para verificar se você pode devolver o pedido, consultei a política da loja:
>
> De acordo com a política de devoluções [política 5.1, p. 4], você tem até 7 dias corridos, a partir da data de recebimento do produto, para solicitar a devolução. O pedido 4 foi entregue em 22/12/2025, e hoje é 10/01/2026. Portanto, o prazo de 7 dias já foi ultrapassado, e a devolução não pode ser feita.
>
> Se precisar de mais informações ou tiver outra dúvida, estou à disposição!

**Full policy:**

> Para verificar se você pode devolver o pedido, consultarei as políticas da loja. Vou buscar as informações relevantes sobre devoluções.

The RAG answer used a shipping citation for a return rule, converted an
estimated date into actual receipt, invented `10/01/2026`, and made a
definitive eligibility decision without the policy tool. The full-policy answer
recognized that policy lookup was needed but ended without performing it.

## Boundaries, existing regressions, and limitations

All guest runs omitted customer identity; only the mixed-order case selected a
customer. Both arms called the order tool for that selected customer and the
returned order identified its imported-snapshot basis. This is scenario review,
not a new cross-customer security proof. Existing API/order tests remain the
evidence for guest selection requirements and customer-scoped reads; see
`apps/backend/tests/test_api.py`, `apps/backend/tests/test_guest_demo.py`,
`apps/backend/tests/test_order_api.py`, and
`apps/backend/tests/test_order_regressions.py`.

The RAG failure and the incorrect full-context answers are retained as results.
Only eight route calls were observed once each; these are qualitative examples,
not statistically meaningful estimates of future model quality. No multilingual
retrieval conclusion follows from Portuguese-only conversations. US-15 still
found no configuration satisfying every frozen retrieval target. These
conversations show that this provisional RAG setup and the full-policy
generation baseline both need further work; they do not establish that RAG is
adequate or superior overall.
