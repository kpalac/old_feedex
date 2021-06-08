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
FLOAT_VALIDATE_RE = re.compile(r'[+-]?(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?')



HANDLER_CHOICE = (
('rss', 'RSS'),
#('twitter', 'Twitter - not supported yet'),
('local', 'Local')
)
HANDLER_CHOICE_NL = (
('rss', 'RSS'),
#('twitter', 'Twitter - not supported yet')
)
HANDLER_CHOICE_ALL = (
('-1','All Handlers'),
('rss','RSS'),
#(1, 'Twitter - not supported yet'),
('local','Local')
)

def handler_combo(active, **args):
    """ Build standard handler combo """
    tooltip = args.get('tooltip')
    if tooltip == None:
#        tooltip = """Choose Channel's protocol handler:
#<b>RSS</b> - use RSS protocol
#<b>Twitter</b> - download entries from Twitter using URL
#<b>Local</b> - no downloads. Can be populated by scripts or command line
#using --add-entries, --add-entries-from-file, --add-entries-from-pipe options
#"""
        tooltip = """Choose Channel's protocol handler:
<b>RSS</b> - use RSS protocol
<b>Local</b> - no downloads. Can be populated by scripts or command line
using <i>--add-entries</i>, <i>--add-entries-from-file</i>, <i>--add-entries-from-pipe</i> options
"""
    if args.get('no_local'): hc = fxcombo(None, HANDLER_CHOICE_NL, tooltip)
    elif args.get('with_all'): hc = fxcombo(None, HANDLER_CHOICE_ALL, tooltip)
    else: hc = fxcombo(None, HANDLER_CHOICE, tooltip)
    hc.set_active(coalesce(active, 0))
    return hc


def lang_combo(FX, connect, **args):
    """ Build combo list of languages """
    if args.get('with_all',True):
        qlang_store = [(None,"All Languages",)]
    else:
        qlang_store = []

    for l in FX.LP.models.keys():
        if l != 'heuristic':
            qlang_store.append( (l, l.upper()) )
    tooltip = args.get('tooltip', 'Select language used fort query tokenizing and stemming')
    return fxcombo(connect, qlang_store , tooltip)



def qtype_combo(connect, **args):
    """ Build query type combo """

    if args.get('rule',False):
        qtype_store = ( (0,'String matching'), (1,'Normal query'), (2,'Exact query'), (3,'REGEX') )
        tooltip = """Set query type to match this rule:
<b>String matching</b>: simple string comparison
<b>Normal:</b> stemmed and tokenized
<b>Exact</b>: unstemmed and tokenized
<b>REGEX</b>: REGEX matching"""
    else:
        qtype_store = ( (1,'Normal query'), (2,'Exact query'), (0,'String matching') )
        tooltip = """Set query type:
<b>Normal:</b> stemmed and tokenized
<b>Exact</b>: unstemmed and tokenized
<b>String matching</b>: simple string comparison"""

    return fxcombo(connect, qtype_store, tooltip)




def qfield_combo(connect, **args):
    """ Build field combo """
    qfield_store = []
    qfield_store.append((-1, ' -- All Fields --'))
    for f in PREFIXES.keys():
        if f != 0: qfield_store.append((f, PREFIXES[f][2]))
    return fxcombo(connect, qfield_store, 'Search in All or a specific field')




def flag_combo(config, **args):
    """ Build combo list of flags """
    tooltip = args.get('tooltip')

    if args.get('filters',True):
        store = (
        ('all', "Flagged and Unflagged", None),
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
        (0, "No Flag", None),
        (1, config.get('gui_flag_1_name','Flag 1'), config.get('gui_flag_1_color')),
        (2, config.get('gui_flag_2_name','Flag 2'), config.get('gui_flag_2_color')),
        (3, config.get('gui_flag_3_name','Flag 3'), config.get('gui_flag_3_color')),
        (4, config.get('gui_flag_4_name','Flag 4'), config.get('gui_flag_4_color')),
        (5, config.get('gui_flag_5_name','Flag 5'), config.get('gui_flag_5_color'))
        )

    return fxcombo(None, store, tooltip, color=True)




