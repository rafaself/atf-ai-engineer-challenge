<p align="center">
  <img src="docs/assets/banner-emporio-da-musica.webp" alt="Empório da Música" width="100%" />
</p>

<p align="center">
  A Portuguese-language AI customer-support demo for a fictional music store.
</p>

## Summary

- [Overview](#overview)
- [Technologies](#technologies)
- [Getting Started](#getting-started)
  - [Requirements](#requirements)
  - [Configure AWS](#configure-aws)
  - [Build, prepare, and start](#build-prepare-and-start)
- [Architecture](#architecture)
- [Tests](#tests)
- [Model and technical choices](#model-and-technical-choices)
- [Known limitations and evidence](#known-limitations-and-evidence)
- [AI-assisted development](#ai-assisted-development)

## Overview

Empório da Música is an AI-powered customer support application for a fictional musical instrument store. Built with Python, FastAPI, React, and Pydantic AI, it combines structured SQL queries with Retrieval-Augmented Generation (RAG) to answer questions about products, pricing, availability, orders, and store policies. Powered by Amazon Bedrock, the application focuses on accurate, context-aware responses through a conversational interface.

## Technologies

- **Backend:** Python, FastAPI, Pydantic AI
- **Frontend:** React, TypeScript, Vite
- **LLM:** GPT-6 Luna by default, with Qwen3 32B as an alternative, via **Amazon Bedrock**
- **RAG:** ChromaDB, Multilingual E5 Embeddings
- **Database:** SQLite
- **Infrastructure:** Docker, Docker Compose
- **Package Management:** uv, npm
- **Testing:** Pytest

## Getting Started

### Requirements

- Docker Engine and Docker Compose. Docker Desktop requires version 4.34+ with host networking enabled.
- AWS credentials authorized to invoke the configured Bedrock model. Credentials are needed to chat, and model requests may incur charges.
- Internet access the first time you prepare the policy index.

### Configure AWS

From the repository root, create `.env` from the example if it doesn’t already exist:

```bash
test -f .env || cp .env.example .env
```

For Docker, put your AWS credentials in `.env`; Docker Compose does not mount your host AWS profile. Uncomment these lines and replace the placeholders with credentials issued for your AWS account:

```dotenv
AWS_ACCESS_KEY_ID=your-access-key-id
AWS_SECRET_ACCESS_KEY=your-secret-access-key
# AWS_SESSION_TOKEN=your-session-token
```

Uncomment and set `AWS_SESSION_TOKEN` when using temporary credentials. Use short-lived credentials with Bedrock invoke permissions when possible. Keep `.env` private and never commit it.

Confirm that `AWS_DEFAULT_REGION` and `BEDROCK_MODEL_ID` in `.env` point to a model your account can invoke. See [Bedrock setup](docs/guides/bedrock.md) for credential and permission details.

### Build, prepare, and start

Run these commands from the repository root. Choose either option.

**Using Make** (requires GNU Make):

```bash
make build
make prepare-data
make prepare-policy
make up
```

**Using Docker Compose** (does not require Make):

```bash
docker compose build app
docker compose run --rm app python -m emporio_music.prepare
docker compose run --rm app python -m emporio_music.prepare_policy_index --allow-download
docker compose up --detach app
```

Open the chat at [http://127.0.0.1:8000](http://127.0.0.1:8000). The API docs are at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

Preparing the policy index downloads the embedding model; do this once for each new data volume. The demo has no authentication, so use fictional data. Stop the app with `make down` or `docker compose down`.

## Architecture

The Docker setup runs a local FastAPI service that serves the React chat. The API uses the shared `emporio_music` Python package to manage conversations and call a Bedrock-backed agent; the optional CLI uses the same package directly. SQLite stores product, order, and conversation data. Store policies are indexed locally with E5 embeddings and Chroma. See the [architecture details](docs/architecture.md).

## Tests

From the repository root, run `make check` for the documented project checks.

## Model and technical choices

The application uses GPT-6 Luna through Amazon Bedrock Runtime's US cross-Region inference profile by default. In the retained model-selection evaluation, Luna and GPT-6.1 Sol each scored 16/16 Pass; Luna won the cost tiebreak. This was one unblinded AI assessment without independent human review, so the result is provisional rather than a general quality guarantee. See the [model-selection record](docs/evaluations/model-selection/README.md).

React/Vite is served by FastAPI from the same origin. Pydantic AI makes typed tool calls; deterministic Python and parameterized SQL handle structured catalog, pricing and order facts. Policy answers use local Chroma retrieval with cached multilingual E5 embeddings, and prompts constrain tool use and factual claims. SQLite stores operational snapshots and conversation history. See [architecture](docs/architecture.md), [Bedrock configuration](docs/guides/bedrock.md) and [policy retrieval](docs/guides/policy-retrieval.md) for details.

## Known limitations and evidence

Retrieved sources and typed tools do not guarantee faithful generated prose. The [model-selection record](docs/evaluations/model-selection/README.md) is a bounded, unblinded AI assessment. The [policy-context comparison](docs/evaluations/policy-context/README.md) still awaits human semantic review. Offline checks verify application behavior, not current model-answer quality. The [documentation index](docs/README.md) links to current guides, decisions and evaluation evidence.

For deterministic project checks, install Python 3.12+, `uv`, and Node.js 20.19+ or 22.12+, then run `make check` from the repository root.

## AI-assisted development

OpenAI Codex assisted with analysis, implementation, tests, review and the GitHub workflow. Project changes and controlled checks were reviewed; live model captures are retained separately with their source revisions and are not presented as current-checkout quality evidence. The [documentation index](docs/README.md) links to implementation guides, decisions and evaluation records.
