# -*- coding: utf-8 -*-
""" RSS handler for Feedex """

from cgitb import html
from os import link
from urllib.error import HTTPError

from numpy import size
from feedex_headers import *



# Handlers need to have a cetain structure and retrievable data





class FeedexRSSHandler:  
    """RSS handler for Feedex"""

    compare_links = True
    no_updates = False
    all_is_html = False

    def __init__(self, FX, **kargs):
    
        self.FX = FX
        self.config = self.FX.config

        self.debug = kargs.get('debug', self.FX.config.get('debug'))
        
        # Containers for entry and field processing
        self.entry = EntryContainer(self.FX) 
        self.feed = FeedContainerBasic()
        self.ifeed = FeedContainerBasic()
        self.entries = []

        self.http_headers = {}

        self.feed_raw = {}

        self.error = False
        self.error_str = ''
        self.changed = True
        self.redirected = False

        self.status = None
        self.modified = None
        self.etag = None
        self.agent = self.config.get('user_agent', FEEDEX_USER_AGENT)

        self.images = []







    def set_feed(self, feed):
        """ Setup feed and headers """
        if isinstance(feed,FeedContainerBasic):
            self.ifeed.populate(feed.tuplify())
        elif isinstance(feed, dict):
            self.ifeed = feed.copy()
        else: raise FeedexTypeError(_('Invalid type of input feed! Should be a FeedContainer or dict!'))

        headers = {}
        headers['etag'] = self.ifeed.get('etag')
        headers['modified'] = self.ifeed.get('modified')
        headers['login'] = self.ifeed.get('login')
        headers['password'] = self.ifeed.get('password')
        headers['domain'] = self.ifeed.get('domain')
        headers['agent'] = self.agent

        # Set up authentication handler
        if self.ifeed.get('auth') is not None and self.ifeed.get('login') is not None and self.ifeed.get('password') is not None:
            if self.debug in (1,3): print('Setting up authentication...')
            auth = urllib.request.HTTPDigestAuthHandler()
            if self.ifeed.get('auth') in ('digest', 'detect'):
                auth.add_password('DigestTest', self.ifeed.get('domain'), self.ifeed.get('login'), self.ifeed.get('password'))
            elif self.ifeed['auth'] == 'basic':
                auth.add_password('BasicTest', self.ifeed.get('domain'), self.ifeed.get('login'), self.ifeed.get('password'))
            else:
                self.error = True
                return _('Unrecognized authentication handler (%a). Must be "digest" or "basic"'), self.ifeed.get('auth')
            headers['handlers'] = [auth]

        # Consolifate headers' dict
        self.http_headers = {}
        for k, v in headers.items():
            if v not in (None, [], '',[None]): self.http_headers[k] = v






    def _do_download(self, url:str, **kargs):
        """ Method for downloading specifically - to be overwritten for child classes/ different HTTP-based protocols"""
        try:
            return feedparser.parse(url, **self.http_headers)
        except Exception as e:
            self.error = True
            self.error_str = f'{e}'
            return {}



    def download(self, **kargs):
        """This one handles getting feeds from the web and authorization if specified. Error handling. Authorization does not work at the moment."""

        self.error = False
        
        url = kargs.get('url', self.ifeed['url'])
        do_redirects = kargs.get('do_redirects', self.config.get('do_redirects',True))
        self.feed_raw = {}

        # This parameter forces download without providing etags or modified date
        force = kargs.get('force',False)
        if force:
            if 'etag' in self.http_headers.keys(): del self.http_headers['etag']
            if 'modified' in self.http_headers.keys(): del self.http_headers['modified']

        # Download and parse...
        try:
            feed_raw = self._do_download(url)
        except Exception as e:
            self.error_str = f'{e}'
            self.error = True
            return f'{e}'

        if self.error: return self.error_str

        # HTTP Status handling...       
        self.status = feed_raw.get('status')
        self.changed = True

        if self.status is None: return _('Could not read HTTP status')
        if self.status == 304:
            self.changed = False
            return 0

        elif self.status in (301, 302) and not self.redirected:
            if not do_redirects: return f'{_("Feed")} {url} {_("moved to new location!")}'
            else:
                new_url = feed_raw.get('href',None)
                if new_url not in (None,''):
                    # Watch out for endless redirect loops!!!
                    self.redirected = True
                    msg = self.download(url=url, do_redirects=False, force=force, redirected=True)
                    return msg
                else:
                    return _('URL to resource empty!')

        elif self.status == 410:
            if self.debug in (1,3): print(f"""410 {scast(feed_raw.get('debug_message'), str, _(' Permanently deleted'))}""")
            self.error = True
            return f'{_("Feed")} {url} {_("removed permanently!")}'


        elif (self.status not in (200, 201, 202, 203, 204, 205, 206)) and not (self.status in (301,302) and self.redirected):
            if self.debug in (1,3): print(f"""{scast(self.status, str, '')} {scast(feed_raw.get('debug_message'), str, _(' Feed error'))}""")
            self.error = True
            return f'{_("Invalid HTTP return code for")} {url} ({self.status})'
                
        #Everything may go seemingly well, but the feed will be empty and then there is no point in processing it
        if feed_raw.get('feed',{}).get('title') is None:
            if self.debug in (1,3): print(feed_raw)
            self.error = True
            return f'{_("Feed")} {url} {_("unreadable!")}'

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
        
        msg = self.download(force=force)
        if msg != 0: yield -3, msg

        if self.error: return -1
        if self.feed_raw == {}: return -1
        if not self.changed:
            yield 0, _('Feed unchanged (304)')
            return 0

        pub_date_raw = self.feed_raw['feed'].get('updated')
        pub_date = scast(convert_timestamp(pub_date_raw), int, 0)

        if pub_date <= last_read and pub_date_raw not in (None,''):
            yield 0, _('Feed unchanged (Published Date)')
            return 0

        if nullif(feed['rx_images'],'') is not None and feed['handler'] != 'html': rx_images = re.compile(scast(feed['rx_images'], str,''), re.DOTALL)
        else: rx_images = None
        if nullif(feed['rx_link'],'') is not None and feed['handler'] != 'html': rx_links = re.compile(scast(feed['rx_link'], str,''), re.DOTALL)
        else: rx_links = None

        # Main loop
        for entry in self.feed_raw.get('entries',()):

            now = datetime.now()
            now_raw = int(now.timestamp())
            
            pub_date_entry_str = entry.get('updated')
            if pub_date_entry_str is None: 
                pub_date_entry_str = now
                pub_date_entry = now_raw
            else:
                pub_date_entry = convert_timestamp(pub_date_entry_str)

            # Go on if nothing change
            if pub_date_entry <= last_read: continue
            # Check for duplicates in saved entries by complaring to previously compiled lists
            if (entry.get('guid'),) in pguids and entry.get('guid') not in ('',None): continue
            if (entry.get('link'),) in plinks and entry.get('link') not in ('',None): continue

            self.entry.clear()

            # Assign fields one by one (I find it more convenient...)
            self.entry['feed_id']                 = feed['id']
            self.entry['title']                   = slist(strip_markup(entry.get('title'), html=True), 0, None)
            
            authors = entry.get('author','')
            if authors == '' and type(entry.get('authors',())) in (list, tuple):
                for a in entry.get('authors',()): 
                   if a.get('name','') != '': authors = f"""{authors}{a.get('name','')}; """

            self.entry['author']                  = nullif(authors,'')
            self.entry['author_contact']          = nullif( f"""{entry.get('author_detail',{}).get('email','')}; {entry.get('author_detail',{}).get('href','')}""", '; ')
            
            contribs = ''
            if type(entry.get('contributors',())) in (list, tuple):
                for c in entry.get('contributors',()): 
                    if c.get('name','') != '': contribs = f"""{contribs}{c.get('name','')}; """

            self.entry['contributors']            = nullif(contribs,'')
            self.entry['publisher']               = entry.get('publisher')
            self.entry['publisher_contact']       = nullif( f"""{entry.get('publisher_detail',{}).get('email','')}; {entry.get('publisher_detail',{}).get('href','')}""", '; ')
            self.entry['category']                = entry.get('category')
            self.entry['lang']                    = entry.get('lang',entry.get('language',self.feed_raw.get('feed',{}).get('language')))
            self.entry['charset']                 = self.feed_raw.get('encoding')
            self.entry['comments']                = entry.get('comments')
            self.entry['guid']                    = entry.get('guid')
            self.entry['pubdate']                 = pub_date_entry
            self.entry['pubdate_str']             = pub_date_entry_str
            self.entry['source']                  = entry.get('source',{}).get('href')        
            self.entry['link']                    = entry.get('link')
            self.entry['adddate']                 = now_raw
            self.entry['adddate_str']             = now

            #Description
            images = ''
            links = ''
            txt, im, ls = strip_markup(entry.get('description'), html=self.all_is_html, rx_images=rx_images, rx_links=rx_links)
            self.entry['desc'] = txt
            for i in im:
                if i is not None and i != '': images = f"""{images}{i}\n"""
            for l in ls:
                if l is not None and i != '': links = f"""{links}{l}\n"""


            #Text from contents
            text=''
            content = entry.get('content')
            if content is not None:
                for c in content:
                    txt, im, ls = strip_markup(c.get('value'), html=True, rx_images=rx_images, rx_links=rx_links)
                    if txt not in (None, ''):
                        text = f"""\n\n{txt.replace(self.entry['desc'],'')}"""
                        for i in im:
                            if i is not None and i != '': images = f"""{images}{i}\n"""
                        for l in ls:
                            if l is not None and i != '': links = f"""{links}{l}\n"""

            
            self.entry['text'] = nullif(text,'')
            self.entry['images'] = nullif(f'{entry.get("images","")}{images}','')

            # Add enclosures
            enclosures = ''
            enc = entry.get('enclosures',())
            for e in enc: enclosures = f"""{enclosures}{e.get('href','')}\n"""
            self.entry['enclosures'] = nullif(enclosures,'')

            # Tag line needs to be combined
            tags = ''
            for t in entry.get('tags', ()): tags = f"""{tags}  {scast(t.get('label',t.get('term','')), str, '')}"""
            self.entry['tags'] = nullif(tags,('',' '))

            # Compile string with present links
            link_string = ''
            for l in entry.get('links',()): link_string = f"""{link_string}{l.get('href','')}\n"""
            self.entry['links'] = nullif(f"""{link_string}{links}""",'')

            pguids.append(self.entry['guid'])
            plinks.append(self.entry['link'])
            yield self.entry




    def _get_images(self):
        """Download feed images/icons/logos to icon folder to use in notifications"""
        for i in self.images:
            href = scast( slist(i, 2, None), str, '')
            feed_id = scast( slist(i, 0, 0), str, '0')

            if href not in ('',None) and feed_id != 0:
                if self.debug in (1,3): print(f'Downloading image for feed {feed_id} from {href}...')
                imfile = f'{FEEDEX_ICON_PATH}{DIR_SEP}feed_{feed_id}_{self.FX.db_hash}.ico'
                try:
                    req = urllib.request.Request(href, None, self.http_headers)
                    response = urllib.request.urlopen(req)
                    if response.status in (200, 201, 202, 203, 204, 205, 206):
                        
                        if response.info().get('Content-Type') not in FEEDEX_IMAGE_MIMES: return f"""{_('Not a valid image type')} ({response.info().get('Content-Type')})"""
                        content_size = scast(response.info().get('Content-Length'), int, None)
                        if content_size is not None and content_size > MAX_DOWNLOAD_SIZE: return f"""{_('Resource size too big')} ({content_size}). {_('Should be')} {MAX_DOWNLOAD_SIZE} {_('max')}"""
                        with open(imfile, 'wb') as f:
                            i = 0
                            while True:
                                i += 1
                                chunk = response.read(FEEDEX_MB)
                                if not chunk: break
                                if i >= MAX_DOWNLOAD_SIZE:
                                    f.close()
                                    return f'{_("Image resource too large! Should be")} {MAX_DOWNLOAD_SIZE} {_("max")}' 
                                f.write(chunk)
                    else: 
                        self.images = []
                        return f'{_("URLLib could not save image from")} {href}! {_("HTTP return status")}: {response.status}'    

                except (urllib.error.URLError, ValueError, TypeError, OSError) as e:
                    self.images = []
                    return f'{_("Could not save image from")} {href}! {_("Error")}: {e}'
            else:
                continue

        self.images = []
        return 0






    def update(self, feed, **kargs):
        """ Consolidate feed data from RSS resource """

        if kargs.get('feed_raw') is not None:
            self.feed_raw = kargs.get('feed_raw')

        if self.feed_raw.get('feed',None) is None: return f'{_("Downloaded feed empty")} ({feed.name()})!'

        self.feed.clear()
        # Get image urls for later download
        if not kargs.get('ignore_images', False):
            icon = self.feed_raw['feed'].get('icon',None)
            if icon is not None:
                self.images.append([feed['id'], None, icon, None])
            else:
                logo = self.feed_raw['feed'].get('logo',None)
                if logo is not None:
                    self.images.append([feed['id'], None, logo, None])
                else:
                    image = self.feed_raw['feed'].get('image',None)
                    if image is not None:
                        self.images.append([feed['id'], None, image.get('href',None), image.get('title',None)])

        # Overwrite Nones in current data and populate feed
        self.feed['id']                       = feed['id']
        self.feed['link']                     = self.feed_raw['feed'].get('link', None)
        self.feed['charset']                  = coalesce(feed['charset'], self.feed_raw.get('encoding',None))
        self.feed['lang']                     = coalesce(feed['lang'], self.feed_raw['feed'].get('lang',self.feed_raw['feed'].get('feed',{}).get('language',None)))
        self.feed['generator']                = coalesce(feed['generator'], self.feed_raw['feed'].get('generator', None))

        authors = feed.get('author','')
        if authors == '' and type(feed.get('authors',())) in (list, tuple):
            for a in feed.get('authors',()): 
                if a.get('name','') != '': authors = f"""{authors}{a.get('name','')}; """
        
        self.feed['author']                   = coalesce(feed['author'], nullif(authors,''))
        self.feed['author_contact']           = nullif( coalesce(feed['author_contact'], self.feed_raw['feed'].get('author_detail',{}).get('email','') + "; " + self.feed_raw['feed'].get('author_detail',{}).get('href','')), '; ')
        self.feed['publisher']                = coalesce(feed['publisher'], self.feed_raw['feed'].get('publisher', None))
        self.feed['publisher_contact']        = nullif( coalesce(self.feed['publisher_contact'], self.feed_raw['feed'].get('publisher_detail',{}).get('email','') + "; " + self.feed_raw['feed'].get('publisher_detail',{}).get('href','')), '; ')

        contribs = ''
        if type(feed.get('contributors',())) in (list, tuple):
            for c in feed.get('contributors',()): 
                if c.get('name','') != '': contribs = f"""{contribs}{c.get('name','')}; """

        self.feed['contributors']             = coalesce(feed['contributors'], nullif(contribs,''))
        self.feed['copyright']                = coalesce(feed['copyright'], self.feed_raw['feed'].get('copyright', None))
        self.feed['title']                    = coalesce(feed['title'], self.feed_raw['feed'].get('title', None))
        self.feed['subtitle']                 = coalesce(feed['subtitle'], self.feed_raw['feed'].get('subtitle', None))
        self.feed['category']                 = coalesce(feed['category'], self.feed_raw['feed'].get('category', None))

        tags = ''
        for t in self.feed_raw['feed'].get('tags', ()): tags = f"""{tags} {scast(t.get('label',t.get('term','')), str, '')}"""
        self.feed['tags']                     = coalesce(feed['tags'], tags)
        self.feed['name']                     = coalesce(feed['name'], self.feed_raw['feed'].get('title', None))
        self.feed['version']                  = self.feed_raw.get('version',None)

        if not kargs.get('ignore_images', False):
            msg = self._get_images()
            if msg != 0: return msg
        return 0





    def set_agent(self, agent):
        """ Set custom user agent """
        if agent is None: self.agent = self.config.get('user_agent', FEEDEX_USER_AGENT)
        else: self.agent = coalesce( nullif(scast(agent, str, '').strip(), ''), self.config.get('user_agent', FEEDEX_USER_AGENT) )










