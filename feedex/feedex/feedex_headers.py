# -*- coding: utf-8 -*-

""" Loads dependencies and all Feedex modules
    Declares constants: field lists, SQL queries, prefixes etc."""



# Standard
import sys
import os
from datetime import datetime, timedelta, date
import re
from math import log10
import subprocess
import time
import pickle
from shutil import copyfile
from random import randint
import json
import threading


# Downloaded
import feedparser
import urllib.request
import hashlib
import sqlite3
from dateutil.relativedelta import relativedelta
import dateutil.parser
import snowballstemmer
import pyphen

import gettext




# Constants
FEEDEX_VERSION = "1.0.0"
FEEDEX_RELEASE="2022"
FEEDEX_AUTHOR ="""Karol Pałac"""
FEEDEX_CONTACT="""palac.karol@gmail.com"""
FEEDEX_WEBSITE="""https://github.com/kpalac/feedex""" 

PLATFORM = sys.platform
if PLATFORM == 'linux':
    FEEDEX_CONFIG = os.environ['HOME'] + '/.config/feedex.conf'
    FEEDEX_SYS_CONFIG = '/etc/feedex.conf'

    FEEDEX_SYS_SHARED_PATH = '/usr/share/feedex'
    FEEDEX_SHARED_PATH = os.environ['HOME'] + '/.local/share/feedex'

    # Paths
    DIR_SEP = '/'
    APP_PATH = '/usr/bin'

    FEEDEX_ICON_PATH = os.environ['HOME'] + '/.local/share/feedex/icons'
    FEEDEX_CACHE_PATH = os.environ['HOME'] + '/.local/share/feedex/cache'

    FEEDEX_DEFAULT_BROWSER = 'xdg-open %u'

FEEDEX_SYS_ICON_PATH = f"{FEEDEX_SYS_SHARED_PATH}{DIR_SEP}data{DIR_SEP}pixmaps"
FEEDEX_MODELS_PATH = f'{FEEDEX_SYS_SHARED_PATH}{DIR_SEP}data{DIR_SEP}models'
FEEDEX_LOCALE_PATH = f'{FEEDEX_SYS_SHARED_PATH}{DIR_SEP}data{DIR_SEP}locales'


gettext.install('feedex', FEEDEX_LOCALE_PATH)

FEEDEX_DESC=_("Personal News and Notes organizer")

FEEDEX_HELP_ABOUT=f"""
<b>Feedex v. {FEEDEX_VERSION}</b>
{FEEDEX_DESC}

{_("Release")}: {FEEDEX_RELEASE}

{_("Author")}: {FEEDEX_AUTHOR}
{_("Contact")}: {FEEDEX_CONTACT}
{_("Website")}: {FEEDEX_WEBSITE}

"""


# Image elements extraction
IM_URL_RE=re.compile('src=\"(.*?)\"', re.IGNORECASE)
IM_ALT_RE=re.compile('alt=\"(.*?)\"', re.IGNORECASE)
IM_TITLE_RE=re.compile('title=\"(.*?)\"', re.IGNORECASE)

# RSS Handling and parsing
FEEDEX_USER_AGENT = 'UniversalFeedParser/5.0.1 +http://feedparser.org/'
RSS_HANDLER_TEST_RE = re.compile('<p.*?>.*?<.*?/p>|<div.*?>.*?<.*?/div>|<br.*?/>|<br/>|<img.*?/>|<span.*?>.*?<.*?/span>')
RSS_HANDLER_IMAGES_RE = re.compile('<img.*?src=\".*?\".*?/>', re.IGNORECASE)
RSS_HANDLER_IMAGES_RE2 = re.compile('<div style=".*?image:url\("(.*?)"\)">', re.IGNORECASE)

RSS_HANDLER_STRIP_HTML_RE = re.compile('<.*?>')

# Mimetypes
FEEDEX_IMAGE_MIMES = ('image/jpeg','image/gif','image/png','image/tiff','image/x-icon','image/svg+xml','image/vnd.microsoft.icon')
FEEDEX_TEXT_MIMES = ('text/html','text/plain',)

#Downloads...
FEEDEX_MB = 1024 * 1024
MAX_DOWNLOAD_SIZE = 50 * FEEDEX_MB

# Checks
FLOAT_VALIDATE_RE = re.compile(r'[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?')
URL_VALIDATE_RE = re.compile('http[s]?://?(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', re.IGNORECASE)
IP4_VALIDATE_RE = re.compile('^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$', re.IGNORECASE)
IP6_VALIDATE_RE = re.compile("""^(?:[0-9a-fA-F]{1,4}:){7}[0-9a-fA-F]{1,4}$|
^::(?:[0-9a-fA-F]{1,4}:){0,6}[0-9a-fA-F]{1,4}$|
^[0-9a-fA-F]{1,4}::(?:[0-9a-fA-F]{1,4}:){0,5}[0-9a-fA-F]{1,4}$|
^[0-9a-fA-F]{1,4}:[0-9a-fA-F]{1,4}::(?:[0-9a-fA-F]{1,4}:){0,4}[0-9a-fA-F]{1,4}$|
^(?:[0-9a-fA-F]{1,4}:){0,2}[0-9a-fA-F]{1,4}::(?:[0-9a-fA-F]{1,4}:){0,3}[0-9a-fA-F]{1,4}$|
^(?:[0-9a-fA-F]{1,4}:){0,3}[0-9a-fA-F]{1,4}::(?:[0-9a-fA-F]{1,4}:){0,2}[0-9a-fA-F]{1,4}$|
^(?:[0-9a-fA-F]{1,4}:){0,4}[0-9a-fA-F]{1,4}::(?:[0-9a-fA-F]{1,4}:)?[0-9a-fA-F]{1,4}$|
^(?:[0-9a-fA-F]{1,4}:){0,5}[0-9a-fA-F]{1,4}::[0-9a-fA-F]{1,4}$|
^(?:[0-9a-fA-F]{1,4}:){0,6}[0-9a-fA-F]{1,4}::$""", re.IGNORECASE)

