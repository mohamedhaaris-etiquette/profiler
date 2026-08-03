import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0021_adminnotification'),
    ]

    operations = [
        migrations.AlterField(
            model_name='plan',
            name='level',
            field=models.SlugField(
                help_text='Stable plan key, for example starter, growth or premium.',
                max_length=50,
                unique=True,
            ),
        ),
        migrations.AddField(
            model_name='plan',
            name='max_invites',
            field=models.PositiveIntegerField(
                default=2,
                help_text='WhatsApp referral invites allowed',
            ),
        ),
        migrations.AddField(
            model_name='plan',
            name='max_hero_slides',
            field=models.PositiveIntegerField(default=1, help_text='Hero slides allowed'),
        ),
        migrations.AddField(
            model_name='plan',
            name='max_promos',
            field=models.PositiveIntegerField(default=1, help_text='Promotional banners allowed'),
        ),
        migrations.AddIndex(
            model_name='organization',
            index=models.Index(
                fields=['status', 'is_active', 'category'],
                name='org_status_cat_idx',
            ),
        ),
        migrations.AddIndex(
            model_name='organization',
            index=models.Index(fields=['city', 'status'], name='org_city_status_idx'),
        ),
        migrations.AddIndex(
            model_name='organization',
            index=models.Index(fields=['created_at'], name='org_created_idx'),
        ),
        migrations.CreateModel(
            name='HeroSlide',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('eyebrow', models.CharField(blank=True, max_length=120)),
                ('title', models.CharField(max_length=220)),
                ('subtitle', models.TextField(blank=True)),
                ('image', models.ImageField(blank=True, null=True, upload_to='hero_slides/')),
                ('primary_label', models.CharField(default='Get a Quote', max_length=60)),
                ('primary_url', models.CharField(default='#enquiry', max_length=500)),
                ('secondary_label', models.CharField(blank=True, max_length=60)),
                ('secondary_url', models.CharField(blank=True, max_length=500)),
                ('is_active', models.BooleanField(default=True)),
                ('order', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('organization', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='hero_slides',
                    to='app.organization',
                )),
            ],
            options={
                'ordering': ['order', 'id'],
                'indexes': [
                    models.Index(
                        fields=['organization', 'is_active', 'order'],
                        name='hero_org_active_order_idx',
                    ),
                ],
            },
        ),
        migrations.CreateModel(
            name='PromoBanner',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('badge_text', models.CharField(blank=True, max_length=60)),
                ('title', models.CharField(max_length=180)),
                ('description', models.TextField(blank=True)),
                ('image', models.ImageField(blank=True, null=True, upload_to='promo_banners/')),
                ('cta_label', models.CharField(blank=True, max_length=60)),
                ('cta_url', models.CharField(blank=True, max_length=500)),
                ('starts_at', models.DateTimeField(blank=True, null=True)),
                ('ends_at', models.DateTimeField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('order', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('organization', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='promo_banners',
                    to='app.organization',
                )),
            ],
            options={
                'ordering': ['order', 'id'],
                'indexes': [
                    models.Index(
                        fields=['organization', 'is_active', 'order'],
                        name='promo_org_active_order_idx',
                    ),
                    models.Index(fields=['starts_at', 'ends_at'], name='promo_window_idx'),
                ],
            },
        ),
        migrations.CreateModel(
            name='TeamRole',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('slug', models.SlugField(max_length=100)),
                ('permissions', models.JSONField(
                    blank=True,
                    default=list,
                    help_text='Permission keys such as enquiries.view or products.edit.',
                )),
                ('is_active', models.BooleanField(default=True)),
                ('order', models.PositiveIntegerField(default=0)),
                ('organization', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='team_roles',
                    to='app.organization',
                )),
            ],
            options={
                'ordering': ['order', 'name'],
                'constraints': [
                    models.UniqueConstraint(
                        fields=('organization', 'slug'),
                        name='unique_team_role_per_organization',
                    ),
                ],
            },
        ),
        migrations.AddField(
            model_name='customuser',
            name='team_role',
            field=models.ForeignKey(
                blank=True,
                help_text='Optional organization-specific role and permissions.',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='members',
                to='app.teamrole',
            ),
        ),
        migrations.CreateModel(
            name='StaffAvailability',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.CharField(
                    choices=[
                        ('available', 'Available'),
                        ('busy', 'Busy'),
                        ('offline', 'Offline'),
                    ],
                    default='available',
                    max_length=12,
                )),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('staff', models.OneToOneField(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='availability',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
        ),
        migrations.AlterField(
            model_name='invitationtoken',
            name='email',
            field=models.EmailField(blank=True, db_index=True, default='', max_length=254),
        ),
        migrations.AddField(
            model_name='invitationtoken',
            name='phone',
            field=models.CharField(blank=True, db_index=True, default='', max_length=20),
        ),
        migrations.AddField(
            model_name='invitationtoken',
            name='delivery_channel',
            field=models.CharField(
                choices=[
                    ('email', 'Email'),
                    ('whatsapp', 'WhatsApp'),
                    ('direct', 'Direct'),
                ],
                default='email',
                max_length=12,
            ),
        ),
        migrations.AddField(
            model_name='invitationtoken',
            name='referral_code',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='invitations',
                to='app.referralcode',
            ),
        ),
        migrations.AlterField(
            model_name='invitationtoken',
            name='invite_type',
            field=models.CharField(
                choices=[
                    ('admin', 'Admin Invite'),
                    ('member', 'Member Invite'),
                    ('direct', 'Direct Registration'),
                ],
                default='admin',
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name='referralbonus',
            name='source_invitation',
            field=models.OneToOneField(
                blank=True,
                help_text='Makes invitation rewards idempotent.',
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='reward_transaction',
                to='app.invitationtoken',
            ),
        ),
        migrations.AlterField(
            model_name='supplychainrole',
            name='role_type',
            field=models.SlugField(
                help_text='Custom role key. New business roles can be added without code changes.',
                max_length=50,
                unique=True,
            ),
        ),
    ]
