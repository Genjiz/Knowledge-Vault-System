# Crawler Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Rebuild the standalone crawler project as a first-class "采集中心" module inside `Knowledge Vault`, using Flask APIs, SQLAlchemy models, Vue pages, SQLite persistence, and JSON/Markdown artifacts.

**Architecture:** Add a dedicated crawler subdomain in the Flask backend for tasks, raw issues, raw papers, analysis, and artifact export. Replace the Streamlit UI with Vue pages that operate entirely through APIs, while preserving JSON and Markdown as generated artifacts rather than primary storage.

**Tech Stack:** Flask, SQLAlchemy, SQLite, Vue 3, Vite, Vue Router, Pinia, Element Plus, existing crawler Python logic refactored into providers/services.

---

### Task 1: Document current crawler inputs and outputs

**Files:**
- Modify: `docs/plans/2026-03-04-crawler-integration-design.md`
- Reference: `爬虫/国内期刊爬虫/`
- Reference: `爬虫/国外期刊爬虫/`
- Reference: `爬虫/pages/`

**Step 1: Write the investigation checklist**

Add a short appendix section listing:

- which crawler scripts are entry points
- what parameters they accept
- what structured fields they emit
- what files they currently write

**Step 2: Verify each source**

Run targeted reads with `rg` and `Get-Content` against the domestic and foreign crawler modules.
Expected: exact mapping for source parameters and output fields.

**Step 3: Update the appendix with confirmed fields**

Write only fields that are truly required for `raw_issue`, `raw_paper`, and analysis artifacts.

**Step 4: Re-read the design doc**

Run: `Get-Content -Raw docs/plans/2026-03-04-crawler-integration-design.md`
Expected: appendix is present and consistent with the plan.

**Step 5: Commit**

```bash
git add docs/plans/2026-03-04-crawler-integration-design.md
git commit -m "docs: refine crawler integration design inputs"
```

### Task 2: Add crawler domain models

**Files:**
- Create: `backend/app/crawler/__init__.py`
- Create: `backend/app/crawler/models/__init__.py`
- Create: `backend/app/crawler/models/crawl_task.py`
- Create: `backend/app/crawler/models/crawl_task_log.py`
- Create: `backend/app/crawler/models/raw_issue.py`
- Create: `backend/app/crawler/models/raw_paper.py`
- Create: `backend/app/crawler/models/raw_issue_analysis.py`
- Create: `backend/app/crawler/models/llm_run.py`
- Modify: `backend/app/models/__init__.py`

**Step 1: Write the failing model import check**

Add a lightweight backend test or import script that imports all new models from `app.models`.

**Step 2: Run the import check to verify it fails**

Run: import check command for `app.models`
Expected: FAIL because crawler models do not exist.

**Step 3: Implement the new SQLAlchemy models**

Include:

- primary keys
- timestamps
- task statuses
- unique constraint on raw issue identity
- relationships from issue to papers and analysis

**Step 4: Run the import check again**

Expected: PASS and database tables can be created by app startup.

**Step 5: Commit**

```bash
git add backend/app/crawler backend/app/models/__init__.py
git commit -m "feat: add crawler domain models"
```

### Task 3: Add crawler repositories and service skeletons

**Files:**
- Create: `backend/app/crawler/repositories/__init__.py`
- Create: `backend/app/crawler/repositories/task_repo.py`
- Create: `backend/app/crawler/repositories/raw_issue_repo.py`
- Create: `backend/app/crawler/repositories/raw_paper_repo.py`
- Create: `backend/app/crawler/repositories/analysis_repo.py`
- Create: `backend/app/crawler/services/__init__.py`
- Create: `backend/app/crawler/services/task_service.py`
- Create: `backend/app/crawler/services/ingestion_service.py`
- Create: `backend/app/crawler/services/translation_service.py`
- Create: `backend/app/crawler/services/analysis_service.py`

**Step 1: Write the failing repository/service smoke test**

Test that a task can be created and a raw issue can be persisted through service APIs.

**Step 2: Run the smoke test to verify it fails**

Expected: FAIL because repositories and services do not exist.

**Step 3: Implement minimal repositories and service orchestration**

Keep the service layer narrow:

- create task
- append logs
- create or update raw issue
- replace raw papers for one issue
- save analysis

**Step 4: Run the smoke test again**

Expected: PASS for local SQLite.

**Step 5: Commit**

```bash
git add backend/app/crawler/repositories backend/app/crawler/services
git commit -m "feat: add crawler repositories and services"
```

### Task 4: Add standardized artifact exporters

**Files:**
- Create: `backend/app/crawler/services/artifact_service.py`
- Create: `backend/artifacts/.gitkeep`
- Modify: `backend/config.py`

**Step 1: Write the failing artifact export test**