# Helper REGEXes
SPLIT_RE = re.compile("""\s|/|\\|\.|;|:|@|#|_|-""")



# SQL...
DOC_COUNT_SQL="""
select count(e.id)
from entries e 
join feeds f on f.id = e.feed_id and coalesce(f.deleted, 0) = 0
where coalesce(e.deleted,0) = 0
"""



GET_RULES_SQL="""
SELECT
null as n, r.name, r.type, r.feed_id, r.field_id, r.string, r.case_insensitive, r.lang,
sum(r.weight * coalesce( coalesce(e.read, 
    case 
        when r.learned = 1 then 0
        else 1
    end
    ) * coalesce(e.weight,
	case 
		when r.learned = 1 then 0
		else 1
	end
	), r.archive) ) as main_weight,
r.additive, r.learned, r.flag, coalesce(r.context_id, 0) as context_id

from rules r
left join entries e on e.id = r.context_id
left join feeds f on f.id = e.feed_id
where coalesce(e.deleted,0) <> 1 and coalesce(f.deleted,0) <> 1

group by n, r.name, r.type, r.feed_id, r.field_id, r.case_insensitive, r.lang, r.additive, r.string, r.learned, r.flag, r.context_id

having sum(r.weight * coalesce( coalesce(e.read, 
    case 
        when r.learned = 1 then 0
        else 1
    end
    ) * coalesce(e.weight,
	case 
		when r.learned = 1 then 0
		else 1
	end
	), r.archive) ) <> 0
order by r.type asc, abs(main_weight) desc
"""


GET_RULES_NL_SQL="""
SELECT
null as n, r.name, r.type, r.feed_id, r.field_id, r.string, r.case_insensitive, r.lang, r.weight, r.additive, r.learned, r.flag, 0 as context_id
from rules r
where coalesce(r.learned,0) = 0 and r.context_id is NULL and r.type not in (5,4)
order by r.weight desc
"""





GET_FEEDS_SQL="""select * from feeds order by display_order asc"""


TERM_NET_SQL="""
select 
r.name,
r.weight, 
count(r.context_id) as c
from rules r where r.context_id in 
( select r1.context_id from rules r1 where lower(r1.name) = lower(:name) )
group by r.name, r.weight
"""


RESULTS_COLUMNS_SQL="""e.*, f.name || ' (' || f.id || ')' as feed_name_id, 
f.name as feed_name, datetime(e.pubdate,'unixepoch', 'localtime') as pubdate_r, strftime('%Y.%m.%d', date(e.pubdate,'unixepoch', 'localtime')) as pudbate_short, 
coalesce( nullif(fl.name,''), fl.id) as flag_name, f.user_agent as user_agent,
c.id as parent_id, coalesce(c.name, c.title, c.id) as parent_name
from entries e 
left join feeds f on f.id = e.feed_id
left join feeds c on c.id = f.parent_id
left join flags fl on fl.id = e.flag"""




EMPTY_TRASH_RULES_SQL = """delete from rules where context_id in
( select e.id from entries e where e.deleted = 1 or e.feed_id in 
( select f.id from feeds f where f.deleted = 1)  )"""

EMPTY_TRASH_ENTRIES_SQL = """delete from entries where deleted = 1 or feed_id in ( select f.id from feeds f where f.deleted = 1)"""

EMPTY_TRASH_FEEDS_SQL1 = """update feeds set parent_id = NULL where parent_id in ( select f1.id from feeds f1 where f1.deleted = 1)"""
EMPTY_TRASH_FEEDS_SQL2 = """delete from feeds where deleted = 1"""




SEARCH_HISTORY_SQL = """
select string,
max(datetime(date,'unixepoch', 'localtime')) as added_date,
max(date) as added_date_raw
from search_history where 
coalesce(string, '') <> '' 
group by string
order by date
"""



def n_(arg): return arg #To facilitate localization


ENTRIES_SQL_TABLE =      ('id','feed_id','charset','lang','title','author','author_contact','contributors','publisher','publisher_contact',
                                'link','pubdate','pubdate_str','guid','desc','category','tags','comments','text','source','adddate','adddate_str','links','read',
                                'importance','tokens','sent_count','word_count','char_count','polysyl_count','com_word_count','numerals_count','caps_count','readability',
                                'weight','flag','images','enclosures','tokens_raw','deleted')

ENTRIES_SQL_TYPES = (int, int,  str, str, str, str, str, str, str, str, str,  int, str,   str, str, str, str, str, str, str,   int, str,
                     str, int, float,     str,    int, int, int, int, int, int, int,    float, float,   int,   str, str, str,   int )

ENTRIES_SQL_TABLE_PRINT = (n_("ID"), n_("Source/Category"), n_("Character encoding"), n_("Language"), n_("Title"), n_("Author"), n_("Author - contact"), n_("Contributors"), n_("Publisher"), n_("Publisher - contact"),
                                  n_("Link"), n_("Date published (Epoch)"), n_("Date published (saved)"), n_("GUID"), n_("Description"), n_("Category"), n_("Tags"), n_("Comments link"), n_("Text"), n_("Source link"), n_("Date added (Epoch)"),
                                  n_("Date added"), n_("Internal links"), n_("Read"), n_("Importance"), n_("Token string (for indexing)"), n_("Sentence count"), n_("Word count"), n_("Character count"), n_("Polysylable count"), n_("Common words count"),
                                  n_("Numerals count"), n_("Capitalized words count"), n_("Readability"), n_("Weight"), n_("Flag"), n_("Images"), n_("Enclosures"), n_("Raw Token string (for term context)"), n_("Deleted?"))


