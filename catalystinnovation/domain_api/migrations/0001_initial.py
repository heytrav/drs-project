# -*- coding: utf-8 -*-
# Generated by Django 1.10.4 on 2016-12-14 04:32
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Person',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('first_name', models.CharField(max_length=200)),
                ('surname', models.CharField(max_length=200)),
                ('email', models.CharField(max_length=200)),
                ('emai2', models.CharField(blank=True, max_length=200)),
                ('emai3', models.CharField(blank=True, max_length=200)),
                ('house_number', models.CharField(max_length=10)),
                ('street1', models.CharField(max_length=200)),
                ('street2', models.CharField(blank=True, max_length=200)),
                ('street3', models.CharField(blank=True, max_length=200)),
                ('city', models.CharField(max_length=200)),
                ('suburb', models.CharField(blank=True, max_length=200)),
                ('state', models.CharField(blank=True, max_length=200)),
                ('postcode', models.CharField(max_length=20)),
                ('country', models.CharField(max_length=200)),
            ],
        ),
    ]