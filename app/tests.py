import json
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import (
    BusinessCategory,
    BusinessFeature,
    CustomUser,
    DealerLocation,
    FAQItem,
    HeroSlide,
    InvitationToken,
    LandingPageConfig,
    MemberInviteConfig,
    Organization,
    PaymentQR,
    Plan,
    PromoBanner,
    Product,
    ReferralBonus,
    Service,
    SuccessStory,
)
from .views_member_invite import _award_member_invite_bonus


@override_settings(ALLOWED_HOSTS=['testserver'])
class SuperAdminSetupTests(TestCase):
    def registration_data(self, suffix='one'):
        return {
            'first_name': 'Platform',
            'last_name': 'Admin',
            'phone': '9000000010',
            'username': f'platform-{suffix}',
            'email': f'platform-{suffix}@example.com',
            'password1': 'StrongPass!482',
            'password2': 'StrongPass!482',
        }

    def test_first_super_admin_can_be_created_publicly(self):
        response = self.client.get(reverse('register_super_admin'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'First-time setup')

        response = self.client.post(
            reverse('register_super_admin'),
            self.registration_data(),
        )
        self.assertRedirects(response, reverse('dashboard'))
        user = CustomUser.objects.get(username='platform-one')
        self.assertEqual(user.role, 'super_admin')
        self.assertTrue(user.is_staff)

    def test_existing_super_admin_shows_locked_page_to_org_admin(self):
        CustomUser.objects.create_user(
            username='existing-root',
            password='StrongPass!482',
            role='super_admin',
            is_staff=True,
        )
        org_admin = CustomUser.objects.create_user(
            username='business-owner',
            password='StrongPass!482',
            role='org_admin',
        )
        self.client.force_login(org_admin)

        response = self.client.get(reverse('register_super_admin'))
        self.assertEqual(response.status_code, 403)
        self.assertContains(
            response,
            'Super Admin setup is complete',
            status_code=403,
        )
        self.assertContains(
            response,
            'Sign Out &amp; Switch Account',
            status_code=403,
        )

    def test_existing_super_admin_can_create_another(self):
        existing = CustomUser.objects.create_user(
            username='existing-root',
            password='StrongPass!482',
            role='super_admin',
            is_staff=True,
        )
        self.client.force_login(existing)
        response = self.client.post(
            reverse('register_super_admin'),
            self.registration_data('two'),
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, reverse('member_list'))
        self.assertTrue(CustomUser.objects.filter(
            username='platform-two',
            role='super_admin',
            is_staff=True,
        ).exists())


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    ALLOWED_HOSTS=['testserver'],
)
class ApprovalAndReferralTests(TestCase):
    def setUp(self):
        self.plan = Plan.objects.create(
            name='Starter',
            level='trial',
            price=99,
            duration_days=30,
            max_invites=5,
            max_hero_slides=3,
            max_promos=3,
        )
        MemberInviteConfig.objects.create(
            pk=1,
            bonus_points_per_invite=50,
            max_invites_trial=5,
        )
        self.super_admin = CustomUser.objects.create_user(
            username='rootadmin',
            email='root@example.com',
            password='StrongPass!482',
            role='super_admin',
            is_staff=True,
        )

    def make_org(self, name, phone, username):
        org = Organization.objects.create(
            name=name,
            plan=self.plan,
            status='active',
            is_active=True,
            email=f'{username}@example.com',
            phone=phone,
            whatsapp=phone,
            address_line1='1 Main Road',
            city='Chennai',
            state='Tamil Nadu',
            pincode='600001',
        )
        user = CustomUser.objects.create_user(
            username=username,
            email=f'{username}@example.com',
            password='StrongPass!482',
            organization=org,
            role='org_admin',
        )
        return org, user

    def test_direct_signup_waits_for_super_admin(self):
        response = self.client.post(reverse('signup'), {
            'first_name': 'New',
            'last_name': 'Owner',
            'username': 'newowner',
            'user_email': 'newowner@example.com',
            'user_phone': '9876543210',
            'password1': 'StrongPass!482',
            'password2': 'StrongPass!482',
            'name': 'New Electricals',
            'email': 'contact@newelectricals.example',
            'phone': '9876543210',
            'whatsapp': '9876543210',
            'address_line1': '2 Market Road',
            'city': 'Chennai',
            'state': 'Tamil Nadu',
            'pincode': '600002',
            'working_hours': 'Mon-Sat: 9 AM - 6 PM',
        })

        org = Organization.objects.get(name='New Electricals')
        user = CustomUser.objects.get(username='newowner')
        invite = InvitationToken.objects.get(organization=org)
        self.assertRedirects(
            response,
            reverse('onboard_pending_review', args=[invite.token]),
        )
        self.assertEqual(org.status, 'pending_approval')
        self.assertFalse(org.is_active)
        self.assertFalse(user.is_active)
        self.assertEqual(invite.invite_type, 'direct')
        self.assertEqual(invite.approval_status, 'pending_review')
        self.assertEqual(ReferralBonus.objects.count(), 0)

    def test_whatsapp_invite_rewards_only_after_approval(self):
        referrer, referrer_admin = self.make_org(
            'Referrer Electricals', '9000000001', 'referrer'
        )
        self.client.force_login(referrer_admin)
        response = self.client.post(
            reverse('member_send_invite'),
            {
                'phone': '9000000002',
                'business_name': 'Friend Mechanics',
                'personal_message': 'Try this for your workshop.',
            },
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['whatsapp_url'].startswith('https://wa.me/919000000002'))

        invite = InvitationToken.objects.get(referred_by_org=referrer)
        self.assertEqual(invite.delivery_channel, 'whatsapp')
        self.assertEqual(invite.email, '')
        self.assertEqual(ReferralBonus.objects.count(), 0)

        self.client.logout()
        response = self.client.post(reverse('onboard_accept', args=[invite.token]), {
            'company_name': 'Friend Mechanics',
            'contact_name': 'Friend Owner',
            'email': 'friend@example.com',
            'mobile': '9000000002',
            'whatsapp': '9000000002',
            'address': '3 Workshop Street',
            'city': 'Chennai',
            'state': 'Tamil Nadu',
            'pincode': '600003',
            'password': 'StrongPass!482',
            'password2': 'StrongPass!482',
        })
        self.assertRedirects(
            response,
            reverse('onboard_pending_review', args=[invite.token]),
        )
        invite.refresh_from_db()
        self.assertEqual(invite.status, 'accepted')
        self.assertEqual(invite.approval_status, 'pending_review')
        self.assertEqual(ReferralBonus.objects.count(), 0)

        self.client.force_login(self.super_admin)
        response = self.client.get(reverse('approve_member', args=[invite.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Approve Friend Mechanics')
        response = self.client.post(reverse('approve_member', args=[invite.pk]))
        self.assertRedirects(response, reverse('pending_approvals'))

        invite.refresh_from_db()
        invite.organization.refresh_from_db()
        joined_admin = invite.organization.members.get(role='org_admin')
        self.assertEqual(invite.approval_status, 'approved')
        self.assertTrue(invite.organization.is_active)
        self.assertTrue(joined_admin.is_active)
        self.assertTrue(invite.bonus_rewarded)
        self.assertEqual(ReferralBonus.objects.filter(organization=referrer).count(), 1)

        self.assertFalse(_award_member_invite_bonus(invite))
        self.assertEqual(ReferralBonus.objects.filter(organization=referrer).count(), 1)


@override_settings(ALLOWED_HOSTS=['testserver'])
class TenantCmsTests(TestCase):
    def setUp(self):
        self.plan = Plan.objects.create(
            name='Growth',
            level='growth',
            price=299,
            max_hero_slides=3,
            max_promos=3,
        )
        self.org_a, self.admin_a = self.make_org('Alpha Services', '9100000001', 'alpha')
        self.org_b, self.admin_b = self.make_org('Beta Services', '9100000002', 'beta')

    def make_org(self, name, phone, username):
        org = Organization.objects.create(
            name=name,
            plan=self.plan,
            status='active',
            is_active=True,
            email=f'{username}@example.com',
            phone=phone,
            address_line1='1 Main Road',
            city='Chennai',
            state='Tamil Nadu',
            pincode='600001',
            plan_start_date=timezone.now().date(),
            plan_end_date=timezone.now().date() + timezone.timedelta(days=30),
        )
        user = CustomUser.objects.create_user(
            username=username,
            password='StrongPass!482',
            organization=org,
            role='org_admin',
        )
        return org, user

    def test_cms_content_is_scoped_to_owner(self):
        foreign_slide = HeroSlide.objects.create(
            organization=self.org_b,
            title='Beta-only hero',
        )
        self.client.force_login(self.admin_a)
        response = self.client.post(reverse('hero_create'), {
            'title': 'Alpha hero',
            'primary_label': 'Get a Quote',
            'primary_url': '#enquiry',
            'order': 0,
            'is_active': 'on',
        })
        self.assertRedirects(response, reverse('page_cms'))
        self.assertTrue(HeroSlide.objects.filter(
            organization=self.org_a,
            title='Alpha hero',
        ).exists())

        response = self.client.post(reverse('hero_edit', args=[foreign_slide.pk]), {
            'title': 'Hijacked',
            'primary_label': 'Get a Quote',
            'primary_url': '#enquiry',
            'order': 0,
        })
        self.assertEqual(response.status_code, 404)
        foreign_slide.refresh_from_db()
        self.assertEqual(foreign_slide.title, 'Beta-only hero')

    def test_public_json_exposes_only_active_business(self):
        HeroSlide.objects.create(
            organization=self.org_a,
            title='Fast Alpha Service',
            is_active=True,
        )
        PromoBanner.objects.create(
            organization=self.org_a,
            title='Summer Service Offer',
            is_active=True,
        )
        response = self.client.get(reverse('public_content_json', args=[self.org_a.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['heroes'][0]['title'], 'Fast Alpha Service')
        self.assertIn('stale-while-revalidate', response['Cache-Control'])
        response = self.client.get(reverse('public_landing', args=[self.org_a.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Fast Alpha Service')
        self.assertContains(response, 'Summer Service Offer')

        self.org_a.status = 'pending_approval'
        self.org_a.is_active = False
        self.org_a.save(update_fields=['status', 'is_active'])
        response = self.client.get(reverse('public_content_json', args=[self.org_a.slug]))
        self.assertEqual(response.status_code, 404)

    def test_owner_can_customize_public_page_inline(self):
        public_url = reverse('public_landing', args=[self.org_a.slug])
        anonymous_response = self.client.get(public_url)
        self.assertNotContains(anonymous_response, 'Customize Page')

        self.client.force_login(self.admin_a)
        owner_response = self.client.get(public_url)
        self.assertContains(owner_response, 'Customize Page')
        editor_response = self.client.get(f'{public_url}?customize=1')
        self.assertContains(editor_response, 'Save Changes')
        self.assertIn(b'Manage All Page Content', editor_response.content)

        response = self.client.post(
            reverse('page_config_update'),
            data={
                'business_name': 'Alpha Electric Pro',
                'hero_title': 'Power restored today',
                'hero_subtitle': 'Fast local electricians at a fair price.',
                'description': 'We handle residential and commercial electrical work.',
                'primary_color': '#123456',
                'accent_color': '#fedcba',
                'background_color': '#101820',
                'show_stats': False,
                'show_featured_services': True,
                'show_promos': False,
                'show_about': True,
                'show_services': True,
                'show_products': False,
                'show_gallery': True,
                'show_testimonials': True,
                'show_payment': False,
                'show_contact': True,
            },
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['ok'])

        self.org_a.refresh_from_db()
        config = LandingPageConfig.objects.get(organization=self.org_a)
        self.assertEqual(self.org_a.name, 'Alpha Electric Pro')
        self.assertEqual(config.hero_title, 'Power restored today')
        self.assertFalse(config.show_stats)
        self.assertFalse(config.show_promos)
        self.assertEqual(config.accent_color, '#fedcba')

        saved_response = self.client.get(public_url)
        self.assertContains(saved_response, 'Power restored today')
        self.assertContains(saved_response, 'data-show-stats="false"')

    def test_saving_active_promo_turns_section_on_and_displays_banner(self):
        LandingPageConfig.objects.create(
            organization=self.org_a,
            show_promos=False,
        )
        self.client.force_login(self.admin_a)

        response = self.client.post(reverse('promo_create'), {
            'badge_text': 'Limited offer',
            'title': 'Twenty percent off this week',
            'description': 'Book before Sunday to claim the discount.',
            'cta_label': 'Book now',
            'cta_url': '#enquiry',
            'starts_at': '',
            'ends_at': '',
            'is_active': 'on',
            'order': 0,
        })
        self.assertRedirects(response, reverse('page_cms'))

        config = LandingPageConfig.objects.get(organization=self.org_a)
        self.assertTrue(config.show_promos)
        landing = self.client.get(reverse('public_landing', args=[self.org_a.slug]))
        self.assertContains(landing, 'Twenty percent off this week')
        self.assertContains(landing, 'data-show-promos="true"')
        self.assertContains(landing, 'data-page-section="promos"')

    def test_landing_does_not_invent_business_claims(self):
        response = self.client.get(reverse('public_landing', args=[self.org_a.slug]))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.org_a.name)
        self.assertContains(response, 'overflow-x: clip')
        self.assertNotContains(response, '500+')
        self.assertNotContains(response, '4.9★')
        self.assertNotContains(response, '24/7 Emergency Service')
        self.assertNotContains(response, 'Certified technicians')
        self.assertNotContains(response, 'Get a Free Inspection')
        self.assertNotContains(response, '₹500')

    def test_expanded_cms_content_is_saved_and_rendered_for_the_owner(self):
        self.client.force_login(self.admin_a)
        response = self.client.post(
            reverse('cms_content_create', args=['feature']),
            {
                'icon': 'shield-check',
                'title': 'Licensed installation team',
                'description': 'Permit-ready installation for declared project scopes.',
                'is_active': 'on',
                'order': 1,
            },
        )
        self.assertRedirects(response, reverse('page_cms'))
        feature = BusinessFeature.objects.get(organization=self.org_a)
        self.assertEqual(feature.title, 'Licensed installation team')

        FAQItem.objects.create(
            organization=self.org_a,
            question='Do you provide written estimates?',
            answer='Yes, after the site review.',
        )
        SuccessStory.objects.create(
            organization=self.org_a,
            business_name='Customer Project',
            title='Scheduled upgrade completed',
            story='The work was completed within the confirmed schedule.',
        )
        DealerLocation.objects.create(
            organization=self.org_a,
            name='Central Branch',
            address='1 Main Road',
            city='Chennai',
            latitude='13.082700',
            longitude='80.270700',
        )

        landing = self.client.get(reverse('public_landing', args=[self.org_a.slug]))
        self.assertContains(landing, 'Licensed installation team')
        self.assertContains(landing, 'Do you provide written estimates?')
        self.assertContains(landing, 'Scheduled upgrade completed')
        self.assertContains(landing, 'Central Branch')
        self.assertContains(landing, 'Find nearest')

        content = self.client.get(reverse('public_content_json', args=[self.org_a.slug])).json()
        self.assertEqual(content['features'][0]['title'], 'Licensed installation team')
        self.assertEqual(content['faqs'][0]['question'], 'Do you provide written estimates?')

    def test_expanded_cms_rejects_cross_tenant_edits(self):
        foreign_feature = BusinessFeature.objects.create(
            organization=self.org_b,
            title='Beta feature',
        )
        self.client.force_login(self.admin_a)
        response = self.client.post(
            reverse('cms_content_edit', args=['feature', foreign_feature.pk]),
            {
                'icon': 'star',
                'title': 'Changed',
                'description': '',
                'is_active': 'on',
                'order': 0,
            },
        )
        self.assertEqual(response.status_code, 404)
        foreign_feature.refresh_from_db()
        self.assertEqual(foreign_feature.title, 'Beta feature')

    def test_footer_social_links_and_google_map_are_cms_driven(self):
        self.client.force_login(self.admin_a)
        embed_url = 'https://www.google.com/maps/embed?pb=test'
        response = self.client.post(reverse('footer_settings_update'), {
            'facebook_url': 'https://facebook.com/alpha',
            'instagram_url': 'https://instagram.com/alpha',
            'linkedin_url': '',
            'twitter_url': 'https://x.com/alpha',
            'google_maps_embed_url': embed_url,
        })
        self.assertRedirects(response, reverse('page_cms'))

        self.org_a.refresh_from_db()
        config = LandingPageConfig.objects.get(organization=self.org_a)
        self.assertEqual(self.org_a.facebook_url, 'https://facebook.com/alpha')
        self.assertEqual(config.google_maps_embed_url, embed_url)

        landing = self.client.get(reverse('public_landing', args=[self.org_a.slug]))
        self.assertContains(landing, embed_url.replace('&', '&amp;'))
        self.assertContains(landing, 'footer-map')

    def test_payment_amount_is_saved_and_rendered_from_cms(self):
        self.client.force_login(self.admin_a)
        response = self.client.post(reverse('add_payment_qr'), {
            'label': 'Booking advance',
            'method': 'upi',
            'amount': '1250.50',
            'upi_id': 'alpha@upi',
        })
        self.assertRedirects(response, reverse('manage_payment_qr'))
        payment_qr = PaymentQR.objects.get(organization=self.org_a)
        self.assertEqual(str(payment_qr.amount), '1250.50')

        landing = self.client.get(reverse('public_landing', args=[self.org_a.slug]))
        self.assertContains(landing, 'Booking advance')
        self.assertContains(landing, '₹1250.50')

    @patch('app.views.create_paypal_order')
    def test_paypal_uses_cms_amount_instead_of_a_fixed_or_client_amount(self, create_order):
        payment_qr = PaymentQR.objects.create(
            organization=self.org_a,
            label='Online deposit',
            method='paypal',
            amount=Decimal('725.00'),
            is_active=True,
        )
        create_order.return_value = ({
            'id': 'PAYPAL-ORDER-1',
            'links': [{'rel': 'approve', 'href': 'https://paypal.example/approve'}],
        }, None)

        response = self.client.post(
            reverse('paypal_create'),
            data=json.dumps({
                'qr_id': payment_qr.pk,
                'amount': '1.00',
                'return_url': reverse('public_landing', args=[self.org_a.slug]),
            }),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['success'])
        self.assertEqual(create_order.call_args.args[0], Decimal('725.00'))
        self.assertEqual(create_order.call_args.kwargs['brand_name'], self.org_a.name)

    def test_customizer_save_is_scoped_to_logged_in_owner(self):
        response = self.client.post(
            reverse('page_config_update'),
            data='{}',
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 302)
        self.assertFalse(LandingPageConfig.objects.filter(organization=self.org_a).exists())

    def test_management_forms_use_the_shared_dashboard_theme(self):
        self.client.force_login(self.admin_a)
        response = self.client.get(reverse('hero_create'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="dashboard-shell"')
        self.assertContains(response, 'class="card-modern"')
        self.assertContains(response, 'Title')

        response = self.client.get(reverse('manage_gallery'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="dashboard-shell"')

    def test_owner_can_save_complete_service_editor_content(self):
        self.client.force_login(self.admin_a)
        response = self.client.post(reverse('add_service'), {
            'name': 'Emergency rewiring',
            'description': 'Safe residential rewiring and fault repair.',
            'price': '850.00',
            'price_unit': 'per visit',
            'icon': 'lightning-charge',
            'video_url': 'https://www.youtube.com/watch?v=example',
            'tags': 'emergency, residential, emergency',
            'is_featured': 'on',
            'is_active': 'on',
            'order': '1',
        })
        self.assertRedirects(response, reverse('manage_services'))

        service = Service.objects.get(organization=self.org_a)
        self.assertEqual(service.name, 'Emergency rewiring')
        self.assertEqual(service.tags, 'emergency,residential')
        self.assertEqual(
            service.video_url,
            'https://www.youtube.com/watch?v=example',
        )

    def test_owner_can_save_product_with_specifications(self):
        self.client.force_login(self.admin_a)
        response = self.client.post(reverse('add_product'), {
            'name': 'Copper cable roll',
            'description': 'ISI-marked residential copper cable.',
            'sku': 'CCR-100',
            'category': 'Electrical supplies',
            'brand': 'Alpha',
            'price': '1250.00',
            'discount_price': '1100.00',
            'stock_quantity': '8',
            'unit': 'roll',
            'condition': 'new',
            'icon': 'box-seam',
            'is_featured': 'on',
            'is_active': 'on',
            'in_stock': 'on',
            'order': '2',
            'youtube_url': '',
            'instagram_url': '',
            'specs_json': '{"length": "90m", "gauge": "2.5 sq mm"}',
        })
        self.assertRedirects(response, reverse('manage_products'))

        product = Product.objects.get(organization=self.org_a)
        self.assertEqual(product.name, 'Copper cable roll')
        self.assertEqual(product.specs_json['length'], '90m')
        self.assertEqual(product.discount_price, Decimal('1100.00'))

    def test_invalid_product_submission_explains_why_nothing_saved(self):
        self.client.force_login(self.admin_a)
        response = self.client.post(reverse('add_product'), {
            'name': 'Missing price product',
            'unit': 'piece',
            'condition': 'new',
            'icon': 'box-seam',
            'stock_quantity': '0',
            'order': '0',
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Nothing was saved yet')
        self.assertContains(response, '<strong>Price:</strong>', html=True)
        self.assertFalse(Product.objects.filter(
            organization=self.org_a,
            name='Missing price product',
        ).exists())


@override_settings(ALLOWED_HOSTS=['testserver'])
class DiscoveryMarketplaceTests(TestCase):
    def setUp(self):
        self.category = BusinessCategory.objects.create(
            name='Electricians',
            slug='electricians',
            icon='lightning-charge',
        )
        self.approved = Organization.objects.create(
            name='Bright Spark Electricals',
            category=self.category,
            tagline='Fast residential electrical support',
            email='bright@example.com',
            phone='9876543210',
            whatsapp='9876543210',
            address_line1='12 Main Road',
            city='Chennai',
            state='Tamil Nadu',
            pincode='600001',
            status='active',
            is_active=True,
            is_verified=True,
        )
        self.pending = Organization.objects.create(
            name='Pending Electricals',
            category=self.category,
            email='pending@example.com',
            phone='9000000000',
            address_line1='22 Main Road',
            city='Chennai',
            state='Tamil Nadu',
            pincode='600002',
            status='pending_approval',
            is_active=True,
        )
        Service.objects.create(
            organization=self.approved,
            name='Emergency rewiring',
            is_active=True,
        )

    def test_discovery_only_shows_super_admin_approved_businesses(self):
        response = self.client.get(reverse('discovery_home'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.approved.name)
        self.assertNotContains(response, self.pending.name)
        self.assertEqual(response.context['platform_total'], 1)
        self.assertEqual(
            response.context['categories'][0].active_business_count,
            1,
        )

    def test_discovery_searches_service_names(self):
        response = self.client.get(
            reverse('discovery_home'),
            {'q': 'rewiring'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.approved.name)
        self.assertEqual(response.context['total'], 1)

    def test_discovery_ajax_returns_only_results_fragment(self):
        response = self.client.get(
            reverse('discovery_home'),
            {'city': 'Chennai'},
            HTTP_X_REQUESTED_WITH='XMLHttpRequest',
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'includes/discovery_results.html')
        self.assertContains(response, self.approved.name)
        self.assertNotContains(response, 'class="discovery-hero"')

    def test_discovery_rejects_invalid_category_value_without_error(self):
        response = self.client.get(
            reverse('discovery_home'),
            {'cat': 'not-a-number'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.approved.name)
