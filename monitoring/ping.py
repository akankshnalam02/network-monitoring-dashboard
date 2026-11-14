import platform
import subprocess
import re


def ping_device(host):

    system = platform.system().lower()

    if system == "windows":
        command = ["ping", "-n", "1", "-w", "2000", host]
    else:
        command = ["ping", "-c", "1", "-W", "2", host]

    try:

        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode != 0:
            return {
                "status": "OFFLINE",
                "latency": None
            }

        output = result.stdout

        latency = None

        if system == "windows":

            match = re.search(
                r"time[=<]\s*(\d+)\s*ms",
                output,
                re.IGNORECASE
            )

        else:

            match = re.search(
                r"time[=]\s*([\d.]+)\s*ms",
                output,
                re.IGNORECASE
            )

        if match:
            latency = float(match.group(1))

        return {
            "status": "ONLINE",
            "latency": latency
        }

    except Exception:

        return {
            "status": "OFFLINE",
            "latency": None
        }