from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0022_scalable_cms_whatsapp_referrals'),
    ]

    operations = [
        migrations.CreateModel(
            name='LandingPageConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('hero_title', models.CharField(blank=True, max_length=220)),
                ('hero_subtitle', models.TextField(blank=True)),
                ('primary_color', models.CharField(default='#2d6a4f', max_length=7)),
                ('accent_color', models.CharField(default='#f59e0b', max_length=7)),
                ('background_color', models.CharField(default='#0a0f0d', max_length=7)),
                ('show_stats', models.BooleanField(default=True)),
                ('show_featured_services', models.BooleanField(default=True)),
                ('show_promos', models.BooleanField(default=True)),
                ('show_about', models.BooleanField(default=True)),
                ('show_services', models.BooleanField(default=True)),
                ('show_products', models.BooleanField(default=True)),
                ('show_gallery', models.BooleanField(default=True)),
                ('show_testimonials', models.BooleanField(default=True)),
                ('show_payment', models.BooleanField(default=True)),
                ('show_contact', models.BooleanField(default=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('organization', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='landing_page_config', to='app.organization')),
            ],
        ),
    ]
