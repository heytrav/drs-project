# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-06-16 10:37
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('domain_api', '0040_auto_20170616_1004'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='registereddomain',
            unique_together=set([]),
        ),
    ]