Test that saving a raw issue produces a JSON artifact path and saving analysis produces a Markdown artifact path.

**Step 2: Run the artifact export test to verify it fails**

Expected: FAIL because no artifact exporter exists.

**Step 3: Implement artifact path generation and file writing**

Generate:

- `backend/artifacts/raw-json/<source>/<journal>/<year>/<issue>.json`
- `backend/artifacts/analysis-md/<source>/<journal>/<year>/<issue>.md`

**Step 4: Run the artifact export test again**

Expected: PASS and files are present in the expected directories.

**Step 5: Commit**

```bash
git add backend/app/crawler/services/artifact_service.py backend/config.py backend/artifacts/.gitkeep
git commit -m "feat: add crawler artifact exporters"
```

### Task 5: Refactor domestic crawler into provider interface

**Files:**
- Create: `backend/app/crawler/providers/__init__.py`
- Create: `backend/app/crawler/providers/base.py`
- Create: `backend/app/crawler/providers/domestic_provider.py`
- Reference: `爬虫/国内期刊爬虫/`

**Step 1: Write the failing provider contract test**

Test that a domestic provider returns a structured issue payload with paper entries.

**Step 2: Run the provider contract test to verify it fails**

Expected: FAIL because the provider does not exist.

**Step 3: Implement the domestic provider**

Refactor reusable crawler logic into a Python-callable interface:

- accept source parameters as function/class inputs
- return structured dictionaries or dataclasses
- do not require CLI or Streamlit

**Step 4: Run the provider contract test again**

Expected: PASS for a controlled fixture or mocked source.

**Step 5: Commit**

```bash
git add backend/app/crawler/providers
git commit -m "feat: add domestic crawler provider"
```

### Task 6: Refactor foreign crawler into provider interface

**Files:**
- Modify: `backend/app/crawler/providers/__init__.py`
- Create: `backend/app/crawler/providers/foreign_provider.py`
- Reference: `爬虫/国外期刊爬虫/`

**Step 1: Write the failing foreign provider contract test**

Test that a foreign provider returns a structured issue payload and surfaces browser/environment errors clearly.

**Step 2: Run the provider contract test to verify it fails**

Expected: FAIL because the provider does not exist.

**Step 3: Implement the foreign provider**

Requirements:

- direct Python-callable interface
- no Streamlit dependency
- environment validation for browser automation
- structured exceptions for task logging

**Step 4: Run the provider contract test again**

Expected: PASS for fixtures/mocks and deterministic failures.

**Step 5: Commit**

```bash
git add backend/app/crawler/providers
git commit -m "feat: add foreign crawler provider"
```

### Task 7: Wire ingestion workflow end-to-end

**Files:**
- Modify: `backend/app/crawler/services/ingestion_service.py`
- Modify: `backend/app/crawler/services/task_service.py`
- Test: `backend/tests/crawler/test_ingestion_service.py`

**Step 1: Write the failing ingestion workflow test**

Test that starting ingestion:

- creates a task
- calls the provider
- persists raw issue and papers
- writes JSON artifact
- completes the task

**Step 2: Run the workflow test to verify it fails**

Expected: FAIL because the orchestration is incomplete.

**Step 3: Implement minimal ingestion orchestration**

Support:

- source dispatch
- task lifecycle updates
- log writes
- upsert or replace issue data safely

**Step 4: Run the workflow test again**

Expected: PASS.

**Step 5: Commit**

```bash
git add backend/app/crawler/services backend/tests/crawler/test_ingestion_service.py
git commit -m "feat: wire crawler ingestion workflow"
```

### Task 8: Add translation provider and service

**Files:**
- Create: `backend/app/crawler/providers/translation_provider.py`
- Modify: `backend/app/crawler/services/translation_service.py`
- Test: `backend/tests/crawler/test_translation_service.py`
- Reference: `爬虫/国外期刊爬虫/3.translator.py`

**Step 1: Write the failing translation service test**

Test that translating an issue updates translated fields and regenerates the JSON artifact.

**Step 2: Run the translation test to verify it fails**

Expected: FAIL because translation service is incomplete.

**Step 3: Implement minimal translation workflow**

Requirements:

- issue-level translation
- optional single-paper translation path
- clear per-paper status updates

**Step 4: Run the translation test again**

Expected: PASS.

**Step 5: Commit**

```bash
git add backend/app/crawler/providers/translation_provider.py backend/app/crawler/services/translation_service.py backend/tests/crawler/test_translation_service.py
git commit -m "feat: add crawler translation workflow"
```

### Task 9: Add analysis provider and service