class FeedexHTMLHandler(FeedexRSSHandler):  
    """HTML handler for Feedex"""

    compare_links = False
    no_updates = False
    all_is_html = True

    def __init__(self, FX, **kargs):
        FeedexRSSHandler.__init__(self, FX, **kargs)


    def _parse_html(self, html, **kargs):
        """ Parse html string with REGEXes """
        ifeed = kargs.get('ifeed',self.ifeed)
        regexes = {}
        for r in FEEDS_REGEX_HTML_PARSERS: 
            restr = scast(ifeed.get(r), str, '')
            if restr == '': regexes[r] = ''
            else: 
                try: regexes[r] = re.compile( scast(ifeed.get(r), str, ''), re.DOTALL)
                except re.error as e: 
                    self.error = True
                    self.error_str = f'{r} {_("REGEX")} {e}'
                    return f'{self.error_str}', _('<ERROR>'), _('<ERROR>'), _('<ERROR>'), _('<ERROR>'), _('<ERROR>'), ()

        feed_title = re.findall(regexes['rx_title_feed'], html)
        feed_title = slist(feed_title, 0, None)
        feed_pubdate = re.findall(regexes['rx_pubdate_feed'], html)
        feed_pubdate = slist(feed_pubdate, 0, None)
        feed_img = re.findall(regexes['rx_image_feed'], html)
        feed_img = slist(feed_img, 0, None)
        feed_charset = re.findall(regexes['rx_charset_feed'], html)
        feed_charset = slist(feed_charset, 0, None)
        feed_lang = re.findall(regexes['rx_lang_feed'], html)
        feed_lang = slist(feed_lang, 0, None)
        
        if regexes['rx_entries'] == '': return feed_title, feed_pubdate, feed_img, feed_charset, feed_lang, '', () 
        entries_str = re.findall(regexes['rx_entries'], html)
        entries = []
        entry_sample = ''
        if type(entries_str) in (tuple,list) and len(entries_str) > 0:
            if entry_sample == '': entry_sample = entries_str[0]
            links = [] # List to avoid duplicates
            for e in entries_str:
                if type(e) is not str: continue
                entry = {}
                
                title = re.findall(regexes['rx_title'], e)
                entry['title'] = slist(title, 0, None)
                if entry['title'] in (None, ''): continue

                link = slist(re.findall(regexes['rx_link'], e), 0, None)
                if link in links: continue
                links.append(link)
                entry['link'] = link

                if type(entry.get('link')) is str:
                    guid = hashlib.sha1(entry.get('link').encode())
                    entry['guid'] = guid.hexdigest()
                else: continue

                if regexes['rx_desc'] != '': entry['description'] = slist( re.findall(regexes['rx_desc'], e), 0, None)
                if regexes['rx_author'] != '': entry['author'] = slist( re.findall(regexes['rx_author'], e), 0, None)
                if regexes['rx_category'] != '': entry['category'] = slist( re.findall(regexes['rx_category'], e), 0, None)
                if regexes['rx_text'] != '': entry['content'] = [{'value':slist( re.findall(regexes['rx_text'], e), 0, None)}]
                if regexes['rx_images'] != '': entry['images'] = slist( re.findall(regexes['rx_images'], e), 0, None)
                if regexes['rx_pubdate'] != '': entry['updated'] = slist( re.findall(regexes['rx_pubdate'], e), 0, None)

                if entry.get('title') is not None and entry.get('link') is not None: entries.append(entry.copy())

        return feed_title, feed_pubdate, feed_img, feed_charset, feed_lang, entry_sample, entries




    def _do_download(self, url: str, **kargs):
        """ Download HTML resource """
        self.http_headers['User-Agent'] = self.agent
        del self.http_headers['agent']
        try:
            req = urllib.request.Request(url, None, self.http_headers)
            response = urllib.request.urlopen(req)
        except Exception as e:
            self.error = True
            self.error_str = f'URLLib: {e}'
            return {}

        content_type = slist(scast(response.info().get('Content-Type'), str, '').split(';'), 0, '')
        if content_type not in FEEDEX_TEXT_MIMES:
            self.error = True
            self.error_str = f"""{_('Invalind content type')} ({response.info().get('Content-Type')})  ({_('Should be text/plain or text/html')})"""
            return {}
        content_size = scast(response.info().get('Content-Length'), int, None)
        if content_size is not None and content_size > MAX_DOWNLOAD_SIZE: 
            self.error = True
            self.error_str = f"""{_('Resource too big')} ({content_size})  ({_('Should be')} {MAX_DOWNLOAD_SIZE} {_('max')})"""
            return {}
        
        html = ''
        i = 0
        try:
            while True:
                chunk = response.read(FEEDEX_MB)
                i += 1
                if not chunk: break
                if i >= MAX_DOWNLOAD_SIZE: 
                    self.error = True
                    self.error_str = _("""Resource too big!""")
                    return {}
                html = f'{html}{chunk.decode("utf-8")}'
        except Exception as e:
            self.error = True
            self.error_str = f'{_("URLLib")}: {e}'
            return {}
        
        html = scast(html, str, None)
        if html is None:
            self.error = True
            self.error_str = _("""Downloaded resource could not be converted to text""")
            return {}

        feed_raw = {}
        feed_raw['status'] = response.status
        feed_raw['etag'] = response.headers.get('etag')
        feed_raw['modified'] = response.headers.get('modified')
        feed_raw['raw_html'] = html

        if kargs.get('download_only',False): return feed_raw

        title, pubdate, image, charset, lang, entry_sample, entries = self._parse_html(html)
        feed_raw['feed'] = {}
        feed_raw['feed']['title'] = title
        feed_raw['feed']['updated'] = pubdate
        feed_raw['feed']['icon'] = image
        feed_raw['feed']['lang'] = lang
        feed_raw['encoding'] = charset

        if entries != []: feed_raw['entries'] = entries
        return feed_raw




    def test_download(self, **kargs):
        """ Test download and parse into displayable string """
        self.error = False
        self.error_str = ''

        if self.feed_raw.get('raw_html') is None:
            if self.debug in (1,3): print(f"""Downloading {self.ifeed.get('url')} ...""")
            self.feed_raw = self._do_download(self.ifeed.get('url'), download_only=True)

        if not self.error: return self._parse_html(self.feed_raw.get('raw_html'))
        else: return f'{self.error_str}', _('<ERROR>'), _('<ERROR>'), _('<ERROR>'), _('<ERROR>'), _('<ERROR>'), () 









