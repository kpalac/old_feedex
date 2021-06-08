# -*- coding: utf-8 -*-
""" GUI classes for FEEDEX """

from feedex_gui_utils import *








class FeedexMainWin(Gtk.Window):
    """ Main window for Feedex """

    def __init__(self, **args):
    
        self.config = args.get('config', DEFAULT_CONFIG)
    
        self.gui_attrs = load_gui_cache(FEEDEX_GUI_ATTR_CACHE)

        self.args = args
        self.debug = args.get('debug',False)

        self.filters = {}
        self.show_trash = False
        self.curr_filters = {}
        self.curr_query = 0
        self.feed_filter = (0,)
        self.feed_ids = '0'
        self.feeds_found = {}
        self.res_per_feed = {}
        self.query = {}

        self.curr_upper = 0
        self.curr_lower = 0

        self.sec_frac_counter = 0
        self.sec_counter = 0
        self.minute_counter = 0

        self.today = 0
        self._time()

        self.new_from_url_fields = {}
        self.entry_fields = {}
        self.new_category_fields = {}
        self.new_feed_fields = {}
        self.new_rule_fields = {}

        self.feed = SQLContainer('feeds', FEEDS_SQL_TABLE, replace_nones=True)
        self.result = SQLContainer('entries', RESULTS_SQL_TABLE, replace_nones=True)
        self.context = SQLContainer('entries', RESULTS_SQL_TABLE + ('context',), replace_nones=True)
        self.rule = SQLContainer('rules', RULES_SQL_TABLE, replace_nones=True)

        self.sel_result = SQLContainer('entries', RESULTS_SQL_TABLE, replace_nones=True)
        self.sel_feed = SQLContainer('feeds', FEEDS_SQL_TABLE, replace_nones=True)
        self.sel_rule = SQLContainer('rules', RULES_SQL_TABLE, replace_nones=True)

        self.FX = Feeder(config=self.config, debug=self.debug, ignore_images=self.config.get('ignore_images', False), gui=True, load_icons=True)
        if self.FX.locked():

            dialog = YesNoDialog(None, "Feedex: Database is Locked", "<b>Database is Locked! Proceed and unlock?</b>", subtitle="Another instance can be performing operations on Database or Feedex did not close properly last time")
            dialog.run()
            if dialog.response == 1:
                self.FX.unlock()
                dialog.destroy()
            else:
                dialog.destroy()
                sys.exit(4)
    
        self.FX.unlock()
        if self.FX.db_status != 0:
            dialog = InfoDialog(None, "Feedex: Database Error!", parse_message(self.FX.db_status), subtitle="Application could not be started! I am sorry for inconvenience :(")
            dialog.run()
            dialog.destroy()
            sys.exit(3)

        self.results = self.FX.QP.query('*', {'from_added': self.FX.get_last(), 'rev':True, 'sort':'+importance'})
        if len(self.results) <= 1:
            self.results = self.FX.QP.query('*', {'last_hour':True, 'rev':True, 'sort':'+importance'})
            if len(self.results) <= 1:
                self.results = self.FX.QP.query('*', {'today':True, 'rev':True, 'sort':'+importance'})
                if len(self.results) <= 1:
                    self.results = self.FX.QP.query('*', {'last_week':True, 'rev':True, 'sort':'+importance'})

        self.contexts = []
        self.rules = []

        # Time series plot
        self.ts_curr_group = 0
        self.ts_terms = []
        self.ts_x_axis = []
        self.ts_plot = None

        self.download_errors = [] #Error list to prevent multiple downloads from faulty links

        # Last new items view
        self.last_viewed_new = scast(self.FX.get_last(), int, 0)

        # Display Queues for threading
        self.message_q = [(0, None)]
        self.images_q = []
        self.changes_q = []

        # Actions
        self.curr_actions = {'fetch':False, 'update_feed':False, 'entry':False, 'feed':False, 'rule':False, 'open':False, 'query':False}
        self.prev_actions = self.curr_actions.copy()

        self.feeds_expanded = {}

        self.plotter_loaded = False

        Gdk.threads_init()
        Gtk.Window.__init__(self, title=f"Feedex {FEEDEX_VERSION}")
        
        self.set_default_size(self.gui_attrs.get('win_width',1500), self.gui_attrs.get('win_height',800))
        self.set_border_width(10)
        self.set_resizable(True)
        self.set_position(Gtk.WindowPosition.CENTER)

        self.icons = get_icons(self.FX.feeds, self.FX.icons)
        self.set_icon(self.icons['main'])

        self.search_status_text = 'Results'
        self.search_status_bar = fxlabel(self.search_status_text,'normal',0,True,True, ellipsize=Pango.EllipsizeMode.END)
        self.search_status_spinner = Gtk.Spinner()

        self.status_bar = fxlabel('','normal',3,True,True, ellipsize=Pango.EllipsizeMode.END) 
        self.status_spinner = Gtk.Spinner()
        lstatus_box = Gtk.Box()
        lstatus_box.set_orientation(Gtk.Orientation.HORIZONTAL)
        lstatus_box.set_homogeneous(False)
        lstatus_box.pack_start(self.status_spinner, False, False, 10)
        lstatus_box.pack_start(self.status_bar, False, False, 10)

        GLib.timeout_add(interval=250, function=self._on_timer)

        # Main Menu
        self.main_menu = Gtk.Menu()
        self.main_menu.append( fxmenu_item(1, 'Preferences', self.on_prefs, icon='preferences-system-symbolic') )
        self.main_menu.append( fxmenu_item(0, 'SEPARATOR', None) )
        self.main_menu.append( fxmenu_item(1, 'Database statistics', self.on_show_stats, icon='drive-harddisk-symbolic') )
        self.main_menu.append( fxmenu_item(1, 'View log', self.on_view_log, icon='text-x-generic-symbolic') )
        self.main_menu.append( fxmenu_item(0, 'SEPARATOR', None) )
        self.main_menu.append( fxmenu_item(1, 'About Feedex...', self.on_show_about, icon='help-about-symbolic') )
        self.main_menu.show_all()

        hbar = Gtk.HeaderBar()
        hbar.set_show_close_button(True)
        hbar.props.title = f"Feedex {FEEDEX_VERSION}"
        if self.config.get('profile_name') != None:
            hbar.props.subtitle = f"{self.config.get('profile_name')}"
        hbar_button_menu = Gtk.MenuButton()
        hbar_button_menu.set_popup(self.main_menu)
        hbar_button_menu.set_tooltip_markup("""Main Menu""")
        hbar_button_menu_icon = Gtk.Image.new_from_icon_name('open-menu-symbolic', Gtk.IconSize.BUTTON)
        hbar_button_menu.add(hbar_button_menu_icon)         
        self.hbar_button_add_entry = fxbutton('','list-add-symbolic', self.on_add_entry, tooltip='Add new <b>Entry</b>') 
        self.set_titlebar(hbar)


        feed_window = Gtk.ScrolledWindow()
        self.feed_store = Gtk.TreeStore(GdkPixbuf.Pixbuf, int, str, str, str, int, str, int, str)
        self.feed_list = Gtk.TreeView(model=self.feed_store)

        feed_window.add(self.feed_list)
        columns = {}
        self.feed_list.append_column( fxcol('', 1, 0, resizable=False, clickable=False, width=16, reorderable=False) )
        columns[2] = fxcol('Title', 3, 2, clickable=False, reorderable=False, color_col=8, start_width=self.gui_attrs.get('feeds',{}).get('2',250), name='2')
        columns[3] = fxcol('Subtitle',0,3, clickable=False, reorderable=False, color_col=8, start_width=self.gui_attrs.get('feeds',{}).get('3',300), name='3')
        columns[4] = fxcol('Link', 0, 4, clickable=False, reorderable=False, color_col=8, start_width=self.gui_attrs.get('feeds',{}).get('4',200), name='4')
        for c in self.gui_attrs.get('feeds_order', (2,3,4)): self.feed_list.append_column(columns[c])
        self.feed_selection = self.feed_list.get_selection()
        
        self.feed_list.connect("row-activated", self.on_activate_feed)
        self.feed_list.set_tooltip_markup("""These are available <b>Channels</b> and <b>Categories</b>
Double-click to filter results according to chosen item.
Right click for more options""")
        self.feed_list.connect("row-expanded", self._on_feed_expanded)
        self.feed_list.connect("row-collapsed", self._on_feed_collapsed)

        self.button_feeds_new        = fxbutton('','list-add-symbolic', self.on_add_from_url, tooltip='<b>Add Channel</b> from URL')
        self.button_feeds_download   = fxbutton('','application-rss+xml-symbolic', self.on_load_news_all, tooltip='<b>Fetch</b> news for all Channels')
        button_feeds_refresh    = fxbutton('','emblem-synchronizing-symbolic', self.reload_feeds, tooltip='Refresh')

        
        result_window = Gtk.ScrolledWindow()
        self.result_store = Gtk.ListStore(GdkPixbuf.Pixbuf, int,int, str,str,str,str,str,str,str,str,int,str,int, int,int, float,float,float, int,float,int,float, int,str, str)
        self.result_list = Gtk.TreeView(model=self.result_store)        

        result_window.add(self.result_list)
        result_window.set_border_width(8)
        self.result_list.append_column( fxcol('', 1, 0, resizable=False, clickable=False, width=16, reorderable=False) )
        columns = {}
        columns[25] = fxcol('Date', 0, 25, color_col=24, attr_col=23, sort_col=11, start_width=self.gui_attrs.get('results',{}).get('25',100), name='25') 
        columns[4] = fxcol('Title', 0, 4, color_col=24, attr_col=23, start_width=self.gui_attrs.get('results',{}).get('4',650), name='4') 
        columns[3] = fxcol('Source', 0, 3, color_col=24, attr_col=23, start_width=self.gui_attrs.get('results',{}).get('3',200), name='3')
        columns[5] = fxcol('Description', 0, 5, color_col=24, attr_col=23, start_width=self.gui_attrs.get('results',{}).get('5',650), name='5')
        columns[7] = fxcol('Author', 0, 7, color_col=24, attr_col=23, start_width=self.gui_attrs.get('results',{}).get('7',200), name='7')
        columns[8] = fxcol('Publisher', 0, 8, color_col=24, attr_col=23, start_width=self.gui_attrs.get('results',{}).get('8',200), name='8')
        columns[9] = fxcol('Category', 0, 9, color_col=24, attr_col=23, start_width=self.gui_attrs.get('results',{}).get('9',200), name='9')
        columns[10] = fxcol('Publ. Timestamp', 0, 10, color_col=24, attr_col=23, start_width=self.gui_attrs.get('results',{}).get('10',200), name='10')
        columns[12] = fxcol('Added', 0, 12, color_col=24, attr_col=23, start_width=self.gui_attrs.get('results',{}).get('12',200), name='12')
        columns[14] = fxcol('Read?', 0, 14, color_col=24, attr_col=23, start_width=self.gui_attrs.get('results',{}).get('14',200), name='14')
        columns[15] = fxcol('Flagged', 0, 15, color_col=24, attr_col=23, start_width=self.gui_attrs.get('results',{}).get('15',200), name='15')
        columns[16] = fxcol('Importance', 0, 16, color_col=24, attr_col=23, start_width=self.gui_attrs.get('results',{}).get('16',200), name='16')
        columns[17] = fxcol('Weight', 0, 17, color_col=24, attr_col=23, start_width=self.gui_attrs.get('results',{}).get('17',200), name='17')
        columns[18] = fxcol('Readability', 0, 18, color_col=24, attr_col=23, start_width=self.gui_attrs.get('results',{}).get('18',200), name='18')
        columns[19] = fxcol('Word Count', 0, 19, color_col=24, attr_col=23, start_width=self.gui_attrs.get('results',{}).get('19',200), name='19')
        columns[6] = fxcol('Link', 0, 6, color_col=24, attr_col=23, start_width=self.gui_attrs.get('results',{}).get('6',400), name='6')
        for c in self.gui_attrs.get('results_order', (25,4,3,5,7,8,9,10,12,14,15,16,17,18,19,6)): self.result_list.append_column(columns[c])

        self.result_list.set_tooltip_markup("""These are search and filtering results. 
Double-click to open in browser. 
Right-click for more options""")

        related_window = Gtk.ScrolledWindow()
        related_window.set_border_width(8)
        related_vbox = Gtk.Box()
        related_vbox.set_orientation(Gtk.Orientation.VERTICAL)
        related_vbox.set_homogeneous(False)
        self.related_text = fxlabel(None, '', 0, True, True)
        related_window.set_tooltip_markup("""Terms related to search phrase are shown here. 
Relations are generated when learning, i.e. when entry is opened or marked as read.
This view allows you to check what interesting articles have connected to searched phrase""")
        related_vbox.pack_start(self.related_text, False, False, 0)
        related_window.add(related_vbox)

        context_window = Gtk.ScrolledWindow()
        context_window.set_border_width(8)
        self.contexts_store = Gtk.ListStore(GdkPixbuf.Pixbuf, int,int, str,str,str,str,str, int,int,int, float,float,float,int,str, str)
        self.contexts_list = Gtk.TreeView(model=self.contexts_store)
        self.contexts_list.append_column( fxcol('', 1, 0, resizable=False, clickable=False, width=16, reorderable=False) )
        columns = {}
        columns[3] = fxcol('Context', 3, 3, color_col=16, start_width=self.gui_attrs.get('contexts',{}).get('3',650), name='3')
        columns[15] = fxcol('Date', 0, 15, color_col=16, sort_col=8, start_width=self.gui_attrs.get('contexts',{}).get('15',150), name='15')
        columns[4] = fxcol('Source', 0, 4, color_col=16, start_width=self.gui_attrs.get('contexts',{}).get('4',200), name='4')
        columns[5] = fxcol('Title', 0, 5, color_col=16, start_width=self.gui_attrs.get('contexts',{}).get('5',650), name='5')
        columns[7] = fxcol('Publ. Timestamp', 0, 7, color_col=16, start_width=self.gui_attrs.get('contexts',{}).get('7',200), name='7')
        columns[9] = fxcol('Read?', 0, 9, color_col=16, start_width=self.gui_attrs.get('contexts',{}).get('9',200), name='9')
        columns[10] = fxcol('Flagged?', 0, 10, color_col=16, start_width=self.gui_attrs.get('contexts',{}).get('10',200), name='10')
        columns[11] = fxcol('Importance', 0, 11, color_col=16, start_width=self.gui_attrs.get('contexts',{}).get('11',200), name='11')
        columns[12] = fxcol('Weight', 0, 12, color_col=16, start_width=self.gui_attrs.get('contexts',{}).get('12',200), name='12')
        columns[13] = fxcol('Readability', 0, 13, color_col=16, start_width=self.gui_attrs.get('contexts',{}).get('13',200), name='13')
        columns[14] = fxcol('Word Count', 0, 14, color_col=16, start_width=self.gui_attrs.get('contexts',{}).get('14',200), name='14')
        columns[6] = fxcol('Link', 0, 6, color_col=16, start_width=self.gui_attrs.get('contexts',{}).get('6',400), name='6')
        for c in self.gui_attrs.get('contexts_order', (3,15,4,5,7,9,10,11,12,13,14,6)): self.contexts_list.append_column(columns[c])

        self.contexts_selection = self.contexts_list.get_selection()
        context_window.set_tooltip_markup("""Search phrase in context is shown here.
Double-click to open the entry containing a context.
Right-click for more options""")
        context_window.add(self.contexts_list)

        rules_window = Gtk.ScrolledWindow()
        rules_window.set_border_width(8)
        self.rules_store = Gtk.ListStore(int, str, str, float, str, str, str, str, str, str, str)
        self.rules_list = Gtk.TreeView(model=self.rules_store)
        columns = {}
        columns[1] = fxcol('Name', 0, 1, color_col=10, start_width=self.gui_attrs.get('rules',{}).get('1',200), name='1')
        columns[2] = fxcol('Search String', 0, 2, color_col=10, start_width=self.gui_attrs.get('rules',{}).get('2',200), name='2')
        columns[3] = fxcol('Weight', 0, 3, color_col=10, start_width=self.gui_attrs.get('rules',{}).get('3',100), name='3')
        columns[4] = fxcol('Case ins.', 0, 4, color_col=10, start_width=self.gui_attrs.get('rules',{}).get('4',50), name='4')
        columns[5] = fxcol('Type', 0, 5, color_col=10, start_width=self.gui_attrs.get('rules',{}).get('5',200), name='5')
        columns[6] = fxcol('Learned?', 0, 6, color_col=10, start_width=self.gui_attrs.get('rules',{}).get('6',50), name='6')
        columns[7] = fxcol('Flag?', 0, 7, color_col=10, start_width=self.gui_attrs.get('rules',{}).get('7',50), name='7')
        columns[8] = fxcol('On Field', 0, 8, color_col=10, start_width=self.gui_attrs.get('rules',{}).get('8',150), name='8')
        columns[9] = fxcol('On Feed/Category', 0, 9, color_col=10, start_width=self.gui_attrs.get('rules',{}).get('9',450), name='9')
        for c in self.gui_attrs.get('rules_order', (1,2,3,4,5,6,7,8,9)): self.rules_list.append_column(columns[c])

        self.rules_list.connect("row-activated", self.on_activated_rule)
        self.rules_selection = self.rules_list.get_selection()
        rules_window.set_tooltip_markup("""These are manually added rules used for flagging. 
Double-click to load rule as a query. 
Right-click for more options""")
        rules_window.add(self.rules_list)
        

        self.upper_notebook = Gtk.Notebook()
        self.upper_notebook.append_page(result_window, Gtk.Label(label="News and Entries"))
        self.upper_notebook.append_page(related_window, Gtk.Label(label="Related Terms"))
        self.upper_notebook.append_page(context_window, Gtk.Label(label="Term in Context"))
        self.upper_notebook.append_page(rules_window, Gtk.Label(label="Rules"))
        self.upper_notebook.set_scrollable(True)
        self.upper_notebook.set_tooltip_markup(
"""Select data you want to display:
<b>News and Entries</b>: standard search for matching entries
<b>Related Terms</b>: view terms that are related to queried terms by context
<b>Term in Time</b>: plot occurrence of searched phrase in time
<b>Term in Context</b>: display search phrase in highlighted contexts
<b>Rules</b>: display and search rules used to rank new entries"""
)
        self.upper_notebook.connect('switch-page', self.on_unb_changed)
                
        self.history = Gtk.ListStore(str)
        self.reload_history()
        self.query_combo = fxcombo(None, self.history,
"""Enter your search phrase here
Wildcard: <b>*</b> (Normal and Exact only)
Field beginning: <b>^</b>
Field end: <b>$</b>
Near: <b>~(number of words)</b> (Normal and Exact only)
""", is_entry=True)
        self.query_entry = self.query_combo.get_child()
        self.query_entry.connect('activate',self.on_query)
        self.query_entry.set_text('')
        self.query_entry.set_icon_from_icon_name(1,'edit-clear-symbolic')
        self.query_entry.set_icon_tooltip_markup(1, 'Clear search phrase')
        self.query_entry.connect('icon-press', self._clear_query_entry)

        self.button_query                    = fxbutton('','edit-find-symbolic', self.on_query, tooltip="Query Entries")
        button_clear                    = fxbutton('','edit-clear-symbolic', self.on_query_clear, tooltip='Clear all query parameters/filters')
        self.button_newest              = fxbutton('', 'star-new-symbolic', self.on_query_newest, tooltip='Show newest articles from last update')
        self.button_similar             = fxbutton('','edit-copy-symbolic', self.on_query_similar, tooltip='<b>Find Similar</b>\nSearch for documents with similar keywords to selected article.\nFor large documents or databases it may take some time\n<i>Results are pruned by Date filters</i>')

        self.case_combo         = fxcombo(self.on_filter_changed, ("Detect case","Case sensitive","Case insensitive"), 'Set query case sensitivity', start_at=0)
        self.read_combo         = fxcombo(self.on_filter_changed, ('Read and Unread','Read','Unread'), 'Filter for Read/Unread news. Manually added entries are read by default')
        self.flag_combo         = flag_combo(self.config, filters=True, tooltip='Filter by Flag or lack thereof') 

        self.qtype_combo        = qtype_combo(self.on_filter_changed, rule=False)
        self.qlang_combo        = lang_combo(self.FX, self.on_filter_changed, with_all=True)

        self.qtime_store = fxstore(['Last Week','Today','Last update','Last Hour','Last Month','Last Quarter','Last Year','All'])
        calendar_button = fxbutton('','x-office-calendar-symbolic',self.on_calendar, tooltip='Choose date range')
        self.qtime_combo        = fxcombo(self.on_filter_changed, self.qtime_store, """Filter by date\n<i>Searching whole database can be time consuming for large datasets</i>""", start_at=1)

        self.qfield_combo       = qfield_combo(self.on_filter_changed)
        self.qhandler_combo       = fxcombo(self.on_filter_changed, HANDLER_CHOICE_ALL, 'Which handler protocols should be taken into account?')


        self.lower_notebook = Gtk.Notebook()

        prev_images_box = Gtk.ScrolledWindow()
        prev_images_box.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
        self.prev_images = Gtk.Box()
        self.prev_images.set_orientation(Gtk.Orientation.HORIZONTAL)
        self.prev_images.set_homogeneous(False)
        prev_images_box.add(self.prev_images)

        self.prev_title = fxlabel(None, 'bold', 2, True, True)
        self.prev_auth  = fxlabel(None, 'italic', 2, True, True)
        self.prev_cat   = fxlabel(None, 'italic_bold', 2, True, True)
        self.prev_desc  = fxlabel(None, 'normal', 3, True, True)
        self.prev_text  = fxlabel(None, 'normal', 0, True, True)
        prev_page       = fxlower_page((prev_images_box, self.prev_title, self.prev_auth, self.prev_cat, self.prev_desc, self.prev_text))
        self.prev_enc   = fxlabel(None, '', 0, True, True)
        enc_page        = fxlower_page((self.prev_enc,))
        self.prev_snips = fxlabel(None, '', 3, True, True)
        snip_page       = fxlower_page((self.prev_snips,))
        self.prev_keyw  = fxlabel(None, 'normal', 0, True, True)
        keyw_page       = fxlower_page((self.prev_keyw,))
        self.prev_stats  = fxlabel(None, 'normal', 0, True, True)
        stats_page       = fxlower_page((self.prev_stats,))
        
        self.lower_notebook.append_page(prev_page, Gtk.Label(label="Preview"))
        self.lower_notebook.append_page(enc_page, Gtk.Label(label="Links"))
        self.lower_notebook.append_page(snip_page, Gtk.Label(label="Snippets"))
        self.lower_notebook.append_page(keyw_page, Gtk.Label(label="Keywords"))
        self.lower_notebook.append_page(stats_page, Gtk.Label(label="Statistics"))

        self.lower_notebook.set_scrollable(True)
        self.lower_notebook.connect('switch-page', self.on_lnb_changed)


        # Build layout
        self.Grid = Gtk.Grid()
        self.add(self.Grid)
        self.Grid.set_column_spacing(10)
        self.Grid.set_row_spacing(10)
        self.Grid.set_column_homogeneous(True)
        self.Grid.set_row_homogeneous(True)

        self.Grid.attach(feed_window, 1, 1, 6, 17)
        self.Grid.attach(self.upper_notebook, 7, 1, 25, 7)
        self.Grid.attach(self.query_combo, 7, 8, 9, 1)
        self.Grid.attach(self.button_query, 16,8,1,1)
        self.Grid.attach(button_clear, 17,8,1,1)
        self.Grid.attach(self.button_newest, 18,8,1,1)
        self.Grid.attach(self.search_status_bar, 20,8,10,1)
        self.Grid.attach(self.search_status_spinner, 30,8,1,1)
        self.Grid.attach(self.case_combo, 28,9,4,1)
        self.Grid.attach(self.qfield_combo, 28,10,4,1)
        self.Grid.attach(self.qtime_combo, 28,11,3,1)
        self.Grid.attach(calendar_button, 31,11,1,1)
        self.Grid.attach(self.read_combo, 28,12,4,1)
        self.Grid.attach(self.flag_combo, 28,13,4,1)
        self.Grid.attach(self.qtype_combo, 28,14,4,1)
        self.Grid.attach(self.qlang_combo, 28,15,4,1)
        self.Grid.attach(self.qhandler_combo, 28,16,4,1)
        self.Grid.attach(self.button_similar, 28,17,1,1)
        self.Grid.attach(self.lower_notebook, 7, 9, 21, 9)
        self.Grid.attach(lstatus_box, 1, 19, 31, 1)

        hbar.pack_start(self.button_feeds_download)
        hbar.pack_start(self.button_feeds_new)
        hbar.pack_start(button_feeds_refresh)

        hbar.pack_end(hbar_button_menu)
        hbar.pack_end(self.hbar_button_add_entry)

        self.result_list.connect("row-activated", self.on_activate_result)
        self.result_selection = self.result_list.get_selection()
        self.result_list.connect("cursor-changed", self.on_changed_result)
        self.result_list.connect("button-press-event", self._rbutton_press, 'results')

        self.contexts_list.connect("row-activated", self.on_activate_result)
        self.contexts_list.connect("cursor-changed", self.on_changed_result)
        self.contexts_list.connect("button-press-event", self._rbutton_press, 'results')

        self.rules_list.connect("cursor-changed", self.load_rule_sel)
        self.rules_list.connect("button-press-event", self._rbutton_press, 'rules')

        self.feed_list.connect("cursor-changed", self.load_feed_sel)
        self.feed_list.connect("button-press-event", self._rbutton_press, 'feeds')


        self.reload_results(first_run=True)
        self.on_filter_changed()

        self.connect("destroy", self._save_gui_attrs)



 

    def _save_gui_attrs(self, *kargs):
        attrs={}
        attrs['feeds'] = {}
        attrs['feeds_order'] = []
        for c in self.feed_list.get_columns():
            name = c.get_name()
            if name == None: continue
            name = int(name)
            attrs['feeds'][name] = c.get_width()
            attrs['feeds_order'].append(name)
        attrs['results'] = {}
        attrs['results_order'] = []
        for c in self.result_list.get_columns():
            name = c.get_name()
            if name == None: continue
            name = int(name)
            attrs['results'][name] = c.get_width()
            attrs['results_order'].append(name)
        attrs['contexts'] = {}
        attrs['contexts_order'] = []
        for c in self.contexts_list.get_columns():
            name = c.get_name()
            if name == None: continue
            name = int(name)
            attrs['contexts'][name] = c.get_width()
            attrs['contexts_order'].append(name)
        attrs['rules'] = {}
        attrs['rules_order'] = []
        for c in self.rules_list.get_columns():
            name = c.get_name()
            if name == None: continue
            name = int(name)
            attrs['rules'][name] = c.get_width()
            attrs['rules_order'].append(name)

        attrs['win_width'], attrs['win_height'] = self.get_size()
        
        if self.gui_attrs != attrs: 
            save_gui_cache(FEEDEX_GUI_ATTR_CACHE, attrs)
            if self.debug: print(attrs)





    def _housekeeping(self): housekeeping(self.config.get('gui_clear_cache',30), debug=self.debug)
    def _time(self, *kargs):
        """ Action on changed minute/day (e.g. housekeeping, changed parameters used for date display """
        old_today = self.today
        self.now = date.today()
        self.yesterday = self.now - timedelta(days=1)
        self.year = self.now.strftime("%Y")
        self.year = f'{self.year}.'
        self.today = self.now.strftime("%Y.%m.%d")
        self.yesterday = self.yesterday.strftime("%Y.%m.%d")
        if old_today != self.today:
            t = threading.Thread(target=self._housekeeping, args=())
            t.start()


    def _rbutton_press(self, widget, event, from_where):
        """ Button press event catcher and menu construction"""
        if event.button == 3:
            menu = None

            if from_where == 'results':
                menu = Gtk.Menu()
                self.load_result_sel()
                if self.sel_result['id'] != None:
                    if not self.curr_actions.get('edit_entry'):
                        flag_menu = Gtk.Menu()
                        flag_menu.append( fxmenu_item(1, self.config.get('gui_flag_1_name','Flag 1'), self.on_mark_flag, kargs=1, color=self.config.get('gui_flag_1_color','blue') ) )
                        flag_menu.append( fxmenu_item(1, self.config.get('gui_flag_2_name','Flag 2'), self.on_mark_flag, kargs=2, color=self.config.get('gui_flag_2_color','blue') ) )
                        flag_menu.append( fxmenu_item(1, self.config.get('gui_flag_3_name','Flag 3'), self.on_mark_flag, kargs=3, color=self.config.get('gui_flag_3_color','blue') ) )
                        flag_menu.append( fxmenu_item(1, self.config.get('gui_flag_4_name','Flag 4'), self.on_mark_flag, kargs=4, color=self.config.get('gui_flag_4_color','blue') ) )
                        flag_menu.append( fxmenu_item(1, self.config.get('gui_flag_5_name','Flag 5'), self.on_mark_flag, kargs=5, color=self.config.get('gui_flag_5_color','blue') ) )

                        menu.append( fxmenu_item(1, 'Mark as Read (+1)', self.on_mark_read, icon='bookmark-new-symbolic', tooltip="Number of reads if counted towards this entry keyword's weight when ranking incoming articles ") )
                        menu.append( fxmenu_item(1, 'Mark as Unread', self.on_mark_unread, icon='edit-redo-rtl-symbolic', tooltip="Unread document does not contriute to ranking rules") )
                        menu.append( fxmenu_item(3, 'Flag Entry', flag_menu, icon='marker-symbolic', tooltip="Flag is a user's marker/bookmark for a given article independent of ranking\n<i>You can setup different flag colors in Preferences</i>") )
                        menu.append( fxmenu_item(1, 'Unflag Entry', self.on_mark_unflag, icon='edit-redo-rtl-symbolic', tooltip="Flag is a user's marker/bookmark for a given article independent of ranking") )
                menu.append( fxmenu_item(1, 'New Entry', self.on_add_entry, icon='list-add-symbolic') )
                if self.sel_result['id'] != None:
                    menu.append( fxmenu_item(1, 'Edit Entry', self.on_edit_entry, icon='edit-symbolic') )
                    if not self.curr_actions.get('edit_entry'): menu.append( fxmenu_item(1, 'Generate Keywords', self.on_gen_keywords, icon='system-run-symbolic') )
                    menu.append( fxmenu_item(1, 'Delete', self.on_del_entry, icon='edit-delete-symbolic') )
                    if self.sel_result['deleted'] == 1: menu.append( fxmenu_item(1, 'Restore', self.on_restore_entry, icon='edit-redo-rtl-symbolic') )
                menu.append( fxmenu_item(0, 'SEPARATOR', None) )
                menu.append( fxmenu_item(1, 'Clear Search History', self.on_clear_history, icon='edit-clear-symbolic') )
                if self.sel_result['id'] != None:
                    if self.debug: menu.append( fxmenu_item(1, 'Details...', self.on_show_detailed, icon='zoom-in-symbolic', tooltip="Show all entry's technical data") )
                
            elif from_where == 'rules':
                self.load_rule_sel()
                menu = Gtk.Menu()
                menu.append( fxmenu_item(1, 'Add Rule', self.on_add_rule, icon='list-add-symbolic') )
                if self.sel_rule['id'] != None:
                    menu.append( fxmenu_item(1, 'Edit Rule', self.on_edit_rule, icon='edit-symbolic') )
                    menu.append( fxmenu_item(1, 'Delete Rule', self.on_del_rule, icon='edit-delete-symbolic') )
                menu.append( fxmenu_item(1, 'Delete Rules from Queries', self.on_del_query_rules, icon='edit-delete-symbolic') )
                menu.append( fxmenu_item(1, 'Clear Search History', self.on_clear_history, icon='edit-clear-symbolic') )
                menu.append( fxmenu_item(1, 'Show Learned Rules', self.show_learned_rules, icon='zoom-in-symbolic', tooltip='Display rules learned from User\'s habits along with weights') )
            
            elif from_where == 'feeds':
                self.load_feed_sel()
                menu = Gtk.Menu()
                if not self.curr_actions['fetch'] and self.sel_feed['id'] not in (-1,None)  and self.sel_feed['deleted'] != 1:
                    menu.append( fxmenu_item(1, 'Show All from newest...', self.on_show_newest_feed, icon='edit-find-symbolic', tooltip="Show all articles for this Channel or Category sorted from newest") )

                menu.append( fxmenu_item(1, 'Add Channel', self.on_add_feed, icon='list-add-symbolic') )
                menu.append( fxmenu_item(1, 'Add Category', self.on_add_category, icon='folder-new-symbolic') )

                if self.sel_feed['id'] in (-1,None):
                    pass
                elif self.sel_feed['id'] == -2:
                    menu.append( fxmenu_item(1, 'Empty Trash', self.on_empty_trash, icon='edit-delete-symbolic') )

                elif self.sel_feed['is_category'] != 1:
                    if not self.curr_actions['fetch']:
                        menu.append( fxmenu_item(1, 'Fetch from selected Channel', self.on_load_news_feed, icon='application-rss+xml-symbolic') )
                        menu.append( fxmenu_item(1, 'Update metadata for Channel', self.on_update_feed, icon='preferences-system-symbolic') )
                        menu.append( fxmenu_item(1, 'Update metadata for All Channels', self.on_update_feed_all, icon='preferences-system-symbolic') )

                    menu.append( fxmenu_item(1, 'Change Category', self.on_change_category, icon='folder-documents-symbolic') )
                    menu.append( fxmenu_item(1, 'Edit Channel', self.on_edit_feed_cat, icon='edit-symbolic') )
                    if self.sel_feed['deleted'] == 1: menu.append( fxmenu_item(1, 'Remove Permanently', self.on_del_feed, icon='edit-delete-symbolic') )
                    else: menu.append( fxmenu_item(1, 'Remove Channel', self.on_del_feed, icon='edit-delete-symbolic') )
                    menu.append( fxmenu_item(1, 'Go to Channel\'s Homepage', self.on_go_home, icon='user-home-symbolic') )
                    menu.append( fxmenu_item(1, 'Mark Channel as healthy', self.on_mark_healthy, icon='go-jump-rtl-symbolic', tooltip="This will nullify error count for this Channel so it will not be ommited on next fetching") )
                    if self.debug: menu.append( fxmenu_item(1, 'Technical details...', self.on_feed_details, icon='zoom-in-symbolic', tooltip="Show all technical information about this Channel") )
                    if self.sel_feed['deleted'] == 1: menu.append( fxmenu_item(1, 'Restore...', self.on_restore_feed, icon='edit-redo-rtl-symbolic') )

                elif self.sel_feed['is_category'] == 1:
                    #menu.append( fxmenu_item(1, 'Show All from newest...', self.on_show_newest_feed, icon='edit-find-symbolic', tooltip="Show all Entries exclusive for this Category sorted from newest") )
                    menu.append( fxmenu_item(1, 'Edit Category', self.on_edit_feed_cat, icon='edit-symbolic') )
                    if self.sel_feed['deleted'] == 1: menu.append( fxmenu_item(1, 'Remove Permanently', self.on_del_feed, icon='edit-delete-symbolic') )
                    else: menu.append( fxmenu_item(1, 'Remove Category', self.on_del_feed, icon='edit-delete-symbolic') )
                    if self.sel_feed['deleted'] == 1: menu.append( fxmenu_item(1, 'Restore...', self.on_restore_feed, icon='edit-redo-rtl-symbolic') )
                
            if menu != None:
                menu.show_all()
                menu.popup(None, None, None, None, event.button, event.time)




    def _on_timer(self, *kargs):
        """ Check for status updates """
        self.sec_frac_counter += 1
        if self.sec_frac_counter > 4:
            self.sec_frac_counter = 0
            self.sec_counter += 1

        if self.sec_counter > 60:
            self.sec_counter = 0
            self.minute_counter += 1
            self._time()
            if self.config.get('gui_fetch_periodically',False):
                self.on_load_news_background()

        if len(self.message_q) > 0:
            m = self.message_q[0]
            self.update_status(slist(m,0,3), slist(m,1,-1))
            del self.message_q[0]

        if len(self.changes_q) > 0:
            ch = self.changes_q[0]
            self.update_local(slist(ch, 0, None), slist(ch, 1, None))
            del self.changes_q[0]        



        if self.curr_actions != self.prev_actions:
            self.prev_actions = self.curr_actions.copy()

            if self.curr_actions['fetch']: 
                self.button_feeds_download.set_sensitive(False)
                self.button_feeds_new.set_sensitive(False)
            else: 
                self.button_feeds_download.set_sensitive(True)
                self.button_feeds_new.set_sensitive(True)

            if self.curr_actions['update_feed']: 
                self.button_feeds_download.set_sensitive(False)
                self.button_feeds_new.set_sensitive(False)
            else: 
                self.button_feeds_new.set_sensitive(True)
                self.button_feeds_download.set_sensitive(True)

        if len(self.images_q) > 0:
            if self.sel_result['id'] == self.images_q[0]:
                self.handle_images(self.sel_result.get('id', None), self.sel_result.get('images',''))
            del self.images_q[0]
            
        return True



    def update_status(self, *kargs):
        """ Updates status bar and busy animation for actions (lower bar)"""
        # Parse message tuple and construct text
        msg = kargs[-1]
        # Handle spinner
        spin = kargs[-2]
        if spin == 1:
            self.status_spinner.show()
            self.status_spinner.start()
        elif spin in (0,3):
            self.status_spinner.stop()
            self.status_spinner.hide()
        if spin != 3:
            self.status_bar.set_markup(parse_message(msg))


    def update_search_status(self, *kargs):
        """ Updates status bar and busy animation for searches"""
        text = kargs[-1]
        spin = kargs[-2]
        if spin:
            self.search_status_spinner.show()
            self.search_status_spinner.start()
        else:
            self.search_status_spinner.stop()
            self.search_status_spinner.hide()
        
        self.search_status_bar.set_markup(text)

        
    def on_lnb_changed(self, *kargs):
        """ Action on changing lower tab """
        self.curr_lower = kargs[2]
        self.on_changed_result(self.result_list.get_selection(), from_tabs=True)


    def on_unb_changed(self, *kargs):
        """ Action on changing upper tab """
        self.curr_upper = kargs[2]

        if self.curr_upper == 3:
            self.reload_rules()
            self.button_query.set_sensitive(False)
            self.button_query.set_tooltip_markup("Query unavailable for Rules")
            self.button_similar.hide()
        else: self.button_query.set_sensitive(True)
        
        if self.curr_upper == 0:
            self.button_query.set_tooltip_markup("Search Entries")
            self.button_similar.show()
        elif self.curr_upper == 1:
            self.button_query.set_tooltip_markup("Generate related keywords' list for Query Term if it appeared in read articles")
            self.button_similar.hide()
        elif self.curr_upper == 2:
            self.button_query.set_tooltip_markup("Display Query Term in contexts")
            self.button_similar.show()



    def on_query_similar(self, *kargs, **args):
        """ Queries for similar document and switches tab to first """
        if self.sel_result['id'] == None: return 0
        if self.curr_actions['query']: return 0
        self.curr_actions['query'] = True
        origin = self.sel_result['id']
        self.show_trash = False
        self.upper_notebook.set_current_page(0)
        self.update_search_status(True, 'Searching for similar entries...')
        self.on_filter_changed()
        self.results = self.FX.QP.find_similar(self.sel_result['id'], **self.filters)
        self.search_status_text = 'Similar entries'
        self.reload_results(ignore_filters=True)
        self.changes_q.append((origin, 'add'))
        self.curr_actions['query'] = False


    def on_show_newest_feed(self, *kargs, **args):
        """ Show all items of a feed/category sorted by pubdate """
        if self.curr_actions['query']: return 0
        if self.sel_feed['id'] == None: return 0
        self.curr_actions['query'] = True
        feed = self.sel_feed['id']
        name = feed_name(self.sel_feed)
        self.upper_notebook.set_current_page(0)
        self.show_trash = False
        self.update_search_status(True, f'Getting newest items for <b>{name}</b>...')
        if self.sel_feed['is_category'] == 1:
            self.results = self.FX.QP.query('*', {'category':feed, 'deleted':False, 'sort':'-pubdate'}, no_history=True)
        else:
            self.results = self.FX.QP.query('*', {'feed':feed, 'deleted':False, 'sort':'-pubdate', 'no_history':True})
        self.search_status_text = f'Entries for <b>{name}</b>'
        self.reload_results(ignore_filters=True)
        self.curr_actions['query'] = False


    def on_query_newest(self, *kargs, **args):
        """ Queries for similar document and switches tab to first """
        if self.curr_actions['query']: return 0
        self.curr_actions['query'] = True
        self.upper_notebook.set_current_page(0)
        self.show_trash = False
        self.update_search_status(True, 'Getting newest items...')
        self.results = self.FX.QP.query('', {'from_added':self.last_viewed_new, 'deleted':False, 'sort':'-importance'}, no_history=True)
        last = scast(self.FX.get_last(), int, 0)
        if self.last_viewed_new < last:
            self.last_viewed_new = last
        self.search_status_text = 'New Entries'
        self.reload_results(ignore_filters=True)
        self.curr_actions['pending'] = False
        self.curr_actions['query'] = False


    def on_query(self, *kargs, **args):
        """ Sends querry to engine and reloads results according to requested data """
        if self.curr_actions['query']: return 0
        self.curr_actions['query'] = True
        query = self.query_entry.get_text()
        self.on_filter_changed()
        self.show_trash = False
        # Check for empty query
        if query.strip() not in ('','*') and query.replace('*','').strip() != '' and query.replace('~','').strip() != '' and not query.replace('~','').strip().isdigit():
            qempty = False
        else:
            qempty = True
            self.filters['sort'] = '+importance'

        self.curr_actions['pending'] = False

        if self.curr_upper == 0:
            self.update_search_status(True, 'Searching...')
            self.results = self.FX.QP.query(query, self.filters)
            self.search_status_text='Results'
            self.reload_results(ignore_filters=True)

        elif self.curr_upper == 1:
            if qempty: 
                self.curr_actions['query'] = False
                return 0
            self.update_search_status(True, 'Searching for related terms...')
            results = self.FX.QP.term_net(query, print=False, lang=self.filters.get('lang'))
            results.sort(key=lambda x: x[-2], reverse=True)
            net_string = ''
            for r in results:
                net_string = f"""{net_string}\n<b>{GObject.markup_escape_text(r[0])}</b>        (weight: <b>{round(scast(r[1], float, 0),3)}</b> found in <b>{r[2]}</b> document(s))"""   
            self.related_text.set_markup(net_string)
            self.update_search_status(False, f'Related terms: {len(self.FX.QP.results)}')

        elif self.curr_upper == 2:
            if qempty: 
                self.curr_actions['query'] = False
                return 0
            self.update_search_status(True, 'Generating contexts...')
            self.contexts = self.FX.QP.term_context(query, **self.filters)
            self.search_status_text='Term contexts'
            self.reload_contexts(ignore_filters=True)
                        
        elif self.curr_upper == 3: pass

        if not qempty:
            self.history.prepend((query,))
            self.query_combo.set_model(self.history)
            if self.config.get('gui_learn_queries',False):
                self.FX.add_rule(name=query, string=query, type=0, case_insensitive=self.filters.get('case',0), additive=1, learned=2, weight=self.config.get('query_rule_weight',10), ignore_lock=True)
        self.curr_actions['query'] = False



    def _clear_query_entry(self, *kargs): self.query_entry.set_text('')

    def on_query_clear(self, *kargs):
        """ Clears query filters and params """
        self.case_combo.set_active(0)
        self.read_combo.set_active(0)
        self.flag_combo.set_active(0)
        self.qtype_combo.set_active(0)
        self.qlang_combo.set_active(0)
        self.qfield_combo.set_active(0)
        self.qtime_combo.set_active(1)
        self.qhandler_combo.set_active(0)
        self.query_entry.set_text('')
        self.on_filter_changed()


    def get_filter_state(self, *kargs, **args):
        """ Save current filter state into a dict """
        filters = {}
        filters['page'] = self.curr_upper
        filters['feeds'] = self.feed_filter
        filters['query'] = self.query_entry.get_text()
        filters['case'] = self.case_combo.get_active()
        filters['field'] = self.qfield_combo.get_active()
        filters['time'] = self.qtime_combo.get_active()
        filters['type'] = self.qtype_combo.get_active()
        filters['lang'] = self.qlang_combo.get_active()
        filters['flag'] = self.flag_combo.get_active()
        filters['read'] = self.read_combo.get_active()
        filters['handler'] = self.qhandler_combo.get_active()       
        return filters      

    

    def on_filter_changed(self, *kargs, **args):
        """ Changes filter dictionary according to widget choices"""
        self.filters={}
        self.filters['rev'] = True
        self.filters['print'] = False

        case_ins = self.case_combo.get_active()
        if case_ins == 0: self.filters['case_ins']=None
        elif case_ins == 1: self.filters['case_ins']=False
        elif case_ins == 2: self.filters['case_ins']=True

        self.filters['field'] = fx_get_combo(self.qfield_combo)
        
        time = self.qtime_combo.get_active()
        if time in (0,1,2,3,4,5,6,7):
            if time == 0:
                self.filters['last_week']=True
            elif time == 1:
                self.filters['today']=True
            elif time == 2:
                self.filters['from_added']=self.FX.get_last()
            elif time == 3:
                self.filters['last_hour']=True
            elif time == 4:
                self.filters['last_month']=True
            elif time == 5:
                self.filters['last_quarter']=True
            elif time == 6:
                self.filters['last_year']=True
            elif time == 7:
                pass

        else:
            rng = self.qtime_combo.get_active()
            rng = scast(self.qtime_store[rng][0], str, '... - ...')
            dlst = rng.split(' - ')
            dfrom = dlst[0]
            dto = dlst[1]    
            if dfrom != '...':
                self.filters['from_date'] = dfrom
            if dto != '...':
                self.filters['to_date'] = dto
 
        self.filters['lang'] = fx_get_combo(self.qlang_combo)
 
        self.filters['qtype'] = fx_get_combo(self.qtype_combo)

        if self.filters['qtype'] in (1,2):
            self.qlang_combo.set_sensitive(True)
            self.case_combo.set_sensitive(True)
        else:
            self.qlang_combo.set_sensitive(False)
            self.case_combo.set_sensitive(False)

        read = self.read_combo.get_active()            
        if read == 1: self.filters['read']=True
        elif read == 2: self.filters['unread']=True

        self.filters['flag'] = fx_get_combo(self.flag_combo)       
        handler = fx_get_combo(self.qhandler_combo)
        if handler == '-1': handler = None
        self.filters['handler'] = handler
        
        if self.debug: print(self.filters)




    def on_calendar(self, *kargs):
        """ Shows calendar dialog and saves date range to the combo """
        dialog = DateChoose(self)
        dialog.run()
        if dialog.response == 1:
            rng = dialog.rng
            rng = f'{scast(rng[0],str,"...")} - {scast(rng[1],str,"...")}' 
            if self.debug: print(rng)
            ix = None
            for i,s in enumerate(self.qtime_store):
                if s == rng:
                    ix = i
                    break
            if ix == None:
                self.qtime_store.append((rng,))
                self.qtime_combo.set_model(self.qtime_store)
                self.qtime_combo.set_active(len(self.qtime_store)-1)
            else:
                self.qtime_combo.set_active(ix)

        dialog.destroy()


    def on_changed_result(self, *kargs, **args):
        """ Generates result preview when result cursor changes """
        if self.load_result_sel() != 0: return 0
        if self.curr_lower == 0:
            title = GObject.markup_escape_text(self.sel_result.get("title",''))
            author = GObject.markup_escape_text(self.sel_result.get('author',''))
            publisher = GObject.markup_escape_text(self.sel_result.get('publisher',''))
            contributors = GObject.markup_escape_text(self.sel_result.get('contributors',''))
            category = GObject.markup_escape_text(self.sel_result.get('category',''))
            desc = self.sel_result.get("desc",'')
            text = self.sel_result.get("text",'')

            self.prev_title.set_markup(f"\n\n<b>{title}</b>")
            self.prev_auth.set_markup(f'<i>{author} {publisher} {contributors}</i>')
            self.prev_cat.set_markup(f'{category}')
            self.prev_desc.set_text(desc)
            self.prev_text.set_text(text)

            if not self.config.get('ignore_images',False):
                self.handle_images(self.sel_result.get('id', None), self.sel_result.get('images',''))


        elif self.curr_lower == 4:

            stat_str = f"""\n\nWord count: <b>{self.sel_result['word_count']}</b>
Character count: <b>{self.sel_result['char_count']}</b>
Sentence count: <b>{self.sel_result['sent_count']}</b>
Capitalized word count: <b>{self.sel_result['caps_count']}</b>
Common word count: <b>{self.sel_result['com_word_count']}</b>
Polysyllable count: <b>{self.sel_result['polysyl_count']}</b>
Numeral count: <b>{self.sel_result['numerals_count']}</b>\n
Importance: <b>{round(self.sel_result['importance'],3)}</b>
Weight: <b>{round(self.sel_result['weight'],3)}</b>
Readability: <b>{round(self.sel_result['readability'],3)}</b>\n"""
            self.prev_stats.set_markup(stat_str)
            

        elif self.curr_lower == 1:
            link_text=''
            for l in self.sel_result.get('links','').splitlines() + self.sel_result.get('enclosures','').splitlines():
                if l.strip() == '':
                    continue
                link_text = f"""{link_text}<a href="{GObject.markup_escape_text(l.replace('<','').replace('>',''))}" title="Click to open link">{GObject.markup_escape_text(l.replace('<','').replace('>',''))}</a>
"""
            self.prev_enc.set_markup(link_text)


        elif self.curr_lower == 2:
            snip_text=''
            if type(self.sel_result['snippets']) in (list, tuple): 
                for s in self.sel_result['snippets']:
                    snip_text=f"{snip_text}\n{sanitize_snippet(s)}"

            self.prev_snips.set_markup(snip_text)


        elif self.curr_lower == 3: 
            keyw_str = ''
            keywords = self.FX.QP.terms_for_entry(self.sel_result['id'], no_recalc=True)
            keywords.sort(key=lambda x: x[-1], reverse=True)
            for kw in keywords:
                keyw_str = f"""{keyw_str}\n<b>{GObject.markup_escape_text(kw[0])}</b>   ({round(float(kw[1]),4)})"""
            self.prev_keyw.set_markup(keyw_str)



    def on_go_home(self, *args):
        """ Executes browser on channel home page """
        if self.load_feed_sel() != 0: return -1
        
        link = self.sel_feed['link']
        if link not in (None, ''):
            command = self.config.get('browser','firefox --new-tab %u').split()
            for idx, arg in enumerate(command):
                if arg in ('%u', '%U', '%f', '%F'):
                    command[idx] = link

            if self.debug: print(' '.join(command))
            subprocess.call(command)


    def on_activated_rule(self, *kargs):
        """ Places rule features (phrase, type etc.) in query filters """
        if self.load_rule_sel() != 0: return -1

        query = self.sel_rule.get('string','')
        case_ins = self.sel_rule.get('case_insensitive',0)
        qtype = self.sel_rule.get('type',1)
        qfield = self.sel_rule.get('field_id',None)

        tfield = fx_get_combo_id(self.qfield_combo, qfield)
        self.qfield_combo.set_active(tfield)
        
        self.query_entry.set_text(query)

        if case_ins == 1:
            self.case_combo.set_active(1)
        else:             
            self.case_combo.set_active(0)
        if qtype == 0:
            self.qtype_combo.set_active(2)
        else:
            self.qtype_combo.set_active(0)
        self.upper_notebook.set_current_page(0)


    def on_activate_feed(self, *kargs):
        """ Feed or category activate - change filter on entries """
        if self.curr_upper in (1,4): return 0
        if self.load_feed_sel() != 0: return -1
        if self.curr_actions['query']: return 0
        self.curr_actions['query'] = True

        self.update_search_status(True, 'Filtering...')

        ids = []
        for id in self.feed_ids.split(','): ids.append(scast(id, int, -1))

        self.feed_filter = ids
        if self.debug: print(self.feed_filter)
        if self.curr_upper == 0:
            if ids in ([-2],(-2),(-2,)):
                self.feed_filter = (-1,)
                self.show_trash = True
                self.update_search_status(True, 'Searching...')
                trash_filters = self.filters.copy()
                trash_filters['deleted'] = True
                trash_filters['from_date'] = None
                trash_filters['to_date'] = None
                trash_filters['today'] = None
                trash_filters['last_hour'] = None
                trash_filters['last_week'] = None
                trash_filters['last_month'] = None
                trash_filters['last_quarter'] = None
                trash_filters['last_year'] = None
                trash_filters['from_added'] = None
                self.results = self.FX.QP.query('', trash_filters)
                self.search_status_text='Deleted items found'
                self.reload_results(ignore_filters=True)
            else:
                self.reload_results(from_feeds=True)
        elif self.curr_upper == 1:
            pass
        elif self.curr_upper == 2:
            self.reload_contexts(from_feeds=True)
        self.curr_actions['query'] = False





