from django.core.urlresolvers import reverse
from django.db import connection
from django.db.models import Count
from django.http import HttpResponse
from django.http import HttpResponseNotModified
from django.views.generic.base import View
from django.views.generic.base import ContextMixin
from django.views.generic.list import MultipleObjectMixin
from icon_commons.models import Collection
from icon_commons.models import Icon
from icon_commons.models import IconData
from icon_commons.utils import process_svg
from taggit.models import TaggedItem
import json
from datetime import datetime


_date_fmt = '%a, %d %b %Y %H:%M:%S GMT'


# can be used around a function to debug db queries. to wrap a generic view:
# ViewClass.func = debug_queries(ViewClass.get)
def debug_queries(func):
    def inner(*args, **kw):
        from django.conf import settings
        settings.DEBUG = True
        connection.queries = []
        resp = func(*args, **kw)
        print len(connection.queries)
        return resp
    return inner


def cors(cls):
    get = cls.get
    def inner(*args, **kw):
        resp = get(*args, **kw)
        resp['Access-Control-Allow-Origin'] = '*'
        resp['Access-Control-Allow-Methods'] = 'GET'
        return resp
    cls.get = inner
    return cls


class JSONMixin(ContextMixin):

    def get(self, request, *args, **kwargs):
        context = self.get_context_data(**kwargs)
        data = self.get_json_data(context)
        callback = request.GET.get('callback', None)
        if callback:
            return HttpResponse('%s(%s);' % (callback, json.dumps(data)), content_type='application/javascript')
        else:
            return HttpResponse(json.dumps(data), content_type='application/json')

    def get_json_data(self, context):
        return context


class JSONListMixin(MultipleObjectMixin, JSONMixin):

    def get(self, request, *args, **kwargs):
        if self.context_object_name is None:
            self.context_object_name = unicode(self.model._meta.verbose_name_plural)
        self.object_list = self.get_queryset()
        return super(JSONListMixin, self).get(request, *args, **kwargs)

    def get_json_data(self, context):
        data = {
            self.context_object_name: [self.encode(o) for o in context[self.context_object_name]]
        }
        paginator = context['paginator']
        if paginator:
            page = context['page_obj']
            data['page'] = page.number
            data['pages'] = paginator.num_pages
            data['count'] = paginator.count
        return data

    def encode(self, o):
        raise Exception('implement me')


@cors
class IconView(View):
    def get(self, request, *args, **kwargs):
        id = kwargs.get('id', None)
        if id is not None:
            query = IconData.objects.filter(icon__id=kwargs['id'])
        else:
            collection = kwargs.get('collection')
            icon = kwargs.get('icon')
            query = IconData.objects.filter(icon__collection__slug=collection).filter(icon__slug=icon)
        params = request.GET.copy()
        version = params.pop('version', None)
        if version:
            icon = query.filter(version=version)[0]
        else:
            icon = query.latest('version')
        stale = request.META.get('HTTP_IF_MODIFIED_SINCE', None)
        if stale:
            if icon.modified.replace(microsecond=0, tzinfo=None) <= datetime.strptime(stale, _date_fmt):
                return HttpResponseNotModified()
        svg = icon.svg
        if params:
            svg = process_svg(svg, params)
        resp = HttpResponse(svg, content_type='image/svg+xml')
        resp['Last-Modified'] = icon.modified.strftime(_date_fmt)
        return resp


@cors
class IconInfoView(View, JSONMixin):
    def get_context_data(self, **kwargs):
        return Icon.objects.select_related('collection').get(id=kwargs['id'])

    def get_json_data(self, icon):
        versions = [{
            'version' : data.version,
            'modified' : data.modified.isoformat(),
            'changelog' : data.change_log,
        } for data in icon.icondata_set.all()]
        return {
            'collection' : {
                'id': icon.collection.id,
                'name': icon.collection.name
            },
            'name' : icon.name,
            'versions' : versions,
            'tags' : [ { 'id':t.id, 'name':t.name }
                for t in icon.tags.all()
            ]
        }


@cors
class IconList(View, JSONListMixin):
    context_object_name = 'icons'
    paginate_by = 24

    def get_queryset(self):
        query = Icon.objects.all()
        collection = self.kwargs.get('collection', None)
        if collection:
            if collection.isdigit():
                query = query.filter(collection__id=collection)
            else:
                query = query.filter(collection__name=collection)
        tags = self.request.GET.getlist('tag', None)
        if tags:
            query = query.filter(tags__name__in=tags)
        return query.order_by('name').distinct()

    def encode(self, o):
        url = reverse('iconcommons_icon_view', kwargs={'id': o.id})
        return {
            'name': o.name,
            'href': url
        }
        return o.name


@cors
class CollectionList(View, JSONListMixin):
    context_object_name = 'collections'

    def get_queryset(self):
        return Collection.objects.all().annotate(Count('icon')).order_by('name')

    def encode(self, o):
        url = reverse('iconcommons_collection_icons', kwargs={'collection': o.id})
        return {
            'name': o.name,
            'icons': o.icon__count,
            'href': url
        }


@cors
class SearchTags(View, JSONMixin):

    def get_context_data(self, **kwargs):
        query = self.request.GET.get('query', None)
        if query is None:
            return {'tags': []}
        filter = {}
        if len(query) > 3:
            filter['name__icontains'] = query
        else:
            filter['name__istartswith'] = query
        tags = TaggedItem.tags_for(Icon).filter(**filter).order_by('name')
        return {
            'tags': [t.name for t in tags]
        }
