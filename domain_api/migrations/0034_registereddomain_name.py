# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-06-16 09:27
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('domain_api', '0033_auto_20170614_1051'),
    ]

    operations = [
        migrations.AddField(
            model_name='registereddomain',
            name='name',
            field=models.CharField(default='changeme', max_length=200),
            preserve_default=False,
        ),
    ]
