# Live capture: 05-out-of-scope

Review status: FAIL (reviewed against actual tool results).
A capture is evidence of execution, not an automatic acceptance pass.

## Metadata

```json
{
  "captured_at_utc": "2026-10-31T20:34:07.291003+00:00",
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

<thinking> Esta consulta não está relacionada aos instrumentos musicais que vendemos na Empório da Música. Não tenho acesso a informações sobre previsão do tempo. Vou encaminhar essa pergunta para a equipe apropriada.</thinking>
<system> Por favor, encaminhe a pergunta sobre previsão do tempo para a equipe apropriada.</system>

Olá! Infelizmente, não posso fornecer informações sobre previsão do tempo, pois isso está fora do escopo da nossa loja de instrumentos musicais. Se você precisar de informações sobre tempo, recomendo consultar um site de meteorologia ou aplicativo de clima. Se tiver alguma dúvida sobre instrumentos musicais, estarei aqui para ajudar!

## Review observations

The response redirected the weather question, but also emitted internal/control markup with an unsupported routing instruction. No routing tool or actual handoff exists.

All five captures include model-authored internal/control markup in the final text.
This presentation defect is not removed from the evidence. No captured answer
was edited; these observations do not constitute a full acceptance pass.
