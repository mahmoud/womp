from base import Input


class InterWikiLinks(Input):
    prefix = 'iw'

    def fetch(self):
        return self.wapiti.get_interwiki_links(self.info)

    stats = {
        'count': lambda f_res: len(f_res),
    }
