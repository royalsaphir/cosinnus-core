# Generated by Django 2.1.15 on 2020-10-21 20:17

import cosinnus.models.mixins.indexes
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import jsonfield.fields
import re


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus', '0071_auto_20201014_1214'),
    ]

    operations = [
        migrations.AddField(
            model_name='likeobject',
            name='starred',
            field=models.BooleanField(default=True, verbose_name='Starred'),
        )
    ]
