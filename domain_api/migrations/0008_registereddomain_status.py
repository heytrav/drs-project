# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-03-10 10:04
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('domain_api', '0007_auto_20170310_0955'),
    ]

    operations = [
        migrations.AddField(
            model_name='registereddomain',
            name='status',
            field=models.CharField(max_length=200, null=True),
        ),
    ]