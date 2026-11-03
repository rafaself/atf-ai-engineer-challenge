<p align="center">
  <img src="docs/assets/banner-emporio-da-musica.webp" alt="Empório da Música" width="100%" />
</p>

<p align="center">
  A Portuguese-language AI customer-support demo for a fictional music store.
</p>

Use the React chat to explore products, orders and store policies. Product,
order and delivery data are local simulations, with no external fulfillment
or carrier calls.

## Getting Started

### Prerequisites

- Docker Engine on Linux, or Docker Desktop 4.34+ with host networking enabled,
  Docker Compose v2 and GNU Make. See Docker's [host networking setup](https://docs.docker.com/engine/network/drivers/host/).
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
served by the single Compose `app` service in host network mode. Uvicorn binds to
`127.0.0.1:8000`, so the app remains local; host mode avoids the Docker bridge
path, which some VPN or firewall policies may block. Host mode shares the host's
network namespace, and Docker Desktop requires version 4.34+ with host networking
enabled. Its named data volume persists snapshots, chat history, the policy
index and E5 cache; `make down` keeps that data. Only run
`docker compose down --volumes` when you intend to delete it. The demo has no
authentication, so use fictional data.

The standalone CLI is optional; see the [CLI guide](docs/guides/cli.md). For local
API and frontend development, see [API setup](docs/guides/api.md) and the
[frontend guide](apps/frontend/README.md).

## Model and technical choices

The application uses GPT-6 Luna through Amazon Bedrock Runtime's US cross-Region
inference profile by default. In the final model-selection benchmark, Luna and
GPT-6.1 Sol each received 16/16 Pass; Luna won the unchanged cost tiebreak. This
was an unblinded AI assessment without independent human review, not a general
quality guarantee. See the [final benchmark](docs/benchmarks/final-model-comparison/README.md).

React/Vite is served by FastAPI from the same origin. Pydantic AI makes typed
tool calls; deterministic Python and parameterized SQL handle structured
catalog, pricing and order facts. Policy answers use local Chroma retrieval with
cached multilingual E5 embeddings, and prompts constrain tool use and factual
claims. SQLite stores operational snapshots and conversation history. See
[architecture](docs/architecture.md), [Bedrock configuration](docs/guides/bedrock.md)
and [policy retrieval](docs/guides/policy-retrieval.md) for details.

## Known limitations and evidence

Retrieved sources and typed tools do not guarantee faithful generated prose.
The final model-selection benchmark is bounded evidence: five failed conversations
were not semantically scored, and no independent human review has occurred. See
the [benchmark analysis](docs/benchmarks/final-model-comparison/analysis.md) for
its scope and limitations. Offline checks verify application behavior, not current
model-answer quality.

For deterministic project checks, install Python 3.12+, `uv`, and Node.js 20.19+
or 22.12+, then run `make check` from the repository root.

## AI-assisted development

OpenAI Codex assisted with analysis, implementation, tests, review and the
GitHub workflow. Project changes and controlled checks were reviewed; benchmark
captures are revision-specific and are not presented as current-checkout quality
evidence. The [documentation index](docs/README.md) links to implementation guides,
decisions and the retained benchmark records.
