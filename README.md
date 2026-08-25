# Lions Roster Game

A simple React game for learning the current Detroit Lions roster by face. The
Python roster updater produces the static CSV and headshot assets consumed by
the frontend; no backend is required to play.

## Update the roster

From the repository root, install the Python dependencies if needed:

```bash
pip install pandas requests beautifulsoup4
```

Then run:

```bash
python scripts/update_roster.py
```

The updater writes the live game assets to `web/public/data/active_roster.csv`
and `web/public/headshots/`. Historical snapshots and roster changes remain in
`lions_roster_data/`.

## Run the frontend

```bash
cd web
npm install
npm run dev
```

Open the local URL printed by Vite.

## Production build

```bash
cd web
npm install
npm run build
```

The static production output is written to `web/dist/`.