**Files:**
- Create: `backend/app/crawler/providers/analysis_provider.py`
- Modify: `backend/app/crawler/services/analysis_service.py`
- Test: `backend/tests/crawler/test_analysis_service.py`
- Reference: `爬虫/journal_paper_analyzer.py`
- Reference: `爬虫/pages/3_📊_Analysis.py`

**Step 1: Write the failing analysis service test**

Test that analyzing an issue saves `raw_issue_analysis`, writes Markdown, and records the task outcome.

**Step 2: Run the analysis test to verify it fails**

Expected: FAIL because the analysis workflow is incomplete.

**Step 3: Implement minimal analysis workflow**

Requirements:

- build prompt from persisted raw papers
- save markdown content in database
- export Markdown artifact

**Step 4: Run the analysis test again**

Expected: PASS.

**Step 5: Commit**

```bash
git add backend/app/crawler/providers/analysis_provider.py backend/app/crawler/services/analysis_service.py backend/tests/crawler/test_analysis_service.py
git commit -m "feat: add crawler analysis workflow"
```

### Task 10: Add crawler API routes

**Files:**
- Create: `backend/app/crawler/routes/__init__.py`
- Create: `backend/app/crawler/routes/task.py`
- Create: `backend/app/crawler/routes/raw_issue.py`
- Create: `backend/app/crawler/routes/raw_paper.py`
- Create: `backend/app/crawler/schemas/task_schema.py`
- Create: `backend/app/crawler/schemas/raw_issue_schema.py`
- Create: `backend/app/crawler/schemas/raw_paper_schema.py`
- Modify: `backend/app/routes/__init__.py`

**Step 1: Write the failing API tests**

Cover:

- create ingestion task
- list raw issues
- fetch one issue with papers
- trigger translation
- trigger analysis

**Step 2: Run the API tests to verify they fail**

Expected: FAIL because routes do not exist.

**Step 3: Implement the API routes**

Use consistent response wrappers with the existing backend style.

**Step 4: Run the API tests again**

Expected: PASS.

**Step 5: Commit**

```bash
git add backend/app/crawler/routes backend/app/crawler/schemas backend/app/routes/__init__.py
git commit -m "feat: add crawler api routes"
```

### Task 11: Add frontend API clients and store

**Files:**
- Create: `frontend/src/api/crawlerTask.js`
- Create: `frontend/src/api/rawIssue.js`
- Create: `frontend/src/api/rawPaper.js`
- Create: `frontend/src/stores/crawler.js`

**Step 1: Write the failing frontend store smoke check**

Test that the store exposes actions for tasks, issue lists, translation, and analysis.

**Step 2: Run the smoke check to verify it fails**

Expected: FAIL because the clients and store do not exist.

**Step 3: Implement API client wrappers and Pinia store**

Keep naming aligned with existing frontend API modules.

**Step 4: Run the smoke check again**

Expected: PASS.

**Step 5: Commit**

```bash
git add frontend/src/api frontend/src/stores/crawler.js
git commit -m "feat: add crawler frontend data layer"
```

### Task 12: Add routes and shell navigation for 采集中心

**Files:**
- Modify: `frontend/src/router/index.js`
- Modify: `frontend/src/App.vue`

**Step 1: Write the failing route/navigation check**

Verify the router contains pages for tasks, raw issues, and analysis, and the shell navigation links to them.

**Step 2: Run the check to verify it fails**

Expected: FAIL because the routes are missing.

**Step 3: Implement route registration and nav changes**

Add a dedicated top-level “采集中心” navigation group.

**Step 4: Run the route/navigation check again**

Expected: PASS.

**Step 5: Commit**

```bash
git add frontend/src/router/index.js frontend/src/App.vue
git commit -m "feat: add crawler navigation shell"
```

### Task 13: Build the 采集任务 page

**Files:**
- Create: `frontend/src/views/CrawlTaskCenter.vue`
- Test: `frontend/src/views/__tests__/CrawlTaskCenter.spec.js`

**Step 1: Write the failing UI test**

Test for:

- source selector
- journal/year/issue inputs
- submit button loading state
- task list rendering
- log panel rendering

**Step 2: Run the UI test to verify it fails**

Expected: FAIL because the view does not exist.

**Step 3: Implement the page**

Requirements:

- efficient task form
- visible async states
- readable recent activity area
- no direct script calls from UI

**Step 4: Run the UI test again**

Expected: PASS.

**Step 5: Commit**

```bash
git add frontend/src/views/CrawlTaskCenter.vue frontend/src/views/__tests__/CrawlTaskCenter.spec.js
git commit -m "feat: add crawl task center page"
```

### Task 14: Build the raw issue list and detail pages

**Files:**
- Create: `frontend/src/views/RawIssueList.vue`
- Create: `frontend/src/views/RawIssueDetail.vue`
- Create: `frontend/src/components/crawler/RawPaperDrawer.vue`
- Test: `frontend/src/views/__tests__/RawIssueList.spec.js`
- Test: `frontend/src/views/__tests__/RawIssueDetail.spec.js`

