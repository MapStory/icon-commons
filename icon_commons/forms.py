from django import forms
from taggit.forms import TagField
from django.core.exceptions import ValidationError


# Validate to make sure that we're only allowing SVG or Zip files.
def validate_file_extension(value):
    if (not value.name.endswith('.svg')) and (not value.name.endswith('.zip')):
        raise ValidationError('Invalid File Type!')


# Create our Icon Form and setup requirements and validators.
class IconForm(forms.Form):
    tags = TagField(required=True)
    svg = forms.FileField(required=True, validators=[validate_file_extension])