RESULTS_SQL_TABLE                = ENTRIES_SQL_TABLE + ("feed_name_id", "feed_name", "pubdate_r", "pubdate_short", "flag_name", "user_agent", "parent_id", "parent_name", "snippets", "rank", "count")
RESULTS_SQL_TYPES                = ENTRIES_SQL_TYPES + (str, str, str, str, str, str, str, int, str, float, int)

RESULTS_SQL_TABLE_PRINT          = ENTRIES_SQL_TABLE_PRINT + (n_("Source (ID)"), n_("Source"), n_("Published - Timestamp"), n_("Date"), n_("Flag name"), n_("User Agent"), n_("Parent Category ID"), n_("Parent Category"), n_("Snippets"), n_("Rank"), n_("Count"))
RESULTS_SHORT_PRINT1             = ("ID", "Source (ID)", "Date", "Title", "Description", "Text", "Author", "Link","Published - Timestamp", "Read", "Flag name", "Parent Category","Parent Category ID", "Importance", "Word count", "Weight", "Snippets", "Rank", "Count")
RESULTS_SHORT_PRINT2             = ("ID", "Source (ID)", "Date", "Title", "Description", "Text", "Author", "Link","Published - Timestamp", "Read", "Flag name","Parent Category","Parent Category ID", "Importance", "Word count", "Weight")

NOTES_PRINT                      = ("ID", "Date", "Title", "Description", "Importance", "Weight", "Deleted?", "Published - Timestamp", "Source (ID)")
HEADLINES_PRINT                  = ("Date", "Title","Source (ID)", "ID")
RESULTS_TOKENIZE_TABLE           = ("title","desc","text")



FEEDS_SQL_TABLE       =  ('id','charset','lang','generator','url','login','domain','passwd','auth','author','author_contact','publisher','publisher_contact',
                                'contributors','copyright','link','title','subtitle','category','tags','name','lastread','lastchecked','interval','error',
                                'autoupdate','http_status','etag','modified','version','is_category','parent_id', 'handler','deleted', 'user_agent', 'fetch',
                                'rx_entries','rx_title', 'rx_link', 'rx_desc', 'rx_author', 'rx_category', 'rx_text', 'rx_images', 'rx_pubdate', 
                                'rx_pubdate_feed', 'rx_image_feed', 'rx_title_feed', 'rx_charset_feed', 'rx_lang_feed',
                                'script_file', 'icon_name', 'display_order')
FEEDS_SQL_TYPES = (int,  str, str, str, str, str,str, str, str, str, str,str, str, str, str, str,str, str, str, str, str, str, str,
                  int, int, int,   str, str, str, str,   int, int,    str, int,     str, int,
                  str, str, str, str, str, str, str, str, str, str, str, str, str, str,
                  str, str, int)

FEEDS_REGEX_HTML_PARSERS = ('rx_entries','rx_title', 'rx_link', 'rx_desc', 'rx_author', 'rx_category', 'rx_text', 'rx_images', 'rx_pubdate', 'rx_pubdate_feed', 'rx_image_feed','rx_title_feed', 'rx_charset_feed', 'rx_lang_feed')


FEEDS_SQL_TABLE_PRINT = (n_("ID"), n_("Character encoding"), n_("Language"), n_("Feed generator"), n_("URL"), n_("Login"), n_("Domain"), n_("Password"), n_("Authentication method"), n_("Author"), n_("Author - contact"),
                                n_("Publisher"), n_("Publisher - contact"), n_("Contributors"), n_("Copyright"), n_("Home link"), n_("Title"), n_("Subtitle"), n_("Category"), n_("Tags"), n_("Name"), n_("Last read date (Epoch)"),
                                n_("Last check date (Epoch)"), n_("Update interval"), n_("Errors"), n_("Autoupdate?"), n_("Last connection HTTP status"), n_("ETag"), n_("Modified tag"), n_("Protocol version"), n_("Is category?"), 
                                n_("Category ID"), n_("Handler"), n_("Deleted?"), n_("User Agent"), n_("Fetch?"),
                                n_("Entries REGEX (HTML)"), n_("Title REGEX (HTML)"), n_("Link REGEX (HTML)"), n_("Description REGEX (HTML)"), n_("Author REGEX (HTML)"), n_("Category REGEX (HTML)"), 
                                n_("Additional Text REGEX (HTML)"), n_("Image extraction REGEX (HTML)"), n_("Published date REGEX (HTML)"),
                                n_("Published date - Feed REGEX (HTML)"), n_("Image/Icon - Feed REGEX (HTML)"), n_("Title REGEX - Feed (HTML)"), n_("Charset REGEX - Feed (HTML)"), 
                                n_("Lang REGEX - Feed (HTML)"), n_("Script file"), n_("Icon name"), n_("Display Order"))


FEEDS_SHORT_PRINT      = ("ID", "Name", "Title", "Subtitle", "Category", "Tags", "Publisher", "Author", "Home link", "URL", "Feedex Category", "Deleted?", "User Agent", "Fetch?", "Display Order")
CATEGORIES_PRINT       = ("ID", "Name", "Subtitle","Deleted?","No of Children", "Icon name")





RULES_SQL_TABLE =        ('id','name','type','feed_id','field_id','string','case_insensitive','lang','weight','additive','learned','context_id','flag','archive','path')
RULES_SQL_TYPES = (int, str, int, int, str,   str, int, str,    float,   int, int, int, int,  float, str)

RULES_SQL_TABLE_RES = RULES_SQL_TABLE + ('flag_name', 'feed_name', 'field_name', 'query_type', 'matched')
_

RULES_SQL_TABLE_PRINT =  (n_('ID'), n_('Name'), n_('Type'),n_('Feed ID'), n_('Field ID'), n_('Search string'), n_('Case insensitive?'), n_('Language'), n_('Weight'), 
                            n_('Additive?'), n_('Learned?'), n_('Context Entry ID'), n_('Flag'), n_('Archived Weight'), n_('In-Context path'))

