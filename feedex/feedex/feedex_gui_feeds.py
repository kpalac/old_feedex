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
        self.processing_flag = False
        self.feed_aggr = {}
        self.selected_feed_id = -99
        self.selected_feed_ids = []

        # Container for selected feed
        self.feed = SQLContainer('feeds', FEEDS_SQL_TABLE, replace_nones=True)

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
Right click for more options""")

        self.feed_selection = self.feed_tree.get_selection()

        self.reload_feeds(load=True)
        self.add(self.feed_tree)

        self.feed_tree.connect("row-activated", self.on_activate_feed)
        self.feed_tree.connect("row-expanded", self._on_feed_expanded)
        self.feed_tree.connect("row-collapsed", self._on_feed_collapsed)
        self.feed_tree.connect("cursor-changed", self.load_selection)
        self.feed_tree.connect("button-press-event", self._rbutton_press, 'feeds')
 










    def _rbutton_press(self, widget, event, from_where):
        self.load_selection()
        self.parent._rbutton_press(widget, event, from_where)




    def load_selection(self, *args):
        """ Loads feed from selection to container """
        self.parent.selection_feed.clear()
        self.selected_feed_ids = []

        model, treeiter = self.feed_selection.get_selected()
        if treeiter is None: return -1
        ids = model[treeiter][6]
        self.selected_feed_id = model[treeiter][1]

        if self.selected_feed_id > 0:
            
            if ids != 'deleted':
                for idd in ids.split(','): 
                    self.selected_feed_ids.append(scast(idd, int, -1))
            else: self.selected_feed_ids = ids

            for f in self.parent.FX.feeds:
                if self.selected_feed_id == f[self.feed.get_index('id')]:
                    self.parent.selection_feed.populate(f)

        else:
            self.selected_feed_ids = ids

        if self.debug: 
            print(f'selected feed ID: {self.selected_feed_id}')
            print(f'additional selected params: {self.selected_feed_ids}')







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

        title = feed_name(self.feed) 

        if self.feed.get('error',0) >= self.config.get('error_threshold',5):
            icon = self.parent.icons.get('error', None)
            color = 'red'
        elif self.feed.get('deleted',0) == 1:
            icon = self.parent.icons.get(self.feed["id"], self.parent.icons.get('default',None))
            color = self.config.get('gui_deleted_color','grey')            
        else:
            icon = self.parent.icons.get(self.feed["id"], self.parent.icons.get('default',None))
            color = None

        if self.feed_aggr.get(self.feed.get("id",-1),0) > 0:
            title = f'<b>({self.feed_aggr.get(self.feed.get("id",-1),0)})  {title}</b>'
        
        if self.feed.get('deleted',0) == 1: ids = 'deleted'
        else: ids = f'{self.feed.get("id",-1)}'

        return (icon,  self.feed.get("id",-1), title, self.feed.get("subtitle",''), self.feed.get("link",''), 0, ids, scast(self.feed.get('deleted',0),int,0), color)







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

        if self.parent.curr_place == 'last': new_row = self.feed_store.append(None, (self.parent.icons.get('new', None), -1, f'<b><u>New</u></b>', '', None, 1, 'last', 0, None))        
        else: new_row = self.feed_store.append(None, (self.parent.icons.get('new', None), -1, 'New', '', None, 1, 'last', 0, None))

        if self.parent.curr_place == 'last_hour': self.feed_store.append(new_row, (self.parent.icons.get('calendar', None), -2, '<b><u>Last Hour</u></b>', '', None, 1, 'last_hour', 0, None))
        else: self.feed_store.append(new_row, (self.parent.icons.get('calendar', None), -2, 'Last Hour', '', None, 1, 'last_hour', 0, None))

        if self.parent.curr_place == 'today': self.feed_store.append(new_row, (self.parent.icons.get('calendar', None), -3, '<b><u>Today</u></b>', '', None, 1, 'today', 0, None))
        else: self.feed_store.append(new_row, (self.parent.icons.get('calendar', None), -3, 'Today', '', None, 1, 'today', 0, None))
 
        if self.parent.curr_place == 'last_week': self.feed_store.append(new_row, (self.parent.icons.get('calendar', None), -4, '<b><u>Last Week</u></b>', '', None, 1, 'last_week', 0, None))
        else: self.feed_store.append(new_row, (self.parent.icons.get('calendar', None), -4, 'This Week', '', None, 1, 'last_week', 0, None))
 
        if self.parent.curr_place == 'last_month': self.feed_store.append(new_row, (self.parent.icons.get('calendar', None), -5, '<b><u>Last Month</u></b>', '', None, 1, 'last_month', 0, None))
        else: self.feed_store.append(new_row, (self.parent.icons.get('calendar', None), -5, 'This Month', '', None, 1, 'last_month', 0, None))
 
        if self.parent.curr_place == 'last_quarter': self.feed_store.append(new_row, (self.parent.icons.get('calendar', None), -6, '<b><u>Last Quarter</u></b>', '', None, 1, 'last_quarter', 0, None))
        else: self.feed_store.append(new_row, (self.parent.icons.get('calendar', None), -6, 'This Quarter', '', None, 1, 'last_quarter', 0, None))
 
# The year bit takes very long, so it is better not to show it 
#        if self.parent.curr_place == 'last_year': self.feed_store.append(new_row, (self.parent.icons.get('calendar', None), -7, '<b><u>This Year</u></b>', '', None, 1, 'last_year', 0, None))
#        else: self.feed_store.append(new_row, (self.parent.icons.get('calendar', None), -7, 'This Year', '', None, 1, 'last_year', 0, None))
 
        if self.parent.gui_attrs.get('feeds_expanded',{}).get('-1',False): expanded.append(new_row)

        self.feed_store.append(None, (None, -99, None, '', None, 1, '-99', 0, None))

        for c in self.parent.FX.feeds:

            if c[self.feed.get_index('is_category')] != 1: continue
            if c[self.feed.get_index('deleted')] == 1: continue

            id = scast(c[self.feed.get_index('id')], int, 0)
            name = GObject.markup_escape_text(scast(c[self.feed.get_index('name')], str, ''))
            match_count = self.feed_aggr.get(id,0)
            ids=f'{id}'
            for f in self.parent.FX.feeds:
                self.feed.populate(f)
                if self.feed['parent_id'] == id and self.feed['is_category'] != 1 and self.feed['deleted'] != 1:
                    match_count += self.feed_aggr.get(self.feed['id'],0)
                    ids = f'{ids},{self.feed.get("id","-1")}'

            if match_count > 0:
                name = f'<b>({match_count})  {name}</b>'
            else:
                name = f'{name}'
            subtitle = GObject.markup_escape_text(f'{scast(c[self.feed.get_index("subtitle")], str, "")}')
            icon = self.parent.icons.get('doc',None)

            cat_row = self.feed_store.append(None, (icon, id, name, subtitle, None, 1, ids, 0, None)) 

            for f in self.parent.FX.feeds:
                self.feed.populate(f)
                if self.feed['parent_id'] == id and self.feed['is_category'] != 1 and self.feed['deleted'] != 1:
                    self.feed_store.append(cat_row, self._feed_store_item(self.feed))
            if self.parent.gui_attrs.get('feeds_expanded',{}).get(str(id),False): expanded.append(cat_row)
        
        
        self.feed_store.append(None, (None, -99, None, '', None, 1, '-99', 0, None))

        all_row = self.feed_store.append(None, (None, -10, 'All Channels ...', '', None, 1, 'all', 0, None))
        for f in self.parent.FX.feeds:
            self.feed.populate(f)
            if self.feed['deleted'] != 1 and self.feed['is_category'] != 1:
                self.feed_store.append(all_row, self._feed_store_item(self.feed))
        if self.parent.gui_attrs.get('feeds_expanded',{}).get('-10',False): expanded.append(all_row)

        self.feed_store.append(None, (None, -99, None, '', None, 1, '-99', 0, None))

        if self.parent.curr_place == 'trash_bin': deleted_row = self.feed_store.append(None, (self.parent.icons.get('trash', None), -11, '<b>Trash</b>', '', None, 1, 'trash_bin', 1, None))            
        else: deleted_row = self.feed_store.append(None, (self.parent.icons.get('trash', None), -11, 'Trash', '', None, 1, 'trash_bin', 1, None)) 
        
        for f in self.parent.FX.feeds:
            self.feed.populate(f)
            if self.feed['deleted'] == 1:
                row = self.feed_store.append(deleted_row, self._feed_store_item(self.feed))

        if self.parent.gui_attrs.get('feeds_expanded',{}).get('-11',False): expanded.append(deleted_row)

        for e in expanded:
            self.feed_tree.expand_row(self.feed_store.get_path(e), False)
                   







    def on_activate_feed(self, *args):
        """ Feed or category activate - change filter on entries """
        
        if self.selected_feed_id == -99: return 0

        if self.selected_feed_id < 0:

            if self.selected_feed_ids == 'all':
                if self.parent.upper_pages[self.parent.curr_upper].type in ('places','search','contexts','similar','feed'):
                    self.parent.upper_pages[self.parent.curr_upper].create_list(False, (), True)
                    self.parent.upper_pages[self.parent.curr_upper].feed_filter_id = 0
                    self._add_underline(0)
            else:
                self.parent.curr_place = self.selected_feed_ids
                self.parent.upper_pages[0].query(None, self.selected_feed_ids)
                self.parent.upper_notebook.set_current_page(0)

        elif self.selected_feed_id > 0 and self.selected_feed_ids != 'deleted':
            if self.parent.upper_pages[self.parent.curr_upper].type in ('places','search','contexts','similar','feed'):
                self.parent.upper_pages[self.parent.curr_upper].create_list(False, self.selected_feed_ids, False )
                self.parent.upper_pages[self.parent.curr_upper].feed_filter_id = self.selected_feed_id
                self._add_underline(self.selected_feed_id)



