# -*- coding: utf-8 -*-
""" 
Main engine for Feedex news reader. Database interface and REST handling, main Fetching mechanism, interface with ling processor

"""


from feedex_headers import *









class Feeder:
    """ Main engine for Feedex. Handles SQLite3 interface, feed and entry data"""

    def __init__(self, **args):

        # Main configuration
        self.config = args.get('config', DEFAULT_CONFIG)

        # Overload config passed in arguments
        self.debug = args.get('debug',False) # Triggers additional info at runtime
        self.timeout = args.get('timeout', self.config.get('timeout',5)) # Wait time if DB is locked

        self.ignore_images = args.get('ignore_images', self.config.get('ignore_images',False))
        self.wait_indef = args.get('wait_indef',False)

        # This tells us if the GUI is running
        self.gui = args.get('gui',False)
        # Load icons on init?
        self.load_icons = args.get('load_icons', False)

        # Global db lock flag
        self.ignore_lock = args.get('ignore_lock',False)

        # Id it a single CLI run? Needed for reloading flag
        self.single_run = args.get('single_run',True)

        # Init and open log file
        try: self.logf = open(self.config.get('log',''),'a')			
        except: sys.stderr.write(f"Could not open log file {self.config.get('log','<<<EMPTY>>>')}\n")
			
        # Last inserted ids
        self.last_entry_id = 0
        self.last_feed_id = 0
        self.last_rule_id = 0		
	
        self.feeds = [] #Feeds from DB
        self.rules = [] #Rules from DB

        self.features = [] # Pending features to add to rule set
    
        self.entry = SQLContainer('entries', ENTRIES_SQL_TABLE) # Containers for entryand field processing
        self.feed = SQLContainer('feeds', FEEDS_SQL_TABLE)
        self.rule = SQLContainer('rules', RULES_SQL_TABLE)

        self.entries = [] # List of pending entries (e.g. for mass-insert)

        # ... start 
        self.db_status = 0
        self._connect_sqlite()
        if self.db_status != 0: return -1
        self._refresh_data(first_run=True) 

        self.icons = {} # List of icons for feeds
        if self.load_icons: self.do_load_icons()

        # initialize linguistic processor for tokenizing and stemming
        self.LP = LingProcessor(**args) 
        # And query parser ...
        if not args.get('no_qp', False):
            self.QP = FeederQueryParser(self, **args)

        # new item count
        self.new_items = 0

    
        


    def _log(self, err:bool, *kargs, **args):
        """Handle adding log entry (add timestamp or output to stderr if specified by true first argument)"""
        if args.get('print',True):
            if err == True:
                sys.stderr.write(*kargs)
            else:
                print(*kargs)
        log_str = ' '.join(kargs)
        log_str = f"{str(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}\t{log_str}\n"
        self.logf.write(log_str)



    def _connect_sqlite(self):
        """ Connect to SQLite and handle errors """ 
        for _ in self._g_connect_sqlite(): pass
    def _g_connect_sqlite(self):
        """ Connect to SQLite and handle errors - generator method"""
        db_path = self.config.get('db_path','')
        first_run = False # Trigger if DB is not present

        # Copy database from shared dir to local dir if not present (e.g. fresh install)
        if not os.path.isfile(db_path):
            first_run = True
            if self.gui: yield 57
            self._msg(57)
            # Create directory if needed
            db_dir = os.path.dirname(db_path)
            if not os.path.isdir(db_dir):
                os.makedirs(db_dir)
                self._msg(58, db_dir)
                if self.gui: yield 58, db_dir
            
        try:
            self.sqlite_conn = sqlite3.connect(db_path)
            self.sqlite_cur = self.sqlite_conn.cursor()
            if self.debug: print(f"Connected to {db_path}")
        except:
            self._msg(-39, db_path)
            if self.gui: yield -39, db_path
            self.db_status = (-39, db_path)

        if first_run:
            # Run DDL on fresh DB
            with open(f'{FEEDEX_SYS_SHARED_PATH}/data/db_scripts/base/feedex_db_ddl.sql', 'r') as sql:
                sql_ddl = sql.read()
            self.sqlite_cur.executescript(sql_ddl)
            self.sqlite_conn.commit()
            self._msg(59)
            if self.gui: yield 59

            with open(f'{FEEDEX_SYS_SHARED_PATH}/data/db_scripts/base/feedex_db_defaults.sql', 'r') as sql:
                sql_ddl = sql.read()
            self.sqlite_cur.executescript(sql_ddl)
            self.sqlite_conn.commit()
            self._msg(60)
            if self.gui: yield 60

        # This is for queries and needs to be done
        self.sqlite_cur.execute("PRAGMA case_sensitive_like=true;")
        self.sqlite_conn.commit()

        version = slist(self.sqlite_cur.execute("select val from params where name = 'version'").fetchone(), 0, None)
        ver_diff = check_version(version, FEEDEX_VERSION)
        if ver_diff == -1:
            self._msg(-40, db_path)
            if self.gui: yield -40, db_path
            self.db_status = (-40, db_path)
            return -1    

        elif ver_diff == 1:
            self._msg(61, db_path)
            if self.gui: yield 61, db_path

            #Run DDL scripts if file is fresly created and then add some default data to tables (feeds and prefixes) """
            # ... and attempt to update it ...

            # ... make a clean backup
            self.sqlite_conn.rollback()
            self.sqlite_conn.close()
            try:
                copyfile(db_path, db_path + '.bak')
                if self.gui: yield 62, db_path
                self._msg(62, db_path)
            except:
                self.db_status = -2
                if self.gui: yield -41, db_path
                self._msg(-41, db_path)
                self.db_status = (-41, db_path)
                return -1
            self.sqlite_conn = sqlite3.connect(db_path)
            self.sqlite_cur = self.sqlite_conn.cursor()


            for d in sorted( os.listdir(f'{FEEDEX_SYS_SHARED_PATH}/data/db_scripts') ):

                if d != 'base' and d <= FEEDEX_VERSION:
                    ver_path = os.path.join(f'{FEEDEX_SYS_SHARED_PATH}/data/db_scripts',d)
                    for f in sorted( os.listdir(ver_path) ):
                        scr_path = os.path.join(ver_path, f)
                        if os.path.isfile(scr_path):
                            if self.gui: yield 63
                            self._msg(63)
                            try:
                                with open(scr_path) as sql_file:
                                    update_script = sql_file.read()
                                self.sqlite_cur.executescript(update_script)
                                self.sqlite_conn.commit()
                            except Exception as e:
                                if self.gui: -42, scr_path
                                self._msg(-42, scr_path)
                                print(e)
                                # Restor backup...
                                self.sqlite_conn.rollback()
                                self.sqlite_conn.close()
                                try:
                                    copyfile(db_path + '.bak', db_path)
                                    if self.gui: 64
                                    self._msg(64)
                                except:
                                    if self.gui: -43
                                    self._msg(-43)
                                self.db_status = -43
                                return -1
            
            if self.gui: yield 65
            self._msg(65)
            


    def _reset_connection(self, **args):
        """ Reset connection to database, rollback all hanging transactions and unlock"""
        self.sqlite_conn.rollback()
        self.sqlite_conn.close()
        self._connect_sqlite()
        self.unlock()

        if args.get('log',False): self._log(False, "Connection reset")





    # Database lock and handling it with timeout - waiting for availability
    def lock(self, **args):
        """ Locks DB """
        self.sqlite_cur.execute("insert into params values('lock', 1)")
        self.sqlite_conn.commit()

    def unlock(self, **args):
        """ Unlocks DB """
        if args.get('ignore',False):
            return False
        self.sqlite_cur.execute("delete from params where name='lock'")
        self.sqlite_conn.commit()

    
    def locked(self, **args):
        """ Checks if DB is locked and waits the timeout checking for availability before aborting"""
        if args.get('ignore',False): return False
        if self.ignore_lock: return False

        if self.gui: timeout = 1
        else: timeout = self.timeout

        tm = 0
        while tm <= timeout or self.wait_indef:
            tm = tm + 1
            time.sleep(1)
            lock = self.sqlite_cur.execute("select * from params where name = 'lock'").fetchone()
            if lock != None: sys.stderr.write(f"Database locked... Waiting ... {tm}")     
            else:
                self.lock()
                return False

        sys.stderr.write("Timeout reached...")
        return True




    def _run_sql(self, query:str, vals:list, **args):
        """ Safely run a SQL insert/update """
        many = args.get('many',False)
        try:
            if many: self.sqlite_cur.executemany(query, vals)
            else: self.sqlite_cur.execute(query, vals)
            return 0
        except Exception as e:
            if hasattr(e, 'message'): return e.message
            else: return e





    def load_feeds(self):
        """Get feed data from database"""
        self.feeds = self.sqlite_cur.execute(GET_FEEDS_SQL).fetchall()

    def do_load_icons(self):
        """ Loads icon paths for feeds """
        self.icons = {}
        for f in self.feeds:
            id = f[self.feed.get_index('id')]
            handler = f[self.feed.get_index('handler')]
            is_category = f[self.feed.get_index('is_category')]
            if is_category == 1:
                self.icons[id] = f'{FEEDEX_SYS_ICON_PATH}/document.svg'
            else:
                if handler == 'rss':
                    if os.path.isfile(f'{FEEDEX_ICON_PATH}/feed_{id}.ico'):
                        self.icons[id] = f'{FEEDEX_ICON_PATH}/feed_{id}.ico'
                    else: 
                        self.icons[id] = f'{FEEDEX_SYS_ICON_PATH}/news-feed.svg'
                elif handler == 'twitter':
                    self.icons[id] = f'{FEEDEX_SYS_ICON_PATH}/twitter.svg'
                elif handler == 'local':
                    self.icons[id] = f'{FEEDEX_SYS_ICON_PATH}/mail.svg'


    def load_rules(self, **args):
        """Get learned and saved rules from DB"""
        no_limit = args.get('no_limit',False)
        limit = scast(self.config.get('rule_limit'), int, 50000)

        if not self.config.get('use_keyword_learning', True):  #This config flag tells if we should learn and rank autoatically or by manual rules only
            self.rules = self.sqlite_cur.execute(GET_RULES_NL_SQL).fetchall()
        else:
            if no_limit or limit == 0:
                self.rules = self.sqlite_cur.execute(GET_RULES_SQL).fetchall()
            else:
                self.rules = self.sqlite_cur.execute(f'{GET_RULES_SQL}LIMIT ?', (limit,) ).fetchall()           
 
        # If this is a first run - update them also for ling processor
        if not args.get('first_run',False): self.LP.rules = self.rules




    def resolve_category(self, val:str, **args):
        """ Resolve entry type depending on whether ID or name was given"""
        if val == None: return None
        load = args.get('load',False)
        if scast(val, str, '').isdigit():
            val = int(val)
            for f in self.feeds:
                if f[self.feed.get_index('id')] == val and f[self.feed.get_index('is_category')] == 1:
                    if load: self.feed.populate(f)
                    return f[self.feed.get_index('id')]
        else:
            val = str(val)
            for f in self.feeds:
                if f[self.feed.get_index('name')] == val and f[self.feed.get_index('is_category')] == 1:
                    if load: self.feed.populate(f)
                    return f[self.feed.get_index('id')]
        self._msg(-5, val)
        return False


    def resolve_field(self, val:str):
        """ Resolve field ID depending on provided field name. Returns -1 if field is not in prefixes """
        if val in (None, -1): return None
        if type(val) == int or str(val).isdigit():
            val = scast(val, int, -1)
            if val in PREFIXES.keys():
                return val

        for p in PREFIXES.keys():
            if scast(val, str, '').lower() == PREFIXES[p][1].replace('e.',''):
                if p == 0: break
                return p

        self._msg(-48, val)
        return False


    def resolve_feed(self, val:int, **args):
        """ check if feed with given ID is present """
        if val == None: return None
        load = args.get('load',False)
        value = scast(val, int, None)
        for f in self.feeds:
            if value == f[self.feed.get_index('id')]:
                if load: self.feed.populate(f)
                return value
        self._msg(-19, val)
        return False


    def _refresh_data(self, **args):
        """Refresh all data (wrapper)"""
        if ( not self.single_run ) or args.get('first_run',False):
            self.load_feeds()
            self.load_rules(first_run=args.get('first_run',False))
		






    # Database statistics...
    def _update_stats(self):
        """ Get DB statistics and save them to params table for quick retrieval"""
        self.sqlite_cur.execute("delete from params where name = 'doc_count'")
        self.sqlite_cur.execute("delete from params where name = 'avg_weight'")

        if self.debug: print("Updating database document statistics...")

        doc_count = self.sqlite_cur.execute('select count(e.id) from entries e').fetchone()[0]
        doc_count = scast(doc_count, int, 0)
        avg_weight = self.sqlite_cur.execute('select avg(coalesce(weight,0)) from entries').fetchone()[0]
        avg_weight = scast(avg_weight, float, 0)

        self.sqlite_cur.execute("insert into params values('doc_count', ?)", (doc_count,) )
        self.sqlite_cur.execute("insert into params values('avg_weight', ?)", (avg_weight,) )

        self.sqlite_conn.commit()

        if self.debug:
            print("Done:")
            print("Doc count: ", doc_count, " ")
            print("Avg weight: ", avg_weight, " ")



    def get_doc_count(self):
        """ Retrieve entry count from params"""
        doc_count = self.sqlite_cur.execute("select val from params where name = 'doc_count'").fetchone()
        if doc_count in (None, (None,),()):
            self._update_stats()
            doc_count = self.sqlite_cur.execute("select val from params where name = 'doc_count'").fetchone()
        doc_count = scast(doc_count[0], int, 1)
        return doc_count


    def get_avg_weight(self):
        """ Retrieve average entry weight - used for soft higlighting downloaded entries"""
        av_weight = self.sqlite_cur.execute("select val from params where name = 'avg_weight'").fetchone()
        if av_weight in (None, (None,),()):
            self._update_stats()
            av_weight = self.sqlite_cur.execute("select val from params where name = 'avg_weight'").fetchone()
        return scast(av_weight[0], float, 1)



    def _msg(self, *kargs):
        """ Printing CLI messages and log handling per need"""
        # Handle different input type - better here, than throughout the code ...
        if len(kargs) == 1:
            if type(kargs[-1]) in (list, tuple):
                code = kargs[-1][0]
                arg = slist(kargs[-1], 1, None)
            elif type(kargs[-1]) == int:
                code = kargs[-1]
                arg = None
            elif type(kargs[-1]) == str:
                code = 0
                arg = kargs[-1]

        elif len(kargs) == 2:
            code = kargs[-2]
            arg = kargs[-1]
        else:
            return -1            
            
        lst = MESSAGES.get(code, (None, False, False)) 
        msg = lst[0]
        arg = scast(arg, str, '')
        log = lst[1]
        error = lst[2]
        if error:
            snorm = TERM_ERR
            sbold = TERM_ERR_BOLD
        else:
            snorm = TERM_NORMAL
            sbold = TERM_BOLD

        if msg == None:
            pmsg = arg
        else:
            parg = f"""{sbold}{arg}{snorm}"""
            if '%a' in msg:
                pmsg = msg.replace('%a', parg)
                lmsg = msg.replace('%a', arg)
            elif arg != f"""{sbold}{snorm}""":
                pmsg = f'{msg} {parg}'
                lmsg = f'{msg} {arg}'
        pmsg = f'{snorm}{pmsg}{TERM_NORMAL}'

        if log:
            self._log(error, lmsg, print=False)

        if error:
            sys.stderr.write(pmsg+'\n')
        else:
            print(pmsg)







############################################
# FEEDS


    def del_feed(self, id:int, **args):
        """Delete feed data - by ID only"""
        for _ in self.g_del_feed(id, **args): pass
    def g_del_feed(self, id:int, **args):
        """Delete feed data - by ID only (generator method)"""
        id = scast(id,int,0)
        stype = args.get('type','feed')
        if stype == 'category' and self.resolve_category(id, load=True) in (None,False) :
            if self.gui: yield -5, id
            return -1            
        if stype == 'feed' and self.resolve_feed(id, load=True) in (None,False) :
            if self.gui: yield -19, id
            return -1            

        if self.feed['deleted'] == 1: deleted = True
        else: deleted = False
        name = feed_name_cli(self.feed)

        if self.locked(ignore=args.get('ignore_lock',False)):
            if self.gui: yield -2, None
            return -2
        if not deleted:
            # Mark as deleted  - no processing, query only if explicitly id'd
            err = self._run_sql("update feeds set deleted = 1 where id = ?", (id,) )                          
        else:
            # Delete permanently with all data
            err = self._run_sql("delete from rules where learned = 1 and context_id in (select e.id from entries e where e.feed_id = ?)", (id,) )
            if err == 0: err = self._run_sql("delete from entries where feed_id = ?", (id,) )
            if err == 0: err = self._run_sql("update feeds set parent_id = NULL where parent_id = ?", (id,) )
            if err == 0: err = self._run_sql("delete from feeds where id = ?", (id,) )
            if err == 0:
                if self.icons == {}: self._load_icons()
                icon = self.icons.get(id)
                if icon != None and icon.startswith(f'{FEEDEX_ICON_PATH}/feed_') and os.path.isfile(icon): os.remove(icon)

        if err != 0:
            if self.gui: yield -32, err
            self._msg(-32, err)
            self.sqlite_conn.rollback()
            self.unlock(ignore=args.get('ignore_lock',False))
            return -1
            
        a = self.sqlite_cur.rowcount
        self.sqlite_conn.commit()
        self.unlock(ignore=args.get('ignore_lock',False))
        if a > 0:
            if not deleted:
                if stype == 'feed':
                    if self.gui: yield 6, f'{name} ({id})'
                    self._msg(6, f'{name} ({id})')
                elif stype == 'category':
                    if self.gui: yield 30, f'{name} ({id})'
                    self._msg(30, f'{name} ({id})')
            else:
                if stype == 'feed':
                    if self.gui: yield 31, f'{name} ({id})'
                    self._msg(31, f'{name} ({id})')
                elif stype == 'category':
                    if self.gui: yield 32, f'{name} ({id})'
                    self._msg(32, f'{name} ({id})')
        else:
            if self.gui: yield 7
            self._msg(7, None)

        self._refresh_data()
        return 0



    def add_feed(self, name:str, fields:dict, **args): 
        """Wrapper for adding a feed to database"""
        for _ in self.g_add_feed(name, fields, **args): pass
    def g_add_feed(self, name:str, fields:dict, **args):
        """Wrapper for adding a feed to database (generator method)"""
        is_category = fields.get('is_category',False)
        if (not is_category) and (not check_url(args.get('url', None)) and args.get('handler','rss') in ('rss',) ):
            if self.gui: yield -4, args.get('url','<<UNKNOWN>>')
            self._msg(-4, args.get('url','<<UNKNOWN>>'))
            return -1
        if (not is_category) and (not check_url(args.get('link', None))):
            if self.gui: yield -4, args.get('link','<<UNKNOWN>>')
            self._msg(-4, args.get('link','<<UNKNOWN>>'))
            return -1

        self.feed.clear()
        self.feed.merge(fields)

        self.feed['id'] = None
        self.feed['name'] = name
        self.feed['is_category'] = binarify(is_category)
        self.feed['autoupdate'] = binarify(self.feed.get('autoupdate',0))
        self.feed['error'] = 0
        self.feed['interval'] = scast(self.feed.get('interval',None), int, self.config.get('default_interval',45))

        self.feed['parent_id'] = self.resolve_category(self.feed.get('parent_id','<<EMPTY>>') )
        if self.feed['parent_id'] == False:
            if self.gui: yield -5, self.feed.get('parent_id','<<EMTPY>>')
            return -1

        if not is_category:
            self.feed['handler'] = args.get('handler','rss')
        else:
            self.feed['handler'] = None

        self.feed.clean()

        if self.locked(ignore=args.get('ignore_lock',False)):
            if self.gui: yield -2, None
            return -2                
        err = self._run_sql(self.feed.insert_sql(all=True), self.feed.vals)
        
        if err != 0:
            if self.gui: yield -32, err
            self._msg(-32, err)
            self.sqlite_conn.rollback()
            self.unlock(ignore=args.get('ignore_lock',False))
            return -1

        self.last_feed_id = self.sqlite_cur.lastrowid
        a = self.sqlite_cur.rowcount
        self.sqlite_conn.commit()
        self.unlock(ignore=args.get('ignore_lock',False))

        self._refresh_data()

        if a == 0:
            if self.gui: yield 7, None
            return -3
        if is_category:
            if self.gui: yield 2, name
            self._msg(2, name)
        elif not is_category:
            if self.gui: yield 3, args.get('url', '<<UNKNOWN>>')
            self._msg(3, args.get('url', '<<UNKNOWN>>'))

        return 0




	
    def add_feed_from_url(self, url, **args): 
        """This adds feed entry just by downloading it by url. Handy for quickly adding a feed"""
        for _ in self.g_add_feed_from_url(url, **args): pass
    def g_add_feed_from_url(self, url, **args):
        """This adds feed entry just by downloading it by url. Handy for quickly adding a feed (generator method)
            Generator method"""
        if not check_url(url):
            if self.gui: yield -4
            self._msg(-4, None)
            return -1
        url = url.strip()

        handler = args.get('handler','rss')

        # Check if feed is already present (by URL)
        results = self.sqlite_cur.execute("""select * from feeds where url = ? and coalesce(deleted,0) <> 1 and handler <> 'local'""", (url,) ).fetchone()
        if results != None:
            res_id = results[self.feed.get_index("id")]
            res_name = results[self.feed.get_index("name")]
            if self.gui: yield -22, f"{res_name} ({res_id})"
            self._msg(-22, f"{res_name} ({res_id})")
            return -1

        if (not check_url(url) and handler == 'rss' ):
            if self.gui: yield -4, url
            self._msg(-4, url)
            return -1

        parent_id = self.resolve_category(args.get('parent_id'))
        if parent_id in (None,False): parent_id = None

        # If all is ok, then make an insert ...
        if self.locked(ignore=args.get('ignore_lock',False)):
            if self.gui: yield -2, None
            return -2
        err = self._run_sql("""insert into feeds (url, login, domain, passwd, auth, interval, is_category, handler, parent_id, autoupdate) 
values(:url, :login, :domain, :passwd, :auth, :interval, 0, :handler, :parent_id, 1)""",
        {'url': url, 
        'login':args.get('login',None), 
        'domain': args.get('domain',None), 
        'passwd': args.get('passwd',None), 
        'auth': args.get('auth',None), 
        'interval': self.config.get('default_interval',45), 
        'handler' : handler, 
        'parent_id': parent_id}
        )
        if err != 0:
            if self.gui: yield -32, err
            self._msg(-32, err)

        # Save the id for further updating
        self.last_feed_id = self.sqlite_cur.lastrowid
        self.sqlite_conn.commit()
    
        self._refresh_data()
		
        if self.last_feed_id == None:
            if self.gui: yield -23, url
            self.unlock()
            return -1
        self.unlock()
		
        # Now we can update data from the source itself
        for msg in self.g_fetch(id=self.last_feed_id, force=True):
            if self.gui: yield msg
            self._msg(msg)

        self._refresh_data()

        if self.gui: yield 29, f'{str(self.last_feed_id)} - {url}'
        self._msg(29, f'{str(self.last_feed_id)} - {url}')
        return 0






    def edit_feed(self, id, fields:dict, **args):
        """Edit Feed's parameter - wrapper for update"""
        for _ in self.g_edit_feed(id, fields, **args): pass
    def g_edit_feed(self, id, fields:dict, **args):
        """Edit Feed's parameter(s) - wrapper for update (generator method)"""
        id = scast(id,int,0)
        stype = args.get('type','feed')
        if stype == 'category' and self.resolve_category(id, load=True) in (None,False) :
            if self.gui: yield -5, id
            return -1            
        if stype == 'feed' and self.resolve_feed(id, load=True) in (None,False) :
            if self.gui: yield -19, id
            return -1            

        name = self.feed.get('name', self.feed.get('title', self.feed.get('id','<<UNKNOWN>>')))

        sets = 'set'
        vals = {}
        flds = []
        for field in fields.keys():

            field = scast(field, str, None)
            if field == None: continue
            if field.lower() == 'id': continue
            value = fields[field]
            if value in ('null','NULL','Null'): value=None

            if field == 'url':
                if fields.get('handler') in ('rss','twitter') or ( fields.get('handler') == None and self.feed['handler'] in ('rss',)):
                    if not check_url(value):
                        if self.gui: yield -4, value
                        self._msg(-4, value)
                        continue

            if field == 'link' and not check_url(value):
                if self.gui: yield -4, value
                self._msg(-4, value)
                continue

            if field in ('parent_id'):
                if self.feed['is_category'] == 1:
                    if self.gui: yield -6, None
                    self._msg(-6, None)
                    continue
                value = self.resolve_category(value, load=False)
                if value == False:
                    if self.gui: yield -5, value
                    continue
                cat_name = '<<UNKNOWN>>'
                for c in self.feeds:
                    if c[self.feed.get_index('id')] == value:
                        cat_name = c[self.feed.get_index('name')]
                        break

            if field not in FEEDS_SQL_TABLE:
                if self.gui: yield -29, field
                self._msg(-29, field)
                continue
            
            if self.feed[field] != value:
                sets = f"""{sets} {field} = :{field},"""
                vals[field] = value
                flds.append(field)
        

        if len(flds) > 0:
            sets = sets[:-1]
            vals['id'] = id
            sql = f"""update feeds\n{sets}\nwhere id = :id""" 

            if self.locked(ignore=args.get('ignore_lock',False)): 
                if self.gui: yield -2
                return -2
            err = self._run_sql(sql, vals)

            if err != 0:
                if self.gui: yield -32, err
                self._msg(-32, err)
                self.sqlite_conn.rollback()
                self.unlock(ignore=args.get('ignore_lock',False))
                return -1

            a = self.sqlite_cur.rowcount
            self.sqlite_conn.commit()
            self.unlock(ignore=args.get('ignore_lock',False))
        else: a = 0

        if a > 0:
            for f in flds:
                if f == 'deleted' and vals[f] in (0, None):
                    if self.gui: yield 36, f'{stype.capitalize()} {name}'
                    self._msg(36, f'{stype.capitalize()} {name}')
                elif f == 'error' and vals[f] in (0, None) and stype == 'feed':
                    if self.gui: yield 37, f'{stype.capitalize()} {name}'
                    self._msg(37, f'{stype.capitalize()} {name}')    
                elif stype == 'feed' and f in ('parent_id',) and vals[f] not in (0, None):
                    if self.gui: yield 38, cat_name
                    self._msg(38, cat_name)
                elif stype == 'feed' and f in ('parent_id',) and vals[f] in (0, None):
                    if self.gui: yield 39, name
                    self._msg(39, name)        
                else:
                    if self.gui: yield 8, f'{stype.capitalize()} {name}: {f} -> {scast(vals[f],str,"NULL")}'
                    self._msg(8, f'{stype.capitalize()} {name}: {f} -> {scast(vals[f],str,"NULL")}')
            if len(flds) > 1:
                if self.gui: yield 45, name
                self._msg(45, name)

        else:
            if self.gui: yield 7, None
            self._msg(7, None)
            return -3            
        return 0






