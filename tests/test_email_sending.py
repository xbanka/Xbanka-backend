import asyncio

import pytest
from fastapi import BackgroundTasks, HTTPException

from app.core import email
from app.core.enums import EmailTypeEnum


@pytest.fixture
def sent(mocker):
    """Capture the params handed to Resend, without touching the network."""
    calls = []
    mocker.patch.object(
        email.resend.Emails,
        "send",
        side_effect=lambda params: calls.append(params) or {"id": "re_test"},
    )
    return calls


def _run(coroutine):
    """Drive a coroutine to completion.

    The suite has no async plugin installed, so `async def test_*` functions are
    skipped rather than run. These stay sync and pump the loop by hand.
    """
    return asyncio.run(coroutine)


def test_invite_sends_the_signup_url_and_correct_subject(sent):
    """Regression: this used to send the body 'Hi there' under the subject
    'Reset Your Password', so invited staff never received a usable link."""
    background_tasks = BackgroundTasks()

    _run(
        email.send_invite_email(
            recipient="new@staff.com",
            signup_url="https://erp.xbankang.com/signup?email=new@staff.com",
            background_tasks=background_tasks,
        )
    )
    _run(background_tasks())

    (params,) = sent
    assert params["subject"] == "You're Invited to Join Xbanka ERP"
    assert "signup?email=new@staff.com" in params["html"]
    assert "Hi there" not in params["html"]


def test_send_is_deferred_to_a_background_task(sent):
    """resend.Emails.send blocks; sending inline would stall the event loop."""
    background_tasks = BackgroundTasks()

    _run(
        email.send_invite_email(
            recipient="new@staff.com",
            signup_url="https://erp.xbankang.com/signup",
            background_tasks=background_tasks,
        )
    )

    assert len(background_tasks.tasks) == 1
    assert sent == []  # nothing sent until the task runs

    _run(background_tasks())
    assert len(sent) == 1


@pytest.mark.parametrize(
    "email_type,expected_product",
    [(EmailTypeEnum.affiliate, "Xbanka"), (EmailTypeEnum.erp, "Xbanka ERP")],
)
def test_verification_uses_the_right_product_name(sent, email_type, expected_product):
    background_tasks = BackgroundTasks()

    _run(
        email.send_verification_email(
            recipient="user@example.com",
            email_type=email_type,
            first_name="Joshua",
            last_name="Oloton",
            verification_url="https://app.xbankang.com/verify?token=t",
            background_tasks=background_tasks,
        )
    )
    _run(background_tasks())

    (params,) = sent
    assert params["subject"] == "Verify Your Email Address"
    assert expected_product in params["html"]


def test_password_reset_sends_both_parts(sent):
    background_tasks = BackgroundTasks()

    _run(
        email.send_forgot_password_email(
            recipient="user@example.com",
            email_type=EmailTypeEnum.erp,
            first_name="Joshua",
            last_name="Oloton",
            reset_url="https://erp.xbankang.com/reset-password?token=t",
            background_tasks=background_tasks,
        )
    )
    _run(background_tasks())

    (params,) = sent
    assert params["subject"] == "Reset Your Password"
    assert params["html"].startswith("<!DOCTYPE html")
    assert params["text"].strip()
    assert params["from"] == email.RESEND_FROM


def test_upstream_failure_does_not_propagate(sent, mocker):
    """The response has already been returned by the time this runs, so a
    delivery failure must be logged rather than raised."""
    mocker.patch.object(
        email.resend.Emails, "send", side_effect=RuntimeError("resend is down")
    )
    background_tasks = BackgroundTasks()

    _run(
        email.send_invite_email(
            recipient="new@staff.com",
            signup_url="https://erp.xbankang.com/signup",
            background_tasks=background_tasks,
        )
    )

    _run(background_tasks())  # must not raise


def test_unknown_email_type_is_rejected():
    with pytest.raises(HTTPException) as exc:
        email._resolve_frontend_url("not-a-type")

    assert exc.value.status_code == 500
