# Generated by Django 5.0.2 on 2024-04-15 05:38

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0003_datasetdescription_file_path'),
    ]

    operations = [
        migrations.AddField(
            model_name='datasetdescription',
            name='dataset_file',
            field=models.FileField(default=15, upload_to='datasets/'),
            preserve_default=False,
        ),
    ]
