from setuptools import find_packages, setup

setup(
    name='django-components',
    packages=find_packages(exclude='tests'),
    classifiers=[
        'Private :: Do Not Upload',
    ],
    install_requires=[
        'Django>=1.7'
    ],
)
