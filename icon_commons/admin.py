from django.contrib import admin
from icon_commons.models import Icon, IconData

# Register your models here.

class IconDataAdmin(admin.ModelAdmin):
	model = IconData

class IconAdmin(admin.ModelAdmin):
	model = Icon

admin.site.register(Icon, IconAdmin)
admin.site.register(IconData, IconDataAdmin)