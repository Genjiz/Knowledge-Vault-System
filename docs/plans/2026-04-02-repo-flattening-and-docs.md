# Repository Flattening and Documentation Overhaul Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Flatten the repository so the git root is the real project root, rename the project to Knowledge Vault, and replace ad-hoc docs with a durable documentation system for GitHub and future agents.

**Architecture:** Treat the current outer git directory as the permanent project root, move the application directories up one level, then update path-sensitive runtime code, branding, and documentation to match the new layout. Keep historical design/plan documents, but migrate operational knowledge into focused docs that are easy for both humans and agents to scan.

**Tech Stack:** PowerShell, Git, Flask, Vue 3, Vite, Markdown

---

### Task 1: Flatten the repository layout

**Files:**
- Move: `backend/`
- Move: `frontend/`
- Move: `docs/`
- Move: `start.bat`
- Move: `stop.bat`
- Move: `.venv/`
- Move: `.tmp/`
- Move: `.pip-cache/`
- Move: `.crawler-browser-profile/`
- Remove: `literature-manager/` after its contents are moved

**Step 1: Confirm the nested project contents before moving**

Run: `Get-ChildItem -Force .\literature-manager`
Expected: Shows `backend`, `frontend`, `docs`, scripts, and local runtime folders.

**Step 2: Move project contents into the repository root**

Run: PowerShell `Move-Item` commands for each top-level item inside `literature-manager`.
Expected: Root now contains `backend`, `frontend`, `docs`, `start.bat`, and `stop.bat`.

**Step 3: Remove the now-empty nested directory**

Run: `Remove-Item .\literature-manager -Force`
Expected: `literature-manager` no longer exists.

**Step 4: Verify the new top-level layout**

Run: `Get-ChildItem -Force`
Expected: Root contains the application folders directly.

### Task 2: Update path-sensitive runtime behavior with tests first

**Files:**
- Modify: `backend/tests/test_runtime_paths.py`
- Modify: `backend/app/crawler/runtime/paths.py`

**Step 1: Write the failing test**

Add assertions that the workspace root itself contains `backend` and `frontend`, and that the default crawler browser profile path resolves to `workspace_root / ".crawler-browser-profile"`.

**Step 2: Run test to verify it fails**

Run: `& .\.venv\Scripts\python.exe -m unittest backend.tests.test_runtime_paths -v`
Expected: FAIL because the old runtime path logic still expects a nested `literature-manager` directory.

**Step 3: Write minimal implementation**

Update the runtime path helpers so `get_workspace_root()` detects the flattened project root and `get_project_root()` returns that root directly.

**Step 4: Run test to verify it passes**

Run: `& .\.venv\Scripts\python.exe -m unittest backend.tests.test_runtime_paths -v`
Expected: PASS

### Task 3: Update repo metadata, startup scripts, and branding

**Files:**
- Modify: `.gitignore`
- Modify: `backend/config.py`
- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`
- Modify: `frontend/index.html`
- Modify: `frontend/src/App.vue`
- Modify: `start.bat`
- Modify: `stop.bat`

**Step 1: Write the failing test**

Use the runtime path test from Task 2 as the guardrail for the restructuring; no additional automated test is required for pure metadata changes.

**Step 2: Write minimal implementation**

Rename project-facing strings to `Knowledge Vault`, update the frontend package name to `knowledge-vault-frontend`, refresh batch script titles, and rewrite ignore rules so they match the flattened root layout and keep secrets/local caches out of Git.

**Step 3: Run targeted verification**

Run:
- `& .\.venv\Scripts\python.exe -m unittest backend.tests.test_runtime_paths -v`
- `npm run build`

Expected: Tests pass and the frontend builds successfully.

### Task 4: Replace the old project docs with a durable documentation system

**Files:**
- Create: `README.md`
- Create: `AGENTS.md`
- Create: `docs/documentation-map.md`
- Create: `docs/project-overview.md`
- Create: `docs/development-guide.md`
- Create: `docs/roadmap.md`
- Create: `docs/project-log.md`
- Modify: `docs/plans/2026-03-04-crawler-integration-design.md`
- Modify: `docs/plans/2026-03-04-crawler-integration.md`
- Delete: `项目说明文档.md`
- Delete: `启动与环境说明.md`

**Step 1: Draft the new document set**

Write public-facing GitHub docs in `README.md`, operational/agent docs in `AGENTS.md`, and split internal knowledge across the new `docs/` files.

**Step 2: Migrate essential information**

Move project scope, architecture, setup, and workflow guidance out of the two old Chinese top-level docs into the new documentation set.

**Step 3: Normalize historical plan references**

Update obvious stale `literature-manager/` path prefixes in the preserved plan/design docs so future readers are not misled by the old nested structure.

**Step 4: Remove superseded docs**

Delete the two top-level legacy docs once their useful content is absorbed elsewhere.

### Task 5: Final verification and safety review

**Files:**
- Review: `git status --short --branch`

**Step 1: Run targeted checks**

Run:
- `& .\.venv\Scripts\python.exe -m unittest backend.tests.test_runtime_paths -v`
- `npm run build`

Expected: Both commands succeed.

**Step 2: Review the resulting worktree**

Run: `git status --short --branch`
Expected: Shows the intended moves/doc updates without overwriting unrelated user changes.

**Step 3: Summarize follow-up**

Report the new project name, the suggested GitHub repository slug (`knowledge-vault`), the new docs entry points, and any residual items the user should decide later.
