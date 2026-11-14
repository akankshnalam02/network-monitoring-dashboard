from datetime import datetime

from models.database import db


class Port(db.Model):

    __tablename__ = "ports"

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    device_id = db.Column(
        db.Integer,
        db.ForeignKey("devices.id"),
        nullable=False
    )

    port_number = db.Column(
        db.Integer,
        nullable=False
    )

    service_name = db.Column(
        db.String(80),
        nullable=False,
        default="TCP"
    )

    status = db.Column(
        db.String(20),
        default="UNKNOWN"
    )

    last_checked = db.Column(
        db.DateTime,
        default=datetime.utcnow
    )

    __table_args__ = (
        db.UniqueConstraint("device_id", "port_number", name="uq_device_port"),
    )