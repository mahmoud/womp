from __future__ import unicode_literals
import os
from os.path import join as pjoin
import shutil

import ConfigParser
from argparse import ArgumentParser

import fetch
import article_list
import dashboard
from wapiti import WapitiClient

_DEFAULT_DIR_PERMS = 0755
_CURDIR = os.path.abspath(os.path.dirname(__file__))
_CONF_NAME = 'womp.conf'


"""
Config values:
* General
  * user email
  * dashboard settings
  * debug (debug level)
* List
  * TBD
* Fetch
  * concurrency level
  * fetch limits
  * inputs
"""


class WompEnv(object):
    def __init__(self, config, path):
        self.config = config
        self.path = path

        self.list_home = pjoin(path, 'article_lists')
        self.list_manager = article_list.ArticleListManager(self)

        self.fetch_home = pjoin(path, 'fetch')
        self.fetch_manager = fetch.FetchManager(self)

        self.dashboard = dashboard.create_dashboard(self)

    def handle_action(self, action_group, **kwargs):
        if action_group == 'list':
            manager = self.list_manager
        elif action_group == 'fetch':
            manager = self.fetch_manager
        else:
            raise ValueError('unrecognized action group %r' % (action_group,))
        try:
            method_name = kwargs['method']
            method = getattr(manager, method_name)
        except KeyError:
            raise ValueError("expected 'method' argument")
        except AttributeError:
            raise ValueError('unknown method %r' % (method_name,))
        return method(**kwargs)

    @classmethod
    def from_path(cls, path=None, config_name=_CONF_NAME):
        path = path or os.getenv('WOMP_HOME') or os.getcwd()
        path = os.path.normpath(path)
        config = ConfigParser.SafeConfigParser()
        config.read(pjoin(path, config_name))

        return cls(config, path)

    @classmethod
    def init_new(cls, path):
        if not isinstance(path, basestring):
            path = path[0]  # friggin nargs=1
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

    def get_wapiti_client(self):
        if getattr(self, '_wapiti_client', None):
            return self._wapiti_client
        email = self.config.get('user', 'email')
        self._wapiti_client = WapitiClient(email)
        return self._wapiti_client

    def start_dashboard(self):
        self.dashboard.serve(use_reloader=False,
                             static_prefix='static',
                             port=5000,  # TODO
                             static_path=dashboard.STATIC_PATH)  # TODO


def _init_default_config(path):
    init_conf = pjoin(path, _CONF_NAME)
    shutil.copyfile(pjoin(_CURDIR, 'default.conf'), init_conf)
    os.chmod(init_conf, 0600)


def create_parser():
    prs = ArgumentParser(description='WOMP: Wikipedia Open Metrics Platform')
    prs.add_argument('--home', help='path to WOMP home directory')
    subs = prs.add_subparsers()

    prs_init = subs.add_parser('init',
                               description='create a new WOMP environment')
    prs_init.set_defaults(action_group='init')
    prs_init.add_argument('path', nargs=1,
                          help='path of new WOMP home directory')

    prs_list = subs.add_parser('list',
                               description='create and manipulate collections of articles')
    prs_list.set_defaults(action_group='list')
    article_list.add_subparsers(prs_list.add_subparsers())

    prs_fetch = subs.add_parser('fetch',
                                description='gather data for articles in a given list')
    prs_fetch.set_defaults(action_group='fetch')
    fetch.create_parser(prs_fetch)

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
    womp_env = None
    if args.action_group == 'init':
        return WompEnv.init_new(kwargs['path'])
    else:
        womp_env = WompEnv.from_path(kwargs['home'])
        return womp_env.handle_action(**kwargs)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        import pdb;pdb.post_mortem()
        raise
