from __future__ import unicode_literals

import os
from os.path import join as pjoin
import sys
import json
import codecs
from datetime import datetime
from collections import namedtuple
from argparse import ArgumentParser
from wapiti.operations.models import PageInfo

DEFAULT_LIMIT = 100
DEFAULT_SOURCE = 'enwiki'
FORMAT = 'v1'

###########
DATE_FORMAT = '%Y-%m-%dT%H:%M:%S'
DEFAULT_EXT = '.txt'
TEST_LIST_NAME = 'test_list'

UnresolvedPage = namedtuple('UnresolvedPage', 'title')


def get_max_width(table, index):
    """Get the maximum width of the given column index"""
    return max([len(str(row[index])) for row in table])


def pprint_table(table):
    """Prints out a table of data, padded for alignment
    @param out: Output stream (file-like object)
    @param table: The table to print. A list of lists.
    Each row must have the same number of columns. """
    col_paddings = []

    for i in range(len(table[0])):
        col_paddings.append(get_max_width(table, i))

    for row in table:
        # left col
        print str(row[0]).ljust(col_paddings[0] + 1),
        # rest of the cols
        for i in range(1, len(row)):
            col = str(row[i]).rjust(col_paddings[i] + 2)
            print col,
        print


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

    def load_list(self, filename, raise_exc=False):
        if not filename:
            return None  # TODO: raise exc here? who uses this?
        filename_path = self._lookup_path(filename)
        if filename_path:
            return ArticleList.from_file(filename_path)
        if raise_exc:
            raise IOError('file not found for target list: %s' % filename)

    def get_list_dict(self, filename):
        article_list = self.load_list(filename)
        ret = {'total': len(article_list.get_articles()),
               'unresolved': len(article_list._get_unresolved_articles()),
               'actions': len(article_list.actions),
               'date': article_list.file_metadata.get('date', 'new'),
               'name': filename}
        return ret

    def _lookup_path(self, filename, raise_exc=False):
        if not filename:
            return None  # TODO: raise exc here? who uses this?
        search_dir = self._home_path
        target_path = None
        if os.path.isdir(search_dir):
            full_path = pjoin(search_dir, filename)
            if os.path.isfile(full_path):
                target_path = full_path
            elif os.path.isfile(full_path + DEFAULT_EXT):
                target_path = full_path + DEFAULT_EXT
        elif os.path.isfile(filename):
            target_path = filename
        if target_path:
            return target_path
        if raise_exc:
            raise IOError('file not found for target list: %s' % filename)
        return None

    def _get_full_list(self):
        ret = []
        try:
            ret.extend([fn.rsplit(DEFAULT_EXT, 1)[0] for fn in os.listdir(self._home_path)
                        if fn.endswith(DEFAULT_EXT)])
        except IOError:
            pass
        return ret

    def get_all_list_dicts(self):
        als = []
        article_lists = self._get_full_list()
        for article_list_name in article_lists:
            als.append(self.get_list_dict(article_list_name))
        return als

    @property
    def output_path(self):
        return self._home_path

    @property
    def wapiti_client(self):
        if self.env:
            return self.env.get_wapiti_client()
        else:
            # testing only, I think
            if self._wapiti_client:
                return self._wapiti_client
            from wapiti import WapitiClient
            self._wapiti_client = WapitiClient('mahmoudrhashemi@gmail.com')
            return self._wapiti_client

    def append_action(self, listname, meta_str, articles):
        new_article_list = self.load_list(listname)
        new_action = ListAction.from_meta_string(meta_str)
        new_action.articles.extend(articles)
        new_article_list.actions.append(new_action)
        self.write(new_article_list, listname)
        return

    def list_op(self,
                op_name,
                target_list,
                operation_list,
                limit=None,
                *a, **kw):
        if op_name not in ListAction.valid_actions:
            raise ValueError('invalid list operation %r' % op_name)
        # argparse can't decode unicode?
        target_list_name = target_list
        target_list = self.load_list(target_list_name, raise_exc=True)
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
        self.write(target_list, target_list_name)
        print 'List:', target_list_name + ';'
        print target_list.summarize()

    def resolve_the_unresolved(self, target_list):
        wc = self.wapiti_client
        t_list = self.load_list(target_list)
        for a, action in enumerate(t_list.actions):
            for i, article in enumerate(action.articles):
                if isinstance(article, UnresolvedPage):
                    # TODO: batch?
                    try:
                        t_list.actions[a].articles[i] = wc.get_page_info(article.title)[0]
                    except IndexError:
                        # no wapiti result
                        t_list.actions[a].articles[i] = article.title
        self.write(t_list, target_list)

    def show(self, target_list=None, **kw):
        article_list = self.load_list(target_list)
        if article_list:
            print json.dumps(article_list.file_metadata, indent=4)
            print '\nTotal articles: ', len(article_list.get_articles()), '\n'
        elif article_list is None:
            article_lists = self.get_all_list_dicts()
            als = [['Articles', 'Unresolved', 'Actions', 'Updated', 'Name']]
            for al in article_lists:
                als.append([al['total'],
                            al['unresolved'],
                            al['actions'],
                            al['date'],
                            al['name']])
            print 'Article lists in', self._home_path
            if len(als) > 1:
                pprint_table(als)
            else:
                print 'none'

    def show_operations(self):
        import wapiti
        from pprint import pprint
        ret = []
        for op in wapiti.operations.ALL_OPERATIONS:
            ret_type = getattr(op, 'singular_output_type', None)
            if ret_type and issubclass(ret_type, wapiti.operations.models.PageInfo):
                ret.append(op)
        pprint([wapiti.client.camel2under(o.__name__) for o in ret])

    def create(self, target_list, **kw):
        existent = self.load_list(target_list)
        if existent:
            raise IOError('list already exists: %s' % target_list)
        if not target_list or '.' in target_list:
            raise ValueError('expected non-empty string without dots')

        out_filename = os.path.join(self.output_path, target_list + DEFAULT_EXT)
        codecs.open(out_filename, 'w', encoding='utf-8').close()
        print 'Created article list %s' % out_filename

    def write(self, target_list, list_name):
        # should write be on ArticleListManager
        output = target_list.to_string()
        full_path = self._lookup_path(list_name)
        with codecs.open(full_path, 'w', encoding='utf-8') as f:
            f.write(output)


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
        now = datetime.utcnow().strftime(DATE_FORMAT)
        ret = u'###'
        ret_dict = {'date': now,
                    'created': self.file_metadata.get('created', now),
                    'name': self.file_metadata.get('name', '(unknown)'),
                    'format': self.file_metadata.get('format', FORMAT)}
        return ret + json.dumps(ret_dict) + u'\n'

    @property
    def titles(self):
        return [a.name for a in self.get_articles()]

    def __len__(self):
        return len(self.get_articles())

    def append_action(self, action, operation_list, page_infos, source):
        new_action = ListAction(action=action,
                                articles=page_infos,
                                term=operation_list,
                                source=source)
        self.actions.append(new_action)
        pass

    def get_articles(self):
        article_set = []
        for action in self.actions:
            if action.action == 'include':
                for cur_article in action.articles:
                    if cur_article.title not in [a.title for a in article_set]:
                        article_set.append(cur_article)
            elif action.action == 'exclude':
                article_set = [a for a in article_set if a.title not in
                              [e.title for e in action.articles]]
            else:
                raise Exception('wut')
        return article_set

    def _get_unresolved_articles(self):
        all_articles = self.get_articles()
        return [a for a in all_articles if isinstance(a, UnresolvedPage)]

    def to_string(self):
        #todo: file metadata
        ret = self.file_metadata_string
        for action in self.actions:
            ret += action.to_string()
        return ret

    def summarize(self):
        desc = (len(self.get_articles()),
                len(self._get_unresolved_articles()),
                len(self.actions),
                self.file_metadata.get('date', 'new'))
        return 'Total: %s;\nUnresolved: %s;\nActions: %s;\nDate: %s;' % desc


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
        ret = u'##'
        ret_dict = {}
        for attr in self.metadata_attrs:
            ret_dict[attr] = getattr(self, attr)
            if hasattr(ret_dict[attr], 'strftime'):
                ret_dict[attr] = ret_dict[attr].strftime(DATE_FORMAT)
        return ret + json.dumps(ret_dict) + '\n'

    def get_article_string(self):
        ret = ''
        for article in self.articles:
            ret += print_page_info(article)
        return ret

    def to_string(self):
        ret = self.get_meta_string()
        # if not page infos, get page info
        ret += self.get_article_string()
        return ret


