# -*- coding: utf-8 -*-
""" Tools and utilities for Feedex """


from feedex_headers import *








def slist(lst, idx, default):
    """ Safely extract list element or give default """
    try: 
        return lst[idx]
    except (IndexError, TypeError, ValueError, KeyError) as e: 
        return default


def scast(value, target_type, default_value):
    """ Safely cast into a given type or give default value """
    try:
        if value is None:
            return default_value
        return target_type(value)
    except (ValueError, TypeError):
        return default_value

def nullif(val, nullifier):
    """ SQL's nullif counterpart for Python, returning None if val is in nullifier (list of str/int/float)"""
    if isinstance(nullifier, (list, tuple)):
        if val in nullifier: return None
    elif isinstance(nullifier, (str, int, float)):
        if val == nullifier: return None
    return val

def coalesce(val1, val2, **kargs):
    nulls = kargs.get('nulls',(None,))
    if val1 in nulls: return val2
    else: return val1


def dezeroe(num, default):
    """ Overwrite zero with default """
    if num == 0: return default
    else: return num


def ellipsize(string, length):
    """ Ellipsize a string for display """
    if len(string) > length: return f"{string[:length]}..."
    else: return string








def convert_timestamp(datestring:str, **kargs):
    """ This is needed to handle timestamps from updates, as it can be tricky at times and will derail the whole thing"""
    if isinstance(datestring, str):
        try:
            date_obj = dateutil.parser.parse(datestring, fuzzy_with_tokens=True)
            return int(date_obj[0].timestamp())
        except dateutil.parser.ParserError as e:
            cli_msg( (-1,f'{e}') )
            return None

    elif isinstance(datestring, int): return datestring
    else: return None






def sanitize_arg(arg, tp, default, **kargs):
    """ Sanitize and error check command line argument """

    if kargs.get('allow_none',False) and arg is None: return None

    exit_fail = kargs.get('exit_fail',True)
    is_file = kargs.get('is_file',False)
    is_dir = kargs.get('is_dir',False)
    stripped = kargs.get('stripped',False)
    valid_list = kargs.get('valid_list')
    singleton = kargs.get('singleton',False)
    arg_name = kargs.get('arg_name','NULL')
    err_code = kargs.get('err_code',9)

    if not singleton:
        arg_list = arg.split('=',1)
        arg_name = slist(arg_list, 0, default)
        arg_val = slist(arg_list, 1, None)
    else:
        arg_val = arg


    if arg_val is None:
        cli_msg( (-1, "Empty argument (%a)", arg_name ) )
        end_val = None
        if exit_fail:
            sys.exit(err_code)
    else:
        end_val = scast(arg_val, tp, None)

    arg_name_str = scast(arg_name, str, '')
    end_val_str = scast(end_val, str, '')

    if end_val is None:
        cli_msg( (-1, "Invalid argument type (%a)", arg_name_str ) )
        if exit_fail: sys.exit(err_code)

    if (stripped or is_file or is_dir) and tp == str:
        end_val = end_val.strip()

    if is_file and not os.path.isfile(end_val):
        cli_msg( (-1,f"File not found ({arg_name_str}, {end_val_str})") )
        end_val = None
        if exit_fail: sys.exit(err_code)


    if is_dir and not os.path.isdir(end_val):
        cli_msg( (-1, f"Directory not found ({arg_name_str}, {end_val_str})") )
        end_val = None
        if exit_fail: sys.exit(err_code)


    if not (valid_list is None):
        if end_val not in valid_list:
            cli_msg( (-1, f"Invalid argument value ({arg_name_str}, {end_val_str})") )
            if exit_fail: sys.exit(err_code)
            else: end_val = None

    if end_val is None and not (default is None):
        cli_msg( (-1, f"Defaulting to %a", scast(default, str, '<NONE>')) )
        end_val = default

    return end_val







