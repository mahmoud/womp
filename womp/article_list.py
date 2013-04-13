from __future__ import unicode_literals

import os
import json
import codecs
from datetime import datetime
from collections import namedtuple
from argparse import ArgumentParser

DEFAULT_LIMIT = 100
DEFAULT_SOURCE = 'enwiki'
FORMAT = 'v1'

###########
DATE_FORMAT = '%Y-%m-%dT%H:%M:%S'
DEFAULT_EXT = '.txt'

ArticleIdentifier = namedtuple('ArticleIdentifier', 'name source')


class ArticleListManager(object):
    def __init__(self, env_or_path=None):
        if not env_or_path or isinstance(env_or_path, basestring):
            self.env = None
            defpath = env_or_path or os.getenv('WOMP_LIST_HOME') or os.getcwd()
            self._home_path = defpath
        else:
            self.env = env_or_path
            self._home_path = self.env.list_home
        self._wapiti_client = None

    def lookup(self, filename, raise_exc=False):
        if not filename:
            return None  # TODO: raise exc here? who uses this?
        search_dir = self._home_path
        target_path = None
        if os.path.isdir(search_dir):
            if os.path.isfile(filename):
                target_path = os.path.join(search_dir, filename)
            elif os.path.isfile(filename + DEFAULT_EXT):
                target_path = os.path.join(search_dir, filename + DEFAULT_EXT)
        if os.path.isfile(filename):
            target_path = filename
        if target_path:
            return ArticleList.from_file(target_path)
        if raise_exc:
            raise IOError('file not found for target list: %s' % target_list)
        return None

    def get_full_list(self):
        ret = []
        try:
            ret.extend([fn for fn in os.listdir(self._home_path)
                        if fn.endswith(DEFAULT_EXT)])
        except IOError:
            pass
        return ret

    @property
    def output_path(self):
        return self._home_path

    @property
    def wapiti_client(self):
        if self._wapiti_client:
            return self._wapiti_client
        if self.env:
            self.env.get_wapiti_client()
        else:
            # testing only, I think
            from wapiti import WapitiClient
            self._wapiti_client = WapitiClient('mahmoudrhashemi@gmail.com')
            return self._wapiti_client

    def list_op(self, op_name, search_target, target_list, limit=None, **kw):
        target_list = self.lookup(target_list, raise_exc=True)
        wc = self.wapiti_client
        if search_target.startswith('Category:'):
            article_list = wc.get_category_recursive(search_target, limit)
        elif search_target.startswith('Template:'):
            article_list = wc.get_transcluded(search_target, limit)

        if op_name == 'include':
            a_list.include([a[2] for a in article_list], source=DEFAULT_SOURCE, term=search_target)
            a_list.write(target_list)
        elif op_name == 'exclude':
            a_list.exclude([a[2] for a in article_list], source=DEFAULT_SOURCE, term=search_target)
            a_list.write(target_list)
        # TODO: summary
        # TODO: tests

    def show(self, target_list=None, **kw):
        article_list = self.lookup(target_list)
        if article_list:
            print json.dumps(article_list.file_metadata, indent=4)
            print '\nTotal articles: ', len(article_list.get_articles()), '\n'
        elif article_list is None:
            print 'Article lists in', self._home_path
            print '\n'.join(self.get_full_list())

    def create(self, target_list, **kw):
        existent = self.lookup(target_list)
        if existent:
            raise IOError('list already exists: %s' % target_list)
        if not target_list or '.' in target_list:
            raise ValueError('expected non-empty string without dots')

        out_filename = os.path.join(self.output_path, target_list + DEFAULT_EXT)
        codecs.open(out_filename, 'w', encoding='utf-8').close()
        print 'Created article list %s' % out_filename


class ArticleList(object):
    def __init__(self, actions=None, comments=None, file_metadata=None):
        if actions is None:
            actions = []
        self.actions = actions
        self.comments = comments or {}
        self.file_metadata = file_metadata or {}

    @classmethod
    def from_file(cls, path):
        with codecs.open(path, 'r', encoding='utf-8') as f:
            f_contents = f.read()
        return cls.from_string(f_contents)

    @classmethod
    def from_string(cls, contents):
        actions, comments, file_metadata = al_parse(contents)
        return cls(actions, comments, file_metadata)

    @property
    def next_action_id(self):
        return len(self.actions) + 1

    @property
    def file_metadata_string(self):
        date = datetime.utcnow()
        created = self.file_metadata.get('created',
                                         datetime.strftime(date, DATE_FORMAT))
        name = self.file_metadata.get('name', '(unknown)')
        format = self.file_metadata.get('format', FORMAT)
        tmpl = '# created={created} name={name} format={format}'
        return tmpl.format(created=created, name=name, format=format)

    @property
    def titles(self):
        return [a.name for a in self.get_articles()]

    def include(self, article_list, term=None, source=None):
        self.do_action('include', article_list, term=term, source=source)

    def exclude(self, article_list, term=None, source=None):
        self.do_action('exclude', article_list, term=term, source=source)

    def xor(self):
        # todo
        pass

    def do_action(self, action, article_list, term=None, source=None):
        newact = ListAction(id=self.next_action_id,
                            action=action,
                            articles=article_list,
                            term=term,
                            source=source)
        self.actions.append(newact)

    def get_articles(self):
        article_set = set()
        for action in self.actions:
            action_articles = set([ArticleIdentifier(a, action.source)
                                    for a in action.articles])
            if action.action == 'include':
                article_set = article_set.union(action_articles)
            elif action.action == 'exclude':
                article_set = article_set - action_articles
            else:
                raise Exception('wut')
        return article_set

    def to_string(self):
        #todo: file metadata
        output = []
        i = 0
        for action in self.actions:
            meta_str = action.get_meta_string()
            output.append(meta_str)
            output += action.articles

        ret = [self.file_metadata_string]
        ai = 0
        for i in xrange(len(self.comments) + len(output)):
            if self.comments.get(i) is not None:
                ret.append(self.comments[i])
            else:
                ret.append(output[ai])
                ai += 1
        return '\n'.join(ret)

    def write(self, path):
        output = self.to_string()
        with codecs.open(path, 'w', encoding='utf-8') as f:
            f.write(output)


