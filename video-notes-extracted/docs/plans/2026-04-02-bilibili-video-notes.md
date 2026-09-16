# Bilibili Video Notes Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build an independent Bilibili video-to-note module that runs `yt-dlp -> whisper -> Gemini` as a background task and stores both intermediate artifacts and the final Markdown note inside the project.

**Architecture:** Add a new `video_notes` backend subdomain with its own models, repositories, services, runtime helpers, and routes. Expose the module in the Vue frontend through a dedicated home page, task list, and task detail page, while persisting large artifacts as files under `backend/artifacts/video-notes/<task_id>/`.

**Tech Stack:** Flask, SQLAlchemy, SQLite, Python subprocess integration, Vue 3, Vite, Pinia, Element Plus, Gemini

---

### Task 1: Bootstrap the backend domain and database tables

**Files:**
- Create: `backend/app/video_notes/__init__.py`
- Create: `backend/app/video_notes/models/__init__.py`
- Create: `backend/app/video_notes/models/video_note_task.py`
- Create: `backend/app/video_notes/models/video_note_task_log.py`
- Test: `backend/tests/test_video_note_models.py`
- Modify: `backend/app/__init__.py`

**Step 1: Write the failing test**

```python
class VideoNoteModelTestCase(unittest.TestCase):
    def test_create_app_creates_video_note_tables(self):
        app = create_app("testing")
        with app.app_context():
            table_names = {
                row[0]
                for row in db.session.execute(
                    text("SELECT name FROM sqlite_master WHERE type='table'")
                ).fetchall()
            }
        self.assertIn("video_note_task", table_names)
        self.assertIn("video_note_task_log", table_names)
```

**Step 2: Run test to verify it fails**

Run: `& .\.venv\Scripts\python.exe -m unittest backend.tests.test_video_note_models -v`
Expected: FAIL because the tables and model imports do not exist yet.

**Step 3: Write minimal implementation**

- Define `VideoNoteTask` with the approved fields:
  - `source_url`, `platform`, `bvid`, `video_title`
  - `status`, `current_step`, `progress_message`, `error_message`
  - `whisper_model`, `language`, `device`, `compute_type`, `use_vad`
  - `audio_path`, `transcript_path`, `note_path`, `metadata_path`
  - `started_at`, `finished_at`
- Define `VideoNoteTaskLog` with `task_id`, `level`, `message`
- Register the models in `backend/app/__init__.py` so `db.create_all()` sees them

**Step 4: Run test to verify it passes**

Run: `& .\.venv\Scripts\python.exe -m unittest backend.tests.test_video_note_models -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/video_notes backend/app/__init__.py backend/tests/test_video_note_models.py
git commit -m "feat: add video note task models"
```

### Task 2: Add runtime helpers for URL parsing, task directories, and the whisper CLI bridge

**Files:**
- Create: `backend/app/video_notes/runtime/__init__.py`
- Create: `backend/app/video_notes/runtime/bilibili.py`
- Create: `backend/app/video_notes/runtime/paths.py`
- Create: `backend/app/video_notes/runtime/transcribe_audio.py`
- Test: `backend/tests/test_video_note_runtime.py`

**Step 1: Write the failing test**

```python
class VideoNoteRuntimeTestCase(unittest.TestCase):
    def test_extract_bvid_from_standard_url(self):
        self.assertEqual(
            extract_bvid("https://www.bilibili.com/video/BV1qdXoBdEYy/"),
            "BV1qdXoBdEYy",
        )

    def test_title_falls_back_to_bvid_and_url(self):
        title = resolve_video_title("", "BV1qdXoBdEYy", "https://www.bilibili.com/video/BV1qdXoBdEYy/")
        self.assertIn("BV1qdXoBdEYy", title)

    def test_task_paths_live_under_backend_artifacts(self):
        paths = build_task_paths(project_root=Path("C:/demo"), task_id=12)
        self.assertEqual(paths["note"], Path("C:/demo/backend/artifacts/video-notes/12/notes/final-note.md"))
```

**Step 2: Run test to verify it fails**

Run: `& .\.venv\Scripts\python.exe -m unittest backend.tests.test_video_note_runtime -v`
Expected: FAIL because the runtime helpers do not exist yet.

**Step 3: Write minimal implementation**

- `extract_bvid(url)` parses a valid Bilibili video URL
- `resolve_video_title(raw_title, bvid, source_url)` returns the `yt-dlp` title when present, otherwise `f"{bvid} - {source_url}"`
- `build_task_paths(project_root, task_id)` returns the exact task directory and file layout
- `transcribe_audio.py` becomes the project-local CLI script that `conda run -n whisper python ...` will execute

**Step 4: Run test to verify it passes**

Run: `& .\.venv\Scripts\python.exe -m unittest backend.tests.test_video_note_runtime -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/video_notes/runtime backend/tests/test_video_note_runtime.py
git commit -m "feat: add video note runtime helpers"
```

