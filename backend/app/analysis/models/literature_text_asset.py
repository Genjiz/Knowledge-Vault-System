from app.core.extensions import db
from app.papers.models.base import BaseModel


class LiteratureTextAsset(BaseModel):
    __tablename__ = "literature_text_asset"
    __table_args__ = (
        db.UniqueConstraint(
            "source_pdf_sha256",
            "pipeline_version",
            name="uq_text_asset_source_pipeline",
        ),
    )

    literature_id = db.Column(
        db.Integer,
        db.ForeignKey("literature.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    source_pdf_sha256 = db.Column(db.String(64), nullable=False)
    pipeline_version = db.Column(db.String(100), nullable=False)
    extractor_name = db.Column(db.String(100))
    extractor_version = db.Column(db.String(100))
    markdown_path = db.Column(db.String(1000))
    markdown_sha256 = db.Column(db.String(64))
    status = db.Column(db.String(20), nullable=False, default="pending")
    error_message = db.Column(db.Text)
    attempts_json = db.Column(db.Text)
    page_count = db.Column(db.Integer)
    char_count = db.Column(db.Integer, nullable=False, default=0)

    literature = db.relationship("Literature")

    def to_dict(self):
        data = super().to_dict()
        data.update(
            {
                "literature_id": self.literature_id,
                "source_pdf_sha256": self.source_pdf_sha256,
                "pipeline_version": self.pipeline_version,
                "extractor_name": self.extractor_name,
                "extractor_version": self.extractor_version,
                "markdown_path": self.markdown_path,
                "markdown_sha256": self.markdown_sha256,
                "status": self.status,
                "error_message": self.error_message,
                "page_count": self.page_count,
                "char_count": self.char_count,
            }
        )
        return data