class ListAction(object):
    metadata_attrs = ('id', 'action', 'term', 'date', 'source')
    valid_actions = ('include', 'exclude')

    def __init__(self,
                 id,
                 action,
                 articles=None,
                 term=None,
                 date=None,
                 source=None,
                 extra_attrs=None):
        self.id = id
        self.action = action
        self.term = term or '(custom)'
        if date is None:
            date = datetime.utcnow()
        elif isinstance(date, basestring):
            date = datetime.strptime(date, DATE_FORMAT)
        elif not hasattr(date, 'strftime'):
            raise ValueError('expected date-like object for argument "date"')
        self.date = date
        self.source = source or DEFAULT_SOURCE
        self.extra_attrs = extra_attrs or {}
        if articles is None:
            articles = []
        self.articles = articles

    @classmethod
    def from_meta_string(cls, string, default_id=1, default_action='include'):
        metadata = parse_meta_string(string)
        extra_attrs = {}
        kw = {}
        for k in metadata:
            if k in cls.metadata_attrs:
                kw[k] = metadata[k]
            else:
                extra_attrs[k] = metadata[k]
        if not kw:
            raise ValueError('no metadata found')
        if not kw.get('id'):
            kw['id'] = default_id
        if not kw.get('action'):
            kw['action'] = default_action
        if kw['action'] not in cls.valid_actions:
            raise ValueError('unrecognized action: ' + str(kw['action']))
        kw['extra_attrs'] = extra_attrs
        return cls(**kw)

    def get_meta_string(self):
        ret = '# '
        for attr in self.metadata_attrs:
            attrval = getattr(self, attr)
            if hasattr(attrval, 'strftime'):
                attrval = attrval.strftime(DATE_FORMAT)
            ret += str(attr) + '=' + str(attrval) + ' '
        return ret


def parse_meta_string(string_orig):
    ret = {}
    string = string_orig.strip().lstrip('#').strip()
    parts = string.split()
    for part in parts:
        k, _, v = part.partition('=')
        ret[k] = v
    return ret


def al_parse(contents):
    lines = contents.splitlines()
    file_metadata = ''
    cur_action = None
    ret_actions = []
    comments = {}
    for i, orig_line in enumerate(lines):
        line = orig_line.strip()
        if not line:
            comments[i] = ''
            continue
        if line.startswith("#"):
            default_id = len(ret_actions) + 1
            try:
                list_action = ListAction.from_meta_string(line,
                                                          default_id)
            except ValueError:
                if not ret_actions:
                    try:
                        file_metadata = parse_meta_string(line)
                        continue
                    except:
                        pass
                comments[i] = line
            else:
                cur_action = list_action
                ret_actions.append(list_action)
        else:
            if not cur_action:
                cur_action = ListAction(1, 'include')
                ret_actions.append(cur_action)
            cur_action.articles.append(line)
    return ret_actions, comments, file_metadata


def add_subparsers(subparsers):
    parser_show = subparsers.add_parser('show')
    parser_show.add_argument('target_list', nargs='?',
                             help='Name of the list or list file')
    parser_show.set_defaults(func_name='show')

    parser_create = subparsers.add_parser('create')
    parser_create.add_argument('target_list',
                               help='name of the list or list file')
    parser_create.set_defaults(func_name='create')

    op_parser = ArgumentParser(description='parses generic search op args.',
                               add_help=False)
    op_parser.add_argument('search_target',
                           help='article, category, or template')
    op_parser.add_argument('target_list',
                           help='name or path of article list')
    op_parser.add_argument('--limit', '-l', type=int,
                           default=DEFAULT_LIMIT,
                           help='number of articles')
    op_parser.add_argument('--recursive', '-R', action='store_true',
                           help='Fetch recursively')
    op_parser.set_defaults(func_name='list_op')

    parser_include = subparsers.add_parser('include', parents=[op_parser])
    parser_include.set_defaults(op_name='include')

    parser_exclude = subparsers.add_parser('exclude', parents=[op_parser])
    parser_exclude.set_defaults(op_name='exclude')

    return


def create_parser():
    """
    Only called when article_list is used directly (i.e., when there
    is no WompEnv).
    """
    root_parser = ArgumentParser(description='article list operations')
    root_parser.add_argument('--list_home', help='list lookup directory')
    add_subparsers(root_parser.add_subparsers())
    return root_parser


def main():
    import sys
    parser = create_parser()
    args = parser.parse_args()
    kwargs = dict(args._get_kwargs())
    for k, v in kwargs.items():
        if not isinstance(v, unicode):
            try:
                kwargs[k] = v.decode(sys.stdin.encoding)
            except AttributeError:
                pass

    list_home = kwargs.pop('list_home', None)
    alm = ArticleListManager(list_home)

    func_name = kwargs.pop('func_name')
    getattr(alm, func_name)(**kwargs)


if __name__ == '__main__':
    main()
