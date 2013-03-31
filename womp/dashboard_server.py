from __future__ import unicode_literals

import os
import time
from collections import defaultdict
from wapiti import WapitiClient
from clastic import Application, json_response
from clastic.render.mako_templates import MakoRenderFactory
from article_list import ArticleListManager
from inputs import ALL_INPUTS

input_mods = ALL_INPUTS

AVAIL_INPUTS = {}

for im in ALL_INPUTS:
    if hasattr(im, 'fetch'):
        AVAIL_INPUTS[im.__name__] = im
        AVAIL_INPUTS[im.__name__.lower()] = im
AVAIL_INPUTS.pop('Input', None)


def input_list():
    return {'inputs': AVAIL_INPUTS}


def article_list():
    alm = ArticleListManager()
    return {'article_lists': alm.get_list_dicts()}


def input_server(input_name, title):
    wc = WapitiClient('testing')
    if not title:
        title = 'Coffee'
    page_info = wc.get_page_info(title)[0]
    input_type = AVAIL_INPUTS.get(input_name.lower())
    if input_type is None:
        raise Exception('No input found with name "' + input_name + '"')
    get_input = input_type(page_info, wc)
    result = get_input()
    result['durations'] = get_input.durations
    return result


def fetch_task_dashboard(fetch_manager):
    cur_time = time.time()
    fetch_failures = defaultdict(list)
    process_failures = defaultdict(list)
    success_count = len([o for o in fetch_manager.result_stats if o['is_successful']])
    failure_count = len(fetch_manager.result_stats) - success_count
    in_prog_times = dict([(o.page_info.title, cur_time - o.times['create']) for o in fetch_manager.pool])
    for input_name in fetch_manager.inputs:
        fetch_failures[input_name.__name__].extend([f['title'] for f in fetch_manager.result_stats
                                                    if not f['inputs'][input_name.__name__]['fetch_succeeded']])
        # todo: safe specific process errors; display in dashboard
        process_failures[input_name.__name__].extend([f['title'] for f in fetch_manager.result_stats
                                                     if f['inputs'][input_name.__name__]['fetch_succeeded'] and
                                                     not f['inputs'][input_name.__name__]['is_successful']])
    ret = {'in_progress_count': len(fetch_manager.pool),
           'in_progress': in_prog_times,
           'complete_count': len(fetch_manager.results),
           'success_count': success_count,
           'failure_count': failure_count,
           'total_articles': len(fetch_manager.articles),
           'input_classes': [i.__name__ for i in fetch_manager.inputs],
           'in_progress': [o.get_status() for o in fetch_manager.pool],
           'complete_times': fetch_manager.result_stats,
           'start_time': time.strftime("%d %b %Y %H:%M:%S UTC", time.gmtime(fetch_manager.start_time)),
           'duration': time.time() - fetch_manager.start_time,
           'fetch_failures': fetch_failures,
           'process_failures': process_failures
           }
    return ret

mako_render = MakoRenderFactory(os.path.join(os.getcwd(), 'templates'))
routes = [('/input_list', input_list, 'list.html'),
          ('/<input_name>/<title>', input_server, json_response),
          ('/article_list', article_list, 'article_list.html')]


def start_dashboard_server(fetch_manager):
    static_path = os.path.join(os.getcwd(), 'templates', 'assets')
    resources = {'fetch_manager': fetch_manager}
    routes.append(('/dashboard', fetch_task_dashboard, 'dashboard.html'))
    app = Application(routes, resources, mako_render)
    app.serve(use_reloader=False, static_prefix='static', static_path=static_path)

if __name__ == '__main__':
    app = Application(routes, render_factory=mako_render)
    app.serve()
