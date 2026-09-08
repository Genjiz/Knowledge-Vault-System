from datetime import UTC, datetime

from app.core.extensions import db
from app.papers.models.base import BaseModel


class PaperAnalysis(BaseModel):
    __tablename__ = "paper_analysis"

    title = db.Column(db.String(255))
    status = db.Column(db.String(20), nullable=False, default="queued")
    profile_id = db.Column(db.Integer, db.ForeignKey("llm_profile.id", ondelete="SET NULL"))
    model_name = db.Column(db.String(255))
    paper_count = db.Column(db.Integer, nullable=False, default=0)
    content_markdown = db.Column(db.Text)
    artifact_md_path = db.Column(db.String(500))
    error_message = db.Column(db.Text)
    started_at = db.Column(db.DateTime)
    finished_at = db.Column(db.DateTime)

    profile = db.relationship("LLMProfile")
    items = db.relationship(
        "PaperAnalysisItem",
        back_populates="analysis",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="PaperAnalysisItem.sort_index.asc()",
    )

    def to_dict(self, *, include_items=False, include_content=True):
        data = super().to_dict()
        data.update(
            {
                "title": self.title,
                "status": self.status,
                "profile_id": self.profile_id,
                "profile_name": self.profile.name if self.profile else None,
                "model_name": self.model_name,
                "paper_count": self.paper_count,
                "artifact_md_path": self.artifact_md_path,
                "error_message": self.error_message,
                "started_at": self.started_at.isoformat() if self.started_at else None,
                "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            }
        )
        if include_content:
            data["content_markdown"] = self.content_markdown
        if include_items:
            data["items"] = [item.to_dict() for item in self.items]
        return data


class PaperAnalysisItem(BaseModel):
    __tablename__ = "paper_analysis_item"
    __table_args__ = (
        db.UniqueConstraint("analysis_id", "literature_id", name="uq_analysis_literature"),
    )

    analysis_id = db.Column(
        db.Integer,
        db.ForeignKey("paper_analysis.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    literature_id = db.Column(
        db.Integer, db.ForeignKey("literature.id", ondelete="SET NULL"), index=True
    )
    sort_index = db.Column(db.Integer, nullable=False, default=0)
    title = db.Column(db.String(500), nullable=False)
    authors = db.Column(db.Text)
    journal = db.Column(db.String(200))
    year = db.Column(db.Integer)
    volume = db.Column(db.String(20))
    issue = db.Column(db.String(20))
    abstract = db.Column(db.Text)
    keywords = db.Column(db.Text)

    analysis = db.relationship("PaperAnalysis", back_populates="items")
    literature = db.relationship("Literature")

    @classmethod
    def from_literature(cls, analysis_id, literature, sort_index):
        return cls(
            analysis_id=analysis_id,
            literature_id=literature.id,
            sort_index=sort_index,
            title=literature.title,
            authors=literature.authors,
            journal=literature.journal,
            year=literature.year,
            volume=literature.volume,
            issue=literature.issue,
            abstract=literature.abstract,
            keywords=literature.keywords,
        )

    def clone_for(self, analysis_id):
        return PaperAnalysisItem(
            analysis_id=analysis_id,
            literature_id=self.literature_id,
            sort_index=self.sort_index,
            title=self.title,
            authors=self.authors,
            journal=self.journal,
            year=self.year,
            volume=self.volume,
            issue=self.issue,
            abstract=self.abstract,
            keywords=self.keywords,
        )

    def to_dict(self):
        data = super().to_dict()
        data.update(
            {
                "analysis_id": self.analysis_id,
                "literature_id": self.literature_id,
                "sort_index": self.sort_index,
                "title": self.title,
                "authors": self.authors,
                "journal": self.journal,
                "year": self.year,
                "volume": self.volume,
                "issue": self.issue,
                "abstract": self.abstract,
                "keywords": self.keywords,
            }
        )
        return data
