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


    def __init__(self, engine, **args):

        # Config and parent classes
        self.FX = engine
        self.config = args.get('config', DEFAULT_CONFIG)

        # Overload config passed in arguments
        self.debug = args.get('debug',False) # Triggers additional info at runtime
        self.timeout = args.get('timeout', self.config.get('timeout',5)) # Wait time if DB is locked

        self.ignore_images = args.get('ignore_images', self.config.get('ignore_images',False))
        self.wait_indef = args.get('wait_indef',False)

        # CLI display options
        self.output = args.get('output','cli')
        self.delim = args.get('delimiter','|')
        self.delim2 = args.get('delimiter2',';')
        self.delim_escape = args.get('delim_escape','\\')
        self.trunc = args.get('trunc',200)

        self.print = args.get('print',False)

        # This tells us if the GUI is running
        self.gui = args.get('gui',False)

        # Container for query results
        self.result = SQLContainer('entries', RESULTS_SQL_TABLE)

        # Query results
        self.results = []

        self.snippets_lst = [] # Snippet lists for query results (string search)
        self.snippets_pos = [] # Snippet positions for query results (full text search)





#################################################################################
#
#       RANKING BY RULE MATCHING
#



    def match_rules(self, fields:list, entry_weight:float, rules:list, **args):
        """ Calculates importance and flags given set of rules and a document represented by fields """
        final_weight = 0
        flag = 0
        entry_weight = dezeroe(scast(entry_weight, float, 1),1)

        to_var = args.get('to_var',False)
        to_print = args.get('print',False)

        if to_var or to_print:
            var_str=''

        flag_dist = {}

        for r in rules:

            name = r[1]
            qtype = scast(r[2], int, 0)
            feed = scast(r[3], int, -1)
            if feed != None and feed != -1 and fields[0] != feed: continue

            field = scast(r[4], int, -1)
            string = scast(r[5], str, '')

            if len(string) < 1: continue

            if r[6] == 1: case_ins = True
            else: case_ins = False

            lang = r[7]
            if lang != None and lang != self.FX.LP.get_model(): continue

            weight = r[8]
            additive = r[9]
            learned = scast(r[10], int, 0)
            do_flag = scast(r[11], int, 0)

            if learned == 1:
                if qtype == 4:
                    matched = self._sregex_matcher(string, scast(fields[10],str,''))
                elif qtype == 5:
                    matched = self._sregex_matcher(string, scast(fields[11],str,''))
                else: matched = self._sregex_matcher(string, scast(fields[10],str,''))

            else:
                if qtype == 3:
                    if field == -1: field_lst = [fields[5],fields[6],fields[8],fields[9]]
                    else: field_lst = [fields[field]]
                    matched = 0

                    for f in field_lst:
                        if type(f) != str: f=''
                    
                        if case_ins: matches = re.findall(string,f, re.IGNORECASE)
                        else: matches = re.findall(string,f)

                        matched += len(matches)

                else:
                    phrase = self._q_prep_phrase(string, qtype=qtype, field=field, sqlize=False, regexify=True, case_ins=case_ins)
                    matched = self._q_match_fields(phrase, qtype, fields, field, case_ins=case_ins, snippets=False)
                
            if matched > 0:

                if to_var or to_print:
                    var_str=f"""{var_str}\nName: {name}  |  String: {string}  |  Type: {qtype}  |  Field: {field}  |  Learned?: {learned}  |  Weight: {weight}  |  Flag: {do_flag}  |  Matched: {matched}"""

                if learned not in (1,2) and do_flag > 0: flag_dist[do_flag] = flag_dist.get(do_flag,0) + (weight * matched)

                if additive == 1: final_weight = final_weight + (weight * matched)
                else: final_weight = weight * matched
    
        if to_var:
            return var_str
        else:
            if to_print: print(var_str)
            if flag_dist != {}:
                flag = max(flag_dist, key=flag_dist.get)
            return final_weight * entry_weight, flag












