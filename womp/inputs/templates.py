from collections import Counter
from base import Input


def uc_first(s):
    return s[0].upper() + s[1:]


class ParsedTemplates(Input):
    prefix = 'pt'

    def fetch(self):
        return self.wapiti.get_parsed_templates_page(self.info.title)

    stats = {
        'citations': lambda f_res: [f.__dict__ for f in f_res if 'cite' in f.name or 'citation' in f.name],
        'template_counter': lambda f_res: Counter([uc_first(f.name) for f in f_res]),
    }
