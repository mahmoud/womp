from base import Input


class LangLinks(Input):
    prefix = 'll'

    def fetch(self):
        return self.wapiti.get_language_links(self.info)

    stats = {
        'count': lambda f_res: len(f_res),
    }
