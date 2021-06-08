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
FEEDEX_RELEASE="2020"
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


FEEDEX_CONFIG = os.environ['HOME'] + '/.config/feedex.conf'
FEEDEX_SYS_CONFIG = '/etc/feedex.conf'

FEEDEX_SYS_SHARED_PATH = '/usr/share/feedex'
FEEDEX_SHARED_PATH = os.environ['HOME'] + '/.local/share/feedex'

# GUI
FEEDEX_GUI_DEFAULT_FILTERS = {'rev': True, 'print': False, 'case_ins': True, 'field': -1, 'last_week': True, 'lang': 'heuristic', 'ntype': 2, 'exact': False, 'group': 'daily'}
FEEDEX_SYS_ICON_PATH = f"{FEEDEX_SYS_SHARED_PATH}/data/pixmaps"
FEEDEX_ICON_PATH = os.environ['HOME'] + '/.local/share/feedex/icons'
FEEDEX_CACHE_PATH = os.environ['HOME'] + '/.local/share/feedex/cache'
FEEDEX_MODELS_PATH = f'{FEEDEX_SYS_SHARED_PATH}/data/models'

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
order by c * r.weight
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
0 : ['MF','f.id','Feed ID', False, True, 1, None, True],
1 : ['ML','e.lang','Language', False, True, 0.1, None, True],
2 : ['MA', 'e.author','Author', False, True, 1, 'www, mail, email, mailto', True],
3 : ['MP', 'e.publisher', 'Publisher', False, True, 1, 'www, mail, email, mailto, http', True],
4 : ['MC', 'e.contributors', 'Contributors', False, True, 1, 'www, mail, email, mailto, http', True],

5 : ['TT', 'e.title', 'Title', True, False, 2, None, False],
6 : ['TD', 'e.desc', 'Description', True, False, 1, None, False],
7 : ['MT', 'e.tags', 'Tags', True, True, 1, None, True],
8 : ['TC', 'e.category', 'Category', True, True, 3, None, True],
9 : ['TX', 'e.text', 'Text', True, False, 1, None, False]
}


# Terminal display
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
            'log' : f'{FEEDEX_SHARED_PATH}/feedex.log',
            'db_path' : f'{FEEDEX_SHARED_PATH}/feedex.db',
            'browser' : '/usr/bin/firefox --new-tab %u',
            'timeout' : 10,
            'notify' : 0,
            'ignore_images' : False
    }


