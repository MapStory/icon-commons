from django.contrib.auth.models import User

from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse

from icon_commons.models import Collection
from icon_commons.models import Icon
from icon_commons.models import IconData
import json


class ModelTest(TestCase):

    def test_icon_new_version(self):
        c = Collection.objects.create(name='default')
        i = Icon.objects.create(collection=c, name='icon')
        d1 = i.new_version('hi', None)
        assert d1.svg == 'hi'
        assert d1.version == 1
        d2 = i.new_version('bye', None)
        assert d2.svg == 'bye'
        assert d2.version == 2
        assert i.icondata_set.count() == 2

    def test_icon_unique(self):
        c = Collection.objects.create(name='default')
        Icon.objects.create(collection=c, name='icon')
        try:
            Icon.objects.create(collection=c, name='icon')
            assert False
        except IntegrityError:
            pass

    def test_latest_version(self):
        c = Collection.objects.create(name='default')
        i = Icon.objects.create(collection=c, name='icon')
        i.new_version('hi', None)
        i.new_version('bye', None)
        q = IconData.objects.select_related('icon')


class ViewTest(TestCase):
    def setUp(self):
        self.collection = Collection.objects.create(name='foobar')
        self.owner = User.objects.create_user(username="user_1", email="demo@demo.com", password="demo")
        self.icon = Icon.objects.create(collection=self.collection, name='baz', owner=self.owner)
        self.icon.tags.add('foobar', 'barfoo', 'foofoobarf')
        self.data = self.icon.new_version('hi', None)

    def test_get_svg(self):
        r = self.client.get('/foobar/baz.svg')

    def test_search_tags(self):
        def search_tags(query, callback=None):
            data = {'query': query}
            if callback:
                data['callback'] = callback
            r = self.client.get(reverse('iconcommons_search_tags'), data)
            if callback is None:
                return json.loads(r.content.decode())
            return r.content.decode()

        # 3 or fewer chars and istarts_with
        self.assertEqual({'tags': ['foobar', 'foofoobarf']}, search_tags('FOO'))
        self.assertEqual({'tags': ['barfoo']}, search_tags('BAR'))
        # more than 3 uses icontains
        self.assertEqual({'tags': ['barfoo', 'foofoobarf']}, search_tags('BARF'))
        # jsonp
        self.assertEqual('blah({"tags": ["barfoo"]});', search_tags('BAR', callback='blah'))

    def test_list_collections(self):
        r = self.client.get(reverse('iconcommons_collection_list'))
        collections = json.loads(r.content)['collections']
        self.assertEqual(1, len(collections))
        self.assertEqual('foobar', collections[0]['name'])
        self.assertEqual(1, collections[0]['icons'])
        self.assertEqual('/collections/1', collections[0]['href'])

    def test_list_icons(self):
        r = self.client.get(reverse('iconcommons_icon_list'))
        data = json.loads(r.content)
        self.assertEqual(1, data['count'])
        self.assertEqual(1, data['page'])
        self.assertEqual(1, data['pages'])
        self.assertEqual(1, len(data['icons']))
        self.assertEqual({'href': '/icon/1', 'name': 'baz', 'owner': 'user_1'}, data['icons'][0])

    def test_icon_view(self):
        r = self.client.get(reverse('iconcommons_icon_view', kwargs={'id': 1}))
        self.assertEqual('hi', r.content.decode())

    def test_icon_info_view(self):
        self.icon.new_version('hi2', 'updated')
        self.icon.new_version('hi3', 'updated again')
        self.icon.tags.add('x', 'y', 'z')
        r = self.client.get(reverse('iconcommons_icon_info_view', kwargs={'id': 1}))
        data = json.loads(r.content.decode())
        self.assertEqual(6, len(data['tags']))
        self.assertEqual(3, len(data['versions']))
        self.assertEqual('foobar', data['collection']['name'])

    def test_list_icons_with_tag_query(self):
        r = self.client.get(reverse('iconcommons_icon_list'), {
            'tag': ['foobar']
        })
        data = json.loads(r.content)
        self.assertEqual(1, data['count'])
        self.assertEqual(1, data['page'])
        self.assertEqual(1, data['pages'])
        self.assertEqual(1, len(data['icons']))
        self.assertEqual({'href': '/icon/1', 'name': 'baz', 'owner': 'user_1'}, data['icons'][0])

    def test_iconcommons_collection_icons(self):
        r = self.client.get(reverse('iconcommons_collection_icons', kwargs={'collection': 'foobar'}))
        data = json.loads(r.content.decode())
        self.assertEqual(1, data['count'])
        self.assertEqual(1, data['page'])
        self.assertEqual(1, data['pages'])
        self.assertEqual(1, len(data['icons']))
        self.assertEqual({'href': '/icon/1', 'name': 'baz', 'owner': 'user_1'}, data['icons'][0])

    def test_iconcommons_icon_by_fqn(self):
        r = self.client.get(reverse('iconcommons_icon_by_fqn', kwargs={'collection': 'foobar', 'icon': 'baz'}))
        self.assertEqual('hi', r.content.decode())
