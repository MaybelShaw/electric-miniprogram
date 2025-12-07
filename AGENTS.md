# Repository Guidelines

## Project Structure & Module Organization
- `backend/`: Django REST API; settings in `backend/settings/` with `development.py` and `production.py`; business apps in `catalog/`, `orders/`, `users/`, `integrations/`, shared utilities in `common/`.
- `frontend/`: Taro + React mini-program; entry config `src/app.config.ts`; UI pages in `src/pages/*`, shared components in `src/components/`, API helpers in `src/services/`, types in `src/types/`.
- `merchant/`: React + Ant Design Pro admin; routes and pages in `src/`, API calls via `axios`; Vite config in `vite.config.ts`.
- `docs/` and top-level `*.md`: reference guides; `deploy/` contains compose files and ops scripts.

## Build, Test, and Development Commands
- Backend setup: `uv sync` (preferred) or `python -m venv .venv && pip install -r requirements.txt` to install deps.
- Backend run: `python manage.py migrate` then `python manage.py runserver` (default http://localhost:8000).
- Backend tests: `python manage.py test` (Django test runner; keep DB migrations current).
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

## Commit & Pull Request Guidelines
- Commits: use Conventional Commit prefixes (`feat`, `fix`, `chore`, `docs`, etc.) and keep messages scoped (e.g., `feat(orders): add cancel flow`).
- PRs: include summary, key commands run, and screenshots for UI changes (mini-program or merchant views). Link issues/tasks and note migrations, env vars, or data scripts required for rollout.
- Keep diffs small and self-contained; update docs/config when adding new endpoints, pages, or env settings.

## Environment & Security Notes
- Secrets: load via env vars; never commit keys or tokens. Local dev may use `.env` loaded by settings; production uses `env_config.py` to map required vars.
- Data safety: avoid running destructive scripts against shared databases; prefer local SQLite for backend dev and mock services for third-party integrations.
