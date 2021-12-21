# -*- coding: utf-8 -*-
""" 
Main engine for Feedex news reader. Database interface and REST handling, main Fetching mechanism, interface with ling processor

"""


from snowballstemmer import norwegian_stemmer
from feedex_headers import *









class Feeder:
    """ Main engine for Feedex. Handles SQLite3 interface, feed and entry data"""

    def __init__(self, **kargs):

        # Main configuration
        self.config = kargs.get('config', DEFAULT_CONFIG)
        self.main_thread = kargs.get('main_thread', False) # Only instance in main thread is allowed actions like updating DB version, creating DB etc.

        # Overload config passed in arguments
        self.debug = kargs.get('debug',False) # Triggers additional info at runtime
        self.timeout = kargs.get('timeout', self.config.get('timeout',15)) # Wait time if DB is locked

        self.ignore_images = kargs.get('ignore_images', self.config.get('ignore_images',False))
        self.wait_indef = kargs.get('wait_indef',False)

        # This tells us if the GUI is running
        self.gui = kargs.get('gui',False)
        # Load icons on init?
        self.load_icons = kargs.get('load_icons', False)

        # Global db lock flag
        self.ignore_lock = kargs.get('ignore_lock',False)

        # Id it a single CLI run? Needed for reloading flag
        self.single_run = kargs.get('single_run',True)

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
        if self.db_status != 0: 
            self._log(True, self.db_status)
            return -1
        self._refresh_data(first_run=True) 

        self.icons = {} # List of icons for feeds
        if self.load_icons: self.do_load_icons()

        # initialize linguistic processor for tokenizing and stemming
        self.LP = LingProcessor(**kargs) 
        # And query parser ...
        if not kargs.get('no_qp', False):
            self.QP = FeederQueryParser(self, **kargs)

        # new item count
        self.new_items = 0

        # SQLite rowcount etc
        self.rowcount = 0
        self.lastrowid = 0

    
        


    def _log(self, err:bool, *args, **kargs):
        """Handle adding log entry (add timestamp or output to stderr if specified by true first argument)"""
        if err: err = 'ERROR: '
        else: err=''
        log_str = ' '.join(args)
        log_str = f"{err}{str(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))}\t{log_str}\n"

        try:
            with open(self.config.get('log'),'a') as logf:
                logf.write(log_str)
        except (OSError, TypeError) as e: 
            sys.stderr.write(f"Could not open log file {self.config.get('log','<<<EMPTY>>>')}: {e}\n")
			
        



    def _connect_sqlite(self): 
        for m in self._g_connect_sqlite(): cli_msg(m)
    def _g_connect_sqlite(self):
        """ Connect to SQLite and handle errors """
        db_path = self.config.get('db_path','')
        first_run = False # Trigger if DB is not present

        # Copy database from shared dir to local dir if not present (e.g. fresh install)
        if not os.path.isfile(db_path):
            if not self.main_thread: 
                self.db_status = f'Could not connect to {db_path}'
                return -1

            first_run = True
            yield 0, 'SQLite Database not found. Creating new one at %a', db_path
            # Create directory if needed
            db_dir = os.path.dirname(db_path)
            if not os.path.isdir(db_dir):
                err = os.makedirs(db_dir)
                if err == 0: yield 0, 'Folder %a created...', db_dir
                else: 
                    yield -1, 'Error creating DB foler %a', db_dir
                    return -1
        try:
            self.sqlite_conn = sqlite3.connect(db_path)
            self.sqlite_cur = self.sqlite_conn.cursor()
        except (OSError, sqlite3.Error) as e: 
            yield -2, 'DB connection error: %a', e
            self.db_status = (f'Error connecting to: {db_path}')
            return -2

        if self.debug: print(f"Connected to {db_path}")

        if first_run:

            # Run DDL on fresh DB
            try:
                with open(f'{FEEDEX_SYS_SHARED_PATH}{DIR_SEP}data{DIR_SEP}db_scripts{DIR_SEP}base{DIR_SEP}feedex_db_ddl.sql', 'r') as sql:
                    sql_ddl = sql.read()
                self.sqlite_cur.executescript(sql_ddl)
                self.sqlite_conn.commit()
            except (OSError, sqlite3.Error) as e:
                yield -2, 'Error writing DDL scripts to database! %a', e
                self.db_status = 'Error writing DDL scripts to database! {e}'
                return -2

            yield 0, 'Database structure created'

            try:
                with open(f'{FEEDEX_SYS_SHARED_PATH}{DIR_SEP}data{DIR_SEP}db_scripts{DIR_SEP}base{DIR_SEP}feedex_db_defaults.sql', 'r') as sql:
                    sql_ddl = sql.read()
                self.sqlite_cur.executescript(sql_ddl)
                self.sqlite_conn.commit()
            except (OSError, sqlite3.Error) as e:
                yield -2, 'Error writing defaults to database: %a', e
                self.db_status = 'Error writing defaults to database: {e}'
                return -2

            yield 0, 'Added some defaults...'

        # This is for queries and needs to be done
        self.sqlite_cur.execute("PRAGMA case_sensitive_like=true;")
        self.sqlite_conn.commit()

        # Checking versions and updating if needed
        version = slist(self.sqlite_cur.execute("select val from params where name = 'version'").fetchone(), 0, None)
        ver_diff = check_version(version, FEEDEX_VERSION)
        if ver_diff == -1:
            yield -1, 'Application version too old for %a Database! Aborting', db_path
            self.db_status = f'Application version too old for {db_path} Database! Aborting'
            return -1    

        elif ver_diff == 1:

            if not self.main_thread:
                self.db_status = 'Cannot update DB from this instance'
                return -1

            yield 0, 'Database %a version too old... Updating...', db_path

            #Run DDL scripts if file is fresly created and then add some default data to tables (feeds and prefixes) """
            # ... and attempt to update it ...

            # ... make a clean backup
            self.sqlite_conn.rollback()
            self.sqlite_conn.close()
            try:
                copyfile(db_path, f'{db_path }.bak')
            except OSError as e:
                self.db_status = f'Error creating database backup to {db_path}.bak: {e}'
                yield -1, 'Error creating database backup to {db_path}.bak: %a', e
                return -1
            
            try:
                self.sqlite_conn = sqlite3.connect(db_path)
                self.sqlite_cur = self.sqlite_conn.cursor()
            except (OSError, sqlite3.Error) as e: 
                yield -2, 'DB reconnection error: %a', e
                self.db_status = (f'DB reconnection error: {e}')
                return -2


            for d in sorted( os.listdir(f'{FEEDEX_SYS_SHARED_PATH}{DIR_SEP}data{DIR_SEP}db_scripts') ):

                if d != 'base' and d <= FEEDEX_VERSION:
                    ver_path = os.path.join(f'{FEEDEX_SYS_SHARED_PATH}{DIR_SEP}data{DIR_SEP}db_scripts',d)
                    for f in sorted( os.listdir(ver_path) ):
                        scr_path = os.path.join(ver_path, f)
                        if os.path.isfile(scr_path):
                            yield 0, 'Running update script... %a', scr_path 
                            try:
                                with open(scr_path) as sql_file:
                                    update_script = sql_file.read()
                                self.sqlite_cur.executescript(update_script)
                                self.sqlite_conn.commit()
                            except (OSError, sqlite3.Error) as e:
                                yield -2, 'Error running %a script! Attempting to restore database', scr_path
                                sys.stderr.write(e)
                                # Restore backup...
                                self.sqlite_conn.rollback()
                                self.sqlite_conn.close()
                                try:
                                    os.remove(db_path)
                                    copyfile(db_path + '.bak', db_path)
                                except OSError as e:
                                    self._log(True, f'Error restoring {db_path} database! {e}' )
                                    yield -1, 'Error restoring %a database! {e}', db_path
                                finally: 
                                    self._log(False, f'Database {db_path} resotred ...')
                                    yield 0, 'Database %a restored ...', db_path

                                self.db_status = 'Version update error'
                                return -1
            
            yield 0, 'Database updated successfully'

            





    def _reset_connection(self, **kargs):
        """ Reset connection to database, rollback all hanging transactions and unlock"""
        self.sqlite_conn.rollback()
        self.sqlite_conn.close()
        self._connect_sqlite()
        self.unlock()

        if kargs.get('log',False): self._log(False, "Connection reset")





    # Database lock and handling it with timeout - waiting for availability
    def lock(self, **kargs):
        """ Locks DB """
        self.sqlite_cur.execute("insert into params values('lock', 1)")
        self.sqlite_conn.commit()

    def unlock(self, **kargs):
        """ Unlocks DB """
        if kargs.get('ignore',False):
            return False
        self.sqlite_cur.execute("delete from params where name='lock'")
        self.sqlite_conn.commit()

    
    def locked(self, **kargs):
        """ Checks if DB is locked and waits the timeout checking for availability before aborting"""
        if kargs.get('ignore',False): return False
        if self.ignore_lock: return False

        if self.gui: timeout = 10
        else: timeout = self.timeout

        tm = 0
        while tm <= timeout or self.wait_indef:
            tm = tm + 1
            time.sleep(1)
            lock = self.sqlite_cur.execute("select * from params where name = 'lock'").fetchone()
            if lock is not None: sys.stderr.write(f"Database locked... Waiting ... {tm}")     
            else:
                self.lock()
                return False

        sys.stderr.write("Timeout reached...")
        return True




    def _run_sql(self, query:str, vals:list, **kargs):
        """ Safely run a SQL insert/update """
        many = kargs.get('many',False)
        try:
            if many: self.sqlite_cur.executemany(query, vals)
            else: self.sqlite_cur.execute(query, vals)
            self.rowcount = self.sqlite_cur.rowcount
            self.lastrowid = self.sqlite_cur.lastrowid
            return 0
        except sqlite3.Error as e:
            if hasattr(e, 'message'): return e.message
            else: return e

    # Below are 2 methods of safely inserting to and updating
    # All actions on DB should be performed using them!
    def _run_sql_lock(self, query:str, vals:list, **kargs):
        """ Run SQL with locking and error catching """
        if self.locked(ignore=kargs.get('ignore_lock', False)): return 'Database busy'
        e = self._run_sql(query, vals, **kargs)
        if e != 0: self.sqlite_conn.rollback()
        self.unlock()
        return e

    def _run_sql_multi_lock(self, qs:list, **kargs):
        """ Run list of queries with locking """
        if self.locked(ignore=kargs.get('ignore_lock', False)): return 'Datbase busy'
        e = 0
        for q in qs:
            e = self._run_sql(q[0], q[1], many=False)
            if e != 0: break

        if e != 0: self.sqlite_conn.rollback()
        self.unlock()
        return e




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


    def load_rules(self, **kargs):
        """Get learned and saved rules from DB"""
        no_limit = kargs.get('no_limit',False)
        limit = scast(self.config.get('rule_limit'), int, 50000)

        if not self.config.get('use_keyword_learning', True):  #This config flag tells if we should learn and rank autoatically or by manual rules only
            self.rules = self.sqlite_cur.execute(GET_RULES_NL_SQL).fetchall()
        else:
            if no_limit or limit == 0:
                self.rules = self.sqlite_cur.execute(GET_RULES_SQL).fetchall()
            else:
                self.rules = self.sqlite_cur.execute(f'{GET_RULES_SQL}LIMIT ?', (limit,) ).fetchall()           
 
        # If this is a first run - update them also for ling processor
        if not kargs.get('first_run',False): self.LP.rules = self.rules




    def resolve_category(self, val:str, **kargs):
        """ Resolve entry type depending on whether ID or name was given"""
        if val is None: return None
        load = kargs.get('load', False)
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
        return -1

    def resolve_feed(self, val:int, **kargs):
        """ check if feed with given ID is present """
        if val is None: return None
        load = kargs.get('load', False)
        val = scast(val, int, None)
        if val is None: return -1
        if val < 0: return -1
        for f in self.feeds:
            if val == f[self.feed.get_index('id')]: 
                if load: self.feed.populate(f)
                if f[self.feed.get_index('is_category')] == 1: return -val
                else: return val
        return -1

    def resolve_f_o_c(self, val, **kargs):
        """ Resolve feed or category """
        print(val)
        if val is None: return None
        if type(val) is not int: return -1
        if val < 0: return -1
        load = kargs.get('load', False)
        for f in self.feeds:
            if f[self.feed.get_index('id')] == val:
                if load: self.feed.populate(f)           
                if f[self.feed.get_index('is_category')] == 1: return -1, val
                return val, -1
        return -1



    def resolve_field(self, val:str):
        """ Resolve field ID depending on provided field name. Returns -1 if field is not in prefixes """
        if val is None: return None

        if type(val) is int:
            if val in PREFIXES.keys(): return val
            else: return -1

        if type(val) is str:
            for p,v in PREFIXES.items():
                if val.lower() == v[1].replace('e.',''):
                    if p == 0: break
                    return p
        return -1


    def resolve_qtype(self, qtype, **kargs):
        """ Resolve query type from string to int """
        if qtype is None: 
            if kargs.get('no_null', False): return -1
            return 1
        if type(qtype) is int and qtype in (0,1,2,3,4,5,): return qtype
        if type(qtype) is str:
            if qtype.lower() in ('string','str',):
                return 0
            elif qtype.lower() in ('full', 'fts', 'full-text','fulltext',):
                return 1
            elif qtype.lower() in ('exact','fts-exact','exact-fts',):
                return 2
            else: return 1

        return -1




    def _refresh_data(self, **kargs):
        """Refresh all data (wrapper)"""
        if ( not self.single_run ) or kargs.get('first_run',False):
            self.load_feeds()
            self.load_rules(first_run=kargs.get('first_run',False))
		






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

        self._run_sql_multi_lock( (("insert into params values('doc_count', ?)", (doc_count,)), \
                                    ("insert into params values('avg_weight', ?)", (avg_weight,))) )

        if self.debug:
            print("Done:")
            print("Doc count: ", doc_count, " ")
            print("Avg weight: ", avg_weight, " ")



    def get_doc_count(self, **kargs):
        """ Retrieve entry count from params"""
        doc_count = self.sqlite_cur.execute("select val from params where name = 'doc_count'").fetchone()
        if doc_count in (None, (None,),()):
            self._update_stats()
            doc_count = self.sqlite_cur.execute("select val from params where name = 'doc_count'").fetchone()
        doc_count = scast(doc_count[0], int, 1)
        return doc_count


    def get_avg_weight(self, **kargs):
        """ Retrieve average entry weight - used for soft higlighting downloaded entries"""
        av_weight = self.sqlite_cur.execute("select val from params where name = 'avg_weight'").fetchone()
        if av_weight in (None, (None,),()):
            self._update_stats()
            av_weight = self.sqlite_cur.execute("select val from params where name = 'avg_weight'").fetchone()

        return scast(av_weight[0], float, 1)








