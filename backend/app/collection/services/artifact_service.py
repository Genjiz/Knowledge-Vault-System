import json
from pathlib import Path

from flask import current_app

from app.core.extensions import db


def _slugify_path_part(value):
    return str(value).replace("/", "-").replace("\\", "-").strip()


class ArtifactService:
    def _artifact_root(self):
        return Path(current_app.config["ARTIFACT_ROOT"])

    def export_raw_issue(self, raw_issue):
        journal = _slugify_path_part(raw_issue.journal_name)
        issue = _slugify_path_part(raw_issue.issue)
        artifact_path = (
            self._artifact_root()
            / "raw-json"
            / raw_issue.source_type
            / journal
            / str(raw_issue.year)
            / f"{issue}.json"
        )
        artifact_path.parent.mkdir(parents=True, exist_ok=True)

        payload = raw_issue.to_dict()
        payload["papers"] = [paper.to_dict() for paper in raw_issue.papers]

        artifact_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

        raw_issue.raw_json_path = str(artifact_path)
        db.session.commit()
        return str(artifact_path)

    def export_analysis(self, analysis):
        raw_issue = analysis.raw_issue
        journal = _slugify_path_part(raw_issue.journal_name)
        issue = _slugify_path_part(raw_issue.issue)
        artifact_path = (
            self._artifact_root()
            / "analysis-md"
            / raw_issue.source_type
            / journal
            / str(raw_issue.year)
            / f"{issue}.md"
        )
        artifact_path.parent.mkdir(parents=True, exist_ok=True)
        artifact_path.write_text(analysis.content_markdown or "", encoding="utf-8")

        analysis.artifact_md_path = str(artifact_path)
        db.session.commit()
        return str(artifact_path)