### Task 3: Build the task repository, artifact writer, and execution pipeline

**Files:**
- Create: `backend/app/video_notes/repositories/__init__.py`
- Create: `backend/app/video_notes/repositories/task_repo.py`
- Create: `backend/app/video_notes/services/__init__.py`
- Create: `backend/app/video_notes/services/task_service.py`
- Create: `backend/app/video_notes/services/artifact_service.py`
- Create: `backend/app/video_notes/services/download_service.py`
- Create: `backend/app/video_notes/services/transcription_service.py`
- Create: `backend/app/video_notes/services/note_generation_service.py`
- Create: `backend/app/video_notes/services/execution_service.py`
- Test: `backend/tests/test_video_note_services.py`

**Step 1: Write the failing test**

```python
class VideoNoteExecutionServiceTestCase(unittest.TestCase):
    def test_pipeline_writes_paths_and_marks_task_completed(self):
        task = self.task_service.create_task(
            source_url="https://www.bilibili.com/video/BV1qdXoBdEYy/",
            platform="bilibili",
            bvid="BV1qdXoBdEYy",
            status="pending",
        )

        self.execution_service.run_task(task.id)
        refreshed = self.task_repo.get_by_id(task.id)

        self.assertEqual(refreshed.status, "completed")
        self.assertEqual(refreshed.current_step, "done")
        self.assertTrue(Path(refreshed.note_path).exists())
        self.assertTrue(Path(refreshed.metadata_path).exists())
```

**Step 2: Run test to verify it fails**

Run: `& .\.venv\Scripts\python.exe -m unittest backend.tests.test_video_note_services -v`
Expected: FAIL because the repository and services do not exist yet.

**Step 3: Write minimal implementation**

- `TaskRepository` manages `VideoNoteTask` and `VideoNoteTaskLog`
- `TaskService` creates tasks, updates status, and appends logs
- `ArtifactService` creates directories and writes:
  - `source/video.wav`
  - `transcript/video.srt`
  - `notes/final-note.md`
  - `metadata.json`
- `DownloadService` wraps `yt-dlp`
- `TranscriptionService` wraps `conda run -n whisper python backend/app/video_notes/runtime/transcribe_audio.py ...`
- `NoteGenerationService` reads SRT and calls Gemini
- `ExecutionService` orchestrates the full state machine:
  - `pending -> running/download_audio`
  - `running/transcribe_srt`
  - `running/generate_note`
  - `completed/done`
  - or `failed`

**Step 4: Run test to verify it passes**

Run: `& .\.venv\Scripts\python.exe -m unittest backend.tests.test_video_note_services -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/video_notes/repositories backend/app/video_notes/services backend/tests/test_video_note_services.py
git commit -m "feat: add video note execution pipeline"
```

### Task 4: Expose the backend API and background execution hook

**Files:**
- Create: `backend/app/video_notes/routes/__init__.py`
- Create: `backend/app/video_notes/routes/task.py`
- Modify: `backend/app/routes/__init__.py`
- Test: `backend/tests/test_video_note_api.py`

**Step 1: Write the failing test**

```python
class VideoNoteApiTestCase(unittest.TestCase):
    def test_create_video_note_task_returns_task_payload(self):
        response = self.client.post(
            "/api/video-note-tasks",
            json={"source_url": "https://www.bilibili.com/video/BV1qdXoBdEYy/"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["data"]["status"], "pending")

    def test_create_video_note_task_rejects_invalid_url(self):
        response = self.client.post(
            "/api/video-note-tasks",
            json={"source_url": "https://example.com/not-bilibili"},
        )
        self.assertEqual(response.status_code, 400)
```

**Step 2: Run test to verify it fails**

Run: `& .\.venv\Scripts\python.exe -m unittest backend.tests.test_video_note_api -v`
Expected: FAIL because the routes are not registered yet.

**Step 3: Write minimal implementation**

- Add route helpers:
  - `POST /api/video-note-tasks`
  - `GET /api/video-note-tasks`
  - `GET /api/video-note-tasks/<id>`
  - `GET /api/video-note-tasks/<id>/logs`
- Inject an executor abstraction so tests can run tasks inline while production uses a background thread
- Keep route handlers thin:
  - validate request
  - create task
  - dispatch executor
  - return task payload

**Step 4: Run test to verify it passes**

Run: `& .\.venv\Scripts\python.exe -m unittest backend.tests.test_video_note_api -v`
Expected: PASS

**Step 5: Commit**

```bash
git add backend/app/video_notes/routes backend/app/routes/__init__.py backend/tests/test_video_note_api.py
git commit -m "feat: add video note task api"
```

### Task 5: Add frontend API bindings, store, routing, and three module pages

