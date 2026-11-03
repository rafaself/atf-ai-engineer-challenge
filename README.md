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

## Technical Decisions


### Framework / Agent approach


### Provider

I chose Amazon Bedrock primarily because I already have some experience with the platform and have been studying its capabilities. I also have remaining AWS credits, which allow me to experiment without significant cost concerns. Beyond that, Bedrock provides access to foundation models from multiple providers through a unified API, along with services and tools for building AI agents. This makes it a practical choice for experimenting with and developing LLM-powered applications.

### Model Selection

I compared ten models using a fixed benchmark of 16 Portuguese conversations and 26 HTTP turns per model. GPT-6 Luna and GPT-6.1 Sol were the only candidates to pass all selection gates: both received Pass on all 16 assessed conversations, completed all 26 HTTP turns, and had zero observed critical errors. I provisionally recommend GPT-6 Luna because the two models tied on these quality and reliability measures, while Luna's estimated main-run cost was about 19.7 times lower than Sol's (US$0.0194 versus US$0.3815). Sol had a lower median latency (4.82 seconds versus 5.41 seconds), but I judged Luna's cost advantage the stronger tradeoff for this project. The recommendation is based on one unblinded AI assessment without independent human review, so it is provisional and does not establish general model superiority. The runtime default remains unchanged.

| Model | Pass / Partial / Fail | Reviewed / completed / 16 | HTTP success / attempted / 26 | Main / preflight estimated USD | Input / output tokens | Provider attempts / missing usage | Median / max latency (s) |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Amazon Nova Micro | 6 / 5 / 4 | 15 / 15 / 16 | 25 / 26 / 26 | 0.009382380 / 0.000413350 | 220340 / 6585 | 61 / 1 | 2.5087865000000003 / 5.576448 |
| Amazon Nova Lite | 7 / 1 / 5 | 13 / 13 / 16 | 23 / 26 / 26 | 0.01775856 / 0.00067110 | 246303 / 7327 | 67 / 1 | 3.6289095 / 7.44033 |
| NVIDIA Nemotron Nano 3 30B | 2 / 5 / 9 | 16 / 16 / 16 | 26 / 26 / 26 | 0.01078050 / 0.00047280 | 156615 / 5765 | 43 / 0 | 2.5202999999999998 / 6.607463 |
| NVIDIA Nemotron Super 3 120B | 12 / 2 / 2 | 16 / 16 / 16 | 26 / 26 / 26 | 0.03381415 / 0.00111445 | 197105 / 6536 | 52 / 0 | 3.2001939999999998 / 9.075601 |
| GPT-OSS 20B | 11 / 1 / 4 | 16 / 16 / 16 | 26 / 26 / 26 | 0.01264563 / 0.00036444 | 144069 / 8536 | 56 / 0 | 4.6813555000000004 / 9.911643 |
| GPT-OSS 120B | 9 / 2 / 4 | 15 / 15 / 16 | 25 / 26 / 26 | 0.02494935 / 0.00078765 | 130609 / 8930 | 52 / 0 | 3.205159 / 7.575956 |
| Qwen3 32B | 7 / 4 / 5 | 16 / 16 / 16 | 26 / 26 / 26 | 0.02742675 / 0.00101745 | 165021 / 4456 | 49 / 0 | 2.7865955 / 4.618212 |
| Claude Haiku 5.5 | 12 / 3 / 1 | 16 / 16 / 16 | 26 / 26 / 26 | 0.03857942 / 0.00121814 | 278687 / 14407 | 53 / 0 | 5.554346499999999 / 8.731618 |
| GPT-6 Luna | 16 / 0 / 0 | 16 / 16 / 16 | 26 / 26 / 26 | 0.0193957775 / 0.000631510 | 140704 / 4936 | 55 / 0 | 5.405984500000001 / 20.982316 |
| GPT-6.1 Sol | 16 / 0 / 0 | 16 / 16 / 16 | 26 / 26 / 26 | 0.38154490 / 0.0124762 | 142760 / 3906 | 55 / 0 | 4.8178465 / 10.057997 |

