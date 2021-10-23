from django.conf.urls import url
from icon_commons.views import SearchTags
from icon_commons.views import CollectionList
from icon_commons.views import IconList
from icon_commons.views import IconView
from icon_commons.views import IconInfoView
from icon_commons.views import upload


urlpatterns = [
    url(r'^$', upload, name='upload'),
    url(r'^search/tags$', SearchTags.as_view(), name='iconcommons_search_tags'),
    url(r'^collections$', CollectionList.as_view(), name='iconcommons_collection_list'),
    url(r'^collections/(?P<collection>[-\w\d]+)$', IconList.as_view(), name='iconcommons_collection_icons'),
    url(r'^icon$', IconList.as_view(), name='iconcommons_icon_list'),
    url(r'^icon/(?P<id>\d+)/info$', IconInfoView.as_view(), name='iconcommons_icon_info_view'),
    url(r'^icon/(?P<id>\d+)$', IconView.as_view(), name='iconcommons_icon_view'),
    url(r'^(?P<collection>[-\w\d]+)/(?P<icon>[-\w\d]+)$', IconView.as_view(), name='iconcommons_icon_by_fqn'),
]
