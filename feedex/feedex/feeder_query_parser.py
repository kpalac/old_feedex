# -*- coding: utf-8 -*-
""" Query Parser for Feedex"""

from feedex_headers import *







class FeederQueryParser:
    """Class for query parsing and rule matching for Feedex
       Requires an engine (class Feeder instance) to work
       Query types:
            0 - string matching
            1 - Full Text Search
            2 - Full Text Search - no stemming
        additional rule matching types:
            3 - REGEX matching
        types for learned rules:
            4 - Stemmed
            5 - Exact

    """


    def __init__(self, parent, **kargs):

        # Config and parent classes
        self.FX = parent
        self.config = kargs.get('config', DEFAULT_CONFIG)

        # Overload config passed in arguments
        self.debug = kargs.get('debug') # Triggers additional info at runtime

        self.ignore_images = kargs.get('ignore_images', self.config.get('ignore_images',False))
        self.wait_indef = kargs.get('wait_indef',False)

        # CLI display options
        self.output = kargs.get('output','cli')
        self.delim = kargs.get('delimiter','|')
        self.delim2 = kargs.get('delimiter2',';')
        self.delim_escape = kargs.get('delim_escape','\\')
        self.trunc = kargs.get('trunc',200)

        self.print = kargs.get('print',False)

        # Processed search phrase
        self.phrase = {}

        # Interface for managing history items
        self.history_item = HistoryItem(self.FX)

        # Container for query results
        self.result = SQLContainer('entries', RESULTS_SQL_TABLE)

        # Query results
        self.results = []

        self.snippets_lst = [] # Snippet lists for query results (string search)

        self.total_result_number = 0 #This is a result number in case a sumary is performed









##############################################################
#
#       QUERY PARSING AND MAIN SEARCH



    def _build_sql(self, phrase:dict, filters:dict, **kargs):
        """ Builds SQL query to get basic lists of results """

        # Construct condition string if search phrase is not empty 
        # Haldle wildcards, beginnings, endings, case sensitivity and such...
        vals = {}
        if not phrase['empty']:

            qtype = filters.get('qtype',0)
            field = filters.get('field')

            vals['phrase'] = phrase['sql']

            # String matching
            if qtype == 0:

                if not filters.get('case_ins', False):
                    if field is None: cond = "\n(e.title LIKE :phrase  ESCAPE '\\' OR e.desc LIKE :phrase  ESCAPE '\\' OR e.category LIKE :phrase  ESCAPE '\\' OR e.text LIKE :phrase  ESCAPE '\\')\n"
                    else: cond = f"\n( {PREFIXES[field]['sql']} LIKE :phrase ESCAPE '\\')\n"
                else:
                    if field is None: cond = "\n(lower(e.title) LIKE lower(:phrase)  ESCAPE '\\' OR lower(e.desc) LIKE lower(:phrase)  ESCAPE '\\' OR lower(e.category) LIKE lower(:phrase)  ESCAPE '\\' OR lower(e.text) LIKE lower(:phrase)  ESCAPE '\\')\n"
                    else: cond = f"\n( lower({PREFIXES[field]['sql']}) LIKE lower(:phrase) ESCAPE '\\')\n"


            # Full text search
            elif qtype == 1: cond = "\n( e.tokens LIKE :phrase ESCAPE '\\'  )"
            elif qtype == 2: cond = "\n( e.tokens_raw LIKE :phrase ESCAPE '\\' )"
            elif qtype == 4: cond = "\n( e.tokens LIKE :phrase ESCAPE '\\'  )"
            elif qtype == 5: cond = "\n( e.tokens_raw LIKE :phrase ESCAPE '\\' )"
 

        else: #string is empty
            cond = "\n1=1\n"


        # And this is a core of a query (with column listing from header constant)
        query = f"select {RESULTS_COLUMNS_SQL}\nwhere {cond}"

        #Add filtering according to given parameters
        if filters.get("feed") is not None:
            vals['feed_id'] = scast(filters.get('feed'), int, 0)
            query = f"{query}\nand ( f.id = :feed_id and f.is_category <> 1 )"

        elif filters.get("category") is not None:
            if filters.get("deleted", False): del_str = ''
            else: del_str = 'and coalesce(c.deleted,0) <> 1'
            vals['parent_category'] = scast(filters.get('category'), int, 0)
            query = f"""{query}\nand ((c.id = :parent_category or f.id = :parent_category) {del_str}) """
            
        if filters.get("id") is not None:
            vals['id'] = scast(filters.get('id'), int, 0)
            query = f"{query}\nand e.id = :id"

        if filters.get("raw_pubdate_from") is not None: 
            query = f"{query}\nand e.pubdate >= :raw_pubdate_from"
            vals['raw_pubdate_from'] = filters['raw_pubdate_from']
        if filters.get("raw_pubdate_to") is not None: 
            query = f"{query}\nand e.pubdate <= :raw_pubdate_to"
            vals['raw_pubdate_to'] = filters['raw_pubdate_to']
        if filters.get("raw_adddate_from") is not None: 
            query = f"{query}\nand e.adddate >= :raw_adddate_from"
            vals['raw_adddate_from'] = filters['raw_adddate_from']
        if filters.get("raw_adddate_to") is not None: 
            query = f"{query}\nand e.adddate <= :raw_adddate_to"
            vals['raw_adddate_to'] = filters['raw_adddate_to']
        

        if filters.get("today", False):
            vals['cdate'] = int(datetime.now().timestamp()) - 86400
            if vals['cdate'] > 0:
                query = f"{query}\nand e.pubdate >= :cdate"

        elif filters.get("last_week", False):
            vals['cdate'] = int(datetime.now().timestamp()) - 604800
            if vals['cdate'] > 0:
                query = f"{query}\nand e.pubdate >= :cdate"

        elif filters.get("last_month", False):
            vals['cdate'] = int(datetime.now().timestamp()) - (86400*31)
            if vals['cdate'] > 0:
                query = f"{query}\nand e.pubdate >= :cdate"

        elif filters.get("last_quarter", False):
            vals['cdate'] = int(datetime.now().timestamp()) - (86400*31*3)
            if vals['cdate'] > 0:
                query = f"{query}\nand e.pubdate >= :cdate"

        elif filters.get("last_six_months", False):
            vals['cdate'] = int(datetime.now().timestamp()) - (86400*31*6)
            if vals['cdate'] > 0:
                query = f"{query}\nand e.pubdate >= :cdate"

        elif filters.get("last_year", False):
            vals['cdate'] = int(datetime.now().timestamp()) - (86400*31*12)
            if vals['cdate'] > 0:
                query = f"{query}\nand e.pubdate >= :cdate"

        elif filters.get('last_hour', False):
            vals['cdate'] = int(datetime.now().timestamp()) - (60*60)
            if vals['cdate'] > 0:
                query = f"{query}\nand e.adddate >= :cdate"


        if filters.get('handler') is not None:
            vals['handler'] = scast(filters.get('handler'), str, '').lower()
            query = f"{query}\nand f.handler = :handler"


        if filters.get("importance",0) != 0:
            vals['importance'] = scast(filters.get('importance'), float, 0)
            query = f"{query}\nand e.importance >= :importance"

        if filters.get("unread",False):
            query = f"{query}\nand coalesce(e.read,0) = 0"
        elif filters.get("read",False):
            query = f"{query}\nand coalesce(e.read,0) > 0"

        if filters.get("flag") is not None:
            if filters.get('flag') == 0:
                query = f"{query}\nand coalesce(e.flag,0) > 0"
            elif filters.get('flag') == -1:
                query = f"{query}\nand coalesce(flag,0) = 0"
            else:  
                vals['flag'] = scast(filters.get('flag',0), int, 0)
                query = f"{query}\nand coalesce(e.flag,0) = :flag"

        if filters.get("deleted",False):
            query = f"{query}\nand (coalesce(e.deleted,0) = 1 or coalesce(f.deleted,0) = 1)"
        elif filters.get("deleted_entries",False):
            query = f"{query}\nand (coalesce(e.deleted,0) = 1)"
        else:
            query = f"{query}\nand coalesce(e.deleted,0) <> 1 and coalesce(f.deleted,0) <> 1"

        # This one is risky, so we have to be very careful every ID is a valis integer
        if filters.get('ID_list') is not None and type(filters.get('ID_list')) in (list,tuple) and len(filters.get('ID_list',[])) > 0:
            ids = ''
            for i in filters.get('ID_list',[]):
                i = scast(i, int, None)
                if i is None: continue
                ids = f'{ids}{i},'
            ids = ids[:-1]
            query = f"{query}\nand e.id in ({ids})"

        # Sorting options
        sort = filters.get('sort')
        default_sort = filters.get('default_sort')
        rev = filters.get('rev')
        if (sort is not None) and (type(sort) is str) and (len(sort) > 2):
            if sort.startswith('-'): desc=True
            else: desc=False
            sort = sort[1:]
            if sort not in ENTRIES_SQL_TABLE:
                cli_msg( (-5, _("%a is not a valid field! Changed to ID"), sort) )
                sort = 'id'
            query = f"{query}\norder by e.{sort}"
            if desc and not rev: query = f"{query} DESC"
            elif not desc and rev: query = f"{query} DESC"
    
        elif phrase.get('empty',False) and default_sort is not None:
            if default_sort.startswith('-'): desc=True
            else: desc=False
            default_sort = default_sort[1:]
            if default_sort not in ENTRIES_SQL_TABLE:
                cli_msg( (-5, _("%a is not a valid field! Changed to ID"), default_sort) )
                default_sort = 'id'
            query = f"{query}\norder by e.{default_sort}"
            if desc and not rev: query = f"{query} DESC"
            elif not desc and rev: query = f"{query} DESC"

        return query, vals







######################################################################
#   BASIC QUERY
#

    def query(self, string:str, filters:dict, **kargs):
        """ Main Query method
            Queries database with search string. """
        # This must be done in two stages:
        # SQL query, and phrase matching/filtering on SQL results (to get match count)

        qtype = self.FX.resolve_qtype(filters.get('qtype'))
        if qtype == -1:
            self.FX.MC.ret_status = cli_msg( (-5, _('Invalid query type!')) )
            return ()
        filters['qtype'] = qtype

        
        lang = filters.get('lang', 'heuristic')

        if qtype in (1,2,): self.FX.LP.set_model(lang)

        if filters.get('field') is not None:
            filters['field'] = self.FX.resolve_field(filters.get('field'))
            if filters['field'] == -1:
                self.FX.MC.ret_status = cli_msg( (-5, _('Invalid search field value!')) )
                return ()

        if filters.get('category') is not None:
            filters['category'] = self.FX.resolve_category(filters.get('category'))
            if filters['category'] == -1: 
                self.FX.MC.ret_status = cli_msg( (-5, _('Category not found!')) )
                return ()

        if filters.get('feed') is not None:
            filters['feed'] = self.FX.resolve_feed(filters.get('feed'))
            if filters['feed'] == -1:
                self.FX.MC.ret_status = cli_msg( (-5, _('Channel ID not found!')) )
                return ()

        if filters.get('feed_or_cat') is not None:
            filters['feed_or_cat'] = self.FX.resolve_f_o_c(filters.get('feed_or_cat'))
            if filters['feed_or_cat'] == -1:
                self.FX.MC.ret_status = cli_msg( (-5, _('Category or Channel not found!')) )
                return ()
            elif filters['feed_or_cat'][0] == -1:
                filters['category'] = filters['feed_or_cat'][1]
            elif filters['feed_or_cat'][1] == -1:
                filters['feed'] = filters['feed_or_cat'][0]



        rev = filters.get('rev',False)
        sort = filters.get('sort')
        
        case_ins = None
        if filters.get('case_ins') is True:
            case_ins = True
        if filters.get('case_sens') is True: 
            case_ins = False

        if case_ins is None:
            if self._has_caps(string):
                case_ins = False
                filters['case_ins'] = False
            else:
                case_ins = True
                filters['case_ins'] = True
        
        filters['flag'] = self._resolve_flag(filters.get('flag'))

        # Resolve date ranges
        if filters.get('date_from') is not None:
            date = convert_timestamp(filters['date_from'])
            if date is None: 
                self.FX.MC.ret_status = cli_msg( (-5, _('Could not parse date (date_from)!')) )
                return ()
            filters['raw_pubdate_from'] = date
        if filters.get('date_to') is not None:
            date = convert_timestamp(filters['date_to'])
            if date is None: 
                self.FX.MC.ret_status = cli_msg( (-5, _('Could not parse date (date_to)!')) )
                return ()
            filters['raw_pubdate_to'] = date

        if filters.get('date_add_from') is not None:
            date = convert_timestamp(filters['date_add_from'])
            if date is None: 
                self.FX.MC.ret_status = cli_msg( (-5, _('Could not parse date (date_add_from)!')) )
                return ()
            filters['raw_adddate_from'] = date
        if filters.get('date_add_to') is not None:
            date = convert_timestamp(filters['date_add_to'])
            if date is None: 
                self.FX.MC.ret_status = cli_msg( (-5, _('Could not parse date (date_add_to)!')) )
                return ()
            filters['raw_add_to'] = date

        if filters.get('last',False): filters['raw_adddate_from'] = self.FX.get_last()

        if filters.get('last_n') is not None:
            last_upd = self.FX.get_last(ord=filters['last_n'])
            if last_upd < 0:
                self.FX.MC.ret_status = cli_msg( (-5, _('Invalid value for last Nth update!')) )
                return ()
            else:
                filters['raw_adddate_from'] = last_upd



        rank =  kargs.get('rank',True)
        cnt = kargs.get('cnt',False)

        snippets = kargs.get('snippets',True)
        max_context_length = self.config.get('max_context_length', 500)

        if cnt or rank or snippets: regexify = True
        else: regexify = False

        if kargs.get('phrase') is None:
            self.phrase = self.FX.LP.f_phrase(string, qtype=qtype, case_ins=case_ins, field=filters.get('field'), sqlize=True, regexify=regexify)
        else: self.phrase = kargs.get('phrase',{})

        # Some queries do not work with wildcards
        if kargs.get('no_wildcards',False) and self.phrase.get('has_wildcards',False):
            self.FX.MC.ret_status = cli_msg( (-5, _('Wildcards are not allowed with this type of query!')) )
            self.results = ()
            return self.results

        (query, vals) = self._build_sql(self.phrase, filters)
        if self.debug in (1,5):
            print(f"\n\n'Query: \n{query}\n{vals}")
            print(f"Phrase: {self.phrase}")
  
        results_tmp = self.FX.qr_sql(query, vals, all=True)
        if self.FX.db_error is not None: 
            self.results = ()
            return self.results

        if self.debug in (1,5): print("Results: ", len(results_tmp))

        self.results = []

        # Rank results (if needed)
        # For this we will use last returned column and then replace it with ranking - a little crude, but works
        # SQL has its limitations and I need something beyond boolean matching

        # No point doing this if no string was given or there was only one result
        matched_docs_count = len(results_tmp)
        if (not self.phrase.get('empty',False)) and matched_docs_count > 0:
            if rank:
                doc_count = kargs.get('doc_count', self.FX.get_doc_count())
                idf = log10(doc_count/matched_docs_count)

            # Calculate ranking for each result
            for r in results_tmp:

                self.result.populate(r)
                if snippets:
                    self.snippets_lst = []
                    snips = []

                (matched, snips) = self.FX.LP.match_fields(self.phrase, qtype, filters.get('field'), entry=self.result, case_ins=case_ins, snippets=snippets)
                if matched <= 0: continue

                # Append snippets
                if snippets:
                    if qtype in (0, 1, 2,):
                        for s in snips:
                            if len(s) == 3 and (len(s[1]) <= max_context_length or max_context_length == 0): # check this to avoid showing long wildcard matches
                                self.snippets_lst.append(s)


                    self.result['snippets'] = self.snippets_lst.copy()

                # Append TF-IDF rank or match count - depending on what option was chosen
                if rank: # Construct TF-IDF
                    doc_len = scast(self.result["word_count"], int, 1)
                    if doc_len == 0: rnk = 0
                    else:
                        tf = matched/doc_len
                        # Final ranking measure - modify at your fancy
                        rnk = tf * idf
                    # append...
                    self.result['rank'] = rnk
                    self.result['count'] = matched

                if cnt:
                    # Append count if it was specified...
                    self.result['count'] = matched

                self.results.append(self.result.tuplify(all=True))

            # Sort results by rank or count if no other sorting method was chosen
            if sort is None:
                if cnt: self.results.sort(key=lambda x: x[self.result.get_index('count')], reverse=rev)
                elif rank: self.results.sort(key=lambda x: x[self.result.get_index('rank')], reverse=rev)
        
        
        else:
            self.results = results_tmp


        # Group results, if needed
        if kargs.get('print', self.print):
            node_col = -1
            node_title_col = None
            node_header = ()

        if kargs.get('allow_group',False):
            if filters.get('group') is not None: 
                self.results = self.group_results(self.results, filters.get('group'),filters.get('depth',self.config.get('default_depth',5)))
                if kargs.get('print', self.print):
                    node_col = len(RESULTS_SQL_TABLE_PRINT)
                    node_title_col = self.result.get_index('title')
                    node_header = ('Is Node?',)

        depth = scast(filters.get('depth'), int,0)
        if depth > 0 and filters.get('group') is None: 
            self.results = self.results[:depth]

        # Save phrase to history        
        if not kargs.get('no_history',False): 
            err = self.history_item.add(self.phrase, filters.get('feed'))
            if err != 0: self.FX.MC.ret_status = cli_msg(err)


        # Display results if needed
        if kargs.get('print', self.print):
            if self.output == 'short': columns = NOTES_PRINT
            elif self.output == 'headlines': columns = HEADLINES_PRINT
            else: columns = RESULTS_SHORT_PRINT1
            self.cli_table_print(RESULTS_SQL_TABLE_PRINT + node_header, self.results, mask=columns, 
                                flag_col=self.result.get_index('flag'), read_col=self.result.get_index('read'), del_col=self.result.get_index('deleted'), 
                                date_col=self.result.get_index('pubdate_short'), node_col=node_col, node_title_col=node_title_col)

        return self.results








