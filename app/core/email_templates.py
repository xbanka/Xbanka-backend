"""Inline HTML builders for every transactional email.

Everything is emitted as a string rather than a Jinja file so the email bodies
travel with the send call, matching how the invite flow already worked.

Two constraints shape the markup, and both differ from ordinary web CSS:

* **Tables, not divs.** Outlook on Windows renders through the Word engine,
  which ignores `max-width` on a `<div>` — a div-based card spans the whole
  window there. Nested `role="presentation"` tables with a fixed `width` are
  the only layout that holds up across clients.
* **Inlined styles, not a `<style>` block.** Several webmail clients strip
  `<head>` CSS entirely, so every declaration lives in a `style=` attribute.
  `bgcolor` attributes sit alongside `background-color` for the same reason.

Colours are chosen against WCAG AA. #0E9A8E carries only 3.52:1 against white,
which clears the 3:1 bar for large text but not the 4.5:1 one for body copy, so
it is used for the header band and its 24px heading. Anything at normal size
that needs to be readable — button labels, links — uses #0A7C72 instead, which
reaches 5.07:1 both against white and with white on top of it.
"""

from html import escape

BRAND = "#0E9A8E"          # header band, large text only (3.52:1 on white)
BRAND_DARK = "#0A7C72"     # buttons and links (5.07:1 — AA at normal size)
BRAND_TINT = "#E6F4F3"     # callout backgrounds
PAGE_BG = "#F4F6F6"
CARD_BG = "#FFFFFF"
BORDER = "#E5E7EB"
HEADING = "#1A1A1A"
BODY = "#4A4A4A"
MUTED = "#8A8A8A"

FONT = (
    "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, "
    "Helvetica, Arial, sans-serif"
)

SUPPORT_EMAIL = "support@xbankang.com"


def _render(
    *,
    title: str,
    preheader: str,
    heading: str,
    greeting: str,
    paragraphs: list[str],
    cta_label: str,
    cta_url: str,
    notice: str,
    product: str = "Xbanka",
) -> str:
    """Assemble one email from the shared skeleton."""
    safe_url = escape(cta_url, quote=True)

    body_copy = "".join(
        f'<p style="margin:0 0 16px 0; font-family:{FONT}; font-size:16px; '
        f'line-height:24px; color:{BODY};">{paragraph}</p>'
        for paragraph in paragraphs
    )

    return f"""<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
<meta http-equiv="Content-Type" content="text/html; charset=UTF-8" />
<meta name="viewport" content="width=device-width, initial-scale=1.0" />
<meta name="x-apple-disable-message-reformatting" />
<title>{escape(title)}</title>
</head>
<body style="margin:0; padding:0; width:100%; background-color:{PAGE_BG};">

<!-- inbox preview line; hidden in the body itself -->
<div style="display:none; max-height:0; max-width:0; opacity:0; overflow:hidden; mso-hide:all; font-size:1px; line-height:1px; color:{PAGE_BG};">{escape(preheader)}</div>

<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:{PAGE_BG};">
<tr>
<td align="center" style="padding:24px 12px;">

<table role="presentation" width="600" cellpadding="0" cellspacing="0" border="0" style="width:600px; max-width:600px; background-color:{CARD_BG}; border:1px solid {BORDER}; border-radius:12px;">

<!-- header -->
<tr>
<td align="center" bgcolor="{BRAND}" style="background-color:{BRAND}; padding:32px 24px; border-radius:12px 12px 0 0;">
<p style="margin:0 0 6px 0; font-family:{FONT}; font-size:13px; font-weight:bold; letter-spacing:1.5px; text-transform:uppercase; color:#D6EFEC;">{escape(product)}</p>
<h1 style="margin:0; font-family:{FONT}; font-size:24px; line-height:32px; font-weight:bold; color:#FFFFFF;">{escape(heading)}</h1>
</td>
</tr>

<!-- body -->
<tr>
<td style="padding:32px 32px 0 32px;">
<p style="margin:0 0 16px 0; font-family:{FONT}; font-size:16px; line-height:24px; font-weight:bold; color:{HEADING};">{greeting}</p>
{body_copy}
</td>
</tr>

<!-- call to action -->
<tr>
<td align="center" style="padding:8px 32px 24px 32px;">
<table role="presentation" cellpadding="0" cellspacing="0" border="0">
<tr>
<td align="center" bgcolor="{BRAND_DARK}" style="background-color:{BRAND_DARK}; border-radius:8px;">
<a href="{safe_url}" style="display:inline-block; padding:14px 36px; font-family:{FONT}; font-size:16px; font-weight:bold; line-height:20px; color:#FFFFFF; text-decoration:none; border-radius:8px;">{escape(cta_label)}</a>
</td>
</tr>
</table>
</td>
</tr>

<!-- link fallback, for clients that strip the button -->
<tr>
<td style="padding:0 32px 24px 32px;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:{BRAND_TINT}; border-radius:8px;">
<tr>
<td style="padding:16px 20px;">
<p style="margin:0 0 6px 0; font-family:{FONT}; font-size:13px; line-height:18px; color:{BODY};"><strong>Button not working?</strong> Paste this link into your browser:</p>
<p style="margin:0; font-family:{FONT}; font-size:13px; line-height:20px; word-break:break-all;"><a href="{safe_url}" style="color:{BRAND_DARK}; text-decoration:underline;">{escape(cta_url)}</a></p>
</td>
</tr>
</table>
</td>
</tr>

<!-- notice -->
<tr>
<td style="padding:0 32px 32px 32px; border-top:1px solid {BORDER};">
<p style="margin:24px 0 0 0; font-family:{FONT}; font-size:13px; line-height:20px; color:{MUTED};">{notice}</p>
</td>
</tr>

<!-- footer -->
<tr>
<td align="center" style="padding:24px 32px; background-color:#FAFBFB; border-top:1px solid {BORDER}; border-radius:0 0 12px 12px;">
<p style="margin:0 0 6px 0; font-family:{FONT}; font-size:13px; line-height:20px; color:{MUTED};">Need help? Contact us at <a href="mailto:{SUPPORT_EMAIL}" style="color:{BRAND_DARK}; text-decoration:underline;">{SUPPORT_EMAIL}</a></p>
<p style="margin:0; font-family:{FONT}; font-size:12px; line-height:18px; color:{MUTED};">&copy; 2026 Xbanka. All rights reserved.</p>
</td>
</tr>

</table>
</td>
</tr>
</table>
</body>
</html>"""


