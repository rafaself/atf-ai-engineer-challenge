# Live validation attempt — 2026-10-31

Status: authentication blocker resolved after key activation; live interactions
completed with behavioral findings below. Earlier failed attempts are retained
for context. Credentials and local .env contents are not recorded.

## Passed local checks

- Catalog import: 9 categories and 65 products; source checksums unchanged.
- Supplied snapshot: 12 available violões at or below R$1,000, default 10 returned
  with truncation; Takamine GD20 at 219900 centavos with stock five; Giannini GF-3D
  has stock zero and is excluded from available-only results.
- Default offline suite: 130 tests passed. Ruff lint/format and strict mypy passed
  (30 source/test files). No real model requests are allowed in that suite.
- Actual local uvicorn server: /docs returned 200; a blank chat message returned
  422; a named-product request returned sanitized 503 with only
  `{"detail":"Agent service unavailable"}`. The server was stopped afterward.

## Live attempts

The bounded Bedrock probe loaded configuration using `uv run --env-file .env`.
Both a profile setting and an access-key pair were present. Explicit profile
selection first failed with ConfigurationError caused by ProfileNotFound.

The retry used the supplied environment access keys, clearing AWS_PROFILE and
AWS_DEFAULT_PROFILE only in the test process. The local .env was not modified.
AWS rejected the request with UnrecognizedClientException, surfaced by Pydantic AI
as ModelAuthenticationError. Preferred target: amazon.nova-micro-v1:0 in us-east-1.
The subsequent API check confirmed that this authentication failure maps to a
sanitized 503 instead of leaking the provider exception.

## Required next step

Configure valid credentials. For key-based authentication, remove profile selection
from the local .env and shell. If using temporary credentials, include the matching
AWS_SESSION_TOKEN. No credential values should be sent in chat or committed.

Then rerun the live probe, API conversation scenarios, and the real-example
recorder described in examples/README.md, using `--env-file .env`. Model access,
tool compatibility, natural-language grounding and the five live conversations
remain unverified; authentication failure does not establish their behavior.

## Retry after key activation

The same access-key authentication succeeded after the user activated the key.
Profile selection was still disabled only for the test processes; .env was not
modified. Nova Micro in us-east-1 completed the fresh-code tool round trip in two
requests. See examples/live-probe-2026-10-31.json for actual evidence.

The actual HTTP API returned /docs 200, blank-input 422, and a named GD20 chat 200.
The generated answer correctly stated R$2.199,00 and five units. The server was
stopped after testing. Five actual SDK conversations were captured and reviewed
under examples/live/; responses and tool traces are unchanged.

Findings that prevent full acceptance:

1. Budget search retrieved 12 matches with truncated=true, but the answer listed
   five and did not disclose that this was a partial result.
2. The explicit unavailable GF-3D lookup omitted available_only=false, so the model
   saw zero matches instead of the actual active/zero-stock entry. Its unavailable
   answer was not grounded in the item's status/stock.
3. Final answers exposed model-authored internal/control markup. The out-of-scope
   example also included an unsupported routing instruction despite no handoff tool.

GD20 facts and literal no-match handling passed their data checks. Out-of-scope
redirection appeared in the answer, but presentation/routing concerns remain.
The unchanged 130-test offline suite and quality checks passed before the key
activation; no production code was changed by these live tests. The five captures
are real evidence of both working behavior and defects, not a full acceptance pass.

Next: correct/evaluate prompting or output handling for the confirmed failures,
then rerun the affected live scenarios while preserving these original captures.
The previous authentication next-step section is historical and is now resolved.
