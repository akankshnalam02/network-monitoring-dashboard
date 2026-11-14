from datetime import datetime

from models.database import db


class MonitoringLog(db.Model):

    __tablename__ = "monitoring_logs"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    device_id = db.Column(
        db.Integer,
        db.ForeignKey("devices.id"),
        nullable=False
    )

    status = db.Column(
        db.String(20),
        nullable=False
    )

    latency = db.Column(
        db.Float,
        nullable=True
    )

    checked_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )