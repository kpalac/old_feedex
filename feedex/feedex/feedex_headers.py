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
import atexit
import pickle
from shutil import copyfile
from random import randint
import json


# Downloaded
import feedparser
#from twitter_scraper import get_tweets
import urllib.request
import hashlib
import sqlite3
from dateutil.relativedelta import relativedelta
import dateutil.parser
import snowballstemmer
import pyphen





# Constants
FEEDEX_VERSION = "1.0.0"
FEEDEX_RELEASE="2021"
FEEDEX_DESC="Personal News and Notes organizer"
FEEDEX_AUTHOR ="""Karol Pałac"""
FEEDEX_CONTACT="""palac.karol@gmail.com"""
FEEDEX_WEBSITE="""https://github.com/kpalac/feedex""" 

FEEDEX_HELP_ABOUT=f"""
<b>Feedex v. {FEEDEX_VERSION}</b>
{FEEDEX_DESC}

Release: {FEEDEX_RELEASE}

Author: {FEEDEX_AUTHOR}
Contact: {FEEDEX_CONTACT}
Website: 

"""
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

FEEDEX_SYS_ICON_PATH = f"{FEEDEX_SYS_SHARED_PATH}{DIR_SEP}data{DIR_SEP}pixmaps"
FEEDEX_MODELS_PATH = f'{FEEDEX_SYS_SHARED_PATH}{DIR_SEP}data{DIR_SEP}models'




# Image elements extraction
IM_URL_RE=re.compile('src=\"(.*?)\"', re.IGNORECASE)
IM_ALT_RE=re.compile('alt=\"(.*?)\"', re.IGNORECASE)
IM_TITLE_RE=re.compile('title=\"(.*?)\"', re.IGNORECASE)

# RSS Handling and parsing
FEEDEX_USER_AGENT = 'UniversalFeedParser/5.0.1 +http://feedparser.org/'
RSS_HANDLER_TEST_RE = re.compile('<p.*?>.*?<.*?/p>|<div.*?>.*?<.*?/div>|<br.*?/>|<br/>|<img.*?/>|<span.*?>.*?<.*?/span>')
RSS_HANDLER_IMAGES_RE = re.compile('<img.*?src=\".*?\".*?/>', re.IGNORECASE)
RSS_HANDLER_STRIP_HTML_RE = re.compile('<.*?>')

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
GET_RULES_SQL="""
SELECT
null as n,
r.name,
r.type,
r.feed_id,
r.field_id,
r.string,
r.case_insensitive,
r.lang,
sum(r.weight * coalesce(e.read, 
    case 
        when r.learned = 1 then 0
        else 1
    end
    ) * coalesce(e.weight,
	case 
		when r.learned = 1 then 0
		else 1
	end
	) ) as weight,
r.additive,
r.learned,
r.flag
from rules r
left join entries e on e.id = r.context_id
left join feeds f on f.id = e.feed_id
where coalesce(e.deleted,0) <> 1 and coalesce(f.deleted,0) <> 1
group by
n, 
r.name,
r.type,
r.feed_id,
r.field_id,
r.case_insensitive,
r.lang,
r.additive,
r.string,
r.learned,
r.flag

having sum(r.weight * coalesce(e.read, 
    case 
        when r.learned = 1 then 0
        else 1
    end
    ) * coalesce(e.weight,
	case 
		when r.learned = 1 then 0
		else 1
	end
	) ) > 0
order by r.type asc, weight desc
"""


GET_RULES_NL_SQL="""
SELECT
null as n,
r.name,
r.type,
r.feed_id,
r.field_id,
r.string,
r.case_insensitive,
r.lang,
sum(r.weight * coalesce(e.read, 
    case 
        when r.learned = 1 then 0
        else 1
    end
    ) * coalesce(e.weight,
	case 
		when r.learned = 1 then 0
		else 1
	end
	) ) as weight,
r.additive,
r.learned,
r.flag
from rules r
left join entries e on e.id = r.context_id
left join feeds f on f.id = e.feed_id
where coalesce(e.deleted,0) <> 1 and coalesce(f.deleted,0) <> 1 and r.learned in (0,2)
group by
n, 
r.name,
r.type,
r.feed_id,
r.field_id,
r.case_insensitive,
r.lang,
r.additive,
r.string,
r.learned,
r.flag

having sum(r.weight * coalesce(e.read, 
    case 
        when r.learned = 1 then 0
        else 1
    end
    ) * coalesce(e.weight,
	case 
		when r.learned = 1 then 0
		else 1
	end
	) ) > 0
order by r.type asc, weight desc
"""





GET_FEEDS_SQL="""select * from feeds"""


PRINT_RULES_SQL="""
select 
id,name,
string, 
weight,
case
    when case_insensitive = 0 then 'No'
    when case_insensitive = 1 then 'Yes'
    else 'No'
end as case_insensitive, 
case
    when type = 0 then 'String matching (keyword)'
    when type = 1 then 'Full text (stemmed, tokenized)'
    when type = 2 then 'Full text (exact)'
    when type = 3 then 'REGEX'
    when type = 4 then 'Learning alg. (stemmed)'
    when type = 5 then 'Learning alg. (exact)'
    else 'UNKNOWN'
end as type,
case
    when learned = 0 then 'No'
    when learned = 1 then 'Yes'
    when learned = 2 then 'From query'
end as learned,
case
    when flag = 0 or flag is NULL then 'None'
    else flag
end as flag
from rules where learned in (0,2)
"""
PRINT_RULES_TABLE = ("ID","Name","Search string","Weight","Case insensitive?","Type", "Learned?","Flag?")


TERM_NET_SQL="""
select 
r.name, 
r.weight, 
count(r.context_id) as c
from rules r where r.context_id in 
( select r1.context_id from rules r1 where r1.name = ?)
group by r.name, r.weight
"""



NOTIFY_LEVEL_ONE_SQL="""
select 
f.name as feed,
count(e.id) as all_entries,
count(case when e.flag >= 1 then e.id end) as flagged,
f.id
from entries e
join feeds f on f.id = e.feed_id
where e.adddate >= ? and (f.is_category is null or f.is_category = 0) and coalesce(f.deleted,0) <> 1
group by f.name, f.id
having count(e.id) > 0
"""

RESULTS_COLUMNS_SQL="""e.*, f.name || ' (' || f.id || ')' as feed_name_id, f.name as feed_name, datetime(e.pubdate,'unixepoch', 'localtime') as pubdate_r, strftime('%Y.%m.%d', date(e.pubdate,'unixepoch', 'localtime')) as pudbate_short
from entries e 
left join feeds f on f.id = e.feed_id"""



NOTIFY_LEVEL_TWO_SQL=f"""
select 
{RESULTS_COLUMNS_SQL}
where e.adddate >= ? and (f.is_category is null or f.is_category = 0) and coalesce(f.deleted,0) <> 1
"""

NOTIFY_LEVEL_THREE_SQL  =       f"{NOTIFY_LEVEL_TWO_SQL} and flag > 0 "


FEEDS_PRINT_SQL="""select f1.*, coalesce(f2.name, '<<UNKNOWN>>>') as feedex_category
from feeds f1
left join feeds f2 on f1.parent_id = f2.id
where f1.is_category in (0, NULL)"""

CATEGORIES_PRINT_SQL = """select id, name, subtitle, deleted from feeds where is_category = 1"""



EMPTY_TRASH_RULES_SQL = """delete from rules where context_id in
( select e.id from entries e where e.deleted = 1 or e.feed_id in 
( select f.id from feeds f where f.deleted = 1)  )"""

EMPTY_TRASH_ENTRIES_SQL = """delete from entries where deleted = 1 or feed_id in ( select f.id from feeds f where f.deleted = 1)"""

EMPTY_TRASH_FEEDS_SQL1 = """update feeds set parent_id = NULL where parent_id in ( select f1.id from feeds f1 where f1.deleted = 1)"""
EMPTY_TRASH_FEEDS_SQL2 = """delete from feeds where deleted = 1"""


ENTRIES_SQL_TABLE =      ('id','feed_id','charset','lang','title','author','author_contact','contributors','publisher','publisher_contact',
                                'link','pubdate','pubdate_str','guid','desc','category','tags','comments','text','source','adddate','adddate_str','links','read',
                                'importance','tokens','sent_count','word_count','char_count','polysyl_count','com_word_count','numerals_count','caps_count','readability',
                                'weight','flag','images','enclosures','tokens_raw','deleted')

ENTRIES_SQL_TABLE_PRINT = ("ID", "Source / Category", "Character encoding", "Language", "Title", "Author", "Author - contact", "Contributors", "Publisher", "Publisher - contact",
                                  "Link","Date published (Epoch)" ,"Date published (saved)", "GUID", "Description", "Category", "Tags", "Comments link", "Text", "Source link", "Date added (Epoch)",
                                  "Date added", "Internal links", "Read", "Importance", "Token string (for indexing)", "Sentence count", "Word count", "Character count", "Polysylable count", "Common words count",
                                  "Numerals count", "Capitalized words count", "Readability", "Weight", "Flag", "Images", "Enclosures","Raw Token string (for term context)", "Deleted?")




RESULTS_SQL_TABLE                = ENTRIES_SQL_TABLE + ("feed_name_id", "feed_name", "pubdate_r", "pubdate_short", "snippets", "rank", "count")
RESULTS_SQL_TABLE_PRINT          = ENTRIES_SQL_TABLE_PRINT + ("Source (ID)", "Source", "Published - Timestamp", "Date", "Snippets", "Rank", "Count")
RESULTS_SHORT_PRINT1             = ("ID", "Source (ID)", "Date", "Title", "Description", "Text", "Author", "Link","Published - Timestamp", "Read", "Flag", "Importance", "Word count", "Weight", "Snippets", "Rank", "Count")
RESULTS_SHORT_PRINT2             = ("ID", "Source (ID)", "Date", "Title", "Description", "Text", "Author", "Link","Published - Timestamp", "Read", "Flag", "Importance", "Word count", "Weight")

NOTES_PRINT                      = ("ID", "Date", "Title", "Description", "Importance", "Weight", "Deleted?", "Published - Timestamp", "Source (ID)")
RESULTS_TOKENIZE_TABLE           = ("title","desc","text")




FEEDS_SQL_TABLE       =  ('id','charset','lang','generator','url','login','domain','passwd','auth','author','author_contact','publisher','publisher_contact',
                                'contributors','copyright','link','title','subtitle','category','tags','name','lastread','lastchecked','interval','error',
                                'autoupdate','http_status','etag','modified','version','is_category','parent_id', 'handler','deleted')

FEEDS_SQL_TABLE_PRINT = ("ID", "Character encoding", "Language", "Feed generator", "URL", "Login", "Domain", "Password", "Authentication method", "Author", "Author - contact",
                                "Publisher", "Publisher - contact", "Contributors", "Copyright", "Home link", "Title", "Subtitle", "Category", "Tags", "Name", "Last read date (Epoch)",
                                "Last check date (Epoch)", "Update interval", "Errors", "Autoupdate?", "Last connection HTTP status","ETag", "Modified tag", "Protocol version", "Is category?", 
                                "Category ID", "Handler", "Deleted?")


FEEDS_SHORT_PRINT      = ("ID", "Name", "Title", "Subtitle", "Category", "Tags", "Publisher", "Author", "Home link", "URL", "Feedex Category", "Deleted?")
CATEGORIES_SQL_TABLE   = ("id", "name", "subtitle","deleted")
CATEGORIES_PRINT       = ("ID", "Name", "Subtitle","Deleted?")



RULES_SQL_TABLE =        ('id','name','type','feed_id','field_id','string','case_insensitive','lang','weight','additive','learned','context_id','flag')
RULES_SQL_TABLE_PRINT =  ('ID','Name','Type','Feed ID', 'Field ID', 'Search string', 'Case insensitive?', 'Language', 'Weight', 'Additive?', 'Learned?', 'Entry ID', 'Flag?')


LING_LIST1 = ('feed_id','lang','author','publisher','contributors','title','desc','tags','category','text')
LING_LIST2 = ('feed_id','lang','author','publisher','contributors','title','desc','tags','category','text','tokens','tokens_raw')


LING_TECH_LIST = ('tokens','tokens_raw','sent_count','word_count','char_count','polysyl_count','com_word_count','numerals_count','caps_count','readability' )

RECALCULATE_FILTER = ('lang','sent_count','word_count','char_count','polysyl_count','com_word_count','numerals_count','caps_count','readability','importance','flag','weight','tokens','tokens_raw') #,'title','desc','text','category')



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

