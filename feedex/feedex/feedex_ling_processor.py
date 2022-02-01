# -*- coding: utf-8 -*-
""" Classes for basic NLP text processing for Feedex """


from attr import has
from feedex_headers import *









class LingProcessor:
    """
    Class for rudimentary NLP

    - Tokenizing
    - Tagging
    - Language model handling
    - Keyphrase extraction
    - Language detection
    
    """


    def __init__(self, top_parent, **kargs):

        # Connect main
        if isinstance(top_parent, FeedexMainDataContainer): self.MC = top_parent
        else: raise FeedexTypeError('Top_parent should be an instance of FeedexMainDataContainer class!')        

        # Load configuration
        self.config = kargs.get('config', DEFAULT_CONFIG)
        # Input parameters
        self.debug = kargs.get('debug',False)

        # Load general dictionary (lookup for all languages - Acronyms, Names and such)
        self.multi_lookups = [
        {'name': 'multi_func', 'caps_only': True, 'stop_if_matched':True, 'stem':False, 'uncommon_only':False},    
        {'name': 'multi_acronyms', 'caps_only': True, 'stop_if_matched':True, 'stem':False, 'uncommon_only':True},    
        {'name': 'multi_geo', 'caps_only': True, 'stop_if_matched':True, 'stem':False, 'uncommon_only':False},    
        {'name': 'multi_names', 'caps_only': True, 'stop_if_matched':True, 'stem':False, 'uncommon_only':False},    
        {'name': 'multi_surnames', 'caps_only': True, 'stop_if_matched':True, 'stem':False, 'uncommon_only':False}    
        ]

        if self.MC.multi_dict == {}:
            self.MC.lock.acquire()
            self.MC.multi_dict = self._load_pickle('multi_dict.pkl')
            if type(self.MC.multi_dict) is not dict: self.MC.multi_dict = {'_none':True}
            self.MC.lock.release()

        # Load model headers from specified dir
        if self.MC.models == {}:

            self.MC.lock.acquire()
            self.MC.models['heuristic'] = HEURISTIC_MODEL
            
            if os.path.isdir(FEEDEX_MODELS_PATH):
                for header_file in os.listdir(FEEDEX_MODELS_PATH):
                    curr_model = {}
                    curr_model_name = None
                    header_file = os.path.join(FEEDEX_MODELS_PATH, header_file)
                    if header_file.endswith('_header.pkl') and os.path.isfile(header_file):
                        try:
                            with open(header_file, 'rb') as f:
                                curr_model = pickle.load(f)
                        except OSError as e:
                            sys.stderr.write(f'{TERM_ERR}Could not load pickle {TERM_ERR_BOLD}{header_file}{TERM_ERR} ...{TERM_NORMAL}\n{e}')
                            continue
                        
                        if self.debug: print(f'Pickle {header_file} loaded...')

                        curr_model_name = slist(curr_model.get('names',()),0,None)
            
                        if curr_model_name is not None:
                            self.MC.models[curr_model_name] = curr_model.copy()
            else:
                sys.stderr.write(f'{TERM_ERR}Invalid path for language models! ({TERM_ERR_BOLD}{FEEDEX_MODELS_PATH}{TERM_ERR}){TERM_NORMAL}\n')
            self.MC.lock.release()

    
        # This is a pointer to actove model
        self.model = {}

        self.fields = []
        self.tokens = []

        # Strings for token and regex rule searches
        self.token_str = ''
        self.raw_token_str = ''
        self.regex_rule_str = ''

        self.rules = []
        self.features = {}
    
        self.token_count = 0
        self.last_pos = 0 # Position of last indexed token
    
        # Stemmer from Snowball. Also - a class-wide config for convenience, as fields per entry
        # are almost always in one language
        self.stemmer = None

        # Addidional params
        self.charset = 'utf-8'

        # Global text parameters
        # Quotation state, if not false it should take value of closing symbol
        self.quot = []
        
        # Defaults fo safety
        self.def_d = (((),None,None,None))

        # Processed entry as a dictionary
        self.entry = {}

        # Set starting model
        self.set_model('heuristic')





    def get_model(self):
        """ Quickly get currently loaded model """
        return slist(self.model.get('names',None), 0, None)



    def _find_model(self, model:str):
        """ Find model given a language name. First search the names list from a model (including crude globs).
            Every model is searched and FIRST one to match is returned """
        model = scast(model, str, '')
        if model is None: return None

        if model in self.MC.models.keys(): return model

        for m, v in self.MC.models.items():
            m = scast(m, str, '')

            for n in v.get('names',()):
                if model.lower() == n.lower(): return m
                if n.endswith('*') and model.startswith(n.lower().replace('*','')): return m

        return None




    def _load_pickle(self, pkl:str, **kargs):
        """ Load pickle file """
        if pkl is None: return {}
        if not os.path.isdir(FEEDEX_MODELS_PATH):
            sys.stderr.write(f'{TERM_ERR}Invalid path for language models! ({TERM_ERR_BOLD}{FEEDEX_MODELS_PATH}{TERM_ERR}){TERM_NORMAL}')
            return {}
        pickle_path = f'{FEEDEX_MODELS_PATH}{DIR_SEP}{pkl}'
        lst = None
        if os.path.isfile(pickle_path):
            try:
                with open(pickle_path, 'rb') as f:
                    lst = pickle.load(f)
                    if type(lst) is not dict: 
                        sys.stderr.write(f'{TERM_ERR}Data not a dictionary structure! {TERM_ERR_BOLD}{pickle_path}{TERM_NORMAL}\n')
                        return {}
            except OSError as e:
                sys.stderr.write(f'{TERM_ERR}Could not load pickle {TERM_ERR_BOLD}{pickle_path}{TERM_ERR}...{TERM_NORMAL}\n{e}')
                lst = {}
            if self.debug: print(f'Pickle {pkl} loaded...')
        else:
            sys.stderr.write(f'{TERM_ERR}Could not find pickle path {TERM_ERR_BOLD}{pickle_path}{TERM_ERR} ...{TERM_NORMAL}\n')
            lst = {}

        return lst







    def _parse_rules(self, irules):
        """ Parse rule strings given in a language  model """
        rules = []
        for r in irules:
            rule = {}
            rule['case'] = r[0]
            rule['weight'] = r[1]
            rule['stem'] = r[2]
            rule['strip'] = r[3]
            rule['pattern'] = re.compile(r[4])
            rules.append(rule)

        return tuple(rules)






    def set_model(self, model:str, **kargs):
        """ Set a language model to currently use given by name"""

        prop_model = self._find_model(model)
        if prop_model == self.get_model() and prop_model is not None: return 0

        # First do what is needed if none is given
        if (model is None or model == 'heuristic') and kargs.get('detect',True) and self.entry != {}:
            # Call language detection and set up 'heuristic' as default
            self.model = self.MC.models.get(self.detect_lang(), self.MC.models.get('heuristic',{}))
        else:
            # Try finding by name (usually this will work):
            self.model = self.MC.models.get(prop_model,{})


        # But sometimes it wont...
        if self.model == {}:
            if kargs.get('detect',True) and self.entry != {}:
                self.model = self.MC.models.get(self.detect_lang(), self.MC.models.get('heuristic',{}))
            else:
                self.model = self.MC.models.get('heuristic',{})
        
        # Finally do this to avoid empty models
        if self.model == {}: self.model = self.MC.models.get('heuristic',{})
    

  
        # Load dictionary data if not yet done for this model
        mname = str(self.get_model())
        if mname not in self.MC.loaded_models:

            self.MC.lock.acquire()
            # Load stemmers and syllable processors
            if self.MC.models[mname].get('writing_system',0) != 0:
                if self.MC.models[mname].get('stemmer') is not None:
                    self.MC.models[mname]['stemmer_obj'] = snowballstemmer.stemmer(self.model.get('stemmer','english'))
                else:
                    self.MC.models[mname]['stemmer_obj'] = None

                if self.MC.models[mname].get('pyphen','en_EN') in pyphen.LANGUAGES:
                    self.MC.models[mname]['syls'] = pyphen.Pyphen(lang=self.model.get('pyphen','en_EN'))
                else:
                    self.MC.models[mname]['syls'] = pyphen.Pyphen(lang='en_EN')
            else:
                self.MC.models[mname]['stemmer_obj'] = None
                self.MC.models[mname]['syls'] = None
                
            # Load pickles, parse rules, compile regexes, and merge lookups :)
            re_tokenixer = re.compile(self.MC.models[mname].get('REGEX_tokenizer'))
            re_q_tokenixer = re.compile(self.MC.models[mname].get('REGEX_query_tokenizer'))

            self.MC.models[mname]['REGEX_tokenizer'] = re_tokenixer
            self.MC.models[mname]['REGEX_query_tokenizer'] = re_q_tokenixer

            tmp_rules = self._parse_rules(self.MC.models.get(mname,{}).get('rules',()) )
            self.MC.models[mname]['rules'] = tmp_rules
            tmp_d = self._load_pickle(self.MC.models.get(mname,{}).get('dict_pickle'))
            for d,v in tmp_d.items(): self.MC.models[mname]['d'][d] = v
            
            if not self.MC.models[mname].get('skip_multiling',False):
                temp_lkps = []
                temp_lkps = self.multi_lookups.copy()
                for l in self.MC.models[mname].get('lookups',()):
                    temp_lkps.append(l)
                self.MC.models[mname]['lookups'] = temp_lkps.copy()
                self.model['lookups'] = temp_lkps.copy()

            self.MC.loaded_models.append(mname)
            
            self.MC.lock.release()

        self.d = self.MC.models.get(mname,{}).get('d',{})
        self.rules = self.MC.models.get(mname,{}).get('rules',[])
        self.stemmer = self.model.get('stemmer_obj')
        self.syls = self.model.get('syls')



    # Token template
    token_template = {
    'raw' : '',
    'case' : 0,
    'lc' : '',
    'stem' : '',
    'stem_lc' : '',
    'syls' : 0,
    'chars' : 0,
    'tags' : set(),    
    'prefix' : '',
    'token' : '',
    'pos' : 0
    }



    def tokenize(self, string:str, field, **kargs):
        """ String tokenization and creating a list of token dictionaries
            Tokenization is done mainly by REGEX """
        if field is None: ignore = ()
        else: ignore = scast(field['ignore'], str, '').split(',')

        if field is None: prefix = 'TD'
        else: prefix = field['prefix']

        split = kargs.get('split',True)
        simple = kargs.get('simple', False) # Sometimes we only need simple token list of strings
        query = kargs.get('query',False)

        self.token_count = 0

        if split: 
            toks = re.split(SPLIT_RE, string)
        elif query:
            string = scast(string, str, '')
            toks = re.findall(self.model.get('REGEX_query_tokenizer',"[\w]+"), string)
        else:
            regex = self.model.get('REGEX_tokenizer',"[\w]+")
            if regex == '':
                regex = "[\w]+"

            string = scast(string, str, '')
            toks = re.findall(regex, string)

        tokens_tmp = []

        for t in toks:
            # Strip from trash
            t = t.replace(' ','').replace("\n",'').replace("\t",'')

            # Ommit empties and ignored
            if t == '' or t in ignore: continue

            # Replace aliases/contractions
            if t in self.model.get('aliases',{}).keys(): tokens_tmp = tokens_tmp + list(self.model.get("aliases",{}).get(t,[]))
            else: tokens_tmp.append(t)

        if simple: return tokens_tmp

        self.tokens = []
        tt = {}

        # Create list of dicts based on token template
        for t in tokens_tmp:
            tt = self.token_template.copy()
            tt['raw'] = t
            tt['lc'] = t.lower()
            tt['case'] = self._case(tt['raw']) 
            tt['prefix'] = prefix
            tt['tags'] = set()

            if field['stem']:
                if self.model.get('morphology',1) in (1,2) and self.stemmer is not None:
                    tt['stem'] = self.stemmer.stemWord(t)
                    tt['stem_lc'] = tt['stem'].lower()
                else:
                    tt['stem'] = t
                    tt['stem_lc'] = tt['lc']

                tt['token'] = f'{tt["prefix"]}{str(tt["case"])}{tt["stem_lc"]}'
            else:
                tt['stem'] = None
                tt['stem_lc'] = None
                tt['token'] = f'{tt["prefix"]}{str(tt["case"])}{tt["lc"]}'

            self.tokens.append(tt)
            self.token_count += 1
        
        return tokens_tmp





    def _isnum(self, string):
        """Check if a string is numeral """
        if string.isnumeric(): return True
        tmp = string.replace('.','')
        tmp = tmp.replace(',','')
        if tmp.isnumeric(): return True
        if len(tmp) > 1 and tmp.startswith('-') and tmp[1:].isnumeric(): return True
        if len(tmp) > 0 and self.model.get('writing_system',1) in (1,2) and tmp[0] in self.model.get('numerals',()): return True
        if self.model.get('writing_system',1) == 3 and tmp in self.model.get('numerals',()): return True
        return False


    def _basic_tag(self, **kargs):
        """ Add basic tags to tokens and handle calculating linguistic stats """

        meta = kargs.get('meta', False)

        quot = False

        # Basic single-word tagging
        for i,tok in enumerate(self.tokens):

            stop = False
            t = tok['raw']

            # Marks beginning or ending of a sentence?
            if t in self.model.get('sent_end',()):
                tok['tags'].add('SE')
                self.entry['sent_count'] += 1
                stop = True

            elif t in self.model.get('sent_beg',()):
                tok['tags'].add('SB')
                stop = True

            # Is quotation mark?
            elif t in self.model.get('quot',()):
                if quot:
                    tok['tags'].add('QE')
                    quot = False
                else:
                    tok['tags'].add('QB')
                    quot = True

            elif t in self.model.get('quot_end',()):
                tok['tags'].add('QE')
                stop = True

            elif t in self.model.get('quot_beg',()):
                tok['tags'].add('QB')
                stop = True

            # Is emphasized by markers?
            elif t == '«' or t in self.model.get('emph_end',()):
                tok['tags'].add('EMPE')
                stop = True

            elif t == '»' or  t in self.model.get('emph_beg',()):
                tok['tags'].add('EMPB')
                stop = True
                
            # Is a punctation character?
            elif t == '»' or t in self.model.get('punctation',()):
                tok['tags'].add('PUNCT')
                stop = True

            # Add to word count (it is always done)
            if not stop:
                if not meta:
                    self.entry['word_count'] += 1

                if self.model.get('writing_system',1) in (1,2):
                    tok_l = len(tok['raw'])
                    tok['chars'] = tok_l
                    # Count characters
                    if not meta:
                        self.entry['char_count'] += tok['chars']
                    
                    # Count syllables and polysyllables
                    if self.model.get('pyphen','') != '':
                        syls_count = len(self.syls.inserted(t).split('-'))
                        if syls_count >= 3:
                            tok['tags'].add('POLYSYL')
                            if not meta:
                                self.entry['polysyl_count'] += 1
    
                    tok['syls'] = syls_count
                        

                else: # ... for other writing systems there is no sense in calculating char number. Instead word count is used
                    tok['chars'] = 1
                    tok['syls'] = 1


            # Is a numeral?
            if not stop and self._isnum(t):
                stop = True
                if not meta:
                    self.entry['numerals_count'] += 1
                tok['tags'].add('NUM')
        

            if not stop:
                # Is its case significant?
                
                if tok['case'] != 0 and self.model.get('bicameral',1) in (1,2):
                    if not meta:
                        self.entry['caps_count'] += 1
                    if tok['case'] == 1 and tok_l > 1:
                        tok['tags'].add('CAP')
                    elif tok['case'] == 2 and tok_l == 1:
                        tok['tags'].add('SCAP')
                    elif tok['case'] == 2 and self.model.get('writing_system',1) in (1,2):
                        tok['tags'].add('ALLCAP')

                # Is it a non-capitalized stop word?
                if tok['lc'] in self.model.get('stops',()) and not (tok['case'] == 2 and self.model.get('bicameral',1) != 0):
                    tok['tags'].add('STOP')
                    tok['tags'].add('COMM')
                    if not meta:
                        self.entry['com_word_count'] += 1
                # Is it a common word?
                elif tok['lc'] in self.model.get('commons',()) or tok['stem_lc'] in self.model.get('commons_stemmed',()):
                    tok['tags'].add('COMM')
                    if not meta:
                        self.entry['com_word_count'] += 1
                else:
                    tok['tags'].add('UNCOMM')



            self.tokens[i] = tok









    def _dict_lookup(self, pos:int, dc:list, **kargs):
        """ Lookup tokens in a dictionary (structure given in sample model generators) """    
        match = True
        tag = None
        len = None
        stem = kargs.get('stem',False)

        for d in dc:
            tag = d[1]
            len = d[2]
            match = True
            if stem: tok = self.tokens[pos]['stem_lc']
            else: tok = self.tokens[pos]['lc']
            # If we have a single whole word, the case is simple...
            if len == 1:
                if tok == d[0][0]:
                    match = True
                    break
            # Below, we implement some kind of morphology-like distictions
            elif len == -1:
                if tok.endswith(d[0][0]):
                    match = True
                    break
            elif len == -2:
                if tok.startswith(d[0][0]):
                    match = True
                    break
            elif len == -3:
                if tok.contains(d[0][0]):
                    match = True
                    break

            # ... and finally phrase searching
            for j, w in enumerate(d[0], start=1):
                if tok != w:
                    match = False
                    break
            
                #print(j, w, tok, pos, d[0])
                if pos+j < self.token_count:
                    if stem: tok = self.tokens[pos+j]['stem_lc']
                    else: tok = self.tokens[pos+j]['lc']
                else:
                    if j < len:
                        match = False
                    break


            if match:
                break
        
        if match:
            return tag, len
        else:
            return None, None









    def _advanced_tag(self, **kargs):
        """ Performs advanced tagging of tokens based on dictionary lookup - helpful in feature extraction """

        for i, t in enumerate(self.tokens):

            t['tags'] = set(t['tags'])

            if t['raw'].startswith('#'):
                t['tags'].add('HASHTAG')
                continue


            # Ignore punctations and such
            if t['tags'].intersection({'NUM','PUNCT','QB','QE','SB','SE'}) != set(): continue
            
            tag = -1
            # Perform lookups given prescribed order and don't repeat lookups if matched
            last_matched = -1
            for o in self.model.get('lookups',()):

                if i <= last_matched: continue

                dc = o.get('name')
                caps_only = o.get('caps_only', False)
                stop_if_matched = o.get('stop_if_matched', False)
                stem = o.get('stem', False)
                uncomm_only = o.get('uncommon_only',False)

                if uncomm_only and t['tags'].intersection({'COMM','STOP'}) != set(): continue

                if caps_only and t['case'] == 0: continue

                (tag, len) = self._dict_lookup(i, self.d.get(dc, self.MC.multi_dict.get(dc,())), stem=stem)
                if tag is None:
                    continue
                else:
                    if len == 1 or len < 0:
                        self.tokens[i]['tags'].add(tag + '_BEG')
                        self.tokens[i]['tags'].add(tag + '_END')
                    elif len > 1:
                        self.tokens[i]['tags'].add(tag + '_BEG')
                        self.tokens[i+len-1]['tags'].add(tag + '_END')

                        for j in range(len-2):
                            self.tokens[i+j+1]['tags'].add(tag)

                    last_matched += len

                    if stop_if_matched:
                        break


                    






    def _extract_patterns(self, field, **kargs):
        """ Feature extraction for learning by matching rule strings from language model against taggs of tokens """
        if self.debug: print(f'Extracting features from field {str(field)}...')

        # Default weight for field to adjust
        field_weight = field['weight']
        if field_weight == 0: return 0

        self._advanced_tag()

        meta = field['meta']

        self.regex_rule_str = ''

        if field['all_feat']:
            prefix = field['prefix']
            field_name = f"""{field['name']}: """
        else:
            prefix = '..'
            field_name = ''

        # Create line for regex search with tags and token numbers
        for i,t in enumerate(self.tokens):
            tags = ''
            tgs = scast(t['tags'], list, [])
            if tgs == []:
                continue
            for tt in sorted(tgs):
                tags=f"{tags};{tt}"
            self.regex_rule_str = f'{self.regex_rule_str} {tags}:{str(i)}'

        if meta: rules = ({},)
        else: rules = self.rules       
        # Search with regex and extract token numbers
        for r in rules:

            if r.get('pattern','') == '' and not field['meta']: continue

            if meta:
                matches = (self.regex_rule_str[1:],)
                rule_stem = True
                rule_case = False
                rule_strip = 0 
            else:
                matches = re.findall(r.get('pattern',''), self.regex_rule_str)
                rule_stem = r['stem']
                rule_case = r['case']
                rule_strip = r['strip']

            rule_weight = (r.get('weight',1) * field_weight)

            if rule_stem: qtype = 4
            else: qtype = 5

            for m in matches:
                
                match_string = ''
                name = ''
                
                matches = m.split(' ')
                if rule_strip in (1,3): del matches[0]
                if rule_strip in (2,3): del matches[-1]

                # Exclude stop-word singletons for balance
                if len(matches) == 1: singleton = True
                else: singleton = False

                for w in matches:
                    
                    word_no = scast(w.split(':')[1], int, -1)
                    if word_no == -1: continue

                    if singleton and self.tokens[word_no].get('tags',set()).intersection(self.model.get('no_feature',{'PUNCT'})) and not self.tokens[word_no].get('tags',set()).intersection({'ALLCAP'}):
                        continue

                    # ... And combine them into a feature dictionary...
                    if rule_stem: t_str = self.tokens[word_no].get('stem_lc',None)
                    else: t_str = self.tokens[word_no].get('lc',None)
                        
                    if t_str is None: t_str = self.tokens[word_no].get('lc',None)
                    if t_str is None: continue

                    if rule_case: match_string = f'{match_string} {prefix}.{t_str}'
                    else: match_string = f'{match_string} {prefix}{str(self.tokens[word_no].get("case",0))}{t_str}'

                    name = f'{name} {self.tokens[word_no].get("raw",0)}'
        

                name = f'{field_name}{name.strip()}'
                match_string = f'{qtype}{match_string.strip()}'
                
                # Add to global feature dictionary
                if match_string not in (f'{qtype}', None):
                    if match_string not in self.features.keys():
                        self.features[match_string] = [0,0,'']

                    self.features[match_string][0] = self.features.get(match_string,[0])[0] + rule_weight
                    self.features[match_string][1] = qtype
                    self.features[match_string][2] = name







    def _prefix(self, field, **kargs):
        """ Ascertain a prefix for a token based on field and case """
        if field is None: prefix = f"""T{kargs.get('wildcard','.')}"""
        else: prefix = PREFIXES[field]['prefix']

        # Add case wildcard to prefix if instructed to
        if kargs.get('case_ins',False): 
            prefix = f'{prefix}{kargs.get("wildcard",".")}'
        else: 
            prefix = f'{prefix}{str(kargs.get("case",0))}'

        return prefix




    def _case(self, t:str, **kargs):
        """ Check token's case and code it into (0,1,2)"""
        if self.model.get('writing_system',1) == 1:
                if t.islower(): case = 0
                elif t.isupper() and len(t) > 1: case = 2
                elif t[0].isupper(): case = 1
                else: case = 3

        elif self.model.get('writing_system',2) == 1:
            if t in self.model.get('capitals',[]): case = 1

        return case
        
        





    def _index_field(self):
        """ Construct strings of tokens to allow full text search by means of SQL """
        self.token_str = f'{self.token_str}   '
        self.raw_token_str = f'{self.raw_token_str}   '

        for t in self.tokens:

            pos_str = str(self.last_pos).zfill(7)
            self.last_pos += 1

            t['tags'] = set(t['tags'])
            if t['tags'].intersection(self.model.get('no_index',{'PUNCT'})) != set():
                self.raw_token_str = f'{self.raw_token_str} {pos_str}{t["prefix"]}{t["case"]}{t["lc"]}'
            elif t['tags'].intersection(self.model.get('dividers',set())) != set():
                self.raw_token_str = f'{self.raw_token_str} {pos_str}{t["prefix"]}0{t["raw"]}'
                self.token_str = f'{self.token_str}   '
            else:
                self.token_str = f'{self.token_str} {pos_str}{t["token"]}'
                self.raw_token_str = f'{self.raw_token_str} {pos_str}{t["prefix"]}{t["case"]}{t["lc"]}'



                




    def process_field(self, string:str, field:str, **kargs):
        """ Process a single field """

        field = PREFIXES[field]
        learn = kargs.get('learn',False)
        index = kargs.get('index',True)

        # Tokenize
        self.tokenize(string, field, split=False, query=False)
        self._basic_tag(meta=field['meta'])

        # .. and push on ...
        if learn: self._extract_patterns(field)

        if index: self._index_field()






    def _load_entry(self, entry, **kargs):
        self.entry = entry
        if kargs.get('no_model',False): return 0
        # This method is a de-facto entry processor, so language will be set-up for the whole thing
        self.charset = self.entry.get('charset')
        self.set_model(self.entry.get('lang'))
        if self.entry.get('lang') is None: self.entry['lang'] = self.get_model()




    def process_entry(self, entry, **kargs):
        """ Proces fields given in a list from Feedex's main class """
        learn = kargs.get('learn',False)
        index = kargs.get('index',True)
        stats = kargs.get('stats',True)
        rank = kargs.get('rank', False)

        # Set processed entry
        self._load_entry(entry)

        # Nullify all present statistics, strings and lists
        self.tokens = [] # List of tokens for further processing
        self.token_str = ''
        self.raw_token_str = ''
        self.last_pos = 0
        self.features = {}

 
        if index or learn or stats:

            # Zeroe all the counters
            for f in self.entry.keys():
                if f in ('sent_count','word_count','char_count','polysyl_count','com_word_count','numerals_count','caps_count','readability'): self.entry[f] = 0

            # Process fields
            for f,v in self.entry.items():
                if f in LING_LIST:
                    field = scast(v, str, '')
                    if field.replace(' ','') == '': continue
                    self.process_field(field, f, learn=learn, index=index)

            #Pad token string end and insert to entry
            self.token_str = f'{self.token_str}   '
            self.raw_token_str = f'{self.raw_token_str}   '
            self.entry['tokens'] = self.token_str
            self.entry['tokens_raw'] = self.raw_token_str

            if self.debug and learn: print(self.features)

            # Consolidate text stats
            if stats: self._calculate_stats()


        if rank: (self.entry['importance'], self.entry['flag']) = self.match_rules()
            






    def _calculate_stats(self):
        """ Calculates document's statistics """
        if self.entry['word_count'] == 0: 
            self.entry['readability'] = 0
            self.entry['weight'] = 0
            return 0

        if self.model.get('writing_system',1) == 0: self.entry['polysyl_count'] = 0

        if self.entry['sent_count'] == 0: self.entry['sent_count'] = 1

        # Calculate readability
        common_freq = self.entry['com_word_count']/self.entry['word_count']
        long_freq = self.entry['polysyl_count']/self.entry['word_count']

        avg_word_len = self.entry['char_count']/self.entry['word_count']
        avg_sent_len = self.entry['word_count']/self.entry['sent_count']

        if self.model.get("logographic",False): readability = common_freq * 1.25   +  1/avg_sent_len * 0.7
        else: readability = common_freq * 1  +  long_freq * 0.25  +  1/avg_word_len * 0.50   +   1/avg_sent_len * 0.25                             
        self.entry['readability'] = readability * 100

        # Calculate document weight (smaller with word count adjusted by uncommon words)
        self.entry['weight'] = 1/log10(coalesce(self.entry['com_word_count'],0)+2)

                
        



    



    def detect_lang(self):
        """ Detects language from loaded fields by various methods and constructs probability distribution """

        if self.debug: print("Language not provided. Running detection...")

        if self.charset is not None: charset = self.charset.lower()
        else: charset = 'utf-8'

        lang_table = []
        
        # First, eliminate irrelevant charsets
        if charset == 'utf-8':
            lang_table = self.MC.models.keys()
        else:
            for l,m in self.MC.models.items():         
                for ch in m.get('charsets',['utf-8']):
                    if charset in ch.lower():
                        lang_table.append(l)

        # ... and return lang if only one remained
        if len(lang_table) == 1:
            return lang_table[0]

        if not isinstance(self.entry, dict): return 'heuristic'
        elif self.entry == {}: return 'heuristic'

        # .. else tokenize and get unique characters of text
        tokens = []
        for f, v in self.entry.items():
            if f in LING_TEXT_LIST:                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                     
                tokens = tokens + re.findall(r"[\w]+",scast(v, str, ''))

        tokens = set(tokens)

        if len(tokens) <= 3: return 'heuristic'

        chars = ''
        for t in tokens:
            chars = chars + t
        chars = set(chars)

        # Construct language freq distribution dictionary
        langs = {}
        for l in lang_table: langs[l] = 0
            

        # And analyze one by one with stoplists, swadesh/common lists and unique characters
        for l, v in langs.items():

            if l == 'heuristic': continue

            if not self.MC.models[l].get('logographic',False):
                
                for t in tokens:
                    t = t.lower()
                    if t in self.MC.models[l].get('stops',[]): langs[l] += 1
                    if t in self.MC.models[l].get('swadesh',[]): langs[l] += 1
                    if t in self.MC.models[l].get('commons',[]): langs[l] += 1


                for c in chars:
                    c = c.lower()
                    if c in self.MC.models[l].get('unique_chars',''):
                        langs[l] += 10  #This is a big deal, so it is weighted quite highly


            else:
        
                for c in chars:
                    c = c.lower()

                    if c in self.MC.models[l].get('stops',[]): langs[l] += 1
                    if c in self.MC.models[l].get('swadesh',[]): langs[l] += 1
                    if c in self.MC.models[l].get('commons',[]): langs[l] += 1

        if self.debug: print("Distribution: ", langs)

        if langs == {}: maximum = 'heuristic'
        else: maximum = max(langs, key=langs.get)

        return(maximum)








    def match_rules(self, **kargs):
        """ Calculates importance and flags given set of rules and a document represented by fields """
        if kargs.get('entry') is not None: self._load_entry(kargs.get('entry'), no_model=False)

        final_weight = 0
        flag = 0
        entry_weight = dezeroe(scast(self.entry['weight'], float, 1),1)

        to_var = kargs.get('to_var',False)
        to_print = kargs.get('print',False)

        if to_var or to_print:
            var_str=''

        flag_dist = {} # Distribution of flag matches
        entry_dist = {} #If matched with many terms from one entry it will significantly raise importance

        for r in self.MC.rules:

            name = r[1]
            qtype = scast(r[2], int, 0)
            feed = scast(r[3], int, -1)
            if feed is not None and feed != -1 and self.entry['feed_id'] != feed: continue

            field = scast(r[4], str, None)
            string = scast(r[5], str, '')

            if len(string) < 1: continue

            if r[6] == 1: case_ins = True
            else: case_ins = False

            lang = r[7]
            if lang is not None and lang != self.get_model(): continue

            weight = r[8]
            additive = r[9]
            learned = scast(r[10], int, 0)
            do_flag = scast(r[11], int, 0)
            context_id = scast(r[12], int, 0)

            if learned == 1:
                if qtype == 4:
                    matched = self.sregex_matcher(string, scast(self.entry['tokens'],str,''))
                elif qtype == 5:
                    matched = self.sregex_matcher(string, scast(self.entry['tokens_raw'],str,''))

            else:
                if qtype == 3:
                    if field is None: field_lst = LING_TEXT_LIST
                    else: field_lst = [field]
                    matched = 0

                    for f in field_lst:
                        if type(self.entry[f]) is not str: continue
                    
                        if case_ins: matches = re.findall(string, self.entry[f], re.IGNORECASE)
                        else: matches = re.findall(string, self.entry[f])

                        matched += len(matches)

                else:
                    phrase = self.f_phrase(string, qtype=qtype, field=field, sqlize=False, regexify=True, case_ins=case_ins)
                    matched = self.match_fields(phrase, qtype, field, case_ins=case_ins, snippets=False)[0]
                
            if matched > 0:

                entry_dist[context_id] = entry_dist.get(context_id,0) + (matched * weight)

                if to_var or to_print:
                    var_str=f"""{var_str}\nName: {name}  |  String: {string}  |  Type: {qtype}  |  Field: {field}  |  Learned?: {learned}  |  Weight: {weight:.4f}  |  Flag: {do_flag}  |  Matched: {matched} | Context: {context_id}"""

                if learned not in (1,2) and do_flag > 0: flag_dist[do_flag] = flag_dist.get(do_flag,0) + (weight * matched)

                if additive == 1: final_weight = final_weight + (weight * matched)
                else: final_weight = weight * matched
    


        importance = entry_dist.get(0,0)

        entry_dist[0] = 0
        entry_dist[self.entry['id']] = 0

        contexts_sorted = sorted(entry_dist.items(), key=lambda x:abs(x[1]), reverse=True)
        
        best_contexts = []
        
        for i,cx in enumerate(contexts_sorted):
            if i > MAX_RANKING_DEPTH: break
            importance = importance + cx[1]
            best_contexts.append(cx[0])

        importance = importance * self.entry['weight']

        if to_var:
            var_str = f"""{var_str}
------------------------------------------------------------------------------------------------------------------------------------------------
Calculated importance (for today): {importance:.4f}

Best matched contexts:
"""
            for cx in best_contexts: var_str = f"{var_str} {cx};"
        
        if to_var: return var_str
        else:
            if to_print: print(var_str)
            if flag_dist != {}:
                flag = max(flag_dist, key=flag_dist.get)
            return importance, flag






    def match_fields(self, phrase:dict, qtype:int, field:str, **kargs):
        """ Performs phrase matching given a search phrase and field list. Returns match count and snippets if needed """
        if kargs.get('entry') is not None: self._load_entry(kargs.get('entry'), no_model=True)

        case_ins = kargs.get('case_ins',False)
        snippets = kargs.get('snippets',True)

        snips = []
        matches = 0

            
        if qtype in (1,2,4,5):
            if type(self.entry['tokens']) is not str: return (0, [])
            if type(self.entry['tokens_raw']) is not str: return (0, [])

        if qtype == 0:
            
            if field is None: field_lst = LING_TEXT_LIST
            else: field_lst = [field]

            for f in field_lst:
                f = self.entry[f]
                if type(f) is not str: continue

                if case_ins: fs = f.lower()
                else: fs = f

                if snippets: 
                    (new_matches, sn) = self.str_matcher(phrase['str_matching'], fs, snippets=True, orig_field=f)
                    for s in sn: snips.append(s)
                else: (new_matches, sn) = self.str_matcher(phrase['str_matching'], fs, snippets=False)


                matches += new_matches


        elif qtype in (1,2,):

            if qtype == 1: matched = re.findall(phrase['regex'], self.entry['tokens'] )
            elif qtype == 2: matched = re.findall(phrase['regex'],  self.entry['tokens_raw'] )

            if snippets:
                for m in matched: 
                    if len(snips) <= MAX_SNIPPET_COUNT: snips.append(self.posrange(m, self.entry['tokens_raw'], 8))

            matches += len(matched)
        
        elif qtype == 4:
            matches = self.sregex_matcher(phrase['str_matching'], self.entry['tokens'])
        elif qtype == 5:
            matches = self.sregex_matcher(phrase['str_matching'], self.entry['tokens_raw'])

        return matches, snips








    def f_phrase(self, string:str, **kargs):
        """ Prepares phrase for query, returns PHRASE dictionary """
        qtype = kargs.get('qtype',0)
        field = kargs.get('field')
        case_ins = kargs.get('case_ins',False)

        sqlize = kargs.get('sqlize',True)
        regexify = kargs.get('regexify', True)
        rstr = random_str(string=string)
        rstr2 = random_str(string=string)

        phrase = {}
        phrase['raw'] = string
        phrase['empty'] = False
        phrase['beg'] = False
        phrase['end'] = False
        phrase['has_wildcards'] = False


        # Deal with start/end
        def _detect_begend(string):
            if string.startswith('^'):
                phrase['beg'] = True
                string = string[1:]
            elif string.startswith('\^'):
                string = string[1:]
        
            if string.endswith('\$'):
                string = f'{string[:-2]}$'
            elif string.endswith('$'):
                phrase['end'] = True
                string = string[:-1]
    
            return string


        # Condense wildcards
        def _cond_wc(string):
            string = string.replace('\*', rstr)
            while '**' in string: string = string.replace('**','*')

            if qtype == 0:
                if '*' in string: phrase['has_wildcards'] = True
                tmp_str = string
                if '.' in tmp_str.replace('\.',rstr2): phrase['has_wildcards'] = True

            string = string.replace(rstr, '\*')
            return string

        def _repl_wc_sql(sql_str):
            sql_str = sql_str.replace('\*',rstr)
            sql_str = sql_str.replace('\.',rstr2)
            sql_str = sql_str.replace('*','%')
            sql_str = sql_str.replace('.','_')
            sql_str = sql_str.replace(rstr, '*')
            sql_str = sql_str.replace(rstr2, '.')
            return sql_str

        def _add_begend_sql(sql_str):
            if not phrase['beg']: sql_str = f"%{sql_str}" 
            if not phrase['end']: sql_str = f"{sql_str}%"
            return sql_str


        def _str_match_split(string):
            sm = []
            string = string.replace('\*', rstr)
            string = string.replace('\.', rstr2)
            for s in string.split('*'):
                if s in ('',' ',None): continue
                for ss in s.split('.'):
                    if ss in ('',' ',None): continue
                    ss = ss.replace(rstr, '*')
                    ss = ss.replace(rstr2, '.')
                    sm.append(ss)
            
            if len(sm) == 1: return ( sm[0], )
            elif len(sm) > 0: return ( sm[0], sm[-1])
            else: return (string)



        if qtype == 0:
            
            string = _detect_begend(string)
            string = _cond_wc(string)

            if string.replace('*','') == '':
                phrase['empty'] = True
                return phrase

            if case_ins: string = string.lower()
            
            if sqlize:
                phrase['sql'] = f'{self._sqlize(string, with_wc=True)}'
                phrase['sql'] = _add_begend_sql(phrase['sql'])
                phrase['sql'] = _repl_wc_sql(phrase['sql'])

            phrase['str_matching'] = _str_match_split(string)
            
             




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
            if string.replace(' ','').replace('*','').replace('~','').replace('.','') == '':
                phrase['empty'] = True
                return phrase
        
            string = _detect_begend(string)
            string = string.strip()
            string = _cond_wc(string)

            # Tokenize query
            phrase['sql'] = ''
            phrase['regex'] = ''
            qtokens = self.tokenize(string, None, simple=True, query=True)
            
            

            for t in qtokens:
            
                sql = ''
                tok = t
                has_wc = False
                is_wc = False

                tst_tok = tok
                tst_tok = tst_tok.replace('\.','').replace('\*','')

                if tok.replace('*','') == '':
                    is_wc = True
                    phrase['has_wildcards'] = True
                    regex = '(?:\s[^\s]*?)*?'

                elif tok == '~' or (tok.startswith('~') and tok.replace('~','').isdigit()):
                    is_wc = True
                    phrase['has_wildcards'] = True
                    near = scast(tok.replace('~',''), int, 5)
                    regex = "(?:\s[^\s]*?){0,"+str(near)+"}"
                
                elif '*' in tst_tok: 
                    has_wc = True
                    phrase['has_wildcards'] = True
                    case = self._case(tok)
                
                elif '.' in tst_tok: 
                    has_wc = True
                    phrase['has_wildcards'] = True
                    case = self._case(tok)

                else: case = self._case(tok)

                
                if qtype == 1 and not is_wc and not has_wc: tok = self.stemmer.stemWord(tok)

                if sqlize:
                    if is_wc:
                        phrase['sql'] = f"""{phrase['sql']}%"""
                    else:
                        tok = tok.lower()
                        sql = self._sqlize(tok)

                        if has_wc: sql = _repl_wc_sql(sql)

                        prefix = self._prefix(field, wildcard='_', case=case, case_ins=case_ins)
                        sql = f"_______{prefix}{sql.lower()}"
                        phrase['sql'] = f"""{phrase['sql']} {sql}"""

                if regexify:
                    if is_wc:
                        phrase['regex'] = f"""{phrase['regex']}{regex}"""
                    else:
                        regex = self._regexify(tok)
                        regex = regex.replace('\*',rstr)
                        regex = regex.replace('\.',rstr2)
                        regex = regex.replace('*','[^\s]*?')
                        regex = regex.replace('.','[^\s]?')
                        regex = regex.replace(rstr,'\*')
                        regex = regex.replace(rstr2,'\.')
                        regex = f".......{self._prefix(field, wildcard='.', case_ins=case_ins, case=case)}{regex}"
                        phrase['regex'] = f"""{phrase['regex']} {regex}"""
            



            if sqlize:
                phrase['sql'] = f"{phrase['sql']} "
                phrase['sql'] = _add_begend_sql(phrase['sql'])

            if regexify:
                if phrase['beg']: phrase['regex'] = f"   {phrase['regex']}"
                if phrase['end']: phrase['regex'] = f"{phrase['regex']}   "
                phrase['regex'] = re.compile(phrase['regex'])





        return phrase











    ################################################
    # Utilities


    def sregex_matcher(self, string, field):
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






    def str_matcher(self, string, field, **kargs):
        """ Simply matches string and extracts snippets if needed """
        snippets = kargs.get('snippets',True)
        orig_field = kargs.get('orig_field', field)

        field = field.replace('\n','').replace('\r','')
        orig_field = orig_field.replace('\n','').replace('\r','')

        snips = []
        matches = 0
        fl = len(field)

        for s in string:
            idx = 0
            abs_idx = 0
            tmp_field = field
        
            l = len(s)

            while idx != -1:
                idx = tmp_field.find(s)
                if idx != -1:
                    if snippets and matches <= MAX_SNIPPET_COUNT:
                        abs_idx += idx
                        snips.append( self.srange(orig_field, abs_idx, l, fl, 70) )
                        abs_idx += l

                    matches += 1
                    tmp_field = tmp_field[idx+l:]

        return matches, snips


    def srange(self, string:str, idx:int, l:int, sl:int, rng:int):
        """ Get range from string - for extracting snippets"""
        string=string.replace(BOLD_MARKUP_BEG,'').replace(BOLD_MARKUP_END,'').replace('\n','').replace('\r','')

        llimit = idx - rng
        if llimit < 0:
            llimit = 0
        if llimit > 0:
            beg = '...'
        else:
            beg = ''

        rlimit = idx + l + rng
        if rlimit > sl:
            rlimit = sl
        if rlimit < sl:
            end = '...'
        else:
            end = ''
    
        return f'{beg}{string[llimit:idx]}', f'{string[idx:idx+l]}', f'{string[idx+l:rlimit]}{end}'





    def posrange(self, pos:str, string:str, rng:int):
        """ Extracts snippet from raw tokens given a position list """    
        tokens = []
        for t in scast(string, str, '').split(' '):
            if t != '': tokens.append(t)
        
        tl = len(tokens)

        phr_toks = []
        tok_pref = None
        for t in pos.split(' '):
            if t.replace(' ','') != '':
                phr_toks.append( scast(t[0:7], int, -1) )
                if tok_pref is None: tok_pref = t[7:9]

        phr_start = phr_toks[0]
        phr_stop = phr_toks[-1]
    
        sel_start = phr_start - rng
        if sel_start < 0: sel_start = 0
        if sel_start > 0: beg = '...'
        else: beg = ''

        sel_stop = phr_stop + rng
        if sel_stop > tl: sel_stop = tl
        if sel_stop < tl: end = '...'
        else: end = ''

        posns = range(sel_start, sel_stop, 1)
        scan_start = sel_start - 5
        if scan_start < 0: scan_start = 0
        scan_stop = sel_stop + 5
        if scan_stop > tl: scan_stop = tl

        bstring = f''
        estring = f''
        phrstring = ''

        for t in tokens[scan_start:scan_stop]:

            tpos = scast(t[0:7], int, -1)

            if tpos in posns:

                tpref = t[7:9]
                tok = t[10:]

                if t[9] == '0': tok = tok
                elif t[9] == '1': tok = tok.capitalize()
                else: tok=tok.upper()

                if tpos < phr_start:
                    if tpref == tok_pref: bstring = f'{bstring} {tok}'
                elif tpos > phr_stop:
                    if tpref == tok_pref: estring = f'{estring} {tok}'
                else:
                    phrstring = f'{phrstring} {tok}'

        return f'{beg}{bstring}', f'{phrstring}', f'{estring}{end}'





    def _regexify(self, string:str, **kargs):
        """ Escapes REGEX scepial chars """
        #regex = string.replace('.','\.')
        regex = string.replace('$','\$')
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
        if kargs.get('with_wc',False): regex = regex.replace('*','\*')
        return regex




    def _sqlize(self, string:str, **kargs):
        """ Escapes SQL wildcards """
        #   sql = string.replace('\\', '\\\\')
        sql = string.replace('%', '\%')
        sql = sql.replace('_', '\_')
        return sql








