# -*- coding: utf-8 -*-
""" Functions for displaying data in CLI for Feedex """


from feedex_headers import *







def table_print(columns:list, table, delim, **args):
    """ Clean printing of a given table (list of lists) given delimiter, truncation etc.
        Output can be filtered by mask (displayed column list) """


    output = args.get('output','cli')

    if output == 'json':
        json_string = json.dumps(table)
        print(json_string)
        return json_string

    number_footnote = args.get('number_footnote','results')
    sdelim = f" {delim} "
    sdelim2 = f" {args.get('delim2',';')} "
    delim_escape = scast(args.get('delim_escape'), str, '')
    if delim_escape != '': delim_escape = f'{delim_escape}{delim}'

    trunc = args.get('truncate',0)
    mask = args.get('mask',columns)

    # Colored columns
    ccol1 = args.get('ccol1', -1)
    ccol2 = args.get('ccol2', -1)
    ccol3 = args.get('ccol3', -1)
    # Threshold for coloring
    ccol1_thr = args.get('ccol1_thr',1)
    ccol2_thr = args.get('ccol2_thr', 0)
    ccol3_thr = args.get('ccol3_thr',1)
    # Date column - for nice formatting short dates
    date_col = args.get('date_col',-1)
    if date_col != -1:
        today = date.today()
        yesterday = today - timedelta(days=1)
        year = today.strftime("%Y")
        year = f'{year}.'
        today = today.strftime("%Y.%m.%d")
        yesterday = yesterday.strftime("%Y.%m.%d")


    # Print header with columns
    string = ''
    for i in mask:
        if type(i) == int:
            string = f'{string}{scast(columns[i], str, "").replace(delim,delim_escape)}{sdelim}'
        else:
            string = f'{string}{scast(i, str, "").replace(delim,delim_escape)}{sdelim}'
    print(string)

    if output == 'cli':
        print("\n----------------------------------------------------------------------------------------------------------------------------------------------------------------------------")

    # If entries are empty, then inform
    if table == [] or table == None:
        print("<<< EMPTY >>>")
        

    # ... and finally, entry list
    for entry in table:
        string = ''
        # Set text colors
        if output in ('cli', 'cli_noline'):
            cs_beg=TERM_NORMAL
            cs_end=TERM_NORMAL
            if ccol1 != -1:
                if scast(slist(entry, ccol1, 0), float,0) >= scast(ccol1_thr, float, 1):
                    cs_end = TERM_NORMAL
                    cs_beg = TERM_FLAG
            if ccol2 != -1:
                if scast(slist(entry, ccol2, 0), float, 0) >= scast(ccol2_thr, float, 1):
                    cs_end = TERM_NORMAL
                    cs_beg = TERM_READ
            if ccol3 != -1:
                if scast(slist(entry, ccol3, 0), float, 0) >= scast(ccol3_thr, float, 1):
                    cs_end = TERM_NORMAL
                    cs_beg = TERM_DELETED

        else:
            cs_beg = ''
            cs_end = ''

        for i in mask:
            sdate = False
            if type(i) != int:
                tix = columns.index(i)
                text = slist(entry, tix, '')
                if tix == date_col:
                    sdate = True
            else:
                text = slist(entry,i,'')
                if date_col != -1 and i == date_col:
                    sdate = True

            if type(text) in (float, int):
                text = scast( round(text,4), str, '<<NUM?>>')

            elif type(text) in (list, tuple):
                field_str = ''
                for s in text:
                    if type(s) == str:
                        field_str = f'{field_str}{sdelim2}{s}'
                    elif type(s) in (list, tuple) and len(s) == 3:
                        if output  in ('cli', 'cli_noline'):
                            field_str = f'{field_str}{sdelim2}{s[0]}{TERM_SNIPPET_HIGHLIGHT}{s[1]}{cs_beg}{s[2]}'
                        else:
                            field_str = f'{field_str}{sdelim2}{s[0]}{BOLD_MARKUP_BEG}{s[1]}{BOLD_MARKUP_END}{s[2]}'

                if field_str.startswith(sdelim2):
                    field_str = field_str.replace(sdelim2,'',1)

                text = field_str

            elif text == None:
                if output in ('cli', 'cli_noline'): 
                    text = 'N\A'
                else: text = ''
            else:
                text = scast(text, str, '')
                if output in ('cli', 'cli_noline'):
                    if sdate:
                        text = text.replace(today, 'Today')
                        text = text.replace(yesterday, 'Yesterday')
                        text = text.replace(year,'')

                    text = text.replace(BOLD_MARKUP_BEG, TERM_SNIPPET_HIGHLIGHT).replace(BOLD_MARKUP_END, cs_beg)

            field = text
            
            # Truncate if needed
            if trunc > 0:
                field = (field[:trunc] + '...') if len(field) > trunc else field
                field = field.replace("\n",' ').replace("\r",' ').replace("\t",' ')
                field = f"{field}{cs_beg}"

            # Delimiter needs to be stripped or escaped (for csv printing etc.)
            string = f"{string}{field.replace(delim,delim_escape)}{sdelim}"

        
        print(f"{cs_beg}{string}{cs_end}")
        if output == 'cli':
            print("\n----------------------------------------------------------------------------------------------------------------------------------------------------------------------------")

    if output  in ('cli', 'cli_noline'):
        print(f'{len(table)} {number_footnote}')