################################################33
# DATA TREE DISPLAY


    def update_local(self, id:int, action, **args):
        """ Updates local stores for display - needed for large query sets not to clog performance"""
        new_result = args.get('new_result')

        if action == 'feeds': 
            self.reload_feeds()

        elif action == 'delete':
            feed_id = None
            for i,r in enumerate(self.result_store):
                if r[1] == id:
                    feed_id = r[2]
                    if self.feed_filter == (-1,):
                        self.result_store[i][24] = 'red'
                    else:
                        self.result_store[i][24] = self.config.get('gui_deleted_color','grey')
                    break
            for i,c in enumerate(self.contexts_store):
                if c[1] == id:
                    self.contexts_store[i][16] = self.config.get('gui_deleted_color','grey')
            for i,r in enumerate(self.results):
                if r[0] == id:
                    del self.results[i]
                    break
            for i,c in enumerate(self.contexts):
                if c[0] == id:
                    del self.contexts[i]
            if feed_id != None: self.feeds_found[feed_id] = self.feeds_found.get(feed_id,0) - 1
            self.reload_feeds()

        elif action == 'edit': 
            if new_result == None: result = list(self.FX.sqlite_cur.execute(f"select {RESULTS_COLUMNS_SQL}\nwhere e.id = ?",(id,)).fetchone())
            else: result = new_result
            for i,r in enumerate(self.result_store):
                if r[1] == id:
                    self.result.populate(result + [None,None])
                    itr = self.result_store.get_iter(i)
                    self.result_store.remove(itr)
                    self.result_store.insert(i, self.result_store_item(self.result))
                    break
            for i,c in enumerate(self.contexts_store):
                if c[1] == id:
                    self.context.populate(result + [None,None,c[3]])
                    new_context = list(self.contexts_store_item(self.context))
                    new_context[3] = c[3]
                    itr = self.contexts_store.get_iter(i)
                    self.contexts_store.remove(itr)
                    self.contexts_store.insert(i, new_context)

            for i,r in enumerate(self.results):
                if r[0] == id:
                    self.results[i] = result + [None,None]
            for i,c in enumerate(self.contexts):
                if c[0] == id:
                    new_context = result + [None,None,c[-1]]
                    self.contexts[i] = new_context

        elif action == 'add':
            if self.feed_filter != (-1,):
                self.result.populate(list(self.FX.sqlite_cur.execute(f"select {RESULTS_COLUMNS_SQL}\nwhere e.id = ?",(id,)).fetchone()) + [None,None])
                new_result = list(self.result_store_item(self.result))
                new_result[-2] = self.config.get('gui_new_color','#0FDACA')
                self.result_store.insert(0, new_result)
                self.results.append(self.result.listify(all=True))


    def load_result_sel(self, *kargs):
        """ Wrapper for loading result data from feeder class results by id and populating SQL container"""
        self.sel_result.clear()
        if self.curr_upper == 0:
            model, treeiter = self.result_selection.get_selected()
            if treeiter is None: return 0
            id = model[treeiter][1]
            for r in self.results:
                if id == r[self.result.get_index('id')]:
                    self.sel_result.populate(r)
                    return 0

        elif self.curr_upper == 2:
            model, treeiter = self.contexts_selection.get_selected()
            if treeiter is None: return 0
            id = model[treeiter][1]
            for r in self.contexts:
                if id == r[self.result.get_index('id')]:
                    self.sel_result.populate(r[:-1])
                    return 0


    def load_feed_sel(self, *kargs):
        """ Loads feed from selection to container """
        self.sel_feed.clear()
        model, treeiter = self.feed_selection.get_selected()
        if treeiter is None: return -1
        id=model[treeiter][1]
        self.feed_ids = model[treeiter][6]
        if self.feed_ids in ('-1','-2'):
            self.sel_feed.clear()
            self.sel_feed['id'] = int(self.feed_ids)
            return 0
        for f in self.FX.feeds:
            if id == f[self.feed.get_index('id')]:
                self.sel_feed.populate(f)
                return 0
        

    def load_rule_sel(self, *kargs):
        """ Load rule from selection """
        self.sel_rule.clear()
        model, treeiter = self.rules_selection.get_selected()
        if treeiter is None: return -1
        id=model[treeiter][0]
        for r in self.rules:
            if r[self.rule.get_index('id')] == id:
                self.sel_rule.populate(r)
                return 0



    def reload_history(self):
        """ Loads search phrase history from DB """
        self.history.clear()
        hist = self.FX.sqlite_cur.execute("select distinct string from search_history order by date DESC").fetchall()
        if hist not in (None, (None,)):
            for h in hist:
                if h not in (None, (None,)):
                    self.history.append((h[0],))



    def _on_feed_expanded(self, *kargs):
        """ Register expanded rows """
        path = kargs[-1]
        id = self.feed_store[path][1]
        self.feeds_expanded[id] = True

    def _on_feed_collapsed(self, *kargs):
        """ Register collapsed rows """
        path = kargs[-1]
        id = self.feed_store[path][1]
        self.feeds_expanded[id] = False


    def feed_store_item(self, feed):
        """ Generates a list of feed fields """
        self.feed.populate(feed)

        title = feed_name(self.feed) 

        if self.feed.get('error',0) >= self.config.get('error_threshold',5):
            icon = self.icons.get('error', None)
            color = 'red'
        elif self.feed.get('deleted',0) == 1:
            icon = self.icons.get(self.feed["id"], self.icons.get('default',None))
            color = self.config.get('gui_deleted_color','grey')            
        else:
            icon = self.icons.get(self.feed["id"], self.icons.get('default',None))
            color = None

        if self.feeds_found.get(self.feed.get("id",-1),0) > 0:
            title = f'<b>({self.feeds_found.get(self.feed.get("id",-1),0)})  {title}</b>'

        return (icon,  self.feed.get("id",-1), title, self.feed.get("subtitle",''), self.feed.get("link",''), 0, f'{self.feed.get("id",-1)}', scast(self.feed.get('deleted',0),int,0), color)

                

    def reload_feeds(self, *kargs, **args):
        """ Loads feed data and entry types (inverse id) into list store """
        if not args.get('first_run',False):
            self.FX.load_feeds()        
        expanded = []
        # Update store ...
        self.feed_store.clear()

        for c in self.FX.feeds:

            if c[self.feed.get_index('is_category')] != 1: continue
            if c[self.feed.get_index('deleted')] == 1: continue

            id = scast(c[self.feed.get_index('id')], int, 0)
            name = GObject.markup_escape_text(scast(c[self.feed.get_index('name')], str, ''))
            match_count = self.feeds_found.get(id,0)
            ids=f'{id}'
            for f in self.FX.feeds:
                self.feed.populate(f)
                if self.feed['parent_id'] == id and self.feed['is_category'] != 1 and self.feed['deleted'] != 1:
                    match_count += self.feeds_found.get(self.feed['id'],0)
                    ids = f'{ids},{self.feed.get("id","-1")}'

            if match_count > 0:
                name = f'<b>({match_count})  {name}</b>'
            else:
                name = f'{name}'
            subtitle = GObject.markup_escape_text(f'{scast(c[self.feed.get_index("subtitle")], str, "")}')
            icon = self.icons.get('doc',None)

            cat_row = self.feed_store.append(None, (icon, id, name, subtitle, None, 1, ids, 0, None)) 

            for f in self.FX.feeds:
                self.feed.populate(f)
                if self.feed['parent_id'] == id and self.feed['is_category'] != 1 and self.feed['deleted'] != 1:
                    self.feed_store.append(cat_row, self.feed_store_item(self.feed))
            if self.feeds_expanded.get(id): expanded.append(cat_row)

        all_row = self.feed_store.append(None, (None, -1, 'All...', '', None, 1, '-1', 0, None))
        for f in self.FX.feeds:
            self.feed.populate(f)
            if self.feed['deleted'] != 1 and self.feed['is_category'] != 1:
                self.feed_store.append(all_row, self.feed_store_item(self.feed))
        if self.feeds_expanded.get(-1): expanded.append(all_row)

        deleted_row = self.feed_store.append(None, (self.icons.get('trash', None), -2, 'Trash', '', None, 1, '-2', 1, None))            
        for f in self.FX.feeds:
            self.feed.populate(f)
            if self.feed['deleted'] == 1:
                row = self.feed_store.append(deleted_row, self.feed_store_item(self.feed))
                if self.feed['is_category'] == 1 and self.feeds_expanded.get(self.feed['id']): expanded.append(row)
        if self.feeds_expanded.get(-2): expanded.append(deleted_row)
                    
        if not args.get('first_run',False):
            self.feed_list.realize()
        else:
            pass

        for e in expanded:
            self.feed_list.expand_row(self.feed_store.get_path(e), False)


    def _humanize_date(self, string):
        """ Format date to be more human readable and context dependent """
        date_short = string
        date_short = date_short.replace(self.today, "Today")
        date_short = date_short.replace(self.yesterday, "Yesterday")
        date_short = date_short.replace(self.year,'')
        return date_short


    def result_store_item(self, result):
        """ Generate result item for table """
        icon = self.icons.get(result["feed_id"],self.icons['default'])
        source = result["feed_name"]

        desc = scast(result.get("desc",''),str,'')
        desc = (desc[:75] + '...') if len(desc) > 75 else desc  
        if result.get('read',0) >= 1: weight = 700
        else: weight = 400

        if result.get('deleted',0) == 1: color = self.config.get('gui_deleted_color','grey')
        elif result.get('flag',0) == 1: color = self.config.get('gui_flag_1_color', 'blue')
        elif result.get('flag',0) == 2: color = self.config.get('gui_flag_2_color', 'blue')
        elif result.get('flag',0) == 3: color = self.config.get('gui_flag_3_color', 'blue')
        elif result.get('flag',0) == 4: color = self.config.get('gui_flag_4_color', 'blue')
        elif result.get('flag',0) == 5: color = self.config.get('gui_flag_5_color', 'blue')
        else: color = None

        return (icon, 
                result.get("id",0),
                result.get("feed_id",0), 
                source,
                result.get("title",'').replace('\n',' '), 
                desc.replace('\n',' '), 
                result.get("link",''),
                result.get("author",''), 
                result.get("publisher",''), 
                result.get("category",''),
                result.get("pubdate_r",''), 
                result.get("pubdate",0), 
                result.get("adddate_str",''), 
                result.get("adddate",0),
                result.get("read",0), 
                result.get("flag",0), 
                result.get("importance",0), 
                result.get("weight",0),
                result.get("readability",0), 
                result.get("word_count",0),
                result.get('rank',0), 
                result.get('count',0), 
                result.get('similarity',0),
                weight,
                color,
                self._humanize_date(result.get('pubdate_short','')))



    def reload_results(self, **args):
        """ Gets result from Feeder subclass and generates display"""
        ignore_filters = args.get('ignore_filters',False)
        first_run = args.get('first_run',False)
        from_feeds = args.get('from_feeds',False)

        today = date.today()
        yesterday = today - timedelta(days=1)
        year = today.strftime("%Y")
        year = f'{year}.'
        today = today.strftime("%Y.%m.%d")
        yesterday = yesterday.strftime("%Y.%m.%d")

        if not from_feeds: self.feeds_found = {}
        tmp_store = Gtk.ListStore(GdkPixbuf.Pixbuf,  int,int, str,str,str,str,str,str,str,str,int,str,int, int,int, float,float,float, int,float,int,float, int,str, str)
        i = 0
        for r in self.results:
            if not first_run:
                i += 1 
                if i == 100:
                    i = 0
                    Gtk.main_iteration()   

            self.result.populate(r)
            
            # Apply filters
            if self.feed_filter not in (0,[0],(0),(0,),(),None,(-1),[-1],(-1,)) and self.result["feed_id"] not in self.feed_filter and not ignore_filters: continue
            if self.feed_filter == (-1): continue

            if self.feed_filter in (0,(0),[0],(0,),(),None,(-1),[-1],(-1,)) or ignore_filters:
                if not from_feeds:
                    self.feeds_found[self.result['feed_id']] = self.feeds_found.get(self.result['feed_id'],0) + 1

            tmp_store.append(self.result_store_item(self.result))
        
        self.result_store = tmp_store
        self.result_list.set_model(self.result_store)
        if not from_feeds: self.reload_feeds()
        self.update_search_status(False, f'{self.search_status_text}: {len(self.result_store)}')



    def contexts_store_item(self, context):
        """ Generates context item for table display """
        icon = self.icons.get(context["feed_id"], self.icons['default'])
        source = context["feed_name"]
        desc = scast(context.get("desc",''),str,'')
        desc = (desc[:75] + '...') if len(desc) > 75 else desc

        #if context.get('flag',0) >= 1: color = self.config.get('gui_flag_color','blue')
        if context.get('deleted',0) == 1: color = self.config.get('gui_deleted_color','grey')
        else: color = None

        return (    icon, 
                    context.get("id",0),
                    context.get("feed_id",0),
                    sanitize_snippet(context.get("context",(None,))[0]),
                    source,
                    context.get("title",''),
                    context.get("link",''),
                    context.get("pubdate_r",''),
                    context.get("pubdate",0),
                    context.get("read",0),
                    context.get("flag",0),
                    context.get("importance",0),
                    context.get("weight",0),
                    context.get("readability",0),
                    context.get("word_count",0),
                    self._humanize_date(context.get('pubdate_short','')),
                    color
                )



    def reload_contexts(self, **args):
        """ Reload context store """
        ignore_filters = args.get('ignore_filters',False)
        tmp_store = Gtk.ListStore(GdkPixbuf.Pixbuf, int,int, str,str,str,str,str, int,int,int, float,float,float,int, str, str)
        from_feeds = args.get('from_feeds',False)
        if not from_feeds: self.feeds_found = {}

        today = date.today()
        yesterday = today - timedelta(days=1)
        year = today.strftime("%Y")
        year = f'{year}.'
        today = today.strftime("%Y.%m.%d")
        yesterday = yesterday.strftime("%Y.%m.%d")

        i = 0
        for r in self.contexts:
            i += 1 
            if i == 100:
                i = 0
                Gtk.main_iteration() 

            self.context.populate(r)
            
            # Apply filters
            if self.feed_filter not in (0,(0,),(0),[0],None,[-1],(-1,),(-1), ()) and self.context["feed_id"] not in self.feed_filter and not ignore_filters: continue

            if self.feed_filter in (0,(0,),(0),[0],None, (), (-1,),[-1],(-1)) or ignore_filters:
                if not from_feeds:
                    self.feeds_found[self.context['feed_id']] = self.feeds_found.get(self.context['feed_id'],0) + 1

            tmp_store.append(self.contexts_store_item(self.context))   
        
        self.contexts_store = tmp_store
        self.contexts_list.set_model(self.contexts_store)
        if not from_feeds: self.reload_feeds()
        self.update_search_status(False, f'{self.search_status_text}: {len(self.contexts_store)}')
        



    def reload_rules(self):
        """ Reload rules store """
        self.rules = self.FX.sqlite_cur.execute("""select * from rules where learned in (0,2) order by id desc""").fetchall()
        
        tmp_store = Gtk.ListStore(int, str, str, float, str, str, str, str, str, str, str)

        for r in self.rules:
            self.rule.populate(r)
            id = self.rule.get('id',None)
            name = scast(self.rule.get('name',''), str, '')
            name = (name[:75] + '...') if len(name) > 75 else name
            string = scast(self.rule.get('string',''), str, '')
            string = (string[:75] + '...') if len(string) > 75 else string
            weight = round(scast(self.rule.get('weight',-1), float, 0), 3)
            if self.rule['case_insensitive'] == 1: case_ins = 'Yes'
            else: case_ins = 'No'
            if self.rule['type'] == 0: qtype = 'String matching'
            elif self.rule['type'] == 1: qtype = 'Full Text (Stemmed)'
            elif self.rule['type'] == 2: qtype = 'Full Text (Exact)'
            elif self.rule['type'] == 3: qtype = 'REGEX'
            else: qtype = '<<UNKNOWN>>'

            qfield = slist(PREFIXES.get(self.rule['field_id'], None), 2, 'Every field')
            if self.rule['feed_id'] == None or self.rule['feed_id'] <= 0: qfeed = 'All feeds and Categories'
            else: qfeed = '<<UNKNOWN>>'

            for f in self.FX.feeds:
                if self.rule['feed_id'] == f[self.feed.get_index('id')]:
                    qfeed = coalesce(f[self.feed.get_index('name')], f[self.feed.get_index('id')])
                    break

            if self.rule['learned'] == 1: learned = 'Yes'
            elif self.rule['learned'] == 2: learned = 'From Query'
            else: learned = 'No'

            if self.rule['flag'] in (0,None): 
                flag = 'No'
                color = None
            elif self.rule['flag'] == 1:
                flag = 'Flag 1'
                color = self.config.get('gui_flag_1_color')
            elif self.rule['flag'] == 2:
                flag = 'Flag 2'
                color = self.config.get('gui_flag_2_color')
            elif self.rule['flag'] == 3:
                flag = 'Flag 3'
                color = self.config.get('gui_flag_3_color')
            elif self.rule['flag'] == 4:
                flag = 'Flag 4'
                color = self.config.get('gui_flag_4_color')
            elif self.rule['flag'] == 5:
                flag = 'Flag 5'
                color = self.config.get('gui_flag_5_color')
            else: color = None

            tmp_store.append(( id, name, string, weight, case_ins, qtype, learned, flag, qfield, qfeed, color ))

        self.rules_store = tmp_store
        self.rules_list.set_model(self.rules_store)
        self.update_search_status(False, f'Rules: {len(self.rules_store)}')
        







