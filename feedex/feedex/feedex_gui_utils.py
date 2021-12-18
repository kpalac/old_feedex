# -*- coding: utf-8 -*-
""" GUI classes for FEEDEX """

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GdkPixbuf, GObject, Gdk, Pango, GLib
import threading

from PIL import Image
from io import StringIO, BytesIO

from feedex_headers import *







FEEDEX_GUI_ATTR_CACHE = f'{FEEDEX_SHARED_PATH}/feedex_gui_cache.json'
FEEDEX_GUI_DEFAULT_SEARCH_FIELDS = {'rev': True, 'print': False,  
'field': None, 
'feed_or_cat' : None,
'today': True,
'qtype': 1,
'exact': False,
'group': 'daily', 
'lang': None,
'hadler': None
}

FEEDEX_GUI_VALID_KEYS='qwertyuiopasdfghjklzxcvbnmQWERTYUIOPASDFGHJKLZXCVBNM1234567890'









# Parameter dictionaries for mnemonics

JUSTIFY_DICT = {
'right': Gtk.Justification.RIGHT,
'center': Gtk.Justification.CENTER,
'left': Gtk.Justification.LEFT,
3: Gtk.Justification.RIGHT,
2: Gtk.Justification.CENTER,
1: Gtk.Justification.LEFT
}

ELLIPSIZE_DICT = {
None: Pango.EllipsizeMode.NONE,
'start': Pango.EllipsizeMode.START,
'middle': Pango.EllipsizeMode.MIDDLE,
'end': Pango.EllipsizeMode.END,
1: Pango.EllipsizeMode.START,
2: Pango.EllipsizeMode.MIDDLE,
3: Pango.EllipsizeMode.END
}





#####################################################################################
# GUI objects factories



def f_pack_page(fields:list):
    """ Wrapper for building page of lower notebook widget (preview result) """
    page = Gtk.ScrolledWindow()
    page.set_border_width(8)
    vbox = Gtk.Box()        
    vbox.set_orientation(Gtk.Orientation.VERTICAL)
    vbox.set_homogeneous(False) 
    for f in fields:
        vbox.pack_start(f, False, True, 5)
    page.add(vbox)
    return page




def f_label(text:str, **kargs):
    """ Build a label quickly """
    label = Gtk.Label()

    if kargs.get('markup',False): label.set_markup(coalesce(text,''))
    else: label.set_text(coalesce(text,''))

    label.set_justify( JUSTIFY_DICT.get(kargs.get('justify', 'left'), Gtk.Justification.LEFT))  
    label.xalign = kargs.get('xalign', 0)    
    
    label.set_selectable(kargs.get('selectable',False))
    label.set_line_wrap(kargs.get('wrap',True))
    label.set_ellipsize(ELLIPSIZE_DICT.get(kargs.get('ellipsize')))

    return label








def f_list_store(store):
    """ Create list store from given list or tuple """
    sample = store[-1]
    types = []

    sample_type = type(sample)
    if sample_type in (list, tuple):
        for f in sample:
            types.append(type(f))

    else:
        types = []
        types.append(sample_type)

    list_store = Gtk.ListStore()
    list_store.set_column_types(types)

    for r in store: list_store.append(r)

    return list_store



def f_dual_combo(store, **kargs):
    """ Construct dual combo from store """
    start_at = kargs.get('start_at')
    color = kargs.get('color', False)
    icon = kargs.get('icon',False)
    style = kargs.get('style',False)
    tooltip = kargs.get('tooltip')
    connect = kargs.get('connect')

    list_store = f_list_store(store)
    combo = Gtk.ComboBox.new_with_model(list_store)
 
    rend = Gtk.CellRendererText()
    if kargs.get('ellipsize', True): rend.props.ellipsize = Pango.EllipsizeMode.START
 
    combo.pack_start(rend, True)
    combo.add_attribute(rend, 'text', 1)
 
    if color: combo.add_attribute(rend, 'foreground', 2)
    elif style: combo.add_attribute(rend, 'weight', 2)

    if tooltip != None: combo.set_tooltip_markup(tooltip)

    if start_at != None:
        for ix, s in enumerate(store):
            if start_at == s[0]: 
                combo.set_active(ix)
                break
    else: combo.set_active(0)

    if connect != None: combo.connect('changed', connect)

    return combo



