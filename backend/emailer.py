"""emailer.py — Resend email sender for prospect audit + internal notification."""

import os
import base64
import resend

RESEND_API_KEY = os.environ.get("RESEND_API_KEY", "")
FROM_EMAIL = os.environ.get("FROM_EMAIL", "Lumina Clippers <audits@openclawagency.ai>")
REPLY_TO_EMAIL = os.environ.get("REPLY_TO_EMAIL", "rhys@luminaclippers.com")
INTERNAL_NOTIFY_EMAIL = os.environ.get("INTERNAL_NOTIFY_EMAIL", "rhys@luminaclippers.com")
CALENDLY_URL = os.environ.get("CALENDLY_URL", "https://calendly.com/openclawagency/30min")


def _init_resend():
    if not RESEND_API_KEY:
        print("[Emailer] RESEND_API_KEY not set — skipping email")
        return False
    resend.api_key = RESEND_API_KEY
    return True


async def send_prospect_email(to_email: str, first_name: str, pdf_path: str):
    """Email 1 — Send the audit PDF to the prospect."""
    if not _init_resend():
        return

    subject = f"Your Free Lumina Marketing Audit, {first_name}"

    html = f"""
    <div style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; max-width: 600px; margin: 0 auto; background: #0D0D0D; color: #F0F0F0; padding: 40px 30px; border-radius: 8px;">
        <div style="text-align: center; margin-bottom: 30px;">
            <span style="font-size: 24px; font-weight: 700; color: #C9A84C; letter-spacing: 2px;">LUMINA</span>
            <span style="font-size: 14px; color: #999; margin-left: 8px;">CLIPPERS</span>
        </div>

        <h1 style="font-size: 22px; color: #F0F0F0; margin-bottom: 16px;">
            Hey {first_name}, your audit is ready.
        </h1>

        <p style="font-size: 15px; color: #BBBBBB; line-height: 1.6;">
            We've analysed your brand visibility across YouTube, TikTok, Instagram, and X — compared your numbers to your biggest competitor — and identified the gaps costing you views and revenue.
        </p>

        <p style="font-size: 15px; color: #BBBBBB; line-height: 1.6;">
            Your personalised audit is attached to this email as a PDF. Open it, read the numbers, and see exactly what you're leaving on the table.
        </p>

        <div style="text-align: center; margin: 32px 0;">
            <a href="{CALENDLY_URL}" style="display: inline-block; background: #C9A84C; color: #0D0D0D; padding: 14px 32px; border-radius: 6px; font-weight: 700; font-size: 15px; text-decoration: none;">
                Book Your Free Strategy Call
            </a>
        </div>

        <p style="font-size: 13px; color: #666; line-height: 1.5; text-align: center;">
            This call is free, no obligation. We'll walk through your audit together and show you how Lumina can help.
        </p>

        <hr style="border: none; border-top: 1px solid #2A2A2A; margin: 30px 0;">

        <p style="font-size: 11px; color: #555; text-align: center;">
            Lumina Clippers — 62,900+ creators, 18 Billion+ views delivered
        </p>
    </div>
    """

    # Build attachments
    attachments = []
    if pdf_path and os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            pdf_b64 = base64.b64encode(f.read()).decode("utf-8")
        attachments.append({
            "content": pdf_b64,
            "filename": os.path.basename(pdf_path),
        })

    params: resend.Emails.SendParams = {
        "from": FROM_EMAIL,
        "to": [to_email],
        "reply_to": REPLY_TO_EMAIL,
        "subject": subject,
        "html": html,
    }
    if attachments:
        params["attachments"] = attachments

    result = resend.Emails.send(params)
    print(f"[Emailer] Prospect email sent to {to_email} — id: {result.get('id', 'unknown')}")
    return result


async def send_internal_notification(
    name: str, email: str, company: str, industry: str,
    own_revenue: str, competitor: str,
    visibility_score: int, fit_score: int, combined_views: int,
):
    """Email 2 — Internal notification to the Lumina team."""
    if not _init_resend():
        return

    if not INTERNAL_NOTIFY_EMAIL:
        print("[Emailer] No INTERNAL_NOTIFY_EMAIL set — skipping internal notification.")
        return

    subject = f"New Audit — {name} @ {company} | Score: {visibility_score}/100"

    html = f"""
    <div style="font-family: monospace; max-width: 600px; padding: 20px; background: #1A1A1A; color: #F0F0F0; border-radius: 8px;">
        <h2 style="color: #C9A84C;">New Audit Completed</h2>
        <table style="width: 100%; color: #F0F0F0; font-size: 14px;">
            <tr><td style="padding: 4px 8px; color: #999;">Name</td><td style="padding: 4px 8px;">{name}</td></tr>
            <tr><td style="padding: 4px 8px; color: #999;">Email</td><td style="padding: 4px 8px;">{email}</td></tr>
            <tr><td style="padding: 4px 8px; color: #999;">Company</td><td style="padding: 4px 8px;">{company}</td></tr>
            <tr><td style="padding: 4px 8px; color: #999;">Industry</td><td style="padding: 4px 8px;">{industry}</td></tr>
            <tr><td style="padding: 4px 8px; color: #999;">Own Revenue</td><td style="padding: 4px 8px;">{own_revenue}</td></tr>
            <tr><td style="padding: 4px 8px; color: #999;">Competitor</td><td style="padding: 4px 8px;">{competitor}</td></tr>
            <tr><td style="padding: 4px 8px; color: #999;">Visibility Score</td><td style="padding: 4px 8px; color: #C9A84C; font-weight: bold;">{visibility_score}/100</td></tr>
            <tr><td style="padding: 4px 8px; color: #999;">Lumina Fit Score</td><td style="padding: 4px 8px; color: #C9A84C; font-weight: bold;">{fit_score}/100</td></tr>
            <tr><td style="padding: 4px 8px; color: #999;">Combined Views (48h)</td><td style="padding: 4px 8px;">{combined_views:,}</td></tr>
        </table>
    </div>
    """

    params: resend.Emails.SendParams = {
        "from": FROM_EMAIL,
        "to": [INTERNAL_NOTIFY_EMAIL],
        "subject": subject,
        "html": html,
    }

    result = resend.Emails.send(params)
    print(f"[Emailer] Internal notification sent — id: {result.get('id', 'unknown')}")
    return result
