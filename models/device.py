from datetime import datetime

from models.database import db


class Device(db.Model):

    __tablename__ = "devices"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(120),
        nullable=False
    )

    ip_address = db.Column(
        db.String(120),
        nullable=False
    )

    device_type = db.Column(
        db.String(50),
        nullable=False,
        default="Other"
    )

    description = db.Column(
        db.Text,
        default=""
    )

    status = db.Column(
        db.String(20),
        default="UNKNOWN"
    )

    monitoring_enabled = db.Column(
        db.Boolean,
        default=True,
        nullable=False
    )

    created_at = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    logs = db.relationship(
        "MonitoringLog",
        backref="device",
        lazy=True,
        cascade="all, delete-orphan"
    )

    ports = db.relationship(
        "Port",
        backref="device",
        lazy=True,
        cascade="all, delete-orphan"
    )

    alerts = db.relationship(
        "Alert",
        backref="device",
        lazy=True,
        cascade="all, delete-orphan"
    )

    @property
    def latest_log(self):
        return max(self.logs, key=lambda log: log.checked_at) if self.logs else None

    @property
    def latest_status(self):
        return self.latest_log.status if self.latest_log else self.status or "UNKNOWN"

    @property
    def uptime_percent(self):
        if not self.logs:
            return None
        online_logs = sum(log.status == "ONLINE" for log in self.logs)
        return round(online_logs / len(self.logs) * 100, 1)