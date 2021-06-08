# -*- coding: utf-8 -*-
""" Tools and utilities for Feedex """




from feedex_headers import *









def srange(string:str, idx:int, l:int, sl:int, rng:int):
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





def posrange(pos:str, string:str, rng:int):
    """ Extracts snippet from raw tokens given a position list """    
    tokens = scast(string, str, '').split(' ')
    tl = len(tokens)

    phr_toks = []
    tok_pref = None
    for t in pos.split(' '):
        if t.replace(' ','') != '':
            phr_toks.append( scast(t[0:7], int, -1) )
            if tok_pref == None:
                tok_pref = t[7:9]

    phr_start = phr_toks[0]
    phr_stop = phr_toks[-1]
    
    sel_start = phr_start - rng
    if sel_start < 0:
        sel_start = 0
    if sel_start > 0:
        beg = '...'
    else:
        beg = ''

    sel_stop = phr_stop + rng
    if sel_stop > tl:
        sel_stop = tl
    if sel_stop < tl:
        end = '...'
    else:
        end = ''

    posns = range(sel_start, sel_stop, 1)

    scan_start = sel_start - 5
    if scan_start < 0:
        scan_start = 0
    scan_stop = sel_stop + 5
    if scan_stop > tl:
        scan_stop = tl
        
    bstring = f''
    estring = f''
    phrstring = ''
    for t in tokens[scan_start:scan_stop]:
        tpos = scast(t[0:7], int, -1)

        if tpos in posns:
            tpref = t[7:9]
            tok = t[10:]
            if t[9] == '0':
                tok = tok
            elif t[9] == '1':
                tok = tok.capitalize()
            else:
                tok=tok.upper()

            if tpos < phr_start:
                if tpref == tok_pref: bstring = f'{bstring} {tok}'
            elif tpos > phr_stop:
                if tpref == tok_pref: estring = f'{estring} {tok}'
            else:
                phrstring = f'{phrstring} {tok}'

    return f'{beg}{bstring}', f'{phrstring}', f'{estring}{end}'





def slist(lst, idx, default):
    """ Safely extract list element or give default """
    try:
        return lst[idx]
    except:
        return default


def scast(value, target_type, default_value):
    """ Safely cast into a given type or give default value """
    try:
        if value == None:
            return default_value
        return target_type(value)
    except (ValueError, TypeError):
        return default_value

def nullif(val, nullifier):
    """ SQL's nullif counterpart for Python, returning None if val is in nullifier (list of str/int/float)"""
    if type(nullifier) in (list, tuple):
        if val in nullifier:
            return None
    elif type(nullifier) in (str, int, float):
        if val == nullifier:
            return None
    return val

def coalesce(val1, val2, **args):
    nulls = args.get('nulls',(None,))
    if val1 in nulls: return val2
    else: return val1

def convert_timestamp(datestring:str):
    """ This is needed to handle timestamps from updates, as it can be tricky at times and will derail the whole thing"""
    if datestring == 0:
        return int(datetime.now().timestamp()) 

    date_dict = dateutil.parser.parse(datestring, fuzzy_with_tokens=True)
    return int(date_dict[0].timestamp())


def dezeroe(num, default):
    """ Overwrite zero with default """
    if num == 0: return default
    else: return num



def binarify(cond:bool):
    """ Simple convert Bool to int (redundant)"""
    if cond == None:
        return None
    if cond:
        return 1
    if not cond:
        return 0

    if cond == 0:
        return 0
    else:
        return 1





def sanitize_arg(arg, tp, default, **args):
    """ Sanitize and error check command line argument """

    if args.get('allow_none',False) and arg == None:
        return None

    exit_fail = args.get('exit_fail',True)
    is_file = args.get('is_file',False)
    is_dir = args.get('is_dir',False)
    stripped = args.get('stripped',False)
    valid_list = args.get('valid_list')
    singleton = args.get('singleton',False)
    arg_name = args.get('arg_name','NULL')
    err_code = args.get('err_code',1)

    if not singleton:
        arg_list = arg.split('=',1)
        arg_name = slist(arg_list, 0, default)
        arg_val = slist(arg_list, 1, None)
    else:
        arg_val = arg


    if arg_val == None:
        sys.stderr.write(f"Empty argument ({arg_name})\n")
        end_val = None
        if exit_fail:
            sys.exit(err_code)
    else:
        end_val = scast(arg_val, tp, None)

    arg_name_str = scast(arg_name, str, '')
    end_val_str = scast(end_val, str, '')

    if end_val == None:
        sys.stderr.write(f"Invalid argument type ({arg_name_str})\n")
        if exit_fail:
            sys.exit(err_code)

    if (stripped or is_file or is_dir) and tp == str:
        end_val = end_val.strip()

    if is_file and not os.path.isfile(end_val):
        sys.stderr.write(f"File not found ({arg_name_str}, {end_val_str})\n")    
        end_val = None
        if exit_fail:
            sys.exit(err_code)


    if is_dir and not os.path.isdir(end_val):
        sys.stderr.write(f"Directory not found ({arg_name_str}, {end_val_str})\n")    
        end_val = None
        if exit_fail:
            sys.exit(err_code)


    if valid_list != None:
        if end_val not in valid_list:
            sys.stderr.write(f"Invalid argument value ({arg_name_str}, {end_val_str})\n")
            if exit_fail:
                sys.exit(err_code)
            else:
                end_val = None

    if end_val == None and default != None:
        sys.stderr.write(f"Defaulting to { scast(default, str, '<<NULL>>')}\n")
        end_val = default

    return end_val







def parse_config(cfile:str, **args):
    """ Parse configuration from a given file and return it to dict """

    config = {}

    config_str = args.get('config_str')

    if config_str == None:
        if not os.path.isfile(cfile):
            sys.stderr.write(f"Configuration file {cfile} not found!")
            return {}
        cfl = open(cfile, 'r') 
        lines = cfl.readlines()
        cfl.close()

    else:
        lines = config_str.splitlines()

    for l in lines:
        l = l.strip()
        if l == '':
            continue
        if l.startswith('#'):
            continue
        if '=' not in l:
            continue
        
        #fields = l.split('#',1)[0]
        fields = l.split('=',1)

        option = scast(slist(fields, 0, None), str, '').strip()
        if option == '':
            continue
        value = scast(slist(fields, 1, None), str, '').strip()
        if value == '':
            continue

        vfloat = scast(value, float, None)

        if value.isdigit():
            value = int(value)
        elif vfloat != None:
            value = vfloat
        elif value in ('True','true','T','Yes','yes','YES','y','Y'):
            value = True
        elif value in ('False','false','F','No','no','NO','n','N'):
            value = False
        else:
            if value.startswith('"') and value.endswith('"'):
                value = value[1:]
                value = value[:-1]
                value = value.replace('\"','"')
            if value.startswith("'") and value.endswith("'"):
                value = value[1:]
                value = value[:-1]
                value = value.replace("'","")
            
            if "/" in value and "~" in value:
                value = value.replace('~',os.getenv('HOME'))
            
        config[option] = value

    return config




def save_config(config, ofile):
    """ Saves config dict to a file """
    base_config = parse_config(ofile)
    for c in config.keys():
        base_config[c] = config[c]

    contents = ''
    for c in base_config.keys():
        opt = c
        val = base_config[c]
        if val in (None,''): val = ''
        elif val == True: val = 'True'
        elif val == False: val = 'False'
        else: val = scast(val, str, '')
        contents = f'{contents}\n{opt} = {val}'

    try:        
        f = open(ofile, "w")
        f.write(contents)
        f.close()
        return contents
    except Exception as e:
        os.stderr.write(str(e))
        return -1



def check_paths(paths:list):
    """ Check if paths in a list exist and create them if not """
    for p in paths:
        if not os.path.isdir(p):
            os.makedirs(p)


def check_if_regex(string:str):
    """ Check if string is a valid REGEX """
    try:
        re.compile(string)
        is_valid = True
    except re.error:
        is_valid = False
    return is_valid





def check_url(string:str):
    """ Check if a string is a valid URL or IP """
    if type(string) != str:
        return False
    matches = re.findall(URL_VALIDATE_RE, string)
    if matches not in (None, (), []):
        return True
    matches = re.findall(URL_VALIDATE_RE, f'http://{string}')
    if matches not in (None, (), []):
        return True
    matches = re.findall(URL_VALIDATE_RE, f'https://{string}')
    if matches not in (None, (), []):
        return True
    matches = re.findall(IP4_VALIDATE_RE, string)
    if matches not in (None, (), []):
        return True
    matches = re.findall(IP6_VALIDATE_RE, string)
    if matches not in (None, (), []):
        return True

    return False







