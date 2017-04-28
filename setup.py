#!/usr/bin/env python
from setuptools import setup, find_packages

setup(
    name='fluffy',
    version="0.0.0",
    url='https://github.com/commoncode/fluffy',
    author="Sebastian Vetter",
    author_email="",
    description="A collection of generic functions for fabric deploy scripts",
    long_description='\n\n'.join([
        open('README.rst').read(),
        open('CHANGELOG.rst').read(),
    ]),
    license='BSD',
    platforms=['linux'],
    packages=find_packages(exclude=["tests*"]),
    include_package_data=True,
    install_requires=[
        'fabric',
    ],
    # See http://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Operating System :: Unix',
        'Programming Language :: Python',
    ]
)