###############################################
# ENTRIES


    def edit_entry(self, id, fields:dict, **args):
        """Wrapper for update on entries """
        for _ in self.g_edit_entry(id, fields, **args): pass
    def g_edit_entry(self, id, fields:dict, **args):
        """Wrapper for update on entries (generator method)"""
        sets = 'set'
        vals = {}
        flds = []
        recalculate = False
        learn = args.get('learn', self.config.get('use_keyword_learning', True))
        relearn = False

        self.entry.populate(self.sqlite_cur.execute("""select * from entries where id = ?""", (id,) ).fetchone())
        if self.entry['id'] == None:
            if self.gui: yield -24, id
            self._msg(-24, id)
            return -1

        for field in fields.keys():
            field = scast(field, str, None)
            if field == None: continue
            if field.lower() == 'id': continue
            value = fields[field]
            
            if value in ('null','NULL','Null'): value=None

            if field == 'link' and not check_url(value):
                if self.gui: yield -4, value
                self._msg(-4, value)
                continue
            
            if field == 'feed_id':
                value = self.resolve_feed(value, load=False) in (None,False)
                if value in (False,None):
                    if self.gui: yield -19
                    continue

            if field == 'category':
                field = 'feed_id'
                value = self.resolve_category(value, load=False)
                if value in (False,None):
                    if self.gui: yield -5, 
                    self._msg(-5)
                    continue

            if field not in ENTRIES_SQL_TABLE: # bad field name
                if self.gui: yield -29, field
                self._msg(-29, field)
                continue

            # restricted field chosen
            if field in LING_TECH_LIST: 
                if self.gui: yield -44, field
                self._msg(-44, field)    
                continue

            if self.entry[field] == value: continue # no changes made
            
            # Text changed - needs recalculation
            if field in LING_LIST1:
                recalculate = True
                self.entry[field] = value
            
            # Read status increased - relearn keywords
            if field == 'read':
                if value not in (0,None) and self.entry['read'] in (None,0):
                    if learn: relearn = True

            sets = f"""{sets} {field} = :{field},"""
            vals[field] = value
            flds.append(field)

        # Deal with recalculations if concerned fields were changed
        if recalculate or relearn:
            if self.gui: yield 66, id
            self._msg(66, id)
            
            self.entry = self._ling(self.entry, stats=True, rank=False, learn=relearn)
            if isinstance(self.entry, SQLContainer):
                for field in LING_TECH_LIST: 
                    sets = f"""{sets} {field} = :{field},"""
                    vals[field] = self.entry[field]
                    flds.append(field)
            else:
                if self.gui: yield -33, id
                self._msg(-33, id)
                return -1


        if len(flds) > 0:
            sets = sets[:-1]
            sql = f"""update entries\n{sets}\nwhere id = :id"""
            vals['id'] = id

            if self.locked(ignore=args.get('ignore_lock',False)): 
                if self.gui: yield -2
                return -2
            err = self._run_sql(sql, vals)

            if err != 0:
                if self.gui: yield -32, err
                self._msg(-32, err)
                self.sqlite_conn.rollback()
                self.unlock(ignore=args.get('ignore_lock',False))
                return -1

            else:
                a = self.sqlite_cur.rowcount
                self.sqlite_conn.commit()
                self.unlock(ignore=args.get('ignore_lock',False))
       
        else: a = 0

        if a > 0:

            for f in flds: 
                if f in LING_TECH_LIST: continue
                elif f == 'deleted' and vals[f] in (None, 0):
                    if self.gui: yield 40, id
                    self._msg(40, id)
                elif f == 'read' and vals[f] in (None, 0):
                    if self.gui: yield 41, id
                    self._msg(41, id)
                elif f == 'read' and vals[f] not in (None, 0):
                    if self.gui: yield 42, id
                    self._msg(42, id)
                elif f == 'flag' and vals[f] not in (0, None):
                    if self.gui: yield 43, id
                    self._msg(43, id)
                elif f == 'flag' and vals[f] in (0, None):
                    if self.gui: yield 44, id
                    self._msg(44, id)
                else:
                    if self.gui: yield 9, f'{scast(id, str, "<<UNKNOWN>>")}: {f} -> {scast(vals[f],str,"NULL")}'    
                    self._msg(9, f'{scast(id, str, "<<UNKNOWN>>")}: {f} -> {scast(vals[f],str,"NULL")}')

            if len(flds) > 1:
                if self.gui: yield 46
                self._msg(46,None)

        else:
            if self.gui: yield 7, None
            self._msg(7, None)
        return 0



    def del_entry(self, id:int, **args):
        """Delete entry by id """
        for _ in self.g_del_entry(id, **args): pass
    def g_del_entry(self, id:int, **args):
        """Delete entry by id (generator method"""
        res = self.sqlite_cur.execute("select * from entries where id = ?", (id,) ).fetchone()
        if res in (None, (None,), ()):
            if self.gui: yield -24, id
            self._msg(-24, id)
            return -1
        
        self.entry.populate(res)

        if self.locked(ignore=args.get('ignore_lock',False)):
            if self.gui: yield -2, None
            return -2

        if self.entry['deleted'] == 1:
            err = self._run_sql("delete from rules where context_id = ?", (id,))
            if err == 0: err = self._run_sql("delete from entries where id = ?", (id,))
        else:
            err = self._run_sql("update entries set deleted = 1 where id = ?", (id,))

        if err != 0:
            if self.gui: yield -32, err
            self._msg(-32, err)
            self.sqlite_conn.rollback()
            self.unlock(ignore=args.get('ignore_lock',False))
            return -1

        a = self.sqlite_cur.rowcount
        self.sqlite_conn.commit()
        self.unlock(ignore=args.get('ignore_lock',False))
        if a > 0:
            if self.entry['deleted'] == 1:
                if self.gui: yield 33, id
                self._msg(33, id)
            else:
                if self.gui: yield 10, id
                self._msg(10, id)
        else:                
            if self.gui: yield 7
            self._msg(7)

        self._update_stats()
        return 0







    def run_entry(self, **args):
        """Wrapper for opening entries in the browser and updating status (increasing by 1 for each opening)"""
        for _ in self.g_run_entry(**args): pass
    def g_run_entry(self, **args):
        """Wrapper for opening entries in the browser and updating status (increasing by 1 for each opening)
            If specified, it will extract and learn rules form newly read entries (generator method)"""

        url = args.get('url')
        id = args.get('id')

        if url != None: url = url.strip()
        elif id == None: return -1

        if self.debug: print(id, url)

        browser_run = args.get('browser_run',True)   
        update_status = args.get('update_status',True) # Change status to 'Read'?
        learn = args.get('learn', self.config.get('use_keyword_learning', True))

        self.entry.clear()

        if id == None and url != None:
            self.entry.populate( self.sqlite_cur.execute("select * from entries where link = ?", (url,)).fetchone() )
        elif id != None:
            self.entry.populate( self.sqlite_cur.execute("select * from entries where id = ?", (id,)).fetchone() )

        if self.entry['id'] != None:
            empty_run = False
        else:
            empty_run = True


        if update_status and not empty_run:
            err = self._run_sql('update entries set read = coalesce(read,0) + 1 where id = ?', (self.entry['id'],))    
            if err != 0:
                if self.gui: yield -32, err
                self._msg(-32, err)
                self.sqlite_conn.rollback()

            self.sqlite_conn.commit()

        if browser_run and self.entry['link'] != None:
            # Parse browser command line from config and run link in browser
            command = self.config.get('browser','firefox --new-tab %u').split()
            for idx, arg in enumerate(command):
                if arg in ('%u', '%U', '%f', '%F'):
                    command[idx] = self.entry['link']

            if self.debug: print(' '.join(command))
            if self.gui: yield 14, self.entry['link']
            self._msg(14, self.entry['link'])    

            subprocess.Popen(command)

        if not empty_run and learn and self.entry['read'] in (0, None):
            # Extract fields and use them to learn and remember the rules
            if self.gui: yield 15
            self._msg(15, None)
            self.LP.process_fields(self.entry.tuplify(filter=LING_LIST2), learn=True, index=False)
            self.learn_rules(self.LP.features, context_id=self.entry['id'], lang=self.LP.get_model())
        if self.gui: yield 16
        self._msg(16, None)

	







    def add_entries(self, **args):
        for _ in self.g_add_entries(**args): pass
    def g_add_entries(self, **args):
        """ Wraper for inseting entries from list of dicts or a file """
        learn = args.get('learn', self.config.get('use_keyword_learning', True))
        pipe = args.get('pipe',False)

        now = datetime.now()
        now_raw = int(now.timestamp())

        efile = args.get('efile')
        if efile == None and not pipe:
            elist = args.get('elist',())
        elif not pipe:
            elist = parse_efile(efile)
        elif pipe:
            elist = parse_efile(None, pipe=True)
        else:
            elist = -1

        if elist == -1:
            if self.gui: yield -25
            self._msg(-25)
            return -1

        self.entries = []

        if self.locked(ignore=args.get('ignore_lock',False)):
            if self.gui: yield -2, None
            return -2

        # Queue processing
        for e in elist:

            self.entry.clear()          
            self.entry.merge(e)

            if e.get('category') != None:
                self.entry['feed_id'] = self.resolve_category(e.get('category'), load=False)
            else:
                self.entry['feed_id'] = self.resolve_feed(e.get('feed_id'), load=False)

            if self.entry['feed_id'] in (False,None):
                if self.gui: yield -8, self.entry['feed_id']
                self._msg(-8, self.entry['feed_id'])
                return -1

            self.entry.clean()            
            self.entry['id'] = None #Needed to avoid id conflicts
            self.entry['adddate'] = now_raw
            self.entry['adddate_str'] = now
            self.entry['pubdate'] = coalesce(self.entry.get('pubdate', None), now_raw)
            self.entry['pubdate_str'] = coalesce(self.entry.get('pubdate_str', None), now)
            self.entry['read'] = coalesce(self.entry['read'], self.config.get('default_entry_weight',2))
            if args.get('ling',True):
                self.entry = self._ling(self.entry, learn=learn, rank=True, stats=True)
            # Insert ...
            err = self._run_sql(self.entry.insert_sql(all=True), self.entry.vals)
            if err != 0:
                if self.gui: yield -32, err
                self._msg(-32, err)
                self.sqlite_conn.rollback()
                self.unlock(ignore=args.get('ignore_lock',False))
                return -1
            # ... and learn
            context_id = self.sqlite_cur.lastrowid
            self.last_entry_id = context_id
            if self.gui: yield 17, context_id
            self._msg(17, context_id)
            if learn and self.entry['tokens'] not in (None,'') and coalesce(self.entry['read'],0) > 0:
                if self.gui: yield 15
                self._msg(15, None)
                self.learn_rules(self.LP.features, context_id=context_id, lang=self.entry['lang'], ignore_lock=True, commit=False)
            
            if self.gui: yield 34, context_id
            self._msg(34, context_id)

        # Commit and stat
        self.sqlite_conn.commit()
        self._update_stats()
        self.unlock(ignore=args.get('ignore_lock',False))
        self._refresh_data()
        if self.gui: yield 35
        self._msg(35)
                            



