# -*- coding: utf-8 -*-
""" RSS handler for Feedex """

from feedex_headers import *



# Handlers need to have a cetain structure and retrievable data





class FeedexRSSHandler:  
    """RSS handler for Feedex"""

    compare_links = True
    no_updates = False

    def __init__(self, FX, **kargs):
    
        self.FX = FX
        self.config = self.FX.config

        self.debug = kargs.get('debug', self.FX.config.get('debug'))
        
        # Containers for entry and field processing
        self.entry = EntryContainer(self.FX) 
        self.feed = FeedContainerBasic()
        self.entries = []

        self.feed_raw = {}

        self.error = False
        self.changed = True
        self.redirected = False

        self.status = None
        self.modified = None
        self.etag = None
        self.agent = self.config.get('user_agent', FEEDEX_USER_AGENT)

        self.images = []





    def download(self, url:str, **kargs):
        """This one handles getting feeds from the web and authorization if specified. Error handling. Authorization does not work at the moment."""
        etag = kargs.get('etag')
        modified = kargs.get('modified')
        login = kargs.get('login')
        password = kargs.get('password')
        domain = kargs.get('domain')
        aauth = kargs.get('auth')
        
        do_redirects = kargs.get('do_redirects', self.config.get('do_redirects',True))


        self.feed_raw = {}

        # This parameter forces download without providing etags or modified date
        force = kargs.get('force',False)
        if force:
            etag = None
            modified = None

        # Set up authentication handler if required
        if aauth is not None:
            if self.debug in (1,3): print('Setting up authentication...')
            auth = urllib.request.HTTPDigestAuthHandler()
            if aauth in ('digest', 'detect'):
                auth.add_password('DigestTest', domain, login, password)
            elif aauth == 'basic':
                auth.add_password('BasicTest', domain, login, password)
            else:
                self.error = True
                return f'Unrecognized authentication handler (%a). Must be "digest" or "basic"', aauth
        else:
            auth = None

        # Argument dictionary for Feedparser        
        fkargs_tmp = {
            'etag' : etag,
            'modified' : modified,
            'agent' : self.agent, # Some publishers have problem with that :(
            'handlers' : [auth]
        }
        fkargs = {}
        for k, v in fkargs_tmp.items():
            if v not in (None, [], '',[None]):
                fkargs[k] = v
    

        # Download and parse...
        try:
            feed_raw = feedparser.parse(url, **fkargs)
        except Exception as e:
            cli_msg( (-1,f'{e}') )
            self.error = True
            return f'{e}'

        # HTTP Status handling...       
        self.status = feed_raw.get('status')
        self.changed = True

        if self.status is None: return 'Could not read HTTP status'
        if self.status == 304:
            self.changed = False
            return 0

        elif self.status in (301, 302):
            if not do_redirects: return f'Feed {url} moved to new location!'
            else:
                new_url = feed_raw.get('href',None)
                if new_url not in (None,''):
                    # Watch out for endless redirect loops!!!
                    self.redirected = True
                    msg = self.download(new_url, etag=etag, modifed=modified, login=login, password=password, auth=aauth, domain=domain, do_redirects=False, force=force, redirected=True)
                    return msg
                else:
                    return 'URL to resource empty!'

        elif self.status == 410:
            if self.debug in (1,3): print(f"""410 {scast(feed_raw.get('debug_message'), str, ' Permanently deleted')}""")
            self.error = True
            return f'Feed {url} removed permanently!'


        elif self.status not in (200, 201, 202, 203, 204, 205, 206):
            if self.debug in (1,3): print(f"""{scast(self.status, str, '')} {scast(feed_raw.get('debug_message'), str, ' Feed error')}""")
            self.error = True
            return f'Invalid HTTP return code for {url} ({self.status})'
                
        #Everything may go seemingly well, but the feed will be empty and then there is no point in processing it
        if feed_raw.get('feed',{}).get('title') is None:
            if self.debug in (1,3): print(feed_raw)
            self.error = True
            return f'Feed {url} unreadable!'

        self.feed_raw = feed_raw
        self.etag = feed_raw.get('etag',None)
        self.modified = feed_raw.get('modified',None)    
        return 0




    
    def fetch(self, feed, **kargs):
        """ Consolidate and return downloaded RSS """
        force = kargs.get('force',False)
        pguids = list(kargs.get('pguids',()))
        plinks = list(kargs.get('plinks',()))
        last_read = kargs.get('last_read',0)

        self.error = False
        self.status = None
        self.modified = None
        self.etag = None
        self.redirected = False

        self.entries = []
        
        msg = self.download(feed['url'], modified=feed['modified'], etag=feed['etag'], force=force, auth=feed['auth'], password=feed['passwd'], login=feed['login'], domain=feed['domain'])
        if msg != 0: yield -3, msg

        if self.error: return -1
        if self.feed_raw == {}: return -1
        if not self.changed:
            yield 0, 'Feed unchanged (304)'
            return 0

        pub_date_raw = self.feed_raw['feed'].get('updated')
        pub_date = scast(convert_timestamp(pub_date_raw), int, 0)

        if pub_date <= last_read and pub_date_raw is not None:
            yield 0, 'Feed unchanged (Published Date)'
            return 0

        # Main loop
        for entry in self.feed_raw.get('entries',()):

            now = datetime.now()
            now_raw = int(now.timestamp())
            
            pub_date_entry = convert_timestamp(entry.updated)

            # Go on if nothing changed		
            if pub_date_entry <= last_read:
                continue
            # Check for duplicates in saved entries by complaring to previously compiled lists
            if (entry.get('guid'),) in pguids and entry.get('guid','') != '':
                continue
            if (entry.get('link'),) in plinks and entry.get('link','') != '':
                continue

            self.entry.clear()

            # Assign fields one by one (I find it more convenient...)
            self.entry['feed_id']                 = feed['id']
            self.entry['title']                   = slist(strip_markup(entry.get('title'), html=True), 0, None)
            self.entry['author']                  = entry.get('author')
            self.entry['author_contact']          = nullif( entry.get('author_detail',{}).get('email','') + "; " + entry.get('author_detail',{}).get('href',''), '; ')
            self.entry['contributors']            = entry.get('contributors')
            self.entry['publisher']               = entry.get('publisher')
            self.entry['publisher_contact']       = nullif( entry.get('publisher_detail',{}).get('email','') + "; " + entry.get('publisher_detail',{}).get('href',''), '; ')
            self.entry['category']                = entry.get('category')
            self.entry['lang']                    = entry.get('lang',entry.get('language',self.feed_raw.get('feed',{}).get('language')))
            self.entry['charset']                 = self.feed_raw.get('encoding')
            self.entry['comments']                = entry.get('comments')
            self.entry['guid']                    = entry.get('guid')
            self.entry['pubdate']                 = pub_date_entry
            self.entry['pubdate_str']             = entry.updated
            self.entry['source']                  = entry.get('source',{}).get('href')        
            self.entry['link']                    = entry.get('link')
            self.entry['adddate']                 = now_raw
            self.entry['adddate_str']             = now

            #Description
            images = ''
            val = strip_markup(entry.get('description'))
            self.entry['desc'] = slist(val , 0, None)
            for i in slist(val, 1, []):
                if i is not None and i != '':
                    images += i + "\n"

            #Text from contents
            text=''
            content = entry.get('content')
            if content is not None:
                for c in content:
                    val = strip_markup(c.get('value'), html=True)
                    if val not in (None, (), (None),[], [None]):
                        text += '\n\n' + slist(val, 0, '').replace(self.entry['desc'],'')
                        for i in slist(val, 1, []):
                            if i is not None and i != '':
                                images += i + "\n"        
            self.entry['text'] = nullif(text,'')
            self.entry['images'] = nullif(images,'')

            # Add enclosures
            enclosures = ''
            enc = entry.get('enclosures',[])
            for e in enc:
                enclosures += e.get('href','') + "\n"
            self.entry['enclosures'] = nullif(enclosures,'')

            # Tag line needs to be combined
            tags = ''
            for t in entry.get('tags', []):
                tags = tags + ' ' + scast(t.get('label',t.get('term','')), str, '')

            # Compile string with present links
            self.entry['tags'] = nullif(tags,('',' '))
            link_string = ''
            for l in entry.links:
                link_string = link_string + l.get('href','') + "\n"
            self.entry['links'] = nullif(link_string,'')

            pguids.append(self.entry['guid'])
            plinks.append(self.entry['link'])
            yield self.entry




    def _get_images(self):
        """Download feed images/icons/logos to icon folder to use in notifications"""
        headers = {'User-Agent' : self.agent} # Many publishers scoff at custom user agents - FeedParser's one seems to be working fine
        for i in self.images:
            href = scast( slist(i, 2, None), str, '')
            feed_id = scast( slist(i, 0, 0), str, '0')

            if href != '' and feed_id != 0:
                if self.debug in (1,3): print(f'Downloading image for feed {feed_id} from {href}...')
                imfile = f'{FEEDEX_ICON_PATH}{DIR_SEP}feed_{feed_id}_{self.FX.db_hash}.ico'
                try:
                    req = urllib.request.Request(href, None, headers)
                    response = urllib.request.urlopen(req)
                    if response.status in (200, 201, 202, 203, 204, 205, 206):
                        with open(imfile, 'wb') as f:
                            f.write(response.read())
                    else: 
                        return f'Could not save image from {href}! HTTP return status: {response.status}'    

                except (urllib.error.URLError, ValueError, TypeError, OSError) as e:
                    return f'Could not save image from {href}! Error: {e}'
            else:
                continue

        self.images = []
        return 0






    def update(self, feed, **kargs):
        """ Consolidate feed data from RSS resource """

        if kargs.get('feed_raw') is not None:
            self.feed_raw = kargs.get('feed_raw')

        if self.feed_raw.get('feed',None) is None: return f'Downloaded feed empty ({feed.name()})!'

        self.feed.clear()
        # Get image urls for later download
        if not kargs.get('ignore_images', False):
            icon = self.feed_raw.feed.get('icon',None)
            if icon is not None:
                self.images.append([feed['id'], None, icon, None])
            else:
                logo = self.feed_raw.feed.get('logo',None)
                if logo is not None:
                    self.images.append([feed['id'], None, logo, None])
                else:
                    image = self.feed_raw.feed.get('image',None)
                    if image is not None:
                        self.images.append([feed['id'], None, image.get('href',None), image.get('title',None)])

        # Overwrite Nones in current data and populate feed
        self.feed['id']                       = feed['id']
        self.feed['link']                     = self.feed_raw.feed.get('link', None)
        self.feed['charset']                  = coalesce(feed['charset'], self.feed_raw.get('encoding',None))
        self.feed['lang']                     = coalesce(feed['lang'], self.feed_raw.feed.get('lang',self.feed_raw.feed.get('feed',{}).get('language',None)))
        self.feed['generator']                = coalesce(feed['generator'], self.feed_raw.feed.get('generator', None))
        self.feed['author']                   = coalesce(feed['author'], self.feed_raw.feed.get('author', None))
        self.feed['author_contact']           = nullif( coalesce(feed['author_contact'], self.feed_raw.feed.get('author_detail',{}).get('email','') + "; " + self.feed_raw.feed.get('author_detail',{}).get('href','')), '; ')
        self.feed['publisher']                = coalesce(feed['publisher'], self.feed_raw.feed.get('publisher', None))
        self.feed['publisher_contact']        = nullif( coalesce(self.feed['publisher_contact'], self.feed_raw.feed.get('publisher_detail',{}).get('email','') + "; " + self.feed_raw.feed.get('publisher_detail',{}).get('href','')), '; ')
        self.feed['contributors']             = coalesce(feed['contributors'], self.feed_raw.feed.get('contributors', None))
        self.feed['copyright']                = coalesce(feed['copyright'], self.feed_raw.feed.get('copyright', None))
        self.feed['title']                    = coalesce(feed['title'], self.feed_raw.feed.get('title', None))
        self.feed['subtitle']                 = coalesce(feed['subtitle'], self.feed_raw.feed.get('subtitle', None))
        self.feed['category']                 = coalesce(feed['category'], self.feed_raw.feed.get('category', None))
        #self.feed['etag']                     = self.feed_raw.feed.get('etag',None)

        tags = ''
        for t in self.feed_raw.feed.get('tags', []):
            tags = tags + ' ' + scast(t.get('label',t.get('term','')), str, '')
        self.feed['tags']                     = coalesce(feed['tags'], tags)
        self.feed['name']                     = coalesce(feed['name'], self.feed_raw.feed.get('title', None))
        #self.feed['modified']                 = self.feed_raw.get('modified',None)
        self.feed['version']                  = self.feed_raw.get('version',None)

        if not kargs.get('ignore_images', False):
            msg = self._get_images()
            if msg != 0: return msg
        return 0





    def set_agent(self, agent):
        """ Set custom user agent """
        if agent is None: self.agent = self.config.get('user_agent', FEEDEX_USER_AGENT)
        else: self.agent = coalesce( nullif(scast(agent, str, '').strip(), ''), self.config.get('user_agent', FEEDEX_USER_AGENT) )