####################################################################################################3
#
#       COMPOSITE QUERIES
#




    def find_similar(self, id, **kargs):
        """ Find entry similar to specified by ID based on extracted features """
        id = scast(id, int, 0)
        entry = EntryContainer(self.FX, id=id)
        if not entry.exists:
            self.FX.MC.ret_status = cli_msg( (-8, _('Nothing to search. Aborting...')) )
            return ()

        limit = kargs.get('limit',self.config.get('default_similarity_limit',20)) # Limit results
        rev = kargs.get('rev',False)  # Reverse sort order
        kargs['limit'] = None
        kargs['rev'] = None

        # Get or generate rules
        rules = self.FX.qr_sql("select * from rules where context_id=:id order by weight desc", {'id':id} , all=True)
        if self.FX.db_error is not None: return ()

        if rules in (None, [], [None]):    

            entry.relearn_keywords()

            rules = self.FX.qr_sql("select * from rules where context_id=:id order by weight desc", {'id':id} , all=True)
            if rules in (None, [], [None], ()):
                if self.debug in (1,5): print("Nothing to find...")
                return ()
        if self.config.get('default_similar_weight', 2) > 0:
            self.FX.run_sql_lock(f"update entries set read = coalesce(read,0) + {self.config.get('default_similar_weight', 2)}  where id = :id", {'id':id} )

        # Search for keywords in entries one by one and record weighted results
        i = 0
        filters = kargs.copy()
        filters['lang'] = entry.get('lang','heuristic')
        filters['case_ins'] = True
        filters['rev'] = False
        doc_cnt = self.FX.get_doc_count()
        freq_dist = {}

        for r in rules:
            if i >= limit: break

            qphrase = r[self.FX.rule.get_index('string')]

            if r[self.FX.rule.get_index('type')] == 5: filters['qtype'] = 5
            else: filters['qtype'] = 4

            if r[self.FX.rule.get_index('case_insensitive')] == 1: filters['case_ins'] = True
            else: filters['case_ins'] = False
            if r[self.FX.rule.get_index('field_id')] is not None:
                filters['field'] = r[self.FX.rule.get_index('field_id')]

            self.query(qphrase, filters, rank=False, cnt=True, doc_count=doc_cnt, snippets=False, print=False, no_history=True, no_wildcards=True)
            if self.FX.db_error is not None: return ()

            if self.results is not None and len(self.results) > 0:
                for rs in self.results:
                    self.result.populate(rs)
                    
                    w = self.result.get('count',0) * coalesce(r[self.FX.rule.get_index('weight')],0) * self.result['weight']
                    freq_dist[self.result['id']] = freq_dist.get(self.result['id'],0) + w
                i += 1

        # Create freq distribution of results-weight
        freq_dist_sorted = []
        for fd, v in freq_dist.items():
            freq_dist_sorted.append((fd, v))
        freq_dist_sorted.sort(key=lambda x: x[-1], reverse=True)
        
        # Construct final list of IDs
        ids=[]
        for i,idd in enumerate(freq_dist_sorted):
            if i >= limit:
                break
            ids.append(idd[0])
        
        # ... and query for them
        if len(ids) > 0:
            results_tmp = self.query('*', {'ID_list': ids} ,rank=False, cnt=False, snippets=False, print=False, no_history=True)
            if self.FX.db_error is not None: return ()
        else:
            results_tmp = []
            return -1

        self.results = []
        # Append similarity measure at the end of each result to sort by it later
        for r in results_tmp:
            result_tmp = list(r)
            result_tmp.append(None)
            result_tmp.append(None)
            result_tmp[self.result.get_index('rank')] = freq_dist.get(result_tmp[self.result.get_index('id')],0)
            self.results.append(result_tmp)

        self.results.sort(key=lambda x: x[self.result.get_index('rank')], reverse=-rev)

        if kargs.get("print",self.print):
            if self.output == 'short': columns = NOTES_PRINT
            elif self.output == 'headlines': columns = HEADLINES_PRINT
            else: columns = RESULTS_SHORT_PRINT1
            
            self.cli_table_print(RESULTS_SQL_TABLE_PRINT, self.results, mask=columns, 
                            read_col=self.result.get_index('read'), flag_col=self.result.get_index('flag'), del_col=self.result.get_index('deleted'), 
                            number_footnote=_('similar documents'), date_col=self.result.get_index('pubdate_short'))
    

        else: return self.results






    def relevance_in_time(self, id, **kargs):
        """ Gets keywords from entry and produces time series for them """
        id = scast(id, int, 0)

        entry = EntryContainer(self.FX, id=id)
        if not entry.exists:
            self.FX.MC.ret_status = cli_msg( (-8, _('Nothing to search. Aborting...')) )
            return ()

        group = kargs.get('group','daily')
        col_name = n_('Month')
        plot = kargs.get('plot',False)
        term_width = kargs.get('term_width',150)
        limit = kargs.get('limit',self.config.get('default_similarity_limit',20)) # Limit results
        rev = kargs.get('rev',False)  # Reverse sort order

        kargs['limit'] = None
        kargs['rev'] = None
        kargs['group'] = None
        kargs['plot'] = None

        if group == 'hourly': col_name = n_('Hour')
        elif group == 'daily': col_name = n_('Day')
        elif group == 'monthly': col_name = n_('Month')
        else:
            self.FX.MC.ret_status = cli_msg( (-5, _('Invalid grouping! Must be: %a'), 'daily, monthly or hourly') )
            return ()

        # Get or generate rules
        rules = self.FX.qr_sql("select * from rules where context_id=:id order by weight desc", {'id':id} , all=True)
        if self.FX.db_error is not None: return ()

        if rules in (None, [], [None]):    

            entry.relearn_keywords()
            rules = self.FX.qr_sql("select * from rules where context_id=:id order by weight desc", {'id':id} , all=True)
            if rules in (None, [], [None], ()):
                if self.debug in (1,5): print("Nothing to find...")
                return ()
        if self.config.get('default_similar_weight', 2) > 0:
            self.FX.run_sql_lock(f"update entries set read = coalesce(read,0) + {self.config.get('default_similar_weight', 2)}  where id = :id", {'id':id} )

        # Search for keywords in entries one by one and record weighted results
        i = 0
        filters = kargs.copy()
        filters['lang'] = entry.get('lang','heuristic')
        filters['case_ins'] = True
        filters['rev'] = False
        doc_cnt = self.FX.get_doc_count()
        freq_dict = {}

        for r in rules:
            if i >= limit: break

            qphrase = r[self.FX.rule.get_index('string')]

            if r[self.FX.rule.get_index('type')] == 5: filters['qtype'] = 5
            else: filters['qtype'] = 4

            if r[self.FX.rule.get_index('case_insensitive')] == 1: filters['case_ins'] = True
            else: filters['case_ins'] = False
            if r[self.FX.rule.get_index('field_id')] is not None:
                filters['field_id'] = r[self.FX.rule.get_index('field_id')]

            self.query(qphrase, filters, rank=False, cnt=True, doc_count=doc_cnt, snippets=False, print=False, no_history=True, no_wildcards=True)
            if self.FX.db_error is not None: return ()

            if self.results is not None and len(self.results) > 0:
                for rs in self.results:
                    self.result.populate(rs)
                    
                    cnt = scast(self.result['count'], int, 0)
                    dtetime = scast(self.result['pubdate'], int, 0)

                if group == 'hourly':
                    hour = time.strftime('%Y-%m-%d %H', time.localtime(dtetime)) + ":00:00"
                    freq_dict[hour] = freq_dict.get(hour,0) + cnt

                elif group == 'daily':
                    day = time.strftime('%Y-%m-%d', time.localtime(dtetime)) + " 00:00:00"
                    freq_dict[day] = freq_dict.get(day,0) + cnt
                    
                elif group == 'monthly':
                    month = time.strftime('%Y-%m', time.localtime(dtetime)) + "-01 00:00:00"
                    freq_dict[month] = freq_dict.get(month,0) + cnt                    

            i += 1

        
        data_points = []
        max = 0
        for f in freq_dict.keys():
            freq = freq_dict.get(f,0)
            if max < freq:
                max = freq
            data_points.append([f, freq])

        data_points.sort(key=lambda x: x[0], reverse=False)

        date_start = data_points[0][0]
        date_end = data_points[-1][0]

        time_series = []
        ts = date_start

        if group == "hourly": time_series.append([date_start[:-3], freq_dict[date_start]])
        elif group == "daily": time_series.append([date_start[:-9], freq_dict[date_start]])
        elif group == "monthly": time_series.append([date_start[:-12], freq_dict[date_start]])
            
        mon_rel = relativedelta(months=1)
        day_rel = relativedelta(days=1)

        # Populate every step on date, even if there were 0 occurences
        while ts != date_end:
            tst = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
            if group == "hourly":
                tst += timedelta(hours=1)
                ts_disp = tst.strftime("%Y-%m-%d %H:%M")
            elif group == "daily":
                tst += day_rel
                ts_disp = tst.strftime("%Y-%m-%d")
            elif group == "monthly":
                tst += mon_rel
                ts_disp = tst.strftime("%Y-%m")
            
            ts = tst.strftime("%Y-%m-%d %H:%M:%S")
            fr = freq_dict.get(ts,0)
            time_series.append([ts_disp,fr])

        if rev: time_series.sort(key=lambda x: x[0], reverse=True)           

        if kargs.get('print',self.print) and not plot:
            self.cli_table_print([col_name, n_("Frequency")], time_series, output='csv')

        if plot:
            self.cli_plot(time_series, max, term_width)

        self.results = time_series
        return time_series
 
                








    def term_context(self, string:str, **kargs):
        """ Get term's context (find entries and print immediate surroundings) """
        string = scast(string, str, '')
        if string == '': 
            self.results = ()
            return self.results
        
        self.query(string, kargs, count=False, rank=True, snippets=True, print=False)
        if self.FX.db_error is not None: return ()

        context = SQLContainer('entries', RESULTS_SQL_TABLE_PRINT + (n_("Context"),) )
        
        results_tmp = []
        
        self.total_result_number = len(self.results)

        for r in self.results:    
            self.result.populate(r)

            for s in self.result['snippets']:
                
                fields = self.result.listify(all=True)
                fields.append((s,))
                context.populate(fields)
                results_tmp.append(context.tuplify())

        self.results = results_tmp

        if kargs.get('print',self.print):
            self.cli_table_print(context.fields, self.results, output='cli_noline', 
                                mask=(context.get_index('Date'), context.get_index('Context'), context.get_index('ID'), context.get_index('Source (ID)'), context.get_index('Published - Timestamp'), context.get_index('Rank'), context.get_index('Count'), ), 
                                date_col=context.get_index('Date'), del_col=context.get_index('Deleted?'), read_col=context.get_index('Read'), flag_col=context.get_index('Flag'),
                                total_number=self.total_result_number, total_number_footnote=_('entries'), number_footnote=_('contexts'))
        
        else:
            return self.results







    def term_net(self, term:str, **kargs):
        """ Show terms/features connected to a given term by analising contexts """
        

        term = scast(term, str, '').strip()
        if term == '':
            self.results = ()
            return self.results

        phrase = self.FX.LP.f_phrase(term, qtype=1, case_ins=True, sqlize=True, regexify=True)
        filters = {'qtype' : 1, 'lang' : kargs.get('lang','heuristic'), 'case_ins' : True, 'read':True}        

        if phrase.get('empty',False): return ()
        if phrase.get('has_wildcards',False): return ()

        # First - try saved rules
        self.results = self.FX.qr_sql(TERM_NET_SQL, {'name':term} , all=True)
        if self.FX.db_error is not None: return ()

        #If the term is not in the rules, query the database
        if self.results in ((),[],None, (None,)):

            self.query(term, filters, rank=False, cnt=False, snippets=False, print=False, no_history=True, no_wildcards=True, phrase=phrase)
            if self.FX.db_error is not None: return ()

            if self.results not in ((),[],None, (None,)):
                ids = []
                for r in self.results:
                    id = scast(slist(r, self.result.get_index('id'), 0), int, 0)
                    ids.append( scast(id, str, "''") )
                ids = ', '.join(ids)
            
                # Get rules from entries that input term comes from 
                sql = f"select r.name as name, r.weight as weight, count(r.context_id) as c from rules r where r.context_id in ( {ids} ) group by r.name, r.weight"

                if self.debug in (1,5): print(sql)

                self.results = self.FX.qr_sql(sql, all=True)
                if self.FX.db_error is not None: return ()
        
        self.results.sort(key=lambda x: x[1], reverse=kargs.get('rev', False))

        self.phrase = phrase
        # Save phrase to history        
        if not kargs.get('no_history',False):
            err = self.history_item.add(self.phrase, filters.get('feed'))
            if err != 0: self.FX.MC.ret_status = cli_msg(err)        

        if kargs.get('print',self.print):
            self.cli_table_print((n_("Term"), n_("Weight"), n_("Documents")), self.results, output='csv')
            if self.debug in (1,5): print(len(self.results), " results")
        else:
            return self.results






    def terms_for_entry(self, id:int, **kargs):
        """ Output terms/features learned from an entry """

        SQL='select r.name, r.weight from rules r where r.context_id = :id order by r.weight'
        if kargs.get('rev',False): SQL=f'{SQL} DESC'
        else: SQL=f'{SQL} ASC'

        self.results = self.FX.qr_sql(SQL, {'id':id} , all=True)
        if self.results in ([],None,[None]) and not kargs.get('no_recalc',False):
            entry = EntryContainer(self.FX, id=id)
            if not entry.exists: 
                self.FX.MC.ret_status = -8
                return ()
            entry.relearn_keywords()
            self.results = self.FX.qr_sql(SQL, {'id':id} , all=True)

        if kargs.get('print',self.print):
            self.cli_table_print((n_("Term"), n_("Weight")), self.results, output='csv')
            if self.debug in (1,5): print(len(self.results), " results")
        else:
            return self.results
                



    def rules_for_entry(self, id:int, **kargs):
        """ Output rules that match and contributed to importance of given entry """
        do_print = kargs.get('print',True)
        entry = EntryContainer(self.FX, id=id)
        rule = SQLContainer('rules',RULES_SQL_TABLE_RES)
        if not entry.exists: 
            self.FX.MC.ret_status = -8
            return ()

        importance, flag, best_entries, flag_dist, results = entry.matched_rules()
        self.results = self.show_rules(results=results, print=False)

        print(f"""{_('Rules matched for entry')} {entry['id']} ({entry.name()}):
--------------------------------------------------------------------------------------------------------""")

        self.cli_table_print(RULES_SQL_TABLE_RES_PRINT, self.results, mask=PRINT_RULES_FOR_ENTRY, interline=False, output='short', flag_col=rule.get_index('flag'))        

        print(f"""--------------------------------------------------------------------------------------------------------
{_('Matched rules:')} {len(self.results)}

{_('Calculated Importance:')} {importance:.3f}, {_('Calculated Flag:')} {flag:.0f}
{_('Saved Importance:')} {entry['importance']:.3f}, {_('Saved Flag:')} {entry['flag']:.0f}
{_('Weight:')} {entry['weight']:.3f}
--------------------------------------------------------------------------------------------------------
{_('Flag distriution:')}""")

        for f,v in flag_dist.items(): print(f"{self.FX.get_flag_name(f)} ({f}): {v:.3f}")

        print(f"""--------------------------------------------------------------------------------------------------------
{_('Most similar read Entries:')}""")
        
        estring=''
        for e in best_entries: 
            estring = f'{estring}{e}, '
        print(estring)

        return self.results






    def term_in_time(self, term:str, **kargs):
        """ Get term frequency in time and output as a table of data points or a plot in terminal """
        term = scast(term, str, '')
        if term == '':
            self.results = ()
            return self.results
    
        group = kargs.get('group','daily')
        col_name = n_('Month')
        plot = kargs.get('plot',False)
        term_width = kargs.get('term_width',150)
        rev = kargs.get('rev', False)
        kargs['rev'] = False

        self.query(term, kargs, rank=False, cnt=True, snippets=False, print=False)
        if self.FX.db_error is not None: return ()

        if len(self.results) == 0:
            self.results = ()
            return ()

        if group == 'hourly': col_name = n_('Hour')
        elif group == 'daily': col_name = n_('Day')
        elif group == 'monthly': col_name = n_('Month')
        else: 
            self.FX.MC.ret_status = cli_msg( (-5, _('Invalid grouping! Must be: %a'), 'daily, monthly or hourly') )
            return ()

        freq_dict = {}
        data_points = []
        # Construct data table without zeroes
        for r in self.results:

            self.result.populate(r)
            cnt = scast(self.result['count'], int, 0)
            dtetime = scast(self.result['pubdate'], int, 0)

            if group == 'hourly':
                hour = time.strftime('%Y-%m-%d %H', time.localtime(dtetime)) + ":00:00"
                freq_dict[hour] = freq_dict.get(hour,0) + cnt

            elif group == 'daily':
                day = time.strftime('%Y-%m-%d', time.localtime(dtetime)) + " 00:00:00"
                freq_dict[day] = freq_dict.get(day,0) + cnt
                    
            elif group == 'monthly':
                month = time.strftime('%Y-%m', time.localtime(dtetime)) + "-01 00:00:00"
                freq_dict[month] = freq_dict.get(month,0) + cnt


        max = 0
        for f in freq_dict.keys():
            freq = freq_dict.get(f,0)
            if max < freq:
                max = freq
            data_points.append([f, freq])

        data_points.sort(key=lambda x: x[0], reverse=False)

        date_start = data_points[0][0]
        date_end = data_points[-1][0]

        time_series = []
        ts = date_start

        if group == "hourly": time_series.append([date_start[:-3], freq_dict[date_start]])
        elif group == "daily": time_series.append([date_start[:-9], freq_dict[date_start]])
        elif group == "monthly": time_series.append([date_start[:-12], freq_dict[date_start]])
            
        mon_rel = relativedelta(months=1)
        day_rel = relativedelta(days=1)

        # Populate every step on date, even if there were 0 occurences
        while ts != date_end:
            tst = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
            if group == "hourly":
                tst += timedelta(hours=1)
                ts_disp = tst.strftime("%Y-%m-%d %H:%M")
            elif group == "daily":
                tst += day_rel
                ts_disp = tst.strftime("%Y-%m-%d")
            elif group == "monthly":
                tst += mon_rel
                ts_disp = tst.strftime("%Y-%m")
            
            ts = tst.strftime("%Y-%m-%d %H:%M:%S")
            fr = freq_dict.get(ts,0)
            time_series.append([ts_disp,fr])

        if rev: time_series.sort(key=lambda x: x[0], reverse=True)  

        if kargs.get('print',self.print) and not plot:
            self.cli_table_print([col_name, n_("Frequency")], time_series, output='csv')

        if plot:
            self.cli_plot(time_series, max, term_width)

        self.results = time_series
        return time_series






    def group_results(self, table:list, group_by:str, depth:int, **kargs):
        """ Creates and prints a tree with results grouped by a column """
        if group_by not in ('category', 'feed', 'flag', 'hourly', 'daily', 'monthly'): 
            self.FX.MC.ret_status = cli_msg( (-5, _('Invalid grouping! Must be: %a'), 'category, feed, flag, hourly, daily or monthly') )
            self.results = ()
            return ()

        results_tmp = []
        node_tmp = []
        count = 0

        if self.print: table.reverse()

        if group_by in ('category','feed'):
            feed = FeedContainerBasic()
            feeds = self.FX.MC.feeds.copy()
            if self.print: feeds.sort(key=lambda x: coalesce(x[feed.get_index('display_order')],0), reverse=True)

        if group_by == 'category':
            parent_id_ix = self.result.get_index('parent_id')
            for f in feeds:
                if coalesce(f[feed.get_index('is_category')],0) == 1:
                    node_tmp = []
                    count = 0
                    feed.populate(f)
                    for r in table:
                        if r[parent_id_ix] == feed['id']:
                            count += 1
                            node_tmp.append(list(r) + [0,])
                            if count >= depth: break

                    if count > 0:
                        self.result.clear()
                        self.result['title'] = f'{feed.name()} ({count})'
                        self.result['flag_name'] = f[feed.get_index('icon_name')]
                        results_tmp.append(self.result.listify() + [1,])
                        results_tmp = results_tmp + node_tmp

        elif group_by == 'feed':
            feed_id_ix = self.result.get_index('feed_id')            
            for f in feeds:
                if coalesce(f[feed.get_index('is_category')],0) != 1:
                    node_tmp = []
                    count = 0
                    feed.populate(f)
                    for r in table:
                        if r[feed_id_ix] == feed['id']:
                            count += 1
                            node_tmp.append(list(r) + [0,])
                            if count >= depth: break

                    if count > 0:
                        self.result.clear()
                        self.result['title'] = f'{feed.name()} ({count})'
                        self.result['flag_name'] = f[feed.get_index('icon_name')]
                        self.result['feed_id'] = f[feed.get_index('id')]
                        results_tmp.append(self.result.listify() + [1,])
                        results_tmp = results_tmp + node_tmp

        elif group_by == 'flag':
            flag_ix = self.result.get_index('flag')
            for f in self.FX.MC.flags.keys():
                node_tmp = []
                count = 0
                for r in table:
                    if r[flag_ix] == f:
                        count += 1
                        node_tmp.append(list(r) + [0,])
                        if count >= depth: break

                if count > 0:
                    self.result.clear()
                    self.result['title'] = f'{self.FX.get_flag_name(f)} ({count})'
                    self.result['flag'] = f
                    results_tmp.append(self.result.listify() + [1,])
                    results_tmp = results_tmp + node_tmp




        elif group_by in ('hourly', 'daily', 'monthly'):

            pubdate_ix = self.result.get_index('pubdate')
            timetable = []
            tt_added = []

            dmonth = relativedelta(months=+1)
            dday = relativedelta(days=+1)
            dhour = relativedelta(hours=+1)
            dsecond_minus = relativedelta(seconds=-1)

            for r in table:

                dtetime = scast(r[pubdate_ix], int, 0)

                if group_by == 'hourly':
                    hour = f"{time.strftime('%Y-%m-%d %H', time.localtime(dtetime))}:00:00"
                    if hour in tt_added: continue
                    beg = datetime.strptime(hour, "%Y-%m-%d %H:%M:%S")
                    end = beg + dhour + dsecond_minus
                    timetable.append( (beg.timestamp(), end.timestamp(), hour) )
                    tt_added.append(hour)

                elif group_by == 'daily':
                    day_disp = time.strftime('%Y-%m-%d', time.localtime(dtetime))
                    day =  f"{day_disp} 00:00:00"
                    if day in tt_added: continue
                    beg = datetime.strptime(day, "%Y-%m-%d %H:%M:%S")
                    end = beg + dday + dsecond_minus
                    timetable.append( (beg.timestamp(), end.timestamp(), day_disp) )
                    tt_added.append(day)

                elif group_by == 'monthly':
                    month_disp = time.strftime('%Y-%m', time.localtime(dtetime))
                    month = f"{month_disp}-01 00:00:00"
                    if month in tt_added: continue
                    beg = datetime.strptime(month, "%Y-%m-%d %H:%M:%S")
                    end = beg + dmonth + dsecond_minus
                    timetable.append( (beg.timestamp(), end.timestamp(), month_disp) )
                    tt_added.append(month)

            if self.print: timetable.sort(key=lambda x: x[2], reverse=False)
            else: timetable.sort(key=lambda x: x[2], reverse=True)

            for t in timetable:
                node_tmp = []
                count = 0
                
                beg = t[0]
                end = t[1]
                ts = t[2]

                for r in table:
                    pubdate = scast(r[pubdate_ix], int, 0)
                    if pubdate >= beg and pubdate <= end:
                        count += 1
                        node_tmp.append(list(r) + [0,])
                        if count >= depth: break
                    
                if count > 0:
                    self.result.clear()
                    self.result['title'] = ts
                    self.result['flag_name'] = 'calendar'
                    results_tmp.append(self.result.listify() + [1,])
                    results_tmp = results_tmp + node_tmp


        self.results = results_tmp
        return self.results





