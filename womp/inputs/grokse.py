from base import Input
from stats import dist_stats
from json import loads


class PageViews(Input):
    prefix = 'pv'

    def fetch(self):
        grokse = self.wapiti.web_request_operation('http://stats.grok.se/json/en/latest90/' + self.info.title)
        ret = loads(grokse[0])
        return ret

    stats = {
        '90_days': lambda f: dist_stats(f['daily_views'].values()),
    }
