#from feedback import FeedbackV4  # removed from WP API
#from feedback import FeedbackV5  # removed from WP API
from article_history import ArticleHistory
from assessment import Assessment
from backlinks import Backlinks
from dom import DOM
from google import GoogleNews
from google import GoogleSearch
from grokse import PageViews
from interwikilinks import InterWikiLinks
from langlinks import LangLinks
from nineteen_dom import NineteenDOM
from protection import Protection
from revisions import Revisions
from templates import ParsedTemplates
from watchers import Watchers
from wikitrust import Wikitrust


ALL_INPUTS = [ArticleHistory,
              Assessment,
              Backlinks,
              DOM,
              GoogleNews,
              GoogleSearch,
              InterWikiLinks,
              LangLinks,
              NineteenDOM,
              PageViews,
              ParsedTemplates,
              Protection,
              Revisions,
              Watchers,
              Wikitrust]

DEFAULT_INPUTS = [ArticleHistory,
                  Backlinks,
                  InterWikiLinks,
                  LangLinks,
                  NineteenDOM,
                  PageViews,
                  ParsedTemplates,
                  Protection]