def cli_plot(data_points, max, term_width):
    """ Plots a dataset in a terminal """
    unit = dezeroe(max,1)/term_width

    for dp in data_points:
        x = dp[0]
        y = dp[1]
        length = int(y/unit)
        points = ""
        for l in range(length):
            points += "*"
                
        print(x, "|", points, " ", y)








def entry_print(lentry:list, lrules:list):
    """ Displays entry given in a list """
    
    entry = SQLContainer('entries', RESULTS_SQL_TABLE)
    entry.populate(lentry)
    if entry['id'] == None:
        print("Entry does not exist!")
        return -1

    string=f"""
Feed or Category (feed_id): {entry['feed_name_id']}  
----------------------------------------------------------------------------------------------------------
Title:  {entry['title']}
----------------------------------------------------------------------------------------------------------
Descripton (desc):     {entry['desc']}
----------------------------------------------------------------------------------------------------------
Text: {entry['text']}
----------------------------------------------------------------------------------------------------------
Links and enclosures:
{entry['links']}
{entry['enclosures']}
Images:
{entry['images']}
Comments:       {entry['comments']}
----------------------------------------------------------------------------------------------------------
Category:       {entry['category']}
Tags:           {entry['tags']}
Author:         {entry['author']} (contact: {entry['author_contact']})
Publisher:      {entry['publisher']} (contact: {entry['publisher_contact']})
Contributors:   {entry['contributors']}
Published:      {entry['pubdate_r']}    Added:  {entry['adddate_str']}
----------------------------------------------------------------------------------------------------------
ID:             {entry['id']}
Language (lang):       {entry['lang']}
Read? (read):   {entry['read']}
Flagged (flag):        {entry['flag']}
Deleted? (deleted):     {entry['deleted']}
-----------------------------------------------------------------------------------------------------------
Weight:         {entry['weight']}       Importance:     {entry['importance']}
    """
    print(string)
    if lrules != None and lrules != []:
        print("-------------------------------------------------------------------------------------------------------------------")
        print("Learned Keywords:\n")
        rule_str = ""
        for r in lrules:
            rule_str += slist(r,0,'') + ";  "
        print(rule_str, "\n\n")











def feed_print(lfeed:list, **args):
    """ Prints channel data given in a list """
    MAIN_TABLE=FEEDS_SQL_TABLE_PRINT + ("Category",)
    feed = SQLContainer('feeds', MAIN_TABLE)
    feed.populate(lfeed)

    output = args.get('output','cli')
    to_var = args.get('to_var',False)

    ostring = ''

    if feed['ID'] == None:
        print("Feed does not exist!")
    else:
        TABLE=FEEDS_SQL_TABLE + ('parent_id -> name',)
        for i,c in enumerate(feed.tuplify(all=True)):
            if output == 'cli' and not to_var:
                ostring = f'{ostring}\n---------------------------------------------------------------------------------------------------------------------------------------'
            ostring=f"""{ostring}\n{MAIN_TABLE[i]} ({TABLE[i]}):          {c}"""

        if not to_var: print(ostring)
        return ostring




def feed_name_cli(feed, **args):
    """ Sanitize feed name - coalesce name to ID"""
    name = coalesce(feed['name'],'')
    if name.strip() == '':
        name = coalesce(feed['title'],'')
        if name.strip() == '':
            name = coalesce(feed['url'],'')
            if name.strip() == '':
                name = scast(feed['id'], str, '<<ERROR>>')
    return name



def rule_name_cli(rule, **args):
    """ Sanitize rule name """
    name = coalesce(rule['name'],'')
    if name.strip() == '':
        name = coalesce(rule['string'],'')
        if name.strip() == '':
            name = scast(rule['id'], str, '<<ERROR>>')
        else:
            if len(name) > 75:
                name = name[:75] + ' ...'
    return name



def help_print(string:str, **args):
    """ Nice print for help messages - with bold etc. """
    string = string.replace('<b>','\033[1;37m')
    string = string.replace('</b>','\033[0m')
    string = string.replace('<i>','\033[1;91m')
    string = string.replace('</i>','\033[0m')

    print(string)
