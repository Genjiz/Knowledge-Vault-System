from app.core.extensions import db
from app.papers.models.base import BaseModel


class Journal(BaseModel):
    """期刊一等实体：文献与采集共用（T-5 期刊筛选、T-1 按期刊配置采集源）。"""

    __tablename__ = "journal"

    name = db.Column(db.String(255), nullable=False, unique=True)
    issn = db.Column(db.String(20))
    publisher = db.Column(db.String(200))

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
    config_json = db.Column(db.Text)

    journal = db.relationship("Journal", back_populates="source_configs")

    def to_dict(self):
        data = super().to_dict()
        data.update(
            {
                "journal_id": self.journal_id,
                "source_id": self.source_id,
                "enabled": self.enabled,
                "config_json": self.config_json,
            }
        )
        return data
