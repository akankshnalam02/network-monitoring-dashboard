from app import app


def authenticated_client():
    client = app.test_client()
    response = client.post(
        "/login",
        data={"username": "admin", "password": "admin"},
    )
    assert response.status_code == 302
    return client


def test_dashboard_requires_login():
    client = app.test_client()
    response = client.get("/")
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_login_rejects_invalid_credentials():
    client = app.test_client()
    response = client.post(
        "/login",
        data={"username": "admin", "password": "wrong"},
    )
    assert response.status_code == 200
    assert b"Invalid username or password" in response.data


def test_authenticated_pages_render():
    client = authenticated_client()
    for path in ["/", "/devices/add", "/ports/add", "/logs", "/reports/logs.csv"]:
        response = client.get(path)
        assert response.status_code == 200, path


def test_unknown_device_detail_returns_not_found():
    client = authenticated_client()
    response = client.get("/devices/999999")
    assert response.status_code == 404


def test_dashboard_search_accepts_inventory_query():
    client = authenticated_client()
    response = client.get("/?q=router")
    assert response.status_code == 200
    assert b"Search devices" in response.data
