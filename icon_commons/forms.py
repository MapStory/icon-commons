from django import forms
from taggit.forms import TagField

class IconForm(forms.Form):
	tags = TagField()
	svg = forms.FileField()
	collection = forms.CharField(max_length=128, required=False)