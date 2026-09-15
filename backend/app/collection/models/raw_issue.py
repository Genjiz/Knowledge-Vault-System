from app.core.extensions import db
from app.papers.models.base import BaseModel


class RawIssue(BaseModel):
    __tablename__ = "raw_issue"
    __table_args__ = (
        db.UniqueConstraint(
            "source_type",
            "journal_name",
            "year",
            "volume",
            "issue",
            name="uq_raw_issue_identity",
        ),
    )

    # source_type 存真实采集源 id，卷号与期号共同参与批次唯一键；
    # region 是区域类别（domestic/foreign），供语言推断与前端分组
    source_type = db.Column(db.String(50), nullable=False)
    region = db.Column(db.String(20))
    journal_name = db.Column(db.String(255), nullable=False)
    journal_slug = db.Column(db.String(255))
    year = db.Column(db.Integer, nullable=False)
    issue = db.Column(db.String(50), nullable=False)
    volume = db.Column(db.String(50))
    language = db.Column(db.String(20), default="mixed")
    source_url = db.Column(db.String(1000))
    expected_paper_count = db.Column(db.Integer, nullable=False, default=0, server_default="0")
    paper_count = db.Column(db.Integer, nullable=False, default=0)
    translation_status = db.Column(db.String(32), nullable=False, default="pending")
    translation_profile_id = db.Column(
        db.Integer, db.ForeignKey("llm_profile.id", ondelete="SET NULL")
    )
    translation_model_name = db.Column(db.String(255))
    analysis_status = db.Column(db.String(32), nullable=False, default="pending")
    raw_json_path = db.Column(db.String(500))
    crawl_task_id = db.Column(db.Integer, db.ForeignKey("crawl_task.id"), index=True)

    crawl_task = db.relationship("CrawlTask", back_populates="raw_issues")
    translation_profile = db.relationship("LLMProfile")
    papers = db.relationship(
        "RawPaper",
        back_populates="raw_issue",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="RawPaper.sort_index.asc()",
    )
    analyses = db.relationship(
        "RawIssueAnalysis",
        back_populates="raw_issue",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    fulltext_tasks = db.relationship(
        "FullTextTask",
        back_populates="raw_issue",
        lazy="selectin",
        passive_deletes=True,
    )

    def to_dict(self):
        title_collected_count = sum(bool((paper.title or "").strip()) for paper in self.papers)
        abstract_collected_count = sum(bool((paper.abstract or "").strip()) for paper in self.papers)
        fulltext_collected_count = sum(
            any(
                source.literature and bool(source.literature.pdf_path)
                for source in paper.literature_sources
            )
            for paper in self.papers
        )
        data = super().to_dict()
        data.update(
            {
                "source_type": self.source_type,
                "region": self.region,
                "journal_name": self.journal_name,
                "journal_slug": self.journal_slug,
                "year": self.year,
                "issue": self.issue,
                "volume": self.volume,
                "language": self.language,
                "source_url": self.source_url,
                "expected_paper_count": (
                    self.expected_paper_count
                    if self.expected_paper_count is not None
                    else self.paper_count or 0
                ),
                "paper_count": self.paper_count,
                "title_collected_count": title_collected_count,
                "abstract_collected_count": abstract_collected_count,
                "fulltext_collected_count": fulltext_collected_count,
                "translation_status": self.translation_status,
                "translation_profile_id": self.translation_profile_id,
                "translation_profile_name": (
                    self.translation_profile.name if self.translation_profile else None
                ),
                "translation_model_name": self.translation_model_name,
                "analysis_status": self.analysis_status,
                "raw_json_path": self.raw_json_path,
                "crawl_task_id": self.crawl_task_id,
            }
        )
        return data
