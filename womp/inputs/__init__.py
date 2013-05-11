from backlinks import Backlinks
from dom import DOM
from grokse import PageViews
from protection import Protection
from article_history import ArticleHistory
from watchers import Watchers
from revisions import Revisions
from langlinks import LangLinks
from interwikilinks import InterWikiLinks
from templates import ParsedTemplates

'''
from feedback import FeedbackV4
from feedback import FeedbackV5
`from dom import DOM
from google import GoogleNews
from google import GoogleSearch
from wikitrust import Wikitrust
`from grokse import PageViews
`from revisions import Revisions
`from langlinks import LangLinks
`from interwikilinks import InterWikiLinks
`from watchers import Watchers
`from article_history import ArticleHistory
`from protection import Protection
'''
ALL_INPUTS = [Backlinks, DOM, PageViews, Protection, Revisions, ArticleHistory, Watchers, LangLinks, InterWikiLinks, ParsedTemplates]

DEFAULT_INPUTS = ALL_INPUTS
