"""
notifications.py — Portal Platform
Notification helpers for enquiries: WhatsApp deep-links + email alerts.
Called from views.py public_landing after a new enquiry is submitted.
"""

import urllib.parse
import logging
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)


# ══════════════════════════════════════════════════════════════════════════════
#  WHATSAPP NOTIFICATION
# ══════════════════════════════════════════════════════════════════════════════

def notify_admin_whatsapp(enquiry) -> str:
    """
    Build a WhatsApp deep-link URL that pre-fills a message to the org admin.
    Returns the URL string (empty string if no WhatsApp number available).

    Usage in view:
        wa_url = notify_admin_whatsapp(enquiry)
    """
    org = enquiry.organization

    # Prefer WhatsApp config number → org.whatsapp → org.phone
    wa_cfg = getattr(org, 'whatsapp_config', None)
    number = ''
    if wa_cfg and wa_cfg.is_active and wa_cfg.whatsapp_number:
        number = wa_cfg.whatsapp_number
    elif org.whatsapp:
        number = org.whatsapp
    elif org.phone:
        number = org.phone

    if not number:
        return ''

    # Sanitise number
    number = number.replace('+', '').replace(' ', '').replace('-', '')
    if not number.startswith('91') and len(number) == 10:
        number = '91' + number

    # Build message
    service_line = f'\nService: {enquiry.service.name}' if enquiry.service else ''
    product_line = f'\nProduct: {enquiry.product.name}' if enquiry.product else ''

    msg = (
        f'🔔 New Enquiry — {org.name}\n\n'
        f'From: {enquiry.name}\n'
        f'Phone: {enquiry.phone}\n'
        f'Email: {enquiry.email}\n'
        f'Subject: {enquiry.subject}'
        f'{service_line}{product_line}\n\n'
        f'Message: {enquiry.message[:200]}'
    )

    return f'https://wa.me/{number}?text={urllib.parse.quote(msg)}'


# ══════════════════════════════════════════════════════════════════════════════
#  EMAIL NOTIFICATION TO ORG ADMIN
# ══════════════════════════════════════════════════════════════════════════════

def notify_admin_email(enquiry):
    """
    Send an email notification to the organization's registered email address
    when a new enquiry arrives.
    Silent on failure (logs error).
    """
    org = enquiry.organization

    if not org.email:
        return

    subject = f'[Portal] New Enquiry: {enquiry.subject} — {org.name}'

    service_line = f'\nService:  {enquiry.service.name}' if enquiry.service else ''
    product_line = f'\nProduct:  {enquiry.product.name}' if enquiry.product else ''

    body = (
        f'Hello {org.name},\n\n'
        f'You have received a new enquiry through your Portal listing.\n\n'
        f'━━━━━━━━━━━━━━━━━━━━━━\n'
        f'Customer Details\n'
        f'━━━━━━━━━━━━━━━━━━━━━━\n'
        f'Name:    {enquiry.name}\n'
        f'Phone:   {enquiry.phone}\n'
        f'Email:   {enquiry.email}\n'
        f'Subject: {enquiry.subject}'
        f'{service_line}{product_line}\n\n'
        f'Message:\n{enquiry.message}\n\n'
        f'━━━━━━━━━━━━━━━━━━━━━━\n'
        f'Reply to this customer as soon as possible to improve your response rate.\n\n'
        f'Log in to your dashboard to manage this enquiry:\n'
        f'{getattr(settings, "SITE_URL", "https://yourplatform.com")}/dashboard/enquiries/\n\n'
        f'— Portal Team'
    )

    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@portal.com'),
            recipient_list=[org.email],
            fail_silently=False,
        )
    except Exception as exc:
        logger.error(f'notify_admin_email failed for enquiry #{enquiry.pk}: {exc}')


# ══════════════════════════════════════════════════════════════════════════════
#  STAFF NOTIFICATION (nearest / available staff)
# ══════════════════════════════════════════════════════════════════════════════

def notify_nearest_staff(enquiry):
    """
    Optionally notify staff members who are currently 'available'.
    Uses StaffAvailability if it exists; otherwise silently skips.
    """
    try:
        from .models import CustomUser

        org   = enquiry.organization
        staff = CustomUser.objects.filter(
            organization=org,
            role='staff',
            is_active=True,
        )

        # Try to filter by availability if that model exists
        try:
            from .models import StaffAvailability
            available_ids = StaffAvailability.objects.filter(
                status='available'
            ).values_list('staff_id', flat=True)
            staff = staff.filter(pk__in=available_ids)
        except Exception:
            pass

        for member in staff:
            if not member.phone:
                continue
            number = member.phone.replace('+', '').replace(' ', '').replace('-', '')
            if not number.startswith('91') and len(number) == 10:
                number = '91' + number
            msg = (
                f'📋 New Enquiry for {org.name}\n'
                f'From: {enquiry.name} ({enquiry.phone})\n'
                f'Subject: {enquiry.subject}'
            )
            # WhatsApp link is logged (in production, send via SMS/WhatsApp API)
            wa_url = f'https://wa.me/{number}?text={urllib.parse.quote(msg)}'
            logger.info(f'Staff notification URL for {member.username}: {wa_url}')

    except Exception as exc:
        logger.error(f'notify_nearest_staff failed for enquiry #{enquiry.pk}: {exc}')


# ══════════════════════════════════════════════════════════════════════════════
#  PLAN EXPIRY NOTIFICATION
# ══════════════════════════════════════════════════════════════════════════════

def notify_plan_expiring(org, days_left: int):
    """
    Send a plan-expiry reminder email to the org admin.
    Call this from a management command / cron job.
    """
    if not org.email:
        return

    subject = f'[Portal] Your {org.plan.name if org.plan else "plan"} expires in {days_left} day(s)'

    body = (
        f'Hello {org.name},\n\n'
        f'Your current plan expires in {days_left} day(s) '
        f'on {org.plan_end_date.strftime("%d %B %Y")}.\n\n'
        f'To continue enjoying uninterrupted service, please renew your plan.\n\n'
        f'Log in to renew:\n'
        f'{getattr(settings, "SITE_URL", "https://yourplatform.com")}/dashboard/settings/\n\n'
        f'— Portal Team'
    )

    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@portal.com'),
            recipient_list=[org.email],
            fail_silently=False,
        )
    except Exception as exc:
        logger.error(f'notify_plan_expiring failed for org #{org.pk}: {exc}')