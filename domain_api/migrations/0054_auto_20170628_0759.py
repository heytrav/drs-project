# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-06-28 07:59
from __future__ import unicode_literals

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('domain_api', '0053_auto_20170628_0759'),
    ]

    operations = [
        migrations.AlterField(
            model_name='registereddomain',
            name='fqdn',
            field=models.CharField(default=uuid.uuid4, max_length=200, null=True),
        ),
    ]