def strip_markup(raw_text:str, **args):
    """ Detect and strip HTML from text
        Extract links to images and return both"""
    raw_text = scast(raw_text, str, None)
    if raw_text == None:
        return None


    # Determine content type (unless overridden)
    html = args.get('html',False)
    if not html:
        test = re.search(RSS_HANDLER_TEST_RE, raw_text)
        if test == None: html = False
        else: html = True

    if html:
        # Search for images
        images = re.findall(RSS_HANDLER_IMAGES_RE, raw_text)

        # Strips markup from text - a simple one for speed and convenience
        # Handle tags...
        raw_text = raw_text.replace("\n",'')
        raw_text = raw_text.replace("\n\r",'')
        raw_text = raw_text.replace("</p>","\n\n")
        raw_text = raw_text.replace("<br>","\n")
        raw_text = raw_text.replace('<em>','»')
        raw_text = raw_text.replace('</em>','«')
        raw_text = raw_text.replace('<b>','»')
        raw_text = raw_text.replace('</b>','«')
        raw_text = raw_text.replace('<i>','»')
        raw_text = raw_text.replace('</i>','«')
        raw_text = raw_text.replace('<u>','»')
        raw_text = raw_text.replace('</u>','«')
        stripped_text = re.sub(RSS_HANDLER_STRIP_HTML_RE, '', scast(raw_text, str, ''))
        stripped_text = stripped_text.strip()

    else:
        stripped_text = raw_text
        images = ()

    # strip most popular HTML specials
    for ent in HTML_ENTITIES:
        stripped_text = stripped_text.replace(ent[0],ent[2])
        stripped_text = stripped_text.replace(ent[1],ent[2])

    return (stripped_text, images)






def parse_efile(ifile:str, **args):
    """ Parse input file/pipe input into list of dicts """
    marker = args.get('marker','->')
    pipe = args.get('pipe',False)

    contents = []    
    if pipe:
        for line in sys.stdin:
            contents.append(line)
    else:
        if not os.path.isfile(ifile):
            return -1

        with open(ifile, "r") as f:
            contents = f.readlines() 

    entry = {}
    entries = []
    # Analyse line by line
    curr_field = None 
    curr_content = ''    
    for ln in contents:

        l = ln.replace('\n','')
        l = l.replace('\r','')

        if l.startswith(f'{marker}entry:'):
            if curr_field != None:
                entry[curr_field] = curr_content.strip()
            curr_field = None
            curr_content = ''
            if entry != {}: entries.append(entry)
            entry = {}
            continue

        if l.startswith(f'{marker}'):
            field = l.replace(marker,'',1)
            field = slist(field.split(':'),0,None)
            if field == None:
                sys.stderr.write('Parsing error! Unknown field after marker')
                return -1
            else:
                if curr_field != None:
                    entry[curr_field] = curr_content.strip()
                curr_content = ''
                curr_field = field
                l = l.replace(f'{marker}{field}:','',1)

        curr_content = f"""{curr_content}\n{l}"""

    if curr_field != None:
        entry[curr_field] = curr_content.strip()
    entries.append(entry)

    entries_out = []
    entry_out = {}
    for e in entries:
        entry_out = {}
        for f in e.keys():
            if e[f].isdigit() or e[f].isdecimal():
                entry_out[f] = scast(e[f], int, None)
            elif e[f] in (f'{marker}NULL', f'{marker}null'):
                entry_out[f] = None
            elif e[f].replace('.','').isdecimal() or e[f].replace(',','').isdecimal():
                entry_out[f] = scast(e[f], float, None)
            else:
                entry_out[f] = e[f]
    
        entries_out.append(entry_out)

    return entries_out




def housekeeping(xdays, **args):
    """ General housekeeping function """
    # Delete old files from cache
    debug = args.get('debug',False)
    now = int(datetime.now().timestamp())
    if debug: print(f'Housekeeping: {now}')
    for root, dirs, files in os.walk(FEEDEX_CACHE_PATH):
        for name in files:
            filename = os.path.join(root, name)
            if os.stat(filename).st_mtime < now - (xdays * 86400):
                os.remove(filename)
                if debug: print(f'Removed : {filename}')



def check_version(db:str, app:str):
    """ Compare version numer strings """
    if db in (None, (None,), ''): return 1
    db_list = db.split('.')
    app_list = app.split('.')
    db_num = scast( slist(db_list, 0, 0), int, 0) * 100 + scast( slist(db_list, 1, 0), int, 0) * 10 + scast( slist(db_list, 2, 0), int, 0)
    app_num = scast( slist(app_list, 0, 0), int, 0) * 100 + scast( slist(app_list, 1, 0), int, 0) * 10 + scast( slist(app_list, 2, 0), int, 0)

    if db_num == app_num: return 0
    elif db_num < app_num: return 1
    else: return -1




def random_str(**args):
    """ Generates a random string with length=length for string=string 
        Assures that random sequence is not in original text
        Useful for escape sequences """
    l = args.get('length',15)
    string = args.get('string','')
    rand_str = ''
 
    while rand_str in string:
        for _ in range(l):
            rand_int = randint(97, 97 + 26 - 1)
            flip = randint(0, 1)
            rand_int = rand_int - 32 if flip == 1 else rand_int
            rand_str += (chr(rand_int))
    
    return rand_str






