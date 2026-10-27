# GEOINT Prospect

Intelligence workstation for geospatial discovery and analysis.

This repository currently contains the project scaffold only: desktop shell, frontend,
Python engine package, and CI. No analytical features are implemented yet.

## Layout

```
src/app/        Next.js App Router routes (TypeScript)
src/components/ layout, workspace chrome, and shadcn/ui components
src/lib/        shared frontend helpers
src-tauri/      Tauri 2 desktop shell (Rust)
engine/         Python analytical engine package (geoint_prospect)
database/       database schemas and migrations
data/           local data manifests and schemas (contents ignored)
configs/        sources, regions, and analysis configuration
.github/        CI workflow
```

Add `src/features/`, `src/hooks/`, `src/types/`, and `src/config/` when the first feature needs
them; they are conventions, not directories that must exist empty.

## Prerequisites

- Node.js 22+ and npm
- Python 3.11+
- Rust stable and the [Tauri 2 system dependencies](https://v2.tauri.app/start/prerequisites/)
- Linux (Debian/Ubuntu): `sudo apt install libwebkit2gtk-4.1-dev build-essential curl wget file libxdo-dev libssl-dev libayatana-appindicator3-dev librsvg2-dev`

## Frontend

```bash
npm install
npm run dev        # http://localhost:3000
npm run build      # static export to out/
npm run lint
npm run typecheck
```

## Desktop shell

```bash
npm run desktop:dev     # starts Next dev server and the Tauri window
npm run desktop:build   # bundles the app into src-tauri/target/release/bundle
```

The first Rust build takes several minutes. Tauri runs `npm run dev` and `npm run build`
from the repository root, then loads `out/`.

### "Connection terminated unexpectedly" in the window

That WebKit error page means the window was pointed at `http://localhost:3000` while nothing was
listening there. Only dev-mode windows do this — a window built with `desktop:build` serves the
embedded `out/` and needs no server.

- Recovery: start `npm run desktop:dev` again, then reload the open window (right-click → Reload)
  or close it. Keep that terminal running.
- Do not launch `src-tauri/target/debug/geoint-prospect` directly, and do not run `cargo run` in
  `src-tauri`: after `tauri dev` those are dev binaries that expect the dev server.
- Want a standalone window with no server? `npm run desktop:build -- --debug --no-bundle`, then run
  `src-tauri/target/debug/geoint-prospect`.

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

The import package is `geoint_prospect`. The engine must stay independent of the UI so it can
run locally or in a cloud job later. Add the geospatial dependencies (GeoPandas, Shapely,
pyproj, NumPy, SciPy, scikit-learn, PyArrow) only when a feature needs them.

## Database, data, and configs

`database/` holds schemas and migrations only; no database technology is chosen yet. `data/`
holds manifests and schemas for local datasets — everything inside it is git-ignored except the
tracked skeleton. `configs/` holds source, region, and analysis configuration. None of these
directories may contain credentials or private datasets.

## Static export constraints

Tauri serves files from disk, so the frontend uses `output: "export"`. Anything that needs a
Node.js server is unavailable: cookies/headers, middleware/proxy, rewrites/redirects, ISR,
draft mode, Server Actions, image optimization with the default loader, and route handlers
that read the request (only statically prerendered `GET` handlers work). Dynamic routes need
`generateStaticParams()`.

Do not add a permanent API server for the engine. Wire local analysis through Tauri commands
or a sidecar when the first feature needs it.

## CI

`.github/workflows/ci.yml` runs frontend lint, typecheck, and build, engine lint, format check,
and tests, plus `cargo fmt --check` and `cargo clippy` for the desktop shell (which needs the
static export first, since Tauri embeds it). Cloud analysis jobs are intentionally not part of
CI yet.
