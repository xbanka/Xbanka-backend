def test_dashboard_information(affiliate_client):
    response = affiliate_client.get("/api/dashboard/summary")
    assert response.status_code == 200