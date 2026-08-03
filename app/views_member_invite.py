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
from django.core.paginator import Paginator
from django.db import transaction
from django.http import JsonResponse
from django.utils import timezone

from .models import (
    InvitationToken, Organization, Plan,
    Referral, ReferralBonus, MemberInviteConfig,
)
from .utils import normalize_indian_phone


# ─────────────────────────────────────────────────────────────────────────────
#  SEND INVITE  (org_admin only)
# ─────────────────────────────────────────────────────────────────────────────

@login_required
def member_send_invite(request):
    """
    An org admin creates a phone-bound invitation and shares it only through
    WhatsApp. Rewards remain locked until super-admin approval.
    """
    user = request.user
    org  = user.organization

    if not org or not user.is_org_admin or not org.is_active or org.status != 'active':
        messages.error(request, 'Only an active business administrator can send invites.')
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
    approved_invites = InvitationToken.objects.filter(
        referred_by_org=org,
        approval_status='approved',
    ).count()

    if request.method == 'POST':
        if not config.allow_member_invites:
            messages.error(request, 'Member invites are currently disabled by the administrator.')
            return redirect('dashboard')

        raw_phone      = request.POST.get('phone', '').strip()
        business_name  = request.POST.get('business_name', '').strip()
        personal_msg   = request.POST.get('personal_message', '').strip()

        errors, phone = _validate_member_invite(raw_phone, org, invites_left)
        if errors:
            for e in errors:
                messages.error(request, e)
        else:
            trial_plan = Plan.objects.filter(level='trial', is_active=True).first()

            invite = InvitationToken.objects.create(
                invited_by          = user,
                referred_by_org     = org,
                email               = '',
                phone               = phone,
                plan                = trial_plan,
                invite_type         = 'member',
                delivery_channel    = 'whatsapp',
                invite_bonus_points = config.bonus_points_per_invite,
                site_title          = business_name,
            )
            whatsapp_url = invite.get_whatsapp_share_url(request, personal_msg)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'ok': True,
                    'invite_id': invite.pk,
                    'whatsapp_url': whatsapp_url,
                    'message': (
                        'Invitation created. The reward will be released only '
                        'after super-admin approval.'
                    ),
                })
            messages.success(
                request,
                'WhatsApp invitation created. '
                f'{config.bonus_points_per_invite} OrgPoints will unlock after approval.'
            )
            return redirect(whatsapp_url)

    return render(request, 'member_send_invite.html', {
        'org':                 org,
        'config':              config,
        'invite_limit':        invite_limit,
        'invites_sent':        invites_sent,
        'invites_left':        invites_left,
        'recent_invites':      recent_invites,
        'total_bonus_earned':  total_bonus_earned,
        'approved_invites':    approved_invites,
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
    total_accepted = all_invites.filter(approval_status='approved').count()
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
    """Open WhatsApp again for a pending member invite."""
    org    = request.user.organization
    invite = get_object_or_404(InvitationToken, pk=pk, referred_by_org=org)
    if invite.status == 'pending':
        invite.expires_at = timezone.now() + timezone.timedelta(days=7)
        invite.save(update_fields=['expires_at'])
        return redirect(invite.get_whatsapp_share_url(request))
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
        messages.success(request, f'Invite for +{invite.phone} revoked.')
    else:
        messages.info(request, 'Only pending invitations can be revoked.')
    return redirect('member_invite_list')


# ─────────────────────────────────────────────────────────────────────────────
#  INTERNAL HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def _validate_member_invite(raw_phone: str, org: Organization, invites_left: int):
    errors = []
    try:
        phone = normalize_indian_phone(raw_phone)
    except ValueError as exc:
        return [str(exc)], ''

    if invites_left <= 0:
        errors.append(
            'You have reached your invite limit for your current plan. '
            'Upgrade to send more invitations.'
        )
    if InvitationToken.objects.filter(phone=phone).filter(
        status__in=['pending', 'accepted'],
        approval_status__in=['pending_review', 'approved'],
    ).exists():
        errors.append('An invitation or registration already exists for this mobile number.')
    if Organization.objects.filter(phone__endswith=phone[-10:]).exists():
        errors.append('This mobile number is already registered on Portal.')
    if org.phone and ''.join(ch for ch in org.phone if ch.isdigit()).endswith(phone[-10:]):
        errors.append('You cannot invite your own business mobile number.')
    return errors, phone


def _get_member_invite_bonus_total(org: Organization) -> int:
    """Sum of OrgPoints earned by this org from member invites."""
    return sum(
        ReferralBonus.objects.filter(
            organization=org,
            note__icontains='member invite'
        ).values_list('points', flat=True)
    ) or 0


def _award_member_invite_bonus(invite: InvitationToken):
    """
    Release a referral reward exactly once, and only after approval.

    The row lock plus the one-to-one ``source_invitation`` database constraint
    prevents two concurrent approval requests from double-crediting points.
    """
    with transaction.atomic():
        locked = InvitationToken.objects.select_for_update().select_related(
            'referred_by_org', 'organization', 'referral_code'
        ).get(pk=invite.pk)
        if (
            not locked.referred_by_org
            or locked.bonus_rewarded
            or locked.invite_type != 'member'
            or locked.invite_bonus_points <= 0
            or locked.approval_status != 'approved'
        ):
            return False

        referral = Referral.objects.filter(
            referrer=locked.referred_by_org,
            referred=locked.organization,
        ).first()
        if not referral:
            referral = Referral.objects.create(
                referrer=locked.referred_by_org,
                referred=locked.organization,
                code=locked.referral_code,
                status='pending',
            )
        referral.status = 'rewarded'
        referral.points_awarded = locked.invite_bonus_points
        referral.confirmed_at = timezone.now()
        referral.save(update_fields=['status', 'points_awarded', 'confirmed_at'])

        _, created = ReferralBonus.objects.get_or_create(
            source_invitation=locked,
            defaults={
                'organization': locked.referred_by_org,
                'referral': referral,
                'transaction_type': 'earn',
                'points': locked.invite_bonus_points,
                'note': (
                    'Member invite bonus — '
                    f'{locked.organization.name if locked.organization else locked.phone} '
                    'approved by the super admin'
                ),
            },
        )
        if not locked.bonus_rewarded:
            locked.bonus_rewarded = True
            locked.save(update_fields=['bonus_rewarded'])
        return created


