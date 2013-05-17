import string
import re
from base import Input
from pyquery import PyQuery

from stats import dist_stats

_PUB_DATE = re.compile(r'(\w\s|\.\s|,\s|\(\w*\s*|-)'
                       r'(?P<year>(14|15|16|17|''18|19|20)[0-9]{2})'
                       r'(\.|,|\)|-)', flags=re.IGNORECASE)
_PUB_LIST = ['Cambridge University Press',
             'Longman',
             'Knopf',
             r'Oxford University Press',
             'Oxford',
             'Camden House Press',
              'University of North Carolina Press',
              'The Viking Press',
              r"Arnold and St\. Martin\'s Press",
              'MacMillan'
              'Yale University Press',
              'Duncker & Humblot',
              'Wallstein',
              'HarperCollins',
              r'\w+ Press']
_PUB_RE_LIST = [(pub, re.compile('(' + pub + ')')) for pub in _PUB_LIST]


def get_root(pq):
    try:
        roottree = pq.root  # for pyquery on lxml 2
    except AttributeError:
        roottree = pq[0].getroottree()  # for lxml 3
    return roottree


def pq_contains(elem, search):
    """Just a quick factory function to create lambdas to do xpath in a cross-version way"""
    def xpath_search(f):
        if not f:
            return 0
        else:
            roottree = get_root(f)
            return len(roottree.xpath(u'//{e}[contains(., "{s}")]'.format(e=elem, s=search)))
    return xpath_search


def word_count(element):
    return len(get_text(element).split())


def get_text(element):
    if hasattr(element, 'text_content'):  # lxml 2
        text = element.text_content()
    else:
        text = ''.join(element.itertext())
    return text


def section_stats(pq):
    all_headers = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'h7']
    headers = []
    headers = pq(','.join(all_headers))
    hs = [h for h in headers if get_text(h) != 'Contents']
    # how not to write Python: ['h'+str(i) for i in range(1, 8)]
    totals = []
    for header in hs:
        if header.getnext() is not None:  # TODO: the next item after an h1 is
                                          # #bodyContents div
            pos = header.getnext()
            text = ''
            while pos.tag not in all_headers:
                text += ' ' + get_text(pos)  # TODO: the references section may
                                             # skew the no. words under an h2
                if pos.getnext() is not None:
                    pos = pos.getnext()
                else:
                    break
            totals.append((get_text(header).replace(' [edit]', ''),
                           len(text.split())))
    dists = {}
    #dists['header'] = dist_stats([len(header.split()) for header, t in totals])
    #dists['text'] = dist_stats([text for h, text in totals])
    dists['headers'] = [h for h, _ in totals]
    return dists


def regex_publister(text):
    for name, pub_re in _PUB_RE_LIST:
        publisher = re.search(pub_re, text)
        if publisher:
            return publisher.groups()
    return 'None found'


def regex_pub_year(text):
    text = re.split(r'retrieved', text, flags=re.IGNORECASE)[0]
    year = list(re.finditer(_PUB_DATE, text))
    if year:
        year = year[0].group('year')
    return year


def reflist_items(pq):
    ret = {}
    links = ['.com', '.net', '.org', '.edu']
    # todo: get heading above?
    reflists = pq('.references')
    for list_i, reflist in enumerate(reflists):
        for i, ref in enumerate(reflist):
            tld = None
            # import pdb;pdb.set_trace()
            refid = ref.get('id')[10:]
            ref_pq = PyQuery(ref)
            ref_text = get_text(ref)
            year = regex_pub_year(ref_text)
            el_element = ref_pq('a.external')
            if el_element:
                external_link = el_element[0].get('href')
                for link in links:
                    if link in external_link:
                        tld = link
            use_tmpl = 'Citation' if ref_pq('span.citation') else 'None'
            use_tmpl = 'Cite book' if ref_pq('span.book') else use_tmpl
            use_tmpl = 'Cite web' if ref_pq('span.web') else use_tmpl
            use_tmpl = 'Cite journal' if ref_pq('span.journal') else use_tmpl
            ret[refid] = {
                'reflist': list_i,
                'ol_index': i + 1,
                'use_count': len(ref_pq('a[href^="#cite"]')),
                'year': year,
                'publisher': regex_publister(ref_text),
                'tld': tld,
                'template': use_tmpl
            }
    return ret