RULES_SQL_TABLE_RES_PRINT = RULES_SQL_TABLE_PRINT + (n_('Flag name'), n_('Feed/Category name'), n_('Field name'), n_('Query Type'), n_('No. of matches'))

PRINT_RULES_SHORT = ("ID", "Name", "Search string", "Weight", "Case insensitive?", "Type", "Learned?", "Flag name", "Flag", "Field name", "Feed/Category name", 'Archived Weight')
PRINT_RULES_FOR_ENTRY = ("Name", "Search string", "No. of matches", "Weight", "Case insensitive?", "Type", "Learned?", "Flag name", "Flag", "Field name", "Feed/Category name", 'Context Entry ID')

RULES_TECH_LIST = ('learned','context_id','archive','path')




LING_LIST = ('feed_id','lang','author','publisher','contributors','title','desc','tags','category','text')
LING_TEXT_LIST = ('title','desc','tags','category','text', 'author', 'publisher', 'contributors')
LING_TECH_LIST = ('tokens','tokens_raw','sent_count','word_count','char_count','polysyl_count','com_word_count','numerals_count','caps_count','readability','weight','importance')


HISTORY_SQL_TABLE = ('id', 'string', 'feed_id', 'date')
HISTORY_SQL_TYPES = (int, str, int, int)

FLAGS_SQL_TABLE = ('id', 'name', 'desc', 'color', 'color_cli')
FLAGS_SQL_TABLE_PRINT = (n_('ID'), n_('Name'), n_('Description'), n_('GUI display color'), n_('CLI display color'))
FLAGS_SQL_TYPES = (int, str, str, str, str)




HEURISTIC_MODEL={
'names' : ('heuristic',),
'skip_multiling' : False,
'REGEX_tokenizer' : r"""([a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+|»|«|\w+['-'\w]\w+|\d+[\.,\d]+\d+|\.[a-z][0-9]+|[\.!\?'"”“””&,;:\[\]\{\}\(\)]|#[a-zA-Z0-9]*|\w+\d+|\d+\w+|\d+|\w+)""",
'REGEX_query_tokenizer' : """(\*|~\d+|~|[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+|[\w\*]+['-'\w\*][\w\*]+|[\d\*]+[\.,\d\*]+[\d\*]+|\.[a-z][0-9\*]+|[\.!\?'"”“””&,;:\[\]\{\}\(\)\*]|#[a-zA-Z0-9\*]*|[\w\*]+[\d\*]+|[\d\*]+[\w\*]+|[\d\*]+|[\w\*]+)""",
'stemmer' : 'english',
'pyphen' : 'en_EN',
'stop_list' : (), 
'swadesh_list' : (),
'bicameral' : 1,
'name_cap' : 1,
'writing_system' : 1,
'rules': (
    (True, 2, True, 0, '(;CAP[^\s]*;UNCOMM:\d*)' ),
    (True, 4, True, 0, '(;ALLCAP[^\s]*;UNCOMM:\d*)' ),
    (True, 5, True, 0, '(;CNER_BEG[^\s]*:\d*.*?;CNER_END[^\s]*:\d*)' ),
    (True, 8, True, 3, '(;QB[^\s]*:\d*.*?\s[^\s]*;QE[^\s]*:\d*)' ),
    (True, 8, True, 3, '(;EMPB[^\s]*:\d*.*?\s[^\s]*;EMPE[^\s]*:\d*)' ),
    (True, 2, True, 0, '(;POLYSYL[^\s]*;UNCOMM:\d*)' ),
    (True, 5, False, 0, '(;HASHTAG[^\s]*:\d*)' ),
    (True, 5, False, 0, '(;EMAIL[^\s]*:\d*)' ),
    (True, 2, True, 0, '(;ALLCAP[^\s]*:\d*)' ),
    (True, 5, False, 0, '(;ACNER[^\s]*:\d*)' ),
    (True, 4, True, 0, '(;NER[^\s]*:\d*)' ),
    (True, 0.3, True, 0, '(;UNCOMM[^\s]*:\d*)' ), # uncommon words can be useful, but we should not exagerate weight
    (True, 5, True, 0, '(;CAP[^\s]*:\d*[\s][^\s]*;CONN[^\s]*:\d*[\s][^\s]*;CAP[^\s]*:\d*)' ), # e.g. Lana del Rey
    (True, 5, True, 0, '(;CAP[^\s]*:\d*[\s][^\s]*;CONN[^\s]*:\d*[\s][^\s]*;CONN[^\s]*:\d*[\s][^\s]*;CAP[^\s]*:\d*)' ), # e.g. Oscar de la Hoya
    (True, 5, True, 0, '(;ALLCAP[^\s]*:\d*\s[^\s]*;CONN[^\s]*:\d*\s[^\s]*;ALLCAP[^\s]*:\d*)' ),
    (True, 5, True, 0, '(;CAP[^\s]*:\d*\s[^\s]*;NNER[^\s]*:\d*)' ),
    (True, 5, True, 0, '(;ALLCAP[^\s]*:\d*\s[^\s]*;NNER[^\s]*:\d*)' ),
    (True, 4, True, 0, '(;NNER[^\s]*:\d*\s[^\s]*;PP1[^\s]*:\d*\s[^\s]*;CAP[^\s]*:\d*)' ),
    (True, 5, True, 0, '(;NNER[^\s]*:\d*\s[^\s]*;PP1[^\s]*:\d*\s[^\s]*;ALLCAP[^\s]*:\d*)' ),
    (True, 5, True, 0, '(;NAME[^\s]*:\d*\s[^\s]*;SURN[^\s]*:\d*)' ),
    (True, 5, True, 0, '(;NAME[^\s]*:\d*\s[^\s]*;FCONN[^\s]*;SURN[^\s]*:\d*)' ),
    (True, 5, True, 0, '(;NAME[^\s]*:\d*\s[^\s]*;CAP[^\s]*:\d*)' ),
    (True, 5, True, 0, '(;NAME[^\s]*:\d*\s[^\s]*;NAME[^\s]*:\d*\s[^\s]*;CAP[^\s]*:\d*)' ),
    (True, 5, True, 0, '(;NAME[^\s]*:\d*\s[^\s]*;CAP[^\s]*:\d*\s[^\s]*;CAP[^\s]*:\d*)' ),
    (True, 3, True, 0, '(;NAME[^\s]*:\d*)' ),
    (True, 4, True, 0, '(;SURN[^\s]*:\d*)' ),
    (True, 5, True, 0, '(;CAP[^\s]*:\d*\s[^\s]*;SURN[^\s]*:\d*)' ),
    (True, 5, True, 0, '(;NAME[^\s]*:\d*\s[^\s]*;RNUM[^\s]*:\d*)' )    
),



}