##############################################################
#
#       QUERY PARSING AND MAIN SEARCH



    def _build_sql(self, phrase:dict, filters:dict, **args):
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

                if field == None: cond = "\n(e.title LIKE :phrase  ESCAPE '\\' OR e.desc LIKE :phrase  ESCAPE '\\' OR e.category LIKE :phrase  ESCAPE '\\' OR e.text LIKE :phrase  ESCAPE '\\')\n"
                else: cond = f"\n( {PREFIXES.get(field, [None, None, 'e.desc'])[1]} LIKE :phrase )  ESCAPE '\\'\n"

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
        if filters.get("feed") not in (None, False, -1):
            vals['feed_id'] = scast(filters.get('feed'), int, 0)
            query = f"{query}\nand ( f.id = :feed_id and f.is_category <> 1 )"

        elif filters.get("category") not in (None, False):
            if filters.get("deleted", False): del_str = ''
            else: del_str = 'and coalesce(ff.deleted,0) <> 1'
            vals['feed_id'] = scast(filters.get('category'), int, 0)

            query = f"""{query}\nand (( f.id=:feed_id and f.is_category = 1) 
or f.id in ( select ff.id from feeds ff where ff.parent_id = :feed_id {del_str} ))"""

        if filters.get("id") != None:
            vals['id'] = scast(filters.get('id'), int, 0)
            query = f"{query}\nand e.id = :id"

        
        if filters.get("from_date") != None:
            vals['from_date'] = scast(convert_timestamp(filters.get('from_date')), int, 0)
            query = f"{query}\nand e.pubdate >= :from_date"                        
        elif filters.get("from_date_raw") != None:
            vals['from_date_raw'] = scast(filters.get('from_date_raw'), int, 0)
            query = f"{query}\nand e.pubdate >= :from_date_raw"

        if filters.get("to_date") != None:
            vals['to_date'] = scast(convert_timestamp(filters.get('to_date')), int, 99999999999)
            query = f"{query}\nand e.pubdate <= :to_date"                        
        elif filters.get("to_date_raw") != None:
            vals['to_date_raw'] = scast(filters.get('to_date_raw'), int, 99999999999)
            query = f"{query}\nand e.pubdate <= :to_date_raw"


        if filters.get("from_added") != None:
            vals['from_added'] = scast(filters.get('from_added'), int, 0)
            query = f"{query}\nand e.adddate >= :from_added"
        if filters.get("to_added") != None:
            vals['to_added'] = scast(filters.get('to_added'), int, 9999999999)
            query = f"{query}\nand e.adddate <= :to_added"



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

        elif filters.get("last_year", False):
            vals['cdate'] = int(datetime.now().timestamp()) - (86400*31*12)
            if vals['cdate'] > 0:
                query = f"{query}\nand e.pubdate >= :cdate"

        elif filters.get('last_hour', False):
            vals['cdate'] = int(datetime.now().timestamp()) - (60*60)
            if vals['cdate'] > 0:
                query = f"{query}\nand e.adddate >= :cdate"


        if filters.get('handler') != None:
            vals['handler'] = scast(filters.get('handler'), str, '').lower()
            query = f"{query}\nand f.handler = :handler"


        if filters.get("importance",0) != 0:
            vals['importance'] = scast(filters.get('importance'), int, 0)
            query = f"{query}\nand e.importance >= :importance"

        if filters.get("unread",False):
            query = f"{query}\nand coalesce(e.read,0) = 0"
        elif filters.get("read",False):
            query = f"{query}\nand coalesce(e.read,0) > 0"

        if filters.get("flag") != None:
            if filters.get('flag') == 0:
                query = f"{query}\nand coalesce(e.flag,0) > 0"
            elif filters.get('flag') == -1:
                query = f"{query}\nand coalesce(flag,0) = 0"
            else:  
                vals['flag'] = scast(filters.get('flag',0), int, 0)
                query = f"{query}\nand coalesce(e.flag,0) = :flag"

        if filters.get("deleted",False):
            query = f"{query}\nand (coalesce(e.deleted,0) = 1 or coalesce(f.deleted,0) = 1)"
        else:
            query = f"{query}\nand coalesce(e.deleted,0) <> 1 and coalesce(f.deleted,0) <> 1"

        # This one is risky, so we have to be very careful every ID is a valis integer
        if filters.get('ID_list') != None and type(filters.get('ID_list')) in (list,tuple) and len(filters.get('ID_list',[])) > 0:
            ids = ''
            for i in filters.get('ID_list',[]):
                i = scast(i, int, None)
                if i == None: continue
                ids = f'{ids}{i},'
            ids = ids[:-1]
            query = f"{query}\nand e.id in ({ids})"

        # Sorting options
        sort = filters.get('sort')
        rev = filters.get('rev')
        if sort != None and type(sort) == str and len(sort) > 2:
            if sort.startswith('-'):
                desc=True
            else:
                desc=False
            sort = sort[1:]
            if sort not in ENTRIES_SQL_TABLE:
                sys.stderr.write(f"{sort} is not a valid field! Changed to ID")
                sort = 'id'
            query = f"{query}\norder by e.{sort}"
            if desc and not rev:
                query = f"{query} DESC"
            elif not desc and rev:
                query = f"{query} DESC"

        #query = f"""{query}\nESCAPE \\"""

        return query, vals






    def notify(self, **args):
        """ Notify about news downloaded during last news check, print them or generate desktop notifications """

        level = args.get('notify_level',1)
        rev = args.get('rev',False)

        if rev: sql='order by e.importance DESC, e.flag DESC, e.weight DESC'
        else: sql='order by e.importance ASC, e.flag ASC, e.weight ASC'
        last = self.FX.get_last()        

        if level == 1:
            self.results = self.FX.sqlite_cur.execute(NOTIFY_LEVEL_ONE_SQL, (last,)).fetchall()
        elif level == 2:
            self.results = self.FX.sqlite_cur.execute(NOTIFY_LEVEL_TWO_SQL+sql, (last,)).fetchall()              
        elif level == 3:
            self.results = self.FX.sqlite_cur.execute(NOTIFY_LEVEL_THREE_SQL+sql, (last,)).fetchall()

        if args.get('print',self.print):
            if not self.debug: mask=RESULTS_SHORT_PRINT1
            else: mask=RESULTS_SQL_TABLE_PRINT

            if level in (2,3):
                table_print(RESULTS_SQL_TABLE_PRINT, self.results, self.delim, delim_escape=self.delim_escape, truncate=self.trunc, output=self.output,
                        ccol1=self.result.get_index('flag'), ccol1_thr=1, ccol2=self.result.get_index('weight'), ccol2_thr=self.FX.get_avg_weight(), ccol3=self.result.get_index('deleted'), ccol3_thr=1,
                        mask=mask, number_footnote='new articles', date_col=self.result.get_index('pubdate_short'))
            elif level == 1:
                table_print(("Feed (ID)", "All news", "Flagged news"), self.results, self.delim, delim_escape=self.delim_escape, truncate=self.trunc, output=self.output,
                            ccol1=2, ccol1_thr=1, number_footnote='channels have new items')

        return self.results




    def query(self, string:str, filters:dict, **args):
        """ Main Query method
            Queries database with search string. """
        # This must be done in two stages:
        # SQL query, and phrase matching/filtering on SQL results (to get match count)

        lang = filters.get('lang', 'heuristic')
        qtype = self.resolve_qtype(filters.get('qtype',1))
        filters['qtype'] = qtype

        if qtype in (1,2,): 
            self.FX.LP.set_model(lang)

        field = filters.get('field')
        field = self.FX.resolve_field(field)
        category = filters.get('category')
        if category != None: category = self.FX.resolve_category(category)
        filters['field'] = field
        filters['category'] = category
        if filters.get('last',False): filters['from_added'] = self.FX.get_last()

        rev = filters.get('rev',True)
        sort = filters.get('sort')
        
        if filters.get('case_ins') not in (True, False):
            if self._has_caps(string):
                filters['case_ins'] = False
            else: filters['case_ins'] = True
        
        case_ins = filters.get('case_ins')
        filters['case_ins'] = case_ins
        filters['flag'] = self._resolve_flag(filters.get('flag'))

        rank =  args.get('rank',True)
        cnt = args.get('cnt',False)

        snippets = args.get('snippets',True)

        if cnt or rank or snippets: regexify = True
        else: regexify = False

        phrase = self._q_prep_phrase(string, qtype=qtype, case_ins=case_ins, field=field, sqlize=True, regexify=regexify)

        (query, vals) = self._build_sql(phrase, filters)
        if self.debug: 
            print(f"\n\nQuery: \n{query}\n")
            print(vals)
    
    
        results_tmp = self.FX.sqlite_cur.execute(query, vals).fetchall()
        
        if self.debug:
            print("Results: ", len(results_tmp))
        
        self.results = []

        # Rank results (if needed)
        # For this we will use last returned column and then replace it with ranking - a little crude, but works
        # SQL has its limitations and I need something beyond boolean matching

        # No point doing this if no string was given or there was only one result
        matched_docs_count = len(results_tmp)
        if (rank or cnt) and (not phrase.get('empty',False)) and matched_docs_count > 0:
            if rank:
                doc_count = args.get('doc_count', self.FX.get_doc_count())
                idf = log10(doc_count/matched_docs_count)

            # Calculate ranking for each result
            for r in results_tmp:

                self.result.populate(r)
                if snippets:
                    self.snippets_lst = []
                    self.snippets_pos = []

                matched = self._q_match_fields(phrase, qtype, self.result.tuplify(filter=LING_LIST2), field, case_ins=case_ins, snippets=snippets)

                # Append snippets
                if snippets:
                    if qtype in (1,2,):
                        for ss in self.snippets_pos:
                            for s in ss: 
                                if len(s) < 400: # do this to avoid showing long wildcard matches
                                    self.snippets_lst.append( posrange(s, self.result['tokens_raw'], 8) )

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
            if sort == None:
                if cnt:
                    self.results.sort(key=lambda x: x[self.result.get_index('count')], reverse=not rev)
                elif rank:
                    self.results.sort(key=lambda x: x[self.result.get_index('rank')], reverse=not rev)
        else:
            self.results = results_tmp


        # Save phrase to history
        if args.get('no_history',False) != True and phrase.get('emtpy',False) != True:
            now = int(datetime.now().timestamp())
            self.FX.sqlite_cur.execute('insert into search_history values(NULL,?,?)',(string,now,))
            self.FX.sqlite_conn.commit()


        # Display results if needed
        if args.get('print', self.print):
            columns = args.get('columns',RESULTS_SHORT_PRINT1)
            if self.debug:
                table_print(RESULTS_SQL_TABLE_PRINT, self.results, self.delim, truncate=self.trunc, 
                            ccol1=self.result.get_index('flag'), ccol2=self.result.get_index('read'), ccol1_thr=1, ccol2_thr=1, ccol3=self.result.get_index('deleted'), ccol3_thr=1,
                            output=self.output, delim2=self.delim2, delim_escape=self.delim_escape)
            else:
                table_print(RESULTS_SQL_TABLE_PRINT, self.results, self.delim, truncate=self.trunc, 
                            mask=columns, ccol1=self.result.get_index('flag'), ccol2=self.result.get_index('read'), ccol1_thr=1, ccol2_thr=1, ccol3=self.result.get_index('deleted'), ccol3_thr=1, 
                            date_col=self.result.get_index('pubdate_short'), output=self.output, delim2=self.delim2, delim_escape=self.delim_escape)
            

        return self.results