**Files:**
- Create: `frontend/src/api/videoNoteTask.js`
- Create: `frontend/src/stores/videoNotes.js`
- Create: `frontend/src/views/VideoNotesHome.vue`
- Create: `frontend/src/views/VideoNoteTaskList.vue`
- Create: `frontend/src/views/VideoNoteTaskDetail.vue`
- Modify: `frontend/src/router/index.js`
- Modify: `frontend/src/App.vue`

**Step 1: Write the failing test**

No frontend unit-test harness exists in this repository today, so the executable guardrail for this task is the production build. The backend API tests from earlier tasks remain the primary behavior safety net.

**Step 2: Run build to capture the current baseline**

Run: `npm run build`
Expected: PASS before the UI changes begin.

**Step 3: Write minimal implementation**

- `videoNoteTask.js` mirrors the crawler API style
- `videoNotes.js` manages:
  - task list
  - current task
  - logs
  - loading/submitting state
- `VideoNotesHome.vue` contains:
  - module intro
  - preparation checklist
  - task creation form
  - recent tasks
- `VideoNoteTaskList.vue` shows task cards / table
- `VideoNoteTaskDetail.vue` shows:
  - metadata
  - step status
  - logs
  - transcript preview
  - Markdown note preview
- Add a clear navigation entry in `App.vue`
- Add the new routes in `router/index.js`

**Step 4: Run build to verify it passes**

Run: `npm run build`
Expected: PASS

**Step 5: Commit**

```bash
git add frontend/src/api/videoNoteTask.js frontend/src/stores/videoNotes.js frontend/src/views/VideoNotesHome.vue frontend/src/views/VideoNoteTaskList.vue frontend/src/views/VideoNoteTaskDetail.vue frontend/src/router/index.js frontend/src/App.vue
git commit -m "feat: add video note frontend module"
```

### Task 6: Update docs for the new module and operating requirements

**Files:**
- Modify: `README.md`
- Modify: `AGENTS.md`
- Modify: `docs/project-overview.md`
- Modify: `docs/development-guide.md`
- Modify: `docs/roadmap.md`
- Modify: `docs/project-log.md`

**Step 1: Write the failing test**

No automated doc test exists. The quality gate for this task is consistency with the implemented module and the approved design doc.

**Step 2: Write minimal implementation**

- Add the `视频转笔记` module to the project overview
- Document runtime expectations:
  - `yt-dlp`
  - `conda run -n whisper`
  - Gemini key
- Add the new frontend route/module entry to README
- Record the new module milestone in the project log
- Reinforce in `AGENTS.md` that module-specific changes must update docs in the same session

**Step 3: Verify docs against code**

Run:
- `rg -n "video-note|video notes|视频转笔记" README.md AGENTS.md docs`

Expected: The docs consistently mention the new module and no stale wording is left behind.

**Step 4: Commit**

```bash
git add README.md AGENTS.md docs/project-overview.md docs/development-guide.md docs/roadmap.md docs/project-log.md
git commit -m "docs: document video note module"
```

### Task 7: Run final verification for the feature

**Files:**
- Review: `git status --short --branch`

**Step 1: Run the focused backend test suite**

Run:
- `& .\.venv\Scripts\python.exe -m unittest backend.tests.test_video_note_models -v`
- `& .\.venv\Scripts\python.exe -m unittest backend.tests.test_video_note_runtime -v`
- `& .\.venv\Scripts\python.exe -m unittest backend.tests.test_video_note_services -v`
- `& .\.venv\Scripts\python.exe -m unittest backend.tests.test_video_note_api -v`

Expected: PASS

**Step 2: Re-run the existing path safety test**

Run: `& .\.venv\Scripts\python.exe -m unittest backend.tests.test_runtime_paths -v`
Expected: PASS

**Step 3: Run the frontend build**

Run: `npm run build`
Expected: PASS

**Step 4: Review the worktree**

Run: `git status --short --branch`
Expected: Only the intended module, UI, and docs changes are present.

**Step 5: Commit**

```bash
git add backend frontend docs README.md AGENTS.md
git commit -m "feat: add bilibili video note workflow"
```

### Task 8: Perform a manual happy-path task run

**Files:**
- Review generated artifacts under: `backend/artifacts/video-notes/<task_id>/`

**Step 1: Start the app**

Run: `start.bat`
Expected: Backend and frontend start successfully.

**Step 2: Create a real task from the UI**

Use a known Bilibili video URL and the default parameters.
Expected: The task moves from `pending` to `running` and eventually reaches `completed`.

**Step 3: Inspect the outputs**

Verify the task directory contains:
- `source/video.wav`
- `transcript/video.srt`
- `notes/final-note.md`
- `metadata.json`

**Step 4: Capture any follow-up**

If environment-specific failures occur, document them in `docs/project-log.md` before moving on to the separate local folder rename task.
