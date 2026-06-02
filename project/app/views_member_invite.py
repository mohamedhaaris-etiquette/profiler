"""
views_member_invite.py
=======================
Step 2 of 7 — Drop this file into your `app/` directory.

Then in views.py, add this import near the top:
    from .views_member_invite import (
        member_send_invite, member_invite_list,
        _award_member_invite_bonus,
    )

And at the bottom of _create_org_and_user_from_onboard (inside onboard_accept),
after invite.save(), call:
    _award_member_invite_bonus(invite)

See onboard_accept_patch.py (file 6) for the exact diff.
"""

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.core.paginator import Paginator
from django.utils import timezone

from .models import (
    InvitationToken, Organization, Plan,
    ReferralBonus, MemberInviteConfig,
)


# ─────────────────────────────────────────────────────────────────────────────
#  SEND INVITE  (org_admin only)
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def member_send_invite(request):
    """
    Any org_admin can invite another business by email.
    On acceptance the inviting org earns OrgPoints.
    """
    user = request.user
    org  = user.organization

    if not org:
        messages.error(request, 'You must be linked to an organisation to send invites.')
        return redirect('dashboard')

    config       = MemberInviteConfig.get_config()
    invite_limit = config.get_limit_for_org(org)

    # Count non-revoked invites this org has sent
    invites_sent = InvitationToken.objects.filter(
        referred_by_org=org
    ).exclude(status='revoked').count()
    invites_left = max(0, invite_limit - invites_sent)

    # Sidebar context
    recent_invites = InvitationToken.objects.filter(
        referred_by_org=org
    ).order_by('-created_at')[:5]

    total_bonus_earned = _get_member_invite_bonus_total(org)

    if request.method == 'POST':
        if not config.allow_member_invites:
            messages.error(request, 'Member invites are currently disabled by the administrator.')
            return redirect('dashboard')

        email          = request.POST.get('email', '').strip().lower()
        personal_msg   = request.POST.get('personal_message', '').strip()

        errors = _validate_member_invite(email, org, invites_left)
        if errors:
            for e in errors:
                messages.error(request, e)
        else:
            trial_plan = Plan.objects.filter(level='trial', is_active=True).first()

            invite = InvitationToken.objects.create(
                invited_by          = user,
                referred_by_org     = org,
                email               = email,
                plan                = trial_plan,
                invite_type         = 'member',
                invite_bonus_points = config.bonus_points_per_invite,
            )
            _send_member_invite_email(invite, request, org, personal_msg)
            messages.success(
                request,
                f'Invitation sent to {email}! '
                f'You\'ll earn {config.bonus_points_per_invite} OrgPoints when they join. 🎉'
            )
            return redirect('member_invite_list')

    return render(request, 'member_send_invite.html', {
        'org':                 org,
        'config':              config,
        'invite_limit':        invite_limit,
        'invites_sent':        invites_sent,
        'invites_left':        invites_left,
        'recent_invites':      recent_invites,
        'total_bonus_earned':  total_bonus_earned,
    })


# ─────────────────────────────────────────────────────────────────────────────
#  INVITE LIST  (org_admin only)
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def member_invite_list(request):
    """All invites sent by this org — status, bonus tracking, pagination."""
    org = request.user.organization
    if not org:
        return redirect('dashboard')

    config = MemberInviteConfig.get_config()

    qs = InvitationToken.objects.filter(
        referred_by_org=org
    ).select_related('organization', 'plan').order_by('-created_at')

    # Optional status filter
    status_filter = request.GET.get('status', '')
    if status_filter:
        qs = qs.filter(status=status_filter)

    paginator = Paginator(qs, 15)
    page      = paginator.get_page(request.GET.get('page'))

    all_invites    = InvitationToken.objects.filter(referred_by_org=org)
    total_sent     = all_invites.count()
    total_accepted = all_invites.filter(status='accepted').count()
    total_pending  = all_invites.filter(status='pending').count()
    total_bonus    = _get_member_invite_bonus_total(org)

    invite_limit = config.get_limit_for_org(org)
    invites_left = max(0, invite_limit - all_invites.exclude(status='revoked').count())

    return render(request, 'member_invite_list.html', {
        'org':            org,
        'config':         config,
        'page_obj':       page,
        'status_filter':  status_filter,
        'status_choices': InvitationToken.STATUS_CHOICES,
        'total_sent':     total_sent,
        'total_accepted': total_accepted,
        'total_pending':  total_pending,
        'total_bonus':    total_bonus,
        'invite_limit':   invite_limit,
        'invites_left':   invites_left,
    })


