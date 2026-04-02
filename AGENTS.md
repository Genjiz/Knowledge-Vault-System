# AGENTS.md

## Project Identity

- Public project name: `Knowledge Vault`
- Suggested GitHub repository slug: `knowledge-vault`
- This repository root is the only project root. Do not reintroduce a nested application root such as `literature-manager/`.

## Read This First

When starting a new task, read documents in this order as needed:

1. `docs/documentation-map.md`
2. `docs/project-overview.md`
3. `docs/development-guide.md`
4. `docs/roadmap.md`
5. `docs/project-log.md`

Use `docs/plans/` for historical designs and implementation plans when the current task touches older areas of the system.

## Documentation Rules

- Every code change must consider whether documentation also needs an update.
- If a change affects project structure, setup, architecture, workflows, naming, or roadmap, update the relevant docs in the same session.
- Record important project-level changes and decisions in `docs/project-log.md`.
- Put new design or implementation plans in `docs/plans/YYYY-MM-DD-<topic>.md`.
- Keep `README.md` public-facing and concise.
- Keep operational and internal knowledge under `docs/`.

## Repository Conventions

- Top-level directories should remain focused: `backend/`, `frontend/`, `docs/`, and a small set of root project files.
- Backend changes should follow the existing layered structure: `models`, `repositories`, `services`, `providers`, `routes`, `runtime`.
- New product features should be integrated into the existing app architecture rather than introduced as separate standalone apps or script entry points.
- The crawler domain stores raw results first, then runs translation, analysis, and export steps on top of those records.
- Independent modules can keep their own task models, routes, and artifact directories when they are conceptually separate from literature management. The `video_notes` domain follows this rule.

## Safety Rules

- Do not commit secrets, especially `backend/gemini_api_key.txt` or `gemini_api_key.txt`.
- Do not commit local runtime data such as `.venv/`, `.crawler-browser-profile/`, `frontend/node_modules/`, or generated artifacts unless explicitly requested.
- Avoid destructive git commands unless the user explicitly asks for them.
- Preserve user changes that are already in the worktree.

## Verification Expectations

- For backend runtime/path changes, run focused Python tests first.
- For frontend-affecting changes, run `npm run build` before closing the task when feasible.
- If verification cannot be run, say so explicitly in the final handoff.
