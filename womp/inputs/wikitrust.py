from base import Input

class Wikitrust(Input):
    prefix = 'wt'

    def fetch(self):
        # TODO need rev_id
        return self.wapiti.web_request_operation('http://en.collaborativetrust.com/WikiTrust/RemoteAPI?method=quality&revid=' + str(self.page_id))

    stats = {
        'wikitrust': lambda f: str(f.text)
    }