# ─────────────────────────────────────────────────────────────────────────────
#  RESEND / REVOKE  (org_admin — their own invites only)
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def member_resend_invite(request, pk):
    """Re-send a pending member invite (refreshes expiry)."""
    org    = request.user.organization
    invite = get_object_or_404(InvitationToken, pk=pk, referred_by_org=org)
    if invite.status == 'pending':
        invite.expires_at = timezone.now() + timezone.timedelta(days=7)
        invite.save(update_fields=['expires_at'])
        _send_member_invite_email(invite, request, org)
        messages.success(request, f'Invite resent to {invite.email}.')
    else:
        messages.warning(request, 'Only pending invitations can be resent.')
    return redirect('member_invite_list')


@login_required
def member_revoke_invite(request, pk):
    """Revoke a pending member invite (frees up the quota slot)."""
    org    = request.user.organization
    invite = get_object_or_404(InvitationToken, pk=pk, referred_by_org=org)
    if invite.status == 'pending':
        invite.status = 'revoked'
        invite.save(update_fields=['status'])
        messages.success(request, f'Invite for {invite.email} revoked.')
    else:
        messages.info(request, 'Only pending invitations can be revoked.')
    return redirect('member_invite_list')


# ─────────────────────────────────────────────────────────────────────────────
#  INTERNAL HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _validate_member_invite(email: str, org: Organization, invites_left: int) -> list:
    errors = []
    if not email:
        errors.append('Email address is required.')
        return errors  # no point checking the rest

    if invites_left <= 0:
        errors.append(
            'You have reached your invite limit for your current plan. '
            'Upgrade to send more invitations.'
        )
    if InvitationToken.objects.filter(email=email, status='pending').exists():
        errors.append(f'A pending invitation already exists for {email}.')
    if Organization.objects.filter(email=email).exists():
        errors.append(f'{email} is already a registered member on Portal.')
    return errors


def _get_member_invite_bonus_total(org: Organization) -> int:
    """Sum of OrgPoints earned by this org from member invites."""
    return sum(
        ReferralBonus.objects.filter(
            organization=org,
            note__icontains='member invite'
        ).values_list('points', flat=True)
    ) or 0


def _send_member_invite_email(
    invite: InvitationToken,
    request,
    referrer_org: Organization,
    personal_message: str = '',
):
    """Send the magic-link email for a member invite."""
    onboard_url = invite.get_onboard_url(request)
    subject     = (
        f'{referrer_org.name} has invited you to list your business on Portal!'
    )

    plain = (
        f'Hi,\n\n'
        f'{referrer_org.name} thinks your business deserves an online presence '
        f'and has invited you to join Portal — the free local business directory.\n'
    )
    if personal_message:
        plain += f'\nPersonal note from {referrer_org.name}:\n"{personal_message}"\n'
    plain += (
        f'\nClick the link below to create your free business profile:\n\n'
        f'{onboard_url}\n\n'
        f'This link expires in 7 days.\n\n'
        f'— Portal Team'
    )

    try:
        html_body = render_to_string('member_invitation.html', {
            'invite':           invite,
            'onboard_url':      onboard_url,
            'referrer_org':     referrer_org,
            'personal_message': personal_message,
            'bonus_points':     invite.invite_bonus_points,
        })
    except Exception:
        html_body = None

    send_mail(
        subject        = subject,
        message        = plain,
        from_email     = getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@Portal.com'),
        recipient_list = [invite.email],
        html_message   = html_body,
        fail_silently  = False,
    )


def _award_member_invite_bonus(invite: InvitationToken):
    """
    Called from onboard_accept after the new org is created.
    Awards OrgPoints to the referring org for member invites.
    Safe to call for admin invites — it no-ops if invite_type != 'member'.
    """
    if (
        not invite.referred_by_org
        or invite.bonus_rewarded
        or invite.invite_type != 'member'
        or invite.invite_bonus_points <= 0
    ):
        return

    pts = invite.invite_bonus_points

    ReferralBonus.objects.create(
        organization     = invite.referred_by_org,
        transaction_type = 'earn',
        points           = pts,
        note             = (
            f'Member invite bonus — '
            f'{invite.organization.name if invite.organization else invite.email} '
            f'joined via your invite link'
        ),
    )

    # Mark as rewarded so it can't be double-credited
    InvitationToken.objects.filter(pk=invite.pk).update(bonus_rewarded=True)