############################################
# FEEDS


    def del_feed(self, id:int, **kargs): cli_msg(self.r_del_feed(id, **kargs))
    def r_del_feed(self, id:int, **kargs):
        """Delete feed data - by ID"""
        id = scast(id,int,0)

        stype = kargs.get('type','feed')   
        if kargs.get('type') is not None:
            if stype == 'category' and self.resolve_category(id, load=True) in (None,False): return -1, 'Category %a not found!', id
            if stype == 'feed' and self.resolve_feed(id, load=True) in (None,False) : return -1, 'Channel %a not found!', id

        if self.feed['deleted'] == 1: deleted = True
        else: deleted = False
        name = feed_name_cli(self.feed)

        if not deleted:
            # Mark as deleted
            err = self._run_sql_lock("update feeds set deleted = 1 where id = ?", (id,) )                          
        else:
            # Delete permanently with all data
            err = self._run_sql_multi_lock( \
                (("delete from rules where learned = 1 and context_id in (select e.id from entries e where e.feed_id = ?)", (id,) ),\
                ("delete from entries where feed_id = ?", (id,)),\
                ("update feeds set parent_id = NULL where parent_id = ?", (id,)),\
                ("delete from feeds where id = ?", (id,))) )

            if err == 0:
                if self.icons == {}: self._load_icons()
                icon = self.icons.get(id)
                if icon is not None and icon.startswith(f'{FEEDEX_ICON_PATH}{DIR_SEP}feed_') and os.path.isfile(icon): os.remove(icon)

        self._refresh_data()

        if err != 0: return -2, 'DB error: %a', err

        if self.rowcount > 0:
            if not deleted:
                if stype == 'feed': 
                    self._log(False, f'Channel {name} ({id}) deleted')
                    return 0, 'Channel %a deleted', f'{name} ({id})'
                elif stype == 'category': 
                    self._log(False, f'Category {name} ({id}) deleted')
                    return 0, 'Category %a deleted', f'{name} ({id})'
            else:
                if stype == 'feed': 
                    self._log(False, f'Channel {name} ({id}) deleted pemanently (with entried and rules)')
                    return 0, 'Channel %a deleted pemanently (with entried and rules)', f'{name} ({id})' 
                elif stype == 'category': 
                    self._log(False, f'Category {name} ({id}) deleted permanently (with entries and rules)')
                    return 0, 'Category %a deleted permanently (with entries and rules)', f'{name} ({id})'
        else:
            return 0, 'Nothing done'






    def add_feed(self, name:str, fields:dict, **kargs): cli_msg(self.r_add_feed(name, fields, **kargs))
    def r_add_feed(self, name:str, fields:dict, **kargs):
        """Wrapper for adding a feed to database """

        is_category = fields.get('is_category',False)

        if (not is_category) and (not check_url(fields.get('url', None)) and kargs.get('handler','rss') in ('rss',) ): return -1, 'Not a valid URL or IP (%a)', fields.get('url','<<EMPTY>>')            
        if (not is_category) and fields.get('link') not in ('', None) and (not check_url(fields.get('link', None))): return -1, 'Not a valid URL or IP (%a)', fields.get('url','<<EMPTY>>')

        self.feed.clear()
        self.feed.merge(fields)

        self.feed['id'] = None
        self.feed['name'] = name
        self.feed['is_category'] = binarify(is_category)
        self.feed['autoupdate'] = binarify(self.feed.get('autoupdate',0))
        self.feed['error'] = 0
        self.feed['interval'] = scast(self.feed.get('interval',None), int, self.config.get('default_interval',45))

        if self.feed['parent_id'] is not None:
            if is_category: return -1, 'Nesting categories nor permitted!'
            self.feed['parent_id'] = self.resolve_category(self.feed.get('parent_id'))
            if self.feed['parent_id'] == False: return -1, 'Category not found!'


        if not is_category: self.feed['handler'] = kargs.get('handler','rss')
        else: self.feed['handler'] = None

        self.feed.clean()
            
        err = self._run_sql_lock(self.feed.insert_sql(all=True), self.feed.vals)
        if err != 0: return -2, 'DB error: %a', err
 
        self.last_feed_id = self.lastrowid

        a = self.rowcount

        self._refresh_data()
 
        if a == 0: return 0, 'Nothing done'
        if is_category: 
            self._log(False, f'Category {name} added')
            return 0, 'Category %a added', name
        else: 
            self._log(False, f"Channel {fields.get('url', '<UNKNOWN>')} ({self.last_feed_id}) added")
            return 0, 'Channel %a added', f"{fields.get('url', '<UNKNOWN>')} ({self.last_feed_id})"





	
    def add_feed_from_url(self, url, **kargs):
        for m in self.g_add_feed_from_url(url, **kargs): cli_msg(m) 
    def g_add_feed_from_url(self, url, **kargs):
        """This adds feed entry just by downloading it by url. Handy for quickly adding a feed (generator method)"""        
        url = url.strip()
        handler = kargs.get('handler','rss')

        if not check_url(url) and handler in ('rss',): 
            yield -1, 'Not a valid URL or IP'
            return -1


        # Check if feed is already present (by URL)
        results = self.sqlite_cur.execute("""select * from feeds where url = ? and coalesce(deleted,0) <> 1 and handler <> 'local'""", (url,) ).fetchone()
        if results is not None:
            res_id = results[self.feed.get_index("id")]
            res_name = results[self.feed.get_index("name")]
            yield -1, 'Channel with this URL already exists (%a)', f'{res_name} ({res_id})'
            return -1

        parent_id = self.resolve_category(kargs.get('category'))
        if parent_id == -1:
            yield -1, 'Category %a not found!', parent_id
            return -1

        # If all is ok, then make an insert ...
        err = self._run_sql_lock("""insert into feeds (url, login, domain, passwd, auth, interval, is_category, handler, parent_id, autoupdate) 
values(:url, :login, :domain, :passwd, :auth, :interval, 0, :handler, :parent_id, 1)""",
        {'url': url, 
        'login':kargs.get('login',None), 
        'domain': kargs.get('domain',None), 
        'passwd': kargs.get('passwd',None), 
        'auth': kargs.get('auth',None), 
        'interval': self.config.get('default_interval',45),
        'autoupdate' : 1,
        'handler' : handler, 
        'parent_id': parent_id}
        )
        if err != 0:
            yield -2, 'DB error: %a', err
            return -2

        self.last_feed_id = self.lastrowid
   
        self._log(False, f'Channel {self.lastrowid} added')
        yield 0, 'Channel %a added...', self.lastrowid

        self.load_feeds()

        for msg in self.g_fetch(id=self.last_feed_id, force=True, ignore_interval=True): 
            yield msg






    def edit_feed(self, id, fields:dict, **kargs): cli_msg(self.r_edit_feed(id, fields, **kargs))
    def r_edit_feed(self, id, fields:dict, **kargs):
        """Edit Feed's parameter(s) - wrapper for update (generator method)"""

        id = scast(id,int,0)
        if id == 0: return -1, 'No valid Channel of Category id provided!'

        stype = kargs.get('type','feed')
        if stype == 'category' and self.resolve_category(id, load=True) in (None,False): return -1, 'Category %a not found!', id
        if stype == 'feed' and self.resolve_feed(id, load=True) in (None,False): return -1, 'Feed %a not found!', id

        name = self.feed.get('name', self.feed.get('title', self.feed.get('id','<<UNKNOWN>>')))

        sets = 'set'
        vals = {}
        flds = []

        for field, value in fields.items():

            field = scast(field, str, None)
            if field is None: continue
            if field.lower() == 'id': continue

            if value in ('null','NULL','Null'): value=None

            if field == 'url':
                if fields.get('handler') in ('rss','twitter') or ( fields.get('handler') is None and self.feed['handler'] in ('rss',)):
                    if not check_url(value): return -1, 'Not a valid URL or IP (%a)!', value

            if field == 'link' and value not in (None, '') and not check_url(value): return -1, 'Not a valid URL or IP (%a)!', value

            if field in ('parent_id'):
                if self.feed['is_category'] == 1: return -1, 'Nesting categories not allowed (parent_id)'

                value = self.resolve_category(value, load=False)
                if value == -1: return -1, 'Parent category not found (%a)!', value

                cat_name = '<<UNKNOWN>>'
                for c in self.feeds:
                    if c[self.feed.get_index('id')] == value:
                        cat_name = c[self.feed.get_index('name')]
                        break

            if field not in FEEDS_SQL_TABLE: return -1, 'Not a valid field (%a)!', field
            
            if self.feed[field] != value:
                sets = f"""{sets} {field} = :{field},"""
                vals[field] = value
                flds.append(field)
        

        if len(flds) > 0:
            sets = sets[:-1]
            vals['id'] = id
            sql = f"""update feeds\n{sets}\nwhere id = :id""" 
            err = self._run_sql_lock(sql, vals)
            if err != 0: return -2, 'DB error: %a', err

            a = self.rowcount

        else: a = 0

        if a > 0:

            if len(flds) > 1: 
                self._log(False, f'{feed_name_cli(self.feed)} ({id}) updated successfully')
                return 0, '%a updated successfully', f'{feed_name_cli(self.feed)} ({id})'

            for f in flds:
                if f == 'deleted' and vals[f] in (0, None):
                    self._log(False, f'{feed_name_cli(self.feed)} ({id}) restored')
                    return 0, '%a restored', f'{feed_name_cli(self.feed)} ({id})'

                elif f == 'error' and vals[f] in (0, None) and stype == 'feed':
                    self._log(False, f'Channel {feed_name_cli(self.feed)} ({id}) marked as healthy')
                    return 0, 'Channel %a marked as healthy', f'{feed_name_cli(self.feed)} ({id})'    

                elif stype == 'feed' and f in ('parent_id',) and vals[f] not in (0, None):
                    self._log(False, f'Channel {feed_name_cli(self.feed)} ({id}) assigned to category {cat_name}')
                    return 0, f'Channel {feed_name_cli(self.feed)} ({id}) assigned to category %a', cat_name

                elif stype == 'feed' and f in ('parent_id',) and vals[f] in (0, None):
                    self._log(False, f'Channel {feed_name_cli(self.feed)} ({id}) detached from category')
                    return 0, f'Channel %a detached from category', f'{feed_name_cli(self.feed)} ({id})'

                else:
                    self._log(False, f'{feed_name_cli(self.feed)} ({id}) updated: {f} -> {vals[f]}')
                    return 0, f'%a updated: {f} -> {vals[f]}', f'{feed_name_cli(self.feed)} ({id})'

        else:
            return 0, 'Nothing done'