##########################################33
#       Terms, rules and keywords
#




    def learn_rules(self, features:dict, **args):
        for _ in self.g_learn_rules(features, **args): pass
    def g_learn_rules(self, features:dict, **args):
        """ Add features/rules to database """
        if self.debug: print("Processing extracted features...")

        if self.locked(ignore=args.get('ignore_lock',False)):
            if self.gui: yield -2, None
            return -2

        context_id = args.get('context_id')
        lang=args.get('lang','heuristic')

        if context_id != None and context_id > 0:
            self.sqlite_cur.execute("delete from rules where context_id = ? and learned = 1", (context_id,) )

        query_list_rules = []
        for f in features.keys():
            weight = slist(features.get(f),0,0)
            qtype = slist(features.get(f),1,0)
            if weight <= 0: continue
            self.rule.clear()
            self.rule['string'] = f[1:]
            self.rule['weight'] = weight
            self.rule['name'] = slist(features.get(f),2,0)
            self.rule['type'] = qtype
            self.rule['case_insensitive'] = 0
            self.rule['lang'] = lang
            self.rule['learned'] = 1
            self.rule['flag'] = 0
            self.rule['additive'] = 1
            self.rule['context_id'] = context_id
            query_list_rules.append(self.rule.vals.copy())

        if self.debug: print(query_list_rules)

        err = self._run_sql(self.rule.insert_sql(all=True), query_list_rules, many=True)
        if err != 0:
            if self.gui: yield -32, err
            self._msg(-32, err)
            return err

        if args.get('commit',True):
            self.sqlite_conn.commit()
            self._refresh_data()

        if self.debug: print('Rules learned')
        self.unlock(ignore=args.get('ignore_lock',False))
        


    def add_rule(self, fields:dict, **args):
        for _ in self.g_add_rule(fields, **args): pass
    def g_add_rule(self, fields:dict, **args):
        """ Add a rule to database """
        # We assume that by defult rule should flag
        ignore_lock = args.get('ignore_lock',False)

     
        if fields.get('flag') in (None,0): fields['flag'] = None
        else: fields['flag'] = scast(fields.get('flag'), int, 0)
        fields['case_insensitive'] = fields.get('case_ins', False)
        fields['learned'] = 0

        self.rule.clear()
        self.rule.merge(fields)

        # Check if REGEX is valid to avoid breaking rule matching later
        self.rule['weight'] = scast(self.rule['weight'], float, None)
        self.rule['type'] = scast(self.rule['type'], int, None)
        
        if self.rule['type'] == 3 and not check_if_regex(self.rule['string']):
            if self.gui: yield -9, self.rule['string']
            self._msg(-9, self.rule['string'])
            return -1
        if self.rule['weight'] == None:
            if self.gui: yield -26
            self._msg(-26, None)
            return -1
        else: self.rule['weight'] = scast(self.rule.get('weight'), float, 0)

        self.rule['field_id'] = self.resolve_field(self.rule.get('field_id'))
        if self.rule['field_id'] == False:
            if self.gui: yield -31, self.rule['field_id']
            self._msg(-31, self.rule['field_id'])
            return -1

        if self.rule['type'] not in (0,1,2,3):
            if self.gui: yield -30
            self._msg(-30)
            return -1
        
        feed_id = self.resolve_feed(self.rule.get('feed_id'), load=False)
        if feed_id == False:
            feed_id = self.resolve_feed(self.rule.get('feed_id'), load=False)
        if feed_id == False:
            if self.gui: yield -3, self.rule.get('feed_id')
        else:
            self.rule['feed_id'] = feed_id


        self.rule.clean()
        if self.locked(ignore=ignore_lock):
            if self.gui: yield -2, None
            return -2
        err = self._run_sql(self.rule.insert_sql(all=True), self.rule.vals) 
        if err != 0:
            if self.gui: yield -32, err
            self._msg(-32, err)
            self.sqlite_conn.rollback()
            self.unlock(ignore=ignore_lock)
            return -1

        self.last_rule_id = self.sqlite_cur.lastrowid
        self.sqlite_conn.commit()
        self.unlock(ignore=ignore_lock)
        if self.gui: yield 18, self.last_rule_id
        self._msg(18, self.last_rule_id)    
        self._refresh_data()



    def del_rule(self,id:int, **args):
        for _ in self.g_del_rule(id, **args): pass
    def g_del_rule(self,id:int, **args):
        """ Delete rule by ID """
        if self.locked(ignore=args.get('ignore_lock',False)):
            if self.gui: yield -2, None
            return -2
        err = self._run_sql("delete from rules where id = ? and learned <> 1", (id,) )
        if err != 0:
            if self.gui: yield -32, err
            self._msg(-32, err)
            self.sqlite_conn.rollback()
            self.unlock(ignore=args.get('ignore_lock',False))
            return -1
        a = self.sqlite_cur.rowcount
        self.sqlite_conn.commit()
        self.unlock(ignore=args.get('ignore_lock',False))
        if a > 0:
            if self.gui: yield 19, id
            self._msg(19, id)
        else:
            if self.gui: yield 7
            self._msg(7, None)
        self._refresh_data()





    def edit_rule(self, id:int, fields:dict, **args):
        for _ in self.g_edit_rule(id, fields, **args): pass
    def g_edit_rule(self, id:int, fields:dict, **args):
        """ Wrapper for editing/updating a rule """
        sets = 'set'
        vals = {}
        flds = []
        self.rule.populate(self.sqlite_cur.execute("""select * from rules where id = ?""", (id,) ).fetchone())
        if self.rule['id'] == None:
            if self.gui: yield -47, id
            self._msg(-47,id)
            return -1
        if self.rule['learned'] in (1,2):
            if self.gui: yield -46 
            self._msg(-46)
            return -1

        for field in fields.keys():
            field = scast(field, str, None)
            if field == None: continue
            if field.lower() == 'id': continue
            value = fields[field]
            
            if field not in RULES_SQL_TABLE: 
                if self.gui: yield -29, field
                self._msg(-29, field)
                continue
            
            if value in ('null','NULL','Null'): value=None

            if field == 'weight':
                value = scast(value, float, None)
                if value == None:
                    if self.gui: yield -26
                    self._msg(-26, None)
                    return -1

            if field == 'flag':
                value = scast(value, int, None)

            if field == 'type': 
                value = scast(value, int, 0)
                if value not in (0,1,2,3):
                    if self.gui: yield -30
                    self._msg(-30)
                    continue

            if field in ('string','type',) and (self.rule['type'] == 3 or fields.get('type') == 3):
                if not check_if_regex(self.rule['string']):
                    if self.gui: yield -9, self.rule['string']
                    self._msg(-9, self.rule['string'])
                    continue                     
                
            if field == 'field_id': 
                value = self.resolve_field(value)
                if value == False:
                    if self.gui: yield -31
                    continue
            
            if field == 'feed_id':
                val = self.resolve_feed(value)
                if val == False:
                    val = self.resolve_category(value)
                if val == False:
                    if self.gui: -3
                    continue    
                else: value = val

            if self.rule[field] != value:
                sets = f"""{sets} {field} = :{field},"""
                vals[field] = value
                flds.append(field)

        if len(flds) > 0:
            sets = sets[:-1]
            sql = f"""update rules\n{sets}\nwhere id = :id"""
            vals['id'] = id
            if self.locked(ignore=args.get('ignore_lock',False)): 
                if self.gui: yield -2
                return -2

            err = self._run_sql(sql, vals)
            if err != 0:
                if self.gui: yield -32, err
                self._msg(-32, err)
                self.sqlite_conn.rollback()
                self.unlock(ignore=args.get('ignore_lock',False))
                return -1

            a = self.sqlite_cur.rowcount
            self.sqlite_conn.commit()
        else: a = 0

        if a > 0:
            for f in flds: 
                if self.gui: yield 48, f'{scast(id, str, "<<UNKNOWN>>")}: {f} -> {scast(vals[f],str,"NULL")}'
                self._msg(48, f'{scast(id, str, "<<UNKNOWN>>")}: {f} -> {scast(vals[f],str,"NULL")}')
            if len(flds) > 1:
                if self.gui: yield 47
                self._msg(47,None)
        else:
            if self.gui: yield 7, None
            self._msg(7, None)
        self.unlock(ignore=args.get('ignore_lock',False))
        return 0
                        






