from app.core.extensions import db
from app.papers.models.base import BaseModel


class RawPaper(BaseModel):
    __tablename__ = "raw_paper"

    raw_issue_id = db.Column(db.Integer, db.ForeignKey("raw_issue.id"), nullable=False, index=True)
    source_identifier = db.Column(db.String(255))
    title = db.Column(db.Text, nullable=False)
    title_zh = db.Column(db.Text)
    authors = db.Column(db.Text)
    abstract = db.Column(db.Text)
    abstract_zh = db.Column(db.Text)
    keywords_json = db.Column(db.Text)
    pages = db.Column(db.String(100))
    detail_url = db.Column(db.String(1000))
    published_at = db.Column(db.String(100))
    sort_index = db.Column(db.Integer, nullable=False, default=0)
    translation_status = db.Column(db.String(32), nullable=False, default="pending")

    raw_issue = db.relationship("RawIssue", back_populates="papers")
    llm_runs = db.relationship("LLMRun", back_populates="raw_paper", lazy="selectin")

    def to_dict(self):
        data = super().to_dict()
        data.update(
            {
                "raw_issue_id": self.raw_issue_id,
                "source_identifier": self.source_identifier,
                "title": self.title,
                "title_zh": self.title_zh,
                "authors": self.authors,
                "abstract": self.abstract,
                "abstract_zh": self.abstract_zh,
                "keywords_json": self.keywords_json,
                "pages": self.pages,
                "detail_url": self.detail_url,
                "published_at": self.published_at,
                "sort_index": self.sort_index,
                "translation_status": self.translation_status,
            }
        )
        return data
