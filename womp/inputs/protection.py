from base import Input


class Protection(Input):
    prefix = 'pr'

    def fetch(self):
        protections = self.wapiti.get_protections(self.info)
        ret = protections[0]
        return ret

    stats = {
        'any': lambda f_res: f_res.has_protection,
        'indef': lambda f_res: f_res.has_indef,
        'full': lambda f_res: f_res.is_full_prot,
        'semi': lambda f_res: f_res.is_semi_prot,
    }
