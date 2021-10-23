from django.db import models
from django.db import transaction
from django.template.defaultfilters import slugify
from taggit.managers import TaggableManager
from base64 import b64encode
from django.conf import settings


class SlugMixin(models.Model):

    name = models.CharField(max_length=128)
    slug = models.CharField(max_length=128)

    def save(self, *args, **kw):
        self.slug = slugify(self.name)
        super(SlugMixin, self).save(*args, **kw)

    class Meta:
        abstract = True


class IconData(models.Model):

    svg = models.TextField()
    version = models.PositiveSmallIntegerField()
    change_log = models.TextField(null=True)
    icon = models.ForeignKey('icon_commons.Icon', on_delete=models.CASCADE)
    modified = models.DateTimeField(auto_now=True)

    def data_uri(self):
        b64 = b64encode(self.svg().encode('utf-8-sig'))
        return 'data:image/svg+xml;base64,%s' % b64

    def __unicode__(self):
        return 'IconData %s %s' % (self.icon.name, self.version)

    class Meta:
        unique_together = ('icon', 'version')


class Icon(SlugMixin):

    owner = models.ForeignKey(settings.AUTH_USER_MODEL, blank=True, null=True, on_delete=models.CASCADE)
    collection = models.ForeignKey('icon_commons.Collection', on_delete=models.CASCADE)
    tags = TaggableManager()
    modified = models.DateTimeField(auto_now=True)

    def current_icon_data(self):
        return IconData.objects.filter(icon=self).latest('version')

    @transaction.atomic
    def new_version(self, svg, change_log):
        try:
            latest = self.icondata_set.latest('version').version
        except IconData.DoesNotExist:
            latest = 0
        data = IconData.objects.create(svg=svg,
                                       version=latest + 1,
                                       change_log=change_log,
                                       icon=self)
        self.save()
        return data

    class Meta:
        unique_together = ('name', 'collection')


class Collection(SlugMixin):

    description = models.TextField(null=True)
