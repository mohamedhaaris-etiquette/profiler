"""
notifications.py
================
WhatsApp notification helpers.

Place this file at:  app/notifications.py

Usage:
    from app.notifications import notify_admin_whatsapp, notify_nearest_staff

    # After saving an Enquiry:
    wa_url = notify_admin_whatsapp(enquiry)
    staff_wa_url = notify_nearest_staff(enquiry)

Settings (add to settings.py if you have WhatsApp Business API):
    WHATSAPP_API_TOKEN  = env('WHATSAPP_API_TOKEN', default='')
    WHATSAPP_PHONE_ID   = env('WHATSAPP_PHONE_ID', default='')
    SUPERADMIN_WHATSAPP = env('SUPERADMIN_WHATSAPP', default='')

Without API credentials the helpers return a wa.me URL that the
server can log or include in a redirect. You can also trigger it
client-side via JavaScript (see landing.html).
"""

import urllib.parse
import logging

logger = logging.getLogger(__name__)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _wa_link(phone: str, message: str) -> str:
    """Build a wa.me click-to-chat URL."""
    clean = phone.replace('+', '').replace(' ', '').replace('-', '')
    if not clean.startswith('91') and len(clean) == 10:
        clean = '91' + clean          # assume India
    return f"https://wa.me/{clean}?text={urllib.parse.quote(message)}"


def _send_via_api(phone: str, message: str) -> bool:
    """
    Send via WhatsApp Cloud API (Meta).
    Returns True on success, False if not configured or failed.
    """
    try:
        from django.conf import settings
        import requests

        token    = getattr(settings, 'WHATSAPP_API_TOKEN', '')
        phone_id = getattr(settings, 'WHATSAPP_PHONE_ID', '')
        if not (token and phone_id):
            return False

        clean = phone.replace('+', '').replace(' ', '').replace('-', '')
        if not clean.startswith('91'):
            clean = '91' + clean

        url = f"https://graph.facebook.com/v18.0/{phone_id}/messages"
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json',
        }
        payload = {
            'messaging_product': 'whatsapp',
            'to': clean,
            'type': 'text',
            'text': {'body': message},
        }
        resp = requests.post(url, json=payload, headers=headers, timeout=8)
        return resp.status_code == 200
    except Exception as exc:
        logger.warning("WhatsApp API send failed: %s", exc)
        return False


# ── Public API ────────────────────────────────────────────────────────────────

def notify_admin_whatsapp(enquiry) -> str:
    """
    Notify the Super Admin (or org owner) about a new enquiry.
    Returns the wa.me URL as fallback (use in JS redirect if desired).
    """
    from .models import CustomUser

    # Prefer the SUPERADMIN_WHATSAPP setting, then first super admin phone.
    from django.conf import settings
    admin_phone = getattr(settings, 'SUPERADMIN_WHATSAPP', '')

    if not admin_phone:
        admin = CustomUser.objects.filter(
            role='super_admin', is_active=True
        ).exclude(phone='').first()
        admin_phone = admin.phone if admin else ''

    if not admin_phone:
        # Fall back to org owner
        members = enquiry.organization.members.filter(
            role='org_admin'
        ).exclude(phone='').first()
        admin_phone = members.phone if members else ''

    if not admin_phone:
        return ''

    svc_name  = enquiry.service.name  if enquiry.service  else '—'
    prod_name = enquiry.product.name  if enquiry.product  else '—'

    message = (
        f"🔔 *New Enquiry — {enquiry.organization.name}*\n\n"
        f"👤 *Name:* {enquiry.name}\n"
        f"📞 *Phone:* {enquiry.phone}\n"
        f"📧 *Email:* {enquiry.email or '—'}\n"
        f"📝 *Subject:* {enquiry.subject}\n"
        f"🛠 *Service:* {svc_name}\n"
        f"📦 *Product:* {prod_name}\n"
        f"💬 *Message:*\n{enquiry.message}\n\n"
        f"⏰ Received at {enquiry.created_at.strftime('%d %b %Y, %I:%M %p')}"
    )

    sent = _send_via_api(admin_phone, message)
    if sent:
        logger.info("WhatsApp admin notification sent for enquiry #%s", enquiry.pk)

    return _wa_link(admin_phone, message)   # always return link as fallback


def notify_nearest_staff(enquiry) -> str:
    """
    When a serviceman is unavailable, find the next available staff in
    the same organization and send them a WhatsApp job notification.

    Returns the wa.me URL of the notified staff (or '' if none found).
    """
    try:
        from .models import StaffAvailability

        # Find available staff in the same org, ordered by last update
        available = StaffAvailability.objects.filter(
            staff__organization=enquiry.organization,
            status='available',
        ).select_related('staff').order_by('updated_at')

        if not available.exists():
            logger.info(
                "No available staff for org %s — cannot auto-notify.",
                enquiry.organization.name
            )
            return ''

        target = available.first()
        wa_num = target.whatsapp or target.staff.phone
        if not wa_num:
            return ''

        message = (
            f"⚡ *New Job Alert — {enquiry.organization.name}*\n\n"
            f"A customer enquiry has been assigned to you because "
            f"another technician is currently unavailable.\n\n"
            f"👤 *Customer:* {enquiry.name}\n"
            f"📞 *Phone:* {enquiry.phone}\n"
            f"📝 *Request:* {enquiry.subject}\n"
            f"💬 {enquiry.message[:200]}\n\n"
            f"Please call the customer at your earliest convenience."
        )

        sent = _send_via_api(wa_num, message)
        if sent:
            logger.info(
                "Auto-assigned enquiry #%s to staff %s",
                enquiry.pk, target.staff.get_full_name()
            )

        return _wa_link(wa_num, message)

    except Exception as exc:
        logger.warning("notify_nearest_staff failed: %s", exc)
        return ''