###############################################
# ENTRIES


    def edit_entry(self, id, fields:dict, **kargs):
        for m in self.g_edit_entry(id, fields, **kargs): cli_msg(m)
    def g_edit_entry(self, id, fields:dict, **kargs):
        """Wrapper for update on entries (generator method)"""
        sets = 'set'
        vals = {}
        flds = []
        recalculate = False
        learn = kargs.get('learn', self.config.get('use_keyword_learning', True))
        relearn = False

        self.entry.populate(self.sqlite_cur.execute("""select * from entries where id = ?""", (id,) ).fetchone())
        if self.entry['id'] is None:
            yield -1, 'Entry %a not found!', id
            return -1



        for field, value in fields.items():

            field = scast(field, str, None)
            if field is None: continue
            if field.lower() == 'id': continue
            
            if value in ('null','NULL','Null'): value=None

            if field == 'link' and not value is None and not check_url(value):
                yield -1, 'Not a valid URL or IP (%a)!', value
                return -1
            
            if field in ('feed_id', 'feed'):
                field = 'feed_id'
                value = self.resolve_feed(value)
                if value == -1:
                    yield -1, 'Feed not found!'
                    return -1

            if field == 'category':
                field = 'feed_id'
                value = self.resolve_category(value)
                if value == -1:
                    yield -1, 'Category not found!'
                    return -1

            if field == 'feed_or_cat':
                field = 'feed_id'
                if self.resolve_f_o_c(value) == -1:
                    yield -1, 'No Channel or Category with id %a found!', value
                    return -1
            

            if field not in ENTRIES_SQL_TABLE: # bad field name
                yield -1, 'Invalid field (%a)', field
                return -1

            # restricted field chosen
            if field in LING_TECH_LIST: 
                yield -1, 'Cannot edit restricted field (%a)', field
                return -1

            if self.entry[field] == value: continue # no changes made
            
            # Text changed - needs recalculation
            if field in LING_LIST1:
                recalculate = True
                self.entry[field] = value
            
            # Read status increased - relearn keywords
            if field == 'read':
                if value not in (0,'0', None) and self.entry['read'] in (None,0):
                    if learn: relearn = True

            sets = f"""{sets} {field} = :{field},"""
            vals[field] = value
            flds.append(field)

        # Deal with recalculations if concerned fields were changed
        if recalculate or relearn:
            if relearn: yield 0, 'Generating keywords for entry %a', id
            
            self.entry = self._ling(self.entry, stats=True, rank=False, learn=relearn, force=relearn)
            if isinstance(self.entry, SQLContainer):
                for field in LING_TECH_LIST: 
                    sets = f"""{sets} {field} = :{field},"""
                    vals[field] = self.entry[field]
                    flds.append(field)
            else:
                yield -1, 'Error processing linguistics for entry %a', id
                return -1


        if len(flds) > 0:
            sets = sets[:-1]
            sql = f"""update entries\n{sets}\nwhere id = :id"""
            vals['id'] = id

            err = self._run_sql_lock(sql, vals)
            if err != 0:
                yield -2, 'DB error: %a', err
                return -1

            else: a = self.rowcount

        else: a = 0

        if a > 0:

            fcnt = 0
            for f in flds:
                if f in LING_TECH_LIST: continue
                fcnt += 1
                
                if f == 'deleted' and vals[f] in (None, 0,'0'):
                    self._log(False, f'Entry {id} restored')
                    yield 0, 'Entry %a restored', id
                elif f == 'read' and vals[f] in (None, 0,'0'):
                    self._log(False, f'Entry {id} marked as unread')
                    yield 0, 'Entry %a marked as unread', id
                elif f == 'read' and vals[f] not in (None, 0,'0'):
                    self._log(False, f'Entry {id} marked as read')
                    yield 0, 'Entry %a marked as read', id
                elif f == 'flag' and vals[f] not in (0, None,'0'):
                    self._log(False, f'Entry {id} flagged')
                    yield 0, 'Entry %a flagged', id
                elif f == 'flag' and vals[f] in (0, None, '0'):
                    self._log(False, f'Entry {id} unflagged')
                    yield 0, 'Entry %a unflagged', id
                else:
                    self._log(False, f'Entry {id} updated: {f} -> {scast(vals[f],str,"NULL")}')
                    yield 0, f'Entry {id} updated: %a', f'{f} -> {scast(vals[f],str,"NULL")}'

            if fcnt > 1: yield 0, 'Entry %a updated successfully', id

        else: yield 0, 'Nothing done'

        return 0






    def del_entry(self, id:int, **kargs): cli_msg(self.r_del_entry(id, **kargs))
    def r_del_entry(self, id:int, **kargs):
        """Delete entry by id """
        res = self.sqlite_cur.execute("select * from entries where id = ?", (id,) ).fetchone()
        if res in (None, (None,), ()): return -1, 'Entry %a not found!', id
        
        self.entry.populate(res)

        if self.entry['deleted'] == 1:
            err = self._run_sql_multi_lock( \
                (("delete from rules where context_id = ?", (id,)),\
                ("delete from entries where id = ?", (id,)) ))
        else:
            err = self._run_sql_lock("update entries set deleted = 1 where id = ?", (id,))

        if err != 0: return -2, 'DB error: %a', err

        if self.rowcount > 0:
            if self.entry['deleted'] == 1: 
                self._log(False, f'Entry {id} deleted permanently with rules')
                return 0, 'Entry %a deleted permanently with rules', id
            else: 
                self._update_stats()
                self._log(False, f'Entry {id} deleted')
                return 0, 'Entry %a deleted', id
        else:                
            return 0, 'Nothing done'






    def run_entry(self, **kargs):
        """Wrapper for opening entries in the browser and updating status (increasing by 1 for each opening)"""
        for m in self.g_run_entry(**kargs): cli_msg(m)
    def g_run_entry(self, **kargs):
        """Wrapper for opening entries in the browser and updating status (increasing by 1 for each opening)
            If specified, it will extract and learn rules form newly read entries (generator method)"""

        url = kargs.get('url')
        id = kargs.get('id')

        if url is not None: url = url.strip()
        elif id is None: return -1

        if self.debug: print(id, url)

        browser_run = kargs.get('browser_run',True)   
        update_status = kargs.get('update_status',True) # Change status to 'Read'?
        learn = kargs.get('learn', self.config.get('use_keyword_learning', True))

        self.entry.clear()

        if id is None and url is not None:
            self.entry.populate( self.sqlite_cur.execute("select * from entries where link = ?", (url,)).fetchone() )
        elif id is not None:
            self.entry.populate( self.sqlite_cur.execute("select * from entries where id = ?", (id,)).fetchone() )

        if self.entry['id'] is not None:
            empty_run = False
        else:
            empty_run = True


        if update_status and not empty_run:
            err = self._run_sql_lock('update entries set read = coalesce(read,0) + 1 where id = ?', (self.entry['id'],))    
            if err != 0: yield -2, 'DB error: %a', err


        if browser_run and self.entry['link'] is not None:
            # Parse browser command line from config and run link in browser
            command = self.config.get('browser','firefox --new-tab %u').split()
            for idx, arg in enumerate(command):
                if arg in ('%u', '%U', '%f', '%F'):
                    command[idx] = self.entry['link']

            if self.debug: print(' '.join(command))
            yield 0, 'Opening in browser (%a) ...', self.entry['link']

            subprocess.Popen(command)

        if not empty_run and learn and self.entry['read'] in (0, None):
            # Extract fields and use them to learn and remember the rules
            yield 0, 'Learning keywords'
            self.LP.process_fields(self.entry.tuplify(filter=LING_LIST2), learn=True, index=False)
            err = self.learn_rules(self.LP.features, context_id=self.entry['id'], lang=self.LP.get_model())
            if err != 0: yield -2, 'DB error: %a', err
            else: yield 0, 'Keywords learned'    

        return 0

	







    def add_entries(self, **kargs):
        for m in self.g_add_entries(**kargs): cli_msg(m)
    def g_add_entries(self, **kargs):
        """ Wraper for inseting entries from list of dicts or a file """
        learn = kargs.get('learn', self.config.get('use_keyword_learning', True))
        pipe = kargs.get('pipe',False)

        now = datetime.now()
        now_raw = int(now.timestamp())

        efile = kargs.get('efile')
        if efile is None and not pipe:
            elist = kargs.get('elist',())
        elif not pipe:
            elist = parse_efile(efile)
        elif pipe:
            elist = parse_efile(None, pipe=True)
        else:
            elist = -1

        if elist == -1:
            yield -1, 'Invalid input/file given!'
            return -1
        if elist == -2:
            yield -1, 'Input data is not a list'
            return -1
        if elist == -3:
            yield -1, 'Invalid element dictionary format!'
            return -1
        if elist == -4:
            yield -1, 'Invalid data type!'
            return -1



        self.entries = []
        num_added = 0
        # Queue processing
        for e in elist:

            self.entry.clear()          
            self.entry.merge(e)

            if e.get('category') is not None:
                self.entry['feed_id'] = self.resolve_category(e.get('category'), load=False)
            else:
                self.entry['feed_id'] = self.resolve_feed(e.get('feed_id'), load=False)

            if self.entry['feed_id'] == -1:
                yield -1, 'No valid Feed or Category given (%a)!', self.entry['feed_id']
                return -1

            self.entry.clean()            
            self.entry['id'] = None #Needed to avoid id conflicts
            self.entry['adddate'] = now_raw
            self.entry['adddate_str'] = now
            self.entry['pubdate'] = coalesce(self.entry.get('pubdate', None), now_raw)
            self.entry['pubdate_str'] = coalesce(self.entry.get('pubdate_str', None), now)
            self.entry['read'] = coalesce(self.entry['read'], self.config.get('default_entry_weight',2))
            if kargs.get('ling',True):
                self.entry = self._ling(self.entry, learn=learn, rank=True, stats=True)
            # Insert ...
            err = self._run_sql_lock(self.entry.insert_sql(all=True), self.entry.vals)
            if err != 0: yield -2, 'DB error: %a', err
            else:            
                # ... and learn
                context_id = self.lastrowid
                self.last_entry_id = context_id
                num_added += 1
                yield 0, 'Entry added (%a)', context_id

                if learn and self.entry['tokens'] not in (None,'') and coalesce(self.entry['read'],0) > 0:
                    yield 0, 'Learning keywords ...'
                    err = self.learn_rules(self.LP.features, context_id=context_id, lang=self.entry['lang'], ignore_lock=True)
                    if err != 0: 
                        self._log(True, f'Error learning rules for entry {context_id}')
                        yield -2, 'DB error while learning keywords (%a)', err
                    else: yield 0, 'Keywords learned for entry %a', context_id

        # stat
        self._update_stats()
        self._refresh_data()
        if num_added > 1: 
            self._log(False, f'Added {num_added} new entries')
            yield 0, 'Added %a new entries', num_added
        return 0






