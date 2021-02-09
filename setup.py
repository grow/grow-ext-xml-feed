"""Setup script for extension."""

from setuptools import setup


setup(
    name='grow-ext-xml-feed',
    version='0.1.1',
    license='MIT',
    author='Grow Authors',
    author_email='hello@grow.io',
    include_package_data=False,
    packages=[
        'xml_feed',
    ],
    install_requires=[
        'feedparser>=6.0.2',
        'html2text>=2018.1.9',
        'python-dateutil>=2.7.3',
        'python-slugify>=3.0.2',
        'protorpc==0.11.1',
        'requests>=2.18.4',
    ],
)
