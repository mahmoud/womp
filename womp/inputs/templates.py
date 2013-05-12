from collections import Counter
from base import Input


def uc_first(s):
    return s[0].upper() + s[1:]

def template_counter(t):
    templates = Counter([uc_first(f.name) for f in t])
    templates['ALL_CITES'] = templates['Cite web'] + \
                             templates['Cite pmid'] + \
                             templates['Cite news'] + \
                             templates['Cite journal'] + \
                             templates['Cite encyclopedia'] + \
                             templates['Cite doi'] + \
                             templates['Cite book'] + \
                             templates['Citation'] + \
                             templates['Cite'] + \
                             templates['Cite conference'] + \
                             templates['Cite thesis']
    return templates


class ParsedTemplates(Input):
    prefix = 'pt'

    def fetch(self):
        return self.wapiti.get_parsed_templates_page(self.info.title)

    stats = {
        'citations': lambda f_res: [f.__dict__ for f in f_res if 'cite' in f.name or 'citation' in f.name],
        'template_counter': template_counter,
    }
