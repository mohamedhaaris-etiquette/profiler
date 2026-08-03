from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0025_service_extended_content'),
    ]

    operations = [
        migrations.AddField(
            model_name='landingpageconfig',
            name='google_maps_embed_url',
            field=models.URLField(
                blank=True,
                help_text='Google Maps embed URL (the URL used inside an iframe).',
                max_length=1000,
            ),
        ),
        migrations.AddField(
            model_name='landingpageconfig',
            name='show_dealers',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='landingpageconfig',
            name='show_faq',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='landingpageconfig',
            name='show_features',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='landingpageconfig',
            name='show_footer_map',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='landingpageconfig',
            name='show_maximise',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='landingpageconfig',
            name='show_plans',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='landingpageconfig',
            name='show_success_stories',
            field=models.BooleanField(default=True),
        ),
        migrations.CreateModel(
            name='BusinessFeature',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('icon', models.CharField(default='check2-circle', help_text='Bootstrap icon name, for example shield-check or lightning-charge.', max_length=50)),
                ('title', models.CharField(max_length=140)),
                ('description', models.TextField(blank=True)),
                ('is_active', models.BooleanField(default=True)),
                ('order', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('organization', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='landing_features', to='app.organization')),
            ],
            options={
                'ordering': ['order', 'id'],
            },
        ),
        migrations.CreateModel(
            name='DealerLocation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=160)),
                ('address', models.TextField()),
                ('city', models.CharField(blank=True, max_length=100)),
                ('phone', models.CharField(blank=True, max_length=20)),
                ('whatsapp', models.CharField(blank=True, max_length=20)),
                ('map_url', models.URLField(blank=True, help_text='Google Maps share link for this location.', max_length=1000)),
                ('latitude', models.DecimalField(blank=True, decimal_places=6, help_text='Optional coordinate used by the Find nearest button.', max_digits=9, null=True)),
                ('longitude', models.DecimalField(blank=True, decimal_places=6, help_text='Optional coordinate used by the Find nearest button.', max_digits=9, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('order', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('organization', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='dealer_locations', to='app.organization')),
            ],
            options={
                'ordering': ['order', 'id'],
            },
        ),
        migrations.CreateModel(
            name='FAQItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('question', models.CharField(max_length=240)),
                ('answer', models.TextField()),
                ('is_active', models.BooleanField(default=True)),
                ('order', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('organization', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='faq_items', to='app.organization')),
            ],
            options={
                'verbose_name': 'FAQ item',
                'ordering': ['order', 'id'],
            },
        ),
        migrations.CreateModel(
            name='MaximiseStep',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('icon', models.CharField(default='graph-up-arrow', help_text='Bootstrap icon name, for example camera, chat-dots or graph-up.', max_length=50)),
                ('title', models.CharField(max_length=140)),
                ('description', models.TextField(blank=True)),
                ('cta_label', models.CharField(blank=True, max_length=60)),
                ('cta_url', models.CharField(blank=True, max_length=500)),
                ('is_active', models.BooleanField(default=True)),
                ('order', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('organization', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='maximise_steps', to='app.organization')),
            ],
            options={
                'ordering': ['order', 'id'],
            },
        ),
        migrations.CreateModel(
            name='SuccessStory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('business_name', models.CharField(max_length=160)),
                ('title', models.CharField(max_length=180)),
                ('story', models.TextField()),
                ('result_value', models.CharField(blank=True, help_text='Optional result, for example 2x or 35%.', max_length=50)),
                ('result_label', models.CharField(blank=True, help_text='What the result measures, for example more enquiries.', max_length=100)),
                ('image', models.ImageField(blank=True, null=True, upload_to='success_stories/')),
                ('is_active', models.BooleanField(default=True)),
                ('order', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('organization', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='success_stories', to='app.organization')),
            ],
            options={
                'verbose_name_plural': 'Success stories',
                'ordering': ['order', 'id'],
            },
        ),
        migrations.AddIndex(
            model_name='businessfeature',
            index=models.Index(fields=['organization', 'is_active', 'order'], name='feature_org_active_order_idx'),
        ),
        migrations.AddIndex(
            model_name='dealerlocation',
            index=models.Index(fields=['organization', 'is_active', 'order'], name='dealer_org_active_order_idx'),
        ),
        migrations.AddIndex(
            model_name='faqitem',
            index=models.Index(fields=['organization', 'is_active', 'order'], name='faq_org_active_order_idx'),
        ),
        migrations.AddIndex(
            model_name='maximisestep',
            index=models.Index(fields=['organization', 'is_active', 'order'], name='maxstep_org_active_order_idx'),
        ),
        migrations.AddIndex(
            model_name='successstory',
            index=models.Index(fields=['organization', 'is_active', 'order'], name='story_org_active_order_idx'),
        ),
    ]
