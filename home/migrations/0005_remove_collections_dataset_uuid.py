# Generated by Django 4.1.13 on 2024-08-26 04:49

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('home', '0004_collections_datasets_collection_name_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='collections',
            name='Dataset_UUID',
        ),
    ]