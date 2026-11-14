import csv
import io
import os
from datetime import datetime, timedelta
from functools import wraps

from apscheduler.schedulers.background import BackgroundScheduler
from flask import Flask, Response, abort, flash, redirect, render_template, request, session, url_for
from sqlalchemy import inspect, or_, text

from models.alert import Alert
from models.database import db
from models.device import Device
from models.monitoring_log import MonitoringLog
from models.port import Port
from monitoring.engine import check_device
from monitoring.port_monitor import get_service_name, monitor_device_ports

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "network-monitor-dev-key")
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///network_monitor.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["ADMIN_USERNAME"] = os.getenv("ADMIN_USERNAME", "admin")
app.config["ADMIN_PASSWORD"] = os.getenv("ADMIN_PASSWORD", "admin")
app.config["LATENCY_THRESHOLD"] = int(os.getenv("LATENCY_THRESHOLD", "200"))
db.init_app(app)


def initialize_database():
    with app.app_context():
        db.create_all()
        inspector = inspect(db.engine)
        if "devices" not in inspector.get_table_names():
            return
        columns = {column["name"] for column in inspector.get_columns("devices")}
        migrations = {
            "status": "ALTER TABLE devices ADD COLUMN status VARCHAR(20) DEFAULT 'UNKNOWN'",
            "monitoring_enabled": "ALTER TABLE devices ADD COLUMN monitoring_enabled BOOLEAN DEFAULT 1",
            "description": "ALTER TABLE devices ADD COLUMN description TEXT",
        }
        for column, statement in migrations.items():
            if column not in columns:
                db.session.execute(text(statement))
        db.session.execute(text("UPDATE devices SET status = 'UNKNOWN' WHERE status IS NULL"))
        db.session.commit()


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("authenticated"):
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped_view


def find_or_404(model, record_id):
    record = db.session.get(model, record_id)
    if record is None:
        abort(404)
    return record


@app.context_processor
def inject_layout_data():
    return {"authenticated": session.get("authenticated", False)}


@app.template_filter("datetime")
def format_datetime(value):
    return value.strftime("%d %b %Y, %H:%M") if value else "Never"


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        valid_credentials = (
            request.form.get("username") == app.config["ADMIN_USERNAME"]
            and request.form.get("password") == app.config["ADMIN_PASSWORD"]
        )
        if valid_credentials:
            session["authenticated"] = True
            return redirect(request.args.get("next") or url_for("dashboard"))
        flash("Invalid username or password.", "danger")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


def monitor_device(device):
    result = check_device(device)
    monitor_device_ports(device)
    if result["latency"] is not None and result["latency"] > app.config["LATENCY_THRESHOLD"]:
        recent_warning = Alert.query.filter_by(
            device_id=device.id, alert_type="HIGH_LATENCY"
        ).order_by(Alert.created_at.desc()).first()
        warning_is_new = (
            not recent_warning
            or recent_warning.created_at < datetime.utcnow() - timedelta(minutes=5)
        )
        if warning_is_new:
            db.session.add(Alert(
                device_id=device.id,
                alert_type="HIGH_LATENCY",
                message=(f"{device.name} latency is {result['latency']} ms "
                         f"(threshold: {app.config['LATENCY_THRESHOLD']} ms)."),
            ))
            db.session.commit()
    return result


def monitor_all_devices():
    with app.app_context():
        for device in Device.query.filter_by(monitoring_enabled=True).all():
            try:
                monitor_device(device)
            except Exception as error:
                app.logger.error("Monitoring failed for %s: %s", device.name, error)


@app.route("/")
@login_required
def dashboard():
    all_devices = Device.query.order_by(Device.name).all()
    search = request.args.get("q", "").strip()
    device_query = Device.query
    if search:
        pattern = f"%{search}%"
        device_query = device_query.filter(or_(
            Device.name.ilike(pattern),
            Device.ip_address.ilike(pattern),
            Device.device_type.ilike(pattern),
        ))
    devices = device_query.order_by(Device.name).all()
    recent_alerts = Alert.query.order_by(Alert.created_at.desc()).limit(10).all()
    recent_logs = MonitoringLog.query.order_by(MonitoringLog.checked_at.desc()).limit(12).all()
    latencies = [
        device.latest_log.latency for device in all_devices
        if device.latest_log and device.latest_log.latency is not None
    ]
    status_counts = {"ONLINE": 0, "OFFLINE": 0, "UNKNOWN": 0}
    for device in all_devices:
        status_counts[device.latest_status] = status_counts.get(device.latest_status, 0) + 1
    chart_logs = MonitoringLog.query.order_by(MonitoringLog.checked_at.asc()).limit(60).all()
    chart_data = [
        {"time": log.checked_at.strftime("%H:%M"), "latency": log.latency, "device": log.device.name}
        for log in chart_logs if log.latency is not None
    ]
    return render_template(
        "dashboard.html",
        devices=devices,
        all_devices=all_devices,
        recent_alerts=recent_alerts,
        recent_logs=recent_logs,
        online_count=status_counts["ONLINE"],
        offline_count=status_counts["OFFLINE"],
        unknown_count=status_counts["UNKNOWN"],
        average_latency=round(sum(latencies) / len(latencies), 2) if latencies else 0,
        chart_data=chart_data,
        latency_threshold=app.config["LATENCY_THRESHOLD"],
        search=search,
    )