##########################################33
#       Terms, rules and keywords
#


    def learn_rules(self, features:dict, **kargs):
        """ Add features/rules to database """
        if self.debug: print("Processing extracted features...")

        context_id = kargs.get('context_id')
        lang=kargs.get('lang','heuristic')

        if context_id is not None and context_id > 0:
            err = self._run_sql_lock("delete from rules where context_id = ? and learned = 1", (context_id,) )
            if err != 0: return err

        query_list_rules = []
        for f,v in features.items():
            weight = slist(v,0,0)
            qtype = slist(v,1,0)
            if weight <= 0: continue
            self.rule.clear()
            self.rule['string'] = f[1:]
            self.rule['weight'] = weight
            self.rule['name'] = slist(v,2,0)
            self.rule['type'] = qtype
            self.rule['case_insensitive'] = 0
            self.rule['lang'] = lang
            self.rule['learned'] = 1
            self.rule['flag'] = 0
            self.rule['additive'] = 1
            self.rule['context_id'] = context_id
            query_list_rules.append(self.rule.vals.copy())

        if self.debug: print(query_list_rules)

        err = self._run_sql_lock(self.rule.insert_sql(all=True), query_list_rules, many=True)
        if err != 0: return err

        self._refresh_data()

        if self.debug: print('Rules learned')
        return 0
   





    def add_rule(self, fields:dict, **kargs): cli_msg(self.r_add_rule(fields, **kargs))
    def r_add_rule(self, fields:dict, **kargs):
        """ Add a rule to database """
        # We assume that by defult rule should flag
        ignore_lock = kargs.get('ignore_lock',False)

     
        if fields.get('flag') in (None,0): fields['flag'] = None
        else: fields['flag'] = scast(fields.get('flag'), int, 0)
        fields['case_insensitive'] = fields.get('case_ins', False)
        fields['learned'] = 0

        self.rule.clear()
        self.rule.merge(fields)

        if self.rule['weight'] is None: self.rule['weight'] = self.config.get('default_rule_weight',2)
        self.rule['weight'] = scast(self.rule['weight'], float, None)
        if self.rule['weight'] is None: return -1, "Rule's weight must be a number!"

        self.rule['type'] = self.resolve_qtype(self.rule.get('type'), no_null=True)
        if self.rule['type'] == -1: return -1, 'Invalid query type!'
        
        # Check if REGEX is valid to avoid breaking rule matching later
        if self.rule['type'] == 3 and not check_if_regex(self.rule['string']): return -1, 'Not a valid REGEX string (%a)!', self.rule['string']


        self.rule['field_id'] = self.resolve_field(self.rule.get('field_id'))
        if self.rule['field_id'] == False: return -1, 'Invalid field ID (%a)', self.rule['field_id']
        
        if self.resolve_f_o_c(self.rule.get('feed_id')) == -1: return -1, 'Channel or Category %a not found!', self.rule.get('feed_id')

        self.rule.clean()

        err = self._run_sql_lock(self.rule.insert_sql(all=True), self.rule.vals) 
        if err != 0: return -2, 'DB error: %a', err

        self.last_rule_id = self.lastrowid

        self._refresh_data()
        self._log(False, f'New rule added ({self.last_rule_id})')
        return 0, 'New rule added (id:%a)', self.last_rule_id






    def del_rule(self,id:int, **kargs): cli_msg(self.r_del_rule(id, **kargs))
    def r_del_rule(self,id:int, **kargs):
        """ Delete rule by ID """
        err = self._run_sql_lock("delete from rules where id = ? and learned <> 1", (id,) )
        if err != 0: return -2, 'DB Error: %a', err
        
        if self.rowcount > 0: 
            self._refresh_data()
            self._log(False, f'Rule {id} deleted')
            return 0, 'Rule %a deleted', id

        else: return 0, 'Nothing done.'







    def edit_rule(self, id:int, fields:dict, **kargs): cli_msg(self.r_edit_rule(id, fields, **kargs))
    def r_edit_rule(self, id:int, fields:dict, **kargs):
        """ Wrapper for editing/updating a rule """
        sets = 'set'
        vals = {}
        flds = []
        self.rule.populate(self.sqlite_cur.execute("""select * from rules where id = ?""", (id,) ).fetchone())

        if self.rule['id'] is None: return -1, 'Rule %a not found!', id
        if self.rule['learned'] in (1,2): return -1, 'Learned rules cannot be edited!'

        for field, value in fields.items():
            field = scast(field, str, None)
            if field is None: continue
            if field.lower() == 'id': continue
            
            if field not in RULES_SQL_TABLE: return -1, 'Not a valid field (%a)!', field
            
            if value in ('null','NULL','Null'): value=None

            if field == 'weight':
                value = scast(value, float, None)
                if value is None:
                    return -1, 'Rule\'s weight must be a number!'

            if field == 'flag':
                if value not in (None, 1,2,3,4,5): return -1, 'Flag needs to be empty or in (1,2,3,4,5)'

            if field == 'type':
                value = self.resolve_qtype(value, no_null=True)
                if value == -1: return -1, 'Invalid rule type!'

            if field in ('string','type',) and (self.rule['type'] == 3 or fields.get('type') == 3):
                if not check_if_regex(self.rule['string']): return -1, 'Not a valid REGEX string (%a)!', self.rule['string']                     
                
            if field == 'field_id':
                value = self.resolve_field(value)
                if value == False: return -1, 'Invalid field ID (%a)', field

            
            if field == 'feed_id':
                if self.resolve_f_o_c(value) == -1: return -1, 'Channel or Category %a not found!', self.rule.get('feed_id')

            if self.rule[field] != value:
                sets = f"""{sets} {field} = :{field},"""
                vals[field] = value
                flds.append(field)

        if len(flds) > 0:
            sets = sets[:-1]
            sql = f"""update rules\n{sets}\nwhere id = :id"""
            vals['id'] = id

            err = self._run_sql_lock(sql, vals)
            if err != 0: return -2, 'DB error: %a', err

            a = self.rowcount

        else: a = 0


        if a > 0:
            msg = ''
            if len(flds) > 1:
                self._log(False, f'Rule {id} updated')
                return 0, 'Rule %a updated', id
            else:
                for f in flds:
                    msg = f'{f} -> {scast(vals[f],str,"NULL")}' 
                self._log(False, f'Rule {id} updated: {msg}')
                return 0, f'Rule {id} updated: %a', msg

        else: return 0, 'Nothing done'
                        






