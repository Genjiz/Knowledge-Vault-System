from datetime import UTC, datetime

from app.core.extensions import db


class LLMProfile(db.Model):
    __tablename__ = "llm_profile"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    protocol = db.Column(db.String(20), nullable=False)
    base_url = db.Column(db.String(1000))
    model_name = db.Column(db.String(255), nullable=False)
    enabled = db.Column(db.Boolean, nullable=False, default=True)
    last_check_status = db.Column(db.String(20))
    last_check_message = db.Column(db.Text)
    last_checked_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    scene_bindings = db.relationship(
        "LLMSceneBinding",
        back_populates="profile",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def to_dict(self, *, has_api_key=False):
        return {
            "id": self.id,
            "name": self.name,
            "protocol": self.protocol,
            "base_url": self.base_url,
            "model_name": self.model_name,
            "enabled": self.enabled,
            "has_api_key": has_api_key,
            "last_check_status": self.last_check_status,
            "last_check_message": self.last_check_message,
            "last_checked_at": self.last_checked_at.isoformat() if self.last_checked_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class LLMSceneBinding(db.Model):
    __tablename__ = "llm_scene_binding"

    id = db.Column(db.Integer, primary_key=True)
    scene = db.Column(db.String(50), nullable=False, unique=True)
    profile_id = db.Column(db.Integer, db.ForeignKey("llm_profile.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    updated_at = db.Column(
        db.DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    profile = db.relationship("LLMProfile", back_populates="scene_bindings")

    def to_dict(self):
        return {
            "scene": self.scene,
            "profile_id": self.profile_id,
            "profile_name": self.profile.name if self.profile else None,
            "model_name": self.profile.model_name if self.profile else None,
        }