@app.route("/devices/<int:device_id>")
@login_required
def device_detail(device_id):
    device = find_or_404(Device, device_id)
    logs = (MonitoringLog.query.filter_by(device_id=device.id)
            .order_by(MonitoringLog.checked_at.desc()).limit(100).all())
    alerts = (Alert.query.filter_by(device_id=device.id)
              .order_by(Alert.created_at.desc()).limit(10).all())
    return render_template("device_detail.html", device=device, logs=logs,
                           alerts=alerts, latency_threshold=app.config["LATENCY_THRESHOLD"])


def device_form_values(device=None):
    return {
        "name": request.form.get("name", device.name if device else ""),
        "ip_address": request.form.get("ip_address", device.ip_address if device else ""),
        "device_type": request.form.get("device_type", device.device_type if device else "Other"),
        "description": request.form.get("description", device.description if device else ""),
    }


@app.route("/devices/add", methods=["GET", "POST"])
@login_required
def add_device():
    values = device_form_values()
    if request.method == "POST":
        if not values["name"].strip() or not values["ip_address"].strip():
            flash("Name and IP address are required.", "danger")
            return render_template("device_form.html", device=None, values=values)
        db.session.add(Device(**values, status="UNKNOWN", monitoring_enabled=True))
        db.session.commit()
        flash("Device added. Run a check to get its current status.", "success")
        return redirect(url_for("dashboard"))
    return render_template("device_form.html", device=None, values=values)


@app.route("/devices/<int:device_id>/edit", methods=["GET", "POST"])
@login_required
def edit_device(device_id):
    device = find_or_404(Device, device_id)
    values = device_form_values(device)
    if request.method == "POST":
        if not values["name"].strip() or not values["ip_address"].strip():
            flash("Name and IP address are required.", "danger")
        else:
            for key, value in values.items():
                setattr(device, key, value)
            db.session.commit()
            flash("Device updated.", "success")
            return redirect(url_for("dashboard"))
    return render_template("device_form.html", device=device, values=values)


@app.post("/devices/<int:device_id>/delete")
@login_required
def delete_device(device_id):
    db.session.delete(find_or_404(Device, device_id))
    db.session.commit()
    flash("Device and its monitoring history were deleted.", "success")
    return redirect(url_for("dashboard"))


@app.post("/devices/<int:device_id>/toggle")
@login_required
def toggle_device(device_id):
    device = find_or_404(Device, device_id)
    device.monitoring_enabled = not device.monitoring_enabled
    db.session.commit()
    return redirect(url_for("dashboard"))


@app.post("/devices/<int:device_id>/check")
@login_required
def check_device_now(device_id):
    device = find_or_404(Device, device_id)
    monitor_device(device)
    flash(f"{device.name} checked: {device.latest_status}.", "success")
    return redirect(url_for("dashboard"))


@app.route("/ports/add", methods=["GET", "POST"])
@login_required
def add_port():
    devices = Device.query.order_by(Device.name).all()
    if request.method == "POST":
        try:
            port_number = int(request.form.get("port_number", ""))
        except ValueError:
            port_number = 0
        device_id = request.form.get("device_id")
        if not device_id or not 1 <= port_number <= 65535:
            flash("Choose a device and enter a port from 1 to 65535.", "danger")
        elif Port.query.filter_by(device_id=device_id, port_number=port_number).first():
            flash("That port is already being monitored for this device.", "danger")
        else:
            service_name = request.form.get("service_name", "").strip() or get_service_name(port_number)
            db.session.add(Port(device_id=device_id, port_number=port_number,
                                service_name=service_name, status="UNKNOWN"))
            db.session.commit()
            flash("Port monitoring added.", "success")
            return redirect(url_for("dashboard"))
    return render_template("port_form.html", devices=devices)


@app.post("/ports/delete/<int:port_id>")
@login_required
def delete_port(port_id):
    db.session.delete(find_or_404(Port, port_id))
    db.session.commit()
    return redirect(url_for("dashboard"))


@app.route("/logs")
@login_required
def logs():
    selected_device = request.args.get("device_id", type=int)
    query = MonitoringLog.query.order_by(MonitoringLog.checked_at.desc())
    if selected_device:
        query = query.filter_by(device_id=selected_device)
    return render_template("logs.html", logs=query.limit(200).all(),
                           devices=Device.query.order_by(Device.name).all(),
                           selected_device=selected_device)


@app.post("/alerts/<int:alert_id>/resolve")
@login_required
def resolve_alert(alert_id):
    alert = find_or_404(Alert, alert_id)
    alert.is_resolved = True
    db.session.commit()
    return redirect(request.referrer or url_for("dashboard"))


@app.get("/reports/logs.csv")
@login_required
def export_logs():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Device", "IP address", "Status", "Latency (ms)", "Checked at"])
    for log in MonitoringLog.query.order_by(MonitoringLog.checked_at.desc()).all():
        writer.writerow([log.device.name, log.device.ip_address, log.status,
                         log.latency if log.latency is not None else "", log.checked_at.isoformat()])
    return Response(output.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=monitoring-logs.csv"})


if __name__ == "__main__":
    initialize_database()
    scheduler = BackgroundScheduler(daemon=True)
    scheduler.add_job(monitor_all_devices, "interval", seconds=30,
                       id="network_monitor", replace_existing=True)
    scheduler.start()
    try:
        app.run(host="127.0.0.1", port=5000, debug=False)
    finally:
        scheduler.shutdown(wait=False)