#####################################################################
#
#       MISC DISPLAY METHODS
#
#

    def list_feeds(self, **kargs):
        """Utility for listing feeds and categories (for GUI and CLI)"""
        # This tells us if we want a CLI output
        self.reults = []
        feed = SQLContainer('feeds',FEEDS_SQL_TABLE)
        cat = FeedContainerBasic()

        cats = kargs.get('cats',False)

        feeds = self.FX.MC.feeds.copy()
        feeds.sort(key=lambda x: coalesce(x[feed.get_index('display_order')],0), reverse=True)
        
        for f in feeds:
            f = list(f)
            if cats: 
                if coalesce(f[feed.get_index('is_category')],0) == 0: continue
                id = f[feed.get_index('id')]
                count = 0
                for ff in feeds:
                    if ff[feed.get_index('parent_id')] == id and ff[feed.get_index('deleted')] != 1: count += 1
                f.append(count)

            parent_id = coalesce(f[feed.get_index('parent_id')],0)
            if parent_id != 0:
                for ff in feeds:
                    if ff[feed.get_index('id')] == parent_id: 
                        cat.clear()
                        cat.populate(ff)
                        f.append(cat.name())
            
            self.results.append(f)


        if kargs.get("print",self.print):
            if not cats:
                self.cli_table_print(FEEDS_SQL_TABLE_PRINT + (n_("Feedex Category"),), self.results, mask=FEEDS_SHORT_PRINT, number_footnote=_('rergistered channels'),
                            del_col=feed.get_index('deleted'), passwd_col=feed.get_index('passwd'))
            else:
                self.cli_table_print(FEEDS_SQL_TABLE_PRINT + (n_("No of Children"),), self.results, mask=CATEGORIES_PRINT, number_footnote=_('categories'),
                            del_col=feed.get_index('deleted'), passwd_col=feed.get_index('passwd'))

        else: return self.results



    def cat_tree_print(self, **kargs):
        """ Display Feed/Category tree in CLI """
        self.results = []
        feed = SQLContainer('feeds',FEEDS_SQL_TABLE)

        feeds = self.FX.MC.feeds.copy()
        feeds.sort(key=lambda x: x[feed.get_index('display_order')], reverse=True)

        for c in feeds:
            if coalesce(c[feed.get_index('deleted')],0) == 1: continue
            subtable = []
            id = coalesce(c[feed.get_index('id')],0)
            if coalesce(c[feed.get_index('is_category')],0) == 1:
                cat_str = f"""{id} | {c[feed.get_index('name')]} | {c[feed.get_index('subtitle')]}"""
                print(cat_str)
                for f in feeds:
                    if coalesce(f[feed.get_index('deleted')],0) == 1: continue
                    if f[feed.get_index('parent_id')] == id: subtable.append(f)
                for f in subtable:
                    feed_str = f"""    |-------------- {f[feed.get_index('id')]} | {f[feed.get_index('name')]} | {f[feed.get_index('title')]} | {f[feed.get_index('subtitle')]} | {f[feed.get_index('url')]} | {f[feed.get_index('link')]} | {f[feed.get_index('handler')]}"""
                    print(feed_str)

        subtable = []
        for f in feeds:
            if coalesce(f[feed.get_index('deleted')],0) == 1: continue
            if coalesce(f[feed.get_index('is_category')],0) == 1: continue
            if f[feed.get_index('parent_id')] is None: subtable.append(f)
        
        for f in subtable:
            feed_str = f"""{f[feed.get_index('id')]} | {f[feed.get_index('name')]} | {f[feed.get_index('title')]} | {f[feed.get_index('subtitle')]} | {f[feed.get_index('url')]} | {f[feed.get_index('link')]} | {f[feed.get_index('handler')]}"""
            print(feed_str)





    def list_flags(self, **kargs):
        """ List all available flags """
        self.results = []
        for f, vals in self.FX.MC.flags.items():
            flag = []
            flag.append(f)
            for v in vals: flag.append(v)
            self.results.append(flag)
 
        if kargs.get("print",self.print):
                self.cli_table_print(FLAGS_SQL_TABLE_PRINT, self.results, number_footnote='flags', flag_col=0) 
        else: return self.results



    def read_feed(self, id:int, **kargs):
        """ Print out detailed feed data """
        lfield = self.FX.qr_sql("select f.*, f1.name from feeds f left join feeds f1 on f1.id = f.parent_id where f.id = :id", {'id':id} , one=True)
        if self.FX.db_error is not None: return ''
        return self.cli_feed_print(lfield, to_var=kargs.get('to_var',False))


    def read_entry(self, id:int, **kargs):
        """ Wrapper for displaying an entry """
        lentry = self.FX.qr_sql(f"select {RESULTS_COLUMNS_SQL} where e.id = :id", {'id':id} , one=True)
        lrules = self.FX.qr_sql("""select name from rules r where r.context_id = :id""", {'id':id} , all=True, ignore_errors=False) 
        if self.FX.db_error is not None: return ''
        if self.debug in (1,8) or kargs.get('to_var',False):
            self.FX.entry.populate(self.FX.qr_sql(f"select * from entries e where e.id = :id", {'id':id} , one=True))
            if self.FX.db_error is not None: return ''
            ostring = self.FX.entry.__str__()
            if kargs.get('to_var',False):
                return ostring
            print(ostring)
        else:
            self.cli_entry_print(lentry, lrules)





    def show_rules(self, **kargs):
        """ Show manually added rules """
        results = kargs.get('results', self.FX.qr_sql("""select * from rules r where coalesce(r.learned,0) = 0""", all=True))
        if self.FX.db_error is not None: return ()

        rule = SQLContainer('rules', RULES_SQL_TABLE_RES, replace_nones=True)
        feed = FeedContainerBasic()

        #String literals - not to do localization in the loop
        l_yes = _('YES')
        l_no = _('NO')
        l_all_fields = _('-- All Fields --')
        l_all_feeds = _('-- All Channels/Categories --')
        l_none = _('<NONE>')
        l_unknown = _('<UNKNOWN>')
        l_type_0 = _('String Matching')
        l_type_1 = _('Full Text Search')
        l_type_2 = _('Full Text Search (Exact)')
        l_type_3 = _('REGEX')
        l_type_4 = _('Learnind algorithm (stemmmed)')
        l_type_5 = _('Learnind algorithm (exact)') 
        
        self.results.clear()

        for r in results:
            rule.clear()
            rule.populate(r)

            if coalesce(rule['case_insensitive'],0) == 0: rule['case_insensitive'] = l_no
            else: rule['case_insensitive'] = l_yes

            if coalesce(rule['additive'],0) == 0: rule['additive'] = l_no
            else: rule['additive'] = l_yes

            qtype = coalesce(rule['type'],0)
            if qtype == 0: rule['query_type'] = l_type_0
            elif qtype == 1: rule['query_type'] = l_type_1
            elif qtype == 2: rule['query_type'] = l_type_2
            elif qtype == 3: rule['query_type'] = l_type_3
            elif qtype == 4: rule['query_type'] = l_type_4
            elif qtype == 5: rule['query_type'] = l_type_5
            else: rule['query_type'] = l_unknown

            if coalesce(rule['learned'],0) == 1: rule['learned'] = l_yes
            else: rule['learned'] = l_no

            flag = coalesce(rule['flag'],0) 
            if flag == 0: rule['flag_name'] = l_none
            else: rule['flag_name'] = self.FX.get_flag_name(flag)

            rule['field_name'] = PREFIXES.get(rule['field_id'],{}).get('name',l_all_fields)

            feed_id = rule['feed_id']
            if feed_id in (None,-1): rule['feed_name'] = l_all_feeds
            else: 
                for f in self.FX.MC.feeds:
                    if feed_id == f[feed.get_index('id')]:
                        feed.populate(f)
                        rule['feed_name'] = feed.name(id=True)
                        break

            self.results.append(rule.tuplify())


        if kargs.get('print', self.print):
            self.cli_table_print(RULES_SQL_TABLE_RES_PRINT, self.results, mask=PRINT_RULES_SHORT, flag_col=rule.get_index('flag'), interline=False, output='short',
                                number_footnote=_('rules'))
        else:
            return self.results






    def show_history(self, **kargs):
        """ Print search history """
        if self.FX.MC.search_history == []: self.FX.load_history()
        self.results = self.FX.MC.search_history

        if kargs.get('print', self.print):
            self.cli_table_print((n_('Search phrase'),n_('Date added'), n_('Date added (raw)'),), self.results, 
                                    mask=(n_('Search phrase'), n_('Date added')), interline=False, output='csv')
        else:
            return self.results




    def test_regexes(self, feed_id, **kargs):
        """ Display test for HTML parsing REGEXes """
        handler = FeedexHTMLHandler(self.FX)
        feed = FeedContainer(self.FX, replace_nones=True, feed_id=feed_id)
        if not feed.exists: return ()
        handler.set_feed(feed)

        feed_title, feed_pubdate, feed_img, feed_charset, feed_lang, entry_sample, entries = handler.test_download(force=True)

        demo_string = f"""{_('Feed title:')} <b>{esc_mu(feed_title)}</b>
{_('Feed Published Date:')} <b>{feed_pubdate}</b>
{_('Feed Image Link:')} <b>{feed_img}</b>
{_('Feed Character Encoding:')} <b>{feed_charset}</b>
{_('Feed Language Code:')} <b>{feed_lang}</b>
------------------------------------------------------------------------------------------------------------------------------

"""
        for e in entries:

            demo_string = f"""{demo_string}
    ------------------------------------------------------------------
    {_('Title:')} <b>{e.get('title')}</b>
    {_('Link:')} <b>{e.get('link')}</b>
    {_('GUID:')} <b>{e.get('guid')}</b>
    {_('Published:')} <b>{e.get('pubdate')}</b>
    {_('Description:')} <b>{e.get('desc')}</b>
    {_('Category:')} <b>{e.get('category')}</b>
    {_('Author:')} <b>{e.get('author')}</b>
    {_('Additional Text:')} <b>{e.get('text')}</b>
    {_('Image HREFs:')} <b>{e.get('images')}</b>"""

        demo_string = f"""{demo_string}
------------------------------------------------------------------------------------------------------------------------------
<i><b>{_('Entry sample:')}</b></i>
{entry_sample}
"""
        help_print(demo_string)






