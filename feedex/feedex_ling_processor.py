# -*- coding: utf-8 -*-
""" Classes for basic NLP text processing for Feedex """

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


    def __init__(self, **args):

        # Load configuration
        self.config = args.get('config', DEFAULT_CONFIG)

        # Input parameters
        self.debug = args.get('debug',False)

        # Load general dictionary (lookup for all languages - Acronyms, Names and such)
        self.multi_lookups = [   
        {'name': 'multi_func', 'caps_only': True, 'stop_if_matched':True, 'stem':False, 'uncommon_only':False},    
        {'name': 'multi_acronyms', 'caps_only': True, 'stop_if_matched':True, 'stem':False, 'uncommon_only':True},    
        {'name': 'multi_geo', 'caps_only': True, 'stop_if_matched':True, 'stem':False, 'uncommon_only':False},    
        {'name': 'multi_names', 'caps_only': True, 'stop_if_matched':True, 'stem':False, 'uncommon_only':False},    
        {'name': 'multi_surnames', 'caps_only': True, 'stop_if_matched':True, 'stem':False, 'uncommon_only':False}    
        ]
        self.multi_dict = self._load_pickle('multi_dict.pkl')
        if type(self.multi_dict) != dict: self.multi_dict = {}

        # Load model headers from specified dir
        self.models = {}
        if os.path.isdir(FEEDEX_MODELS_PATH):
            for header_file in os.listdir(FEEDEX_MODELS_PATH):
                curr_model = {}
                curr_model_name = None
                header_file = os.path.join(FEEDEX_MODELS_PATH, header_file)
                if header_file.endswith('_header.pkl') and os.path.isfile(header_file):
                    try:
                        with open(header_file, 'rb') as f:
                            curr_model = pickle.load(f)
                    except:
                        sys.stderr.write(f'{TERM_ERR}Could not load pickle {TERM_ERR_BOLD}{header_file}{TERM_ERR} ...{TERM_NORMAL}\n')
                        continue

                    curr_model_name = slist(curr_model.get('names',()),0,None)
            
                    if curr_model_name != None:
                        self.models[curr_model_name] = curr_model.copy()
        else:
            sys.stderr.write(f'{TERM_ERR}Invalid path for language models! ({TERM_ERR_BOLD}{FEEDEX_MODELS_PATH}{TERM_ERR}){TERM_NORMAL}\n')


        # Set default model as heuristic 
        self.models['heuristic'] = HEURISTIC_MODEL.copy()
    
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

        self.stats = {}
    
        self.token_count = 0
        self.last_pos = 0 # Position of last indexed token

        # This is a currently loaded model. They are not big, so can be changed quite rapidly. 
        self.loaded = []
    
        # Stemmer from Snowball. Also - a class-wide config for convenience, as fields per entry
        # are almost always in one language
        self.stemmer = []

        # Addidional params
        self.charset = 'utf-8'

        # Global text parameters
        # Quotation state, if not false it should take value of closing symbol
        self.quot = []
        
        # Defaults fo safety
        self.def_d = (((),None,None,None))
        # Set starting model
        self.set_model('heuristic')





    def get_model(self):
        """ Quickly get currently loaded model """
        return slist(self.model.get('names',None), 0, None)






    def _find_model(self, model:str):
        """ Find model given a language name. First search the names list from a model (including crude globs).
            Every model is searched and FIRST one to match is returned """
        model = scast(model, str, '')
        if model == None: return None

        if model in self.models.keys():
            return model

        for m in self.models.keys():
            m = scast(m, str, '')

            for n in self.models[m].get('names',()):
                if model.lower() == n.lower():
                    return m
                if n.endswith('*') and model.startswith(n.lower().replace('*','')):
                    return m
        
        return None




    def _load_pickle(self, pkl:str, **args):
        """ Load pickle file """
        if pkl == None: return {}
        if not os.path.isdir(FEEDEX_MODELS_PATH):
            sys.stderr.write(f'{TERM_ERR}Invalid path for language models! ({TERM_ERR_BOLD}{FEEDEX_MODELS_PATH}{TERM_ERR}){TERM_NORMAL}')
            return {}
        pickle_path = FEEDEX_MODELS_PATH + "/" + pkl
        lst = None
        if os.path.isfile(pickle_path):
            try:
                with open(pickle_path, 'rb') as f:
                    lst = pickle.load(f)
                    if type(lst) != dict: 
                        sys.stderr.write(f'{TERM_ERR}Data not a dictionary structure! {TERM_ERR_BOLD}{pickle_path}{TERM_NORMAL}\n')
                        return {}
            except:
                sys.stderr.write(f'{TERM_ERR}Could not load pickle {TERM_ERR_BOLD}{pickle_path}{TERM_ERR}...{TERM_NORMAL}\n')
                lst = {}
        else:
            sys.stderr.write(f'{TERM_ERR}Could not find pickle path {TERM_ERR_BOLD}{pickle_path}{TERM_ERR} ...{TERM_NORMAL}\n')
            lst = {}

        return lst







    def _parse_rules(self, irules):
        """ Parse rule strings given in a language  model """
        rules = []
        for r in irules:
            rule = {}
            rule['case'] = scast( slist(r,0,None), bool, False)
            rule['weight'] = scast( slist(r,1,None), float, 0)
            rule['stem'] = scast( slist(r,2,None), bool, False)
            rule['strip'] = scast( slist(r,3,None), int, 0)
            rule['pattern'] = re.compile(scast( slist(r,4,None), str, ''))                        
            rules.append(rule)

        return tuple(rules)






    def set_model(self, model:str, **args):
        """ Set a language model to currently use given by name"""
        prop_model = self._find_model(model)
        if prop_model == self.get_model() and prop_model != None: return 0

        # First do what is needed if none is given
        if (model == None or model == 'heuristic') and args.get('detect',True) and self.fields not in ([],()):
            # Call language detection and set up 'heuristic' as default
            self.model = self.models.get(self.detect_lang(), self.models.get('heuristic',{}))
        else:
            # Try finding by name (usually this will work):
            self.model = self.models.get(prop_model,{})


        # But sometimes it wont...
        if self.model == {}:
            if args.get('detect',True) and self.fields != []:
                self.model = self.models.get(self.detect_lang(), self.models.get('heuristic',{}))
            else:
                self.model = self.models.get('heuristic',{})
        
        if self.model == {}: self.model = self.models.get('heuristic',{})
    

        # Setup stemmers and uh... 'syllablers' beforehand
        if self.model.get('writing_system',0) != 0:
            if self.model.get('stemmer') != None:
                self.stemmer = snowballstemmer.stemmer(self.model.get('stemmer','english'))
            else:
                self.stemmer = None

            if self.model.get('pyphen','en_EN') in pyphen.LANGUAGES:
                self.syls = pyphen.Pyphen(lang=self.model.get('pyphen','en_EN'))
            else:
                self.syls = pyphen.Pyphen(lang='en_EN')

        # Load dictionary data if not yet done for this model
        mname = str(self.get_model())
        if mname not in self.loaded:

            # Load pickles, parse rules, compile regexes, and merge lookups :)
            re_tokenixer = re.compile(self.models[mname].get('REGEX_tokenizer'))
            re_q_tokenixer = re.compile(self.models[mname].get('REGEX_query_tokenizer'))

            self.models[mname]['REGEX_tokenizer'] = re_tokenixer
            self.models[mname]['REGEX_query_tokenizer'] = re_q_tokenixer

            tmp_rules = self._parse_rules(self.models.get(mname,{}).get('rules',()) )
            self.models[mname]['rules'] = tmp_rules
            tmp_d = self._load_pickle(self.models.get(mname,{}).get('dict_pickle'))
            for d in tmp_d.keys(): self.models[mname]['d'][d] = tmp_d[d]
            
            if not self.models[mname].get('skip_multiling',False):
                temp_lkps = []
                temp_lkps = self.multi_lookups.copy()
                for l in self.models[mname].get('lookups',()):
                    temp_lkps.append(l)
                self.models[mname]['lookups'] = temp_lkps.copy()
                self.model['lookups'] = temp_lkps.copy()

            self.loaded.append(mname)
            
        self.d = self.models.get(mname,{}).get('d',{})
        self.rules = self.models.get(mname,{}).get('rules',[])




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



    def tokenize(self, string:str, field:int, **args):
        """ String tokenization and creating a list of token dictionaries
            Tokenization is done mainly by REGEX """
        ignore = scast(args.get('ignore',[]), list, [])
        split = args.get('split',True)
        stem = args.get('stem',False)
        simple = args.get('simple', False) # Sometimes we only need simple token list of strings
        query = args.get('query',False)

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

        if simple:
            return tokens_tmp

        self.tokens = []
        tt = {}

        # Create list of dicts based on token template
        for t in tokens_tmp:
            tt = dict(self.token_template)
            tt['raw'] = t
            tt['lc'] = t.lower()
            tt['case'] = self._case(tt['raw']) 
            tt['prefix'] = PREFIXES.get(field, ['TD'])[0]

            if stem:
                if self.model.get('morphology',1) in (1,2) and self.stemmer != None:
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
        if self.model.get('writing_system',1) in (1,2) and tmp[0] in self.model.get('numerals',()): return True
        if self.model.get('writing_system',1) == 3 and tmp in self.model.get('numerals',()): return True
        return False


    def _basic_tag(self, **args):
        """ Add basic tags to tokens and handle calculating linguistic stats """

        meta = args.get('meta', False)

        quot = False

        # Basic single-word tagging
        for i,tok in enumerate(self.tokens):

            stop = False
            t = tok['raw']
            tok['tags'] = set(tok['tags'])

            # Marks beginning or ending of a sentence?
            if t in self.model.get('sent_end',()):
                tok['tags'].add('SE')
                self.stats['sent_count'] = self.stats.get('sent_count',0) + 1
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
                    self.stats['word_count'] = self.stats.get('word_count',0) + 1


            # Is a numeral?
            if not stop and self._isnum(t):
                stop = True
                if not meta:
                    self.stats['numerals_count'] = self.stats.get('numerals_count',0) + 1
                tok['tags'].add('NUM')
        

            if not stop:
                # Is its case significant?
                tok_l = len(tok['raw'])
                if tok['case'] != 0 and self.model.get('bicameral',1) in (1,2):
                    if not meta:
                        self.stats['caps_count'] = self.stats.get('caps_count',0) + 1
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
                        self.stats['com_word_count'] = self.stats.get('com_word_count',0) + 1
                # Is it a common word?
                elif tok['lc'] in self.model.get('commons',()) or tok['stem_lc'] in self.model.get('commons_stemmed',()):
                    tok['tags'].add('COMM')
                    if not meta:
                        self.stats['com_word_count'] = self.stats.get('com_word_count',0) + 1
                else:
                    tok['tags'].add('UNCOMM')



                if self.model.get('writing_system',1) in (1,2):
                    # Count characters
                    tok['chars'] = tok_l
                    if not meta:
                        self.stats['char_count'] = self.stats.get('char_count',0) + tok['chars']
                    
                    # Count syllables and polysyllables
                    if self.model.get('pyphen','') != '':
                        syls_count = len(self.syls.inserted(t).split('-'))
                        if not meta:
                            self.stats['syl_count'] = self.stats.get('syl_count',0) + syls_count
                        if syls_count >= 3:
                            tok['tags'].add('POLYSYL')
                            if not meta:
                                self.stats['polysyl_count'] = self.stats.get('polysyl_count',0) + 1
    
                    tok['syls'] = syls_count
                        

                else: # ... for other writing systems there is no sense in calculating char number. Instead word count is used
                    tok['chars'] = 1
                    tok['syls'] = 1


            self.tokens[i] = tok









    def _dict_lookup(self, pos:int, dc:list, **args):
        """ Lookup tokens in a dictionary (structure given in sample model generators) """    
        match = True
        tag = None
        len = None
        stem = args.get('stem',False)

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









    def _advanced_tag(self, **args):
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

                (tag, len) = self._dict_lookup(i, self.d.get(dc, self.multi_dict.get(dc,())), stem=stem)
                if tag == None:
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


                    




    def _extract_patterns(self, field, **args):
        """ Feature extraction for learning by matching rule strings from language model against taggs of tokens """

        if self.debug:
            print(f'Extracting features from field {str(field)}...')

        self.regex_rule_str = ''

        # Default weight for field to adjust
        field_weight = slist(PREFIXES.get(field), 5, 1)
        meta = args.get('meta', slist(PREFIXES.get(field), 4, False))
        field_feat = args.get('field_feat', slist(PREFIXES.get(field), 7, []))

        if field_feat:
            prefix = slist(PREFIXES.get(field), 0, '..')
            field_name = f"""{slist(PREFIXES.get(field), 2, '')}: """
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

            if r.get('pattern','') == '' and not meta: continue

            if meta:
                matches = (self.regex_rule_str[1:],)
                rule_weight = field_weight
                rule_stem = True
                rule_case = False
                rule_strip = 0 
            else:
                matches = re.findall(r.get('pattern',''), self.regex_rule_str)
                rule_weight = r.get('weight',1)
                rule_stem = r['stem']
                rule_case = r['case']
                rule_strip = r['strip']

            if rule_stem: qtype = 4
            else: qtype = 5

            for m in matches:
                
                match_string = ''
                name = ''
                
                matches = m.split(' ')
                if rule_strip in (1,3): matches.pop(0)
                if rule_strip in (2,3): matches.pop()

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
                        
                    if t_str == None: t_str = self.tokens[word_no].get('lc',None)
                    if t_str == None: continue

                    if rule_case: match_string = f'{match_string} {prefix}.{t_str}'
                    else: match_string = f'{match_string} {prefix}{str(self.tokens[word_no].get("case",0))}{t_str}'

                    name += f' {self.tokens[word_no].get("raw",0)}'
        

                item = {}
                item['name'] = f'{field_name}{name.strip()}'
                item['string'] = f'{qtype}{match_string.strip()}'
                item['weight'] = rule_weight

                # Add to global feature dictionary
                if match_string.strip() != '':
                    self.features[item.get('string','')] = [0,0,'']
                    self.features[item.get('string','')][0] = self.features.get(item.get('string',''),[0,''])[0] +  ( item['weight'] * field_weight )
                    self.features[item.get('string','')][1] = qtype
                    self.features[item.get('string','')][2] = item.get('name','')







    def _prefix(self, field=-1, **args):
        """ Ascertain a prefix for a token based on field and case """
        if field in (None,-1):
            prefix = f"""T{args.get('wildcard','.')}"""
        else:
            prefix = PREFIXES.get(field,['',None,None,False,None])[0]

        # Add case wildcard to prefix if instructed to
        if args.get('case_ins',False):
            prefix = f'{prefix}{args.get("wildcard",".")}'
        else:
            prefix = f'{prefix}{str(args.get("case",0))}'

        return prefix




    def _case(self, t:str, **args):
        """ Check token's case and code it into (0,1,2)"""
        if self.model.get('writing_system',1) == 1:
                if t.islower():
                    case = 0
                elif t.isupper() and len(t) > 1:
                    case = 2
                elif t[0].isupper():
                    case = 1
                else:
                    case = 3

        elif self.model.get('writing_system',2) == 1:
            if t in self.model.get('capitals',[]):
                case = 1

        return case
        
        





    def _index_tokens(self):
        """ Construct strings of tokens to allow full text search by means of SQL """
        for t in self.tokens:

            pos_str = str(self.last_pos).zfill(7)
            self.last_pos += 1

            t = dict(t)
            t['tags'] = set(t['tags'])
            if t['tags'].intersection(self.model.get('no_index',{'PUNCT'})) != set():
                self.raw_token_str = f'{self.raw_token_str} {pos_str}{t["prefix"]}{t["case"]}{t["lc"]}'
                continue
            elif t['tags'].intersection(self.model.get('dividers',set())) != set():
                self.raw_token_str = f'{self.raw_token_str} {pos_str}{t["prefix"]}0{t["raw"]}'
                self.token_str = f'{self.token_str}   '
            else:
                self.token_str = f'{self.token_str} {pos_str}{t["token"]}'
                self.raw_token_str = f'{self.raw_token_str} {pos_str}{t["prefix"]}{t["case"]}{t["lc"]}'


                




    def process(self, string:str, field:int, **args):
        """ Process a single field """

        self.token_str = f'{self.token_str}   '

        stem = args.get('stem', slist(PREFIXES.get(field,[]), 3, False)) # Should field's tokens be stemmed?
        meta = args.get('meta', slist(PREFIXES.get(field,[]), 4, False)) # ... or maybe they are meta information?
        ignore = args.get('ignore', slist(PREFIXES.get(field,[]), 6, [])) 
        field_feat = args.get('field_feat', slist(PREFIXES.get(field,[]), 8, [])) # ... or every token in this field contains valuable data?

        learn = args.get('learn',False)
        index = args.get('index',True)

        # Tokenize
        self.tokenize(string, field, split=False, query=False, stem=stem, ignore=ignore, field_feat=field_feat)
        self._basic_tag(meta=meta)
        # .. and push on ...
        if learn:
            self._advanced_tag()
            self._extract_patterns(field)
        if index:
            self._index_tokens()







    def process_fields(self, fields:list, **args):
        """ Proces fields given in a list from Feedex's main class """
        learn = args.get('learn',False)
        index = args.get('index',True)
        stats = args.get('stats',True)

        self.fields = fields

        # This method is a de-facto entry processor, so language will be set-up for the whole thing
        self.set_model(self.fields[1])

        # Nullify all present statistics, strings and lists
        self.tokens = [] # List of tokens for further processing
        self.token_str = ''
        self.raw_token_str = ''
        self.last_pos = 0

        self.features = {}
        self.stats = {}


        # process fields
        for i, field in enumerate(self.fields):
            if i >= 10:
                break
            field = scast(field, str, '')
            if field.replace(' ','') == '':
                continue

            self.process(field, i, learn=learn, index=index)

        #Pad token string end
        self.token_str = f'{self.token_str}   '
        self.raw_token_str = f'{self.raw_token_str}   '

        if self.debug:
            print(self.features)


        # Consolidate text stats
        if stats:
            self._calculate_stats()
        
            # Add readability to tokens for ML - maybe will be a good feature?
            if self.stats.get('readability') != None:
                self.token_str = self.token_str + '   MX' + scast(self.stats.get('readability_class',0), str, 0) + ' '







    def _calculate_stats(self):
        """ Calculates document's statistics """
        if self.model.get('writing_system',1) == 0:
            self.stats['polysyl_count'] = 0

        # Calculate complexities
        self._readability()

        # Calculate document weight (smaller with word count adjusted by uncommon words)
        arg = self.stats.get('word_count',1) - (self.stats.get('word_count',1)-self.stats.get('com_word_count',0))
        self.stats['weight'] = 1/dezeroe(arg,1)

                



    def _readability(self):
        """ Calculates crude readability statistics """ 
        if self.stats.get('sent_count',0) == 0:
            self.stats['sent_count'] = 1
            
        if self.stats.get('word_count',0) == 0:
            return 0

        
        common_freq = self.stats.get('com_word_count',0)/self.stats.get('word_count',1)
        long_freq = self.stats.get('polysyl_count',0)/self.stats.get('word_count',1)

        avg_word_len = self.stats.get('char_count',0)/self.stats.get('word_count',1)
        avg_sent_len = self.stats.get('word_count',0)/self.stats.get('sent_count',1)

        if self.model.get("logographic",False):
            readability = common_freq * 1.25   +  1/avg_sent_len * 0.7
        else:
            readability = common_freq * 1    +       long_freq * 0.25        +       1/avg_word_len * 0.50   +       1/avg_sent_len * 0.25                             


        self.stats['readability'] = readability * 100

        if readability >= 0 and readability <= 60:
            self.stats['readability_class'] = 3
        elif readability >= 61 and readability <= 80:
            self.stats['readability_class'] = 2
        elif readability >= 81:
            self.stats['readability_class'] = 1
    
        
    



    def detect_lang(self):
        """ Detects language from loaded fields by various methods and constructs probability distribution """

        if self.debug:
            print("Language not provided. Running detection...")

        if self.charset != None:
            charset = self.charset.lower()
        else:
            charset = 'utf-8'

        lang_table = []
        
        # First, eliminate irrelevant charsets
        if charset == 'utf-8':
            lang_table = self.models.keys()
        else:
            for l in self.models.keys():         
                for ch in self.models[l].get('charsets',['utf-8']):
                    if charset in ch.lower():
                        lang_table.append(l)

        # ... and return lang if only one remained
        if len(lang_table) == 1:
            return lang_table[0]

        # .. else tokenize and get unique characters of text
        tokens = []
        for t in self.fields:
            if PREFIXES.get("i",[None,None,None,None])[3] == False:
                continue                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                
            tokens = tokens + re.findall(r"[\w]+",scast(t, str, ''))

        tokens = set(tokens)

        if len(tokens) <= 3:
            return 'heuristic'


        chars = ''
        for t in tokens:
            chars = chars + t
        chars = set(chars)

        # Construct language freq distribution dictionary
        langs = {}
        for l in lang_table:
            langs[l] = 0
            

        # And analyze one by one with stoplists, swadesh/common lists and unique characters
        for l in langs.keys():

            if l == 'heuristic':
                continue

            if not self.models[l].get('logographic',False):
                
                for t in tokens:
                    t = t.lower()
                    if t in self.models[l].get('stops',[]):
                        langs[l] = langs[l] + 1
                    
                    if t in self.models[l].get('swadesh',[]):
                        langs[l] = langs[l]+ 1

                    if t in self.models[l].get('commons',[]):
                        langs[l] = langs[l]+ 1


                for c in chars:
                    c = c.lower()
                    if c in self.models[l].get('unique_chars',''):
                        langs[l] = langs[l] + 10  #This is a big deal, so it is weighted quite highly


            else:
        
                for c in chars:
                    c = c.lower()

                    if c in self.models[l].get('stops',[]):
                        langs[l] = langs[l]+ 1

                    if c in self.models[l].get('swadesh',[]):
                        langs[l] = langs[l]+ 1

                    if c in self.models[l].get('commons',[]):
                        langs[l] = langs[l]+ 1

        if self.debug:
            print("Distribution: ", langs)

        if langs == {}:
            maximum = 'heuristic'
        else:
            maximum = max(langs, key=langs.get)

        return(maximum)









