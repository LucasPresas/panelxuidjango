from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('panel', '0005_reseller_password_plano'),
    ]

    operations = [
        migrations.AddField(
            model_name='canal',
            name='proveedor_data',
            field=models.JSONField(blank=True, null=True, help_text='Metadata cruda del proveedor'),
        ),
        migrations.AddField(
            model_name='canal',
            name='proveedor_id',
            field=models.CharField(blank=True, db_index=True, max_length=20, null=True),
        ),
        migrations.AddField(
            model_name='canal',
            name='proveedor_source',
            field=models.CharField(blank=True, help_text='stix / claro / directo', max_length=20, null=True),
        ),
        migrations.AlterField(
            model_name='canal',
            name='url_origen',
            field=models.URLField(blank=True, null=True),
        ),
    ]