############################################
#   IMAGE HANDLING




    def show_image(self, widget, event, url, title, alt):
        """ Wrapper for showing full-size image in app tool or chosen external viewer"""
        if event.button == 1:
            dialog = DisplayWindow(self, title, alt, image_url=url, close_on_unfocus=True, save_as=True)
            dialog.run()
            dialog.destroy()

        elif event.button == 3:
            hash_obj = hashlib.sha1(url.encode())
            filename = f"""{FEEDEX_CACHE_PATH}/{hash_obj.hexdigest()}_full.img"""
            if not os.path.isfile(filename):                
                err = download_res(url, filename, no_thumbnail=True)
                if err == -1: return -1
            command = self.config.get('image_viewer')
            if command not in (None,''):
                command = command.split()
                for idx, arg in enumerate(command):
                    if arg in ('%u', '%U', '%f', '%F'):
                        command[idx] = filename
                    elif arg == '%t': command[idx] = title
                    elif arg == '%a': command[idx] = alt

                if self.debug: print(' '.join(command))
                subprocess.call(command)


    def download_images(self, id, queue):
        """ Image download wrapper for separate thread"""
        for i in queue:
            url = i[0]
            filename = i[1]
            if url not in self.download_errors:
                if download_res(url, filename) == -1:
                    self.download_errors.append(url)        
        self.images_q.append(id)
        

    def handle_images(self, id:int, string:str, **args):
        """ Handle preview images """
        for c in self.prev_images.get_children():
            self.prev_images.remove(c)

        urls = []
        boxes = []
        download_q = []
        for i in string.splitlines():
            im = res(i)
            if im == 0:
                continue
            if im['url'] in urls:
                continue
            if im['url'] in self.download_errors: continue
            urls.append(im['url'])
            if os.path.isfile(im['filename']) and os.path.getsize(im['filename']) > 0:
                pass
            else:
                download_q.append((im['url'], im['filename']))
                continue

            if id != self.sel_result.get('id', None): continue

            eventbox = Gtk.EventBox()
            pixb = GdkPixbuf.Pixbuf.new_from_file(im['filename'])
            image = Gtk.Image.new_from_pixbuf(pixb)
            if im['alt'] not in (None, '', "\n"):
                image.set_tooltip_markup(im['alt'])
            eventbox.add(image)
            eventbox.connect("button-press-event", self.show_image, im['url'], im['title'], im['alt'])
            image.show()
            eventbox.show()
            boxes.append(eventbox)

        if len(download_q) > 0:
            t = threading.Thread(target=self.download_images, args=(self.sel_result['id'],download_q))
            t.start()

        for b in boxes:
            self.prev_images.pack_start(b, True, True, 3)



