from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0024_paymentqr_amount'),
    ]

    operations = [
        migrations.AddField(
            model_name='service',
            name='after_image',
            field=models.ImageField(blank=True, null=True, upload_to='services/'),
        ),
        migrations.AddField(
            model_name='service',
            name='banner_image',
            field=models.ImageField(blank=True, null=True, upload_to='services/'),
        ),
        migrations.AddField(
            model_name='service',
            name='before_image',
            field=models.ImageField(blank=True, null=True, upload_to='services/'),
        ),
        migrations.AddField(
            model_name='service',
            name='image2',
            field=models.ImageField(blank=True, null=True, upload_to='services/'),
        ),
        migrations.AddField(
            model_name='service',
            name='tags',
            field=models.CharField(
                blank=True,
                help_text='Comma-separated search and display tags.',
                max_length=500,
            ),
        ),
        migrations.AddField(
            model_name='service',
            name='video_url',
            field=models.URLField(blank=True, help_text='Optional YouTube or service video URL'),
        ),
    ]