def f_time_combo(**kargs):
    """ Construct combo for time search filters """
    store = (
    ('last','Last Update'),
    ('last_hour','Last Hour'),
    ('today','Today'),
    ('last_week','Week'),
    ('last_month','Month'),
    ('last_quarter','Quarter'),
    ('last_year','Year'),
    ('choose_dates','Choose dates...'),
    )
    return f_dual_combo(store, **kargs)


def f_time_series_combo(**kargs):
    """ Construct combo for time series grouping """
    store = (
    ('monthly','Group Monthly'),
    ('daily','Group Daily'),
    ('hourly','Group Hourly'),
    )
    return f_dual_combo(store, **kargs)



def f_read_combo(**kargs):
    """ Constr. combo for read/unread search filters """
    store = (
    ('__dummy', 'Read and Unread'),
    ('read', 'Read'),
    ('unread', 'Unread')
    )
    return f_dual_combo(store, **kargs)



def f_flag_combo(config, **kargs):
    """ Constr. combo for flag choosers and search filters """
    if kargs.get('filters',True):
        store = (
        (None, "Flagged and Unflagged", None),
        ('no', "Unflagged", None),
        ('all_flags', "All Flags", None),
        ('1', config.get('gui_flag_1_name','Flag 1'), config.get('gui_flag_1_color')),
        ('2', config.get('gui_flag_2_name','Flag 2'), config.get('gui_flag_2_color')),
        ('3', config.get('gui_flag_3_name','Flag 3'), config.get('gui_flag_3_color')),
        ('4', config.get('gui_flag_4_name','Flag 4'), config.get('gui_flag_4_color')),
        ('5', config.get('gui_flag_5_name','Flag 5'), config.get('gui_flag_5_color'))
        )

    else:
        store = (
        (-1, "No Flag", None),
        (1, config.get('gui_flag_1_name','Flag 1'), config.get('gui_flag_1_color')),
        (2, config.get('gui_flag_2_name','Flag 2'), config.get('gui_flag_2_color')),
        (3, config.get('gui_flag_3_name','Flag 3'), config.get('gui_flag_3_color')),
        (4, config.get('gui_flag_4_name','Flag 4'), config.get('gui_flag_4_color')),
        (5, config.get('gui_flag_5_name','Flag 5'), config.get('gui_flag_5_color'))
        )
    kargs['color'] = True
    return f_dual_combo(store, **kargs)



def f_feed_combo(FX, **kargs):
    """ Builds Feed/Category store for combos. This action is often repeated """
    store = []
    feed = SQLContainer('feeds', FEEDS_SQL_TABLE)
    empty_label = kargs.get('empty_label' , '-- No Category --')

    if not kargs.get('no_empty',False):
        store.append((-1, empty_label, 400))

    if kargs.get('with_categories',True):
        for c in FX.feeds:
            feed.populate(c)
            if feed['is_category'] == 1 and feed['deleted'] != 1:
                store.append((feed['id'], feed_name_cli(feed), 700,))

    if kargs.get('with_feeds',False):
        for f in FX.feeds:
            feed.populate(f)
            if feed['is_category'] != 1 and feed['deleted'] != 1:
                store.append(  (feed['id'], feed_name_cli(feed), 400,)  )

    kargs['icons'] = True
    return f_dual_combo(store, **kargs)





def f_handler_combo(**kargs):
    """ Build standard handler combo """
    kargs['tooltip'] = kargs.get('tooltip', """Choose Channel's protocol handler:
<b>RSS</b> - use RSS protocol
<b>Local</b> - no downloads. Can be populated by scripts or command line
using <i>--add-entries</i>, <i>--add-entries-from-file</i>, <i>--add-entries-from-pipe</i> options
""")
    store = [
    ('rss', 'RSS'),
    #('twitter', 'Twitter')
    ]

    if kargs.get('local',False):
        store.append( ('local', 'Local') )
    if kargs.get('all', False):
        store.insert(0, (None, 'All handlers'))

    return f_dual_combo(store, **kargs)