These costs are benchmark estimates, not invoices. See the [full benchmark results](docs/evaluations/model-selection/results.md) for the scenario matrix and evaluation limits.

### User Interface

I chose React as the primary user interface because I believed it would provide a better experience for interacting with the agent. I also implemented a CLI for users who prefer working in the terminal.

### Data Persistence


### Data Processing

I decided to process some data to make the informations retrieved by the model cleaner. One of them was about the holiday.

## Known limitations and evidence

- I didn't make too much tests in the embedding process, I choose a light and simple approach in this flow. So it could be tested better as well, but I got good results though.
- The demo currently depends on Bedrock for live model inference, with the provider integration isolated behind an agent boundary.
- Answer-quality problems were more evident with lower-performing models such as Qwen3 32B. GPT-6 Luna and GPT-6.1 Sol performed well on the evaluated scenarios, but that does not guarantee they will always answer correctly.
- Earlier runs showed Qwen misreading a conditional Christmas-hours policy. It passed that specific case in the later benchmark, so describe the issue as an observed failure mode, not a persistent failure.
- The application enforces structured business rules and customer scoping, and checks for blank responses or internal markup. It does not comprehensively verify every generated claim or screen every answer for sensitive content.


## AI-assisted development

I used an iterative, human-led workflow to develop the project. I contributed directly to the code and used AI agents as guided collaborators. I stayed responsible for the scope, architectural choices, tradeoffs, and acceptance criteria, treating AI suggestions as proposals to evaluate rather than decisions to accept automatically.

I used ChatGPT mainly to explore approaches, clarify requirements, structure work into issues or stories, and refine technical prompts. Codex was my main environment for repository work, including implementation, refactoring, testing, reviews, and subagent coordination. The roles overlapped: I also used Codex to plan when its access to the codebase was useful, and ChatGPT sometimes helped formalize project artifacts.

I planned work from the challenge requirements and project goals, turning them into bounded tasks with clear outcomes, constraints, and validation expectations. I emphasized simplicity, correctness, code quality, and maintainability, and refined plans when a proposal exceeded the task’s scope or added complexity without enough value.

For larger or parallel tasks, I used separate branches and Git worktrees to isolate changes and let work proceed against a specific repository state. I delegated independent, well-bounded tasks to subagents, giving each a clear objective, scope or file ownership, constraints, and expected deliverables. I kept dependent work sequenced, then integrated and reviewed the results centrally to catch conflicts and check them against the original requirements.

Repository guidance helped make this process repeatable. `AGENTS.md` documented project-wide working agreements and constraints; repository skills under `.agents/skills/` provided focused workflows for tasks such as implementing work items, domain testing, and architecture audits. These instructions helped align agent work with the project’s scope, quality expectations, and validation practices.

I've made some mistakes in the beginning, the project was going into a unnecessary complexity, I had to go back and review the codebase in order to change and proceed with a clearer direction. Also I took too much time trying to improve the quality using only Qwen-3 32B, although it's a very good model, it hallucinates in some ambiguos or not too much clear context. That was one of the reason that I proceeded with data processing, some points in the policits was not too clear such as the time context related to "Natal" and "Feriados".

The usual cycle was to define the goal and boundaries, plan the work, delegate where it made sense, review the changes, and validate the result. I used delegation where it reduced execution time, while keeping coordination overhead, rework, and unnecessary complexity under control.

## Architecture

The Docker setup runs a local FastAPI service that serves the React chat. The API uses the shared `emporio_music` Python package to manage conversations and call a Bedrock-backed agent; the optional CLI uses the same package directly. SQLite stores product, order, and conversation data. Store policies are indexed locally with E5 embeddings and Chroma. See the [architecture details](docs/architecture.md).

## Tests

From the repository root, run `make check` for the documented project checks.
