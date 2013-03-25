from __future__ import unicode_literals
import os
from os.path import join as pjoin
import shutil
import ConfigParser
from argparse import ArgumentParser

from wapiti import WapitiClient

import article_list
#import fetch

_DEFAULT_DIR_PERMS = 0755
_CURDIR = os.path.abspath(os.path.dirname(__file__))
_CONF_NAME = 'womp.conf'


class WompEnv(object):
    def __init__(self, config, path):
        self.config = config
        self.path = path

        self.list_manager = article_list.ArticleListManager(self)

    @classmethod
    def from_path(cls, path=None, config_name=_CONF_NAME):
        path = path or os.getenv('WOMP_HOME') or os.getcwd()
        path = os.path.normpath(path)
        config = ConfigParser.SafeConfigParser()
        config.read(pjoin(path, config_name))

        return cls(config, path)

    @classmethod
    def init_new(cls, path):
        path = os.path.normpath(path)
        if os.path.exists(path):
            # TODO: force?
            raise IOError('path already exists: %s' % path)

        os.makedirs(path, _DEFAULT_DIR_PERMS)
        os.mkdir(pjoin(path, 'article_lists'), _DEFAULT_DIR_PERMS)
        os.mkdir(pjoin(path, 'inputs'), _DEFAULT_DIR_PERMS)
        os.mkdir(pjoin(path, 'fetch_data'), _DEFAULT_DIR_PERMS)
        os.mkdir(pjoin(path, 'projects'), _DEFAULT_DIR_PERMS)

        _init_default_config(path)

        return cls.from_path(path)

    @property
    def list_home(self):
        return pjoin(self.path, 'article_lists')

    def get_wapiti_client(self):
        if self._wapiti_client:
            return self._wapiti_client
        email = self.config.get('user', 'email')
        self._wapiti_client = WapitiClient(email)
        return self._wapiti_client


def _init_default_config(path):
    init_conf = pjoin(path, _CONF_NAME)
    shutil.copyfile(pjoin(_CURDIR, 'default.conf'), init_conf)
    os.chmod(init_conf, 0600)


def init_home(path, **kw):
    WompEnv.init_new(path)


def create_parser():
    prs = ArgumentParser(description='womp: Wikipedia Open Metrics Platform')
    prs.add_argument('--home', help='path to womp home directory')
    subprs = prs.add_subparsers()

    prs_init = subprs.add_parser('init')
    prs_init.set_defaults(subparser_name='init')
    prs_init.add_argument('path', nargs=1,
                          help='path of new womp home directory')
    prs_init.set_defaults(func_name='init_new')

    prs_list = subprs.add_parser('list')
    prs_list.set_defaults(subparser_name='list')
    article_list.add_subparsers(prs_list.add_subparsers())

    #prs_fetch = subprs.add_parser('fetch')
    #prs_fetch.set_defaults(subparser_name='fetch')
    #fetch.add_subparsers(prs_fetch.add_subparsers())

    return prs


def get_decoded_kwargs(args):
    import sys
    kwargs = dict(args._get_kwargs())
    for k, v in kwargs.items():
        if not isinstance(v, unicode):
            try:
                kwargs[k] = v.decode(sys.stdin.encoding)
            except AttributeError:
                pass
    return kwargs


def main():
    parser = create_parser()
    args = parser.parse_args()
    kwargs = get_decoded_kwargs(args)
    subparser_name = kwargs.pop('subparser_name')
    func_name = kwargs.pop('func_name')
    if func_name == 'init_new':
        path = kwargs['path'][0]  # friggin nargs=1
        WompEnv.init_new(path)
    else:
        womp_env = WompEnv.from_path(kwargs['home'])
        if subparser_name == 'list':
            getattr(womp_env.list_manager, func_name)(**kwargs)
        else:
            raise ValueError('unrecognized subparser: %r' % subparser_name)

if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        import pdb;pdb.post_mortem()
        raise
