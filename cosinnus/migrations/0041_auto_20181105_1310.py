# -*- coding: utf-8 -*-
# Generated by Django 1.10.8 on 2018-11-05 12:10
from __future__ import unicode_literals

import django.core.validators
from django.db import migrations, models
import re


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus', '0040_auto_20180926_1620'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tagobject',
            name='topics',
            field=models.CharField(blank=True, max_length=255, null=True, validators=[django.core.validators.RegexValidator(re.compile('^\\d+(?:\\,\\d+)*\\Z', 32), code='invalid', message='Enter only digits separated by commas.')], verbose_name='Topics'),
        ),
    ]
