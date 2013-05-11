"""
    womp
    ~~~~

    womp (Wikipedia Open Metrics Platform) is a workflow-oriented
    suite, used for the collection, extraction, processing, and
    management of data from Wikipedia APIs.

    :copyright: (c) 2013 by Mahmoud Hashemi and Stephen LaPorte
    :license: GPL, see LICENSE for more details.

"""

import sys
from setuptools import setup


__author__ = 'Mahmoud Hashemi and Stephen LaPorte'
__version__ = '0.0.1'
__contact__ = 'mahmoudrhashemi@gmail.com'
__url__ = 'https://github.com/mahmoud/womp'
__license__ = 'GPL'

desc = ('Wikipedia Open Metrics Platform: data collection, '
        'extraction, and management.')

if sys.version_info < (2, 6):
    raise NotImplementedError("Sorry, womp only supports Python >2.6")

if sys.version_info >= (3,):
    raise NotImplementedError("womp Python 3 support still en route")


setup(name='womp',
      version=__version__,
      description=desc,
      long_description=__doc__,
      author=__author__,
      author_email=__contact__,
      url=__url__,
      packages=['womp',
                'womp.inputs'],
      include_package_data=True,
      zip_safe=False,
      install_requires=['clastic',
                        'pyquery',
                        'lxml>=3.1',
                        'Mako',
                        'psutil'],
      license=__license__,
      platforms='any',
      classifiers=['Programming Language :: Python :: 2.7'])