def f_query_type_combo(**kargs):
    """ Construct combo for choice of query type for search or a rule"""

    if kargs.get('rule',False):
        store = ( (0,'String matching'), (1,'Normal query'), (2,'Exact query'), (3,'REGEX') )
        kargs['tooltip'] = kargs.get('tooltip',"""Set query type to match this rule:
<b>String matching</b>: simple string comparison
<b>Normal:</b> stemmed and tokenized
<b>Exact</b>: unstemmed and tokenized
<b>REGEX</b>: REGEX matching""")
    else:
        store = ( (1,'Normal query'), (2,'Exact query'), (0,'String matching') )
        kargs['tooltip'] = kargs.get('tooltip',"""Set query type:
<b>Normal:</b> stemmed and tokenized
<b>Exact</b>: unstemmed and tokenized
<b>String matching</b>: simple string comparison""")

    return f_dual_combo(store, **kargs)



def f_lang_combo(FX, **kargs):
    """ Build combo list of languages """

    kargs['tooltip'] = kargs.get('tooltip', 'Select language used fort query tokenizing and stemming')

    if kargs.get('with_all',True): store = [(None,"All Languages",)]
    else: store = []

    for l in FX.LP.models.keys():
        if l != 'heuristic':
            store.append( (l, l.upper()) )

    return f_dual_combo(store, **kargs)



def f_field_combo(**kargs):
    """ Build field combo """
    store = []
    store.append((-1, '-- All Fields --',))
    for f in PREFIXES.keys():
        if f != 0: store.append((f, PREFIXES[f][2]))
    print(store)
    return f_dual_combo(store, **kargs)




def f_combo_entry(store, **kargs):
    """ Builds an entry with history/options """
    tooltip = kargs.get('tooltip')
    tooltip_button = kargs.get('tooltip_button')
    connect = kargs.get('connect')
    connect_button = kargs.get('connect_button')

    combo = Gtk.ComboBox.new_with_entry()
    combo.set_entry_text_column(0)
    combo.set_model(store)

    entry = combo.get_child()
    entry.set_text(kargs.get('text',''))
    if connect != None: entry.connect('activate', connect)
    if tooltip != None: combo.set_tooltip_markup(tooltip)

    entry.set_icon_from_icon_name(1,'edit-clear-symbolic')
    if tooltip_button != None: entry.set_icon_tooltip_markup(1, tooltip_button)
    if connect_button != None: entry.connect('icon-press', connect_button)

    return combo, entry









def f_get_combo(combo, **kargs):
    """ Get current combo's ID value (assumed to be the first on the store list) """
    model = combo.get_model()
    active = combo.get_active()
    val = model[active][0]
    if type(val) == int:
        if val == kargs.get('null_val',-1): val = None
    return val



def f_set_combo(combo, val, **kargs):
    """ Set combo to a specified value """
    if val == None: val = kargs.get('null_val', -1)
    model = combo.get_model()
    for i,m in enumerate(model):
        if m[0] == val: 
            combo.set_active(i)
            return 0

    combo.set_active(0)
    return -1


def f_set_combo_from_bools(combo, dc, **kargs):
    """ Set combo given a dictionary (set if value is TRUE)"""
    for k in dc.keys():
        if type(dc[k]) == bool and dc[k] == True:
            found = f_set_combo(combo, k, **kargs)
            if found == 0: return 0
    return -1



def f_get_combo_id(combo, id):
    """ Get the combo's element with a given ID (assumed to be the first on the store list)"""
    model = combo.get_model()
    for i,m in enumerate(model):
        if m[0] == id: return i
    return 0             







def f_button(label:str, icon:str, **kargs):
    """ Construct a button :)"""
    if icon != None: 
        if label == None: button = Gtk.Button.new_from_icon_name( icon, kargs.get('size',Gtk.IconSize.BUTTON) )
        else:
            button = Gtk.Button()
            image = Gtk.Image.new_from_icon_name(icon, kargs.get('size', Gtk.IconSize.BUTTON) )
            image.show()
            text_label = Gtk.Label()
            text_label.set_text(label)
            box = Gtk.HBox()
            box.pack_start(image, False, False, 3)
            box.pack_start(text_label, False, False, 3)
            button.add(box)

    else: button = Gtk.Button.new_with_label(label)

    if kargs.get('tooltip') != None: button.set_tooltip_markup(kargs.get('tooltip',''))
    if kargs.get('connect') != None: button.connect('clicked', kargs.get('connect'))

    return button










