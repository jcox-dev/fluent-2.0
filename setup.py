import os
from setuptools import setup, find_packages

NAME = 'fluent'
PACKAGES = find_packages()
DESCRIPTION = 'A Django translation system'
URL = "https://github.com/potatolondon/fluent"
LONG_DESCRIPTION = open(os.path.join(os.path.dirname(__file__), 'README.md')).read()
AUTHOR = 'Potato London Ltd.'

setup(
    name=NAME,
    version='0.2.0',
    packages=PACKAGES,
    package_data={'': [
        'fluent/templates/admin/fluent/mastertranslation/*.html',
        'fluent/templates/fluent/includes/*.inc',
        'fluent/plurals.xml',
        'fluent/static/fluent/css/*.css',
        'fluent/static/fluent/js/*.js',
        'fluent/static/fluent/js/*.gif',
        'fluent/static/fluent/js/*.png',
    ]},
    include_package_data=True,
    # metadata for upload to PyPI
    author=AUTHOR,
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    keywords=["django", "translation", "Google App Engine", "GAE"],
    url=URL,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Framework :: Django',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
    ]
)