def parse_config(cfile:str, **kargs):
    """ Parse configuration from a given file and return it to dict """

    config = {}
    config_str = kargs.get('config_str')

    if config_str is None:
        try:        
            with open(cfile, 'r') as f:
                lines = f.readlines()
        except OSError as e:
            cli_msg( (-1, f'Error reading %a: {e}', cfile) )
            return -1

    else:
        lines = config_str.splitlines()

    for l in lines:
        l = l.strip()
        if l == '': continue
        if l.startswith('#'): continue
        if '=' not in l: continue
        
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
            value = scast(value, int, 0)
        elif not (vfloat is None):
            value = vfloat
        elif value in ('True','true','Yes','yes','YES'):
            value = True
        elif value in ('False','false','No','no','NO'):
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
    for c, val in config.items(): base_config[c] = val

    contents = ''
    for c, val in base_config.items():
        opt = c
        if val in (None,''): val = ''
        elif val is True: val = 'True'
        elif val is False: val = 'False'
        else: val = scast(val, str, '')
        contents = f'{contents}\n{opt} = {val}'

    try:        
        with open(ofile, 'w') as f:
            f.write(contents)

        return contents
    except OSError as e:
        cli_msg( (-1, f'Error saving configuration to %a: {e}', ofile ) )
        return -1




def validate_config(config, **kargs):
    """ Validates config dictionary """
    msg = kargs.get('msg',False)
    new_config = config.copy()
    old_config = kargs.get('old_config',{}).copy()

    for k,v in config.items():
        
        if msg and v is None: continue

        v_int = scast(v, int, None)
        v_float = scast(v, float, None)
        v_str = scast(v, str, None)
        v_bool = scast(v, bool, None)

        if k in CONFIG_INTS_NZ:
            if v_int is None or v_int <= 0:
                if msg: return -1, f'%a must be integer > 0', CONFIG_NAMES.get(k)
                cli_msg( (-1, f'Invalid config option: %a; Defaulting to {DEFAULT_CONFIG[k]}', k) )
                new_config[k] = DEFAULT_CONFIG[k]
        if k in CONFIG_INTS_Z:
            if v_int is None or v_int < 0:
                if msg: return -1, f'%a must be integer >= 0', CONFIG_NAMES.get(k)
                cli_msg( (-1, f'Invalid config option: %a; Defaulting to {DEFAULT_CONFIG[k]}', k) )
                new_config[k] = DEFAULT_CONFIG[k]
        if k in CONFIG_BOOLS:
            if v_bool is None:
                if msg: return -1, f'%a must be True or False', CONFIG_NAMES.get(k)
                cli_msg( (-1, f'Invalid config option: %a; Defaulting to {DEFAULT_CONFIG[k]}', k) )
                new_config[k] = DEFAULT_CONFIG[k]
        if k in CONFIG_FLOATS:
            if v_float is None:
                if msg: return -1, f'%a must be a valid number', CONFIG_NAMES.get(k)
                cli_msg( (-1, f'Invalid config option: %a; Defaulting to {DEFAULT_CONFIG[k]}', k) )
                new_config[k] = DEFAULT_CONFIG[k]
        if k in CONFIG_STRINGS:
            if v_str is None:
                if msg: return -1, f'%a must be a valid string', CONFIG_NAMES.get(k)
                cli_msg( (-1, f'Invalid config option: %a; Defaulting to {DEFAULT_CONFIG[k]}', k) )
                new_config[k] = DEFAULT_CONFIG[k]
        if k in CONFIG_KEYS:
            if v_str is None or len(v) > 1:
                if msg: return -1, f'%a must be a single character ([a-zA-Z0-9])', CONFIG_NAMES.get(k)
                cli_msg( (-1, f'Invalid config option: %a; Defaulting to {DEFAULT_CONFIG[k]}', k) )
                new_config[k] = DEFAULT_CONFIG[k]

    
    if msg: 
        config['restart'] = False
        config['reload'] = False

        if not os.path.isfile(config.get('db_path')): return -1, f'Database file %a does not exist!', config.get('db_path')

        if old_config.get('db_path') != config.get('db_path'): config['restart'] = True

        if scast(old_config.get('use_keyword_learning'), bool, None) != scast( config.get('use_keyword_learning'), bool, None): config['reload'] = True
        if scast(old_config.get('rule_limit'), int, None) != scast(config.get('rule_limit'), int, None): config['reload'] = True

        return 0


    # ... CLI display and markup options ...
    if config.get('normal_color') is not None and config.get('normal_color') in TCOLS.keys():
        new_config['TERM_NORMAL'] = TCOLS[config.get('normal_color')]
    if config.get('flag_color') is not None and config.get('flag_color') in TCOLS.keys():
        new_config['TERM_FLAG'] = TCOLS[config.get('flag_color')]
    if config.get('read_color') is not None and config.get('read_color') in TCOLS.keys():
        new_config['TERM_READ'] = TCOLS[config.get('read_color')]
    if config.get('deleted_color') is not None and config.get('deleted_color') in TCOLS.keys():
        new_config['TERM_DELETED'] = TCOLS[config.get('deleted_color')]
    if config.get('bold_color') is not None and config.get('bold_color') in TCOLS.keys():
        new_config['TERM_SNIPPET_HIGHLIGHT'] = TCOLS[config.get('bold_color')]

    if config.get('bold_markup_beg') is not None and type(config.get('bold_markup_beg')) is str:
        BOLD_MARKUP_BEG = config.get('bold_markup_beg')
    if config.get('bold_markup_end') is not None and type(config.get('bold_markup_end')) is str:
        BOLD_MARKUP_END = config.get('bold_markup_end')

    return new_config



   