# Hardcoded limit params
MAX_SNIPPET_COUNT = 50
MAX_RANKING_DEPTH = 20

LOCAL_DB_TIMEOUT = 180 

MAX_LAST_UPDATES = 25


#Prefix, sql field name, Field name, 
PREFIXES={
'feed_id' :     {'prefix':'MF', 'sql':'f.id',           'name':_('Feed ID'),       'stem':False, 'meta':True, 'weight':2,      'ignore':None,                              'all_feat':True},
'lang' :        {'prefix':'ML', 'sql':'e.lang',         'name':_('Language'),      'stem':False, 'meta':True, 'weight':0,    'ignore':None,                              'all_feat':True},
'author' :      {'prefix':'MA', 'sql':'e.author',       'name':_('Author'),        'stem':False, 'meta':True, 'weight':1,      'ignore':'www,mail,email,mailto',        'all_feat':True},
'publisher':    {'prefix':'MP', 'sql':'e.publisher',    'name':_('Publisher'),     'stem':False, 'meta':True, 'weight':1,      'ignore':'www,mail,email,mailto,http',  'all_feat':True},
'contributors': {'prefix':'MC', 'sql':'e.contributors', 'name':_('Contributors'),  'stem':False, 'meta':True, 'weight':1,      'ignore':'www,mail,email,mailto,http',  'all_feat':True},

'title':        {'prefix':'TT', 'sql':'e.title',    'name':_('Title'),         'stem':True, 'meta':False,  'weight':2, 'ignore':None, 'all_feat':False},
'desc':         {'prefix':'TD', 'sql':'e.desc',     'name':_('Description'),   'stem':True, 'meta':False,  'weight':1, 'ignore':None, 'all_feat':False},
'tags':         {'prefix':'MT', 'sql':'e.tags',     'name':_('Tags'),          'stem':True, 'meta':True,   'weight':2, 'ignore':None, 'all_feat':True},
'category':     {'prefix':'TC', 'sql':'e.category', 'name':_('Category'),      'stem':True, 'meta':True,   'weight':3, 'ignore':None, 'all_feat':True},
'text':         {'prefix':'TX', 'sql':'e.text',     'name':_('Text'),          'stem':True, 'meta':False,  'weight':1, 'ignore':None, 'all_feat':False}
}


# Terminal display
if PLATFORM == 'linux':
    TCOLS = {
    'DEFAULT'    : '\033[0m',
    'WHITE'      : '\033[0;37m',
    'WHITE_BOLD' : '\033[1;37m',
    'YELLOW'     : '\033[0;33m',
    'YELLOW_BOLD': '\033[1;33m',
    'CYAN'       : '\033[0;36m',
    'CYAN_BOLD'  : '\033[1;36m',
    'BLUE'       : '\033[0;34m',
    'BLUE_BOLD'  : '\033[1;34m',
    'RED'        : '\033[0;31m',
    'RED_BOLD'   : '\033[1;31m',
    'GREEN'      : '\033[0;32m',
    'GREEN_BOLD' : '\033[1;32m',
    'PURPLE'     : '\033[0;35m',
    'PURPLE_BOLD': '\033[1;35m',
    'LIGHT_RED'  : '\033[0;91m',
    'LIGHT_RED_BOLD' : '\033[1;91m'
    }



TERM_NORMAL = TCOLS['DEFAULT']
TERM_BOLD   = TCOLS['WHITE_BOLD']
TERM_ERR = TCOLS['LIGHT_RED']
TERM_ERR_BOLD = TCOLS['LIGHT_RED_BOLD']

TERM_FLAG = TCOLS['YELLOW_BOLD']
TERM_READ = TCOLS['WHITE_BOLD']
TERM_DELETED = TCOLS['RED']
TERM_SNIPPET_HIGHLIGHT = TCOLS['CYAN_BOLD']

BOLD_MARKUP_BEG = '<b>'
BOLD_MARKUP_END = '</b>'


DEFAULT_CONFIG = {
            'log' : f'{FEEDEX_SHARED_PATH}{DIR_SEP}feedex.log',
            'db_path' : f'{FEEDEX_SHARED_PATH}{DIR_SEP}feedex.db',
            'browser' : f'{APP_PATH}{DIR_SEP}firefox --new-tab %u',
            'lang' : 'en',
            'user_agent' : FEEDEX_USER_AGENT,
            'timeout' : 15,
            'default_interval': 45,
            'error_threshold': 5,
            'max_items_per_transaction': 300,
            'ignore_images' : False,
            'rule_limit' : 50000,
            'use_keyword_learning' : True,
            'use_search_habits' : True,
            'learn_from_added_entries': True,
            'no_history': False,
            'default_entry_weight' : 2,
            'default_rule_weight' : 2,
            'query_rule_weight' : 10,
            'default_similarity_limit' : 20,
            'default_depth' : 5,
            'do_redirects' : True,
            'save_perm_redirects': False,
            'mark_deleted' : False,
            'ignore_modified': True,
            
            'gui_desktop_notify' : True, 
            'gui_fetch_periodically' : False,
            'gui_notify_group': 'feed',
            'gui_notify_depth': 5,

            'gui_new_color' : '#0FDACA',
            'gui_deleted_color': 'grey',
            'gui_hilight_color' : 'blue',
            'gui_default_flag_color' : 'blue',

            'gui_layout' : 0,
            'gui_orientation' : 0,

            'window_name_exclude' : 'Firefox,firefox,chrome,Chrome,Mozilla,mozilla,Thunderbird,thunderbird',

            'imave_viewer': '',
            'text_viewer' : '',
            'search_engine': 'https://duckduckgo.com/?t=ffab&q=%Q&ia=web',
            'gui_clear_cache' : 30,
            'gui_key_search': 's',
            'gui_key_new_entry': 'n',
            'gui_key_new_rule': 'r',

            'normal_color' : 'DEFAULT',
            'flag_color': 'YELLOW_BOLD',
            'read_color': 'WHITE_BOLD',
            'bold_color': 'WHITE_BOLD',
            'bold_markup_beg': '<b>',
            'bold_markup_end': '</b>'


}