def feed_combo(FX, **args):
    """ Builds Feed/Category store for combos. This action is often repeated """
    store = []
    feed = SQLContainer('feeds', FEEDS_SQL_TABLE)
    empty_label = args.get('empty_label', '-- No Category --')

    if not args.get('no_empty',False):
        store.append((0, empty_label,400))

    if args.get('with_categories',True):
        for c in FX.feeds:
            feed.populate(c)
            if feed['is_category'] == 1 and feed['deleted'] != 1:
                store.append((feed['id'], feed_name_cli(feed), 700,))

    if args.get('with_feeds',False):
        for f in FX.feeds:
            feed.populate(f)
            if feed['is_category'] != 1 and feed['deleted'] != 1:
                store.append(  (feed['id'], feed_name_cli(feed), 400,)  )

    if args.get('tooltip') != None: tooltip = args.get('tooltip')
    else: tooltip = 'Choose Channel or Category'

    combo = fxcombo(args.get('connect'), store, tooltip, style=True)

    return combo





def fxlower_page(fields:list):
    """ Wrapper for building page of lower notebook widget (preview result) """
    page = Gtk.ScrolledWindow()
    page.set_border_width(8)
    vbox = Gtk.Box()        
    vbox.set_orientation(Gtk.Orientation.VERTICAL)
    vbox.set_homogeneous(False) 
    for f in fields:
        vbox.pack_start(f, False, False, 5)
    page.add(vbox)
    return page






def fxlabel(text:str, style:str, justify:int, selectable:bool, wrap:bool, **args):
    """ Wrapper for building a label """
    label = Gtk.Label()

    if justify == 1:
        label.set_justify(Gtk.Justification.RIGHT)
        label.set_xalign(1)
    elif justify == 2:
        label.set_justify(Gtk.Justification.CENTER)
    elif justify == 3:
        label.set_justify(Gtk.Justification.LEFT)
    else:
        label.set_xalign(0)
        label.set_justify(Gtk.Justification.LEFT)

    label.set_selectable(selectable)
    label.set_line_wrap(wrap)
    
    if text != None:
        if args.get('markup',False):
            label.set_markup(text)
        else:
            label.set_text(text)

    ellipsize = args.get('ellipsize')
    if ellipsize != None: label.set_ellipsize(ellipsize)

    return label





def fxstore(store, **args):
    """ Builds store for combos """
    st = Gtk.ListStore(str)
    for i in store:
        st.append((i,))
    return st


def fxcombo(connect, store, tooltip:str, **args):
    """ Builds a combobox based on given list """        
    is_entry = args.get('is_entry',False)
    start_at = args.get('start_at',0)
    color = args.get('color', False)
    icon = args.get('icon',False)
    style = args.get('style',False)
    
    if type(store) in (tuple, list):
        sample = slist(store, 1, slist(store, 0, (None,)) )
        if type(sample) == str:
            cstore = Gtk.ListStore(str)
            text_col=0
            for s in store:
                cstore.append((s,))

        elif type(sample) in (tuple, list):
            key = slist(sample, 0, None)
            label = slist(sample, 1, None)
            
            if type(key) == str:
                if color: cstore = Gtk.ListStore(str, str, str)
                elif style: cstore = Gtk.ListStore(str, str, int)
                else: cstore = Gtk.ListStore(str, str)
            elif type(key) == int:
                if color: cstore = Gtk.ListStore(int, str, str)
                elif style: cstore = Gtk.ListStore(int, str, int)
                else: cstore = Gtk.ListStore(int, str)

            text_col=1

            for s in store:
                cstore.append(s)
    else:
        cstore = store
        text_col=0

    if is_entry:
        combo = Gtk.ComboBox.new_with_entry()
        combo.set_entry_text_column(text_col)
        combo.set_model(cstore)
    else:
        combo = Gtk.ComboBox.new_with_model(cstore)
        rend = Gtk.CellRendererText()
        rend.props.ellipsize = Pango.EllipsizeMode.START
        combo.pack_start(rend, True)
        combo.add_attribute(rend, 'text', text_col)
        if color: combo.add_attribute(rend, 'foreground', 2)
        elif style: combo.add_attribute(rend, 'weight', 2)
            
    combo.set_tooltip_markup(tooltip)
    combo.set_active(start_at)

    if connect not in (None,''):
        combo.connect('changed', connect)

    return combo



def fx_get_combo(combo):
    """ Get current combo's ID value (assumed to be the first on the store list) """
    model = combo.get_model()
    active = combo.get_active()
    return model[active][0]

def fx_get_combo_id(combo, id):
    """ Get the combo's element with a given ID (assumed to be the first on the store list)"""
    model = combo.get_model()
    for i,m in enumerate(model):
        if m[0] == id: return i
    return 0             






