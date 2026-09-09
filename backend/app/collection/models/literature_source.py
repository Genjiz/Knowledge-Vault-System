from app.core.extensions import db
from app.papers.models.base import BaseModel


class LiteratureSource(BaseModel):
    __tablename__ = "literature_source"
    __table_args__ = (
        db.UniqueConstraint("raw_paper_id", name="uq_literature_source_raw_paper"),
    )

    literature_id = db.Column(
        db.Integer,
        db.ForeignKey("literature.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    raw_paper_id = db.Column(
        db.Integer,
        db.ForeignKey("raw_paper.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_type = db.Column(db.String(50), nullable=False, index=True)

    literature = db.relationship("Literature", back_populates="collection_sources", lazy="joined")
    raw_paper = db.relationship("RawPaper", back_populates="literature_sources")

    def to_dict(self):
        data = super().to_dict()
        data.update(
            {
                "literature_id": self.literature_id,
                "raw_paper_id": self.raw_paper_id,
                "source_type": self.source_type,
            }
        )
        return data
