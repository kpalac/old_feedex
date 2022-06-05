# -*- coding: utf-8 -*-
""" Resource download utils for FEEDEX """


from feedex_gui_utils import *










class FeedexResDownloader:
    """ Resource download engine for Feedex GUI """
    def __init__(self, parent, **kargs) -> None:

        self.lock = threading.Lock()

        self.parent = parent
        self.FX = self.parent.FX
        self.config = self.FX.config
        self.debug = kargs.get('debug', self.FX.debug)

        self.queue = []
        self.errors = []

        self.entries = {}
        self.resources = {}




    def _parse_res_string(self, string:str, **kargs):
        """ Parse resource string """
        if string.strip() == '': return None, {}
        if string.startswith('http://') or string.startswith('https://'): 
            is_raw_url = True
            url = string
        else: 
            is_raw_url = False
            url = slist(re.findall(IM_URL_RE, string), 0, None)

        # This is to avoid showing icons from feedburner
        if url is None or url.startswith('http://feeds.feedburner.com'): return None, {}
        # Ommit previous dead links
        if url in self.errors: return None, {}

        if not is_raw_url:
            alt = slist(re.findall(IM_ALT_RE, string), 0, '')
            title = slist(re.findall(IM_TITLE_RE, string), 0, '')

            title = slist( strip_markup(scast(title, str,''), html=True), 0, '')
            alt = slist( strip_markup(scast(alt, str, ''), html=True), 0, '')
        else:
            alt = ''
            title = ''


        hash_obj = hashlib.sha1(url.encode())

        tooltip=''
        if title.strip() not in ('',None): tooltip=f"""<b><i>{esc_mu(title)}</i></b>
"""
        if alt.strip() not in ('',None): tooltip=f"""{tooltip}<b>{esc_mu(alt)}</b>"""

        return url, {'alt':alt, 'title':title, 'tooltip':tooltip, 'hash':hash_obj.hexdigest()}





        
    def get_resource(self, string, **kargs):
        """ Establish content type for a resource """
        url, resource = self._parse_res_string(string)
        if url is None or resource == {}: return -1
        resource['ready'] = False

        resource['filename'] = f"""{FEEDEX_CACHE_PATH}{DIR_SEP}{self.FX.db_hash}_{resource.get('hash','')}.res""" 

        if os.path.isfile(resource['filename']):
            resource['ready'] = True
            resource['type'] = 'image'
            return 0, resource
        elif self.resources.get(url,{}).get('ready',False):
            return 0, resource

        headers = {'User-Agent' : kargs.get('user_agent', self.config.get('user_agent',FEEDEX_USER_AGENT))}

        try:
            req = urllib.request.Request(url, None, headers)
            response = urllib.request.urlopen(req)

            resource['status'] = response.status

            if response.status not in (200, 201, 202, 203, 204, 205, 206): 
                self.lock.acquire()
                self.errors.append(url)
                self.lock.release()
                return -1, f'{_("Could not download resource at %a! HTTP return status:")} {response.status}', f'{url}'

            resource['mime-type'] = response.info().get('Content-Type')
            resource['size'] = scast(response.info().get('Content-Length'), int, None)



            if resource['mime-type'] in FEEDEX_IMAGE_MIMES:
                resource['type'] = 'image'
                if resource['size'] is not None and resource['size'] > MAX_DOWNLOAD_SIZE: return -1, _('Resource too large! Should be %a max'), MAX_DOWNLOAD_SIZE

                if not open:
                    
                    i = 0
                    img_data = BytesIO()
                    while True:
                        i += 1
                        img_chunk = response.read(FEEDEX_MB)
                        if not img_chunk: break
                        if i >= MAX_DOWNLOAD_SIZE: return -1, _('Resource too large! Should be %a max'), MAX_DOWNLOAD_SIZE
                        img_data.write(img_chunk)

                    img = Image.open(img_data)
                    img.thumbnail((150, 150))
                    img.save(resource['filename'], format="PNG")
                    
                else:
                    i = 0
                    with open(resource['filename'], 'wb') as f:
                        while True:
                            i += 1
                            chunk = response.read(FEEDEX_MB)
                            if not chunk: break
                            if i >= MAX_DOWNLOAD_SIZE:
                                f.close()
                                return -1, _('Resource too large! Should be %a max'), MAX_DOWNLOAD_SIZE
                            f.write(chunk)
                
                    err = ext_open(self.config, 'image_viewer', resource['filename'], title=resource['title'], alt=resource['alt'], file=True, debug=self.debug)
                    if err != 0: return -1, err


            elif resource['mime-type'] in FEEDEX_AUDIO_MIMES:
                resource['type'] = 'audio'


            elif resource['mime-type'] in FEEDEX_VIDEO_MIMES:
                resource['type'] = 'video'

            
            resource['ready'] = True
            return 0, resource

        except (urllib.error.URLError, ValueError, TypeError, OSError, UnidentifiedImageError, Image.DecompressionBombError, FileNotFoundError, AttributeError) as e:
            self.lock.acquire()
            self.errors.append(url)
            self.lock.release()
            return -1, f'{_("Could not download resource at %a! Error:")} {e}', f'{url}'

        



    def create_thumbnail(self, resource, **kargs):
        """ Build thumbnail widget for image """