####################################################################################################3
#
#       SPECIAL QUERIES
#




    def find_similar(self, id, **args):
        """ Find entry similar to specified by ID based on extracted features """
        id = scast(id, int, 0)
        limit = args.get('limit',self.config.get('default_similarity_limit',20)) # Limit results
        rev = args.get('rev',False)  # Reverse sort order
        args['limit'] = None
        args['rev'] = None

        # Get or generate rules
        rules = self.FX.sqlite_cur.execute("select * from rules where context_id=? order by weight desc",(id,)).fetchall()
        if rules in (None, [], [None]):
            self.FX.recalculate(id=id, learn=True, stats=False, rank=False, force=True, verbose=False, ignore_lock=True)
            rules = self.FX.sqlite_cur.execute("select * from rules where context_id=? order by weight desc",(id,)).fetchall()
            if rules in (None, [], [None]):
                if self.debug: print("Nothing to find...")
                return 0
        # Search for keywords in entries one by one and record weighted results
        i = 0
        filters = args.copy()
        filters['lang'] = args.get('lang','heuristic')
        filters['case_ins'] = True
        filters['rev'] = False
        doc_cnt = self.FX.get_doc_count()
        freq_dist = {}

        for r in rules:
            if i >= limit:
                break

            qphrase = r[self.FX.rule.get_index('string')]

            if r[self.FX.rule.get_index('type')] == 5: filters['qtype'] = 5
            else: filters['qtype'] = 4

            if r[self.FX.rule.get_index('case_insensitive')] == 1: filters['case_ins'] = True
            else: filters['case_ins'] = False
            if r[self.FX.rule.get_index('field_id')] != None:
                filters['feed'] = r[self.FX.rule.get_index('field_id')]

            self.query(qphrase, filters, rank=False, cnt=True, doc_count=doc_cnt, snippets=False, print=False, no_history=True, )

            if self.results != None and len(self.results) > 0:
                for rs in self.results:
                    self.result.populate(rs)
                    
                    w = self.result.get('count',0) * coalesce(r[self.FX.rule.get_index('weight')],0) * self.result['weight']
                    freq_dist[self.result['id']] = freq_dist.get(self.result['id'],0) + w
                i += 1

        # Create freq distribution of results-weight
        freq_dist_sorted = []
        for fd in freq_dist.keys():
            freq_dist_sorted.append((fd, freq_dist[fd]))
        freq_dist_sorted.sort(key=lambda x: x[-1], reverse=True)
        
        # Construct final list of IDs
        ids=[]
        for i,idd in enumerate(freq_dist_sorted):
            if i >= limit:
                break
            ids.append(idd[0])
        
        # ... and query for them
        if len(ids) > 0:
            results_tmp = self.query('*', {'ID_list': ids} ,rank=False, cnt=False, snippets=False, print=False)
        else:
            results_tmp = []

        self.results = []
        # Append similarity measure at the end of each result to sort by it later
        for r in results_tmp:
            result_tmp = list(r)
            result_tmp.append(None)
            result_tmp.append(None)
            result_tmp[self.result.get_index('rank')] = freq_dist.get(result_tmp[self.result.get_index('id')],0)
            self.results.append(result_tmp)

        self.results.sort(key=lambda x: x[self.result.get_index('rank')], reverse=rev)

        if args.get("print",self.print):
            if self.debug:
                table_print(RESULTS_SQL_TABLE_PRINT, self.results, self.delim, truncate=self.trunc, delim_escape=self.delim_escape, 
                            ccol1=self.result.get_index('user_marked'), ccol2=self.result.get_index('status'), ccol1_thr=1, ccol2_thr=1, ccol3=self.result.get_index('deleted'), ccol3_thr=1,
                            output=self.output, number_footnote='similar documents')
            else:
                table_print(RESULTS_SQL_TABLE_PRINT, self.results, self.delim, truncate=self.trunc, delim_escape=self.delim_escape, mask=RESULTS_SHORT_PRINT1, 
                            ccol1=self.result.get_index('user_marked'), ccol2=self.result.get_index('status'), ccol1_thr=1, ccol2_thr=1, ccol3=self.result.get_index('deleted'), ccol3_thr=1,
                            output=self.output, number_footnote='similar documents', date_col=self.result.get_index('pubdate_short'))
    

        else:
            return self.results







    def term_context(self, string:str, **args):
        """ Get term's context (find entries and print immediate surroundings) """
        self.query(string, args, count=False, rank=True, snippets=True, print=False)

        context = SQLContainer('entries', RESULTS_SQL_TABLE_PRINT + ("Context",) )
        
        results_tmp = []
        
        for r in self.results:    
            self.result.populate(r)

            for s in self.result['snippets']:
                
                fields = self.result.listify(all=True)
                fields.append((s,))
                context.populate(fields)
                results_tmp.append(context.tuplify())

        self.results = results_tmp

        if args.get('print',self.print):
            if self.debug:
                table_print(context.fields, self.results, self.delim, truncate=self.trunc, output='cli_noline', delim2=self.delim2, delim_escape=self.delim_escape)
            else:
                table_print(context.fields, self.results, self.delim, truncate=self.trunc, output='cli_noline', delim2=self.delim2, delim_escape=self.delim_escape, 
                            mask=(context.get_index('Date'), context.get_index('Context'), context.get_index('ID'), context.get_index('Source (ID)'), 
                             context.get_index('Published - Timestamp'), ), date_col=context.get_index('Date'))
        
        else:
            return self.results




    def term_net(self, term:str, **args):
        """ Show terms/features connected to a given term by analising contexts """
        
        self.results = self.FX.sqlite_cur.execute(TERM_NET_SQL, (term,)).fetchall()
        
        #If the term is not in the rules, query the database
        if self.results in ((),[],None, (None,)):

            filters = {'qtype' : 1, 'lang' : args.get('lang','heuristic'), 'case_ins' : True}
            self.query(term, filters, rank=False, cnt=False, snippets=False, print=False)

            if self.results not in ((),[],None, (None,)):
                ids = []
                for r in self.results:
                    id = scast(slist(r, self.result.get_index('id'), 0), int, 0)
                    ids.append( scast(id, str, "''") )
                ids = ', '.join(ids)
            
                # Get rules from entries that input term comes from 
                sql = f"select r.name, r.weight, count(r.context_id) as c from rules r where r.context_id in ( {ids} ) group by r.name, r.weight order by c * r.weight"
                self.results = self.FX.sqlite_cur.execute(sql).fetchall()


        if args.get('print',self.print):
            table_print(("Term", "Weight", "Documents"), self.results, self.delim, truncate=self.trunc, output='csv', delim_escape=self.delim_escape)
            if self.debug: print(len(self.results), " results")
        else:
            return self.results






    def terms_for_entry(self, id:int, **args):
        """ Output terms/features learned from an entry """
        SQL='select r.name, r.weight from rules r where r.context_id = ? order by r.weight asc'

        self.results = self.FX.sqlite_cur.execute(SQL, (id,) ).fetchall()
        if self.results in ([],None,[None]) and not args.get('no_recalc',False):
            self.FX.recalculate(id=int(id), learn=True, stats=False, rank=False, force=True, verbose=False)
            self.results = self.FX.sqlite_cur.execute(SQL, (id,) ).fetchall()

        if args.get('print',self.print):
            table_print(("Term", "Weight"), self.results, self.delim, delim_escape=self.delim_escape, truncate=self.trunc, output='csv')
            if self.debug: print(len(self.results), " results")
        else:
            return self.results
                

    def rules_for_entry(self, id:int, **args):
        """ Output rules that match and contributed to importance of given entry """
        to_var = args.get('to_var', False)
        print = args.get('print',True)
        entry = SQLContainer('entries', ENTRIES_SQL_TABLE)
        entry.populate(self.FX.sqlite_cur.execute('select * from entries e where e.id = ?', (id,) ).fetchone())
        if print: print(f'Rules matched for entry {str(id)} (weight: {str(entry["weight"])}):')
        self.FX.LP.charset = entry['charset']
        self.FX.LP.set_model(entry['lang'])
        if print:
            (importance, flag) = self.match_rules(entry.tuplify(filter=LING_LIST2), entry['weight'], self.FX.rules, print=True, to_var=False)
            print(f'Importance: {importance}')
            print(f'Flag: {flag}')

        if to_var:
            return self.match_rules(entry.tuplify(filter=LING_LIST2), entry['weight'], self.FX.rules, print=False, to_var=True)




    def term_in_time(self, term:str, **args):
        """ Get term frequency in time and output as a table of data points or a plot in terminal """
        group = args.get('group','daily')
        col_name = 'Month'
        plot = args.get('plot',False)
        term_width = args.get('term_width',150)

        self.query(term, args, rank=False, cnt=True, snippets=False, print=False)

        if group == 'hourly':
            col_name = 'Hour'
        elif group == 'daily':
            col_name = 'Day'
        elif group == 'monthly':
            col_name = 'Month'

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
        time_series.append([date_start, freq_dict[date_start]])
        ts = date_start
        mon_rel = relativedelta(months=1)
        day_rel = relativedelta(days=1)

        # Populate every step on date, even if there were 0 occurences
        while ts != date_end:
            tst = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
            if group == "hourly":
                tst += timedelta(hours=1)
            elif group == "daily":
                tst += day_rel
            elif group == "monthly":
                tst += mon_rel

            ts = tst.strftime("%Y-%m-%d %H:%M:%S")
            fr = freq_dict.get(ts,0)
            time_series.append([ts,fr])
                    

        if args.get('print',self.print) and not plot:
            table_print([col_name, "Frequency"], time_series, self.delim, delim_escape=self.delim_escape, truncate=self.trunc, output='csv')

        if plot:
            cli_plot(time_series, max, term_width)

        self.results = time_series
        return time_series





