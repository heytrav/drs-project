# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-06-25 20:38
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('domain_api', '0050_auto_20170617_0656'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='defaultcontact',
            unique_together=set([]),
        ),
        migrations.RemoveField(
            model_name='defaultcontact',
            name='contact',
        ),
        migrations.RemoveField(
            model_name='defaultcontact',
            name='contact_type',
        ),
        migrations.RemoveField(
            model_name='defaultcontact',
            name='provider',
        ),
        migrations.RemoveField(
            model_name='defaultcontact',
            name='user',
        ),
        migrations.AlterUniqueTogether(
            name='defaultregistrant',
            unique_together=set([]),
        ),
        migrations.RemoveField(
            model_name='defaultregistrant',
            name='registrant',
        ),
        migrations.RemoveField(
            model_name='defaultregistrant',
            name='user',
        ),
        migrations.DeleteModel(
            name='DefaultContact',
        ),
        migrations.DeleteModel(
            name='DefaultRegistrant',
        ),
    ]