def check_paths(paths:list):
    """ Check if paths in a list exist and create them if not """
    for p in paths:
        if not os.path.isdir(p): os.makedirs(p)


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
    if type(string) is not str:
        return False
    matches = re.findall(URL_VALIDATE_RE, string)
    if matches not in (None, (), []): return True
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







def strip_markup(raw_text:str, **kargs):
    """ Detect and strip HTML from text
        Extract links to images and return both"""
    raw_text = scast(raw_text, str, None)
    if raw_text is None: return None


    # Determine content type (unless overridden)
    html = kargs.get('html',False)
    if not html:
        test = re.search(RSS_HANDLER_TEST_RE, raw_text)
        if test is None: html = False
        else: html = True

    if html:
        # Search for images
        images = re.findall(RSS_HANDLER_IMAGES_RE, raw_text)

        # Strips markup from text - a simple one for speed and convenience
        # Handle tags...
        raw_text = raw_text.replace("\n\r",' ')
        raw_text = raw_text.replace("\n",' ')
        raw_text = raw_text.replace("\r",' ')
        raw_text = raw_text.replace("</p>","\n\n")
        raw_text = raw_text.replace("<br>","\n")
        raw_text = raw_text.replace("<br />","\n")
        raw_text = raw_text.replace("<br/>","\n")
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




def load_json(infile, default):
    """ Loads JSON file and returns default if failed  """
    if not os.path.isfile(infile): return default
    out = default
    try:
        with open(infile, 'r') as f:
            out = json.load(f)
    except (OSError, JSONDecodeError) as e:
        cli_msg( (-1, f'Error reading from %a: {e}', infile ) )
        return default
    return out


def save_json(ofile:str, data):
    """ Saves GUI attrs into text file """
    try:
        with open(ofile, 'w') as f:
            json.dump(data, f)
    except (OSError, JSONDecodeError) as e:
        cli_msg( (-1, f'Error writing to %a: {e}', ofile) )
        return -1
    return 0



def ext_open(config, command_id, main_arg, **kargs):
    """ Wrapper for executing external commands """
    background = kargs.get('bakcground',True)
    if kargs.get('file',False):
        if not os.path.isfile(main_arg): return -1, 'File %a not found!', main_arg

    if command_id == 'search_engine':
        command_id = 'browser'
        main_arg = config.get('search_engine',DEFAULT_CONFIG.get('search_engine', main_arg)).replace('%Q', main_arg)

    command = scast( coalesce( nullif(config.get(command_id),''), FEEDEX_DEFAULT_BROWSER), str, '').split()
    for idx, arg in enumerate(command):
        arg_tmp = arg
        arg_tmp = arg_tmp.replace('%u', main_arg)
        arg_tmp = arg_tmp.replace('%U', main_arg)
        arg_tmp = arg_tmp.replace('%f', main_arg)
        arg_tmp = arg_tmp.replace('%F', main_arg)
        if kargs.get('title') is not None: arg_tmp = arg_tmp.replace('%t', scast(kargs.get('title'), str, '') )
        if kargs.get('alt') is not None: arg_tmp = arg_tmp.replace('%a', scast(kargs.get('alt'), str, '') )
        command[idx] = arg_tmp

    if kargs.get('debug') in (1,6): 
        print(' '.join(command))
        if background: print('Runing in background...')

    try:
        if background: subprocess.Popen(command)
        else: subprocess.run(command)
    except OSError as e: return -1, f'Error opening %a: {e}', main_arg

    return 0