def _plaintext(
    *,
    heading: str,
    greeting: str,
    paragraphs: list[str],
    cta_label: str,
    cta_url: str,
    notice: str,
) -> str:
    """Plain-text alternative.

    Not optional decoration: an HTML-only message scores worse with spam
    filters, and this is what screen readers and watch previews fall back to.
    """
    lines = [heading, "=" * len(heading), "", greeting, ""]
    lines += [f"{paragraph}\n" for paragraph in paragraphs]
    lines += [f"{cta_label}:", cta_url, "", notice, "", "--", f"Need help? Contact {SUPPORT_EMAIL}", "(c) 2026 Xbanka. All rights reserved."]
    return "\n".join(lines)


def _full_name(first_name: str, last_name: str) -> str:
    name = " ".join(part for part in [first_name, last_name] if part).strip()
    return escape(name) if name else "there"


def verification_email(
    first_name: str, last_name: str, verification_url: str, product: str
) -> tuple[str, str]:
    """(html, text) for the address-verification email."""
    greeting = f"Hello {_full_name(first_name, last_name)},"
    paragraphs = [
        f"Thanks for signing up for {escape(product)}. Confirm this email address "
        "to activate your account and get started.",
    ]
    notice = (
        "This link expires in 24 hours. If you didn't create this account, "
        "you can safely ignore this email."
    )

    html = _render(
        title="Verify Your Email Address",
        preheader="Confirm your email address to activate your account.",
        heading="Verify your email address",
        greeting=greeting,
        paragraphs=paragraphs,
        cta_label="Verify Email Address",
        cta_url=verification_url,
        notice=notice,
        product=product,
    )
    text = _plaintext(
        heading="Verify your email address",
        greeting=f"Hello {' '.join(p for p in [first_name, last_name] if p) or 'there'},",
        paragraphs=[
            f"Thanks for signing up for {product}. Confirm this email address "
            "to activate your account and get started.",
        ],
        cta_label="Verify your email address",
        cta_url=verification_url,
        notice=notice,
    )
    return html, text


def password_reset_email(
    first_name: str, last_name: str, reset_url: str, product: str
) -> tuple[str, str]:
    """(html, text) for the password-reset email."""
    greeting = f"Hello {_full_name(first_name, last_name)},"
    paragraphs = [
        "We received a request to reset the password on your account. "
        "Choose a new one using the button below.",
    ]
    notice = (
        "This link expires in 24 hours. If you didn't request a password reset, "
        "ignore this email — your password will not change."
    )

    html = _render(
        title="Reset Your Password",
        preheader="Reset the password on your Xbanka account.",
        heading="Reset your password",
        greeting=greeting,
        paragraphs=paragraphs,
        cta_label="Reset Password",
        cta_url=reset_url,
        notice=notice,
        product=product,
    )
    text = _plaintext(
        heading="Reset your password",
        greeting=f"Hello {' '.join(p for p in [first_name, last_name] if p) or 'there'},",
        paragraphs=paragraphs,
        cta_label="Reset your password",
        cta_url=reset_url,
        notice=notice,
    )
    return html, text


def staff_invite_email(signup_url: str) -> tuple[str, str]:
    """(html, text) for the ERP staff invitation."""
    paragraphs = [
        "You've been invited to join the Xbanka team as a staff member. "
        "Complete your registration to set up your account and sign in.",
    ]
    notice = (
        "This invitation expires in 24 hours. If you weren't expecting it, "
        "you can safely ignore this email."
    )

    html = _render(
        title="You're Invited to Join Xbanka ERP",
        preheader="Complete your registration to join the Xbanka team.",
        heading="You've been invited",
        greeting="Hello,",
        paragraphs=paragraphs,
        cta_label="Complete Your Signup",
        cta_url=signup_url,
        notice=notice,
        product="Xbanka ERP",
    )
    text = _plaintext(
        heading="You've been invited",
        greeting="Hello,",
        paragraphs=paragraphs,
        cta_label="Complete your signup",
        cta_url=signup_url,
        notice=notice,
    )
    return html, text
