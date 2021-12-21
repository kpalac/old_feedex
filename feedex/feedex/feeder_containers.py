# -*- coding: utf-8 -*-
""" Containers for facilitating interface with SQL for Feedex

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
        if not isinstance(ilist, (list, tuple)):
            return -1
        self.clear()
        for i,e in enumerate(ilist):
            if (kargs.get('safe', False) and i > self.length): break
            self.vals[self.fields[i]] = e
    
    def merge(self, idict:dict):
        """ Merge a dictionary into container. Input dict keys must exist within this class """
        for m,v in idict.items(): self.vals[m] = v





    def __getitem__(self, key:str):
        if isinstance(key, str): return self.vals.get(key)

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
        if not isinstance(filter, (list, tuple)): return {}
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

    