def housekeeping(xdays:int, db_hash:str, **kargs):
    """ General housekeeping function """
    # Delete old files from cache
    debug = kargs.get('debug')
    now = int(datetime.now().timestamp())
    db_hash = f'{db_hash}_'
    if debug in (1,6): print(f'Housekeeping: {now}')
    for root, dirs, files in os.walk(FEEDEX_CACHE_PATH):
        for name in files:
            if not name.startswith(db_hash): continue
            filename = os.path.join(root, name)
            if os.stat(filename).st_mtime < now - (xdays * 86400):
                try: os.remove(filename)
                except OSError as e: cli_msg( (-1,f'Error removing %a: {e}', filename) )
                if debug in (1,6): print(f'Removed : {filename}')



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




def random_str(**kargs):
    """ Generates a random string with length=length for string=string 
        Assures that random sequence is not in original text
        Useful for escape sequences """
    l = kargs.get('length',15)
    string = kargs.get('string','')
    rand_str = ''
 
    while rand_str in string:
        for _ in range(l):
            rand_int = randint(97, 97 + 26 - 1)
            flip = randint(0, 1)
            rand_int = rand_int - 32 if flip == 1 else rand_int
            rand_str += (chr(rand_int))
    
    return rand_str





def to_csv(table, columns, mask, **kargs):
    """ Converts table data into CSV"""
    delim = kargs.get('delim','|')
    delim2 = kargs.get('delim',';')
    escape = kargs.get('escape',' ')

    csv_string = ''
    for i,c in enumerate(columns): 
        if columns[i] in mask:
            csv_string = f"{csv_string}{delim}{scast(c, str, '').replace(delim, escape)}"

    csv_string = csv_string[1:]

    for r in table:
        row = ''
        for i,c in enumerate(r): 
            if columns[i] in mask:
                if isinstance(c, (list,tuple)):
                    row1 = ''
                    for cc in c:
                        row1 = f'{row1}{delim2}{scast(cc[0], str, "").replace(delim2, escape)}{scast(cc[1], str, "").replace(delim2, escape)}{scast(cc[2], str, "").replace(delim2, escape)}'
                    row1 = row1[1:]
                    row = f'{row}{delim}{row1}'
                else: 
                    row = f'{row}{delim}{scast(c, str, "").replace(delim, escape)}'

        row = row.replace("\n","\t")
        csv_string = f"{csv_string}\n{row[1:]}"

    return csv_string





def help_print(string:str, **kargs):
    """ Nice print for help messages - with bold etc. """
    string = string.replace('<b>',f'{TERM_BOLD}')
    string = string.replace('</b>',f'{TERM_NORMAL}')
    string = string.replace('<i>',f'{TERM_FLAG}')
    string = string.replace('</i>',f'{TERM_NORMAL}')

    print(string)



def cli_msg(msg):
    """ Print nice CLI message """
    if type(msg) not in (tuple, list): 
        print(msg)
        return 0

    code = msg[0]
    if type(code) is str:
        print(code)
        return 0
    elif type(code) is not int: return -1
    
    text = scast( msg[1], str, '<???>')
    if len(msg) > 2: arg = scast( msg[2], str, '<???>')
    else: arg = None

    if code < 0:
        text = f'{TERM_ERR}{text}{TERM_NORMAL}'
        if arg is not None: arg = f'{TERM_ERR_BOLD}{arg}{TERM_ERR}'
    else:
        if arg is not None: arg = f'{TERM_BOLD}{arg}{TERM_NORMAL}'

    if arg is not None: text = text.replace('%a', arg)

    if code < 0: sys.stderr.write(text + "\n")
    else: print(text)

    return code