######################################
#       Fetching


    def get_last(self):
        """ Get timestamp of last news check """
        last = self.sqlite_cur.execute("select max(val) from params where name = 'last'").fetchone()
        if last == (None,): return 0
        else: return last[0]




    def _ling(self, entry, **kargs):
        """ Linguistic processing for an entry """
        learn = kargs.get('learn',False)
        stats = kargs.get('stats',True)
        rank = kargs.get('rank',True)
        force = kargs.get('force',False)

        
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
        if entry['lang'] is None: entry['lang'] = self.LP.get_model()

        if rank: 
            (entry['importance'], entry['flag']) = self.QP.match_rules(entry.tuplify(filter=LING_LIST2), entry['weight'], self.rules)
        if learn:
            if force or coalesce(entry['read'],0) > 0:
                self.learn_rules(self.LP.features, context_id=entry['id'], lang=entry['lang'])

        return entry

        



    def fetch(self, **kargs): 
        for m in self.g_fetch(**kargs): cli_msg(m)
    def g_fetch(self, **kargs):
        """ Check for news taking into account specified intervals and defaults as well as ETags and Modified tags"""
        feed_ids = scast(kargs.get('ids'), tuple, None)
        feed_id = scast(kargs.get('id'), int, 0)

        force = kargs.get('force', False)
        ignore_interval = kargs.get('ignore_interval', True)

        skip_ling = kargs.get('skip_ling',False)
        update_only = kargs.get('update_only', False)

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
            if self.feed['interval'] == 0 and feed_id == 0 and feed_ids is None: continue # Setting interval to 0 deactivates automated fetching
            if feed_id != 0 and feed_id != self.feed['id']: continue
            if feed_ids is not None and self.feed['id'] not in feed_ids: continue
            if self.feed['is_category'] not in (0,None) or self.feed['handler'] in ('local'): continue

            # Ignore unhealthy feeds...
            if scast(self.feed['error'],int,0) >= self.config.get('error_threshold',5) and not kargs.get('ignore_errors',False):
                yield 0, 'Feed %a ignored due to previous errors', feed_name_cli(self.feed)
                continue

            #Check if time difference exceeds the interval
            last_checked = scast(self.feed['lastchecked'], int, 0)
            if not ignore_interval:
                diff = (started - last_checked)/60
                if diff < scast(self.feed['interval'], int, self.config.get('default_interval',45)):
                    if self.debug: print(f'Feed {self.feed["id"]} ignored (interval: {self.feed["interval"]}, diff: {diff})')
                    continue

            yield 0, 'Processing %a ...', feed_name_cli(self.feed)

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
                yield -1, 'Handler %a not recognized!', self.feed['handler']
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
                                yield -1, 'Error while linguistic processing %a!', item
                        else:
                            entries_sql.append(item.vals.copy())

                        # Track new entries and take care of massive insets by dividing them into parts
                        tech_counter += 1
                        if tech_counter >= self.config.get('max_items_per_transaction', 300):
                            err = self._run_sql_lock(self.entry.insert_sql(all=True), entries_sql, many=True)
                            if err != 0:
                                yield -2, 'DB error: %a', err
                            else: 
                                entries_sql = []

                            tech_counter = 0  

                    elif item != 0:
                        if self.gui: yield -3, 'Handler error: %a', item



            else:
                msg = handler.download(self.feed['url'], force=force, etag=self.feed['etag'], modified=self.feed['modified'], login=self.feed['login'], password=self.feed['passwd'], auth=self.feed['auth'])
                if msg != 0: yield -3, 'Handler error: %a', msg



            if handler.error:
                # Save info about errors if they occurred
                if update_only:
                    err = self._run_sql_lock("""update feeds set http_status = :status, error = coalesce(error,0)+1 where id = :id""", {'status': handler.status, 'id': self.feed['id']} )
                else:
                    err = self._run_sql_lock("""update feeds set lastchecked = :now, http_status = :status, error = coalesce(error,0)+1 where id = :id""", {'now':now_raw, 'status':handler.status, 'id': self.feed['id']} )
                if err != 0: yield -2, 'DB error: %a', err

                continue

            else:				
                #Update feed last checked date and other data
                if update_only:
                    err = self._run_sql_lock("""update feeds set http_status = :status, error = 0  where id = :id""", {'status':handler.status, 'id': self.feed['id']} )
                else:
                    err = self._run_sql_lock("""update feeds set lastread = :now, lastchecked = :now, etag = :etag, modified = :modified, http_status = :status, error = 0  where id = :id""", 
                    {'now':now_raw, 'etag':handler.etag, 'modified':handler.modified, 'status':handler.status, 'id':self.feed['id']} )
                if err != 0: yield -2, 'DB error: %a', err


            # Inform about redirect
            if handler.redirected: 
                self._log(False, f"Channel redirected ({self.feed['url']})")
                yield 0, 'Channel redirected (%a)', self.feed['url']

            # Save permanent redirects to DB
            if handler.feed_raw.get('href',None) != self.feed['url'] and handler.status == 301:
                self.feed['url'] = rss_handler.feed_raw.get('href',None)
                if not update_only and kargs.get('save_perm_redirects',True):
                    err = self._run_sql_lock('update feeds set url = :url where id = :id', {'url':self.feed['url'], 'id':self.feed['id']} )    
                    if err != 0: yield -2, 'DB error: %a', err


            # Push to DB
            err = self._run_sql_lock(self.entry.insert_sql(all=True), entries_sql, many=True)
            if err != 0: yield -2, 'DB error: %a', err


            # Autoupdate metadata if needed or specified by 'forced' or 'update_only'
            if (scast(self.feed['autoupdate'], int, 0) == 1 or update_only) and not handler.no_updates:

                yield 0, 'Updating metadata for %a', feed_name_cli(self.feed)

                msg = handler.update(self.feed, ignore_images=self.config.get('ignore_images',False))
                if msg != 0: yield -3, 'Handler error: %a', msg

                updated_feed = handler.feed

                if updated_feed == -1:
                    if self.debug: yield -1, 'Error updating metadata for feed %a', feed_name_cli(self.feed)
                    continue
                elif updated_feed == 0:
                    continue
 
                err = self._run_sql_lock(updated_feed.update_sql(wheres=f'id = :id'), updated_feed.vals)
                if err != 0: yield -2, 'DB Error: %a', err
        
                yield 0, 'Metadata updated for feed %a', feed_name_cli(self.feed)

            # Stop if this was the specified feed...
            if feed_id != 0: break


        if self.new_items > 0:
            self._run_sql_lock("""insert into params values('last', ?)""", (started,) )

        if kargs.get('update_stats',True):
            if self.new_items > 0:
                self._update_stats()

        if not update_only: yield 0, 'Finished fetching (%a new articles)', self.new_items
        else: yield 0, 'Finished updating metadata'

        return 0







