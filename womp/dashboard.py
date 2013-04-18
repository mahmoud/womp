from __future__ import unicode_literals

import os
from os.path import join as pjoin
import time
from collections import defaultdict

from wapiti import WapitiClient
from clastic import Application
from clastic.render import dev_json_response
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


def input_server(input_name, title=None, wapiti_client=None):
    wc = wapiti_client or WapitiClient('test@example.com')
    title = title or 'Coffee'
    page_info = wc.get_page_info(title)[0]
    try:
        input_type = AVAIL_INPUTS[input_name.lower()]
    except KeyError:
        raise ValueError('No input found with name %r' % (input_name,))
    get_input = input_type(page_info, wc)
    result = get_input()
    result['durations'] = get_input.durations
    return result


def fetch_task_dashboard(fetch_manager):
    cur_time = time.time()
    fetch_failures = ff = defaultdict(list)
    process_failures = pf = defaultdict(list)
    success_count = len([o for o in fetch_manager.result_stats
                         if o['is_successful']])
    failure_count = len(fetch_manager.result_stats) - success_count
    in_prog_times = dict([(o.page_info.title, cur_time - o.times['create'])
                          for o in fetch_manager.pool])
    start_time = time.strftime("%d %b %Y %H:%M:%S UTC",
                               time.gmtime(fetch_manager.start_time)),
    for inp in fetch_manager.inputs:
        inp_name = inp.__name__
        ff[inp_name].extend([f['title'] for f in fetch_manager.result_stats
                             if not f['inputs'][inp_name]['fetch_succeeded']])
        # todo: safe specific process errors; display in dashboard
        pf[inp_name].extend([f['title'] for f in fetch_manager.result_stats
                             if f['inputs'][inp_name]['fetch_succeeded'] and
                             not f['inputs'][inp_name]['is_successful']])
    ret = {'in_progress_count': len(fetch_manager.pool),
           'in_progress': in_prog_times,
           'complete_count': len(fetch_manager.results),
           'success_count': success_count,
           'failure_count': failure_count,
           'total_articles': len(fetch_manager.articles),
           'input_classes': [i.__name__ for i in fetch_manager.inputs],
           'in_progress': [o.get_status() for o in fetch_manager.pool],
           'complete_times': fetch_manager.result_stats,
           'start_time': start_time,
           'duration': time.time() - fetch_manager.start_time,
           'fetch_failures': fetch_failures,
           'process_failures': process_failures,
           'name': fetch_manager.name}
    return ret


def create_input_server(wapiti_client=None):
    wapiti_client = wapiti_client or WapitiClient('test@example.com')
    resources = {'wapiti_client': wapiti_client}
    routes = [('/', input_list, 'list.html'),
              ('/<input_name>/<title>', input_server, dev_json_response)]
    mako_render = MakoRenderFactory(_TEMPLATE_PATH)
    return Application(routes, resources, mako_render)


def create_fetch_dashboard(fetch_manager):
    routes = [('/', fetch_task_dashboard, 'dashboard.html'),
              ('/json', fetch_task_dashboard, dev_json_response)]
    resources = {'fetch_manager': fetch_manager}
    mako_render = MakoRenderFactory(_TEMPLATE_PATH)
    return Application(routes, resources, mako_render)


def create_dashboard(womp_env):
    wapiti_client = womp_env.get_wapiti_client()
    input_server = create_input_server(wapiti_client)
    fetch_dashboard = create_fetch_dashboard(womp_env.fetch_manager)
    resources = {'womp_env': womp_env,
                 'list_manager': womp_env.list_manager}
    routes = [('/', fetch_dashboard),
              ('/inputs', input_server),
              ('/article_list', article_list, 'article_list.html')]

    mako_render = MakoRenderFactory(_TEMPLATE_PATH)

    return Application(routes, resources, mako_render)


if __name__ == '__main__':
    create_input_server().serve()
