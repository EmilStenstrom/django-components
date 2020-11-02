# -*- coding: utf-8 -*-
import os

from setuptools import find_packages, setup

VERSION = '0.4.1'

setup(
    name="django_reusable_components",
    packages=find_packages(exclude=["tests"]),
    version=VERSION,
    description="A way to create simple reusable template components in Django.",
    long_description=open(os.path.join(os.path.dirname(__file__), "README.md")).read(),
    long_description_content_type="text/markdown",
    author=u"Emil Stenström",
    author_email="em@kth.se",
    url="https://github.com/EmilStenstrom/django-components/",
    install_requires=["Django>=1.11", "six"],
    license="MIT",
    keywords=["django", "components", "css", "js", "html"],
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Operating System :: OS Independent",
        "Framework :: Django"
    ],
)