CONFIG_NAMES = {
            'log' : _('Log file'),
            'db_path' : _('Feedex database'),
            'browser' : _('Browser command'),
            'lang' : _('Language'),
            'user_agent': _('User Agent String'),
            'timeout' : _('Database timeout'),
            'default_interval': _('Default Channel check interval'),
            'error_threshold': _('Channel error threshold'),
            'max_items_per_transaction': _('Max items for a single transaction'),
            'ignore_images' : _('Ignore image processing'),
            'rule_limit' : _('Limit for rules'),
            'use_keyword_learning' : _('Use keyword learning'),
            'use_search_habits' : _('Use search habits'),
            'no_history' : _('Do not save queries in History'),
            'learn_from_added_entries': _('Learn from added Entries'),
            'default_entry_weight' : _('Default Entry weight'),
            'default_rule_weight' : _('Default Rule weight'),
            'query_rule_weight' : _('Default Rule wieght (query)'),
            'default_similarity_limit' : _('Max similar items'),
            'default_depth' : _('Default grouping depth'),
            'do_redirects' : _('Do HTTP redirects'),
            'save_perm_redirects' : _('Save permanent HTTP redirects'),
            'mark_deleted' : _('Mark deleted RSS channels as unhealthy'),
            'do_redirects' : _('Do HTTP redirects'),

            'ignore_modified': _('Ignore MODIFIED and ETag tags'),
            
            'gui_desktop_notify' : _('Push desktop notifications for new items'), 
            'gui_fetch_periodically' : _('Fetch news periodically'),
            'gui_notify_group': _('Notification grouping'),
            'gui_notify_depth': _('Notification depth'),

            'gui_new_color' : _('New item color'),
            'gui_deleted_color': _('Deleted item color'),
            'gui_hilight_color' : _('Search hilight color'),
            'gui_default_flag_color' : _('Default Color for Flags'),

            'gui_layout' : _('GUI pane layout'),
            'gui_orientation' : _('GUI pane orientation'),

            'window_name_exclude' : _('Phrases to exclude from window name'),

            'imave_viewer': _('Image viewer command'),
            'text_viewer': _('Text File viewer command'),
            'search_engine': _('Search Engine to use in GUI'),
            'gui_clear_cache' : _('Clear image cache after n days'),
            'gui_key_search': _('New Search shortkut key'),
            'gui_key_new_entry': _('New Entry shortcut key'),
            'gui_key_new_rule': _('New Rule shortcut key'),

            'normal_color' : _('CLI normal color'),
            'flag_color': _('CLI default flagged color'),
            'read_color': _('CLI read color'),
            'bold_color': _('CLI bold style'),
            'bold_markup_beg': _('Bold section beginning markup'),
            'bold_markup_end': _('Bold section end markup')
}


CONFIG_INTS_NZ=('timeout','notify_level','default_interval','error_threshold','max_items_per_transaction', 'default_similarity_limit')
CONFIG_INTS_Z=('rule_limit','gui_clear_cache','default_depth','gui_layout','gui_orientation','gui_notify_depth')

CONFIG_FLOATS=('default_entry_weight', 'default_rule_weight', 'query_rule_weight' )

CONFIG_STRINGS=('log','db_path','browser','lang','user_agent', 'gui_notify_group', 'window_name_exclude', \
    'gui_new_color','gui_deleted_color', 'gui_hilight_color', 'gui_default_flag_color' ,'imave_viewer','text_viewer','search_engine','bold_markup_beg','bold_markup_end')
CONFIG_KEYS=('gui_key_search','gui_key_new_entry', 'gui_key_new_rule')

CONFIG_BOOLS=('notify','ignore_images', 'use_keyword_learning', 'learn_from_added_entries','do_redirects','ignore_modified','gui_desktop_notify',
'gui_fetch_periodically', 'use_search_habits', 'save_perm_redirects', 'mark_deleted', 'no_history')

CONFIG_COLS=('normal_color','flag_color','read_color','bold_color')




# Exceptions
class FeedexTypeError(Exception):
    def __init__(self, *args):
        if args: self.message = args[0]
        else: self.message = None

    def __str__(self):
        print(f'Type invalid! {self.message}')