#####################################################################
#
#       MISC DISPLAY METHODS
#
#

    def list_feeds(self, **args):
        """Utility for listing feeds (for GUI and CLI)"""
        # This tells us if we want a CLI output
        feeds = self.FX.sqlite_cur.execute(FEEDS_PRINT_SQL).fetchall()
        if args.get("print",self.print):
            if self.debug:
                table_print(FEEDS_SQL_TABLE_PRINT + ("Feedex Category",), feeds, self.delim, output=self.output, truncate=self.trunc, number_footnote='registered channels', 
                ccol3=self.FX.feed.get_index('deleted'), ccol3_thr=1, delim_escape=self.delim_escape)
            else:
                table_print(FEEDS_SQL_TABLE_PRINT + ("Feedex Category",), feeds, self.delim, mask=FEEDS_SHORT_PRINT, output=self.output, truncate=self.trunc, number_footnote='rergistered channels',
                            ccol3=self.FX.feed.get_index('deleted'), ccol3_thr=1, delim_escape=self.delim_escape)
        else: 
            return self.FX.feeds


    def list_categories(self, **args):
        """ Lists all categories """
        categories = self.FX.sqlite_cur.execute(CATEGORIES_PRINT_SQL).fetchall()
        if args.get("print",self.print):
                table_print(CATEGORIES_PRINT, categories, self.delim, output=self.output, truncate=self.trunc, number_footnote='categories', ccol3=3, ccol3_thr=1, delim_escape=self.delim_escape) 
        else: 
            return categories



    def read_feed(self, id:int, **args):
        """ Print out detailed feed data """
        lfield = self.FX.sqlite_cur.execute("select f.*, f1.name from feeds f left join feeds f1 on f1.id = f.parent_id where f.id = ?", (id,) ).fetchone()
        string = feed_print(lfield, output=self.output, to_var=args.get('to_var',False))
        return string


    def read_entry(self, id:int, **args):
        """ Wrapper for displaying an entry """
        lentry = self.FX.sqlite_cur.execute(f"select {RESULTS_COLUMNS_SQL} where e.id = ?", (id,)).fetchone()
        lrules = self.FX.sqlite_cur.execute("""select name from rules r where r.context_id = ?""", (id,)).fetchall() 
        if self.debug or args.get('to_var',False):
            self.FX.entry.populate(self.FX.sqlite_cur.execute(f"select * from entries e where e.id = ?", (id,)).fetchone())
            ostring = self.FX.entry.__str__()
            if args.get('to_var',False):
                return ostring
            print(ostring)
        else:
            entry_print(lentry, lrules)



    def show_rules(self, **args):
        """ Show manually added rules """
        self.results = self.FX.sqlite_cur.execute(PRINT_RULES_SQL).fetchall()
        print(self.results)
        if args.get('print', self.print):
            table_print(PRINT_RULES_TABLE, self.results, self.delim, delim_escape=self.delim_escape, interline=False, truncate=self.trunc, output='csv')
        else:
            return self.results