# Standard error codes and other messages (message (%a replaces argument), log?, error?)
MESSAGES = {
# Errors
-2 : ('Database is locked for modification!', False, True),
-3 : ('Feed or Category %a not found!', False, True),
-4 : ('Not a valid URL or IP!', False, True),
-5 : ('Category %a not found!', False, True),
-6 : ('Nesting categories not allowed', False, True),
-7 : ('Could not download image from %a', False, True),
-8 : ('No valid Feed or Category given (%a)!', False, True),
-9 : ('Not a valid REGEX string (%a)!', False, True),
-10 : ('File %a already exists!', False, True),
-11 : ('Feedparser download error!', True, True),
-12 : ('Feed %a prermanently moved to new location!', True, True),
-13 : ('Failed redirect (%a)!', True, True),
-14 : ('Failed redirect (%a) - invalid HTTP status!', True, True),
-15 : ('Feed removed permanently (%a)!', True, True),
-16 : ('Invalid HTTP return code (%a)!', True, True),
-17 : ('Feed unreadable (%a)!', True, True),
-18 : ('Processing aborted', False, True),
-19 : ('Feed %a not found', False, True),
-20 : ('Error updating metadata for feed %a', True, True),
-21 : ('Handler %a not recognized!', True, True),
-22 : ('There exists a Feed with this URL (%a)', False, True),
-23 : ('Could not find last feed id with given URL! (%a)', False, True),
-24 : ('Entry %a not found!', False, True),
-25 : ('Invalid input method/file given!', False, True),
-26 : ('Rule\'s weight must be a number!', False, True),
-27 : ('Rule ID must be provided for in-place edit!', False, True),
-28 : ('Downloaded feed %a was empty!', True, True),
-29 : ('Not a valid field (%a)!', False, True),
-30 : ('Invalid rule type - should be 0,1,2 or 3', False, True),
-31 : ('Infalid field ID (%a)', False, True),
-32 : ('DB error: %a', False, True),
-33 : ('Error recalculating linguistics for entry %a', False, True),
-34 : ('Error saving configuration to %a!', False, True),
-35 : ('Error importing feeds from %a. Operation aborted', False, True),
-36 : ('Error importing rules from %a. Operation aborted', False, True),
-37 : ('File %a already exists!', False, True),
-38 : ('File %a not found!', False, True),
-39 : ('Could not connect to or create %a database! Aborting', True, True),
-40 : ('Application version too old for %a Database! Aborting', True, True),
-41 : ('Error creating backup for %a Database!', True, True),
-42 : ('Error executing %a script! Restoring databse!', True, True),
-43 : ('Error restoring Database!', True, True),
-44 : ('Cannot change value of field %a - restricted for technical usage', False, True),
-45 : ('Error while linguistic processing %a!', False, True),
-46 : ('Learned rules cannot be edited!', False, True),
-47 : ('Rule %a not found!', False, True),
-48 : ('Not a valid field (%a)!', False, True),


# Messages
2  : ('Category %a added', True, False),
3  : ('Feed %a added', True, False),
4  : ('Category %a modified', True, False),
5  : ('Feed %a modified', True, False),
6  : ('Feed %a deleted', True, False),
7  : ('Nothing done.', False, False),
8  : ('Value changed (%a)', True, False),
9  : ('Entry value changed (%a)', True, False),
10 : ('Entry %a deleted', True, False),
11 : ('Entry: nothing done', False, False),
12 : ('Rules for entry %a deleted', False, False),
13 : ('Rules: nothing done', False, False),
14 : ('Opening in browser (%a)', False, False),
15 : ('Learning keywords', False, False),
16 : ('Done.', False, False),
17 : ('Entry added (%a)', True, False),
18 : ('Rule saved (%a)', True, False),
19 : ('Rule %a deleted', True, False),
20 : ('Results saved to %a', True, False),
21 : ('Processing %a ...', False, False),
22 : ('Finished fetching (%a new articles)', False, False),
23 : ('Updating data for feed %a', False, False),
24 : ('Metadata updated for feed %a', False, False),
25 : ('Updating images for feed %a', False, False),
26 : ('Feed redirected (%a)', True, False),
27 : ('Feed %a ignored due to previous errors', False, True),
28 : ('Finished updating metadata', False, False),
29 : ('Feed added (%a)', True, False),
30 : ('Category %a deleted', True, False),
31 : ('Feed %a deleted permanently', True, False),
32 : ('Category %a deleted permanently', True, False),
33 : ('Entry %a deleted permanently with rules', True, False),
34 : ('Entry %a ready to add...', False, False),
35 : ('Changes saved', False, False),
36 : ('%a restored', False, False),
37 : ('%a marked as healthy', False, False),
38 : ('Feed assigned to %a category', False, False),
39 : ('Feed %a detached from any category', False, False),
40 : ('Entry %a restored', False, False),
41 : ('Entry %a marked as unread', False, False),
42 : ('Entry %a marked as read', False, False),
43 : ('Entry %a flagged', False, False),
44 : ('Entry %a unflagged', False, False),
45 : ('Feed %a updated successfully', False, False),
46 : ('Entry updated successfully', False, False),
47 : ('Rule updated successfully', False, False),
48 : ('Rule value changed (%a)', False, False),
49 : ('Entry recalculated', False, False),
50 : ('Configuration saved successfully!', False, False),
51 : ('Removing deleted items...', False, False),
52 : ('Trash emptied (permanently removed: %a)', False, False),
53 : ('Search History cleared (removed %a items)', False, False),
54 : ('Deleted %a rules learned from searches', False, False),
55 : ('Feeds imported successfully from %a', True, False),
56 : ('Rules imported successfully from %a', True, False),
57 : ('SQLite Database not found. Creating new one...', True, False),
58 : ('Folder %a created...', True, False),
59 : ('Database metadata created...', False, False),
60 : ('Defaults added to fresh Database...', False, False),
61 : ('Database %a version too old... Updating...', False, False),
62 : ('Backup created (%a)...', False, False),
63 : ('Running update scripts... %a', False, False),
64 : ('Database restored', True, False),
65 : ('Database updated successfully', True, False),
66 : ('Generating keywords for entry %a', False, False),
67 : ('Removing all learned keywords', False, False),
68 : ('%a learned rules deleted', True, False),

69 : ('Performing maintenance on database... This may take some time...', True, False),
70 : ('Performing VACUUM', True, False),
71 : ('Performing ANALYZE', True, False),
72 : ('REINDEXING all tables', True, False),
73 : ('Maintenance complete', True, False)
}






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

