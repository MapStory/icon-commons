#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup, find_packages

try:
    readme_text = open('README.md', 'rb').read()
except IOError as e:
    readme_text = ''

setup(name="django-icon-commons",
      version="0.0.1",
      description="Icon Commons App",
      long_description=readme_text,
      keywords="",
      license="",
      url="",
      author="Ian Schneider",
      author_email="ischneider@boundlessgeo.com",
      packages=["icon_commons"],
      package_dir={"icon_commons": "icon_commons"},
      install_requires=[
          "django-taggit",
          "lxml",
          "django_extensions",
          "django_nose"
      ],
      classifiers=[
      ],
      )