def f_col(title:str, ctype:int,  model_col:int, **kargs):
    """ Wrapper for building a TreeVeiw column """
    color_col = kargs.get('color_col')
    attr_col = kargs.get('attr_col')
    ellipsize = kargs.get('ellipsize','end')
    clickable = kargs.get('clickable', True)
    sort_col = kargs.get('sort_col')
    start_width = kargs.get('start_width')
    width = kargs.get('width',16)
    name = kargs.get('name')

    if ctype in (0,1):
        renderer = Gtk.CellRendererText()
        if ctype == 0: col = Gtk.TreeViewColumn( title, renderer, text=model_col)
        elif ctype == 1: col = Gtk.TreeViewColumn( title, renderer, markup=model_col)

        if ellipsize != None: renderer.props.ellipsize = ELLIPSIZE_DICT.get(ellipsize)
        if attr_col != None:  col.add_attribute(renderer, 'weight', attr_col)    
        if color_col != None: col.add_attribute(renderer, 'foreground', color_col)    


    else:
        renderer = Gtk.CellRendererPixbuf()
        col = Gtk.TreeViewColumn( title, renderer, pixbuf=model_col)

    if clickable:
        col.set_clickable(True)
        if sort_col != None: col.set_sort_column_id(sort_col)    
        else: col.set_sort_column_id(model_col)
    else: col.set_clickable(False)

    col.set_resizable(kargs.get('resizeable',True))
    col.set_reorderable(kargs.get('reorderable',True))

    if width != None: col.set_min_width(width)
    if start_width != None: col.props.fixed_width = start_width
    if name != None: col.set_name(name)

    return col







def f_menu_item(item_type:int, label:str, connect, **kargs):
    """ Factory for building menu item """
    icon = kargs.get('icon')
    color = kargs.get('color')
    tooltip = kargs.get('tooltip')
    args = kargs.get('args',[])
    kwargs = kargs.get('kargs')

    if item_type == 0:
        item = Gtk.SeparatorMenuItem()
        return item

    if icon in (None,'') and color in (None,''):
        item = Gtk.MenuItem(label)
    else:
        item = Gtk.MenuItem()

    if color != None:
        lb = Gtk.Label()
        lb.set_markup(f'<span foreground="{color}">{label}</span>')
        vbox = Gtk.Box()
        vbox.set_orientation(Gtk.Orientation.HORIZONTAL)
        vbox.set_homogeneous(False)
        vbox.pack_start(lb, False, False, 3)
        item.add(vbox)


    elif icon != None:
        im = Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.MENU)     
        im.show()
        lb = Gtk.Label()
        lb.set_text(label)
        vbox = Gtk.Box()
        vbox.set_orientation(Gtk.Orientation.HORIZONTAL)
        vbox.set_homogeneous(False)
        vbox.pack_start(im, False, False, 3)
        vbox.pack_start(lb, False, False, 3)
        item.add(vbox)

    if item_type == 3:
        if connect != None: item.set_submenu(connect)
        
    elif connect != None:
        if kwargs != None: args.append(kwargs)
        item.connect('activate', connect, *args)

    if tooltip != None:
        item.set_tooltip_markup(tooltip)

    return item






####################################################################################################
# Utilities


def sanitize_snippet(snip:tuple):
    """ Sanitizes snippet string for output with Pango markup """
    if len(snip) == 3:
        beg = GObject.markup_escape_text(scast(snip[0], str, ''))
        phr = GObject.markup_escape_text(scast(snip[1], str, ''))
        end = GObject.markup_escape_text(scast(snip[2], str, ''))
        return f'{beg}<b>{phr}</b>{end}'
    else:
        return '--- ERROR ---'    


