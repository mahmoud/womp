from __future__ import unicode_literals

import os
from os.path import join as pjoin
import time
from collections import defaultdict

from wapiti import WapitiClient
from clastic import Application, json_response
from clastic.render.mako_templates import MakoRenderFactory
from inputs import ALL_INPUTS

_CURDIR = os.path.abspath(os.path.dirname(__file__))
_TEMPLATE_PATH = pjoin(_CURDIR, 'templates')
_STATIC_PATH = pjoin(_CURDIR, 'templates', 'assets')


AVAIL_INPUTS = dict([(i.__name__.lower(), i) for i in ALL_INPUTS
                     if i.__name__ != 'Input'])


def input_list():
    return {'inputs': [i.__name__ for i in AVAIL_INPUTS.values()]}


def article_list(list_manager):
    return {'article_lists': list_manager.get_list_dicts()}


def input_server(input_name, title):
    wc = WapitiClient('test@example.com')
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
           'process_failures': process_failures,
           'name': fetch_manager.name,
           }
    return ret


def create_input_server():
    routes = [('/', input_list, 'list.html'),
              ('/<input_name>/<title>', input_server, json_response)]
    mako_render = MakoRenderFactory(_TEMPLATE_PATH)
    return Application(routes, render_factory=mako_render)


def create_dashboard(womp_env):
    resources = {'womp_env': womp_env,
                 'fetch_manager': womp_env.fetch_manager,
                 'list_manager': womp_env.list_manager}
    input_server = create_input_server()
    routes = [('/', fetch_task_dashboard, 'dashboard.html'),
              ('/dashboard', fetch_task_dashboard, 'dashboard.html'),
              ('/dashboard/json', fetch_task_dashboard, json_response),
              ('/article_list', article_list, 'article_list.html'),
              ('/inputs', input_server)]
    mako_render = MakoRenderFactory(_TEMPLATE_PATH)

    if not fetch_manager.dashboard_port:
        fetch_manager.dashboard_port = 5000

    return Application(routes, resources, mako_render)
    #app.serve(use_reloader=False,
    #          static_prefix='static',
    #          port=fetch_manager.dashboard_port,
    #          static_path=static_path)



if __name__ == '__main__':
    create_input_server().serve()
