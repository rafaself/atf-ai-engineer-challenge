# Empório da Música frontend

A React + TypeScript + Vite customer-support chat for US-19, US-20, and issue #84, centered on a subtle branded background. It streams messages from FastAPI `/api/chat/stream` and reconciles each committed answer when the server completes the turn.

## Run locally

Use Node.js 20.19+ or 22.12+ and npm.

For the complete packaged application, follow the Docker quick start in the [root README](../../README.md). The commands below run the frontend separately for development.

From `apps/frontend`:

```bash
npm ci
npm run dev
```

The development server binds to `127.0.0.1`. The chat is the main interface, centered on desktop and nearly fullscreen on mobile. There is no storefront, overlay, or minimize control.

For API integration, start the backend on `127.0.0.1:8000` using the setup instructions in the [root README](../../README.md). Vite proxies `/api` requests to that local server. The backend supplies the fixed fictional demo identity; the browser does not send a customer ID. This is demo context, not authentication.

## Checks and production build

```bash
npm run lint
npm run typecheck
npm test
npm run build
npm run preview
```

The chat keeps its transcript and returned session ID in memory. Starting a new conversation clears both and starts a new API session. The backend owns persisted conversation history; a user message shown as pending or failed is not presented as a confirmed completed turn. Requests are not retried automatically. If the connection is lost, the UI reports that completion could not be confirmed because the server may have committed before the response was lost.