def parse_meta_string(string_orig):
    string = string_orig.strip()
    try:
        ret = json.loads(string)
    except ValueError:
        pass  # invalid meta string
    return ret


def print_page_info(pi):
    if isinstance(pi, UnresolvedPage):
        ret = pi.title
    else:
        try:
            ret = json.dumps((pi.title, pi.page_id, pi.ns, pi.subject_id, pi.talk_id))
        except AttributeError:
            # probably UnresolvedPage
            ret = pi
    return ret + u'\n'


def parse_page_info(raw_pi, source):
    try:
        title, page_id, ns, subject_id, talk_id = json.loads(raw_pi)
        ret = PageInfo(title=title,
                       page_id=page_id,
                       ns=ns,
                       subject_id=subject_id,
                       talk_id=talk_id,
                       source=source)
    except ValueError as ve:
        import pdb;pdb.post_mortem()
        ret = UnresolvedPage(raw_pi)
    return ret


def al_parse(contents):
    lines = contents.splitlines()
    file_metadata = ''
    ret_actions = []
    comments = {}
    for i, orig_line in enumerate(lines):
        line = orig_line.strip()
        if not line:
            comments[i] = ''
        elif line.startswith(u'###'):
            file_metadata = parse_meta_string(line.lstrip('###'))
        elif line.startswith(u'##'):
            ret_actions.append(ListAction.from_meta_string(line.lstrip('##')))
        elif line.startswith('#'):
            comments[i] = line.lstrip('#')
        else:
            if not ret_actions:
                # no action metadata
                ret_actions.append(ListAction('include'))
            try:
                page = parse_page_info(line, source=ret_actions[-1].source)
            except ValueError:
                pass  # cannot parse line?
            ret_actions[-1].articles.append(page)
    return ret_actions, comments, file_metadata


