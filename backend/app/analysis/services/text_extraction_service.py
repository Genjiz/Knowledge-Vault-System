from dataclasses import dataclass
import hashlib
from importlib.metadata import PackageNotFoundError, version
import json
from pathlib import Path

from flask import current_app

from app.analysis.models import LiteratureTextAsset
from app.core.extensions import db
from app.core.paths import data_root, literature_text_assets_root


DEFAULT_PIPELINE_VERSION = "academic-markdown-v1"


class TextExtractionError(ValueError):
    pass


@dataclass(frozen=True)
class ExtractionResult:
    markdown: str
    page_count: int | None = None


def _package_version(package):
    try:
        return version(package)
    except PackageNotFoundError:
        return "not-installed"


class PyMuPDF4LLMExtractor:
    name = "pymupdf4llm"

    @property
    def version(self):
        return _package_version("pymupdf4llm")

    def extract(self, path):
        import pymupdf
        import pymupdf4llm

        markdown = pymupdf4llm.to_markdown(str(path))
        with pymupdf.open(path) as document:
            page_count = document.page_count
        return ExtractionResult(markdown=markdown, page_count=page_count)


class DoclingExtractor:
    name = "docling"

    @property
    def version(self):
        return _package_version("docling")

    def extract(self, path):
        from docling.document_converter import DocumentConverter

        result = DocumentConverter().convert(str(path))
        return ExtractionResult(markdown=result.document.export_to_markdown())


class LiteratureTextExtractionService:
    def __init__(self, extractors=None, pipeline_version=DEFAULT_PIPELINE_VERSION):
        self.extractors = extractors or [PyMuPDF4LLMExtractor(), DoclingExtractor()]
        self.pipeline_version = pipeline_version

    @staticmethod
    def _pdf_path(literature):
        if not literature.pdf_path:
            raise TextExtractionError("文献没有可解析的 PDF")
        path = Path(literature.pdf_path)
        if not path.is_absolute():
            path = data_root() / path
        if not path.is_file():
            raise TextExtractionError("PDF 文件不存在")
        return path

    @staticmethod
    def _sha256(path):
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _asset_root():
        configured = current_app.config.get("LITERATURE_TEXT_ASSET_ROOT")
        return Path(configured) if configured else literature_text_assets_root()

    def _target_path(self, pdf_sha256):
        return (
            self._asset_root()
            / pdf_sha256
            / self.pipeline_version
            / "content.md"
        )

    @staticmethod
    def _completed_asset_is_valid(asset):
        if asset.status != "completed" or not asset.markdown_path or not asset.markdown_sha256:
            return False
        path = Path(asset.markdown_path)
        if not path.is_file():
            return False
        return LiteratureTextExtractionService._sha256(path) == asset.markdown_sha256

    def get_or_extract(self, literature):
        pdf_path = self._pdf_path(literature)
        pdf_sha256 = self._sha256(pdf_path)
        if literature.pdf_sha256 != pdf_sha256:
            literature.pdf_sha256 = pdf_sha256
            literature.pdf_size_bytes = pdf_path.stat().st_size
            db.session.commit()

        asset = LiteratureTextAsset.query.filter_by(
            source_pdf_sha256=pdf_sha256,
            pipeline_version=self.pipeline_version,
        ).first()
        if asset is not None and self._completed_asset_is_valid(asset):
            return asset
        if asset is None:
            asset = LiteratureTextAsset(
                literature_id=literature.id,
                source_pdf_sha256=pdf_sha256,
                pipeline_version=self.pipeline_version,
                status="pending",
            )
            db.session.add(asset)
        else:
            asset.status = "pending"
            asset.error_message = None
        db.session.commit()

        attempts = []
        for extractor in self.extractors:
            try:
                result = extractor.extract(pdf_path)
                markdown = str(result.markdown or "").strip()
                if not markdown:
                    raise TextExtractionError("解析器未返回可用文本")
                target = self._target_path(pdf_sha256)
                target.parent.mkdir(parents=True, exist_ok=True)
                temporary = target.with_name(f"{target.name}.part-{asset.id}")
                try:
                    temporary.write_text(markdown, encoding="utf-8")
                    temporary.replace(target)
                finally:
                    if temporary.exists():
                        temporary.unlink()
                attempts.append({"extractor": extractor.name, "status": "completed"})
                asset.extractor_name = extractor.name
                asset.extractor_version = extractor.version
                asset.markdown_path = str(target)
                asset.markdown_sha256 = self._sha256(target)
                asset.status = "completed"
                asset.error_message = None
                asset.attempts_json = json.dumps(attempts, ensure_ascii=False)
                asset.page_count = result.page_count
                asset.char_count = len(markdown)
                db.session.commit()
                db.session.refresh(asset)
                return asset
            except Exception as exc:
                attempts.append(
                    {
                        "extractor": extractor.name,
                        "status": "failed",
                        "error": str(exc),
                    }
                )

        asset.status = "failed"
        asset.error_message = "；".join(item["error"] for item in attempts)
        asset.attempts_json = json.dumps(attempts, ensure_ascii=False)
        db.session.commit()
        raise TextExtractionError(f"PDF 文本提取失败：{asset.error_message}")

    @staticmethod
    def read_markdown(asset):
        if not LiteratureTextExtractionService._completed_asset_is_valid(asset):
            raise TextExtractionError("全文 Markdown 缺失或校验失败")
        return Path(asset.markdown_path).read_text(encoding="utf-8")
