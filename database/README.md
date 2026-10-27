# Database assets

Schema definitions and migrations for GEOINT Prospect live here, separate from the UI and the
Python engine.

- `schemas/` — table, index, and reference definitions in whatever form the chosen technology uses.
- `migrations/` — forward-only migration files, ordered by name.

No database server or technology is selected yet. Do not add a server, connection strings,
credentials, or data dumps here; requirements decide the technology first. Local datasets belong
in `data/` (ignored by git), not in this directory.
