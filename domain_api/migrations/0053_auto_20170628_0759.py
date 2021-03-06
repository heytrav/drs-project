# -*- coding: utf-8 -*-
# Generated by Django 1.10.5 on 2017-06-28 07:59
from __future__ import unicode_literals

from django.db import migrations


def gen_fqdn(apps, schema_editor):
    RegisteredDomain = apps.get_model('domain_api', 'RegisteredDomain')
    for row in RegisteredDomain.objects.all():
        row.fqdn = '.'.join([row.name, row.tld.zone])
        row.save(update_fields=['fqdn'])

class Migration(migrations.Migration):

    dependencies = [
        ('domain_api', '0052_registereddomain_fqdn'),
    ]

    operations = [
        migrations.RunPython(gen_fqdn, reverse_code=migrations.RunPython.noop),
    ]
