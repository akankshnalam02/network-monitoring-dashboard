import socket
from datetime import datetime

from models.database import db
from models.port import Port
from models.alert import Alert


# ============================================================
# COMMON SERVICES
# ============================================================

COMMON_SERVICES = {

    20: "FTP-DATA",
    21: "FTP",
    22: "SSH",
    23: "TELNET",
    25: "SMTP",
    53: "DNS",
    80: "HTTP",
    110: "POP3",
    143: "IMAP",
    443: "HTTPS",
    3306: "MySQL",
    5432: "PostgreSQL",
    6379: "Redis",
    8080: "HTTP-ALT",

}


# ============================================================
# TCP PORT CHECK
# ============================================================

def check_tcp_port(
    ip_address,
    port_number,
    timeout=2
):

    try:

        with socket.socket(
            socket.AF_INET,
            socket.SOCK_STREAM
        ) as sock:

            sock.settimeout(timeout)

            result = sock.connect_ex(
                (ip_address, port_number)
            )

            if result == 0:

                return "OPEN"

            return "CLOSED"

    except (
        socket.timeout,
        socket.error,
        OSError
    ):

        return "CLOSED"


# ============================================================
# SERVICE NAME
# ============================================================

def get_service_name(port_number):

    return COMMON_SERVICES.get(
        port_number,
        f"TCP/{port_number}"
    )


# ============================================================
# MONITOR PORTS FOR ONE DEVICE
# ============================================================

def monitor_device_ports(device):

    ports = Port.query.filter_by(
        device_id=device.id
    ).all()

    for port in ports:

        previous_status = port.status

        current_status = check_tcp_port(
            device.ip_address,
            port.port_number
        )

        port.status = current_status
        port.last_checked = datetime.utcnow()

        # ====================================================
        # FIRST CHECK
        # ====================================================

        if previous_status == "UNKNOWN":

            print(
                f"[PORT] "
                f"{device.name} | "
                f"{device.ip_address} | "
                f"{port.port_number} | "
                f"{port.service_name} | "
                f"{current_status}"
            )

            continue

        # ====================================================
        # STATE CHANGED
        # ====================================================

        if previous_status != current_status:

            if current_status == "OPEN":

                message = (
                    f"Port {port.port_number} "
                    f"({port.service_name}) "
                    f"changed from CLOSED to OPEN "
                    f"on {device.name}."
                )

                alert_type = "PORT_OPENED"

            else:

                message = (
                    f"Port {port.port_number} "
                    f"({port.service_name}) "
                    f"changed from OPEN to CLOSED "
                    f"on {device.name}."
                )

                alert_type = "PORT_CLOSED"

            alert = Alert(

                device_id=device.id,

                alert_type=alert_type,

                message=message,

                is_resolved=False

            )

            db.session.add(alert)

            print(
                f"[PORT ALERT] "
                f"{device.name} | "
                f"Port {port.port_number} | "
                f"{previous_status} -> "
                f"{current_status}"
            )

        else:

            print(
                f"[PORT] "
                f"{device.name} | "
                f"Port {port.port_number} | "
                f"{current_status}"
            )

    db.session.commit()