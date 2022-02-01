# -*- coding: utf-8 -*-
""" Entities classes:
     feeds - categories and channels

"""


from feedex_headers import *






class SQLContainer:
    """ Container class for SQL table. It helps to cleanly interface with SQL, output SQL statements 
        and keep data tidy. Lifts the burden of dealing with long lists with only indices as indicators,
        creates structure with named fields instead """

    def __init__(self, table:str, fields:list, **kargs):
        self.vals = {}
        self.fields = fields
        self.table = table
        self.clear()
        self.length = len(fields)

        self.replace_nones = kargs.get('replace_nones',False)




    def clear(self):
        """ Clear data """
        for f in self.fields: self.vals[f] = None

    def populate(self, ilist:list, **kargs):
        """ Populate container with a list (e.g. query result where fields are ordered as in DB (select * ...) """
        if not isinstance(ilist, (list, tuple)): return -1
        self.clear()
        for i,e in enumerate(ilist):
            if (kargs.get('safe', False) and i > self.length): break
            self.vals[self.fields[i]] = e
    
    def merge(self, idict:dict):
        """ Merge a dictionary into container. Input dict keys must exist within this class """
        for m,v in idict.items(): self.vals[m] = v





    def __getitem__(self, key:str):
        if isinstance(key, str): return self.vals.get(key)
        else: raise FeedexTypeError('Field name of an SQL container must be a str!')

    def get(self, key:str, *args):
        """ Get item from value table, optional param.: default value """
        if len(args) >= 1: default = args[0]
        else: default = None
        val = self.vals.get(key, default)
        if self.replace_nones and val is None: val = default
        return val



    def get_index(self, field:str):
        """ Get field index - useful for processing SQL result lists without populating the class """
        for idx,f in enumerate(self.fields):
            if field == f: return idx
        return -1
    

    def __setitem__(self, key:str, value):
        if key in self.fields: self.vals[key] = value

    def __delitem__(self, key:str):
        if key in self.fields: self.vals[key] = None


    def pop(self, field:str):
        if field in self.vals.keys(): self.vals.pop(field)

    def clean(self): # Pop all undeclared fields
        keys = tuple(self.vals.keys())
        for f in keys:
            if f not in self.fields:
                self.vals.pop(f)

    def __str__(self):
        ostring = ''
        for f in self.fields:
            ostring = f"{ostring}\n{f}:{self.vals[f]}"
        return ostring


    def __len__(self):
        olen = 0
        for f in self.vals.keys():
            if self.vals.get(f) is not None: olen += 1
        
        return olen


    def insert_sql(self, **kargs):
        """ Build SQL insert statement based on all or non-Null fields """
        cols = ''
        vs = ''
        for f in self.fields:
            if kargs.get('all',False) or self.vals.get(f) is not None :
                vs = f'{vs}, :{f}'
                cols = f'{cols}, {f}'

        return f'insert into {self.table} ({cols[1:]}) values ( {vs[1:]} )'



    def update_sql(self, **kargs):
        """ Build SQL update statement with all or selected (by filter) fields """
        sets = 'set '
        filter = kargs.get('filter')
        if filter is not None: do_filter = True
        else: do_filter = False

        for f in self.fields:
            if (not do_filter and self.vals.get(f) is not None) or (do_filter and f in filter):
                sets = f'{sets}{f} = :{f},'

        return f'update {self.table} {sets[:-1]} where {kargs.get("wheres","")}'





    def filter(self, filter:list, **kargs):
        """ Returns filtered dictionary of values"""
        odict = {}
        if not isinstance(filter, (list, tuple)): raise FeedexTypeError('Filter must be a list or a tuple!')
        for f in filter: odict[f] = self.vals[f]
        return odict

    
    def listify(self, **kargs):
        """ Return a sublist of fields specified by input field (key) list """
        filter = kargs.get('filter')
        if filter is None: filter = self.fields
        olist = []

        if kargs.get('in_order',True):
            for f in filter:
                if f in self.fields:
                    olist.append(self.vals[f])
        else:
            for f in self.fields:
                if f in filter:
                    olist.append(self.vals[f])
        return olist


    def tuplify(self, **kargs):
        """ Return a subtuple of fields specified by input field (key) list """
        return tuple(self.listify(in_order=kargs.get('in_order',True), filter=kargs.get('filter')))

    












