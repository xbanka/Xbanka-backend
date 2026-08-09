from uuid import uuid4

import pytest

from app.core.enums import PayoutStatusEnum, ServiceTypeEnum
from app.models.customer import Customer
from app.models.payouts import Payout
from app.models.transactions import Transaction


@pytest.fixture
def affiliate_customer(db_session, verified_affiliate):
    customer = Customer(
        first_name="Jane",
        last_name="Doe",
        email="jane.doe@example.com",
        affiliate_id=verified_affiliate.id,
    )
    db_session.add(customer)
    db_session.commit()
    db_session.refresh(customer)
    return customer


def _make_transaction(db_session, customer, amount_in, commission_rate=10):
    txn = Transaction(
        txn_id=f"TXN-{uuid4().hex[:10]}",
        service_type=ServiceTypeEnum.crypto,
        amount_in=amount_in,
        commission_rate=commission_rate,
        vendor="TestVendor",
        customer_id=customer.id,
    )
    db_session.add(txn)
    db_session.commit()
    db_session.refresh(txn)
    return txn


def _make_paid_payout(db_session, affiliate_id, amount):
    payout = Payout(
        amount=amount,
        status=PayoutStatusEnum.paid,
        bank="Test Bank",
        affiliate_id=affiliate_id,
    )
    db_session.add(payout)
    db_session.commit()
    return payout


def test_create_payout_success(
    affiliate_client, db_session, verified_affiliate, affiliate_customer
):
    # amount_in=1000, commission_rate=10% -> earnings = 100
    _make_transaction(db_session, affiliate_customer, amount_in=1000)

    response = affiliate_client.post(
        "/api/affiliates/payout", json={"amount": 50, "bank": "Test Bank"}
    )

    assert response.status_code == 201
    body = response.json()
    assert body["payout"]["amount"] == 50
    assert body["payout"]["bank"] == "Test Bank"

    payout = (
        db_session.query(Payout)
        .filter(Payout.affiliate_id == verified_affiliate.id)
        .first()
    )
    assert payout is not None
    assert float(payout.amount) == 50


def test_create_payout_rejects_zero_amount(
    affiliate_client, db_session, affiliate_customer
):
    _make_transaction(db_session, affiliate_customer, amount_in=1000)

    response = affiliate_client.post(
        "/api/affiliates/payout", json={"amount": 0, "bank": "Test Bank"}
    )

    assert response.status_code == 400
    assert "greater than zero" in response.json()["detail"]


def test_create_payout_rejects_negative_amount(
    affiliate_client, db_session, affiliate_customer
):
    _make_transaction(db_session, affiliate_customer, amount_in=1000)

    response = affiliate_client.post(
        "/api/affiliates/payout", json={"amount": -10, "bank": "Test Bank"}
    )

    assert response.status_code == 400
    assert "greater than zero" in response.json()["detail"]


def test_create_payout_rejects_amount_over_available_balance(
    affiliate_client, db_session, affiliate_customer
):
    # earnings = 100
    _make_transaction(db_session, affiliate_customer, amount_in=1000)

    response = affiliate_client.post(
        "/api/affiliates/payout", json={"amount": 150, "bank": "Test Bank"}
    )

    assert response.status_code == 400
    assert "insufficient" in response.json()["detail"].lower()


def test_create_payout_accounts_for_previous_paid_payouts(
    affiliate_client, db_session, verified_affiliate, affiliate_customer
):
    # earnings = 100, 60 already paid out -> available balance = 40
    _make_transaction(db_session, affiliate_customer, amount_in=1000)
    _make_paid_payout(db_session, verified_affiliate.id, amount=60)

    over_balance = affiliate_client.post(
        "/api/affiliates/payout", json={"amount": 41, "bank": "Test Bank"}
    )
    assert over_balance.status_code == 400
    assert "insufficient" in over_balance.json()["detail"].lower()

    at_balance = affiliate_client.post(
        "/api/affiliates/payout", json={"amount": 40, "bank": "Test Bank"}
    )
    assert at_balance.status_code == 201


def test_create_payout_parses_comma_formatted_string_amount(
    affiliate_client, db_session, affiliate_customer
):
    # earnings = 1000
    _make_transaction(db_session, affiliate_customer, amount_in=10000)

    response = affiliate_client.post(
        "/api/affiliates/payout", json={"amount": "1,000.00", "bank": "Test Bank"}
    )

    assert response.status_code == 201
    assert response.json()["payout"]["amount"] == 1000.0


def test_create_payout_with_no_earnings_rejected(affiliate_client):
    response = affiliate_client.post(
        "/api/affiliates/payout", json={"amount": 10, "bank": "Test Bank"}
    )

    assert response.status_code == 400
    assert "insufficient" in response.json()["detail"].lower()
