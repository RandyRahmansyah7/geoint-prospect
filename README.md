# GEOINT Prospect

Intelligence workstation for geospatial discovery and analysis.

This repository currently contains the project scaffold only: desktop shell, frontend,
Python engine package, and CI. No analytical features are implemented yet.

## Layout

```
frontend/    Next.js App Router + TypeScript + Tailwind + shadcn/ui
src-tauri/   Tauri 2 desktop shell (Rust)
engine/      Python analytical engine package
.github/     CI workflow
```

## Prerequisites

- Node.js 22+ and npm
- Python 3.11+
- Rust stable and the [Tauri 2 system dependencies](https://v2.tauri.app/start/prerequisites/)
- Linux (Debian/Ubuntu): `sudo apt install libwebkit2gtk-4.1-dev build-essential curl wget file libxdo-dev libssl-dev libayatana-appindicator3-dev librsvg2-dev`

## Frontend

```bash
npm install
npm run dev        # http://localhost:3000
npm run build      # static export to frontend/out
npm run lint
npm run typecheck
```

## Desktop shell

```bash
npm run desktop:dev     # starts Next dev server and the Tauri window
npm run desktop:build   # bundles the app into src-tauri/target/release/bundle
```

The first Rust build takes several minutes. Tauri runs `npm run dev` and `npm run build`
from the repository root, then loads `frontend/out`.

```bash
cd src-tauri
cargo fmt --check
cargo clippy
```

## Engine

```bash
cd engine
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
ruff check .
ruff format --check .
```

The engine must stay independent of the UI so it can run locally or in a cloud job later.
Add the geospatial dependencies (GeoPandas, Shapely, pyproj, NumPy, SciPy, scikit-learn,
PyArrow) only when a feature needs them.

## Static export constraints

Tauri serves files from disk, so the frontend uses `output: "export"`. Anything that needs a
Node.js server is unavailable: cookies/headers, middleware/proxy, rewrites/redirects, ISR,
draft mode, Server Actions, image optimization with the default loader, and route handlers
that read the request (only statically prerendered `GET` handlers work). Dynamic routes need
`generateStaticParams()`.

Do not add a permanent API server for the engine. Wire local analysis through Tauri commands
or a sidecar when the first feature needs it.

## CI

`.github/workflows/ci.yml` runs frontend lint, typecheck, and build, plus engine lint, format
check, and tests. Cloud analysis jobs are intentionally not part of CI yet.
