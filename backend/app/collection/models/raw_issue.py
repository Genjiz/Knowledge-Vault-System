from app.core.extensions import db
from app.papers.models.base import BaseModel


class RawIssue(BaseModel):
    __tablename__ = "raw_issue"
    __table_args__ = (
        db.UniqueConstraint(
            "source_type",
            "journal_name",
            "year",
            "issue",
            name="uq_raw_issue_identity",
        ),
    )

    # source_type 存真实采集源 id（ncpssd/magtech/elsevier），参与期号唯一键；
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
    paper_count = db.Column(db.Integer, nullable=False, default=0)
    translation_status = db.Column(db.String(32), nullable=False, default="pending")
    analysis_status = db.Column(db.String(32), nullable=False, default="pending")
    raw_json_path = db.Column(db.String(500))
    crawl_task_id = db.Column(db.Integer, db.ForeignKey("crawl_task.id"), index=True)

    crawl_task = db.relationship("CrawlTask", back_populates="raw_issues")
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
                "paper_count": self.paper_count,
                "translation_status": self.translation_status,
                "analysis_status": self.analysis_status,
                "raw_json_path": self.raw_json_path,
                "crawl_task_id": self.crawl_task_id,
            }
        )
        return data