def add_subparsers(parent_subprs):
    # womp list show
    prs_show = parent_subprs.add_parser('show',
                                        help=('print information about'
                                              'available lists'))
    prs_show.add_argument('target_list', nargs='?',
                          help='Name of the list or list file')
    prs_show.set_defaults(func_name='show')

    # womp list show_operations
    parser_show_operations = parent_subprs.add_parser('show_operations',
                                                      help='print available \
                                                      wapiti operations')
    parser_show_operations.set_defaults(func_name='show_operations')

    # womp list create *listname
    prs_create = parent_subprs.add_parser('create',
                                          help=('create a new list for'
                                                ' article storage'))
    prs_create.add_argument('target_list',
                            help='name of the list or list file')
    prs_create.set_defaults(func_name='create')

    # womp list create *listname
    prs_create = parent_subprs.add_parser('resolve',
                                          help=('fetch page info for unresolved'
                                                ' pages (not implemented)'))
    prs_create.add_argument('target_list',
                            help='name of the list or list file')
    prs_create.set_defaults(func_name='resolve_the_unresolved')

    # womp list *arg *listname *wapitisource
    op_prs = ArgumentParser(description='parses generic search op args.',
                            add_help=False)
    op_prs.add_argument('target_list',
                        help='name or path of article list')
    op_prs.add_argument('operation_list', nargs='*',
                        help='article, category, or template')
    op_prs.add_argument('--limit', '-l', type=int,
                        help='max number of articles',
                        default=DEFAULT_LIMIT)
    op_prs.set_defaults(func_name='list_op')

    # actions
    _include_help = 'add articles to the list based on a wapiti operation'
    include_prs = parent_subprs.add_parser('include', parents=[op_prs],
                                           help=_include_help)
    include_prs.set_defaults(op_name='include')

    _exclude_help = 'remove articles from the list based on a wapiti operation'
    exclude_prs = parent_subprs.add_parser('exclude', parents=[op_prs],
                                           help=_exclude_help)
    exclude_prs.set_defaults(op_name='exclude')
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
    import sys
    parser = create_parser()
    if len(sys.argv) == 1:
        parser.print_help()
        print ''
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

    func_name = kwargs.pop('func_name', None)
    getattr(alm, func_name)(**kwargs)


def create_test():
    alm = ArticleListManager()
    try:
        os.remove(alm._lookup_path(TEST_LIST_NAME))
    except TypeError:
        pass
    alm.create(target_list=TEST_LIST_NAME)
    return ArticleListManager()


def test_create_alm():
    alm = create_test()
    return len(alm.load_list(TEST_LIST_NAME).actions) == 0


def test_include_list_op():
    alm = create_test()
    alm.list_op(op_name='include',
                target_list=TEST_LIST_NAME,
                operation_list=['get_category', 'Physics'],
                limit=20)
    return len(alm.load_list(TEST_LIST_NAME).actions[0].articles) == 20


def test_exclude_list_op():
    alm = create_test()
    alm.list_op(op_name='include',
                target_list=TEST_LIST_NAME,
                operation_list=['get_category', 'Physics'],
                limit=50)
    alm.list_op(op_name='exclude',
                target_list=TEST_LIST_NAME,
                operation_list=['get_category', 'Physics'],
                limit=30)
    ret = alm.load_list(TEST_LIST_NAME).get_articles()
    return len(ret) < 50 and len(ret) >= 20


def test_show():
    alm = create_test()
    try:
        alm.show()
        return True
    except:
        return False


def test_load_list():
    alm = create_test()
    try:
        test_list_data = alm.get_list_dict(TEST_LIST_NAME)
        return test_list_data['total'] == 0
    except:
        return False


def _main():
    from pprint import pprint
    results = {}
    tests = [v for k, v in globals().items() if k.startswith('test_')]
    for test_func in tests:
        results[test_func.func_name] = test_func()
    pprint(results)


if __name__ == '__main__':
    try:
        main()
    except Exception as e:
        import pdb;pdb.post_mortem()
        raise