#######################################################################
#
#           UTILITIES
#




    def _has_caps(self, string):
        """ Checks if a string contains capital letters """
        for c in string:
            if c.isupper(): return True
        return False

    def _resolve_flag(self, flag:str):
        if flag in (None,'','all'): return None

        elif flag == 'all_flags': return 0
        elif flag == 'no': return -1
        else: return self.FX.resolve_flag(flag)

 




    ##########################################################################3
    #   CLI DISPLAY TOOLS
    #


    def cli_table_print(self, columns:list, table, **kargs):
        """ Clean printing of a given table (list of lists) given delimiter, truncation etc.
            Output can be filtered by mask (displayed column list) """

        output = kargs.get('output', self.output)

        if output == 'json':
            json_string = json.dumps(table)
            print(json_string)
            return json_string

        STERM_NORMAL = self.config.get('TERM_NORMAL', TERM_NORMAL)
        STERM_READ = self.config.get('TERM_READ', TERM_READ)
        STERM_DELETED = self.config.get('TERM_DELETED', TERM_DELETED)
        SBOLD_MARKUP_BEG = self.config.get('BOLD_MARKUP_BEG', BOLD_MARKUP_BEG)
        SBOLD_MARKUP_END = self.config.get('BOLD_MARKUP_END', BOLD_MARKUP_END)
        STERM_SNIPPET_HIGHLIGHT = self.config.get('TERM_SNIPPET_HIGHLIGHT', TERM_SNIPPET_HIGHLIGHT)


        number_footnote = kargs.get('number_footnote',_('results'))
    
        total_number = kargs.get('total_number', 0)
        total_number_footnote = kargs.get('total_number_footnote', _('entries'))

        sdelim = f" {self.delim} "
        sdelim2 = f" {self.delim2} "
        delim_escape = self.delim_escape
        if delim_escape not in ('', None): delim_escape = f'{delim_escape}{self.delim}'

        if self.debug in (1,8): mask = columns
        else: mask = kargs.get('mask',columns)

        # Colored columns
        read_col = kargs.get('read_col', -1)
        flag_col = kargs.get('flag_col', -1)
        del_col  = kargs.get('del_col', -1)

        # Date column - for nice formatting short dates
        date_col = kargs.get('date_col',-1)
        if date_col != -1 and (not self.debug in (1,5)):
            today = date.today()
            yesterday = today - timedelta(days=1)
            year = today.strftime("%Y")
            year = f'{year}.'
            today = today.strftime("%Y.%m.%d")
            yesterday = yesterday.strftime("%Y.%m.%d")

        # Column containing auth data - to be hidden
        passwd_col = kargs.get('passwd_col', -1)

        # Node columns
        node_col = kargs.get('node_col',-1)
        node_title_col = kargs.get('node_title_col',-1)

        # Print header with columns
        string = ''
        for i in mask:
            if type(i) is int: string = f'{string}{_(scast(columns[i], str, "")).replace(self.delim,delim_escape)}{sdelim}'
            else: string = f'{string}{_(scast(i, str, "")).replace(self.delim,delim_escape)}{sdelim}'
        print(string)

        if output == 'cli': print("\n----------------------------------------------------------------------------------------------------------------------------------------------------------------------------")

        # If entries are empty, then inform
        if table == [] or table is None:
            print("<<< EMPTY >>>")
        

        # ... and finally, entry list
        for entry in table:
            string = ''
            # Set text colors
            if output in ('cli', 'cli_noline','short','headlines'):
                cs_beg=STERM_NORMAL
                cs_end=STERM_NORMAL
                if flag_col != -1: flag_id = scast(slist(entry, flag_col, 0), int, 0)

                if del_col != -1 and scast(slist(entry, del_col, 0), int, 0)  >= 1:
                        cs_end = STERM_NORMAL
                        cs_beg = STERM_DELETED
                elif read_col != -1 and scast(slist(entry, read_col, 0), int, 0)  >= 1:
                        cs_end = STERM_NORMAL
                        cs_beg = STERM_READ
                elif flag_col != -1 and flag_id >= 1:
                        cs_end = STERM_NORMAL
                        cs_beg = TCOLS.get(self.FX.get_flag_color_cli(flag_id),'')

                if node_col != -1:
                    if scast(slist(entry, node_col, 0), int, 0)  == 1:
                        print(f'\n\n========= {scast(slist(entry, node_title_col, None), str, _("<<UNKNOWN>>"))} ===========================\n')
                        continue
                    #else: string = f'|--------- {string}'

            else:
                cs_beg = ''
                cs_end = ''

            for i in mask:
                sdate = False
                spass = False
                if type(i) is not int:
                    tix = columns.index(i)
                    text = slist(entry, tix, '')
                    if tix == passwd_col:
                        spass = True
                    elif tix == date_col:
                        sdate = True
                else:
                    text = slist(entry,i,'')
                    if passwd_col != -1 and i == passwd_col:
                        spass = True
                    if date_col != -1 and i == date_col:
                        sdate = True

                if type(text) in (float, int):
                    text = scast( round(text,4), str, _('<<NUM?>>'))

                elif type(text) in (list, tuple):
                    field_str = ''
                    for s in text:
                        if type(s) is str:
                            field_str = f'{field_str}{sdelim2}{s}'
                        elif type(s) in (list, tuple) and len(s) >= 3:
                            if output  in ('cli', 'cli_noline'):
                                field_str = f'{field_str}{sdelim2}{s[0]}{STERM_SNIPPET_HIGHLIGHT}{s[1]}{cs_beg}{s[2]}'
                            else:
                                field_str = f'{field_str}{sdelim2}{s[0]}{SBOLD_MARKUP_BEG}{s[1]}{SBOLD_MARKUP_END}{s[2]}'

                    if field_str.startswith(sdelim2):
                        field_str = field_str.replace(sdelim2,'',1)

                    text = field_str

                elif text is None:
                    if output in ('cli', 'cli_noline','short','headlines'): text = _('<NONE>')
                    else: text = ''
                else:
                    text = scast(text, str, '')
                    if output in ('cli', 'cli_noline','short','headlines'):
                        if spass:
                            text = '**********'
                        elif sdate and not self.debug in (1,8):
                            text = text.replace(today, _('Today'))
                            text = text.replace(yesterday, _('Yesterday'))
                            text = text.replace(year,'')

                        text = text.replace(SBOLD_MARKUP_BEG, STERM_SNIPPET_HIGHLIGHT).replace(SBOLD_MARKUP_END, cs_beg)

                field = text
            
                # Truncate if needed
                if self.trunc > 0:
                    field = ellipsize(field, self.trunc)
                    field = field.replace("\n",' ').replace("\r",' ').replace("\t",' ')
                    field = f"{field}{cs_beg}"

                # Delimiter needs to be stripped or escaped (for csv printing etc.)
                string = f"{string}{field.replace(self.delim, delim_escape)}{sdelim}"

        
            print(f"{cs_beg}{string}{cs_end}")
            if output == 'cli': print("\n----------------------------------------------------------------------------------------------------------------------------------------------------------------------------")

        if output  in ('cli', 'cli_noline','short','headlines'):
            print(f'{len(table)} {number_footnote}')
            if total_number != 0:
                print(f'{total_number} {total_number_footnote}')






    def cli_plot(self, data_points, max, term_width):
        """ Plots a dataset in a terminal """
        unit = dezeroe(max,1)/term_width

        for dp in data_points:
            x = dp[0]
            y = dp[1]
            length = int(y/unit)
            points = ""
            for l in range(length): points = f"{points}*"
                
            print(x, "|", points, " ", y)








    def cli_entry_print(self, lentry:list, lrules:list):
        """ Displays entry given in a list """
    
        entry = SQLContainer('entries', RESULTS_SQL_TABLE)
        entry.populate(lentry)
        if entry['id'] is None:
            self.FX.MC.ret_status = cli_msg((-8,_("Entry does not exist!")))
            return -1

        string=f"""
{_('Feed or Category')} (feed_id): {entry['feed_name_id']}  
----------------------------------------------------------------------------------------------------------
{_('Title:')}  {entry['title']}
----------------------------------------------------------------------------------------------------------
{_('Descripton')} (desc):     {entry['desc']}
----------------------------------------------------------------------------------------------------------
{_('Text')} (text): {entry['text']}
----------------------------------------------------------------------------------------------------------
{_('Links and enclosures:')}
{entry['links']}
{entry['enclosures']}
{_('Images')}:
{entry['images']}
{_('Comments')}:       {entry['comments']}
----------------------------------------------------------------------------------------------------------
{_('Category')}:       {entry['category']}
{_('Tags')}:           {entry['tags']}
{_('Author')}:         {entry['author']} ({_('contact')}: {entry['author_contact']})
{_('Publisher')}:      {entry['publisher']} ({_('contact')}: {entry['publisher_contact']})
{_('Contributors')}:   {entry['contributors']}
{_('Published')}:      {entry['pubdate_r']}    {_('Added')}:  {entry['adddate_str']}
----------------------------------------------------------------------------------------------------------
{_('ID')}:             {entry['id']}
{_('Language')} (lang):       {entry['lang']}
{_('Read?')} (read):   {entry['read']}
{_('Flagged')} (flag):        {entry['flag']}
{_('Deleted?')} (deleted):     {entry['deleted']}
-----------------------------------------------------------------------------------------------------------
{_('Weight')}:         {entry['weight']}       {_('Importance')}:     {entry['importance']}
    """
        print(string)
        if lrules is not None and lrules != []:
            print("-------------------------------------------------------------------------------------------------------------------")
            print(_("Learned Keywords:\n"))
            rule_str = ""
            for r in lrules: rule_str += slist(r,0,'') + ";  "
            print(rule_str, "\n\n")











    def cli_feed_print(self, lfeed:list, **kargs):
        """ Prints channel data given in a list """
        MAIN_TABLE=FEEDS_SQL_TABLE_PRINT + ("Category",)
        feed = SQLContainer('feeds', MAIN_TABLE)
        feed.populate(lfeed)

        output = kargs.get('output','cli')
        to_var = kargs.get('to_var',False)

        ostring = ''

        if feed['ID'] is None: 
            self.FX.MC.ret_status = cli_msg((-8,_("Channel does not exist!")))
        else:
            TABLE=FEEDS_SQL_TABLE + ('parent_id -> name',)
            for i,c in enumerate(feed.tuplify(all=True)):
                if i == feed.get_index('Password') and c not in ('',None): c = '**********'
                if output == 'cli' and not to_var:
                    ostring = f'{ostring}\n---------------------------------------------------------------------------------------------------------------------------------------'
                ostring=f"""{ostring}\n{MAIN_TABLE[i]} ({TABLE[i]}):          {c}"""

            if not to_var: print(ostring)
            return ostring


