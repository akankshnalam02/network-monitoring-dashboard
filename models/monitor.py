import subprocess
import platform
import re

def ping_device(ip_address, timeout=2):
    """
    Pings a device once and returns (is_online: bool, latency_ms: float|None)
    """
    param = '-n' if platform.system().lower() == 'windows' else '-c'
    timeout_param = '-w' if platform.system().lower() == 'windows' else '-W'
    timeout_val = str(timeout * 1000) if platform.system().lower() == 'windows' else str(timeout)

    try:
        result = subprocess.run(
            ['ping', param, '1', timeout_param, timeout_val, ip_address],
            capture_output=True, text=True, timeout=timeout + 2
        )
        output = result.stdout

        if 'TTL=' in output or 'ttl=' in output:
            match = re.search(r'time[=<]\s*(\d+(?:\.\d+)?)\s*ms', output, re.IGNORECASE)
            latency = float(match.group(1)) if match else None
            return True, latency
        return False, None
    except (subprocess.TimeoutExpired, Exception):
        return False, None


def check_port(ip_address, port, timeout=1.5):
    """
    Returns True if the TCP port is open, else False.
    """
    import socket
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(timeout)
            result = sock.connect_ex((ip_address, port))
            return result == 0
    except Exception:
        return False