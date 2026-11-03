# Empório da Música — customer-support agent

Empório da Música is a fictional Portuguese-language store-support demo. The
React chat is the recommended interface; product, order and delivery data are
local simulations, with no external fulfillment or carrier calls.

## Getting Started

### Prerequisites

- Docker Engine or Docker Desktop with Docker Compose v2, plus GNU Make.
- An AWS account and credentials authorized to invoke an Amazon Bedrock model.
- Internet access during the first policy-index preparation to download the
  pinned CPU E5 embedding model.

### Configure AWS and the model

From the repository root, create the ignored local environment file and edit it:

```bash
test -f .env || cp .env.example .env
```

The defaults are `AWS_DEFAULT_REGION=us-east-1` and
`BEDROCK_MODEL_ID=us.openai.gpt-6-luna`. For Docker, put temporary
`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` and `AWS_SESSION_TOKEN` credentials
in `.env` using your approved AWS credential workflow. Compose passes them to the
container at runtime; `.env` is Git-ignored and excluded from the Docker build context.
Compose does not mount your host `~/.aws` directory, so a host `AWS_PROFILE` or
SSO session alone is not available in the container. The chat can start without
AWS credentials, but sending a message makes a real Bedrock request and may incur
usage charges.

GPT-6 Luna remains the default. **If Luna cannot be invoked in your account,
Qwen3 32B is the recommended alternative for evaluation.** In `.env`, change
`BEDROCK_MODEL_ID` to `qwen.qwen3-32b-v1:0`; the repository's example region,
`us-east-1`, supports this Bedrock Runtime model in-region. The current [Qwen3
32B model card](https://docs.aws.amazon.com/bedrock/latest/userguide/model-card-qwen-qwen3-32b.html)
lists the other supported Runtime regions: `us-east-2`, `us-west-2`,
`eu-central-1`, `eu-north-1`, `eu-south-1`, `eu-west-1`, `eu-west-2`,
`ap-northeast-1`, `ap-south-1`, `ap-southeast-2`, `ap-southeast-3` and
`sa-east-1`. Qwen also requires valid credentials, model access and
`bedrock:InvokeModel` permission. There is no automatic model fallback.

> **Note:** Bedrock invocation can depend on the account, IAM permissions, AWS
> Region and model-access requirements. A model appearing in discovery results
> does not prove that the current account can invoke it; verify with an actual
> request. See AWS's current [model access and authorization
> guidance](https://docs.aws.amazon.com/bedrock/latest/userguide/model-access.html).
> In one development account, Luna appeared in discovery but initial inference
> failed. After requesting Claude Haiku 5.5 access, completing an additional AWS
> verification step and receiving approval, Luna and other previously failing
> models became callable. This sequence suggests account authorization or
> verification may have been involved, but did not establish the cause; Haiku
> access is not a general Luna prerequisite.

### Build, prepare data and start the chat

Run these commands from the repository root on a fresh checkout:

```bash
make build
make prepare-data
make prepare-policy
make up
```

`make prepare-data` creates the operational SQLite snapshots from the supplied
data. `make prepare-policy` explicitly downloads the pinned E5 model if needed
and creates the local Chroma index; it is required once for a new data volume.
If an index already exists, preparation fails rather than silently replacing it;
use `make rebuild-policy` only when intentionally rebuilding after a policy-source
change. Image build and normal startup do not prepare snapshots, download weights,
create or rebuild the index, or call Bedrock.

Open the React chat at [http://127.0.0.1:8000](http://127.0.0.1:8000). The API
docs are at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs). Both are
served by the single Compose `app` service on loopback. Its named data volume
persists snapshots, chat history, the policy index and E5 cache; `make down` keeps
that data. Only run `docker compose down --volumes` when you intend to delete it.
The demo has no authentication, so keep it on loopback and use fictional data.

The standalone CLI is optional; see the [CLI guide](docs/cli.md). For local
API and frontend development, see [API setup](docs/api.md) and the
[frontend guide](apps/frontend/README.md).

## Model and technical choices

The application uses GPT-6 Luna through Amazon Bedrock Runtime's US cross-Region
inference profile by default. The selected model followed a dated 12-conversation
comparison: Luna scored 11 Pass / 1 Partial / 0 Fail at lower cost and median
latency than GPT-6.1 Sol, which scored 12 / 0 / 0 at about 20.5 times the cost in
that sample. The capture came from a dirty source tree, so it is historical
evidence, not a quality validation of this checkout; see the
[reviewed comparison](docs/examples/model-comparison/full-qwen-luna-sol-2026-11-03.md).

React/Vite is served by FastAPI from the same origin. Pydantic AI makes typed
tool calls; deterministic Python and parameterized SQL handle structured
catalog, pricing and order facts. Policy answers use local Chroma retrieval with
cached multilingual E5 embeddings, and prompts constrain tool use and factual
claims. SQLite stores operational snapshots and conversation history. See
[architecture](docs/architecture.md), [Bedrock configuration](docs/bedrock.md)
and [policy retrieval](docs/policy-retrieval.md) for details.

## Known limitations and evidence

Retrieved sources and typed tools do not guarantee faithful generated prose.
Recorded model runs include unsupported policy conclusions and failed mixed
order/return conversations; review their revision and limits before relying on
them. Start with the [representative Portuguese conversations](docs/examples/submission.md),
the [dated model-evaluation index](docs/examples/model-comparison/README.md),
and the [US-18 failure report](docs/examples/us-18/README.md). Offline checks
verify application behavior, not current model-answer quality. Current follow-up
areas and prior decisions are recorded in [docs/follow-up.md](docs/follow-up.md).

For deterministic project checks, install Python 3.12+, `uv`, and Node.js 20.19+
or 22.12+, then run `make check` from the repository root. See the
[validation record](docs/validation.md) for scope and results.

## AI-assisted development

OpenAI Codex assisted with analysis, implementation, tests, review and the
GitHub workflow. Project changes and controlled checks were reviewed; live model
captures are retained separately with their source revisions and are not
presented as current-checkout quality evidence. The [documentation index](docs/README.md)
links to implementation guides, decisions and evaluation records.
