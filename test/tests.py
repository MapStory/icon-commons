from django.core.urlresolvers import reverse
from django.db import IntegrityError
from django.test import TestCase
from django.test.client import Client
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
        self.icon = Icon.objects.create(collection=self.collection, name='baz')
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
                return json.loads(r.content)
            return r.content
        # 3 or fewer chars and istarts_with
        self.assertEquals({'tags':['foobar', 'foofoobarf']}, search_tags('FOO'))
        self.assertEquals({'tags':['barfoo']}, search_tags('BAR'))
        # more than 3 uses icontains
        self.assertEquals({'tags':['barfoo', 'foofoobarf']}, search_tags('BARF'))
        # jsonp
        self.assertEquals('blah({"tags": ["barfoo"]});', search_tags('BAR', callback='blah'))

    def test_list_collections(self):
        r = self.client.get(reverse('iconcommons_collection_list'))
        collections = json.loads(r.content)['collections']
        self.assertEquals(1, len(collections))
        self.assertEquals('foobar', collections[0]['name'])
        self.assertEquals(1, collections[0]['icons'])
        self.assertEquals('/collections/1', collections[0]['href'])

    def test_list_icons(self):
        r = self.client.get(reverse('iconcommons_icon_list'))
        data = json.loads(r.content)
        self.assertEquals(1, data['count'])
        self.assertEquals(1, data['page'])
        self.assertEquals(1, data['pages'])
        self.assertEquals(1, len(data['icons']))
        self.assertEquals({'href':'/icon/1','name':'baz'}, data['icons'][0])

    def test_icon_view(self):
        r = self.client.get(reverse('iconcommons_icon_view', kwargs={'id':1}))
        self.assertEquals('hi', r.content)

    def test_icon_info_view(self):
        self.icon.new_version('hi2', 'updated')
        self.icon.new_version('hi3', 'updated again')
        self.icon.tags.add('x','y','z')
        r = self.client.get(reverse('iconcommons_icon_info_view', kwargs={'id':1}))
        data = json.loads(r.content)
        self.assertEquals(6, len(data['tags']))
        self.assertEquals(3, len(data['versions']))
        self.assertEquals('foobar', data['collection']['name'])

    def test_list_icons_with_tag_query(self):
        r = self.client.get(reverse('iconcommons_icon_list'), {
            'tag' : ['foobar']
        })
        data = json.loads(r.content)
        self.assertEquals(1, data['count'])
        self.assertEquals(1, data['page'])
        self.assertEquals(1, data['pages'])
        self.assertEquals(1, len(data['icons']))
        self.assertEquals({'href':'/icon/1','name':'baz'}, data['icons'][0])

    def test_iconcommons_collection_icons(self):
        r = self.client.get(reverse('iconcommons_collection_icons', kwargs={'collection':'foobar'}))
        data = json.loads(r.content)
        self.assertEquals(1, data['count'])
        self.assertEquals(1, data['page'])
        self.assertEquals(1, data['pages'])
        self.assertEquals(1, len(data['icons']))
        self.assertEquals({'href':'/icon/1','name':'baz'}, data['icons'][0])

    def test_iconcommons_icon_by_fqn(self):
        r = self.client.get(reverse('iconcommons_icon_by_fqn', kwargs={'collection':'foobar', 'icon': 'baz'}))
        self.assertEquals('hi', r.content)