#######################################################################
#
#           UTILITIES
#




    def resolve_qtype(self, qtype):
        """ Resolve query type from string to int """
        if qtype == None: return 1
        if type(qtype) == int and qtype in (0,1,2,): return qtype
        if type(qtype) == str:
            if qtype.lower() in ('string','str','0'):
                return 0
            elif qtype.lower() in ('full', 'fts', 'full-text','fulltext','1'):
                return 1
            elif qtype.lower() in ('exact','fts-exact','exact-fts','2'):
                return 2
            else: return 1
        elif qtype in (4,5): return qtype

        return 1


    def _regexify(self, string:str, **args):
        """ Escapes REGEX scepial chars """
        regex = string.replace('.','\.')
        regex = regex.replace('$','\$')
        regex = regex.replace('^','\^')
        regex = regex.replace('[','\[')
        regex = regex.replace(']','\]')
        regex = regex.replace('{','\{')
        regex = regex.replace('}','\}')
        regex = regex.replace('|','\|')
        regex = regex.replace('+','\+')
        regex = regex.replace('?','\?')
        regex = regex.replace('(','\(')
        regex = regex.replace(')','\)')
        if args.get('with_wc',False):
            regex = regex.replace('*','\*')
        return regex

    
    def _sqlize(self, string:str, **args):
        """ Escapes SQL wildcards """
        #   sql = string.replace('\\', '\\\\')
        sql = string.replace('%', '\%')
        sql = sql.replace('_', '\_')
        return sql





    def _str_matcher(self, string, field, **args):
        """ Simply matches string and extracts snippets if needed """
        snippets = args.get('snippets',True)
        orig_field = args.get('orig_field', field)

        idx = 0
        abs_idx = 0
        matches = 0
        tmp_field = field.replace('\n','')
        
        l = len(string)
        fl = len(field)

        while idx != -1:
            idx = tmp_field.find(string)
            if idx != -1:
                if snippets:
                    abs_idx += idx
                    self.snippets_lst.append( srange(orig_field, abs_idx, l, fl, 70) )
                    abs_idx += l

                matches += 1
                tmp_field = tmp_field[idx+l:]

        return matches





    def _sregex_matcher(self, string, field):
        """ Matches learned rules (simplified, REGEX-like) """
        tokens = string.split(' ')
        tbases = []
        tcases = []
        tprefixes = []
        for t in tokens:
            tbases.append(f'{t[3:]} ')
            tcases.append(t[2])
            tprefixes.append(t[0:2])

        l = len(tokens)
        tmp_field = field
        idx=0
        matches=0

        while idx != -1:
            for i in range(0,l):
                idx = tmp_field.find(tbases[i])
                if idx != -1:
                    if  tmp_field[idx-11] == ' ' and (tmp_field[idx-1] == tcases[i] or tcases[i] == '.') and (tmp_field[idx-3:idx-1] == tprefixes[i] or (tprefixes[i] == '..' and tmp_field[idx-3] == 'T' )):
                        if i == l-1:
                            matches += 1
                    tmp_field = tmp_field[idx+len(tbases[i])-1:]
                else:
                    break

        return matches





    def _q_prep_phrase(self, string:str, **args):
        """ Prepares phrase for query, returns PHRASE dictionary """
        qtype = args.get('qtype',0)
        field = args.get('field',-1)
        case_ins = args.get('case_ins',False)

        sqlize = args.get('sqlize',True)
        regexify = args.get('regexify', True)
        rstr = random_str(string=string)
        phrase = {}
        phrase['raw'] = string
        phrase['empty'] = False

        if qtype == 0:

            if string == '': 
                phrase['empty'] = True
                return phrase

            if case_ins: string = string.lower()
            
            if sqlize: phrase['sql'] = f'%{self._sqlize(string, with_wc=True)}%'
            phrase['str_matching'] = string



        elif qtype in (4, 5):

            if string == '': 
                phrase['empty'] = True
                return phrase
            
            phrase['sql'] = ''
            phrase['str_matching'] = string

            for w in string.split(' '):
                w = f"_______{w.replace('.','_')}"
                phrase['sql'] = f"{phrase['sql']} {w}"

            phrase['sql'] = f"%{phrase['sql']} %"
            return phrase


        elif qtype in (1, 2):

            # Check if empty
            if string.replace(' ','').replace('*','').replace('~','') == '':
                phrase['empty'] = True
                return phrase

            # Check for end and beg markers
            if string.startswith('\^'):
                string = string[1:]
                phrase['beg'] = False
            elif string.startswith('^'):
                phrase['beg'] = True
                string = string[1:]
            else: phrase['beg'] = False

            if string.endswith('\$'):
                string = string[:-2] + '$'
                phrase['end'] = False
            elif string.endswith('$'):
                phrase['end'] = True
                string = string[:-1]
            else: phrase['end'] = False
        
            string = string.strip()
            
            # Condense wildcards
            string = string.replace('\*', rstr)
            while '**' in string: string = string.replace('**','*')

            # Tokenize query
            phrase['sql'] = ''
            phrase['regex'] = ''
            qtokens = self.FX.LP.tokenize(string,-1, simple=True, query=True)
            for t in qtokens:
                sql = ''
                tok = t
                has_wc = False
                is_wc = False

                if tok.replace('*','') == '': 
                    is_wc = True
                    regex = '(?:\s[^\s]*?)*?'

                elif tok == '~' or (tok.startswith('~') and tok.replace('~','').isdigit()):
                    is_wc = True
                    near = scast(tok.replace('~',''), int, 5)
                    regex = "(?:\s[^\s]*?){0,"+str(near)+"}"
                
                elif '*' in tok: 
                    has_wc = True
                    case=self.FX.LP._case(tok)
                
                else: case=self.FX.LP._case(tok)

                
                if qtype == 1 and not is_wc and not has_wc:
                    tok = self.FX.LP.stemmer.stemWord(tok)

                if sqlize:
                    if is_wc:
                        phrase['sql'] = f"""{phrase['sql']}%"""
                    else:
                        tok = tok.lower()
                        sql = self._sqlize(tok)
                        sql = sql.replace('*','%')
                        sql = sql.replace(rstr, '*')

                        prefix = self.FX.LP._prefix(field, wildcard='_', case=case, case_ins=case_ins)
                        sql = f"_______{prefix}{sql.lower()}"
                        phrase['sql'] = f"""{phrase['sql']} {sql}"""

                if regexify:
                    if is_wc:
                        phrase['regex'] = f"""{phrase['regex']}{regex}"""
                    else:
                        regex = self._regexify(tok)
                        regex = regex.replace('*','[^\s]*?')
                        regex = regex.replace(rstr,'\*')
                        regex = f".......{self.FX.LP._prefix(field, wildcard='.', case_ins=case_ins, case=case)}{regex}"
                        phrase['regex'] = f"""{phrase['regex']} {regex}"""
            
            if sqlize:
                phrase['sql'] = f"{phrase['sql']} "
                if not phrase['beg']: phrase['sql'] = f"%{phrase['sql']}"
                if not phrase['end']: phrase['sql'] = f"{phrase['sql']}%"

            if regexify:
                if phrase['beg']: phrase['regex'] = f"   {phrase['regex']}"
                if phrase['end']: phrase['regex'] = f"{phrase['regex']}   "
                phrase['regex'] = re.compile(phrase['regex'])

        return phrase







    def _q_match_fields(self, phrase:dict, qtype:int, fields:list, field:int, **args):
        """ Performs phrase matching given a search phrase and field list. Returns match count and snippets if needed """

        case_ins = args.get('case_ins',False)
        snippets = args.get('snippets',True)
        matches = 0

        if qtype == 0:
            
            if field in (-1, None, False): field_lst = [fields[5],fields[6],fields[8],fields[9]]
            else: field_lst = [fields[field]]

            for f in field_lst:

                if type(f) != str: f=''

                if case_ins: fs = f.lower()
                else: fs = f

                if snippets: matches += self._str_matcher(phrase['str_matching'], fs, snippets=True, orig_field=f)
                else: matches += self._str_matcher(phrase['str_matching'], fs, snippets=False)
            


        elif qtype in (1,2,):
        
            if qtype == 1: matched = re.findall(phrase['regex'], scast(fields[10],str,'') )
            elif qtype == 2: matched = re.findall(phrase['regex'], scast(fields[11],str,'') )

            if snippets: self.snippets_pos.append(matched)

            matches += len(matched)
        
        elif qtype == 4:
            matches = self._sregex_matcher(phrase['str_matching'], scast(fields[10],str,''))
        elif qtype == 5:
            matches = self._sregex_matcher(phrase['str_matching'], scast(fields[11],str,''))

        return matches





    def _has_caps(self, string):
        """ Checks if a string contains capital letters """
        for c in string:
            if c.isupper(): return True
        return False

    def _resolve_flag(self, flag:str):
        if flag == None: return None
        if flag == 'all':
            return None
        elif flag == 'all_flags':
            return 0
        elif flag == 'no':
            return -1
        elif flag.isdigit():
            return scast(flag, int, None)
        return None