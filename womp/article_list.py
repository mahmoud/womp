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
        filename_path = self.lookup_path(filename)
        if filename_path:
            return ArticleList.from_file(filename_path)
        if raise_exc:
            raise IOError('file not found for target list: %s' % filename)

    def lookup_path(self, filename, raise_exc=False):
        if not filename:
            return None  # TODO: raise exc here? who uses this?
        search_dir = self._home_path
        target_path = None
        filename = filename + DEFAULT_EXT
        if os.path.isdir(search_dir):
            if os.path.isfile(filename):
                target_path = os.path.join(search_dir, filename)
            elif os.path.isfile(filename + DEFAULT_EXT):
                target_path = os.path.join(search_dir, filename + DEFAULT_EXT)
        if os.path.isfile(filename):
            target_path = filename
        if target_path:
            return target_path
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

    def list_op(self, op_name, target_list, operation_list, limit=None, *a, **kw):
        if op_name not in ListAction.valid_actions:
            raise ValueError('invalid list operation %r' % op_name)
        # argparse can't decode unicode?
        target_list_name = target_list
        target_list = self.lookup(target_list_name, raise_exc=True)
        wc = self.wapiti_client
        try:
            wapiti_operation, wapiti_param = operation_list
        except (ValueError, TypeError):
            search_target = operation_list[0]
            if search_target.startswith('Category:'):
                wapiti_operation = 'get_category_recursive'
                wapiti_param = search_target
            elif search_target.startswith('Template:'):
                wapiti_operation = 'get_transcluded'
                wapiti_param = search_target
            else:
                wapiti_operation = search_target
                wapiti_param = None
        try:
            op = getattr(wc, wapiti_operation)
        except AttributeError:
            print 'No wapiti operation', wapiti_operation
            return
        if wapiti_param:
            page_infos = op(wapiti_param, limit=limit)
        else:
            page_infos = op(limit=limit)
        target_list.append_action(op_name, operation_list, page_infos, wc.api_url)
        target_list.write(self.lookup_path(target_list_name))
        # TODO: summary
        # TODO: tests

    def show(self, target_list=None, **kw):
        article_list = self.lookup(target_list)
        if article_list:
            print json.dumps(article_list.file_metadata, indent=4)
            print '\nTotal articles: ', len(article_list._get_articles()), '\n'
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
        tmpl = '# created={created} name={name} format={format}\n'
        return tmpl.format(created=created, name=name, format=format)

    @property
    def titles(self):
        return [a.name for a in self._get_articles()]

    def __len__(self):
        return len(self._get_articles())

    def append_action(self, action, operation_list, page_infos, source):
        new_action = ListAction(action=action,
                                articles=page_infos,
                                term=operation_list,
                                source=source)
        self.actions.append(new_action)
        pass

    def _get_articles(self):
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
        ret = self.file_metadata_string
        for action in self.actions:
            ret += action.to_string()
        return ret
        '''
        ai = 0
        for i in xrange(len(self.comments) + len(output)):
            if self.comments.get(i) is not None:
                ret.append(self.comments[i])
            else:
                ret.append(output[ai])
                ai += 1
        return '\n'.join(ret)
        '''

    def len_unresolved(self):
        ret = 0
        for action in self.actions:
            ret += action.len_unresolved()
        return ret

    def write(self, path):
        # should write be on ArticleListManager
        output = self.to_string()
        with codecs.open(path, 'w', encoding='utf-8') as f:
            f.write(output)


class ListAction(object):
    metadata_attrs = ('action', 'term', 'date', 'source')
    valid_actions = ('include', 'exclude')

    def __init__(self,
                 action,
                 articles=None,
                 term=None,
                 date=None,
                 source=None,
                 extra_attrs=None):
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
    def from_meta_string(cls, string, default_action='include'):
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

    def to_string(self):
        ret = self.get_meta_string() + '\n'
        tmpl = u'({title}, {id}, {ns}, {subject_id}, {talk_id})\n'
        # if not page infos, get page info
        for article in self.articles:
            try:
                ret += tmpl.format(title=article.title,
                                   id=article.page_id,
                                   ns=article.ns,
                                   subject_id=article.subject_id,
                                   talk_id=article.talk_id)
            except AttributeError:
                ret += article
        return ret

    def len_unresolved(self):
        return len([a for a in self.articles if isinstance(a, basestring)])


def parse_meta_string(string_orig):
    ret = {}
    string = string_orig.strip().lstrip('#').strip()
    parts = string.split()
    for part in parts:
        k, _, v = part.partition('=')
        ret[k] = v
    import pdb; pdb.set_trace()
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
            # remove action id
            try:
                list_action = ListAction.from_meta_string(line)
            except ValueError:
                if not ret_actions:
                    try:
                        file_metadata = parse_meta_string(line)
                        continue
                    except:
                        import pdb;pdb.set_trace
                        pass
                comments[i] = line
            else:
                cur_action = list_action
                ret_actions.append(list_action)
        else:
            if not cur_action:
                # no action metadata
                cur_action = ListAction('include')
                ret_actions.append(cur_action)
            cur_action.articles.append(line)
    return ret_actions, comments, file_metadata


def add_subparsers(subparsers):
    # womp list show
    parser_show = subparsers.add_parser('show')
    parser_show.add_argument('target_list', nargs='?',
                             help='Name of the list or list file')
    parser_show.set_defaults(func_name='show')

    # womp list create *listname
    parser_create = subparsers.add_parser('create')
    parser_create.add_argument('target_list',
                               help='name of the list or list file')
    parser_create.set_defaults(func_name='create')

    # womp list *arg *listname *wapitisource
    op_parser = ArgumentParser(description='parses generic search op args.',
                               add_help=False)
    op_parser.add_argument('target_list',
                           help='name or path of article list')
    op_parser.add_argument('operation_list', nargs='*',
                           help='article, category, or template')
    op_parser.add_argument('--limit', '-l', type=int,
                           default=DEFAULT_LIMIT,
                           help='number of articles')
    op_parser.set_defaults(func_name='list_op')

    # actions
    parser_include = subparsers.add_parser('include', parents=[op_parser])
    parser_include.set_defaults(op_name='include')
    parser_exclude = subparsers.add_parser('exclude', parents=[op_parser])
    parser_exclude.set_defaults(op_name='exclude')
    '''
    # someday
    parser_intersect = subparsers.add_parser('intersect', parents=[op_parser])
    parser_intersect.set_defaults(op_name='intersect')
    parser_xor = subparsers.add_parser('xor', parents=[op_parser])
    parser_xor.set_defaults(op_name='xor')
    '''
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
    parser = create_parser()
    args = parser.parse_args()
    kwargs = dict(args._get_kwargs())

    list_home = kwargs.pop('list_home', None)
    alm = ArticleListManager(list_home)

    func_name = kwargs.pop('func_name')
    getattr(alm, func_name)(**kwargs)


if __name__ == '__main__':
    try:
        main()
    except:
        import pdb;pdb.post_mortem()
        raise