def res(string:str):
    """ Extracts elements and generates resource filename for cache """
    url = slist(re.findall(IM_URL_RE, string), 0, None)
    alt = slist(re.findall(IM_ALT_RE, string), 0, '')
    title = slist(re.findall(IM_TITLE_RE, string), 0, '')

    if url == None or url.startswith('http://feeds.feedburner.com'):
        return 0

    hash_obj = hashlib.sha1(url.encode())
    filename = f"""{FEEDEX_CACHE_PATH}/{hash_obj.hexdigest()}.img"""

    if title not in ('',None,()):
        alt = f"""<b>{title}</b>\n{alt}"""
    else:
        title = alt

    return {'url':url, 'alt':alt.strip(), 'filename':filename, 'title':title}






def download_res(url:str, filename:str, **kargs):
    """ Downloads a resource at URL and creates a cache file from hashed URL """
    headers = {'User-Agent' : 'UniversalFeedParser/5.0.1 +http://feedparser.org/'}
    try:
        req = urllib.request.Request(url, None, headers)
        response = urllib.request.urlopen(req)
        if response.status == 200:
            img_data = BytesIO(response.read())
            img = Image.open(img_data)
            if not kargs.get('no_thumbnail',False):
                img.thumbnail((150, 150))
            img.save(filename, format="PNG")
    except Exception as e:
        sys.stderr.write(f'Could not download image at {url}! ({e})')
        return -1


def image2pixbuf(im):
    """Convert Pillow image to GdkPixbuf"""
    data = im.tobytes()
    w, h = im.size
    data = GLib.Bytes.new(data)
    pix = GdkPixbuf.Pixbuf.new_from_bytes(data, GdkPixbuf.Colorspace.RGB,
            False, 8, w, h, w * 3)
    return pix




def get_icons(feeds, ficons):
    """ Sets up a dictionary with feed icon pixbufs for use in lists """
    icons = {}
    for f in ficons.keys():
        icons[f] = GdkPixbuf.Pixbuf.new_from_file_at_size(ficons[f], 16, 16)

    icons['default']  = GdkPixbuf.Pixbuf.new_from_file_at_size(f"{FEEDEX_SYS_ICON_PATH}/news-feed.svg", 16, 16)
    icons['main']  = GdkPixbuf.Pixbuf.new_from_file_at_size(f"{FEEDEX_SYS_ICON_PATH}/feedex.png", 64, 64)
    icons['tray_new']  = GdkPixbuf.Pixbuf.new_from_file_at_size(f"{FEEDEX_SYS_ICON_PATH}/tray_new.png", 64, 64)
    icons['doc'] = GdkPixbuf.Pixbuf.new_from_file_at_size(f"{FEEDEX_SYS_ICON_PATH}/document.svg", 16, 16)
    icons['ok'] = GdkPixbuf.Pixbuf.new_from_file_at_size(f"{FEEDEX_SYS_ICON_PATH}/ok.svg", 16, 16)
    icons['error'] = GdkPixbuf.Pixbuf.new_from_file_at_size(f"{FEEDEX_SYS_ICON_PATH}/error.svg", 16, 16)
    icons['trash'] = GdkPixbuf.Pixbuf.new_from_file_at_size(f"{FEEDEX_SYS_ICON_PATH}/trash.svg", 16, 16)
    icons['calendar'] = GdkPixbuf.Pixbuf.new_from_file_at_size(f"{FEEDEX_SYS_ICON_PATH}/calendar.svg", 16, 16)
    icons['new'] = GdkPixbuf.Pixbuf.new_from_file_at_size(f"{FEEDEX_SYS_ICON_PATH}/new.svg", 16, 16)
    icons['db'] = GdkPixbuf.Pixbuf.new_from_file_at_size(f"{FEEDEX_SYS_ICON_PATH}/db.svg", 64, 64)

    return icons



def parse_message(msg:list):
    """ Splits message tuple into a markup """
    if type(msg) == int:
        msg = (msg, None)

    if type(msg) in (tuple,list):
        lst =  MESSAGES.get(slist(msg, 0, -1), ('', False, False))
        text = slist(lst, 0, '').strip()
        text = text.replace('\n','')
        text = text.replace('\r','')
        text = GObject.markup_escape_text(text)
        arg = scast(slist(msg, 1, ''),str,'').strip()
        arg = arg.replace('\n','')
        arg = arg.replace('\r','')
        arg =  GObject.markup_escape_text(arg)
        error = slist(lst, 2, False)
    
        arg = f'<b>{arg}</b>'
            
        if '%a' in text:
            text = text.replace('%a',arg)
        elif arg not in ('','<b></b>'):
            text = f'{text} {arg}'

        if error:
            text = f'<span foreground="red">{text}</span>'

    elif type(msg) == str:
        text = msg
    else:
        text = ''

    return text




