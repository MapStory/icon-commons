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
from icon_commons.forms import IconForm
from icon_commons.utils import process_svg
from taggit.models import TaggedItem
import json
from datetime import datetime
import zipfile
from django.shortcuts import render_to_response
from django.http import HttpResponseRedirect
from django.template import RequestContext
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth.decorators import login_required

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
                        'version': data.version,
                        'modified': data.modified.isoformat(),
                        'changelog': data.change_log,
                    } for data in icon.icondata_set.all()]
        return {
            'collection': {
                'id': icon.collection.id,
                'name': icon.collection.name
            },
            'name': icon.name,
            'versions': versions,
            'tags': [{'id': t.id, 'name': t.name}
                     for t in icon.tags.all()
                     ]
        }


@cors
class IconList(View, JSONListMixin):
    context_object_name = 'icons'
    paginate_by = 100

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
            'owner': o.owner,
            'href': url
        }
    

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


@login_required
# Notes: error proof the splits
def upload(req):
    if req.method == 'POST':
        form = IconForm(req.POST, req.FILES)
        if form.is_valid():
            tags = form.cleaned_data['tags']
            # This should be the same as form.cleaned_data['svg'] I think
            svg = req.FILES['svg']
            collection_name = form.cleaned_data['collection']
            # If they defined a collection name, use that. Otherwise, use the name of the file/zip
            col_name = collection_name if collection_name else svg.name.split('.')[0]
            # Two possibilities we want to handle:
            # a) it's a .zip, so unzip it and ingest all files
            # b) it's a .svg, so just ingest this one file
            file_type = svg.name.split('.')[1]
            if file_type == 'zip':
                unzipped = zipfile.ZipFile(svg)
                for file_name in unzipped.namelist():
                    # If it doesn't have an extension, skip it
                    if len(file_name.split('.')) == 1:
                        continue
                    unzipped_type = file_name.split('.')[1]
                    if unzipped_type != 'svg':
                        continue
                    col, col_created = Collection.objects.get_or_create(name=col_name)
                    icon_name = file_name.split('.')[0].split('/')[1]  # NOTE: not sure if this is correct to do on all OS's...
                    icon, icon_created = Icon.objects.get_or_create(name=icon_name, collection=col, owner=req.user)
                    msg = 'initial import' if icon_created else 'automatic update'
                    # Add tags to the icon
                    icon.tags.add(*tags)
                    data = unzipped.read(file_name)
                    updated = True
                    try:
                        latest = icon.icondata_set.latest('version')
                        updated = latest.svg == data
                    except ObjectDoesNotExist:
                        pass
                    if updated:
                        icon.new_version(data, msg)  # Pass req.user
                    icon.save()
            elif file_type == 'svg':
                col, col_created = Collection.objects.get_or_create(name=col_name)
                icon_name = svg.name.split('.')[0]
                icon, icon_created = Icon.objects.get_or_create(name=icon_name, collection=col, owner=req.user)
                msg = 'initial import' if icon_created else 'automatic update'
                icon.tags.add(*tags)
                data = svg.read()
                updated = True
                try:
                    latest = icon.icondata_set.latest('version')
                    updated = latest.svg == data
                except ObjectDoesNotExist:
                    pass
                if updated:
                    icon.new_version(data, msg)
                icon.save()
            else:
                return HttpResponseRedirect(reverse('icon_upload'))
    else:
        form = IconForm()
    return render_to_response('icons/icon_upload.html', RequestContext(req, {"icon_form": form}))
