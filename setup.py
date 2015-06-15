from setuptools import setup, find_packages

setup(
    name='django-components',
    packages=find_packages(exclude='tests'),
    classifiers=[
        'Private :: Do Not Upload',
    ],
    install_requires=[
        'Django>=1.8'
    ],
)