class FeedexScriptHandler:  
    """User fetching script handler for Feedex"""

    compare_links = True
    no_updates = True

    def __init__(self, FX, **kargs):
        FeedexRSSHandler.__init__(self, FX, **kargs)


    def _do_download(self, dummy, **kargs):
        """ Execute script and load JSON return value to load as raw feed"""
        command = self.ifeed.get('script_file')
        if command is None: 
            self.error = True
            self.error_str = _('No script file provided!')
            return {}

        # Substitute command line params ...
        rstr = random_str(string=command)
        command = command.split()
        
        for i, arg, in enumerate(command):
            arg = arg.replace('%%',rstr)
            arg = arg.replace('%A', self.http_headers.get('agent'))
            arg = arg.replace('%E', self.http_headers.get('etag'))
            arg = arg.replace('%M', self.http_headers.get('modified'))
            arg = arg.replace('%L', self.http_headers.get('login'))
            arg = arg.replace('%P', self.http_headers.get('password'))
            arg = arg.replace('%D', self.http_headers.get('domain'))
            arg = arg.replace('%U', self.ifeed.get('url'))
            arg = arg.replace('%F', self.ifeed.get('id'))
            arg = arg.replace(rstr, '%')
            command[i] = arg

        if self.debug in (1,3): print(f"""Runing script: {' '.join(command)}""")

        try:
            comm_pipe = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            json_str = comm_pipe.stdout.read()
        except OSError as e:
            self.error = True
            self.error_str = f'{_("Error executing script")}: {e}'
            return {}

        if self.debug in (1,3): print(f'Output: {json_str}')

        try:
            return json.loads(json_str)
        except (OSError, JSONDecodeError) as e:
            self.error = True
            self.error_str = f'{_("Error decoding JSON")}: {e}'
            return {}