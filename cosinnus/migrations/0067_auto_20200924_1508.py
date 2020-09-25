# Generated by Django 2.1.15 on 2020-09-24 13:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cosinnus', '0066_auto_20200924_1104'),
    ]

    operations = [
        migrations.AlterField(
            model_name='bbbroom',
            name='max_participants',
            field=models.PositiveIntegerField(blank=True, default=None, help_text='Maximum number in the conference at the same time. NOTE: Seems this needs to be +1 more the number that you actually want for BBB to allow!', null=True, verbose_name='maximum number of users'),
        ),
    ]