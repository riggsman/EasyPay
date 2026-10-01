"""Admin tenant registration with optional logo upload."""
from io import BytesIO

from PIL import Image


def _login(client, username, password):
    r = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _png_bytes(color=(19, 72, 50, 255), size=(64, 64)) -> bytes:
    buf = BytesIO()
    Image.new("RGBA", size, color).save(buf, format="PNG")
    return buf.getvalue()


def test_register_tenant_with_logo(client):
    token = _login(client, "admin", "admin123")
    headers = {"Authorization": f"Bearer {token}"}
    code = f"LOGO{__import__('uuid').uuid4().hex[:6].upper()}"
    files = {"logo": ("tenant-logo.png", _png_bytes(), "image/png")}
    data = {
        "tenant_code": code,
        "organization_name": "Logo Demo Council",
        "organization_type": "COUNCIL",
        "email": "logo-demo@example.com",
        "phone_number": "670111222",
        "currency": "XAF",
        "zone_change_mode": "IMMEDIATE",
    }
    created = client.post("/api/v1/tenants/register", headers=headers, data=data, files=files)
    assert created.status_code == 200, created.text
    body = created.json()
    assert body["tenant_code"] == code
    assert body["logo_path"]
    assert body["logo_path"].startswith("tenants/")

    listing = client.get("/api/v1/tenants", headers=headers)
    assert listing.status_code == 200
    row = next(t for t in listing.json() if t["tenant_id"] == body["tenant_id"])
    assert row["logo_path"]

    logo = client.get(f"/api/v1/tenants/{body['tenant_id']}/logo", headers=headers)
    assert logo.status_code == 200, logo.text
    assert logo.content[:8] == b"\x89PNG\r\n\x1a\n"


def test_register_tenant_without_logo_then_upload(client):
    token = _login(client, "admin", "admin123")
    headers = {"Authorization": f"Bearer {token}"}
    code = f"NOLG{__import__('uuid').uuid4().hex[:6].upper()}"
    created = client.post(
        "/api/v1/tenants/register",
        headers=headers,
        data={
            "tenant_code": code,
            "organization_name": "No Logo Yet",
            "organization_type": "BUSINESS",
            "currency": "XAF",
        },
    )
    assert created.status_code == 200, created.text
    body = created.json()
    assert not body.get("logo_path")

    missing = client.get(f"/api/v1/tenants/{body['tenant_id']}/logo", headers=headers)
    assert missing.status_code == 404

    uploaded = client.post(
        f"/api/v1/tenants/{body['tenant_id']}/logo",
        headers=headers,
        files={"file": ("later.png", _png_bytes((40, 100, 80, 255)), "image/png")},
    )
    assert uploaded.status_code == 200, uploaded.text
    assert uploaded.json()["logo_path"]

    logo = client.get(f"/api/v1/tenants/{body['tenant_id']}/logo", headers=headers)
    assert logo.status_code == 200
    assert logo.content[:8] == b"\x89PNG\r\n\x1a\n"


def test_json_create_tenant_still_works(client):
    token = _login(client, "admin", "admin123")
    headers = {"Authorization": f"Bearer {token}"}
    code = f"JSON{__import__('uuid').uuid4().hex[:6].upper()}"
    created = client.post(
        "/api/v1/tenants",
        headers=headers,
        json={
            "tenant_code": code,
            "organization_name": "JSON Tenant",
            "organization_type": "OTHER",
            "currency": "XAF",
        },
    )
    assert created.status_code == 200, created.text
    assert created.json()["tenant_code"] == code