######################################
#       Fetching


    def update_last(self, started):
        """ Change last check timestamp """
        self.sqlite_cur.execute("""insert into params values('last', ?)""", (started,) )
        self.sqlite_conn.commit()

    def get_last(self):
        """ Get timestamp of last news check """
        last = self.sqlite_cur.execute("select max(val) from params where name = 'last'").fetchone()
        if last == (None,): return 0
        else: return last[0]




    def _ling(self, entry, **args):
        """ Linguistic processing for an entry """
        learn = args.get('learn',False)
        stats = args.get('stats',True)
        rank = args.get('rank',True)
        force = args.get('force',False)

        
        if stats or (learn and coalesce(entry['read'],0) > 0) or (learn and force):

            self.LP.charset = entry['charset'] # Give a charset should language detection is needed
            self.LP.process_fields(entry.tuplify(filter=LING_LIST1), learn=learn, index=True, stats=stats) # This is the main engine
            entry['tokens'] = nullif(self.LP.token_str,'')
            entry['tokens_raw'] = nullif(self.LP.raw_token_str,'')
            # Merge document statistics
            entry.merge(self.LP.stats)
                                                                                    
        else:
            self.LP.set_model(self.entry['lang'])

        # If language was detected it would be a waste not to record it 
        if entry['lang'] == None: entry['lang'] = self.LP.get_model()

        if rank: 
            (entry['importance'], entry['flag']) = self.QP.match_rules(entry.tuplify(filter=LING_LIST2), entry['weight'], self.rules)
        if learn:
            if force or coalesce(entry['read'],0) > 0:
                self.learn_rules(self.LP.features, context_id=entry['id'], lang=entry['lang'], ignore_lock=True)

        return entry

        



    def fetch(self, **args):
        for _ in self.g_fetch(**args): pass
    def g_fetch(self, **args):
        """ Check for news taking into account specified intervals and defaults as well as ETags and Modified tags"""
        if self.locked(): 
            yield -2, None
            return -2

        feed_ids = scast(args.get('ids'), tuple, None)
        feed_id = scast(args.get('id'), int, 0)

        force = args.get('force', False)
        ignore_interval = args.get('ignore_interval', True)

        skip_ling = args.get('skip_ling',False)
        update_only = args.get('update_only', False)

        started = int(datetime.now().timestamp())
        self.new_items = 0

        tech_counter = 0

        handler = None
        # Data handlers - to expand in the future...
        rss_handler = FeedexRSSHandler(self.config, gui=self.gui, debug=self.debug)
        twitter_handler = FeedexTwitterHandler(self.config, gui=self.gui, debug=self.debug)
        
        for feed in self.feeds:

            self.feed.clear()
            self.feed.populate(feed)

            # Check for processing conditions...
            if self.feed['deleted'] == 1 and not update_only and feed_id == 0: continue
            if self.feed['interval'] == 0 and feed_id == 0 and feed_ids == None: continue # Setting interval to 0 deactivates automated fetching
            if feed_id != 0 and feed_id != self.feed['id']: continue
            if feed_ids != None and self.feed['id'] not in feed_ids: continue
            if self.feed['is_category'] not in (0,None) or self.feed['handler'] in ('local'): continue
            # Ignore unhealthy feeds...
            if scast(self.feed['error'],int,0) >= self.config.get('error_threshold',5) and not args.get('ignore_errors',False):
                if self.gui: yield 27, feed_name_cli(self.feed)
                self._msg(27, feed_name_cli(self.feed))
                continue

            #Check if time difference exceeds the interval
            last_checked = scast(self.feed['lastchecked'], int, 0)
            if not ignore_interval:
                diff = (started - last_checked)/60
                if diff < scast(self.feed['interval'], int, self.config.get('default_feed_interval',120)):
                    if self.debug: print(f'Feed {self.feed["id"]} ignored (interval: {self.feed["interval"]}, diff: {diff})')
                    continue

            if self.gui: yield 21, feed_name_cli(self.feed)
            else: self._msg(21, feed_name_cli(self.feed))

            entries_sql = []

            now = datetime.now()
            now_raw = int(now.timestamp())
            last_read = scast(self.feed['lastread'], int, 0)
            
            # Choose appropriate handler           
            if self.feed['handler'] == 'rss':
                handler = rss_handler
            elif self.feed['handler'] == 'twitter':
                handler = twitter_handler
            else:
                if self.gui: yield -21, self.feed['handler']
                self._msg(-21, self.feed['handler'])
                continue     


            if not update_only:

                pguids = self.sqlite_cur.execute("""select distinct guid from entries e where e.feed_id = ?""", (self.feed['id'],) ).fetchall()
                if handler.compare_links:
                    plinks = self.sqlite_cur.execute("""select distinct link from entries e where e.feed_id = ?""", (self.feed['id'],) ).fetchall()
                else:
                    plinks = ()

                for item in handler.fetch(self.feed, force=force, pguids=pguids, plinks=plinks, last_read=last_read, last_checked=last_checked):
                    
                    if isinstance(item, SQLContainer):
                        self.new_items += 1
                        if not skip_ling:
                            item = self._ling(item).vals.copy()
                            if isinstance(item, dict):
                                entries_sql.append(item)
                            else:
                                if self.gui: yield -45, item
                                self._msg(-45,item)
                        else:
                            entries_sql.append(item.vals.copy())

                        # Track new entries and take care of massive insets by dividing them into parts
                        tech_counter += 1
                        if tech_counter >= self.config.get('max_items_per_transaction', 300):
                            err = self._run_sql(self.entry.insert_sql(all=True), entries_sql, many=True)
                            if err != 0:
                                if self.gui: yield -32, err
                                self._msg(-32, err)
                            else: 
                                entries_sql = []
                                self.sqlite_conn.commit()
                            tech_counter = 0  

                    elif item != (0,None):
                        if self.gui: yield item
                        self._msg(slist(item,0,0), slist(item,1,None))


            else:
                msg = handler.download(self.feed['url'], force=force, etag=self.feed['etag'], modified=self.feed['modified'], login=self.feed['login'], password=self.feed['passwd'], auth=self.feed['auth'])
                if msg != (0, None):
                    if self.gui: yield msg
                    self._msg(slist(msg,0,0), slist(msg,1,None))



            if handler.error:
                # Save info about errors if they occurred
                if update_only:
                    self.sqlite_cur.execute("""update feeds set http_status = :status, error = coalesce(error,0)+1 where id = :id""", {'status': handler.status, 'id': self.feed['id']} )
                else:
                    self.sqlite_cur.execute("""update feeds set lastchecked = :now, http_status = :status, error = coalesce(error,0)+1 where id = :id""", {'now':now_raw, 'status':handler.status, 'id': self.feed['id']} )
                self.sqlite_conn.commit()
                continue

            else:				
                #Update feed last checked date and other data
                if update_only:
                    self.sqlite_cur.execute("""update feeds set http_status = :status, error = 0  where id = :id""", {'status':handler.status, 'id': self.feed['id']} )
                else:
                    self.sqlite_cur.execute("""update feeds set lastread = :now, lastchecked = :now, etag = :etag, modified = :modified, http_status = :status, error = 0  where id = :id""", 
                    {'now':now_raw, 'etag':handler.etag, 'modified':handler.modified, 'status':handler.status, 'id':self.feed['id']} )
    
            # Inform about redirect
            if handler.redirected:
                if self.gui: yield 26, self.feed['url']
                self._msg(26, self.feed['url'])

            # Save permanent redirects to DB
            if handler.feed_raw.get('href',None) != self.feed['url'] and handler.status == 301:
                self.feed['url'] = rss_handler.feed_raw.get('href',None)
                if not update_only and args.get('save_perm_redirects',True):
                    self.sqlite_cur.execute('update feeds set url = :url where id = :id', {'url':self.feed['url'], 'id':self.feed['id']} )    

            # Push to DB
            err = self._run_sql(self.entry.insert_sql(all=True), entries_sql, many=True)
            if err != 0:
                if self.gui: yield -32, err
                self._msg(-32, err)
            self.sqlite_conn.commit()


            # Autoupdate metadata if needed or specified by 'forced' or 'update_only'
            if (scast(self.feed['autoupdate'], int, 0) == 1 or update_only) and not handler.no_updates:

                if self.debug: yield 23, feed_name_cli(self.feed)
                self._msg(23, feed_name_cli(self.feed))

                msg = handler.update(self.feed, ignore_images=self.config.get('ignore_images',False))
                if msg != (0, None):
                    if self.debug: yield msg
                    self._msg(msg)
                updated_feed = handler.feed

                if updated_feed == -1:
                    if self.debug: yield -20, feed_name_cli(self.feed)
                    self._msg(-20, feed_name_cli(self.feed))
                    continue
                elif updated_feed == 0:
                    continue

                err = self._run_sql(updated_feed.update_sql(wheres=f'id = :id'), updated_feed.vals)
                if err != 0:
                    if self.gui: yield -32, err
                    self._msg(-32, err)
                self.sqlite_conn.commit()
        
                if self.gui: yield 24, feed_name_cli(self.feed)
                self._msg(24, feed_name_cli(self.feed))

            # Stop if this was the specified feed...
            if feed_id != 0:
                break


        if self.new_items > 0:
            self.update_last(started)
        if args.get('update_stats',True):
            if self.new_items > 0:
                self._update_stats()

        self.unlock()
        if not update_only:
            if self.gui: yield 22, self.new_items
        else:
            if self.gui: yield 28

        return 0