#################################################
# Utilities 


    def clear_history(self, **kargs): cli_msg(self.r_clear_history(**kargs))
    def r_clear_history(self, **kargs):
        """ Clears search history """
        err = self._run_sql_lock("delete from search_history",())
        if err != 0: return -2, 'DB error: %a', err
        else: items_deleted = self.rowcount

        self._refresh_data()

        return 0, 'Deleted %a items from search history', items_deleted
        
        


    def delete_query_rules(self, **kargs): cli_msg(self.r_delete_query_rules(**kargs))
    def r_delete_query_rules(self, **kargs): 
        """ Deletes all rules comming from searches """
        err = self._run_sql_lock("delete from rules where learned = 2",[])
        if err != 0: return -2, 'DB error: %a', err
        else: items_deleted = self.rowcount

        self._refresh_data()
        return 0, 'Deleted %a rules from queries', items_deleted



    def delete_learned_rules(self, **kargs): cli_msg(self.r_delete_learned_rules(**kargs))
    def r_delete_learned_rules(self, **kargs):
        """ Deletes all learned rules """
        err = self._run_sql_lock("""delete from rules where learned = 1""",[])
        if err != 0: return -2, 'DB error: %a', err
        else:
            deleted_rules = self.rowcount
            self._refresh_data()
            return 0, 'Deleted %a learned rules', deleted_rules




    def empty_trash(self, **kargs): cli_msg(self.r_empty_trash(**kargs))
    def r_empty_trash(self, **kargs):
        """ Removes all deleted items permanently """
        # Delete permanently with all data
        rules_deleted = 0
        entries_deleted = 0
        feeds_deleted = 0
        err = self._run_sql_lock(EMPTY_TRASH_RULES_SQL,[])
        rules_deleted = self.rowcount
        if err == 0: 
            err = self._run_sql_lock(EMPTY_TRASH_ENTRIES_SQL,[])
            entries_deleted = self.rowcount
        if err == 0: err = self._run_sql_lock(EMPTY_TRASH_FEEDS_SQL1,[])
        if err == 0:
            feeds_to_remove = self.sqlite_cur.execute('select id from feeds where deleted = 1').fetchall()
            for f in feeds_to_remove:
                if self.icons == {}: self._load_icons()
                icon = self.icons.get(f)
                if icon is not None and icon.startswith(f'{FEEDEX_ICON_PATH}/feed_') and os.path.isfile(icon): os.remove(icon)
        else: return -2, 'DB error: %a', err

        err = self._run_sql_lock(EMPTY_TRASH_FEEDS_SQL2,[])
        feeds_deleted = self.rowcount
        if err != 0: return -2, 'DB error: %a', err
 
        self._refresh_data()
        self._log(False, f'Trash emptied: {feeds_deleted} channels/categories, {entries_deleted} entries, {rules_deleted} rules removed' )
        return 0, 'Trash emptied: %a', f'{feeds_deleted} channels/categories, {entries_deleted} entries, {rules_deleted} rules removed' 





    def recalculate(self, **kargs):
        """ Utility to recalculate, retokenize, relearn, etc. """

        verbose = kargs.get('verbose',True)
        entry_id = scast(kargs.get('id'), int, 0)
        learn = kargs.get('learn',False)
        rank = kargs.get('rank',False)
        stats = kargs.get('stats',False)
        force = kargs.get('force',False)

        if entry_id == 0:
            self._log(False, "Mass recalculation started...")
            if verbose: print("Mass recalculation started...")
            if rank:
                self._log(False,"Ranking according to saved rules...")
                if verbose: print("Ranking according to saved rules...")
            if learn:
                self._log(False,"Learning keywords ...")
                if verbose: print("Learning keywords ...")
            if stats:
                self._log(False,"Recalculating entries' stats ...")
                if verbose: print("Recalculating entries' stats ...")

            entries = self.sqlite_cur.execute("select * from entries").fetchall()

        else:
            if verbose: print(f'Recalculating entry {id} ...')
            entries = self.sqlite_cur.execute("select * from entries where id=?", (entry_id,)).fetchall()


        upd1_q = []
        upd2_q = []
        i = 0
        for entry in entries:
    
            i +=1

            self.entry.populate(entry)
            if verbose: print(f"Processing entry: {self.entry['id']}")
    
            self.entry = self._ling(self.entry, learn=learn, stats=stats, rank=rank, force=force)
            
            if not stats and rank:
                upd1_q.append({'importance': self.entry['importance'], 'flag': self.entry['flag'], 'id': self.entry['id']})
 
            if stats:
                vals = self.entry.filter(RECALCULATE_FILTER)
                vals['id'] = self.entry['id']
                upd2_q.append(vals)

            if self.debug: print("Done.")

            if i == self.config.get('max_items_per_transaction', 500):
            
                if not stats and rank:
                    err = self._run_sql_lock("""update entries set importance = :importance, flag = :flag where id = :id""", upd1_q, many=True)
                    if err != 0: sys.stderr.write(err)
                if stats:
                    err = self._run_sql_lock(self.entry.update_sql(filter=RECALCULATE_FILTER, wheres='id = :id'), upd2_q, many=True)
                    if err != 0: sys.stderr.write(err)

                i = 0
                upd1_q = []
                upd2_q = []

                if self.debug: print("Committed to DB")

        
        if not stats and rank:
            err = self._run_sql_lock("""update entries set importance = :importance, flag = :flag where id = :id""", upd1_q, many=True)
            if err != 0: sys.stderr.write(err)

        if stats:
            err = self._run_sql_lock(self.entry.update_sql(filter=RECALCULATE_FILTER, wheres='id = :id'), upd2_q, many=True)
            if err != 0: sys.stderr.write(err)

        if self.debug: print("Committed to DB")
    
        if verbose: self._log(False, "Recalculation finished")

        self._update_stats()
        if learn: self._refresh_data()
        return 0





    def db_stats(self, **kargs):
        """ Displays database statistics """
        version = self.sqlite_cur.execute("select val from params where name='version'").fetchone()
        doc_count = self.sqlite_cur.execute("select val from params where name='doc_count'").fetchone()
        avg_weight = self.sqlite_cur.execute("select val from params where name='avg_weight'").fetchone()
        last_update = self.sqlite_cur.execute("select max(val) from params where name='last'").fetchone()
        rule_count = self.sqlite_cur.execute("select count(id) from rules where learned=1").fetchone()
        keyword_count = self.sqlite_cur.execute("select count(id) from rules where learned=0").fetchone()
        feed_count = self.sqlite_cur.execute("select count(id) from feeds").fetchone()

        lock = self.sqlite_cur.execute("select * from params where name = 'lock'").fetchone()
        if lock is not None:
            lock=True     
        else:
            lock=False

        last_time = scast(slist(last_update,0,None),int,None)
        if last_time is not None:
            last_time_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(last_time))
        else:
            last_time_str = 'NOT FOUND'

        if kargs.get('markup',False) and not kargs.get('print',True):
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
            stat_str=f"{stat_str}DATABASE LOCKED!\n\n"
        
        if self.check_due_maintenance():
            stat_str=f"{stat_str}DATABASE MAINTENANCE ADVISED!\nUse {mb}feedex --db-maintenance{me} command"
                    
        stat_str=f"{stat_str}\n\n"

        if kargs.get('print',True):
            help_print(stat_str)
        
        return stat_str




    def check_due_maintenance(self):
        last_maint = slist(self.sqlite_cur.execute("""select coalesce(val,0) from params where name = 'last_maintenance' """).fetchone(), 0, 0)
        doc_count = self.get_doc_count()

        if doc_count - scast(last_maint, int, 0) >= 50000: return True
        else: return False


    def db_maintenance(self, **kargs):
        for m in self.g_db_maintenance(**kargs): cli_msg(m)        
    def g_db_maintenance(self, **kargs):
        """ Performs database maintenance to increase performance at large sizes """
        if self.locked(ignore=kargs.get('ignore_lock',False)):
            yield -2, 'DB locked!'
            return -2

        yield 0, 'Staring DB miantenance'

        yield 0, 'Performing VACUUM'
        self.sqlite_cur.execute('VACUUM')
        yield 0, 'Performing ANALYZE'
        self.sqlite_cur.execute('ANALYZE')
        yield 0, 'REINDEXING all tables'
        self.sqlite_cur.execute('REINDEX')

        yield 0, 'Updating document statistics'
        doc_count = self.sqlite_cur.execute('select count(e.id) from entries e').fetchone()[0]
        doc_count = scast(doc_count[0], int, 1)
        avg_weight = self.sqlite_cur.execute('select avg(coalesce(weight,0)) from entries').fetchone()[0]
        avg_weight = scast(avg_weight, float, 0)

        self.sqlite_cur.execute("insert into params values('doc_count', ?)", (doc_count,))
        self.sqlite_cur.execute("insert into params values('avg_weight', ?)", (avg_weight,))

        self.sqlite_cur.execute("""delete from params where name = 'last_maintenance'""")
        self.sqlite_cur.execute("""insert into params values('last_maintenance',?)""", (doc_count,))
        self.sqlite_conn.commit

        self._log(False, 'DB maintenance completed')
        yield 0, 'DB maintenance completed'

        self.unlock(ignore=kargs.get('ignore_lock',False))





    def port_data(self, ex:bool, pfile:str, mode:str, **kargs): cli_msg(self.r_port_data(ex, pfile, mode, **kargs))
    def r_port_data(self, ex:bool, pfile:str, mode:str, **kargs):
        """ Handles exporting and importing data to/from text files """
        if ex:
            if os.path.isfile(pfile): return -1, 'File already exists!'

            if mode == 'feeds':
                if self.debug: print("Exporting feeds...")
                ldata = list(self.feeds)
            elif mode == 'rules':
                if self.debug: print("Exporting rules...")
                ldata = list(self.sqlite_cur.execute("select * from rules r where coalesce(r.learned,0) = 0").fetchall())
            
            if save_json(pfile, ldata) == 0: return 0, 'Data successfully exported'
            else: return -1, 'Error writing JSON data to %a', pfile

        else:
            ldata = load_json(pfile,())
            if ldata == (): return -1, 'Invalid data'
            if type(ldata) not in (list, tuple): return -1, 'Invalid data format (not a list)'

            if mode == 'feeds':
                if self.debug: print("Importing feeds...")
                # Max ID will be added to imported ids to prevent ID collision
                max_id = self.sqlite_cur.execute('select max(id) from feeds').fetchone()
                max_id = slist(max_id, 0, 0)
                ldata_sql = []
                if max_id in (None, (None), ()): max_id = 0
                if self.debug: print(f'Max ID: {max_id}') 
                for l in ldata:
                    self.feed.populate(l)
                    if self.feed['parent_id'] is not None: self.feed['parent_id'] = self.feed['parent_id'] + max_id
                    self.feed['id'] = coalesce(self.feed['id'],0) + max_id
                    ldata_sql.append(self.feed.vals.copy())

                
                err = self._run_sql_lock(self.feed.insert_sql(all=True), ldata_sql, many=True)
                if err != 0: return -2, 'DB error: %a', err
                else: 
                    self._log(False, f'Feed data imported from {pfile}')
                    return 0, 'Feed data successfully imported from %a', pfile 


            elif mode == 'rules':
                if self.debug: print("Importing rules...")
                # Nullify IDs to avoid conflicts
                ldata_sql = []
                for l in ldata:
                    self.rule.populate(l)
                    self.rule['id'] = None
                    ldata_sql.append(self.rule.vals.copy())

                err = self._run_sql_lock(self.rule.insert_sql(all=True), ldata_sql, many=True)
                if err != 0: return -2, 'DB error: %a', err
                else:
                    self._log(False, f'Rules successfully imported from {pfile}')
                    return 0, 'Rules successfully imported from %a', pfile


