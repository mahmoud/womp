from base import Input

class Backlinks(Input):
    prefix = 'bl'

    def fetch(self):
        return self.wapiti.get_backlinks(self.info.title)

    stats = {
        'count': lambda f_res: len(f_res),
    }