def fxbutton(label:str, icon:str, connect, **args):
    """ Wrapper for building a button """
    if icon != None and label in (None,''):
        but = Gtk.Button.new_from_icon_name(icon, Gtk.IconSize.BUTTON)
    else:
        but = Gtk.Button()

    label = scast(label, str, '')
    if label != '' and icon in (None,''):
        but.set_label(label)

    if icon not in (None, '') and label not in (None,''):
        im = Gtk.Image.new_from_icon_name(icon, Gtk.IconSize.BUTTON)
        im.show()
        lb = Gtk.Label()
        lb.set_text(label)
        vbox = Gtk.Box()
        vbox.set_orientation(Gtk.Orientation.HORIZONTAL)
        vbox.pack_start(im, False, False, 3)
        vbox.pack_start(lb, False, False, 3)
        but.add(vbox)

    if args.get('tooltip',None) != None:
        but.set_tooltip_markup(args.get('tooltip',''))

    if connect not in (None,''):
        but.connect('clicked', connect)

    return but







def fxcol(title:str, ctype:int,  model_col:int, **args):
    """ Wrapper for building a TreeVeiw column """
    color_col = args.get('color_col')
    attr_col = args.get('attr_col')
    ellipsize = args.get('ellipsize','end')
    sort_col = args.get('sort_col')
    start_width = args.get('start_width')
    name = args.get('name')

    if ctype in (0,3):
        renderer = Gtk.CellRendererText()
    else:
        renderer = Gtk.CellRendererPixbuf()

        
    if ctype == 0:
        col = Gtk.TreeViewColumn( title, renderer, text=model_col)
    elif ctype == 1:
        col = Gtk.TreeViewColumn( title, renderer, pixbuf=model_col)
    elif ctype == 3:
        col = Gtk.TreeViewColumn( title, renderer, markup=model_col)

    if attr_col != None and ctype in (0,3):
        col.add_attribute(renderer, 'weight', attr_col)    
    if color_col != None and ctype in (0,3):
        col.add_attribute(renderer, 'foreground', color_col)    

    if ctype in (0,3):    
        if ellipsize == None: pass
        elif ellipsize == 'end':
            renderer.props.ellipsize = Pango.EllipsizeMode.END
        elif ellipsize == 'start':
            renderer.props.ellipsize = Pango.EllipsizeMode.START


    if args.get('clickable',True):
        col.set_clickable(True)
        if sort_col != None:
            col.set_sort_column_id(sort_col)    
        else:
            col.set_sort_column_id(model_col)
        col.set_sort_indicator(True)
    else:
        col.set_clickable(False)

    if args.get('resizable',True):
        col.set_resizable(True)
    else:
        col.set_resizable(False)

    if args.get('reorderable',True):
        col.set_reorderable(True)
    else:
        col.set_reorderable(False)

    if args.get('width',None) != None:
        col.set_min_width(args.get('width',16))

    if start_width != None:
        col.props.fixed_width = start_width
    if name != None:
        col.set_name(name)

    return col




def fxmenu_item(itype:int, label:str, connect, **args):
    """ Wrapper for building menu item """
    icon = args.get('icon')
    color = args.get('color')
    tooltip = args.get('tooltip')
    kargs = args.get('kargs')

    if itype == 0:
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

    if itype == 3:
        if connect != None:
            item.set_submenu(connect)
        
    elif connect != None:
        item.connect('activate', connect, kargs)

    if tooltip != None:
        item.set_tooltip_markup(tooltip)

    return item





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






def download_res(url:str, filename:str, **args):
    """ Downloads a resource at URL and creates a cache file from hashed URL """
    headers = {'User-Agent' : 'UniversalFeedParser/5.0.1 +http://feedparser.org/'}
    try:
        req = urllib.request.Request(url, None, headers)
        response = urllib.request.urlopen(req)
        if response.status == 200:
            img_data = BytesIO(response.read())
            img = Image.open(img_data)
            if not args.get('no_thumbnail',False):
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



def feed_name(feed, **args):
    """ Sanitize feed name for GUI """
    return GObject.markup_escape_text(feed_name_cli(feed))

def rule_name(rule, **args):
    """ Sanitize rule name for GUI """
    return GObject.markup_escape_text(rule_name_cli(rule))





def load_gui_cache(ifile:str):
    """ Loads GUI attr from file to dict """
    if not os.path.isfile(ifile): return {}

    try:
        attrs = {}
        with open(ifile, 'r') as f:
            attrs = json.load(f)
        return attrs    
    except:
        return {}


def save_gui_cache(ofile:str, attrs:dict):
    """ Saves GUI attrs into text file """
    try:
        with open(ofile, 'w') as f:
            json.dump(attrs, f)
        return 0
    except:
        sys.stderr.write('Error saving to cache!')
        return -1







from feedex_desktop_notifier import DesktopNotifier
from feedex_gui_dialogs import *
