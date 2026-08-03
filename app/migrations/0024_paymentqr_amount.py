from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0023_landingpageconfig'),
    ]

    operations = [
        migrations.AddField(
            model_name='paymentqr',
            name='amount',
            field=models.DecimalField(
                blank=True,
                decimal_places=2,
                help_text='Optional fixed amount displayed on the public payment card.',
                max_digits=10,
                null=True,
            ),
        ),
    ]