#Prefix, sql field name, Field name, 
PREFIXES={
0 : ('MF','f.id','Feed ID', False, True, 1, None, True),
1 : ('ML','e.lang','Language', False, True, 0.1, None, True),
2 : ('MA', 'e.author','Author', False, True, 1, 'www, mail, email, mailto', True),
3 : ('MP', 'e.publisher', 'Publisher', False, True, 1, 'www, mail, email, mailto, http', True),
4 : ('MC', 'e.contributors', 'Contributors', False, True, 1, 'www, mail, email, mailto, http', True),

5 : ('TT', 'e.title', 'Title', True, False, 2, None, False),
6 : ('TD', 'e.desc', 'Description', True, False, 1, None, False),
7 : ('MT', 'e.tags', 'Tags', True, True, 1, None, True),
8 : ('TC', 'e.category', 'Category', True, True, 3, None, True),
9 : ('TX', 'e.text', 'Text', True, False, 1, None, False)
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



TERM_NORMAL             = TCOLS['DEFAULT']
TERM_BOLD               = TCOLS['WHITE_BOLD']
TERM_ERR              = TCOLS['LIGHT_RED']
TERM_ERR_BOLD         = TCOLS['LIGHT_RED_BOLD']

TERM_FLAG               = TCOLS['YELLOW_BOLD']
TERM_READ               = TCOLS['WHITE_BOLD']
TERM_DELETED            = TCOLS['RED']
TERM_SNIPPET_HIGHLIGHT  = TCOLS['CYAN_BOLD']

BOLD_MARKUP_BEG = '<b>'
BOLD_MARKUP_END = '</b>'


DEFAULT_CONFIG = {
            'log' : f'{FEEDEX_SHARED_PATH}{DIR_SEP}feedex.log',
            'db_path' : f'{FEEDEX_SHARED_PATH}{DIR_SEP}feedex.db',
            'browser' : f'{APP_PATH}{DIR_SEP}firefox --new-tab %u',
            'timeout' : 15,
            'notify' : False,
            'notify_level': 10,
            'default_interval': 45,
            'error_threshold': 5,
            'max_items_per_transaction': 300,
            'ignore_images' : False,
            'rule_limit' : 5000,
            'use_keyword_learning' : True,
            'use_search_habits' : True,
            'learn_from_added_entries': True,
            'default_entry_weight' : 2,
            'default_rule_weight' : 2,
            'query_rule_weight' : 10,
            'default_similarity_limit' : 20,
            'do_redirects' : True,
            'ignore_modified': True,
            
            'gui_desktop_notify' : True, 
            'gui_fetch_periodically' : False,
            'gui_flag_1_color': 'blue',
            'gui_flag_1_name': 'Flag 1',
            'gui_flag_2_color': 'blue',
            'gui_flag_2_name': 'Flag 2',
            'gui_flag_3_color': 'blue',
            'gui_flag_3_name': 'Flag 3',
            'gui_flag_4_color': 'blue',
            'gui_flag_4_name': 'Flag 4',
            'gui_flag_5_color': 'blue',
            'gui_flag_5_name': 'Flag 5',

            'gui_new_color' : '#0FDACA',
            'gui_deleted_color': 'grey',
            'gui_hilight_color' : 'blue',

            'imave_viewer': '',
            'gui_clear_cache' : 30,
            'gui_key_search': 's',
            'gui_key_new_entry': 'n',
            'gui_key_new_rule': 'r',

            'normal_color' : TCOLS['DEFAULT'],
            'flag_color': TCOLS['YELLOW_BOLD'],
            'read_color': TCOLS['WHITE_BOLD'],
            'bold_color': TCOLS['WHITE_BOLD'],
            'bold_markup_beg': BOLD_MARKUP_BEG,
            'bold_markup_end': BOLD_MARKUP_END


}

CONFIG_INTS_NZ=('timeout','notify_level','default_interval','error_threshold','max_items_per_transaction', 'default_similarity_limit')
CONFIG_INTS_Z=('rule_limit','gui_clear_cache')

CONFIG_FLOATS=('default_entry_weight', 'default_rule_weight', 'query_rule_weight' )

CONFIG_STRINGS=('log','db_path','browser','gui_flag_1_color','gui_flag_2_color','gui_flag_3_color','gui_flag_4_color','gui_flag_5_color',\
    'gui_new_color','gui_deleted_color', 'gui_hilight_color', 'imave_viewer','bold_markup_beg','bold_markup_end')
CONFIG_KEYS=('gui_key_search','gui_key_new_entry', 'gui_key_new_rule')

CONFIG_BOOLS=('notify','ignore_images', 'use_keyword_learning', 'learn_from_added_entries','do_redirects','ignore_modified','gui_desktop_notify','gui_fetch_periodically', 'use_search_habits')

CONFIG_COLS=('normal_color','flag_color','read_color','bold_color')











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
)



# Our modules
from feedex_utils import *
from feedex_docs import *
from feeder_containers import *
from feedex_ling_processor import *
from feedex_cli import *
from feedex_rss_handler import *
from feedex_twitter_handler import *
from feeder_query_parser import FeederQueryParser
from feeder import Feeder

