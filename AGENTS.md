# Repository Guidelines

## Project Structure & Module Organization
- `backend/`: Django REST API; settings in `backend/settings/` with `development.py` and `production.py`; business apps in `catalog/`, `orders/`, `users/`, `integrations/`, shared utilities in `common/`.
- `frontend/`: Taro + React mini-program; entry config `src/app.config.ts`; UI pages in `src/pages/*`, shared components in `src/components/`, API helpers in `src/services/`, types in `src/types/`.
- `merchant/`: React + Ant Design Pro admin; routes and pages in `src/`, API calls via `axios`; Vite config in `vite.config.ts`.
- `docs/` and top-level `*.md`: reference guides; `deploy/` contains compose files and ops scripts.
- `docs/plan/`: active execution plans only (one independent task per file, naming `YYYY-MM-DD-short-title.md`); completed, canceled, or superseded plans should be deleted after their final behavior is reflected in long-lived docs. `docs/plan/archive/` is only for historical plans with real review value. Read [docs/plan/README.md](docs/plan/README.md) before starting sizable features or refactors.

## Build, Test, and Development Commands
- Backend setup: `uv sync` (preferred) or `python -m venv .venv && pip install -r requirements.txt` to install deps.
- Backend runtime: the backend is normally run in Docker. Do not run bare host commands like `python manage.py ...` or `uv run python manage.py ...` from Windows PowerShell unless the user explicitly asks for a local-venv run; they can trigger the Windows Python app alias popup.
- Backend run: `docker compose -f docker/docker-compose.dev.yaml up -d backend` (default http://localhost:8000; starts `db` as needed).
- Backend management commands/tests: `docker compose -f docker/docker-compose.dev.yaml exec backend .venv/bin/python manage.py <command>`; for tests use `docker compose -f docker/docker-compose.dev.yaml exec backend .venv/bin/python manage.py test`.
- Frontend install: `cd frontend && npm install`.
- Frontend dev build: `npm run dev:weapp` (watch WeChat mini-program); other targets available (`dev:alipay`, `dev:h5`, etc.).
- Frontend production build: `npm run build:weapp` (or platform-specific build command).
- Merchant install: `cd merchant && npm install`.
- Merchant run/build: `npm run dev` for local Vite dev server, `npm run build` for production assets; `npm run preview` to smoke-test the bundle.

## Coding Style & Naming Conventions
- Python: follow Django/DRF patterns; prefer readable services; keep settings per env under `backend/settings/`. Use 4-space indentation and type hints where practical.
- JavaScript/TypeScript: Taro + React with TS for frontend; React + Ant Design Pro for merchant. Keep page directories kebab-case (e.g., `product-detail`), components PascalCase, helpers camelCase.
- Linting/formatting: frontend uses ESLint (`eslint-config-taro`) and Stylelint; apply equivalent ESLint/TypeScript style in merchant. Commit messages follow Conventional Commits (see `commitlint.config.mjs`).

## Testing Guidelines
- Backend: place tests alongside apps (e.g., `backend/integrations/test_*.py`); name after behavior (`test_ylh_callback.py`). Use factories/fixtures to isolate business rules; integration tests should hit DRF views via APIClient.
- Frontend/merchant: automated tests are minimal; when adding, colocate near code (`__tests__/` or `*.test.tsx`) and cover page logic, service utilities, and API adapters. Smoke-test key flows (auth, catalog, orders) after changes.

## Documentation Sync Rules
- Treat `docs/` as part of the deliverable, not as an optional follow-up. When code changes alter behavior, API routes, payload fields, permissions, data models, user flows, pages, menus, env vars, deployment steps, or operational scripts, update the relevant docs in the same task before final verification.
- Use this mapping by default:
  - Backend models, serializers, viewsets, URLs, permissions, pricing/business rules, migrations: update `docs/backend.md`, `docs/backend/backend.md`, and when endpoints change, `docs/api/api.md`.
  - Mini-program pages, services, routes, request/response assumptions, visible user flows: update `docs/frontend.md` and `docs/frontend/frontend.md`.
  - Merchant admin routes, menu items, permissions, service APIs, operational workflows: update `docs/merchant.md` and `docs/merchant/merchant.md`.
  - Deployment, Docker, Nginx, env vars, build/runtime commands: update `docs/deployment.md` and `docs/deployment/deployment.md`.
  - New or multi-step features/refactors: add or update the matching `docs/plan/YYYY-MM-DD-short-title.md` only while the work is active; after completion, move final behavior into long-lived docs and delete the plan unless it has historical review value. Update `docs/README.md` or `docs/plan/README.md` when document indexes or active plans change.
- Before finishing a task, scan the touched code paths against `docs/` with `rg` and update stale references such as old endpoints, removed models, renamed pages, permission changes, or changed status values.
- In the final response, mention which docs were updated. If no docs needed changes, say why (for example, test-only or internal refactor with no behavior/API/UI/config change).

## Commit & Pull Request Guidelines
- Commits: use Conventional Commit prefixes (`feat`, `fix`, `chore`, `docs`, etc.) and keep messages scoped (e.g., `feat(orders): add cancel flow`).
- PRs: include summary, key commands run, and screenshots for UI changes (mini-program or merchant views). Link issues/tasks and note migrations, env vars, or data scripts required for rollout.
- Keep diffs small and self-contained; update docs/config when adding new endpoints, pages, or env settings.
- Planning: for new epics or multi-phase work, add or update a plan under `docs/plan/` (see `docs/plan/README.md`); remove the plan after implementation, required tests, and documentation sync are done, unless it should be kept in `docs/plan/archive/` for review history.

### Confirm before commit (agents and automation)
- Before running `git add` / `git commit`, show the user: current branch, `git status`, `git diff --stat` (or an equivalent summary of what would be staged), paths to be committed, and the proposed commit message.
- Run the commit only after the user explicitly confirms. If the user already asked to commit in the same message *after* review (e.g. “看一下 diff 然后提交”), treat that as confirmation once the preview has been shown.

## Environment & Security Notes
- Secrets: load via env vars; never commit keys or tokens. Local dev may use `.env` loaded by settings; production uses `env_config.py` to map required vars.
- Data safety: avoid running destructive scripts against shared databases; prefer local SQLite for backend dev and mock services for third-party integrations.
