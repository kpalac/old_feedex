#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""Process dictionary for ling_processor Feedex
"""

import sys
sys.path.append('/usr/share/feedex/feedex')
from feedex_headers import *


if len(sys.argv) == 1: 
    print('No arguments given!')
    sys.exit(1)

action = 'display'
ifile = None
ofile = None
oformat = 'csv'
lang = None
dic = None
stem = False
tokenize = False
replace = False



for i,arg in enumerate(sys.argv):

    if arg in ('--help','-h'):
        print("""
Usage:

    dict_processor.py [--lang=STR] [--stem] [--tokenize] [--add|--remove|--summary|--csv]


        --lang          Language model for tokenizind and stemming
        --tokenize      Tokenize dictionary to be added
        --stem          Stem dictionary to be added




        --add   MAIN_FILE   FILE_TO_ADD   DICTIONARY  

                Add dictionary from FILE_TO_ADD to MAIN_FILE with name DICTIONARY
                
                MAIN_FILE - if exists, must be pickle with proper dictionary structure
                            if does not exist, it will be created as new language model dictionary
                
                FILE_TO_ADD - can be pickle or csv with dictionary list with structure:
                    
                    TOKEN(S) | PREFIX | LENGHT

                    TOKENS - tokens should be separated with ';' symbol
                    If not, they can be tokenized with --tokenize option
                    Tokens can also be stemmed with --stem option
                    All tokens are turned to lower case. To controll for case use 'caps_only' option or lookup in language model

                    PREFIX - prefix attached to token(s) if matched (used later by feature extraction rules)
                    LENGTH - How many tokens are in the TOKENS list? or:
                                If length is -1 - token ends with given TOKEN entry
                                If length is -2 - token begins with TOKEN entry
                                If length is -3 - token contains TOKEN entry
                                ( so it is a very basic implementation of morphology, useless with stemming, of course)

        --remove    MAIN_FILE   DICTIONARY

                Remove dictionary by name from MAIN_FILE


        --csv       MAIN_FILE   DICTIONARY

                Print a dictionary from MAIN_FILE as a proper language model CSV 


        """)
        sys.exit()      



    if arg.startswith('--lang='):
        lang = sanitize_arg(arg, str, None, stripped=False, exit_fail=True, allow_none=False, arg_name='Language to use')

    if arg == '--stem':
        stem=True
        continue

    if arg == '--tokenize':
        tokenize=True
        continue

    if arg == '--stem':
        stem=True
        continue

    if arg == '--summary':
        action = 'summary'
        argument = sanitize_arg(slist(sys.argv, i+1, None), str, None, singleton=True, arg_name='File to summarize', exit_fail=True, allow_none=False, is_file=True)
        break
    
    if arg == '--csv':
        action = 'csv'
        argument = sanitize_arg(slist(sys.argv, i+1, None), str, None, singleton=True, arg_name='File to convert to CSV', exit_fail=True, allow_none=False, is_file=True)
        argument2 = sanitize_arg(slist(sys.argv, i+2, None), str, None, singleton=True, arg_name='dictionary name to extract', exit_fail=True, allow_none=False)    
        break

    if arg == '--add':
        action = 'add'
        argument = sanitize_arg(slist(sys.argv, i+1, None), str, None, singleton=True, arg_name='Target file', exit_fail=True, allow_none=False)
        argument2 = sanitize_arg(slist(sys.argv, i+2, None), str, None, singleton=True, arg_name='File with new data', exit_fail=True, allow_none=False, is_file=True)
        argument3 = sanitize_arg(slist(sys.argv, i+3, None), str, None, singleton=True, arg_name='Dictionary name', exit_fail=True, allow_none=False)
        break

    if arg == '--remove':
        action = 'remove'
        argument = sanitize_arg(slist(sys.argv, i+1, None), str, None, singleton=True, arg_name='Dictionary file', exit_fail=True, allow_none=False, is_file=True)
        argument2 = sanitize_arg(slist(sys.argv, i+2, None), str, None, singleton=True, arg_name='Name of Dictionary to remove', exit_fail=True, allow_none=False)    
        break





lingua = LingProcessor(config=DEFAULT_CONFIG, debug=False)
lingua.set_model(lang)



def get_format(ifile:str):
    """ Get file format from extension """
    if ifile.endswith('.csv') or ifile.endswith('.CSV'): return 'csv'
    elif ifile.endswith('.pkl') or ifile.endswith('.PKL') or ifile.endswith('.pickle') or ifile.endswith('.PICKLE'): return 'pickle'
    else: return None


def read_csv(ifile:str):
    """ Reads CSV file to list """
    with open(ifile, 'r') as f:
        lines = f.readlines()

    d = []
    for l in lines:
        if l.strip() == '': continue
        row = []
        fields = l.split('|')
        tok_len = 0
        for i,f in enumerate(fields):
            if i == 0:
                subcols = []
                subfields = f.split(';')
                if subfields[0] != f:
                    for sf in subfields:
                        if sf == '': continue
                        subcols.append(sf.lower())
                    row.append(subcols)
                    tok_len = len(subcols)
                else:
                    tok_len = 1
                    row.append((f.lower(),))
            elif i == 1:
                row.append(f)
            elif i == 2:
                l = int(f)
                if l > 0:
                    row.append(tok_len)
                else:
                    row.append(l)
            else:
                print('Invalid CSV structure!')
                sys.exit()
        d.append(row)
    return d




def listify_row(row:list):
    """ Converts row to editable list """
    row_tmp = []
    row_tmp.append(list(row[0]))
    row_tmp.append(row[1])
    row_tmp.append(row[2])
    return row_tmp

def tuplify_row(row:list):
    """ Converts row to editable list """
    try:
        row_tmp = []
        row_tmp.append(tuple(row[0]))
        row_tmp.append(row[1])
        row_tmp.append(row[2])
    except:
        print(f'Error: {row}')
        sys.exit(-7)
    return tuple(row_tmp)


def read_pickle(ifile:str):
    """ Convert data to lists """
    with open(ifile, 'rb') as f:
        d = pickle.load(f)
    if type(d) in (list,tuple):
        d_tmp = []
        for row in d:
            d_tmp.append(listify_row(row))
        return d_tmp
    
    elif type(d) == dict:
        dic_tmp = {}
        for dk in d.keys():
            d_tmp = []
            for row in d[dk]:
                d_tmp.append(listify_row(row))
            dic_tmp[dk] = d_tmp
        return dic_tmp

    return None



def dp_tokenize(dic:list):
    """Tokenizes dictionary list"""
    dic_tmp = []
    for row in dic:
        toks = row[0]
        if len(toks) > 1 and type(toks) != str:
            print('Data seems to be already tokenized or invalid!')
            sys.exit(-5)
        string = toks[0]        
        row_tmp = []
        tokens = lingua.tokenize(string, None, simple=True)
        row_tmp.append(tokens)
        length = len(tokens)
        row_tmp.append(row[1])
        if row[2] > 0:
            row_tmp.append(length)
        else:
            row_tmp.append(row[2])
        dic_tmp.append(row_tmp)
    return dic_tmp


def dp_stem(dic:list):
    """Stems dictionary list """
    dic_tmp = []
    for row in dic:
        tokens = row[0]
        row_tmp = []
        toks_tmp = []
        if type(tokens) not in (list,tuple):
            print("Can stem only token list! Invalid data!")
            sys.exit()
        for t in tokens:
            tok = lingua.stemmer.stemWord(t)
            toks_tmp.append(tok)
        
        row_tmp.append(toks_tmp)
        length = len(toks_tmp)
        row_tmp.append(row[1])
        if row[2] > 0:
            row_tmp.append(length)
        else:
            row_tmp.append(row[2])
        dic_tmp.append(row_tmp)
    return dic_tmp
   



def summary(data):
    """Summarize data"""
    if type(data) in (list,tuple):
        print('Single dictionary:')
        print(f'{len(data)} items')   
    elif type(data) == dict:
        print("Multiple dictionary:")
        for d in data.keys():
            print(f'\nDictionary: {d}')
            print(f'    {len(data[d])} items')
            print('Sample:')
            i = 0
            for it in data[d]:
                i += 1 
                print(it)
                if i >= 50: break

    else:
        print('Invalid data!')



def print_csv(data):
    """ Converts list to CSV """
    if type(data) not in (list,tuple):
        print('Must be a list!')
        return -1

    for row in data:
        row_str = ''
        for i,col in enumerate(row):
            if i == 0:
                col_str = ''
                for r in col:
                    col_str = f'{col_str};{r}'
                row_str = f'{row_str}|{col_str[1:]}'
            else:
                row_str = f'{row_str}|{col}'
        print(row_str[1:])





if action == 'summary':
    format = get_format(argument)
    if format == 'csv': data = read_csv(argument)
    elif format == 'pickle': data = read_pickle(argument)
    else:
        print('Format not recognized! Use extensions (csv or pkl)')
        sys.exit(-2)
    summary(data)


if action == 'csv':
    dic = argument2
    format = get_format(argument)
    if format == 'csv': data = read_csv(argument)
    elif format == 'pickle': data = read_pickle(argument)
    else:
        print('Format not recognized! Use extensions (csv or pkl)')
        sys.exit(-2)
    
    if dic == None: print_csv(data)
    else: print_csv(data[dic])



def tuplify(data):
    odict = {}
    for d in data.keys():
        tmp_list = []
        for row in data[d]:
            tmp_list.append(tuplify_row(row))
        odict[d] = tuple(tmp_list)
    return odict






if action == 'remove':
    format_main = get_format(argument)
    dic = argument2
    if format_main != 'pickle':
        print('Main file must be pickle!')
        sys.exit(-3)
    else:
        if os.path.isfile(argument):
            orig_data = read_pickle(argument)
        else:
            orig_data = {}
        if type(orig_data) != dict or orig_data == {}:
            print('Main file must be a dictionary pickle!')
            sys.exit(-3)

    final_data = orig_data.copy()
    final_data.pop(dic)

    with open(argument, 'wb') as f:
        pickle.dump(final_data,f)



    

if action == 'add':
    format_main = get_format(argument)
    format_add = get_format(argument2)
    dic = argument3

    if format_main != 'pickle':
        print('Main file must be pickle!')
        sys.exit(-3)
    else:
        if os.path.isfile(argument):
            orig_data = read_pickle(argument)
        else:
            orig_data = {}
        if type(orig_data) != dict:
            print('Main file must be a dictionary pickle!')
            sys.exit(-3)

    if format_add == 'csv': data = read_csv(argument2)
    elif format_add == 'pickle': data = read_pickle(argument2)
    else:
        print('Format not recognized! Use extensions (csv or pkl)')
        sys.exit(-2)

    if type(data) not in (list, tuple):
        print('Added data must be a list!')
        sys.exit(-5)

    if tokenize or stem:
        if lingua.get_model() == 'heuristic':
            print('Language model not found!')
            sys.exit(-6)

    if tokenize:
        data = dp_tokenize(data)
    if stem:
        data = dp_stem(data)

    final_data = orig_data.copy()
    final_data[dic] = data

    final_data = tuplify(final_data)

    with open(argument, 'wb') as f:
        pickle.dump(final_data,f)







