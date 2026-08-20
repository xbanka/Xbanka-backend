import pytest

from app.core import email_templates as templates

VERIFY_URL = "https://app.xbankang.com/affiliate/verify?token=abc123"
RESET_URL = "https://erp.xbankang.com/reset-password?token=xyz789"
SIGNUP_URL = "https://erp.xbankang.com/signup?email=new@staff.com"


def _all_emails():
    return [
        templates.verification_email("Joshua", "Oloton", VERIFY_URL, "Xbanka"),
        templates.password_reset_email("Joshua", "Oloton", RESET_URL, "Xbanka ERP"),
        templates.staff_invite_email(SIGNUP_URL),
    ]


@pytest.mark.parametrize("html,text", _all_emails())
def test_every_email_returns_both_parts(html, text):
    """HTML-only mail scores worse with spam filters and breaks screen readers."""
    assert html.startswith("<!DOCTYPE html")
    assert text.strip()


@pytest.mark.parametrize("html,text", _all_emails())
def test_layout_is_table_based(html, text):
    """Outlook's Word engine ignores max-width on divs, so the card must be tables."""
    assert html.count("<table") >= 4
    assert 'role="presentation"' in html


@pytest.mark.parametrize("html,text", _all_emails())
def test_styles_are_inlined_not_in_a_style_block(html, text):
    """Several webmail clients strip <head> CSS entirely."""
    assert "<style" not in html
    assert 'style="' in html


@pytest.mark.parametrize("html,text", _all_emails())
def test_uses_the_brand_palette(html, text):
    assert templates.BRAND in html          # header band
    assert templates.BRAND_DARK in html     # button + links, AA at normal size


@pytest.mark.parametrize(
    "html,text,url",
    [
        (*templates.verification_email("A", "B", VERIFY_URL, "Xbanka"), VERIFY_URL),
        (*templates.password_reset_email("A", "B", RESET_URL, "Xbanka"), RESET_URL),
        (*templates.staff_invite_email(SIGNUP_URL), SIGNUP_URL),
    ],
)
def test_action_url_appears_in_both_parts(html, text, url):
    """Both as the button target and as a copy-pasteable fallback."""
    assert html.count(url) >= 2
    assert url in text


def test_recipient_name_cannot_inject_html():
    html, _ = templates.verification_email(
        "<script>alert(1)</script>", 'O\'Brien "X"', VERIFY_URL, "Xbanka"
    )

    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_missing_name_falls_back_to_a_generic_greeting():
    html, text = templates.verification_email("", "", VERIFY_URL, "Xbanka")

    assert "Hello there," in html
    assert "Hello there," in text


def test_product_name_distinguishes_erp_from_affiliate():
    affiliate, _ = templates.verification_email("A", "B", VERIFY_URL, "Xbanka")
    erp, _ = templates.verification_email("A", "B", VERIFY_URL, "Xbanka ERP")

    assert "Xbanka ERP" in erp
    assert "Xbanka ERP" not in affiliate
