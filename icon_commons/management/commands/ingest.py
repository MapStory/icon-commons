from django.core.management.base import BaseCommand
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from icon_commons.models import Collection
from icon_commons.models import Icon
from taggit.models import Tag
from optparse import make_option
import os
import re
import time


def visit(visitor, dirname, names):
    paths = (os.path.join(dirname, n) for n in names)
    is_svg = lambda n: os.path.isfile(n) and os.path.splitext(n)[1].lower() == '.svg'
    for p in filter(is_svg, paths):
        t = time.time()
        col = visitor.collection(p)
        svg_name = os.path.basename(p)
        # deal w/ odd OSM paths
        if ',' in svg_name:
            svg_name = svg_name[svg_name.rfind(',') + 1:]
        icon, created = Icon.objects.get_or_create(name=svg_name, collection=col)
        icon.tags.add(*visitor.tags(p))
        msg = 'initial import' if created else 'automatic update'
        with open(p, 'rb') as fp:
            data = fp.read()
            updated = True
            try:
                latest = icon.icondata_set.latest('version')
                updated = latest.svg == data
            except ObjectDoesNotExist:
                pass
            if updated:
                icon.new_version(data, msg)
        print('imported ' if created else 'updated', p, ' in %.3f seconds' % (time.time() - t))


_tag_splitter = re.compile('[-_ ]')


class Visitor(object):
    def __init__(self, base):
        self.base = base
        self.collections_cache = {}
        self.tags_cache = {}

    def collection(self, path):
        name = self.collection_name(path)
        col = self.collections_cache.get(name, None)
        if col is None:
            col, created = Collection.objects.get_or_create(name=name)
            self.collections_cache[name] = col
        return col

    def collection_name(self, path):
        relpath = os.path.relpath(path, self.base)
        return os.path.split(relpath)[0]

    def tag(self, name):
        tag = self.tags_cache.get(name, None)
        if tag is None:
            tag, created = Tag.objects.get_or_create(name=name)
            self.tags_cache[name] = tag
        return tag

    def tags(self, path):
        relpath = os.path.relpath(path, self.base)
        # don't auto-tag OSM for now
        if ';' in relpath:
            return []
        tags = []
        while True:
            head, tail = os.path.split(relpath)
            if not head:
                break
            tail = tail.replace('.svg', '')
            found = [t for t in _tag_splitter.split(tail) if not t.isdigit()]
            tags.extend(found)
            relpath = head
        return [self.tag(t) for t in tags]


class Command(BaseCommand):

    args = '<dir ...>'
    help = 'Ingest icons found in the provided directories'
    option_list = BaseCommand.option_list + (
        make_option('--base', help='Specify base directory'),
    )

    def handle(self, *args, **options):
        visitor = None
        with transaction.atomic():
            for arg in args:
                if not visitor:
                    visitor = Visitor(arg)
                else:
                    visitor.base = arg
                if options['base']:
                    visitor.base = options['base']
                os.path.walk(args[0], visit, visitor)
