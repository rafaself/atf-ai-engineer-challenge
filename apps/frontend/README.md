# Empório da Música frontend demo

A standalone React + TypeScript + Vite customer-support chat for US-19, centered on a subtle branded background. Chat replies are deterministic and do not call the backend, AWS, or an LLM provider.

## Run locally

Use Node.js 20.19+ or 22.12+ and npm.

From `apps/frontend`:

```bash
npm ci
npm run dev
```

The development server binds to `127.0.0.1`. The chat is the main interface, centered on desktop and nearly fullscreen on mobile. There is no storefront, overlay, or minimize control.

## Checks and production build

```bash
npm run lint
npm run typecheck
npm run build
npm run preview
```

The chat supports a small set of scripted replies and simple keyword matching. Enter `erro` to display the predictable mock error and retry control. Starting a new conversation clears the in-memory transcript. US-20 replaces the mock client with the existing HTTP API integration.