# HTML entities
HTML_ENTITIES = (
('&#160;','&nbsp;',''),
('&#161;','&iexcl;','¡'),
('&#162;','&cent;','¢'),
('&#163;','&pound;','£'),
('&#164;','&curren;','¤'),
('&#165;','&yen;','¥'),
('&#166;','&brvbar;','¦'),
('&#167;','&sect;','§'),
('&#168;','&uml;','¨'),
('&#169;','&copy;','©'),
('&#170;','&ordf;','ª'),
('&#171;','&laquo;','«'),
('&#172;','&not;','¬'),
('&#173;','&shy;',''),
('&#174;','&reg;','®'),
('&#175;','&macr;','¯'),
('&#176;','&deg;','°'),
('&#177;','&plusmn;','±'),
('&#178;','&sup2;','²'),
('&#179;','&sup3;','³'),
('&#180;','&acute;','´'),
('&#181;','&micro;','µ'),
('&#182;','&para;','¶'),
('&#183;','&middot;','·'),
('&#184;','&ccedil;','¸'),
('&#185;','&sup1;','¹'),
('&#186;','&ordm;','º'),
('&#187;','&raquo;','»'),
('&#188;','&frac14;','¼'),
('&#189;','&frac12;','½'),
('&#190;','&frac34;','¾'),
('&#191;','&iquest;','¿'),
('&#192;','&Agrave;','À'),
('&#193;','&Aacute;','Á'),
('&#194;','&Acirc;','Â'),
('&#195;','&Atilde;','Ã'),
('&#196;','&Auml;','Ä'),
('&#197;','&Aring;','Å'),
('&#198;','&AElig;','Æ'),
('&#199;','&Ccedil;','Ç'),
('&#200;','&Egrave;','È'),
('&#201;','&Eacute;','É'),
('&#202;','&Ecirc;','Ê'),
('&#203;','&Euml;','Ë'),
('&#204;','&Igrave;','Ì'),
('&#205;','&Iacute;','Í'),
('&#206;','&Icirc;','Î'),
('&#207;','&Iuml;','Ï'),
('&#208;','&ETH;','Ð'),
('&#209;','&Ntilde;','Ñ'),
('&#210;','&Ograve;','Ò'),
('&#211;','&Oacute;','Ó'),
('&#212;','&Ocirc;','Ô'),
('&#213;','&Otilde;','Õ'),
('&#214;','&Ouml;','Ö'),
('&#215;','&times;','×'),
('&#216;','&Oslash;','Ø'),
('&#217;','&Ugrave;','Ù'),
('&#218;','&Uacute;','Ú'),
('&#219;','&Ucirc;','Û'),
('&#220;','&Uuml;','Ü'),
('&#221;','&Yacute;','Ý'),
('&#222;','&THORN;','Þ'),
('&#223;','&szlig;','ß'),
('&#224;','&agrave;','à'),
('&#225;','&aacute;','á'),
('&#226;','&acirc;','â'),
('&#227;','&atilde;','ã'),
('&#228;','&auml;','ä'),
('&#229;','&aring;','å'),
('&#230;','&aelig;','æ'),
('&#231;','&ccedil;','ç'),
('&#232;','&egrave;','è'),
('&#233;','&eacute;','é'),
('&#234;','&ecirc;','ê'),
('&#235;','&euml;','ë'),
('&#236;','&igrave;','ì'),
('&#237;','&iacute;','í'),
('&#238;','&icirc;','î'),
('&#239;','&iuml;','ï'),
('&#240;','&eth;','ð'),
('&#241;','&ntilde;','ñ'),
('&#242;','&ograve;','ò'),
('&#243;','&oacute;','ó'),
('&#244;','&ocirc;','ô'),
('&#245;','&otilde;','õ'),
('&#246;','&ouml;','ö'),
('&#247;','&divide;','÷'),
('&#248;','&oslash;','ø'),
('&#249;','&ugrave;','ù'),
('&#250;','&uacute;','ú'),
('&#251;','&ucirc;','û'),
('&#252;','&uuml;','ü'),
('&#253;','&yacute;','ý'),
('&#254;','&thorn;','þ'),
('&#255;','&yuml;','ÿ'),
('&#402;','&fnof;','ƒ'),
('&#913;','&Alpha;','Α'),
('&#914;','&Beta;','Β'),
('&#915;','&Gamma;','Γ'),
('&#916;','&Delta;','Δ'),
('&#917;','&Epsilon;','Ε'),
('&#918;','&Zeta;','Ζ'),
('&#919;','&Eta;','Η'),
('&#920;','&Theta;','Θ'),
('&#921;','&Iota;','Ι'),
('&#922;','&Kappa;','Κ'),
('&#923;','&Lambda;','Λ'),
('&#924;','&Mu;','Μ'),
('&#925;','&Nu;','Ν'),
('&#926;','&Xi;','Ξ'),
('&#927;','&Omicron;','Ο'),
('&#928;','&Pi;','Π'),
('&#929;','&Rho;','Ρ'),
('&#931;','&Sigma;','Σ'),
('&#932;','&Tau;','Τ'),
('&#933;','&Upsilon;','Υ'),
('&#934;','&Phi;','Φ'),
('&#935;','&Chi;','Χ'),
('&#936;','&Psi;','Ψ'),
('&#937;','&Omega;','Ω'),
('&#945;','&alpha;','α'),
('&#946;','&beta;','β'),
('&#947;','&gamma;','γ'),
('&#948;','&delta;','δ'),
('&#949;','&epsilon;','ε'),
('&#950;','&zeta;','ζ'),
('&#951;','&eta;','η'),
('&#952;','&theta;','θ'),
('&#953;','&iota;','ι'),
('&#954;','&kappa;','κ'),
('&#955;','&lambda;','λ'),
('&#956;','&mu;','μ'),
('&#957;','&nu;','ν'),
('&#958;','&xi;','ξ'),
('&#959;','&omicron;','ο'),
('&#960;','&pi;','π'),
('&#961;','&rho;','ρ'),
('&#962;','&sigmaf;','ς'),
('&#963;','&sigma;','σ'),
('&#964;','&tau;','τ'),
('&#965;','&upsilon;','υ'),
('&#966;','&phi;','φ'),
('&#967;','&chi;','χ'),
('&#968;','&psi;','ψ'),
('&#969;','&omega;','ω'),
('&#977;','&thetasym;','ϑ'),
('&#978;','&upsih;','ϒ'),
('&#982;','&piv;','ϖ'),
('&#8226;','&bull;','•'),
('&#8230;','&hellip;','…'),
('&#8242;','&prime;','′'),
('&#8243;','&Prime;','″'),
('&#8254;','&oline;','‾'),
('&#8260;','&frasl;','⁄'),
('&#8472;','&weierp;','℘'),
('&#8465;','&image;','ℑ'),
('&#8476;','&real;','ℜ'),
('&#8482;','&trade;','™'),
('&#8501;','&alefsym;','ℵ'),
('&#8592;','&larr;','←'),
('&#8593;','&uarr;','↑'),
('&#8594;','&rarr;','→'),
('&#8595;','&darr;','↓'),
('&#8596;','&harr;','↔'),
('&#8629;','&crarr;','↵'),
('&#8656;','&lArr;','⇐'),
('&#8657;','&uArr;','⇑'),
('&#8658;','&rArr;','⇒'),
('&#8659;','&dArr;','⇓'),
('&#8660;','&hArr;','⇔'),
('&#8704;','&forall;','∀'),
('&#8706;','&part;','∂'),
('&#8707;','&exist;','∃'),
('&#8709;','&empty;','∅'),
('&#8711;','&nabla;','∇'),
('&#8712;','&isin;','∈'),
('&#8713;','&notin;','∉'),
('&#8715;','&ni;','∋'),
('&#8719;','&prod;','∏'),
('&#8721;','&sum;','∑'),
('&#8722;','&minus;','−'),
('&#8727;','&lowast;','∗'),
('&#8730;','&radic;','√'),
('&#8733;','&prop;','∝'),
('&#8734;','&infin;','∞'),
('&#8736;','&ang;','∠'),
('&#8743;','&and;','∧'),
('&#8744;','&or;','∨'),
('&#8745;','&cap;','∩'),
('&#8746;','&cup;','∪'),
('&#8747;','&int;','∫'),
('&#8756;','&there4;','∴'),
('&#8764;','&sim;','∼'),
('&#8773;','&cong;','≅'),
('&#8776;','&asymp;','≈'),
('&#8800;','&ne;','≠'),
('&#8801;','&equiv;','≡'),
('&#8804;','&le;','≤'),
('&#8805;','&ge;','≥'),
('&#8834;','&sub;','⊂'),
('&#8835;','&sup;','⊃'),
('&#8836;','&nsub;','⊄'),
('&#8838;','&sube;','⊆'),
('&#8839;','&supe;','⊇'),
('&#8853;','&oplus;','⊕'),
('&#8855;','&otimes;','⊗'),
('&#8869;','&perp;','⊥'),
('&#8901;','&sdot;','⋅'),
('&#8968;','&lceil;','⌈'),
('&#8969;','&rceil;','⌉'),
('&#8970;','&lfloor;','⌊'),
('&#8971;','&rfloor;','⌋'),
('&#9001;','&lang;','〈'),
('&#9002;','&rang;','〉'),
('&#9674;','&loz;','◊'),
('&#9824;','&spades;','♠'),
('&#9827;','&clubs;','♣'),
('&#9829;','&hearts;','♥'),
('&#9830;','&diams;','♦'),
('&#34;','&quot;','"'),
('&#38;','&amp;','&'),
('&#60;','&lt;','<'),
('&#62;','&gt;','>'),
('&#338;','&OElig;','Œ'),
('&#339;','&oelig;','œ'),
('&#352;','&Scaron;','Š'),
('&#353;','&scaron;','š'),
('&#376;','&Yuml;','Ÿ'),
('&#710;','&circ;','ˆ'),
('&#732;','&tilde;','˜'),
('&#8194;','&ensp;',''),
('&#8195;','&emsp;',''),
('&#8201;','&thinsp;',''),
('&#8204;','&zwnj;',''),
('&#8205;','&zwj;',''),
('&#8206;','&lrm;',''),
('&#8207;','&rlm;',''),
('&#8211;','&ndash;','–'),
('&#8212;','&mdash;','—'),
('&#8216;','&lsquo;','‘'),
('&#8217;','&rsquo;','’'),
('&#8218;','&sbquo;','‚'),
('&#8220;','&ldquo;','“'),
('&#8221;','&rdquo;','”'),
('&#8222;','&bdquo;','„'),
('&#8224;','&dagger;','†'),
('&#8225;','&Dagger;','‡'),
('&#8240;','&permil;','‰'),
('&#8249;','&lsaquo;','‹'),
('&#8250;','&rsaquo;','›'),
('&#039;','&apos;',"'"),
('&#038;','&apos;',"'"),
)




