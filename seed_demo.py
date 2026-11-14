"""Create realistic local demo data without performing network checks."""

from datetime import datetime, timedelta

from app import app, initialize_database
from models.alert import Alert
from models.database import db
from models.device import Device
from models.monitoring_log import MonitoringLog
from models.port import Port


DEMO_DEVICES = [
    {
        "name": "Core Router",
        "ip_address": "192.168.1.1",
        "device_type": "Router",
        "description": "Primary gateway for the lab network",
    },
    {
        "name": "Web Server",
        "ip_address": "192.168.1.10",
        "device_type": "Server",
        "description": "Internal application and documentation server",
    },
    {
        "name": "Database Server",
        "ip_address": "192.168.1.20",
        "device_type": "Server",
        "description": "Database host for the lab environment",
    },
]


def seed_demo_data():
    initialize_database()
    with app.app_context():
        if Device.query.first():
            print("Demo data skipped: the database already contains devices.")
            return

        devices = [Device(**data, status="UNKNOWN", monitoring_enabled=True)
                   for data in DEMO_DEVICES]
        db.session.add_all(devices)
        db.session.flush()

        ports = [
            Port(device_id=devices[0].id, port_number=80,
                 service_name="HTTP", status="OPEN"),
            Port(device_id=devices[1].id, port_number=443,
                 service_name="HTTPS", status="OPEN"),
            Port(device_id=devices[1].id, port_number=22,
                 service_name="SSH", status="CLOSED"),
            Port(device_id=devices[2].id, port_number=3306,
                 service_name="MySQL", status="OPEN"),
        ]
        db.session.add_all(ports)

        now = datetime.utcnow()
        samples = [
            (devices[0], "ONLINE", 12.0),
            (devices[1], "ONLINE", 28.0),
            (devices[2], "OFFLINE", None),
        ]
        for device, status, latency in samples:
            for offset in range(5, 0, -1):
                log = MonitoringLog(
                    device_id=device.id,
                    status=status,
                    latency=latency + offset if latency is not None else None,
                    checked_at=now - timedelta(minutes=offset * 5),
                )
                db.session.add(log)
            device.status = status

        db.session.add(Alert(
            device_id=devices[2].id,
            alert_type="DEVICE_OFFLINE",
            message="Database Server is offline.",
            created_at=now - timedelta(minutes=4),
        ))
        db.session.add(Alert(
            device_id=devices[1].id,
            alert_type="PORT_OPENED",
            message="Port 22 (SSH) changed from CLOSED to OPEN on Web Server.",
            created_at=now - timedelta(minutes=12),
        ))
        db.session.commit()
        print("Demo data created: 3 devices, 4 ports, 15 logs, and 2 alerts.")


if __name__ == "__main__":
    seed_demo_data()
