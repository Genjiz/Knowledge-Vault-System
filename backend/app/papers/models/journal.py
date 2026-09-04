from app.core.extensions import db
from app.papers.models.base import BaseModel


class Journal(BaseModel):
    """期刊一等实体：文献与采集共用（T-5 期刊筛选、T-1 按期刊配置采集源）。"""

    __tablename__ = "journal"

    name = db.Column(db.String(255), nullable=False, unique=True)
    issn = db.Column(db.String(20))
    publisher = db.Column(db.String(200))
    # 期刊区域（domestic/foreign），用户在期刊页维护；决定该期刊可选的采集源范围，
    # 也是判断采集论文为中文/英文的依据
    region = db.Column(db.String(20))

    source_configs = db.relationship(
        "JournalSourceConfig",
        back_populates="journal",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def to_dict(self):
        data = super().to_dict()
        data.update(
            {
                "name": self.name,
                "issn": self.issn,
                "publisher": self.publisher,
                "region": self.region,
                "sources": [config.to_dict() for config in self.source_configs],
            }
        )
        return data


class JournalSourceConfig(BaseModel):
    """期刊-采集源配置：每个期刊可配置多个可用采集源（T-1）。"""

    __tablename__ = "journal_source_config"
    __table_args__ = (db.UniqueConstraint("journal_id", "source_id", name="uq_journal_source"),)

    journal_id = db.Column(db.Integer, db.ForeignKey("journal.id"), nullable=False, index=True)
    source_id = db.Column(db.String(50), nullable=False)
    enabled = db.Column(db.Boolean, nullable=False, default=True)
    # 采集源私有配置（JSON 字符串），键取自源声明的 config_fields
    config_json = db.Column(db.Text)
    # 每个期刊至多一个默认源，采集台发起任务时默认选中
    is_default = db.Column(db.Boolean, nullable=False, default=False)
    # 最近一次「测试连接」的结果，落库后列表页直接展示，避免每次进页面重测
    last_checked_at = db.Column(db.DateTime)
    last_check_status = db.Column(db.String(16))
    last_check_message = db.Column(db.Text)

    journal = db.relationship("Journal", back_populates="source_configs")

    def to_dict(self):
        data = super().to_dict()
        data.update(
            {
                "journal_id": self.journal_id,
                "source_id": self.source_id,
                "enabled": self.enabled,
                "is_default": self.is_default,
                "last_checked_at": (
                    self.last_checked_at.isoformat(timespec="seconds")
                    if self.last_checked_at
                    else None
                ),
                "last_check_status": self.last_check_status,
                "last_check_message": self.last_check_message,
                "config_json": self.config_json,
            }
        )
        return data