#################################################
# Utilities 

    def clear_history(self, **args):
        for _ in self.g_clear_history(**args): pass
    def g_clear_history(self, **args):
        """ Clears search history """
        if self.locked(ignore=args.get('ignore_lock',False)):
            if self.gui: yield -2, None
            return -2

        items_deleted = 0
        err = self._run_sql("delete from search_history",())
        if err != 0:
            if self.gui: yield -32, err
            self._msg(-32, err)
        else:
            items_deleted = self.sqlite_cur.rowcount
            self.sqlite_conn.commit()

        self.unlock(ignore=args.get('ignore_lock',False))

        if self.gui: yield 53, items_deleted
        self._msg(53, items_deleted)

        self._refresh_data()
        return 0
        
        


    def delete_query_rules(self, **args):
        for _ in self.g_delete_query_rules(**args): pass
    def g_delete_query_rules(self, **args): 
        """ Deletes all rules comming from searches """
        if self.locked(ignore=args.get('ignore_lock',False)):
            if self.gui: yield -2, None
            return -2

        items_deleted = 0
        err = self._run_sql("delete from rules where learned = 2",[])
        if err != 0:
            if self.gui: yield -32, err
            self._msg(-32, err)
        else:
            items_deleted = self.sqlite_cur.rowcount
            self.sqlite_conn.commit()

        self.unlock(ignore=args.get('ignore_lock',False))

        if self.gui: yield 54, items_deleted
        self._msg(54, items_deleted)

        self._refresh_data()
        return 0




    def delete_learned_rules(self, **args):
        for _ in self.g_delete_learned_rules(**args): pass
    def g_delete_learned_rules(self, **args):
        """ Deletes all learned rules """
        if self.locked(ignore=args.get('ignore_lock',False)):
            if self.gui: yield -2, None
            return -2
        
        if self.gui: yield 67
        self._msg(67, None)

        err = self._run_sql("""delete from rules where learned = 1""",[])
        if err != 0:
            if self.gui: yield -32, err
            self._msg(-32, err)
            self.unlock(ignore=args.get('ignore_lock',False))
            return -1
        else:
            deleted_rules = self.sqlite_cur.rowcount
            self.sqlite_conn.commit()
            self.unlock(ignore=args.get('ignore_lock',False))

            if self.gui: yield 68, deleted_rules
            self._msg(68, deleted_rules)
            self._refresh_data()
            return 0




    def empty_trash(self, **args):
        for _ in self.g_empty_trash(**args): pass
    def g_empty_trash(self, **args):
        """ Removes all deleted items permanently """
        if self.locked(ignore=args.get('ignore_lock',False)):
            if self.gui: yield -2, None
            return -2

        if self.gui: yield 51
        self._msg(51, None)

        # Delete permanently with all data
        rules_deleted = 0
        entries_deleted = 0
        feeds_deleted = 0
        err = self._run_sql(EMPTY_TRASH_RULES_SQL,[])
        rules_deleted = self.sqlite_cur.rowcount
        if err == 0: 
            err = self._run_sql(EMPTY_TRASH_ENTRIES_SQL,[])
            entries_deleted = self.sqlite_cur.rowcount
        if err == 0: err = self._run_sql(EMPTY_TRASH_FEEDS_SQL1,[])
        if err == 0:
            feeds_to_remove = self.sqlite_cur.execute('select id from feeds where deleted = 1').fetchall()
            for f in feeds_to_remove:
                if self.icons == {}: self._load_icons()
                icon = self.icons.get(f)
                if icon != None and icon.startswith(f'{FEEDEX_ICON_PATH}/feed_') and os.path.isfile(icon): os.remove(icon)
                  
        if err == 0: 
            err = self._run_sql(EMPTY_TRASH_FEEDS_SQL2,[])
            feeds_deleted = self.sqlite_cur.rowcount
    
        if err != 0:
            if self.gui: yield -32, err
            self._msg(-32, err)
        else:
            self.sqlite_conn.commit()
        self.unlock(ignore=args.get('ignore_lock',False))
        
        if self.gui: yield 52, f'{feeds_deleted} feeds, {entries_deleted} entries, {rules_deleted} rules'
        self._msg(52, f'{feeds_deleted} feeds, {entries_deleted} entries, {rules_deleted} rules')

        self._refresh_data()
        return 0




    def recalculate(self, **args):
        """ Utility to recalculate, retokenize, relearn, etc. """
        if self.locked(ignore=args.get('ignore_lock',False)):
            return -2

        verbose = args.get('verbose',True)
        entry_id = scast(args.get('id'), int, 0)
        learn = args.get('learn',False)
        rank = args.get('rank',False)
        stats = args.get('stats',False)
        force = args.get('force',False)

        if rank and verbose:
            self._log(False,"Ranking according to saved rules...")
        if learn and verbose:
            self._log(False,"Learning features ...")
        if stats and verbose:
            self._log(False,"Recalculating entries' stats ...")
            
        if entry_id == 0:
            if verbose:
                self._log(False, "Recalculating all entries")
            entries = self.sqlite_cur.execute("select * from entries").fetchall()
        else:
            if verbose:
                self._log(False, "Recalculating for entry:", str(args.get('id')))
            entries = self.sqlite_cur.execute("select * from entries where id=?", (entry_id,)).fetchall()


        for entry in entries:
    
            self.entry.populate(entry)
            if verbose: print(f"Processing entry: {self.entry['id']}")
    
            self.entry = self._ling(self.entry, learn=learn, stats=stats, rank=rank, force=force)
            
            if not stats and rank:
                err = self._run_sql("""update entries set importance = :importance, flag = :flag where id = :id""",
                {'importance': self.entry['importance'], 'flag': self.entry['flag'], 'id': self.entry['id']} )            
                if err != 0: self._msg(-32, err)
            if stats:
                vals = self.entry.filter(RECALCULATE_FILTER)
                vals['id'] = self.entry['id']
                err = self._run_sql(self.entry.update_sql(filter=RECALCULATE_FILTER, wheres='id = :id'), vals)
                if err != 0: self._msg(-32, err)

            if self.debug: print("Done.")
    


        self.sqlite_conn.commit()
    
        if verbose:
            self._log(False, "Recalculation finished")

        self._update_stats()
        if learn:
            self._refresh_data()
        self.unlock(ignore=args.get('ignore_lock',False))
        return 0




    def db_stats(self, **args):
        """ Displays database statistics """
        version = self.sqlite_cur.execute("select val from params where name='version'").fetchone()
        doc_count = self.sqlite_cur.execute("select val from params where name='doc_count'").fetchone()
        avg_weight = self.sqlite_cur.execute("select val from params where name='avg_weight'").fetchone()
        last_update = self.sqlite_cur.execute("select max(val) from params where name='last'").fetchone()
        rule_count = self.sqlite_cur.execute("select count(id) from rules where learned=1").fetchone()
        keyword_count = self.sqlite_cur.execute("select count(id) from rules where learned=0").fetchone()
        feed_count = self.sqlite_cur.execute("select count(id) from feeds").fetchone()

        lock = self.sqlite_cur.execute("select * from params where name = 'lock'").fetchone()
        if lock != None:
            lock=True     
        else:
            lock=False

        last_time = scast(slist(last_update,0,None),int,None)
        if last_time != None:
            last_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(last_time))
        else:
            last_time_str = 'NOT FOUND'

        if args.get('markup',False) and not args.get('print',True):
            mb = '<b>'
            me = '</b>'
        else:
            mb = ''
            me = ''

        stat_str=f"""

Statistics for database: {mb}{self.config.get('db_path','<<EMPTY>>')}{me}

FEEDEX version:         {mb}{slist(version,0,'NOT FOUND')}{me}
Entry count:            {mb}{slist(doc_count,0,'NOT FOUND')}{me}
Avg entry weight:       {mb}{slist(avg_weight,0,'NOT FOUND')}{me}

Last news update:       {mb}{last_time_str}{me}

Learned rule count:     {mb}{slist(rule_count,0,'0')}{me}
Manual rule count:       {mb}{slist(keyword_count,0,'0')}{me}

Feed count:             {mb}{slist(feed_count,0,'0')}{me}


"""
        if lock:
            stat_str=f"{stat_str}DATABASE LOCKED!"
        
        if self.check_due_maintenance():
            stat_str=f"{stat_str}DATABASE MAINTENANCE ADVISED!\nUse {mb}feedex --db-maintenance{me} command"
                    
        stat_str=f"{stat_str}\n\n"

        if args.get('print',True):
            help_print(stat_str)
        
        return stat_str




    def check_due_maintenance(self):
        last_maint = slist(self.sqlite_cur.execute("""select coalesce(val,0) from params where name = 'last_maintenance' """).fetchone(), 0, 0)
        doc_count = self.get_doc_count()

        if doc_count - last_maint >= 50000: return True
        else: return False


    def db_maintenance(self, **args):
        for _ in self.g_db_maintenance(**args): pass        
    def g_db_maintenance(self, **args):
        """ Performs database maintenance to increase performance at large sizes """
        if self.locked(ignore=args.get('ignore_lock',False)):
            if self.gui: yield -2, None
            return -2

        if self.gui: yield 69
        self._msg(69, None)

        if self.gui: yield 70
        self._msg(70, None)
        self.sqlite_cur.execute('VACUUM')
        if self.gui: yield 71
        self._msg(71, None)
        self.sqlite_cur.execute('ANALYZE')
        if self.gui: yield 72
        self._msg(72, None)
        self.sqlite_cur.execute('REINDEX')

        doc_count = self.get_doc_count()
        self.sqlite_cur.execute("""delete from params where name = 'last_maintenance'""")
        self.sqlite_cur.execute("""insert into params values('last_maintenance',?)""", (doc_count,))
        self.sqlite_conn.commit

        if self.gui: yield 73
        self._msg(73, None)






    def port_data(self, ex:bool, pfile:str, mode:int):
        """ Handles exporting and importing data to/from text files """
        if ex:
            if os.path.isfile(pfile):
                self._msg(-37, pfile)
                return -1

            if mode == 'feeds':
                print("Exporting feeds...")
                ldata = list(self.feeds)
            elif mode == 'rules':
                print("Exporting rules...")
                ldata = list(self.sqlite_cur.execute("select * from rules").fetchall())
            
            with open(pfile, "w") as f:
                json.dump(ldata, f)
                #f.write(serialize_table(ldata))

            print('Done')

        else:
            if not os.path.isfile(pfile):
                self._msg(-38, pfile)
                return -1
            
            with open(pfile, "r") as f:
                ldata = json.load(f)
                #ldata = deserialize_table( f.read())


            if mode == 'feeds':
                print("Importing feeds...")
                # Max ID will be added to imported ids to prevent ID collision
                max_id = self.sqlite_cur.execute('select max(id) from feeds').fetchone()
                max_id = slist(max_id, 0, 0)
                ldata_sql = []
                if max_id in (None, (None), ()): max_id = 0
                if self.debug: print(f'Max ID: {max_id}') 
                for l in ldata:
                    self.feed.populate(l)
                    if self.feed['parent_id'] != None: self.feed['parent_id'] = self.feed['parent_id'] + max_id
                    self.feed['id'] = coalesce(self.feed['id'],0) + max_id
                    ldata_sql.append(self.feed.vals.copy())
                
                err = self._run_sql(self.feed.insert_sql(all=True), ldata_sql, many=True)
                if err != 0:
                    self._msg(-32, err)
                    self._msg(-35, pfile)
                else:
                    self.sqlite_conn.commit()
                    self._msg(55, pfile)
 

            elif mode == 'rules':
                print("Importing rules...")
                # Nullify IDs to avoid conflicts
                ldata_sql = []
                for l in ldata:
                    self.rule.populate(l)
                    self.rule['id'] = None
                    ldata_sql.append(self.rule.vals.copy())

                err = self._run_sql(self.rule.insert_sql(all=True), ldata_sql, many=True)
                if err != 0: 
                    self._msg(-32, err)
                    self._msg(-36, pfile)
                else:
                    self.sqlite_conn.commit()            
                    self._msg(56, pfile)



