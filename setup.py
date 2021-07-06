# -*- coding: utf-8 -*-
import os

from setuptools import find_packages, setup

VERSION = '0.15'

setup(
    name="django_components",
    packages=find_packages(exclude=["tests"]),
    version=VERSION,
    description="A way to create simple reusable template components in Django.",
    long_description=open(os.path.join(os.path.dirname(__file__), "README.md")).read(),
    long_description_content_type="text/markdown",
    author=u"Emil Stenström",
    author_email="emil@emilstenstrom.se",
    url="https://github.com/EmilStenstrom/django-components/",
    install_requires=["Django>=2.2"],
    license="MIT",
    keywords=["django", "components", "css", "js", "html"],
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Operating System :: OS Independent",
        "Framework :: Django",
        "Framework :: Django :: 2.2",
        "Framework :: Django :: 3.0",
        "Framework :: Django :: 3.1",
        "Framework :: Django :: 3.2",
    ],
)