def wording_counts(pq):
    ret = {}
    ret['word_count'] = len(pq('p').text().split())
    ret['p_count'] = len(pq('div#content p'))
    ret['ref_count'] = len(pq('sup[id^="cite_ref"]'))
    ret['word_per_ref'] = float(ret['ref_count']) and ret['word_count'] / float(ret['ref_count'])
    ret['p_wo_cites'] = len([p for p in pq('div#content p') if not len(PyQuery(p).find('sup[id^="cite_ref"]'))])
    return ret


def phrase_count(pq, pattern):
    all_text = pq('div#content').text()
    found = re.findall(pattern, all_text, flags=re.IGNORECASE)
    return len(found)


def contains_num(founds):
    ret = []
    for found in founds:
        if re.search(r'18[0-9]+', get_text(found)):
            ret.append(get_text(found))
    return ret


def word_frequency(word, total):
    total_split = total.split(' ')
    word_count = len([w for w in total_split if word in w.lower()])
    if total_split:
        return word_count / (len(total_split) * 1.0)
    else:
        return 0


class NineteenDOM(Input):
    prefix = 'ntd'

    def fetch(self):
        # avg process time: 0.14827052116394043 seconds
        ret = self.wapiti.web_request_operation('http://en.wikipedia.org/wiki/' + self.info.title)
        return ret[0]

    def process(self, f_res):
        ret = PyQuery(f_res).find('div#content')
        ret('div#siteNotice').remove()
        return super(NineteenDOM, self).process(ret)

    stats = {

        # to detect if article concerns 19th century history
        '_cat_contains_history': lambda f: len(f('#mw-normal-catlinks a[href*="History"]') + f('#mw-normal-catlinks a[href*="history"]')),
        '_cat_contains_military': lambda f: len(f('#mw-normal-catlinks a[href*="Military"]') + f('#mw-normal-catlinks a[href*="military"]')),
        '_cat_contains_1800': lambda f: len(contains_num(f('#mw-normal-catlinks a[href*="18"]'))),
        '_cat_contains_19th_century': lambda f: len(f('#mw-normal-catlinks a[href*="19th-century"]')),
        '_intro_p_contains_1800': lambda f: True if len(contains_num(f('#toc').prevAll('p'))) else False,
        '_infobox_contains_1800': lambda f: True if len(contains_num(f('.infobox'))) else False,
        '_total_history_freq': lambda f: word_frequency('history', get_text(f('#content')[0])),

        'general': wording_counts,
        'refbegin_count': lambda f: len(f('div.refbegin')),
        'reflist_count': lambda f: len(f('div.reflist')),
        'ref_text_count': lambda f: len(f('.reference-text')),

        'pq': reflist_items,
        'sections': section_stats,
        'c_probably': lambda f: phrase_count(f, r'probably'),
        'c_possibly': lambda f: phrase_count(f, r'possibly'),
        'c_other_hand': lambda f: phrase_count(f, r'on the other hand'),
        'c_one_view': lambda f: phrase_count(f, r'one view'),
        'c_bias': lambda f: phrase_count(f, r'bias'),
        'c_according': lambda f: phrase_count(f, r'according to'),
        'c_historian': lambda f: phrase_count(f, r'historian[s]*'),
        'c_academic': lambda f: phrase_count(f, r'the academic'),
        # looking for "the sometimes historian"
        'c_adj_historian': lambda f: phrase_count(f, r'the \w* hisorian[s]*'),
        'c_biographer': lambda f: phrase_count(f, r'the biographer'),
        'c_biographer': lambda f: phrase_count(f, r'the biographer'),
        'c_historiography': lambda f: phrase_count(f, r'historiography'),
        'c_ealiest_works': lambda f: phrase_count(f, r'earliest works'),
        'c_earliest_histories': lambda f: phrase_count(f, r'earliest histor(y|ies)'),
        'c_popular_historian': lambda f: phrase_count(f, r'popular historian[s]*'),
        'c_academic_interest': lambda f: phrase_count(f, r'academic interest'),
        'c_popular_history': lambda f: phrase_count(f, r'popular history'),
        'c_historiographical': lambda f: phrase_count(f, r'historiographical'),

        # citation types
        'cite_cl': lambda f: len(f('.citation')),  # not to be confused with cite_count
        'cite_journal': lambda f: len(f('.citation.Journal')),
        'cite_web': lambda f: len(f('.citation.web')),
        'cite_news': lambda f: len(f('.citation.news')),
        'cite_episode': lambda f: len(f('.citation.episode')),
        'cite_newsgroup': lambda f: len(f('.citation.newgroup')),
        'cite_patent': lambda f: len(f('.citation.patent')),
        'cite_pressrelease': lambda f: len(f('.citation.pressrelease')),
        'cite_report': lambda f: len(f('.citation.report')),
        'cite_video': lambda f: len(f('.citation.video')),
        'cite_videogame': lambda f: len(f('.citation.videogame')),
        'cite_book': lambda f: len(f('.citation.book')),

        # Template inspection, mostly fault detection
        'tmpl_general': lambda f: len(f('.ambox')),
        'tmpl_delete': lambda f: len(f('.ambox-delete')),
        'tmpl_autobiography': lambda f: len(f('.ambox-autobiography')),
        'tmpl_advert': lambda f: len(f('.ambox-Advert')),
        'tmpl_citation_style': lambda f: len(f('.ambox-citation_style')),
        'tmpl_cleanup': lambda f: len(f('.ambox-Cleanup')),
        'tmpl_COI': lambda f: len(f('.ambox-COI')),
        'tmpl_confusing': lambda f: len(f('.ambox-confusing')),
        'tmpl_context': lambda f: len(f('.ambox-Context')),
        'tmpl_copy_edit': lambda f: len(f('.ambox-Copy_edit')),
        'tmpl_dead_end': lambda f: len(f('.ambox-dead_end')),
        'tmpl_disputed': lambda f: len(f('.ambox-disputed')),
        'tmpl_essay_like': lambda f: len(f('.ambox-essay-like')),
        'tmpl_expert': pq_contains('td', 'needs attention from an expert'),
        'tmpl_fansight': pq_contains('td', 's point of view'),
        'tmpl_globalize': pq_contains('td', 'do not represent a worldwide view'),
        'tmpl_hoax': pq_contains('td', 'hoax'),
        'tmpl_in_universe': lambda f: len(f('.ambox-in-universe')),
        'tmpl_intro_rewrite': lambda f: len(f('.ambox-lead_rewrite')),
        'tmpl_merge': pq_contains('td', 'suggested that this article or section be merged'),
        'tmpl_no_footnotes': lambda f: len(f('.ambox-No_footnotes')),
        'tmpl_howto': pq_contains('td', 'contains instructions, advice, or how-to content'),
        'tmpl_non_free': lambda f: len(f('.ambox-non-free')),
        'tmpl_notability': lambda f: len(f('.ambox-Notability')),
        'tmpl_not_english': lambda f: len(f('.ambox-not_English')),
        'tmpl_NPOV': lambda f: len(f('.ambox-POV')),
        'tmpl_original_research': lambda f: len(f('.ambox-Original_research')),
        'tmpl_orphan': lambda f: len(f('.ambox-Orphan')),
        'tmpl_plot': lambda f: len(f('.ambox-Plot')),
        'tmpl_primary_sources': lambda f: len(f('.ambox-Primary_sources')),
        'tmpl_prose': lambda f: len(f('.ambox-Prose')),
        'tmpl_refimprove': lambda f: len(f('.ambox-Refimprove')),
        'tmpl_sections': lambda f: len(f('.ambox-sections')),
        'tmpl_tone': lambda f: len(f('.ambox-Tone')),
        'tmpl_tooshort': lambda f: len(f('.ambox-lead_too_short')),
        'tmpl_style': lambda f: len(f('.ambox-style')),
        'tmpl_uncategorized': lambda f: len(f('.ambox-uncategorized')),
        'tmpl_update': lambda f: len(f('.ambox-Update')),
        'tmpl_wikify': lambda f: len(f('.ambox-Wikify')),
        'tmpl_multiple_issues': lambda f: len(f('.ambox-multiple_issues li')),

        # Hatnotes
        'hn_rellink_count': lambda f: len(f('div.rellink')),  # "See also" link for a section
        'hn_dablink_count': lambda f: len(f('div.dablink')),  # Disambiguation page links
        'hn_mainlink_count': lambda f: len(f('div.mainarticle')),  # Link to main, expanded article
        'hn_seealso_count': lambda f: len(f('div.seealso')),  # Generic see also
        'hn_relarticle_count': lambda f: len(f('div.relarticle')),  # somehow distinct from rellink

        # Inline/link-based stats
        'ref_count': lambda f: len(f('sup.reference')),
        'cite_count': lambda f: len(f('li[id^="cite_note"]')),
        'red_link_count': lambda f: len(f('.new')),  # New internal links, aka "red links"
        'ext_link_count': lambda f: len(f('.external')),
        'int_link_text': lambda f: dist_stats([len(get_text(text)) for text in f('p a[href^="/wiki/"]')]),
        'dead_link_count': lambda f: len(f('a[title^="Wikipedia:Link rot"]')),
        'ref_needed_span_count': pq_contains('span', 'citation'),
        'pov_span_count': pq_contains('span', 'neutrality'),

        # DOM-based category stats, not to be confused with the API-based Input
        'cat_count': lambda f: len(f("#mw-normal-catlinks ul li")),
        'hidden_cat_count': lambda f: len(f('#mw-hidden-catlinks ul li')),

        # Media/page richness stats
        #'wiki_file_link_count': lambda f: len(f("a[href*='/wiki/File:']")),
        'ipa_count': lambda f: len(f('span[title="pronunciation:"]')),
        'all_img_count': lambda f: len(f('img')),
        'thumb_img_count': lambda f: len(f('div.thumb')),
        'thumb_left_count': lambda f: len(f('div.tleft')),
        'thumb_right_count': lambda f: len(f('div.tright')),
        #'image_map_count': lambda f: len(f('map')),  # The clickable image construct (EasyTimeline)
        #'tex_count': lambda f: len(f('.tex')),  # LaTeX/TeX used by mathy things
        'infobox_count': lambda f: len(f('.infobox')),
        #'navbox_word': element_words_dist('.navbox'),
        #'caption_word': element_words_dist('.thumbcaption'),
        #'ogg_count': lambda f: len(f("a[href$='.ogg']")),
        #'svg_count': lambda f: len(f("img[src*='.svg']")),
        #'pdf_count': lambda f: len(f("a[href$='.pdf']")),
        #'midi_count': lambda f: len(f("a[href$='.mid']")),
        'geo_count': lambda f: len(f('.geo-dms')),
        'blockquote_count': lambda f: len(f('blockquote')),
        #'metadata_link_count': lambda f: len(f('.metadata.plainlinks')),  # Commons related media
        'spoken_wp_count': lambda f: len(f('#section_SpokenWikipedia')),
        #'wikitable_word': element_words_dist('table.wikitable'),
        'gallery_li_count': lambda f: len(f('.gallery').children('li')),
        #'unicode_count': lambda f: len(f('.unicode, .Unicode')),
    }