**Step 1: Write the failing UI tests**

Cover:

- filters
- issue table
- detail metadata
- paper list
- single-paper action entry

**Step 2: Run the UI tests to verify they fail**

Expected: FAIL because the pages do not exist.

**Step 3: Implement the pages and drawer**

Requirements:

- issue-first browsing
- efficient filters
- strong detail hierarchy
- visible artifact links

**Step 4: Run the UI tests again**

Expected: PASS.

**Step 5: Commit**

```bash
git add frontend/src/views/RawIssueList.vue frontend/src/views/RawIssueDetail.vue frontend/src/components/crawler/RawPaperDrawer.vue frontend/src/views/__tests__/RawIssueList.spec.js frontend/src/views/__tests__/RawIssueDetail.spec.js
git commit -m "feat: add raw issue browsing pages"
```

### Task 15: Build the analysis page

**Files:**
- Create: `frontend/src/views/RawIssueAnalysis.vue`
- Test: `frontend/src/views/__tests__/RawIssueAnalysis.spec.js`

**Step 1: Write the failing UI test**

Test for:

- analysis summary area
- generate/regenerate actions
- markdown content display
- download entry

**Step 2: Run the UI test to verify it fails**

Expected: FAIL because the page does not exist.

**Step 3: Implement the page**

Requirements:

- strong reading layout
- clear action states
- graceful empty state before analysis exists

**Step 4: Run the UI test again**

Expected: PASS.

**Step 5: Commit**

```bash
git add frontend/src/views/RawIssueAnalysis.vue frontend/src/views/__tests__/RawIssueAnalysis.spec.js
git commit -m "feat: add raw issue analysis page"
```

### Task 16: Apply the refined visual system

**Files:**
- Modify: `frontend/src/style.css`
- Modify: `frontend/src/App.vue`
- Modify: `frontend/src/views/Dashboard.vue`
- Modify: `frontend/src/views/CrawlTaskCenter.vue`
- Modify: `frontend/src/views/RawIssueList.vue`
- Modify: `frontend/src/views/RawIssueDetail.vue`
- Modify: `frontend/src/views/RawIssueAnalysis.vue`

**Step 1: Write the visual acceptance checklist**

List required outcomes:

- magazine-tech visual system
- improved typography
- layered backgrounds
- accessible contrast
- no emoji icons
- responsive layouts

**Step 2: Run manual visual verification**

Run the frontend locally and inspect at 375px, 768px, 1024px, and 1440px.
Expected: note all violations before implementing.

**Step 3: Implement the design system and page styling**

Requirements:

- new design tokens
- refined shell layout
- strong page hierarchy
- restrained motion

**Step 4: Run manual visual verification again**

Expected: layouts remain responsive, readable, and consistent.

**Step 5: Commit**

```bash
git add frontend/src/style.css frontend/src/App.vue frontend/src/views/Dashboard.vue frontend/src/views/CrawlTaskCenter.vue frontend/src/views/RawIssueList.vue frontend/src/views/RawIssueDetail.vue frontend/src/views/RawIssueAnalysis.vue
git commit -m "feat: apply crawler visual system"
```

### Task 17: Update startup and environment documentation

**Files:**
- Modify: `启动与环境说明.md`
- Modify: `项目说明文档.md`

**Step 1: Write the failing doc checklist**

List missing items:

- crawler module startup behavior
- artifact directories
- browser requirements for foreign sources
- Gemini requirements

**Step 2: Review the current docs and verify gaps**

Expected: the new crawler architecture is not documented yet.

**Step 3: Update the docs**

Explain:

- unified architecture
- where data is stored
- where artifacts are stored
- what dependencies are required

**Step 4: Re-read the docs**

Expected: instructions match the implemented system.

**Step 5: Commit**

```bash
git add 启动与环境说明.md 项目说明文档.md
git commit -m "docs: update unified crawler architecture docs"
```

### Task 18: Verify end-to-end behavior

**Files:**
- Test: `backend/tests/crawler/`
- Test: `frontend/src/views/__tests__/`

**Step 1: Run backend crawler tests**

Run: backend test command for crawler domain
Expected: PASS.

**Step 2: Run frontend tests**

Run: frontend test command for crawler-related views/stores
Expected: PASS.

**Step 3: Run the app manually**

Verify:

- task creation works
- raw issues appear
- translation updates fields
- analysis writes markdown
- JSON/MD downloads are reachable

**Step 4: Fix any failures and rerun**

Expected: all targeted checks pass.

**Step 5: Commit**

```bash
git add .
git commit -m "test: verify crawler integration end to end"
```

