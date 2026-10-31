# Live capture: 05-out-of-scope

Review status: PASS for the captured scenario (manual review of tool data and final output).
A capture is evidence of execution, not an automatic acceptance pass.

## Metadata

```json
{
  "captured_at_utc": "2026-10-31T20:52:51.856574+00:00",
  "model": "amazon.nova-micro-v1:0",
  "region": "us-east-1",
  "pydantic_ai": "2.64.0",
  "boto3": "1.43.123",
  "database_sha256": "bfc149afdb0bc5d98c0102dc49d00f3a71268f29aa37c27b736c969a7230422d",
  "requests": 1
}
```

## User

Qual será a previsão do tempo amanhã em Paris?

## Actual tool trace

```json
[]
```

## Actual answer

Desculpe, mas não posso fornecer previsão do tempo. Meu foco é ajudar com informações sobre instrumentos musicais vendidos na Empório da Música. Se você precisar de detalhes sobre algum instrumento, estarei aqui para ajudar!

## Review observations

No catalog tool was called. The answer politely redirected to instrument support without internal/control tags, routing instructions or a claimed handoff.

No internal/control markup appears in the final customer answer. The final
answer is the SDK result after application output validation and, for truncated
queries, the deterministic selection notice. This single run is evidence for the
scenario, not a guarantee about every possible future model answer.