def humanize_date(string, today, yesterday, year):
    """ Format date to be more human readable and context dependent """
    date_short = string
    date_short = date_short.replace(today, "Today")
    date_short = date_short.replace(yesterday, "Yesterday")
    date_short = date_short.replace(year,'')
    return date_short







def feed_name(feed, **kargs):
    """ Sanitize feed name for GUI """
    return GObject.markup_escape_text(feed_name_cli(feed))

def rule_name(rule, **kargs):
    """ Sanitize rule name for GUI """
    return GObject.markup_escape_text(rule_name_cli(rule))

def entry_name(entry, **kargs):
    """ Sanitize feed name for GUI """
    return GObject.markup_escape_text( ellipsize(entry.get('title',''), 75) )









def validate_gui_attrs(gui_attrs):
    """ Validate GUI attributes in case the config file is not right ( to prevent crashing )"""
    new_gui_attrs = {}
    
    new_gui_attrs['win_width'] = scast(gui_attrs.get('win_width'), int, 1500)
    new_gui_attrs['win_height'] = scast(gui_attrs.get('win_height'), int, 800)
    new_gui_attrs['win_maximized'] = scast(gui_attrs.get('win_maximized'), bool, False)

    new_gui_attrs['div_horiz'] = scast(gui_attrs.get('div_horiz'), int, 400)
    new_gui_attrs['div_vert'] = scast(gui_attrs.get('div_vert'), int, 350)

    new_gui_attrs['feeds_expanded'] = scast(gui_attrs.get('feeds_expanded',{}).copy(), dict, {})

    for v in new_gui_attrs['feeds_expanded'].values():
        if type(v) != bool: 
            new_gui_attrs['feeds_expanded'] = {}
            break

    new_gui_attrs['results'] = scast(gui_attrs.get('results',{}).copy(), dict, {})
    for v in new_gui_attrs['results'].values():
        if type(v) != int: 
            new_gui_attrs['results'] = {}
            break


    new_gui_attrs['contexts'] = scast(gui_attrs.get('contexts',{}).copy(), dict, {})
    for v in new_gui_attrs['contexts'].values():
        if type(v) != int:
            new_gui_attrs['contexts'] = {}
            break

    new_gui_attrs['terms'] = scast(gui_attrs.get('terms',{}).copy(), dict, {})
    for v in new_gui_attrs['terms'].values():
        if type(v) != int: 
            new_gui_attrs['terms'] = {}
            break

    new_gui_attrs['time_series'] = scast(gui_attrs.get('time_series',{}).copy(), dict, {})
    for v in new_gui_attrs['time_series'].values():
        if type(v) != int: 
            new_gui_attrs['time_series'] = {}
            break

    new_gui_attrs['rules'] = scast(gui_attrs.get('rules',{}).copy(), dict, {})
    for v in new_gui_attrs['rules'].values():
        if type(v) != int: 
            new_gui_attrs['rules'] = {}
            break



    new_gui_attrs['results_order'] = scast(gui_attrs.get('results_order',()), tuple, ())
    for c in (25,4,3,5,7,8,9,10,12,14,15,16,17,18,19,6): 
        if c not in new_gui_attrs['results_order']:
                new_gui_attrs['results_order'] = (25,4,3,5,7,8,9,10,12,14,15,16,17,18,19,6)
                break

    new_gui_attrs['contexts_order'] = scast(gui_attrs.get('contexts_order', ()), tuple, ())
    for c in (3,15,4,5,7,9,10,11,12,13,14,6):
        if c not in new_gui_attrs['contexts_order']:
                new_gui_attrs['contexts_order'] = (3,15,4,5,7,9,10,11,12,13,14,6)
                break

    new_gui_attrs['terms_order'] = scast(gui_attrs.get('terms_order',(1,2,3)), tuple, ())
    for c in (1,2,3): 
        if c not in new_gui_attrs['terms_order']:
                new_gui_attrs['terms_order'] = (1,2,3)
                break

    new_gui_attrs['time_series_order'] = scast(gui_attrs.get('time_series_order',(1,2,3)), tuple, ())
    for c in (1,2,3): 
        if c not in new_gui_attrs['time_series_order']:
                new_gui_attrs['time_series_order'] = (1,2,3)
                break

    new_gui_attrs['rules_order'] = scast(gui_attrs.get('rules_order', (1,2,3,4,5,6,7,8,9)), tuple, ())
    for c in (1,2,3,4,5,6,7,8,9): 
        if c not in new_gui_attrs['rules_order']:
                new_gui_attrs['rules_order'] = (1,2,3,4,5,6,7,8,9)
                break

    
    new_gui_attrs['default_search_filters'] = scast(gui_attrs.get('default_search_filters',FEEDEX_GUI_DEFAULT_SEARCH_FIELDS).copy(), dict, {})
    gui_attrs['default_search_filters'] = scast(gui_attrs.get('default_search_filters',FEEDEX_GUI_DEFAULT_SEARCH_FIELDS).copy(), dict, {})


    if new_gui_attrs['default_search_filters'] != {}:

        new_gui_attrs['default_search_filters']['qtype'] = scast(gui_attrs['default_search_filters'].get('qtype'), int, 0)

        new_gui_attrs['default_search_filters']['field'] = scast(gui_attrs['default_search_filters'].get('field'), int, None)
    
        new_gui_attrs['default_search_filters']['feed_or_cat'] = scast(gui_attrs['default_search_filters'].get('feed_or_cat'), int, None)
    
        new_gui_attrs['default_search_filters']['exact'] = scast(gui_attrs['default_search_filters'].get('exact'), bool, False)
        new_gui_attrs['default_search_filters']['last'] = scast(gui_attrs['default_search_filters'].get('last'), bool, None)
        new_gui_attrs['default_search_filters']['last_hour'] = scast(gui_attrs['default_search_filters'].get('last_hour'), bool, None)
        new_gui_attrs['default_search_filters']['today'] = scast(gui_attrs['default_search_filters'].get('today'), bool, None)
        new_gui_attrs['default_search_filters']['last_week'] = scast(gui_attrs['default_search_filters'].get('last_week'), bool, None)
        new_gui_attrs['default_search_filters']['last_month'] = scast(gui_attrs['default_search_filters'].get('last_month'), bool, None)
        new_gui_attrs['default_search_filters']['last_quarter'] = scast(gui_attrs['default_search_filters'].get('last_quarter'), bool, None)
        new_gui_attrs['default_search_filters']['last_year'] = scast(gui_attrs['default_search_filters'].get('last_year'), bool, None)

        new_gui_attrs['default_search_filters']['group'] = scast(gui_attrs['default_search_filters'].get('group'), str, 'daily')

        new_gui_attrs['default_search_filters']['lang'] = scast(gui_attrs['default_search_filters'].get('lang'), str, None)
        new_gui_attrs['default_search_filters']['handler'] = scast(gui_attrs['default_search_filters'].get('handler'), str, None)

        new_gui_attrs['default_search_filters']['case_ins'] = scast(gui_attrs['default_search_filters'].get('case_ins'), bool, None)
        new_gui_attrs['default_search_filters']['case_sens'] = scast(gui_attrs['default_search_filters'].get('case_sens'), bool, None)

        new_gui_attrs['default_search_filters']['read'] = scast(gui_attrs['default_search_filters'].get('read'), bool, None)
        new_gui_attrs['default_search_filters']['unread'] = scast(gui_attrs['default_search_filters'].get('unread'), bool, None)

        new_gui_attrs['default_search_filters']['flag'] = scast(gui_attrs['default_search_filters'].get('flag'), str, None)


    return new_gui_attrs








from feedex_desktop_notifier import DesktopNotifier
from feedex_gui_dialogs import *
from feedex_gui_tabs import *
from feedex_gui_feeds import *


