from datetime import datetime

from models.database import db


class Alert(db.Model):

    __tablename__ = "alerts"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    device_id = db.Column(
        db.Integer,
        db.ForeignKey("devices.id"),
        nullable=False
    )

    alert_type = db.Column(
        db.String(50),
        nullable=False
    )

    message = db.Column(
        db.String(255),
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    is_resolved = db.Column(
        db.Boolean,
        default=False
    )