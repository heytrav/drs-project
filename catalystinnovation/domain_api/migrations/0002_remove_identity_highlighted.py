# -*- coding: utf-8 -*-
# Generated by Django 1.10.4 on 2016-12-23 18:21
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('domain_api', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='identity',
            name='highlighted',
        ),
    ]