def _login(client, username, password):
    r = client.post("/api/v1/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def test_receipt_list_includes_pdf_download_url(client):
    token = _login(client, "admin", "admin123")
    headers = {"Authorization": f"Bearer {token}"}
    res = client.get("/api/v1/receipts?page=1&page_size=5", headers=headers)
    assert res.status_code == 200, res.text
    body = res.json()
    items = body.get("items") or []
    assert items, "expected seeded receipts"
    receipt = items[0]
    assert receipt["pdf_download_url"] == f"/api/v1/receipts/{receipt['receipt_id']}/pdf"


def test_receipt_pdf_download(client):
    token = _login(client, "admin", "admin123")
    headers = {"Authorization": f"Bearer {token}"}
    listing = client.get("/api/v1/receipts?page=1&page_size=1", headers=headers)
    assert listing.status_code == 200, listing.text
    receipt = listing.json()["items"][0]
    pdf = client.get(receipt["pdf_download_url"], headers=headers)
    assert pdf.status_code == 200, pdf.text
    assert pdf.headers.get("content-type", "").startswith("application/pdf")
    assert pdf.content[:4] == b"%PDF"
    assert "attachment" in (pdf.headers.get("content-disposition") or "")
    assert receipt["receipt_number"] in (pdf.headers.get("content-disposition") or "")


def test_payer_can_download_own_receipt_pdf(client):
    token = _login(client, "abctrading", "payer123")
    headers = {"Authorization": f"Bearer {token}"}
    listing = client.get("/api/v1/receipts?page=1&page_size=5", headers=headers)
    assert listing.status_code == 200, listing.text
    items = listing.json().get("items") or []
    assert items, "expected payer receipts"
    receipt = items[0]
    pdf = client.get(f"/api/v1/receipts/{receipt['receipt_id']}/pdf", headers=headers)
    assert pdf.status_code == 200, pdf.text
    assert pdf.content[:4] == b"%PDF"


def test_payment_detail_includes_receipt_pdf_url(client):
    token = _login(client, "admin", "admin123")
    headers = {"Authorization": f"Bearer {token}"}
    payments = client.get("/api/v1/payments?page=1&page_size=20&status=SETTLED", headers=headers)
    assert payments.status_code == 200, payments.text
    items = payments.json().get("items") or payments.json()
    assert items
    txn_id = items[0]["transaction_id"]
    detail = client.get(f"/api/v1/payments/{txn_id}", headers=headers)
    assert detail.status_code == 200, detail.text
    body = detail.json()
    if body.get("receipt_id"):
        assert body.get("receipt_pdf_url") == f"/api/v1/receipts/{body['receipt_id']}/pdf"
