# Repository Guidelines

## Project Structure & Module Organization
- `app.py`: Flask API + server-side rendering, serves built React assets from `frontend/build` and HTML from `templates/index.html`.
- `templates/` and `static/`: Server-rendered assets (landing page, styling, any future static files).
- `frontend/`: Create React App PWA (React 18) for the client UI; built output is served by Flask in production.
- Platform configs: `.daytona/`, `.devcontainer/`, `docker-compose.yml`, and `Dockerfile` for local or Daytona-based environments.

## Build, Test, and Development Commands
- Python backend: `pip install -r requirements.txt` then `python app.py` (default port 8080). Use `FLASK_ENV=development` if you want auto-reload.
- React frontend: `cd frontend && npm install` then `npm start` for dev, or `npm run build` to emit `frontend/build` for Flask.
- Docker: `docker compose up --build` to run the full stack with the baked frontend.

## Coding Style & Naming Conventions
- Python: 4-space indent, keep functions cohesive in `app.py`; prefer separating helpers into modules if they grow. Aim for Black/PEP8 style (88–100 cols). Use descriptive names for analyzers and indicators.
- JavaScript/React: Functional components, PascalCase for components, camelCase for props/state. Stick to CRA defaults; lint with `npm run test` (includes eslint via react-scripts).
- Templates/CSS: Keep inline styles minimal; prefer extracting shared styles into `static/` if you extend the server-rendered page.

## Testing Guidelines
- No automated tests included; validate API endpoints manually with `curl`/Postman:
  - `POST /api/analyze` with `{"ticker":"AAPL"}`.
  - `GET /api/screen?filter=strong_buys&limit=20`.
  - `GET /api/market-sentiment`.
- Frontend: `npm test` (CRA) for basic sanity; otherwise, manual QA in the browser for scoring flows and PWA install.

## Commit & Pull Request Guidelines
- Commits: concise, sentence-case subjects (e.g., `Add earnings sentiment endpoint`, `Tweak score weights`).
- PRs: describe scope, list endpoints or UI changes, and include screenshots/GIFs for frontend tweaks. Note any new env vars.

## Configuration & Secrets
- Backend env: `ELEVENLABS_API_KEY` (and optional `ELEVENLABS_VOICE_ID`), plus any future API keys. Set them in your shell or compose overrides; do not commit secrets.
- Frontend uses CRA defaults; no env required unless you add APIs (`REACT_APP_*`).
- If using Daytona, keep `.daytona/config.yaml` and `Dockerfile` in sync with dependency changes; rebuild images after Python/Node upgrades.