class FeedexMainDataContainer:
    """ Main Container class for Feedex """    
    def __init__(self, **kargs):

        # Data edit lock
        self.__dict__['lock'] = threading.Lock()

        # Global configuration
        self.__dict__['config'] = kargs.get('config', DEFAULT_CONFIG)

        # Language models
        self.__dict__['models'] = {}
        self.__dict__['multi_dict'] = {}
        self.__dict__['loaded_models'] = []

        
        # DB stuff
        self.__dict__['feeds'] = []
        self.__dict__['rules'] = []
        self.__dict__['search_history'] = []
        self.__dict__['flags'] = {}

        self.__dict__['doc_count'] = None
        self.__dict__['avg_weight'] = None
        self.__dict__['fetches'] = None

        # Hash for DB path for ID
        self.__dict__['db_hash'] = None

        # GUI stuff
        self.__dict__['icons'] = {}

        # Local DB lock
        self.__dict__['db_lock'] = False

        # Connection counter
        self.__dict__['conns'] = 0

        # Main return status
        self.__dict__['ret_status'] = 0



    def __setattr__(self, __name: str, __value) -> None:
        """ Setter with lock """
        self.lock.acquire()
        self.__dict__[__name] = __value
        self.lock.release()






# Our modules
from feedex_utils import *
from feedex_feed import *
from feedex_ling_processor import *
from feedex_entry import *
from feedex_rule import *
from feedex_handlers import *
from feeder_query_parser import *
from feeder import *
from feedex_docs import *
