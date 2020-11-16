# Generated by Django 2.1.15 on 2020-11-16 07:44

import cosinnus.models.mixins.indexes
import django.contrib.postgres.fields.jsonb
import django.core.validators
from django.db import migrations, models
import django.db.models.deletion
import jsonfield.fields
import re


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus', '0074_auto_20201109_1410'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprofile',
            name='dynamic_fields',
            field=django.contrib.postgres.fields.jsonb.JSONField(blank=True, default=dict, help_text='Extra userprofile fields for each portal, as defined in `settings.COSINNUS_USERPROFILE_EXTRA_FIELDS`', verbose_name='Dynamic extra fields'),
        ),
        migrations.AlterField(
            model_name='cosinnusportal',
            name='dynamic_field_choices',
            field=django.contrib.postgres.fields.jsonb.JSONField(blank=True, default=dict, help_text='A dict storage for all choice lists for the dynamic fields of type `DYNAMIC_FIELD_TYPE_ADMIN_DEFINED_CHOICES_TEXT`', verbose_name='Dynamic choice field choices'),
        ),
        migrations.AlterField(
            model_name='userprofile',
            name='extra_fields',
            field=jsonfield.fields.JSONField(blank=True, default={}, help_text='NO LONGER USED! Extra userprofile fields for each portal, as defined in `settings.COSINNUS_USERPROFILE_EXTRA_FIELDS`'),
        ),
    ]
