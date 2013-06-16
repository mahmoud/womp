import os
from clastic import Application, json_response, redirect
from clastic.render.mako_templates import MakoRenderFactory
from wapiti import WapitiClient
from gevent import socket
from gevent.threadpool import ThreadPool
from article_list import ArticleListManager, ListAction
from fetch import FetchManager
from json import dumps
import time


###
DEFAULT_HOST = '0.0.0.0'
DEFAULT_PORT = 1870


def find_port(host=DEFAULT_HOST, start_port=DEFAULT_PORT, end_port=None):
    start_port = int(start_port)
    end_port = end_port or start_port + 100
    for p in range(start_port, end_port):
        try:
            s = socket.socket()
            s.bind((host, p))
        except socket.error:
            return None
        else:
            s.close()
            return p
    return None


def article_list():
    alm = ArticleListManager()
    return {'article_lists': alm.get_all_list_dicts()}


def start_fetch(listname, port):
    fm = FetchManager()  # include env
    fm.load_list(listname)
    fm.fetch_list(listname, port=port)
    return fm.results


def fetch_controller(listname):
    port = find_port()
    if port:
        tpool = ThreadPool(2)
        tpool.spawn(start_fetch, listname, port)
        ret = {'port': port,
               'name': listname,
               'url': 'http://localhost:' + str(port),
               'status': 'running'}
    else:
        ret = {'port': port,
               'name': listname,
               'url': '',
               'status': 'occupied'}
    return ret


def list_editor(listname):
    alm = ArticleListManager()
    article_list = alm.load_list(listname)
    ret = {'name': listname,
           'meta': article_list.file_metadata_string,
           'actions': [],
           'article_set': article_list.get_articles()}
    for action in article_list.actions:
        ret['actions'].append({'meta': {'action': action.action},
                               'articles': action.articles})
    return ret


def list_editor_submit(request):
    meta = request.values['meta'].lstrip('##')
    listname = request.values['name']
    articles = [a.strip() for a in request.values['articles'].split('\n')]
    resolve = request.values.get('resolve')
    alm = ArticleListManager()
    alm.append_action(listname, meta, articles)
    if resolve:
        alm.resolve_the_unresolved(listname)
    return redirect('/list_editor/' + listname)


def list_editor_remove(request):
    listname = request.values['_list_name']
    article_list = []
    for article_name in request.values.keys():
        if request.values[article_name] == 'remove' \
           and article_name != '_list_name':
            article_list.append(article_name)
    meta = dumps({'action': 'exclude',
                  'date': time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()),
                  'term': ['manual action'],
                  'source': 'http://en.wikipedia.org/w/api.php'})
    alm = ArticleListManager()
    alm.append_action(listname, meta, article_list)
    return redirect('/list_editor/' + listname)

def list_create(listname, request):
    alm = ArticleListManager()
    try:
        alm.create(listname)
        thelist = alm.load_list(listname)
    except IOError as e:
        return {
            'error': str(e),
            'code': 409
        }
    except ValueError as e:
        return {
            'error': str(e),
            'code': 400
        }

    return {
        'name': listname,
        'articles': len(thelist._get_unresolved_articles()),
        'actions': len(thelist.actions),
        'date': thelist.file_metadata.get('date', 'new')
    }

def list_delete(listname, request):
    alm = ArticleListManager()
    alm.delete(listname)
    return {
        'success': True
    }

mako_render = MakoRenderFactory(os.path.join(os.getcwd(), 'templates'))
routes = [('/start_fetch/<listname>', fetch_controller, json_response),
          ('/list_editor/<listname>', list_editor, 'list_editor.html'),
          ('/list_editor/submit', list_editor_submit, json_response),
          ('/list_editor/remove', list_editor_remove, json_response),
          ('/list_create/<listname>', list_create, json_response),
          ('/list_delete/<listname>', list_delete, json_response),
          ('/', article_list, 'index.html')]


def main():
    static_path = os.path.join(os.getcwd(), 'templates', 'assets')
    app = Application(routes, None, mako_render)
    app.serve(static_prefix='static',
              static_path=static_path)

if __name__ == '__main__':
    main()