#########################################################3
# DIALOGS FROM MENUS OR BUTTONS

    def on_load_news_feed(self, *kargs):
        t = threading.Thread(target=self.load_news, args=('feed',))
        t.start()
    def on_load_news_all(self, *kargs):
        t = threading.Thread(target=self.load_news, args=('all',))
        t.start()
    def on_load_news_background(self, *kargs):
        t = threading.Thread(target=self.load_news, args=('background',))
        t.start()
    def load_news(self, mode):
        """ Fetching news/articles from feeds """
        if self.curr_actions['fetch']: return -2
        self.curr_actions['fetch'] = True
        self.curr_actions['pending'] = False
        if mode == 'all':
            feed_id=None
            ignore_interval = True
            ignore_modified = self.config.get('ignore_modified',True)
            self.message_q.append((1, '<b>Checking all Channels for news...</b>'))
        elif mode == 'background':
            feed_id=None
            ignore_interval = False
            ignore_modified = self.config.get('ignore_modified',True)
            self.message_q.append((1, '<b>Checking all Channels for news...</b>'))
        elif mode == 'feed':
            if self.load_feed_sel() != 0: return -1
            if self.sel_feed['is_category'] != 1:
                self.message_q.append((1,f'Checking <b>{feed_name(self.sel_feed)}</b> for news'))
                feed_id = self.sel_feed['id']
                ignore_interval = True
                ignore_modified = True
            else:
                return -1        
        else: return -1

        FX = Feeder(config=self.config, debug=self.debug, ignore_images=self.config.get('ignore_images',False), gui=True, timeout=1)
        for msg in FX.g_fetch(id=feed_id, force=ignore_modified, ignore_interval=ignore_interval): self.message_q.append((2, msg,))

        if FX.new_items > 0:
            if self.config.get('gui_desktop_notify', True):
                fx_notifier = DesktopNotifier(parent=self, icons=self.FX.icons)
                results = FX.QP.notify(notify_level=self.config.get('notify_level',1), rev=False, print=False)
                fx_notifier.load(results, self.config.get('notify_level',1))
                fx_notifier.show()
            self.curr_actions['pending'] = True

        self.message_q.append((3,None))
        self.curr_actions['fetch'] = False
        self.changes_q.append((None, 'feeds'))


    def on_update_feed(self, *kargs):
        """ Wrapper for feed updating """
        if self.curr_actions['fetch']: return -2
        self.curr_actions['fetch'] = True
        if self.load_feed_sel() != 0: return -1
        if self.sel_feed['is_category'] != 1:
            t = threading.Thread(target=self.update_feed, args=(self.sel_feed['id'],))
            t.start()
    def on_update_feed_all(self, *kargs):
        if self.curr_actions['fetch']: return -2
        t = threading.Thread(target=self.update_feed, args=(None,))
        t.start()
        
    def update_feed(self, *kargs):
        """ Updates metadata for all/selected feed """
        feed_id = kargs[-1]
        FX = Feeder(config=self.config, debug=self.debug, ignore_images=self.config.get('ignore_images',False), gui=True, timeout=1)
        for msg in FX.g_fetch(id=feed_id, update_only=True, force=True):
            self.message_q.append((1, msg,))
        self.icons = get_icons(FX.feeds, self.FX.icons)
        self.message_q.append((3, None,))
        self.curr_actions['fetch'] = False
        self.changes_q.append((None, 'feeds'))


    def add_from_url(self, url, handler, category):
        """ Add from URL - threading """
        FX = Feeder(config=self.config, debug=self.debug, ignore_images=self.config.get('ignore_images',False), gui=True, timeout=1, no_qp=True)
        err = False
        for msg in FX.g_add_feed_from_url(url, handler=handler, category=category):
            if slist(msg, 0, 0) < 0 or scast(msg, int, 0) < 0: err = True
            self.message_q.append((1, msg,))
        self.message_q.append((3, None,))
        self.curr_actions['fetch'] = False
        self.changes_q.append((None, 'feeds'))
        if not err: self.new_from_url_fields = {}

    def on_add_from_url(self, *kargs):
        """ Adds a new feed from URL - dialog """
        if self.curr_actions['fetch']: return -2
        dialog = NewFromURL(self, self.config, self.new_from_url_fields, debug=self.debug)
        dialog.run()
        self.new_from_url_fields = dialog.result
        if dialog.response == 1:
            self.curr_actions['fetch'] = True
            t = threading.Thread(target=self.add_from_url, args=(dialog.result.get('url'), dialog.result.get('handler'), dialog.result.get('category') ))
            t.start()
        dialog.destroy()



    def on_add_entry(self, *kargs): self.edit_entry(None)
    def on_edit_entry(self, *kargs): self.edit_entry(self.sel_result)
    def edit_entry(self, entry, *kargs):
        """ Add / Edit Entry """
        if entry == None: dialog = EditEntry(self, self.config, self.entry_fields, new=True)
        else:
            if self.sel_result['id'] == None: return 0 
            dialog = EditEntry(self, self.config, entry, new=False)
        dialog.run()
        if entry == None: self.entry_fields = dialog.result
        if dialog.response == 1:
            self.curr_actions['edit_entry'] = True
            if entry == None: t = threading.Thread(target=self.edit_entry_thr, args=(None, dialog.result) )
            else: t = threading.Thread(target=self.edit_entry_thr, args=(self.sel_result['id'], dialog.result) )
            t.start()
        dialog.destroy()


    def edit_entry_thr(self, id, result, **args):
        """ Add/Edit Entry low-level interface for threading """
        err = False
        FX = Feeder(config=self.config, debug=self.debug, ignore_images=self.config.get('ignore_images',False), gui=True, wait_indef=True)
        if id == None:
            for msg in FX.g_add_entries(elist=(result,), learn=result.get('learn',False), ignore_lock=True): 
                if slist(msg, 0, 0) < 0 or scast(msg, int, 0) < 0: err = True
                self.message_q.append((1, msg,))
            if not err: 
                self.entry_fields = {}
                self.changes_q.append((FX.last_entry_id, 'add'))
        else:
            del result['learn']
            for msg in FX.g_edit_entry(id, result, ignore_lock=True):
                if slist(msg, 0, 0) < 0 or scast(msg, int, 0) < 0: err = True
                self.message_q.append((1, msg))
            if not err: self.changes_q.append((self.sel_result['id'], 'edit'))
        self.message_q.append((3, None))
        self.curr_actions['edit_entry'] = False        





    def on_del_entry(self, *kargs):
        """ Deletes selected entry"""
        if self.sel_result['id'] == None: return 0
        if self.sel_result['deleted'] != 1: 
            dialog = YesNoDialog(self, 'Delete Entry', '<b>Are you sure you want to delete this entry?</b>')
        else:
            dialog = YesNoDialog(self, 'Delete Entry permanently', '<b>Are you sure you want to permanently delete this entry and associated rules?</b>')
        dialog.run()
        if dialog.response == 1:
            err = False
            for msg in self.FX.g_del_entry(self.sel_result['id'], ignore_lock=True): 
                if slist(msg, 0, 0) < 0 or scast(msg, int, 0) < 0: err = True
                self.update_status(1, msg)
            if not err: self.update_local(self.sel_result['id'], 'delete')
            self.update_status(3, None)
        dialog.destroy()

    def on_restore_entry(self, *kargs):
        """ Restore entry """
        if self.sel_result['id'] == None: return 0
        dialog = YesNoDialog(self, 'Restore Entry', 'Are you sure you want to restore this entry?')
        dialog.run()
        if dialog.response == 1:
            err = False
            for msg in self.FX.g_edit_entry(self.sel_result['id'], {'deleted': 0}, ignore_lock=True): 
                if slist(msg, 0, 0) < 0 or scast(msg, int, 0) < 0: err = True
                self.update_status(1, msg)
            if not err: self.update_local(self.sel_result['id'], 'delete')
            self.update_status(3, None)
        dialog.destroy()






    def on_add_category(self, *kargs): self.edit_category(None)
    def on_add_feed(self, *kargs): self.edit_feed(None)

    def on_change_category(self, *kargs):
        """ Changes feed's category from dialog """
        if self.load_feed_sel() != 0: return -1
        if self.sel_feed['is_category'] == 1: return 0
        dialog = ChangeCategory(self, self.sel_feed.get('name', self.sel_feed.get('title', self.sel_feed.get('id','<<UNKNOWN?>>'))), self.sel_feed.get('parent_id',0))
        dialog.run()
        if dialog.response == 1:
            for msg in self.FX.g_edit_feed(self.sel_feed['id'], {'parent_id': dialog.result}, ignore_lock=True): self.update_status(1, msg)
            self.update_status(3, None)
            self.reload_feeds()
        dialog.destroy()
                
    def on_edit_feed_cat(self, feed, *kargs):
        """ Edit feed/category - wrapper """
        if self.load_feed_sel() != 0: return -1
        if self.sel_feed['is_category'] == 1: self.edit_category(self.sel_feed)
        else: self.edit_feed(self.sel_feed)

    def edit_category(self, category):            
        """ Add/Edit Category """
        if category == None: dialog = EditCategory(self, self.new_category_fields, new=True)
        else: dialog = EditCategory(self, category, new=False)
        dialog.run()
        if category == None: self.new_category_fields = dialog.result
        if dialog.response == 1:
            err = False
            if category == None:
                for msg in self.FX.g_add_feed(dialog.result.get('name'), {'subtitle':dialog.result.get('subtitle'), 'is_category':True}, ignore_lock=True): 
                    if slist(msg, 0, 0) < 0 or scast(msg, int, 0) < 0: err = True
                    self.update_status(1, msg)
            else:
                for msg in self.FX.g_edit_feed(category['id'], dialog.result, ignore_lock=True, type='category'):
                    if slist(msg, 0, 0) < 0 or scast(msg, int, 0) < 0: err = True
                    self.update_status(1, msg)
            self.update_status(3, None)
            if not err: self.new_category_fields = {}
            self.reload_feeds()
        dialog.destroy()


    def edit_feed(self, feed):
        """ Add/Edit Feed from dialog"""
        if feed == None:
            dialog = EditFeed(self, self.new_feed_fields, self.FX, new=True, config=self.config)
        else:
            dialog = EditFeed(self, feed, self.FX, new=False, config=self.config)
        dialog.run()
        if feed == None: self.new_feed_fields = dialog.result
        if dialog.response == 1:
            if feed == None:
                name = dialog.result['name']
                del dialog.result['name']
                dialog.result['is_category'] = False
                dialog.result['ignore_lock'] = True
                for msg in self.FX.g_add_feed(name, **dialog.result): self.update_status(1, msg)
            else:
                for msg in self.FX.g_edit_feed(feed['id'], dialog.result, ignore_lock=True): self.update_status(1, msg)                
            self.update_status(3, None)
            self.reload_feeds()
        dialog.destroy()            


    def on_del_feed(self, *kargs):
        """ Deletes feed or category """
        if self.load_feed_sel() != 0: return -1

        if self.sel_feed['is_category'] != 1:
            if self.sel_feed['deleted'] == 1:
                dialog = YesNoDialog(self, 'Delete Feed permanently', f'<b>Are you sure you want to permanently delete <i>{feed_name(self.sel_feed)}</i> Feed?</b>')
            else:
                dialog = YesNoDialog(self, 'Delete Feed', f'<b>Are you sure you want to delete <i>{feed_name(self.sel_feed)}</i> Feed?</b>')
            dialog.run()
            if dialog.response == 1:
                for msg in self.FX.g_del_feed(self.sel_feed['id'], type='feed'): self.update_status(1, msg)
                self.update_status(3, None)
                self.reload_feeds()
            dialog.destroy()
            
        else:
            if self.sel_feed['deleted'] == 1:
                dialog = YesNoDialog(self, 'Delete Category permanently', f'<b>Are you sure you want to permanently delete <i>{feed_name(self.sel_feed)}</i> Category?</b>')
            else:
                dialog = YesNoDialog(self, 'Delete Category', f'<b>Are you sure you want to delete <i>{feed_name(self.sel_feed)}</i> Category?</b>')
            dialog.run()
            if dialog.response == 1:
                for msg in self.FX.g_del_feed(self.sel_feed['id'], type='category'): self.update_status(1, msg)
                self.update_status(3, None)
                self.reload_feeds()
            dialog.destroy()


    def on_restore_feed(self, *kargs):
        """ Restores selected feed/category """
        if self.load_feed_sel() != 0: return -1
        if self.feed['is_category'] == 1:
            dialog = YesNoDialog(self, 'Restore Category', f'<b>Restore <i>{feed_name(self.sel_feed)}</i> Category?</b>')
        else:
            dialog = YesNoDialog(self, 'Restore Feed', f'<b>Restore <i>{feed_name(self.sel_feed)}</i> Feed?</b>')
        dialog.run()
        if dialog.response == 1:
            for msg in self.FX.g_edit_feed(self.sel_feed['id'], {'deleted': 0}, ignore_lock=True): self.update_status(1, msg)
            self.update_status(3, None)
            self.reload_feeds()
        dialog.destroy()


    def on_empty_trash(self, *kargs):
        """ Empt all Trash items """
        dialog = YesNoDialog(self, 'Empty Trash', f'<b>Do you really want to permanently remove Trash content?</b>')
        dialog.run()
        if dialog.response == 1:
            for msg in self.FX.g_empty_trash(): self.update_status(1, msg)
        self.update_status(3, None)
        self.reload_feeds()
        dialog.destroy()



    def on_mark_healthy(self, *kargs):
        """ Marks a feed as healthy -> zeroes the error count """
        if self.load_feed_sel() != 0: return -1
        for msg in self.FX.g_edit_feed(self.sel_feed['id'], {'error': 0}, ignore_lock=True): self.update_status(1, msg)
        self.update_status(3, None)
        self.reload_feeds()




    def mark_read(self, *kargs):
        """ Marks entry as read """
        id = self.sel_result['id']
        read = scast(self.sel_result['read'], int, 0)
        err = False
        FX = Feeder(config=self.config, debug=self.debug, ignore_images=self.config.get('ignore_images',False), gui=True)
        for msg in FX.g_edit_entry(id, {'read': read+1}, ignore_lock=True):
            if slist(msg, 0, 0) < 0: err = True
            self.message_q.append((1, msg))
        self.message_q.append((3, None))
        self.curr_actions['edit_entry'] = False
        if err: return -1
        self.changes_q.append((id, 'edit'))

    def on_mark_read(self, *kargs):
        if self.sel_result['id'] == None: return 0
        self.curr_actions['edit_entry'] = True
        t = threading.Thread(target=self.mark_read)
        t.start()
        

    def on_mark_unread(self, *kargs):
        """ Marks entry as unread """
        if self.sel_result['id'] == None: return 0        
        err = False
        for msg in self.FX.g_edit_entry(self.sel_result['id'], {'read': 0}, ignore_lock=True):
            if slist(msg, 0, 0) < 0: err = True
            self.update_status(1, msg)
        self.update_status(3, None)
        if err: return -1
        self.update_local(self.sel_result['id'], 'edit')

    def on_mark_flag(self, *kargs):
        """ Marks entry as flagged """
        if self.sel_result['id'] == None: return 0        
        flag = slist(kargs,-1,0)
        err = False
        for msg in self.FX.g_edit_entry(self.sel_result['id'], {'flag': flag}, ignore_lock=True):
            if slist(msg, 0, 0) < 0: err = True
            self.update_status(1, msg)
        self.update_status(3, None)
        if err: return -1
        self.update_local(self.sel_result['id'], 'edit')

    def on_mark_unflag(self, *kargs):
        """ Marks entry as unflagged """
        if self.sel_result['id'] == None: return 0        
        err = False
        for msg in self.FX.g_edit_entry(self.sel_result['id'], {'flag': 0}, ignore_lock=True):
            if slist(msg, 0, 0) < 0: err = True
            self.update_status(1, msg)
        self.update_status(3, None)
        if err: return -1
        self.update_local(self.sel_result['id'], 'edit')

    

    def on_del_rule(self, *kargs):
        """ Deletes rule - wrapper """
        if self.load_rule_sel() != 0: return -1
        dialog = YesNoDialog(self, 'Delete Rule', f'Are you sure you want to permanently delete <b><i>{rule_name(self.sel_rule)}</i></b> Rule?')           
        dialog.run()
        if dialog.response == 1:
            for msg in self.FX.g_del_rule(self.sel_rule['id'], ignore_lock=True): self.update_status(1, msg) 
            self.update_status(3, None)
            self.reload_rules()
        dialog.destroy()


    def on_del_query_rules(self, *kargs):
        """ Deletes all rules from queries """
        dialog = YesNoDialog(self, 'Delete Query Rules', f'Are you sure you want to permanently delete all <b>rules saved from queries</b>?')           
        dialog.run()
        if dialog.response == 1:
            for msg in self.FX.g_delete_query_rules(ignore_lock=True): self.update_status(1, msg) 
            self.update_status(3, None)
            self.reload_rules()
        dialog.destroy()
        

    def on_clear_history(self, *kargs):
        """ Clears search history """
        dialog = YesNoDialog(self, 'Clear Search History', f'Are you sure you want to clear <b>Search History</b>?')           
        dialog.run()
        if dialog.response == 1:
            for msg in self.FX.g_clear_history(ignore_lock=True): self.update_status(1, msg) 
            self.update_status(3, None)
            self.reload_rules()
            self.history.clear()
            self.query_combo.set_model(self.history)
        dialog.destroy()


    def on_add_rule(self, *kargs): self.edit_rule(None)
    def on_edit_rule(self, *kargs): self.edit_rule(self.sel_rule)
    def edit_rule(self, rule):
        """ Edit / Add Rule with dialog """
        if rule == None: 
            dialog = EditRule(self, self.config, self.new_rule_fields, new=True)
        else: 
            if self.load_rule_sel() != 0: return -1
            dialog = EditRule(self, self.config, rule, new=False)

        dialog.run()
        if rule == None: self.new_rule_fields = dialog.result
        if dialog.response == 1:
            err = False
            if rule == None:
                for msg in self.FX.g_add_rule(dialog.result, ignore_lock=True): 
                    if slist(msg, 0, 0) < 0: err = True
                    self.update_status(1, msg)
                if not err: self.new_rule_fields = {}
            else:
                for msg in self.FX.g_edit_rule(rule['id'], dialog.result, ignore_lock=True): 
                    if slist(msg, 0, 0) < 0: err = True
                    self.update_status(1, msg)

            self.update_status(3, None)
            self.reload_rules()
        dialog.destroy()       



    def gen_keywords(self, *kargs, **args):
        """ Manually generates/learns keywords for selected entry """
        if self.sel_result['id'] == None: return 0
        self.message_q.append((1,'Generating keywords...',))
        self.curr_actions['edit_entry'] = True
        FX = Feeder(config=self.config, debug=self.debug, ignore_images=False, gui=True)
        FX.recalculate(id=self.sel_result['id'], learn=True, stats=False, rank=False, force=True, verbose=False, ignore_lock=True)
        self.message_q.append((0,'Finished generating keywords',))
        self.curr_actions['edit_entry'] = False

    def on_gen_keywords(self, *kargs, **args):
        t = threading.Thread(target=self.gen_keywords)
        t.start()




        
    def open_entry(self, id:int):
        """ Wrappper for opening entry and learning in a separate thread """
        if self.curr_actions['open']: return -2
        self.curr_actions['open'] = True
        FX = Feeder(config=self.config, debug=self.debug, ignore_images=True, gui=True, desktop_notify=False)
        for msg in FX.g_run_entry(id=id):
            self.message_q.append((1, msg,))
        self.changes_q.append((id, 'edit'))
        self.message_q.append((0, 'Done...'))
        self.curr_actions['open'] = False

    def on_activate_result(self, *kargs, **args):
        """ Run in browser and learn """
        if self.load_result_sel() != 0: return -1
        t = threading.Thread(target=self.open_entry, args=(self.sel_result['id'],))
        t.start()





    def on_prefs(self, *kargs):
        """ Run preferences dialog """
        dialog = PreferencesDialog(self, self.config)
        dialog.run()
        if dialog.response == 1:
            new_config = save_config(dialog.result, FEEDEX_CONFIG)
            if new_config == -1: self.update_status(-34, FEEDEX_CONFIG)
            else:
                self.update_status(50, None)
                self.config = parse_config(None, config_str=new_config)
                if self.debug: print(self.config)
        dialog.destroy()



    def on_view_log(self, *kargs):
        """ Shows dialog for reviewing log """
        try:
            with open(self.config.get('log',None)) as logf:
                log_str=logf.read()
        except:
            sys.stderr.write(f'Could not open log file ({self.config.get("log","<< UNKNOWN >>>")})')
            return -1
        dialog = DisplayWindow(self, "Feedex Log", GObject.markup_escape_text(log_str), go_to_end=True)
        dialog.run()
        dialog.destroy()

    def on_show_detailed(self, *kargs):
        """ Shows dialog with entry's detailed technical info """
        rules_str=self.FX.QP.rules_for_entry(self.sel_result.get('id'), to_var=True, print=False)
        det_str=f"""\n\n{self.sel_result.__str__()}\n\nMatched rules:\n{rules_str}\n\n"""
        dialog = DisplayWindow(self, "Technical Details", GObject.markup_escape_text(det_str))
        dialog.run()
        dialog.destroy()

    def on_feed_details(self, *kargs):
        """ Shows feed's techical details in a dialog """
        if self.load_feed_sel() != 0: return -1
        det_str=self.FX.QP.read_feed(self.sel_feed['id'], to_var=True)
        dialog = DisplayWindow(self, "Channel's Technical Details", GObject.markup_escape_text(det_str))
        dialog.run()
        dialog.destroy()

    def on_show_stats(self, *kargs):
        """ Shows dialog with SQLite DB statistics """
        stat_str = self.FX.db_stats(print=False, markup=True)
        dialog = DisplayWindow(self, "Database Statistics", stat_str, width=600, height=500, emblem=self.icons.get('db'))
        dialog.run()
        dialog.destroy()

    def on_show_about(self, *kargs):
        """ Shows 'About...' dialog """
        dialog = AboutDialog(self)
        dialog.run()
        dialog.destroy()

        
    def show_learned_rules(self, *kargs):
        """ Shows learned rules with weights in a separate window """
        self.FX.load_rules(no_limit=True)        
        rule_store = Gtk.ListStore(int, str, str, float, str)
        weight_sum = 0
        for r in self.FX.rules:
            if r[self.rule.get_index('learned')] == 1:
                if r[self.rule.get_index('type')] == 5: qtype = 'Exact'
                else: qtype = 'Stemmed'
                rule_store.append( (r[self.rule.get_index('id')], r[self.rule.get_index('name')], r[self.rule.get_index('string')], r[self.rule.get_index('weight')], qtype) )
                weight_sum += r[self.rule.get_index('weight')]
        rule_count = len(rule_store)
        if rule_count == 0:
            dialog =InfoDialog(None, "Dataset Empty", "There are no learned rules to display")
            dialog.run()
            dialog.destroy()
            return 0            
        avg_weight = weight_sum / rule_count
        header = f'Unique Rule count: <b>{rule_count}</b>, Avg Rule weight: <b>{round(avg_weight,3)}</b>'
        dialog = DisplayRules(self, header, rule_store)
        dialog.run()
        if dialog.response == 1:
            for msg in self.FX.g_delete_learned_rules(): self.update_status(1, msg)
            self.update_status(3, None)
        dialog.destroy()
        self.FX.load_rules(no_limit=False)        






def feedex_run_main_win(**args):
    """ Runs main Gtk loop with main Feedex window"""
    win = FeedexMainWin(**args)
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()
