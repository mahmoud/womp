# -*- coding: utf-8 -*-
from setuptools import setup

setup(
    name='womp',
    description='Wikipedia Open Metrics Platform: data collection, extraction, and management',
    version='0.0.1dev',
    license='BSD',
    author='Mahmoud Hashemi and Stephen LaPorte',
    author_email='mahmoudrhashemi@gmail.com',
    url='https://github.com/mahmoud/womp',
    long_description=__doc__,
    classifiers=(
        #'Development Status :: 4 - Beta',
        #'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python :: 2',
        #'Programming Language :: Python :: 3',
        #'Topic :: Internet :: WWW/HTTP',
        #'Topic :: Internet :: WWW/HTTP :: Dynamic Content',
        #'Topic :: Text Processing :: Markup',
    ),
    py_modules=('womp',),
    platforms='any'
)
