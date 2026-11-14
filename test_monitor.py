from app import app

from models.device import Device

from monitoring.engine import check_device


with app.app_context():

    device = Device.query.first()

    if device is None:

        print("No devices found.")
        print("Add a device from the dashboard first.")

    else:

        result = check_device(device)

        print()
        print("===== MONITORING RESULT =====")
        print("Device:", device.name)
        print("IP:", device.ip_address)
        print("Status:", result["status"])
        print("Latency:", result["latency"])
        print("=============================")