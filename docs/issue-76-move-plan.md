# Issue #76 move plan

Baseline inventory captured before moving files.

## Inventory

- `apps/backend/src/emporio_music_backend` currently combines reusable agent,
  contracts, ports, application, SQLite/provider infrastructure, policy retrieval,
  shared composition and the FastAPI adapter in one distribution.
- `apps/cli` is already a separate terminal application, but imports the backend
  distribution for contracts, repositories and composition.
- `apps/backend/scripts` contains repository evaluation utilities and the policy
  index/benchmark commands. Backend tests also cover both the shared logic and
  the HTTP adapter.
- Root Docker, Compose, Make and documentation commands target `apps/backend`.
  The API resolves frontend assets through the backend package, and
  `paths.py` derives the repository root from its installed source location.
- The AI path is already divided into cohesive modules for model settings,
  tools, persona, output checks, corpus parsing, query expansion, embeddings,
  indexing and shared composition. `agent/factory.py` also owns execution error
  translation, while `agent/policies.py` combines the retrieval service with its
  Pydantic AI tool wrapper.

## Move and split plan

1. Move transport-neutral code into one `emporio-music` distribution at
   `packages/emporio_music`; place domain contracts under `domain/` and policy
   corpus, retrieval rules and local search under `policies/`.
2. Move HTTP routes, schemas, error mapping and static UI serving into
   `apps/api`; retain the interactive terminal application in `apps/cli`.
   Both apps depend on the shared package. Neither app imports the other.
3. Keep the current focused AI modules. Split only the provider-independent
   agent executor from provider/model construction, and split local policy
   search from its Pydantic AI tool wrapper. Keep corpus normalization and
   preparation together because they form one source-specific pipeline.
4. Move repository evaluation/indexing utilities to root `scripts/`, the shared
   regression suite to root `tests/`, and keep CLI-specific tests in
   `apps/cli/tests`.
5. Replace source-tree-derived paths with explicit
   `EMPORIO_MUSIC_DATA_DIR` and API frontend asset configuration. Preserve the
   local root `data/` layout and Docker `/app/data` persistent volume; leave
   supplied data and frozen inference captures unchanged.
6. Update project metadata/locks, Docker and local commands, imports, tests,
   examples and architecture/setup documentation. Add no production dependency.

## Completed result

- Reusable code now ships as `emporio-music` from `packages/emporio_music`;
  FastAPI lives in `apps/api`, and the CLI remains in `apps/cli`.
- Agent execution/provider construction and local policy search/the AI tool
  wrapper have separate modules. HTTP and CLI depend on the shared package only.
- Data and frontend paths use `EMPORIO_MUSIC_DATA_DIR` and
  `EMPORIO_MUSIC_FRONTEND_DIR`. Supplied data and frozen JSON captures were left
  unchanged.
- The workspace lock retains all 124 third-party package versions; no
  production dependency was added. See the Issue #76 record in
  [validation](validation.md) for commands, results and the time-sensitive test
  limitation.
