from models.database import db
from models.monitoring_log import MonitoringLog
from models.alert import Alert

from monitoring.ping import ping_device


def check_device(device):

    # Get the previous monitoring result
    previous_log = (
        MonitoringLog.query
        .filter_by(device_id=device.id)
        .order_by(MonitoringLog.checked_at.desc())
        .first()
    )

    # Check the device
    result = ping_device(device.ip_address)

    # Save the new monitoring result
    log = MonitoringLog(
        device_id=device.id,
        status=result["status"],
        latency=result["latency"]
    )

    db.session.add(log)
    device.status = result["status"]

    # Detect ONLINE -> OFFLINE
    if (
        previous_log
        and previous_log.status == "ONLINE"
        and result["status"] == "OFFLINE"
    ):

        alert = Alert(
            device_id=device.id,
            alert_type="DEVICE_OFFLINE",
            message=f"{device.name} is offline."
        )

        db.session.add(alert)

        print(
            f"[ALERT] {device.name} is OFFLINE"
        )

    # Detect OFFLINE -> ONLINE
    elif (
        previous_log
        and previous_log.status == "OFFLINE"
        and result["status"] == "ONLINE"
    ):

        alert = Alert(
            device_id=device.id,
            alert_type="DEVICE_RECOVERED",
            message=f"{device.name} is back online."
        )

        db.session.add(alert)

        print(
            f"[RECOVERY] {device.name} is ONLINE"
        )

    db.session.commit()

    return result