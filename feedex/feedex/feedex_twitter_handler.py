# -*- coding: utf-8 -*-
""" Basic Twitter handler for Feedex - currently not supported, on TODO list :)
    Need to register application with Twitter to get access to API"""

from feedex_headers import *



# Handlers need to have a cetain structure and retrievable data





class FeedexTwitterHandler:
    """Twitter handler for Feedex"""

    compare_links = False
    no_updates = True

    def __init__(self, config, **kargs):
    
        self.config = config

        self.debug = kargs.get('debug',False)
        self.gui = kargs.get('gui',False)
        
        self.entry = SQLContainer('entries', ENTRIES_SQL_TABLE) # Containers for entry and field processing
        self.feed = SQLContainer('feeds', FEEDS_SQL_TABLE + ('category_name',))
        self.entries = []

        self.feed_raw = {}

        self.error = False
        self.changed = True
        self.redirected = False

        self.status = None
        self.modified = None
        self.etag = None

        self.images = []



    def get_tweets(*katgs): 
        """ Placeholder """
        yield 0
        return 0

    def fetch(self, feed, **kargs):
        """ Consolidate and return downloaded RSS """
        pguids = list(kargs.get('pguids',()))
        last_read = kargs.get('last_read',0)
        last_checked = kargs.get('last_checked',0)

        self.error = False
        self.changed = True
        self.status = None
        self.modified = None
        self.etag = None
        self.redirected = False

        self.entries = []


        for tweet in get_tweets(feed['url'], pages=1):
            
            self.entry.clear()
            if tweet.get('tweetid') in pguigs: continue

            now = datetime.now()
            now_raw = int(now.timestamp())
                                    
            self.entry['feed_id'] = feed['id']
            self.entry['guid'] = tweet.get('twetid')
            self.entry['author'] = tweet.get('username')
            self.entry['author_contact'] = tweet.get('userid')
            self.entry['pubdate_str'] = tweet.get('time')
            self.entry['pubdate'] = convert_timestamp(tweet.get('time')) 
            self.entry['adddate'] = now_raw
            self.entry['adddate_str'] = now
            self.entry['link'] = tweet.get('tweetURL')
            
            title = tweet.get('text')
            if len(title) > 100:
                title = f'{title[:100]} ...'
                desc = title
            else: 
                desc = None
            self.entry['title'] = title
            self.entry['desc'] = desc
            tags = ''
            enclosures = ''
            images = ''

            pguids.append(self.entry['guid'])            

            yield self.entry

            




    def update(self, feed, **kargs):
        """ Consolidate feed data Twitter handler """
        yield 0        
        return 0, None