class SQLContainerEditable(SQLContainer):
    """ Container with type validation and update queue """

    def __init__(self, table:str, fields:list, **kargs):

        SQLContainer.__init__(self, table, fields, **kargs)

        self.FX = None #DB connection

        self.types = kargs.get('types', ()) # Field types for validation

        self.to_update_sql = '' # Update command 
        self.to_update = [] # List of fields to be updated (names only, for values are in main dictionary)

        self.backup_vals = self.vals # Backup for faulty update

        self.exists = False # Was entity found in DB?
        self.updating = False # is update pending?

        self.immutable = () # Immutable field



    def set_interface(self, interface):
        if interface.__class__.__name__ == 'Feeder': self.FX = interface
        else: raise FeedexTypeError('Interface should be an instance of Feeder class!')


    def validate_types(self, **kargs):
        """ Validate field's type with given template """
        for f, v in self.vals.items():
            if v is not None and f in self.fields:
                vv = scast(v, self.types[self.get_index(f)], None)
                if vv is None: return f
                self.vals[f] = vv
                
        return 0


    def backup(self): self.backup_vals = self.vals.copy()
    def restore(self): self.vals = self.backup_vals.copy()


    def add_to_update(self, idict:dict, **kargs):
        """ Merge update queue with existing field values"""
        self.to_update.clear()
        self.backup()

        for f, v in idict.items():

            if f == 'id' or f in self.immutable: 
                self.updating = False
                self.restore()
                return -1, 'Editting field %a is not permitted!', f

            if v in ('NULL','NONE'): self.vals[f] = None
            else: self.vals[f] = v
            self.updating = True

        if self.updating: return 0
        else: return 1, 'Nothing to do'


    def constr_update(self):
        """ Consolidates updates list """
        self.to_update.clear()
        for u in self.fields:
            if u == 'id': continue
            if self.vals[u] != self.backup_vals.get(u): self.to_update.append(u)
        if len(self.to_update) == 0: return 1, 'No changes detected'

        self.to_update_sql = self.update_sql(filter=self.to_update, wheres=f'id = :id')
        self.to_update.append('id')

        return 0





class FeedContainerBasic(SQLContainerEditable):
    """ Basic container for Feeds - in case no DB interface is needed """
    def __init__(self, **kargs):
        SQLContainerEditable.__init__(self, 'feeds', FEEDS_SQL_TABLE, types=FEEDS_SQL_TYPES, **kargs)


    def name(self, **kargs):
        id = kargs.get('id', False)

        if id: id_str = f' ({self.vals["id"]})'
        else: id_str = ''

        name = coalesce(self.vals['name'],'')
        sname = f'{name}{id_str}'
        if name.strip() == '':
            name = coalesce(self.vals['title'],'')
            sname = f'{name}{id_str}'
            if name.strip() == '':
                name = coalesce(self.vals['url'],'')
                sname = f'{name}{id_str}'
                if name.strip() == '':
                    sname = scast(self.vals['id'], str, '<UNKNOWN>')
                    
        return sname










