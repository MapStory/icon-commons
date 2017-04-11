# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models
from django.conf import settings
import taggit.managers


class Migration(migrations.Migration):

    dependencies = [
        ('taggit', '0002_auto_20150616_2121'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Collection',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=128)),
                ('slug', models.CharField(max_length=128)),
                ('description', models.TextField(null=True)),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='Icon',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('name', models.CharField(max_length=128)),
                ('slug', models.CharField(max_length=128)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('collection', models.ForeignKey(to='icon_commons.Collection')),
                ('owner', models.ForeignKey(blank=True, to=settings.AUTH_USER_MODEL, null=True)),
                ('tags', taggit.managers.TaggableManager(to='taggit.Tag', through='taggit.TaggedItem', help_text='A comma-separated list of tags.', verbose_name='Tags')),
            ],
        ),
        migrations.CreateModel(
            name='IconData',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('svg', models.TextField()),
                ('version', models.PositiveSmallIntegerField()),
                ('change_log', models.TextField(null=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('icon', models.ForeignKey(to='icon_commons.Icon')),
            ],
        ),
        migrations.AlterUniqueTogether(
            name='icondata',
            unique_together=set([('icon', 'version')]),
        ),
        migrations.AlterUniqueTogether(
            name='icon',
            unique_together=set([('name', 'collection')]),
        ),
    ]
