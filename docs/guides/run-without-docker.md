# Run locally without Docker

This guide runs the API and React frontend directly on your machine. It uses the same local SQLite data and policy index as the Docker setup; no database server is needed.

## Requirements

- Python 3.12 or newer and [uv](https://docs.astral.sh/uv/).
- Node.js 20.19+ or 22.12+ and npm for the React frontend. npm is included with Node.js.
- AWS credentials authorized to invoke the configured Amazon Bedrock model. A host AWS profile, including SSO, works through the standard AWS credential chain.
- Internet access to install dependencies and download the policy embedding model the first time the index is prepared.

Docker and Docker Compose are not used by these steps. Model requests may incur AWS charges.

## Configure and prepare

Run these commands from the repository root:

```bash
test -f .env || cp .env.example .env
uv sync --project apps/api --locked --extra policy-rag
uv run --env-file .env --project apps/api --extra policy-rag --locked python -m emporio_music.prepare
uv run --env-file .env --project apps/api --extra policy-rag --locked python -m emporio_music.prepare_policy_index --allow-download
```

Edit `.env` to set `AWS_DEFAULT_REGION` and `BEDROCK_MODEL_ID` for a model your account can invoke. For profile-based authentication, set `AWS_PROFILE` to the configured host profile; for other authentication methods, use credentials available through the standard AWS credential chain. The app does not load `.env` itself, so the `uv --env-file .env` option is needed when starting the API. Existing shell environment variables take precedence over `.env` values.

The data preparation command imports the supplied CSV snapshots into local SQLite files. Preparing the policy index downloads the pinned local embedding model and creates the index under the configured data directory. Repeat data preparation when you intentionally want to refresh the imported snapshots; prepare the policy index once for each new data directory.

## Start the API and frontend

Start the API from the repository root:

```bash
uv run --env-file .env --project apps/api --extra policy-rag --locked uvicorn emporio_music_api.app:create_app --factory --host 127.0.0.1 --port 8000
```

In a second terminal, start the Vite development server:

```bash
npm --prefix apps/frontend ci
npm --prefix apps/frontend run dev
```

Open [http://127.0.0.1:5173](http://127.0.0.1:5173) for the chat. Vite forwards `/api` requests to the API on port 8000. The API documentation is available at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

To serve the built frontend and API from one origin instead, build the frontend with `npm --prefix apps/frontend ci` and `npm --prefix apps/frontend run build`, then start the API. The default `EMPORIO_MUSIC_FRONTEND_DIR=apps/frontend/dist` in `.env.example` points the API to the built files; open [http://127.0.0.1:8000](http://127.0.0.1:8000).

Keep the API bound to loopback and use only fictional demo data; the application has no authentication.

## Run it with a coding agent

Give your coding agent this prompt:

```text
Clone this project from https://github.com/rafaself/atf-ai-engineer-challenge, then set it up and run it locally without Docker. Follow docs/guides/run-without-docker.md. Check for Python 3.12+, uv, Node.js 20.19+ or 22.12+, and npm. Do not overwrite an existing .env file; if it is missing, create it from .env.example. Use the documented host AWS credential setup without printing or exposing secrets. Install project dependencies, prepare the demo data and policy index, then start the API and frontend as documented. Keep the API bound to localhost and use fictional data. If credentials or required tools are missing, stop and tell me what to configure. Report the chat and API docs URLs when it is running.
```
