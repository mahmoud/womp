from base import Input
from json import loads


class Watchers(Input):
    prefix = 'wa'

    def fetch(self):
        url = 'http://toolserver.org/~slaporte/rs/wl?title=' + self.info.title.replace(' ', '_')
        watchers = self.wapiti.web_request_operation(url)
        ret = loads(watchers[0])
        return ret

    stats = {
        'count': lambda f_res: f_res.get('watchers'),
    }
