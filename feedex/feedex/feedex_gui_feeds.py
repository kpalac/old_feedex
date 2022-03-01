# -*- coding: utf-8 -*-
""" GUI classes for FEEDEX """

from feedex_gui_utils import *













class FeedexFeedWindow(Gtk.ScrolledWindow):
    """ Singleton for feed selection in GUI """


    def __init__(self, parent, *args, **kargs):

        # Maint. stuff
        self.parent = parent
        self.config = parent.config
        self.debug = parent.debug

        # GUI init
        Gtk.ScrolledWindow.__init__(self)
        

        # Flags and changeable params
        self.feed_aggr = {}
        self.selected_feed_id = None
        self.selected_feed_ids = []
        self.selected_place = None

        # Container for selected feed
        self.feed = FeedContainerBasic()

        # Feed Tree
        self.feed_store = Gtk.TreeStore(GdkPixbuf.Pixbuf, int, str, str, str, int, str, int, str)
        self.feed_tree = Gtk.TreeView(model=self.feed_store)

        self.feed_tree.append_column( f_col(None, 3, 0, resizable=False, clickable=False, width=16, reorderable=False) )
        self.feed_tree.append_column( f_col(None, 1, 2, clickable=False, reorderable=False, color_col=8) )
        self.feed_selection = self.feed_tree.get_selection()
        self.feed_tree.set_headers_visible(False)
        
        self.feed_tree.set_tooltip_markup("""These are available <b>Places</b>, <b>Channels</b> and <b>Categories</b>
Double-click on a place to quickly load entries  
Double-click on feed or category to filter results according to chosen item (All Channels clears filters)
Right click for more options
Hit <b>Ctrl-F</b> for interactive search""")

        self.feed_selection = self.feed_tree.get_selection()

        self.reload_feeds(load=True)
        self.add(self.feed_tree)

        self.feed_tree.connect("row-activated", self.on_activate_feed)
        self.feed_tree.connect("row-expanded", self._on_feed_expanded)
        self.feed_tree.connect("row-collapsed", self._on_feed_collapsed)
        self.feed_tree.connect("cursor-changed", self.load_selection)
        self.feed_tree.connect("button-press-event", self._rbutton_press, FX_TAB_FEEDS)

        self.feed_tree.set_enable_search(True)
        self.feed_tree.set_search_equal_func(self._quick_find_feed, 2)
 







    def _quick_find_feed(self, model, column, key, rowiter, *args):
        """ Quick find 'equals' function - basically case insensitivity """
        column = args[-1]
        row = model[rowiter]
        if key.lower() in scast(list(row)[column], str, '').lower(): return False

        # Search in child rows.  If one of the rows matches, expand the row so that it will be open in later checks.
        for inner in row.iterchildren():
            if key.lower() in scast(list(inner)[column], str, '').lower():
                self.feed_tree.expand_to_path(row.path)
                return False
        
        return True


    def _rbutton_press(self, widget, event, from_where):
        self.load_selection()
        self.parent._rbutton_press(widget, event, from_where)




    def load_selection(self, *args):
        """ Loads feed from selection to container """
        self.parent.selection_feed.clear()
        self.selected_feed_ids = []

        model, treeiter = self.feed_selection.get_selected()
        if treeiter is None: return -1

        self.selected_feed_id = model[treeiter][1]
        self.selected_place = model[treeiter][5]
        self.selected_feed_ids = None
        ids = model[treeiter][6]

        if self.selected_feed_id > 0:
            for f in self.parent.FX.MC.feeds:
                if self.selected_feed_id == f[self.feed.get_index('id')]:
                    self.parent.selection_feed.populate(f)
                    break

        if ids is not None:
            self.selected_feed_ids = []
            for id in ids.split(','): self.selected_feed_ids.append(int(id.strip()))

        if self.debug in (1,7):
            print(f'selected feed ID: {self.selected_feed_id}')
            print(f'selected place: {self.selected_place}')
            print(f'selected IDs: {self.selected_feed_ids}')







    def _on_feed_expanded(self, *args):
        """ Register expanded rows """
        path = args[-1]
        id = self.feed_store[path][1]
        self.parent.gui_attrs['feeds_expanded'][str(id)] = True

    def _on_feed_collapsed(self, *args):
        """ Register collapsed rows """
        path = args[-1]
        id = self.feed_store[path][1]
        self.parent.gui_attrs['feeds_expanded'][str(id)] = False





    def _feed_store_item(self, feed):
        """ Generates a list of feed fields """
        self.feed.populate(feed)

        title = esc_mu(self.feed.name()) 

        if coalesce(self.feed.get('error'),0) >= self.config.get('error_threshold',5):
            icon = self.parent.icons.get('error', None)
            color = 'red'


        elif coalesce(self.feed.get('deleted'),0) == 1:
            if coalesce(self.feed.get('is_category'),0) == 1:
                icon = self.parent.icons.get(self.feed["id"], self.parent.icons.get('doc',None))
            else:
                icon = self.parent.icons.get(self.feed["id"], self.parent.icons.get('default',None))
            color = self.config.get('gui_deleted_color','grey')


        else:
            icon = self.parent.icons.get(self.feed["id"], self.parent.icons.get('default',None))
            color = None


        if self.feed_aggr.get(self.feed.get("id",-1),0) > 0:
            title = f'<b>({self.feed_aggr.get(self.feed.get("id",-1),0)})  {title}</b>'
        
        if self.feed.get('deleted',0) == 1: ids = None
        else: ids = f'{self.feed.get("id",-1)}'

        return (icon,  self.feed.get("id",-1), title, esc_mu(self.feed.get("subtitle",'')), esc_mu(self.feed.get("link",'')), -1, ids, scast(self.feed.get('deleted',0),int,0), color)







    def _add_underline_func(self, store, treepath, treeiter, *args):
        """ Underline feed or category that we are currently filtering with """
        if self.feed_store[treepath][1] == args[-1]:
            self.feed_store[treepath][2] = f'<u>{self.feed_store[treepath][2]}</u>'


        elif self.feed_store[treepath][1] > 0 \
            and self.feed_store[treepath][2].startswith('<u>') \
            and self.feed_store[treepath][2].endswith('</u>'):
            
            title = self.feed_store[treepath][2]
            title = title.replace('<u>','',1)
            title = title[:-4]
            self.feed_store[treepath][2] = title


    def _add_underline(self, id): self.feed_store.foreach(self._add_underline_func, id)







    def reload_feeds(self, *args, **kargs):
        """ Loads feed data and entry types (inverse id) into list store """

        if kargs.get('load',False): self.parent.FX.load_feeds()

        expanded = []

        # Update store ...
        self.feed_store.clear()

        if self.parent.curr_place == FX_PLACE_LAST: 
            new_row = self.feed_store.append(None, (self.parent.icons.get('new', None), -1, f'<b><u>New</u></b>', '', None, FX_PLACE_LAST, None, 0, None))        
        else: 
            new_row = self.feed_store.append(None, (self.parent.icons.get('new', None), -1, 'New', '', None, FX_PLACE_LAST, None, 0, None))

        if self.parent.curr_place == FX_PLACE_PREV_LAST: 
            self.feed_store.append(new_row, (self.parent.icons.get('calendar', None), -7, '<b><u>Previous Update</u></b>', '', None, FX_PLACE_PREV_LAST, None, 0, None))
        else: 
            self.feed_store.append(new_row, (self.parent.icons.get('calendar', None), -7, 'Previous Update', '', None, FX_PLACE_PREV_LAST, None, 0, None))

        if self.parent.curr_place == FX_PLACE_LAST_HOUR: 
            self.feed_store.append(new_row, (self.parent.icons.get('calendar', None), -2, '<b><u>Last Hour</u></b>', '', None, FX_PLACE_LAST_HOUR, None, 0, None))
        else: 
            self.feed_store.append(new_row, (self.parent.icons.get('calendar', None), -2, 'Last Hour', '', None, FX_PLACE_LAST_HOUR, None, 0, None))

        if self.parent.curr_place == FX_PLACE_TODAY: 
            self.feed_store.append(new_row, (self.parent.icons.get('calendar', None), -3, '<b><u>Today</u></b>', '', None, FX_PLACE_TODAY, None, 0, None))
        else: 
            self.feed_store.append(new_row, (self.parent.icons.get('calendar', None), -3, 'Today', '', None, FX_PLACE_TODAY, None, 0, None))
 
        if self.parent.curr_place == FX_PLACE_LAST_WEEK: 
            self.feed_store.append(new_row, (self.parent.icons.get('calendar', None), -4, '<b><u>Last Week</u></b>', '', None, FX_PLACE_LAST_WEEK, None, 0, None))
        else: 
            self.feed_store.append(new_row, (self.parent.icons.get('calendar', None), -4, 'This Week', '', None, FX_PLACE_LAST_WEEK, None, 0, None))
 
        if self.parent.curr_place == FX_PLACE_LAST_MONTH: 
            self.feed_store.append(new_row, (self.parent.icons.get('calendar', None), -5, '<b><u>Last Month</u></b>', '', None, FX_PLACE_LAST_MONTH, None, 0, None))
        else: 
            self.feed_store.append(new_row, (self.parent.icons.get('calendar', None), -5, 'This Month', '', None, FX_PLACE_LAST_MONTH, None, 0, None))
 
        if self.parent.curr_place == FX_PLACE_LAST_QUARTER: 
            self.feed_store.append(new_row, (self.parent.icons.get('calendar', None), -6, '<b><u>Last Quarter</u></b>', '', None, FX_PLACE_LAST_QUARTER, None, 0, None))
        else: 
            self.feed_store.append(new_row, (self.parent.icons.get('calendar', None), -6, 'This Quarter', '', None, FX_PLACE_LAST_QUARTER, None, 0, None))
 



        if self.parent.gui_attrs.get('feeds_expanded',{}).get('-1',False): expanded.append(new_row)

        self.feed_store.append(None, (None, -99, None, None, None, -1, None, 0, None))

        for c in self.parent.FX.MC.feeds:

            if c[self.feed.get_index('is_category')] != 1: continue
            if c[self.feed.get_index('deleted')] == 1: continue

            id = scast(c[self.feed.get_index('id')], int, 0)
            name = esc_mu(scast(c[self.feed.get_index('name')], str, ''))
            match_count = self.feed_aggr.get(id,0)
            ids=f'{id}'
            for f in self.parent.FX.MC.feeds:
                self.feed.populate(f)
                if self.feed['parent_id'] == id and self.feed['is_category'] != 1 and self.feed['deleted'] != 1:
                    match_count += self.feed_aggr.get(self.feed['id'],0)
                    ids = f'{ids},{self.feed.get("id","-1")}'

            if match_count > 0:
                name = f'<b>({match_count})  {name}</b>'
            else:
                name = f'{name}'
            subtitle = esc_mu(f'{scast(c[self.feed.get_index("subtitle")], str, "")}')
            icon = self.parent.icons.get('doc',None)

            cat_row = self.feed_store.append(None, (icon, id, name, subtitle, None, -1, ids, 0, None)) 

            for f in self.parent.FX.MC.feeds:
                self.feed.populate(f)
                if self.feed['parent_id'] == id and self.feed['is_category'] != 1 and self.feed['deleted'] != 1:
                    self.feed_store.append(cat_row, self._feed_store_item(self.feed))
            if self.parent.gui_attrs.get('feeds_expanded',{}).get(str(id),False): expanded.append(cat_row)
        
        
        self.feed_store.append(None, (None, -99, None, None, None, -1, None, 0, None))

        all_row = self.feed_store.append(None, (None, -20, 'All Channels ...', '', None, FX_PLACE_ALL_CHANNELS, None, 0, None))
        for f in self.parent.FX.MC.feeds:
            self.feed.populate(f)
            if self.feed['deleted'] != 1 and self.feed['is_category'] != 1:
                self.feed_store.append(all_row, self._feed_store_item(self.feed))
        if self.parent.gui_attrs.get('feeds_expanded',{}).get('-20',False): expanded.append(all_row)

        self.feed_store.append(None, (None, -99, None, None, None, -1, None, 0, None))

        if self.parent.curr_place == 'trash_bin': deleted_row = self.feed_store.append(None, (self.parent.icons.get('trash', None), -30, '<b>Trash</b>', '', None, FX_PLACE_TRASH_BIN, None, 1, None))            
        else: deleted_row = self.feed_store.append(None, (self.parent.icons.get('trash', None), -30, 'Trash', '', None, FX_PLACE_TRASH_BIN, None, 1, None)) 
        
        for f in self.parent.FX.MC.feeds:
            self.feed.populate(f)
            if self.feed['deleted'] == 1:
                row = self.feed_store.append(deleted_row, self._feed_store_item(self.feed))

        if self.parent.gui_attrs.get('feeds_expanded',{}).get('-30',False): expanded.append(deleted_row)

        for e in expanded:
            self.feed_tree.expand_row(self.feed_store.get_path(e), False)
                   







    def on_activate_feed(self, *args):
        """ Feed or category activate - change filter on entries """   
        if self.selected_place == FX_PLACE_ALL_CHANNELS:
            if self.parent.upper_pages[self.parent.curr_upper].type in (FX_TAB_PLACES, FX_TAB_SEARCH, FX_TAB_CONTEXTS, FX_TAB_SIMILAR):
                self.parent.upper_pages[self.parent.curr_upper].create_list(False, (), True)
                self.parent.upper_pages[self.parent.curr_upper].feed_filter_id = 0
                self._add_underline(0)

        elif self.selected_place > 0:
            
            self.parent.curr_place = self.selected_place
            self.parent.upper_pages[0].query(self.selected_place, {})
            self.parent.upper_notebook.set_current_page(0)

        elif self.selected_feed_ids is not None:
            if self.parent.upper_pages[self.parent.curr_upper].type in (FX_TAB_PLACES, FX_TAB_SEARCH, FX_TAB_CONTEXTS, FX_TAB_SIMILAR):

                if self.selected_feed_id == self.parent.upper_pages[self.parent.curr_upper].feed_filter_id:
                    self.parent.upper_pages[self.parent.curr_upper].create_list(False, (), True)
                    self.parent.upper_pages[self.parent.curr_upper].feed_filter_id = 0
                    self._add_underline(0)
                else:
                    self.parent.upper_pages[self.parent.curr_upper].create_list(False, self.selected_feed_ids, False )
                    self.parent.upper_pages[self.parent.curr_upper].feed_filter_id = self.selected_feed_id
                    self._add_underline(self.selected_feed_id)