class FeedContainer(FeedContainerBasic):
    """ Container for Feeds """

    def __init__(self, FX, **kargs):
        FeedContainerBasic.__init__(self, **kargs)

        self.set_interface(FX)
        self.debug = self.FX.debug
        self.config = self.FX.config

        self.parent_feed = FeedContainerBasic()

        if kargs.get('id') is not None: self.get_by_id(kargs.get('id'))
        elif kargs.get('feed_id') is not None: self.get_feed_by_id(kargs.get('feed_id'))
        elif kargs.get('category_id') is not None: self.get_cat_by_id(kargs.get('category_id'))





    def get_feed_by_id(self, id:int):
        feed = self.FX.resolve_feed(id, load=True)
        if feed == -1: 
            self.exists = False
            cli_msg( (-1, 'Channel %a not found!', id) )
            return -1
        else:
            self.exists = True
            self.populate(feed)
            return 0

    def get_cat_by_id(self, id:int):     
        feed = self.FX.resolve_category(id, load=True)
        if feed == -1:
            self.exists = False
            cli_msg( (-1, 'Category %a not found!', id) )
            return -1
        else:
            self.exists = True
            self.populate(feed)
            return 0
    
    def get_by_id(self, id:int):
        for f in self.FX.MC.feeds:
            if f[self.get_index('id')] == id:
                self.populate(f)
                self.exists = True
                return 0

        cli_msg( (-1, 'Channel/Category %a not found!', id) )
        return -1



    def open(self, **kargs): self.FX.MC.ret_status = cli_msg(self.open(**kargs))
    def r_open(self, **kargs):
        """ Open in browser """
        if not self.exists: return -8, 'Nothing to open!'
        if self.vals['is_category'] == 1: return -7, 'Cannot open category!'

        if self.vals.get('link') is not None:
            err = ext_open(self.config, 'browser', self.vals.get('link',''), debug=self.debug)
        else: return -8, 'Empty URL!'

        if err == 0: return 0, 'Sent to browser (%a)', self.vals.get('link', '<UNKNOWN>')
        else: return err






    def validate(self, **kargs):
        """ Validate present values """
        err = self.validate_types()
        if err != 0: return -7, 'Invalid data type for %a', err

        if self.vals['is_category'] == 1:
            if self.vals['parent_id'] not in (None, 0): return -7, 'Nested categories are not allowed!'
            if self.vals.get('parent_category') not in (None, 0): return -7, 'Nested categories are not allowed!'
        else:
            if self.vals['handler'] in ('rss',) and not check_url(self.vals['url']): return -7, 'Not a valid URL! (%a)', self.vals['url']
            if self.vals['link'] is not None and not check_url(self.vals['link']): return -7, 'Not a valid URL! (%a)', self.vals['link']

            if 'parent_category' in self.vals.keys():
                if self.vals.get('parent_category') is not None:
                    feed = self.FX.resolve_category(self.vals['parent_category'], load=True)
                    if feed == -1: return -7, 'Category %a not found!', self.vals['parent_category']
                    self.parent_feed.populate(feed)
                    self.vals['parent_id'] = self.parent_feed['id']
                else: self.vals['parent_id'] = None

            elif 'parent_id' in self.vals.keys():
                if self.vals['parent_id'] is not None:
                    feed = self.FX.resolve_category(self.vals['parent_id'], load=True)
                    if feed == -1: return -7, 'Category %a not found!', self.vals['parent_id']
                    self.parent_feed.populate(feed)
                    self.vals['parent_id'] = self.parent_feed['id']
                else: self.vals['parent_id'] = None


            if self.vals['handler'] not in ('rss','local'): return -7, 'Invalid handler!'
            if self.vals['interval'] is None or self.vals['interval'] < 0: return -7, 'Interval must be >= 0!'
            if self.vals['autoupdate'] not in (None, 0, 1): return -7, 'Autoupdate flag must be 0 or 1!'
            if self.vals['auth'] is not None:
                if self.vals['auth'] not in ('detect','basic','digest'): return -7, 'Invalid authentication methon (must be NONE, detect, basic or digest)'
                if self.vals['passwd'] in ('',None): return -7, 'Password must be provided!'
                if self.vals['login'] in ('',None): return -7, 'Login must be provided!'
                
        if self.vals['deleted'] not in (None, 0, 1): return -7, 'Daleted flag must be 0 or 1!'

        return 0





    def do_update(self, **kargs): self.FX.MC.ret_status = cli_msg(self.r_do_update(**kargs)) 
    def r_do_update(self, **kargs):
        """ Apply edit changes to DB """
        if not self.updating: return 0, 'Nothing to do'
        if not self.exists: return -8, 'Nothing to do. Aborting...'

        if kargs.get('validate', True):
            err = self.validate()
            if err != 0: 
                self.restore()
                return err

        if coalesce(self.vals['deleted'],0) == 0 and coalesce(self.backup_vals['deleted'],0) >= 1: restoring = True
        else: restoring = False

        err = self.constr_update()
        if err != 0:
            self.restore()
            return err

        err = self.FX.run_sql_lock(self.to_update_sql, self.filter(self.to_update))
        if err != 0:
            self.restore()
            return -2, 'DB error: %a', err
        



        if self.FX.rowcount > 0:

            if not self.FX.single_run: 
                err = self.FX.load_feeds()
                if err != 0: return -2, f'Error reloading Feeds after successfull update: %a', err

            if restoring:
                err = self.FX.update_stats()
                if err != 0: return -2, f'Error updating DB stats after successfull update: %a', err
                err = self.FX.load_rules()
                if err != 0: return -2, f'Error reloading rules after successfull update: %a', err

            if self.vals['is_category'] == 1: stype = 'Category'
            else: stype = 'Channel'

            for i,u in enumerate(self.to_update):
                if u in self.immutable or u == 'id': del self.to_update[i]

            if len(self.to_update) > 1:
                self.FX.log(False, f'{stype} {self.vals["id"]} updated')
                return 0, f'{stype} %a updated successfuly!', self.name()
            else:
                for f in self.to_update:

                    if f == 'parent_id' and self.vals[f] not in (None, 0): 
                        self.FX.log(False, f'{stype} {self.name(id=True)} assigned to {self.parent_feed.name(id=True)}')
                        return 0, f'{stype} %a assigned to {self.parent_feed.name(id=True)}', self.name(id=True)

                    elif f == 'parent_id' and self.vals[f] in (None, 0): 
                        self.FX.log(False, f'{stype} {self.name(id=True)} detached from category')
                        return 0, f'{stype} %a detached from category', self.name(id=True)

                    elif f == 'error' and self.vals[f] in (None,0):
                        self.FX.log(False, f'{stype} {self.name(id=True)} marked as healthy')
                        return 0, f'{stype} %a marked as healthy', self.name(id=True)
                        
                    elif f == 'deleted' and self.vals[f] in (None,0):
                        self.FX.log(False, f'{stype} {self.name(id=True)} restored')
                        return 0, f'{stype} %a restored', self.name(id=True)

                    elif f == 'auth':
                        self.FX.log(False, f'Authentication method changed for {self.name(id=True)}')
                        return 0, f'Authentication method changed for %a', self.name(id=True)
                    elif f == 'passwd':
                        self.FX.log(False, f'Password changed for {self.name(id=True)}')
                        return 0, f'Password changed for %a', self.name(id=True)
                    elif f == 'login':
                        self.FX.log(False, f'Login changed for {self.name(id=True)}')
                        return 0, f'Login changed for %a', self.name(id=True)
                    elif f == 'domain':
                        self.FX.log(False, f'Domain (auth) changed for {self.name(id=True)}')
                        return 0, f'Domain (auth) changed for %a', self.name(id=True)

                    else:
                        self.FX.log(False, f'{stype} {self.name(id=True)} updated: {f} -> {self.vals.get(f,"<NULL>")}')
                        return 0, f'{stype} %a updated:  {f} -> {self.vals.get(f,"<NULL>")}', self.name(id=True)
                return 0, 'Nothing done'
        else:
            return 0, 'Nothing done'





    def update(self, idict, **kargs): self.FX.MC.ret_status = cli_msg(self.r_update(idict, **kargs))
    def r_update(self, idict, **kargs):
        """ Quick update with a value dictionary """
        if not self.exists: return -8, 'Nothing to do. Aborting...'

        err = self.add_to_update(idict)
        if err != 0: return err

        err = self.r_do_update(validate=True)
        return err
      



    def delete(self, **kargs): self.FX.MC.ret_status = cli_msg(self.r_delete(**kargs))
    def r_delete(self, **kargs):
        """ Remove channel/cat with entries and rules if required """
        if not self.exists: return -8, 'Nothing to do. Aborting...'

        deleted = self.vals['deleted']

        id = {'id': self.vals['id']}
        if deleted == 1:
            # Delete irreversably with all data and icon
            err = self.FX.run_sql_multi_lock( \
                (("delete from rules where learned = 1 and context_id in (select e.id from entries e where e.feed_id = :id)", id ),\
                ("delete from entries where feed_id = :id", id),\
                ("update feeds set parent_id = NULL where parent_id = :id", id),\
                ("delete from feeds where id = :id", id)) )
            if err == 0:
                if self.FX.MC.icons == {}: self.FX._load_icons()
                icon = self.FX.MC.icons.get(self.vals['id'])
                if icon is not None and icon.startswith(f'{FEEDEX_ICON_PATH}{DIR_SEP}feed_') and os.path.isfile(icon): os.remove(icon)

        else:
            # Simply mark as deleted
            err = self.FX.run_sql_lock("update feeds set deleted = 1 where id = :id", id)

        if err != 0: return -2, 'DB error: %a', err



        if self.FX.rowcount > 0:

            if not self.FX.single_run: 
                err = self.FX.refresh_data()
                if err != 0: return -2, f'Error reloading data after successfull delete: %a', err
            
            err = self.FX.update_stats()
            if err != 0: return -2, f'Error updating DB stats after successfull delete: %a', err


            if self.vals['is_category'] == 1: stype = 'Category'
            else: stype = 'Channel'

            if deleted == 1:
                self.vals['deleted'] == 2
                self.exists = False
                self.FX.log(False, f'{stype} {self.name()} ({self.vals["id"]}) deleted permanently')
                return 0, f'{stype} %a deleted permanently (with entries and rules)', f'{self.name()} ({self.vals["id"]})'
            else:
                self.vals['deleted'] = 1
                self.FX.log(False, f'{stype} {self.name()} ({self.vals["id"]}) deleted')
                return 0, f'{stype} %a deleted', f'{self.name()} ({self.vals["id"]})'
        else:
            return 0, 'Nothing done'





    def add(self, **kargs): self.FX.MC.ret_status = cli_msg(self.r_add(**kargs))
    def r_add(self, **kargs):
        """ Add feed to database """
        if kargs.get('new') is not None: 
            self.clear()
            self.merge(kargs.get('new'))

        self.vals['id'] = None
        
        if kargs.get('validate',True):
            err = self.validate()
            if err != 0: return err

        if self.vals['is_category'] == 0:
            self.vals['error'] = 0
            self.vals['interval'] = scast(self.vals.get('interval'), int, self.config.get('default_interval',45))

        self.clean()
        err = self.FX.run_sql_lock(self.insert_sql(all=True), self.vals)
        if err != 0: return -2, 'DB error: %a', err
        
        self.vals['id'] = self.FX.lastrowid
        self.FX.last_feed_id = self.vals['id']

        if not self.FX.single_run: 
            err = self.FX.load_feeds()
            if err != 0: return -2, f'Error reloading Feeds after successfull add: %a', err

        if self.vals['is_category'] == 1: stype = 'Category'
        else: stype = 'Channel'

        self.FX.log(False, f'{stype} {self.name()} ({self.vals["id"]}) added')
        return 0, f'{stype} %a added successfully', f'{self.name()} ({self.vals["id"]})'





    def add_from_url(self, **kargs): 
        for msg in self.g_add_from_url(**kargs): self.FX.update_ret_code( cli_msg(msg) )
    def g_add_from_url(self, **kargs):
        """ Wrapper for adding and updating channel from URL """
        if kargs.get('new') is not None: 
            self.clear()
            self.merge(kargs.get('new'))

        self.vals['is_category'] = 0
        self.vals['url'] = self.vals['url'].strip()
        if self.vals.get('handler') is None: self.vals['handler'] = 'rss'
        self.vals['interval'] = self.config.get('default_interval', 45)
        self.vals['autoupdate'] = 1

        err = self.validate()
        if err != 0:
            yield err
            return -7

        # Check if feed is already present (by URL)
        for f in self.FX.MC.feeds:
            if f[self.get_index('url')] == self.vals['url'] and f[self.get_index('deleted')] != 1:
                yield -7, 'Channel with this URL already exists (%a)', f'{f[self.get_index("name")]} ({f[self.get_index("id")]})'
                return -7

        err = self.r_add(validate=False)
        yield err
        if err[0] != 0: return -7

        if kargs.get('no_fetch',False): return 0 # Sometimes fetching must be ommitted to allow further editing (e.g. authentication)
        if self.vals['handler'] in ('local',): return 0 # ...also, don't fetch if channel is local etc.

        err = self.FX.load_feeds()
        if err == 0:
            for msg in self.FX.g_fetch(id=self.vals['id'], force=True, ignore_interval=True): yield msg
        else:
            yield -2, 'Error while reloading Feeds for fetching: %a', err
            return -2 
        
        return 0


