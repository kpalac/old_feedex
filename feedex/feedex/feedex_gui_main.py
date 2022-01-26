# -*- coding: utf-8 -*-
""" GUI classes for FEEDEX """


from feedex_gui_utils import *









class FeedexMainWin(Gtk.Window):
    """ Main window for Feedex """

    def __init__(self, feedex_main_container, **kargs):
    
        #Maint. stuff
        if isinstance(feedex_main_container, FeedexMainDataContainer): self.MC = feedex_main_container
        else: raise FeedexTypeError('feedex_main_container should be an instance of FeedexMainDataContainer class!')

        self.config = kargs.get('config', DEFAULT_CONFIG)
        self.debug = kargs.get('debug',False)

        self.gui_attrs = validate_gui_attrs( load_json(FEEDEX_GUI_ATTR_CACHE, {}) )

        # Timer related ...
        self.sec_frac_counter = 0
        self.sec_counter = 0
        self.minute_counter = 0

        self.today = 0
        self._time()


        # Main DB interface - init and check for lock and/or DB errors
        self.FX = Feeder(self.MC, config=self.config, debug=self.debug, ignore_images=self.config.get('ignore_images', False), gui=True, load_icons=True, main_thread=True)

        # Default fields for edit and new items
        self.default_search_filters = self.gui_attrs.get('default_search_filters', FEEDEX_GUI_DEFAULT_SEARCH_FIELDS).copy()

        self.new_feed_url = FeedContainer(self.FX)
        self.new_entry = EntryContainer(self.FX)
        self.new_category = FeedContainer(self.FX)
        self.new_feed = FeedContainer(self.FX)
        self.new_rule = RuleContainer(self.FX)

        self.date_store_added = []

        # Selection references
        self.selection_res = ResultContainer(replace_nones=True)
        self.selection_term = ''
        self.selection_feed = FeedContainerBasic(replace_nones=True)
        self.selection_rule = RuleContainerBasic(replace_nones=True)
        self.selection_time_series = {}


        if self.FX.locked(timeout=2):
            dialog = YesNoDialog(None, "Feedex: Database is Locked", "<b>Database is Locked! Proceed and unlock?</b>", 
                                        subtitle="Another instance can be performing operations on Database or Feedex did not close properly last time. Proceed anyway?")
            dialog.run()
            if dialog.response == 1:
                self.FX.unlock()
                dialog.destroy()
            else:
                dialog.destroy()
                self.FX.close()
                sys.exit(4)
    
        self.FX.unlock()
        if self.FX.db_status != 0:
            dialog = InfoDialog(None, "Feedex: Database Error!", gui_msg(self.FX.db_status), subtitle="Application could not be started! I am sorry for inconvenience :(")
            dialog.run()
            dialog.destroy()
            self.FX.close()
            sys.exit(2)


        # Image handling
        self.icons = get_icons(self.FX.MC.feeds, self.FX.MC.icons)

        self.download_errors = [] #Error list to prevent multiple downloads from faulty links

        # Display queues for threading
        self.message_q = [(0, None)]
        self.images_q = []
        self.entry_changes_q = []

        # Actions and Places
        self.curr_actions = {'fetch':False, 'feed_update':False, 'edit_entry':False}
        self.prev_actions = self.curr_actions.copy()
        self.curr_place = 'last'

        # Start threading and main window
        Gdk.threads_init()
        Gtk.Window.__init__(self, title=f"Feedex {FEEDEX_VERSION}")
        self.lock = threading.Lock()

        self.set_border_width(10)
        self.set_resizable(True)
        self.set_position(Gtk.WindowPosition.CENTER)
        self.set_icon(self.icons['main'])
        self.set_default_size(self.gui_attrs.get('win_width'), self.gui_attrs.get('win_height'))
        


        GLib.timeout_add(interval=250, function=self._on_timer)




        # Lower status bar
        self.status_bar = f_label('', justify='left', wrap=True, markup=True, selectable=True, ellipsize='end') 
        self.status_spinner = Gtk.Spinner()
        lstatus_box = Gtk.Box()
        lstatus_box.set_orientation(Gtk.Orientation.HORIZONTAL)
        lstatus_box.set_homogeneous(False)
        lstatus_box.pack_start(self.status_spinner, False, False, 10)
        lstatus_box.pack_start(self.status_bar, False, False, 10)


        # Main Menu
        self.main_menu = Gtk.Menu()
        self.main_menu.append( f_menu_item(1, 'Preferences', self.on_prefs, icon='preferences-system-symbolic') )
        self.main_menu.append( f_menu_item(1, 'Rules', self.add_tab, kargs={'type':'rules'}, icon='view-list-compact-symbolic', tooltip='Open a new tap showing Saved Rules') )
        self.main_menu.append( f_menu_item(0, 'SEPARATOR', None) )
        self.main_menu.append( f_menu_item(1, 'Export Feed data to JSON', self.export_feeds, icon='go-next-symbolic'))  
        self.main_menu.append( f_menu_item(1, 'Import Feed data from JSON', self.import_feeds, icon='go-previous-symbolic'))  
        self.main_menu.append( f_menu_item(1, 'Export Rules to JSON', self.export_rules, icon='go-next-symbolic'))  
        self.main_menu.append( f_menu_item(1, 'Import Rules data from JSON', self.import_rules, icon='go-previous-symbolic'))  
        self.main_menu.append( f_menu_item(0, 'SEPARATOR', None) )
        self.main_menu.append( f_menu_item(1, 'Database statistics', self.on_show_stats, icon='drive-harddisk-symbolic') )
        self.main_menu.append( f_menu_item(1, 'View log', self.on_view_log, icon='text-x-generic-symbolic') )
        self.main_menu.append( f_menu_item(0, 'SEPARATOR', None) )
        self.main_menu.append( f_menu_item(1, 'About Feedex...', self.on_show_about, icon='help-about-symbolic') )
        self.main_menu.show_all()

        # Search Menu
        self.search_menu = Gtk.Menu()
        self.search_menu.append( f_menu_item(1, 'Search', self.add_tab, kargs={'type':'search'}, icon='edit-find-symbolic', tooltip='Search entries'))  
        self.search_menu.append( f_menu_item(1, 'Show Contexts for a Term', self.add_tab, kargs={'type':'contexts'}, icon='view-list-symbolic', tooltip='Search for Term Contexts'))  
        self.search_menu.append( f_menu_item(1, 'Search for Related Terms', self.add_tab, kargs={'type':'terms'}, icon='emblem-shared-symbolic', tooltip='Search for Related Terms from read/opened entries'))  
        self.search_menu.append( f_menu_item(1, 'Show Time Series for a Term', self.add_tab, kargs={'type':'time_series'}, icon='office-calendar-symbolic', tooltip='Generate time series plot'))  
        self.search_menu.show_all()

        # Header bar
        hbar = Gtk.HeaderBar()
        hbar.set_show_close_button(True)
        hbar.props.title = f"Feedex {FEEDEX_VERSION}"
        
        if self.config.get('profile_name') is not None:
            hbar.props.subtitle = f"{self.config.get('profile_name')}"
        
        hbar_button_menu = Gtk.MenuButton()
        hbar_button_menu.set_popup(self.main_menu)
        hbar_button_menu.set_tooltip_markup("""Main Menu""")
        hbar_button_menu_icon = Gtk.Image.new_from_icon_name('open-menu-symbolic', Gtk.IconSize.BUTTON)
        hbar_button_menu.add(hbar_button_menu_icon)         
        self.set_titlebar(hbar)

        self.button_feeds_new        = f_button(None,'list-add-symbolic', connect=self.on_add_from_url, tooltip='<b>Add Channel</b> from URL')
        self.button_feeds_download   = f_button(None,'application-rss+xml-symbolic', connect=self.on_load_news_all, tooltip='<b>Fetch</b> news for all Channels')
       
        self.button_search = Gtk.MenuButton()
        self.button_search.set_popup(self.search_menu)
        self.button_search.set_tooltip_markup("""Open a new tab for Searches...""")
        button_search_icon = Gtk.Image.new_from_icon_name('edit-find-symbolic', Gtk.IconSize.BUTTON)
        self.button_search.add(button_search_icon)

    

        # Upper notebook stuff 
        self.rules_tab = -1
        self.curr_upper = 0

        self.upper_pages = []
        
        self.upper_notebook = Gtk.Notebook()
        self.upper_notebook.set_scrollable(True)
 
        self.upper_notebook.connect('switch-page', self._on_unb_changed)





        # Lower notebook
        prev_images_box = Gtk.ScrolledWindow()
        prev_images_box.set_policy(Gtk.PolicyType.AUTOMATIC, Gtk.PolicyType.NEVER)
        self.prev_images = Gtk.Box()
        self.prev_images.set_orientation(Gtk.Orientation.HORIZONTAL)
        self.prev_images.set_homogeneous(False)
        prev_images_box.add(self.prev_images)

        self.prev_title = f_label(None, justify='center', selectable=True, wrap=True, markup=True)
        self.prev_auth  = f_label(None, justify='center', selectable=True, wrap=True, markup=True)
        self.prev_cat   = f_label(None, justify='center', selectable=True, wrap=True, markup=True)
        self.prev_desc  = f_label(None, justify='left', selectable=True, wrap=True, markup=True)
        self.prev_text  = f_label(None, justify='left', selectable=True, wrap=True, markup=True)
        self.prev_enc   = f_label(None, justify='center', selectable=True, wrap=True, markup=True)
        stats_box = Gtk.HBox(homogeneous=False)
        self.prev_stats  = f_label(None,selectable=True, wrap=True, markup=True)
        stats_box.pack_start(self.prev_stats, False, False, 1)

        preview_box       = f_pack_page((prev_images_box, self.prev_title, self.prev_auth, self.prev_cat, self.prev_desc, self.prev_text, self.prev_enc, stats_box))


        # Feed section
        self.feed_win = FeedexFeedWindow(self)

        # Build layout
        self.Grid = Gtk.Grid()
        self.add(self.Grid)
        self.Grid.set_column_spacing(5)
        self.Grid.set_row_spacing(5)
        self.Grid.set_column_homogeneous(True)
        self.Grid.set_row_homogeneous(True)
        
        main_box = Gtk.VBox(homogeneous=False)
 
        self.div_horiz = Gtk.VPaned()
        self.div_vert = Gtk.HPaned()
        self.div_horiz.set_position(self.gui_attrs['div_horiz'])
        self.div_vert.set_position(self.gui_attrs['div_vert'])


        self.div_horiz.pack1(self.upper_notebook, resize=True, shrink=True)
        self.div_horiz.pack2(preview_box, resize=True, shrink=True)

        self.div_vert.pack1(self.feed_win, resize=True, shrink=True)
        self.div_vert.pack2(self.div_horiz, resize=True, shrink=True)

        main_box.add(self.div_vert)

        self.Grid.attach(main_box, 1, 1, 31, 18)
        self.Grid.attach(lstatus_box, 1, 19, 31, 1)

        hbar.pack_start(self.button_feeds_download)
        hbar.pack_start(self.button_feeds_new)
        hbar.pack_start(self.button_search)
        
        hbar.pack_end(hbar_button_menu)
        
        self.connect("destroy", self._on_close)
        self.connect("key-press-event", self._on_key_press)

        self.add_tab({'type':'places'})
        self.upper_pages[0].query('startup',{})
        self.startup_decor()
 

    def _on_close(self, *args):
        self.FX.close()
        self._save_gui_attrs()

    def _save_gui_attrs(self, *args):

        #(self.gui_attrs['win_width'], self.gui_attrs['win_height']) = self.get_size()

        self.gui_attrs['div_horiz'] = self.div_horiz.get_position()
        self.gui_attrs['div_vert'] = self.div_vert.get_position()

        err = save_json(FEEDEX_GUI_ATTR_CACHE, self.gui_attrs)
        if self.debug: 
            if err == 0: print('Saved GUI attributes: ', self.gui_attrs)





    def _housekeeping(self): housekeeping(self.config.get('gui_clear_cache',30), self.MC.db_hash, debug=self.debug)
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




    def _on_key_press(self, widget, event):
        """ When keyboard is used ... """
        key = event.keyval
        key_name = Gdk.keyval_name(key)
        state = event.state
        ctrl = (state & Gdk.ModifierType.CONTROL_MASK)
        if ctrl and key_name == self.config.get('gui_key_search','s'): self.add_tab({'type':'search'}) 
        elif ctrl and key_name == self.config.get('gui_key_new_entry','n'): self.on_edit_entry(True)
        elif ctrl and key_name == self.config.get('gui_key_new_rule','r'): self.on_edit_rule(True)







    def _rbutton_press(self, widget, event, from_where):
        """ Button press event catcher and menu construction"""
        if event.button == 3:
            menu = None

            if from_where in ('results', 'contexts'):
                menu = Gtk.Menu()
                
                if not (self.curr_upper == 0 and self.curr_place == 'trash_bin'):
                    menu.append( f_menu_item(1, 'Add Entry', self.on_edit_entry, args=(True,), icon='list-add-symbolic') )

                if self.selection_res['id'] is not None:

                    if (not self.curr_actions['edit_entry']) and self.selection_res['deleted'] != 1 and not (self.curr_upper == 0 and self.curr_place == 'trash_bin'):

                        menu.append( f_menu_item(1, 'Mark as Read (+1)', self.on_mark_recalc, args=('read',), icon='bookmark-new-symbolic', tooltip="Number of reads if counted towards this entry keyword's weight when ranking incoming articles ") )
                        menu.append( f_menu_item(1, 'Mark as Unread', self.on_mark, args=('unread',), icon='edit-redo-rtl-symbolic', tooltip="Unread document does not contriute to ranking rules") )
                        menu.append( f_menu_item(1, 'Mark as Unimportant', self.on_mark_recalc, args=('unimp',), icon='edit-redo-rtl-symbolic', tooltip="Mark this as unimportant and learn negative rules") )

                        flag_menu = Gtk.Menu()
                        flag_menu.append( f_menu_item(1, self.config.get('gui_flag_1_name','Flag 1'), self.on_mark, args=(1,), color=self.config.get('gui_flag_1_color','blue') ) )
                        flag_menu.append( f_menu_item(1, self.config.get('gui_flag_2_name','Flag 2'), self.on_mark, args=(2,), color=self.config.get('gui_flag_2_color','blue') ) )
                        flag_menu.append( f_menu_item(1, self.config.get('gui_flag_3_name','Flag 3'), self.on_mark, args=(3,), color=self.config.get('gui_flag_3_color','blue') ) )
                        flag_menu.append( f_menu_item(1, self.config.get('gui_flag_4_name','Flag 4'), self.on_mark, args=(4,), color=self.config.get('gui_flag_4_color','blue') ) )
                        flag_menu.append( f_menu_item(1, self.config.get('gui_flag_5_name','Flag 5'), self.on_mark, args=(5,), color=self.config.get('gui_flag_5_color','blue') ) )

                        menu.append( f_menu_item(3, 'Flag Entry', flag_menu, icon='marker-symbolic', tooltip="Flag is a user's marker/bookmark for a given article independent of ranking\n<i>You can setup different flag colors in Preferences</i>") )
                        menu.append( f_menu_item(1, 'Unflag Entry', self.on_mark, args=('unflag',), icon='edit-redo-rtl-symbolic', tooltip="Flag is a user's marker/bookmark for a given article independent of ranking") )
                        menu.append( f_menu_item(1, 'Edit Entry', self.on_edit_entry, args=(False,), icon='edit-symbolic') )
                        

                    if self.selection_res['deleted'] == 1: 
                        menu.append( f_menu_item(1, 'Restore', self.on_restore_entry, icon='edit-redo-rtl-symbolic') )
                        menu.append( f_menu_item(1, 'Delete permanently', self.on_del_entry, icon='edit-delete-symbolic') )
                    else: menu.append( f_menu_item(1, 'Delete', self.on_del_entry, icon='edit-delete-symbolic') )
                           
                    similar_menu = Gtk.Menu()
                    similar_menu.append( f_menu_item(1, 'Last update', self.on_find_similar, args=('last',) ) )
                    similar_menu.append( f_menu_item(1, 'Today', self.on_find_similar, args=('today',) ) )
                    similar_menu.append( f_menu_item(1, 'Last Week', self.on_find_similar, args=('last_week',) ) )
                    similar_menu.append( f_menu_item(1, 'Last Month', self.on_find_similar, args=('last_month',) ) )
                    similar_menu.append( f_menu_item(1, 'Last Quarter', self.on_find_similar, args=('last_quarter',) ) )
                    similar_menu.append( f_menu_item(1, 'Last Year', self.on_find_similar, args=('last_year',) ) )
                    similar_menu.append( f_menu_item(1, 'Select Range...', self.on_find_similar, args=('range',) ) )
                        
                    menu.append( f_menu_item(0, 'SEPARATOR', None) )
                    menu.append( f_menu_item(3, 'Find Similar Entries', similar_menu, icon='edit-copy-symbolic', tooltip="Find Entries similar to the one selected with current date filters applied") )
                    menu.append( f_menu_item(1, 'Show Keywords for Entry', self.on_show_keywords, icon='zoom-in-symbolic') )
                    if self.debug: menu.append( f_menu_item(1, 'Details...', self.on_show_detailed, icon='zoom-in-symbolic', tooltip="Show all entry's technical data") )
                
                menu.append( f_menu_item(0, 'SEPARATOR', None) )
                menu.append( f_menu_item(1, 'Save results to CSV', self.export_results_csv, icon='x-office-spreadsheet-symbolic', tooltip='Save results from current tab'))  

                if self.upper_pages[self.curr_upper].type in ('search', 'contexts'):
                    menu.append( f_menu_item(0, 'SEPARATOR', None) )
                    menu.append( f_menu_item(1, 'Clear Search History', self.on_clear_history, icon='edit-clear-symbolic') )
                
                if self.curr_upper == 0 and self.curr_place == 'trash_bin': menu.append( f_menu_item(1, 'Empty Trash', self.on_empty_trash, icon='edit-delete-symbolic') ) 
                menu.append( f_menu_item(0, 'SEPARATOR', None) )
                menu.append( f_menu_item(1, 'Save layout', self.upper_pages[self.curr_upper].save_layout, icon='view-column-symbolic', tooltip='Save column layout and sizing for current tab.\nIt will be used as default in the future' ) )
                if self.upper_pages[self.curr_upper].type in ('search', 'contexts'):
                    menu.append( f_menu_item(1, 'Save filters', self.upper_pages[self.curr_upper].save_filters, icon='gtk-find-and-replace', tooltip='Save current search filters as defaults for future' ) )


            elif from_where == 'rules':
                menu = Gtk.Menu()
                menu.append( f_menu_item(1, 'Add Rule', self.on_edit_rule, args=(True,), icon='list-add-symbolic') )
                if self.selection_rule['id'] is not None:
                    menu.append( f_menu_item(1, 'Edit Rule', self.on_edit_rule, args=(False,), icon='edit-symbolic') )
                    menu.append( f_menu_item(1, 'Delete Rule', self.on_del_rule, icon='edit-delete-symbolic') )
                menu.append( f_menu_item(1, 'Clear Search History', self.on_clear_history, icon='edit-clear-symbolic') )
                menu.append( f_menu_item(1, 'Show Learned Rules', self.show_learned_rules, icon='zoom-in-symbolic', tooltip='Display rules learned from User\'s habits along with weights') )
                menu.append( f_menu_item(1, 'Save layout', self.upper_pages[self.curr_upper].save_layout, icon='view-column-symbolic', tooltip='Save column layout and sizing for current tab.\nIt will be used as default in the future' ) )

            elif from_where  == 'terms':            
                menu = Gtk.Menu()
                if self.selection_term not in (None,''):
                    menu.append( f_menu_item(1, 'Search for this Term', self.add_tab, kargs={'type':'search', 'phrase':self.selection_term}, icon='edit-find-symbolic'))  
                    menu.append( f_menu_item(1, 'Show this Term\'s Contexts', self.add_tab, kargs={'type':'contexts', 'phrase':self.selection_term}, icon='view-list-symbolic'))  
                    menu.append( f_menu_item(1, 'Show Terms related to this Term', self.add_tab, kargs={'type':'terms', 'phrase':self.selection_term}, icon='emblem-shared-symbolic'))  
                    menu.append( f_menu_item(1, 'Show Time Series for this Term', self.add_tab,kargs={'type':'time_series', 'phrase':self.selection_term}, icon='office-calendar-symbolic'))  
                    menu.append( f_menu_item(0, 'SEPARATOR', None) )
                
                menu.append( f_menu_item(1, 'Save results to CSV', self.export_results_csv, icon='x-office-spreadsheet-symbolic', tooltip='Save results from current tab'))  
                menu.append( f_menu_item(0, 'SEPARATOR', None) )
                menu.append( f_menu_item(1, 'Clear Search History', self.on_clear_history, icon='edit-clear-symbolic') )
                menu.append( f_menu_item(0, 'SEPARATOR', None) )
                menu.append( f_menu_item(1, 'Save layout', self.upper_pages[self.curr_upper].save_layout, icon='view-column-symbolic', tooltip='Save column layout and sizing for current tab.\nIt will be used as default in the future' ) )

            elif from_where  == 'time_series':            
                menu = Gtk.Menu()
                if self.selection_time_series not in (None, {}):
                    menu.append( f_menu_item(1, 'Search this Time Range', self.add_tab, kargs={'type':'search', 'date_range':True}, icon='edit-find-symbolic'))  
                    menu.append( f_menu_item(0, 'SEPARATOR', None) )  
                menu.append( f_menu_item(1, 'Save results to CSV', self.export_results_csv, icon='x-office-spreadsheet-symbolic', tooltip='Save results from current tab'))  
                menu.append( f_menu_item(0, 'SEPARATOR', None) )
                menu.append( f_menu_item(1, 'Clear Search History', self.on_clear_history, icon='edit-clear-symbolic') )
                menu.append( f_menu_item(0, 'SEPARATOR', None) )
                menu.append( f_menu_item(1, 'Save layout', self.upper_pages[self.curr_upper].save_layout, icon='view-column-symbolic', tooltip='Save column layout and sizing for current tab.\nIt will be used as default in the future' ) )
                menu.append( f_menu_item(1, 'Save filters', self.upper_pages[self.curr_upper].save_filters, icon='gtk-find-and-replace', tooltip='Save current search filters as defaults for future' ) )


            elif from_where == 'feeds':
                menu = Gtk.Menu()

                if self.selection_feed.get('id',0) > 0 and self.selection_feed['deleted'] != 1:
                    menu.append( f_menu_item(1, 'Show All from newest...', self.add_tab, kargs={'type':'feed'}, icon='edit-find-symbolic', tooltip="Show all articles for this Channel or Category sorted from newest") )

                if not self.curr_actions['feed_update']:
                    menu.append( f_menu_item(1, 'Add Channel', self.on_feed_cat, args=('new_channel',), icon='list-add-symbolic') )
                    menu.append( f_menu_item(1, 'Add Category', self.on_feed_cat, args=('new_category',), icon='folder-new-symbolic') )


                if self.selection_feed.get('id',0) > 0: 

                    if self.selection_feed['deleted'] == 1:
                        menu.append( f_menu_item(1, 'Restore...', self.on_restore_feed, icon='edit-redo-rtl-symbolic') )
                        menu.append( f_menu_item(1, 'Remove Permanently', self.on_del_feed, icon='edit-delete-symbolic') )


                    elif self.selection_feed['is_category'] != 1:
                        
                        menu.append( f_menu_item(1, 'Go to Channel\'s Homepage', self.on_go_home, icon='user-home-symbolic') )
                        
                        if not self.curr_actions['fetch']:
                            menu.append( f_menu_item(1, 'Fetch from selected Channel', self.on_load_news_feed, icon='application-rss+xml-symbolic') )
                            menu.append( f_menu_item(1, 'Update metadata for Channel', self.on_update_feed, icon='preferences-system-symbolic') )
                            menu.append( f_menu_item(1, 'Update metadata for All Channels', self.on_update_feed_all, icon='preferences-system-symbolic') )

                        menu.append( f_menu_item(1, 'Change Category', self.on_change_category, icon='folder-documents-symbolic') )
                        menu.append( f_menu_item(1, 'Edit Channel', self.on_feed_cat, args=('edit',), icon='edit-symbolic') )
                        menu.append( f_menu_item(1, 'Mark Channel as healthy', self.on_mark_healthy, icon='go-jump-rtl-symbolic', tooltip="This will nullify error count for this Channel so it will not be ommited on next fetching") )
                        menu.append( f_menu_item(0, 'SEPARATOR', None) )
                        menu.append( f_menu_item(1, 'Remove Channel', self.on_del_feed, icon='edit-delete-symbolic') )
                        if self.debug: menu.append( f_menu_item(1, 'Technical details...', self.on_feed_details, icon='zoom-in-symbolic', tooltip="Show all technical information about this Channel") )

                    elif self.selection_feed['is_category'] == 1:
                        menu.append( f_menu_item(1, 'Edit Category', self.on_feed_cat, args=('edit',), icon='edit-symbolic') )
                        menu.append( f_menu_item(1, 'Remove Category', self.on_del_feed, icon='edit-delete-symbolic') )
                    

                elif self.feed_win.selected_feed_id < 0:
                    if self.feed_win.selected_feed_ids == 'trash_bin': 
                        menu.append( f_menu_item(1, 'Empty Trash', self.on_empty_trash, icon='edit-delete-symbolic') )
                
            if menu is not None:
                menu.show_all()
                menu.popup(None, None, None, None, event.button, event.time)








    def _on_timer(self, *kargs):
        """ Check for status updates from threads on time interval  """
        self.sec_frac_counter += 1
        if self.sec_frac_counter > 4:
            self.sec_frac_counter = 0
            self.sec_counter += 1

        # Fetch news if specified in config
        if self.sec_counter > 60:
            self.sec_counter = 0
            self.minute_counter += 1
            self._time()
            if self.config.get('gui_fetch_periodically', False):
                self.on_load_news_background()

        # Show queued messages from threads
        if len(self.message_q) > 0:
            m = self.message_q[0]
            self.update_status(slist(m,0,3), slist(m,1,-1))
            del self.message_q[0]

 
        # Apply changes on tabs 
        if len(self.entry_changes_q) > 0:
            m = self.entry_changes_q[0]

            action = slist( m, 1, None)
            if action == 'finished_search':
                uid = slist(m, 0, None)
                for u in self.upper_pages:
                    if u.uid == uid: 
                        u.finish_search()
                        break
            
            else:
                self.upper_pages[self.curr_upper].apply_changes(slist(m, 0, None), action)

            del self.entry_changes_q[0]



        # Deal with user interface updates
        if self.curr_actions != self.prev_actions:
            self.prev_actions = self.curr_actions.copy()

            if self.curr_actions['fetch']: 
                self.button_feeds_download.set_sensitive(False)
                self.button_feeds_new.set_sensitive(False)
            else: 
                self.feed_win.reload_feeds()
                self.button_feeds_download.set_sensitive(True)
                self.button_feeds_new.set_sensitive(True)

            if self.curr_actions['feed_update']: 
                self.button_feeds_download.set_sensitive(False)
                self.button_feeds_new.set_sensitive(False)
            else:
                self.FX.do_load_icons()
                self.icons = get_icons(self.FX.MC.feeds, self.FX.MC.icons)
                self.feed_win.reload_feeds(load=True)
                self.button_feeds_new.set_sensitive(True)
                self.button_feeds_download.set_sensitive(True)
                
        # Show images processed by threads
        if len(self.images_q) > 0:
            if self.selection_res['id'] == self.images_q[0]:
                self.handle_images(self.selection_res.get('id', None), self.selection_res.get('images',''))
            del self.images_q[0]

        return True






    def on_find_similar(self, *args):
        """ Open a new tab to find entries similar to selected """
        time = args[-1]
        filters = {}

        if time == 'range':

                dialog = CalendarDialog(self)
                dialog.run()
                if dialog.response == 1:
                    if self.debug: print(dialog.results)
                    filters = {'date_from': dialog.result['date_from'], 'date_to': dialog.result['date_to']}
                    dialog.destroy()
                else:
                    dialog.destroy()
                    return 0

        else: filters[time] = True

        self.add_tab({'type': 'similar', 'filters': filters})







    def add_tab(self, *args):
        """ Deal with adding tabs and requesting initial queries if required. Accepts args as a dictionary """
        kargs = args[-1]

        type = kargs.get('type','search')
        phrase = kargs.get('phrase')
        date_range = kargs.get('date_range', False)


        if type == 'places': tab_id = 0
        else: tab_id = len(self.upper_pages)

        # Keep track of which tab contains rules
        if type == 'rules' and self.rules_tab != -1:
            self.upper_notebook.set_current_page(self.rules_tab)            
            return 0
        elif type == 'rules' and self.rules_tab == -1:
            self.rules_tab = tab_id


        tab = FeedexTab(self, tab_id=tab_id, type=type, title=kargs.get('title',''), results=kargs.get('results',[]))
        self.upper_pages.append(tab)
        self.upper_notebook.append_page(tab.main_box, tab.header_box)
        tab.header_box.show_all()

        self._reindex_tabs()

        # Quick launch a query if launched from a menu
        if type == 'feed': self.upper_pages[tab_id].query(self.selection_feed.name(), {'feed_or_cat':self.selection_feed['id'], 'deleted':False, 'sort':'-pubdate'} )
        elif type == 'rules': self.upper_pages[self.rules_tab].create_rules_list()
        elif type == 'similar': self.upper_pages[tab_id].query(self.selection_res, kargs.get('filters',{}))

        # Fill up search phrase if provided
        if phrase is not None and type in ('search','contexts','terms','time_series'): self.upper_pages[tab_id].query_entry.set_text(scast(phrase, str, ''))
        
        # Add date range to filters if provided
        if date_range and type in ('search','contexts','terms','time_series'):
            start_date = self.selection_time_series.get('start_date')
            group = self.selection_time_series.get('group')

            if group in ('hourly', 'daily', 'monthly'):
                dmonth = relativedelta(months=+1)
                dday = relativedelta(days=+1)
                dhour = relativedelta(hours=+1)
                dsecond_minus = relativedelta(seconds=-1)

                end_date = None
                if group == 'hourly': 
                    start_date = datetime.strptime(start_date, "%Y-%m-%d %H:%M")
                    end_date = start_date + dhour + dsecond_minus
                elif group == 'daily': 
                    start_date = datetime.strptime(start_date, "%Y-%m-%d")
                    end_date = start_date + dday + dsecond_minus
                elif group == 'monthly': 
                    start_date = datetime.strptime(start_date, "%Y-%m")
                    end_date = start_date + dmonth + dsecond_minus
            

                date_str = f'{start_date.strftime("%Y/%m/%d %H:%M:%S")} --- {end_date.strftime("%Y/%m/%d %H:%M:%S")}'
                self.upper_pages[tab_id].add_date_str_to_combo(date_str)
                f_set_combo(self.upper_pages[tab_id].qtime_combo, f'_{date_str}')


        self.upper_notebook.show_all()
        self.upper_notebook.set_current_page(tab_id)

        if type in ('search','contexts','terms','time_series'): self.upper_pages[tab_id].query_entry.grab_focus()





    def remove_tab(self, tab_id):
        """ Deal with removing tabs and cleaning up """
        if tab_id == 0: return -1

        if self.upper_pages[tab_id].type == 'rules': self.rules_tab = -1  
        self.upper_notebook.remove_page(tab_id)
        self.upper_pages.pop(tab_id)

        self._reindex_tabs()



    def _reindex_tabs(self):
        """ Recalculate tab indexes and parameters after tab addition/deletion """
        self.processing_flags = {}
        for i,t in enumerate(self.upper_pages):
            self.upper_pages[i].tab_id = i
            self.processing_flags[i] = self.upper_pages[i].processing_flag

            if self.upper_pages[i].type == 'rules': self.rules_tab = i



    def _reload_rules(self):
        """ Reload rules if rules tab is open """
        if self.rules_tab != -1:
            self.upper_pages[self.rules_tab].create_rules_list()




    def update_status(self, *args):
        """ Updates lower status bar and busy animation for actions """
        # Parse message tuple and construct text
        msg = args[-1]
        # Handle spinner
        spin = args[-2]
        if spin == 1:
            self.status_spinner.show()
            self.status_spinner.start()
        elif spin in (0,3):
            self.status_spinner.stop()
            self.status_spinner.hide()
        if spin != 3:
            self.status_bar.set_markup(gui_msg(msg, debug=self.debug))

 


    def _on_unb_changed(self, *args):
        """ Action on changing upper tab """
        self.curr_upper = args[2]
        type = self.upper_pages[args[2]].type
        if type in ('places','search','contexts','deleted','similar', 'feed'):
            self.feed_win.feed_aggr = self.upper_pages[args[2]].feed_aggr
        else: self.feed_win.feed_aggr = {}

        self.feed_win.reload_feeds()
            
        if self.upper_pages[args[2]].feed_filter_id > 0:
            self.feed_win._add_underline( self.upper_pages[args[2]].feed_filter_id )

        self.upper_pages[args[2]].load_selection()







    def on_changed_selection(self, *args, **kargs):
        """ Generates result preview when result cursor changes """
        
        title = GObject.markup_escape_text(self.selection_res.get("title",''))
        author = GObject.markup_escape_text(self.selection_res.get('author',''))
        publisher = GObject.markup_escape_text(self.selection_res.get('publisher',''))
        contributors = GObject.markup_escape_text(self.selection_res.get('contributors',''))
        category = GObject.markup_escape_text(self.selection_res.get('category',''))
        desc = GObject.markup_escape_text(self.selection_res.get("desc",''))
        text = GObject.markup_escape_text(self.selection_res.get("text",''))

        # Hilight query using snippets
        if self.selection_res.get('snippets',[]) != []:
            srch_str = []
            snips = self.selection_res.get('snippets',[])
            for s in snips:
                s1 = s[1].strip()
                s1 = GObject.markup_escape_text(s1)
                if s1 not in srch_str: srch_str.append(s1)

            col = self.config.get('gui_hilight_color','blue')
                        
            for s in srch_str:
                title = title.replace(s, f'<span foreground="{col}">{s}</span>')
                author = author.replace(s, f'<span foreground="{col}">{s}</span>')
                publisher = publisher.replace(s, f'<span foreground="{col}">{s}</span>')
                contributors = contributors.replace(s, f'<span foreground="{col}">{s}</span>')
                category = category.replace(s, f'<span foreground="{col}">{s}</span>')
                desc = desc.replace(s, f'<span foreground="{col}">{s}</span>')
                text = text.replace(s, f'<span foreground="{col}">{s}</span>')


        self.prev_title.set_markup(f"\n\n<b>{title}</b>")
        self.prev_auth.set_markup(f'<i>{author} {publisher} {contributors}</i>')
        self.prev_cat.set_markup(f'{category}')
        self.prev_desc.set_markup(desc)
        self.prev_text.set_markup(text)


        link_text=''
        for l in self.selection_res.get('links','').splitlines() + self.selection_res.get('enclosures','').splitlines():

            if l.strip() == '' or l == self.selection_res['link']: continue
            link_text = f"""{link_text}
<a href="{GObject.markup_escape_text(l.replace('<','').replace('>',''))}" title="Click to open link">{GObject.markup_escape_text(l.replace('<','').replace('>',''))}</a>"""
        
        if link_text != '': link_text = f"\n\nLinks:\n{link_text}"
        self.prev_enc.set_markup(link_text)

        if not self.config.get('ignore_images',False):
            self.handle_images(self.selection_res.get('id', None), self.selection_res.get('images',''))


        stat_str = f"""\n\n\n\n<small>-------------------------------------\nWord count: <b>{self.selection_res['word_count']}</b>
Character count: <b>{self.selection_res['char_count']}</b>
Sentence count: <b>{self.selection_res['sent_count']}</b>
Capitalized word count: <b>{self.selection_res['caps_count']}</b>
Common word count: <b>{self.selection_res['com_word_count']}</b>
Polysyllable count: <b>{self.selection_res['polysyl_count']}</b>
Numeral count: <b>{self.selection_res['numerals_count']}</b>\n
Importance: <b>{round(self.selection_res['importance'],3)}</b>
Weight: <b>{round(self.selection_res['weight'],3)}</b>
Readability: <b>{round(self.selection_res['readability'],3)}</b></small>\n"""

        self.prev_stats.set_markup(stat_str)
    










    


############################################
#   IMAGE HANDLING




    def handle_image(self, widget, event, url, title, alt):
        """ Wrapper for showing full-size image in chosen external viewer """
        if event.button == 1:
            hash_obj = hashlib.sha1(url.encode())
            filename = f"""{FEEDEX_CACHE_PATH}{DIR_SEP}{self.MC.db_hash}_{hash_obj.hexdigest()}_full.img"""
            if not os.path.isfile(filename):                
                err = download_res(url, filename, no_thumbnail=True, user_agent=self.config.get('user_agent', FEEDEX_USER_AGENT))
                if err != 0:
                    self.update_status(0, err)
                    return -1

            err = ext_open(self.config, 'image_viewer', filename, title=title, alt=alt, file=True, debug=self.debug)
            if err != 0:
                self.update_status(0, err)
                return -1


    def download_images(self, id, queue):
        """ Image download wrapper for separate thread"""
        for i in queue:
            url = i[0]
            filename = i[1]
            if url not in self.download_errors:
                err = download_res(url, filename, user_agent=self.config.get('user_agent', FEEDEX_USER_AGENT))
                if  err != 0:
                    self.lock.acquire()
                    self.download_errors.append(url)
                    self.message_q.append( (0, err) )
                    self.lock.release()

        self.lock.acquire()        
        self.images_q.append(id)
        self.lock.release()


    def handle_images(self, id:int, string:str, **kargs):
        """ Handle preview images """
        for c in self.prev_images.get_children():
            self.prev_images.remove(c)

        urls = []
        boxes = []
        download_q = []
        for i in string.splitlines():
            im = res(i, self.MC.db_hash)
            if im == 0: continue
            if im['url'] in urls: continue
            if im['url'] in self.download_errors: continue

            urls.append(im['url'])
            if os.path.isfile(im['filename']) and os.path.getsize(im['filename']) > 0:
                pass
            else:
                download_q.append((im['url'], im['filename']))
                continue

            if id != self.selection_res.get('id', None): continue

            eventbox = Gtk.EventBox()
            pixb = GdkPixbuf.Pixbuf.new_from_file(im['filename'])
            image = Gtk.Image.new_from_pixbuf(pixb)
            image.set_tooltip_markup(f"""{im.get('tooltip')}
Click to open in image viewer""")

            eventbox.add(image)
            eventbox.connect("button-press-event", self.handle_image, im['url'], im['title'], im['alt'])
            image.show()
            eventbox.show()
            boxes.append(eventbox)

        if len(download_q) > 0:
            t = threading.Thread(target=self.download_images, args=(self.selection_res['id'],download_q))
            t.start()

        for b in boxes:
            self.prev_images.pack_start(b, True, True, 3)















#########################################################3
# DIALOGS ADN ACTIONS FROM MENUS OR BUTTONS



        




    def on_load_news_feed(self, *args):
        if self.curr_actions['fetch'] or self.curr_actions['feed_update']: return -2
        if not self._fetch_lock(): return 0
        self.update_status(1, 'Checking for news ...')
        self.curr_actions['fetch'] = True
        t = threading.Thread(target=self.load_news_thr, args=('feed',))
        t.start()
    def on_load_news_all(self, *args):
        if self.curr_actions['fetch'] or self.curr_actions['feed_update']: return -2
        if not self._fetch_lock(): return 0
        self.update_status(1, 'Checking for news ...')
        self.curr_actions['fetch'] = True
        t = threading.Thread(target=self.load_news_thr, args=('all',))
        t.start()
    def on_load_news_background(self, *args):
        if self.curr_actions['fetch'] or self.curr_actions['feed_update']: return -2
        if not self._fetch_lock(): return 0
        self.update_status(1, 'Checking for news ...')
        self.curr_actions['fetch'] = True
        t = threading.Thread(target=self.load_news_thr, args=('background',))
        t.start()

    def _fetch_lock(self, *args):
        """ Handle fetching lock gracefully """
        if self.FX.lock_fetching(check_only=True) != 0:
            dialog = YesNoDialog(self, "Database is Locked for Fetching", "<b>Database is Locked for Fetching! Proceed and unlock?</b>", 
                                subtitle="Another instance may be fetching news right now. If not, proceed with operation. Proceed?")
            dialog.run()
            if dialog.response == 1:
                dialog.destroy()
                err = self.FX.unlock_fetching()
                if err == 0: 
                    self.update_status(0, 'Database manually unlocked for fetching...')
                    return True
                else: 
                    self.update_status(0, err)
                    return False
            else:
                dialog.destroy()
                return False
        else: return True


    def load_news_thr(self, mode):
        """ Fetching news/articles from feeds """
        if mode == 'all':
            feed_id=None
            ignore_interval = True
            ignore_modified = self.config.get('ignore_modified',True)
        elif mode == 'background':
            feed_id=None
            ignore_interval = False
            ignore_modified = self.config.get('ignore_modified',True)
        elif mode == 'feed':
            if self.selection_feed['is_category'] != 1:
                feed_id = self.selection_feed['id']
                ignore_interval = True
                ignore_modified = True
            else:
                self.lock.acquire()
                self.curr_actions['fetch'] = False
                self.lock.release()
                return -1
        else:
            self.lock.acquire()
            self.curr_actions['fetch'] = False
            self.lock.release()
            return -1

        FX = Feeder(self.MC, config=self.config, debug=self.debug, ignore_images=self.config.get('ignore_images',False), gui=True, timeout=1)
        for msg in FX.g_fetch(id=feed_id, force=ignore_modified, ignore_interval=ignore_interval): 
            self.lock.acquire()
            self.message_q.append((2, msg,))
            self.lock.release()

        if FX.new_items > 0:
            if self.config.get('gui_desktop_notify', True):
                fx_notifier = DesktopNotifier(parent=self, icons=self.FX.MC.icons)
                results = FX.QP.notify(notify_level=self.config.get('notify_level',1), rev=False, print=False)
                fx_notifier.load(results, self.config.get('notify_level',1), total_number=FX.QP.total_result_number)
                fx_notifier.show()

        self.lock.acquire()
        self.message_q.append((3,None))
        self.curr_actions['fetch'] = False
        self.lock.release()



    def on_update_feed(self, *args):
        """ Wrapper for feed updating """
        if self.curr_actions['fetch'] or self.curr_actions['feed_update']: return -2
        if not self._fetch_lock(): return 0
        self.curr_actions['fetch'] = True
        self.curr_actions['feed_update'] = True
        if self.selection_feed['is_category'] != 1:
            self.update_status(1, 'Updating channel ...')
            t = threading.Thread(target=self.update_feed_thr, args=(self.selection_feed['id'],))
            t.start()

    def on_update_feed_all(self, *args):
        if self.curr_actions['fetch'] or self.curr_actions['feed_update']: return -2
        if not self._fetch_lock(): return 0
        self.curr_actions['fetch'] = True
        self.curr_actions['feed_update'] = True
        self.update_status(1, 'Updating all channels ...')
        t = threading.Thread(target=self.update_feed_thr, args=(None,))
        t.start()


    def update_feed_thr(self, *args):
        """ Updates metadata for all/selected feed """
        feed_id = args[-1]
        FX = Feeder(self.MC, config=self.config, debug=self.debug, ignore_images=self.config.get('ignore_images',False), gui=True, timeout=1)
        for msg in FX.g_fetch(id=feed_id, update_only=True, force=True): 
            self.lock.acquire()
            self.message_q.append((1, msg,))
            self.lock.release()

        icons = get_icons(FX.MC.feeds, self.FX.MC.icons)      
        self.lock.acquire()
        self.icons = icons
        self.message_q.append((3, None,))
        self.curr_actions['fetch'] = False
        self.curr_actions['feed_update'] = False
        self.lock.release()


    def add_from_url_thr(self):
        """ Add from URL - threading """
        FX = Feeder(self.MC, config=self.config, debug=self.debug, ignore_images=self.config.get('ignore_images',False), gui=True, timeout=1)

        self.lock.acquire()
        self.new_feed_url.set_interface(FX)
        self.lock.release()

        err = False
        for msg in self.new_feed_url.g_add_from_url():
            if msg[0] < 0: err = True
            self.lock.acquire()
            self.message_q.append((1, msg,))
            self.lock.release()

        self.lock.acquire()
        self.message_q.append((3, None,))
        self.curr_actions['fetch'] = False
        self.curr_actions['feed_update'] = False
        if not err: self.new_feed_url.clear()
        self.new_feed_url.set_interface(self.FX)
        self.lock.release()


    def on_add_from_url(self, *args):
        """ Adds a new feed from URL - dialog """
        if self.curr_actions['fetch'] or self.curr_actions['feed_update']: return 0

        dialog = NewFromURL(self, self.new_feed_url, debug=self.debug)
        dialog.run()
        if dialog.response == 1:
            self.update_status(1, 'Adding Channel...')
            if not self._fetch_lock(): return 0
            self.curr_actions['fetch'] = True
            self.curr_actions['feed_update'] = True
            t = threading.Thread(target=self.add_from_url_thr)
            t.start()
        dialog.destroy()












    def on_edit_entry(self, *args):
        """ Add / Edit Entry """
        new = args[-1]
        if not new and self.curr_actions['edit_entry']: return 0

        if new: entry = self.new_entry
        else: 
            if self.selection_res['id'] is None: return 0            
            entry = EntryContainer(self.FX, id=self.selection_res['id'])
            if not entry.exists: return -1

        dialog = EditEntry(self, self.config, entry, new=new)
        dialog.run()

        if dialog.response == 1:         
            if new: self.update_status(1, 'Adding entry ...')
            else: self.update_status(1, 'Updating entry ...')
            
            self.curr_actions['edit_entry'] = True    
            t = threading.Thread(target=self.edit_entry_thr, args=(entry, new) )
            t.start()
        dialog.destroy()


    def edit_entry_thr(self, entry, new:bool):
        """ Add/Edit Entry low-level interface for threading """
        err = False
        FX = Feeder(self.MC, config=self.config, debug=self.debug, ignore_images=self.config.get('ignore_images',False), gui=True, wait_indef=True)
        
        self.lock.acquire()
        entry.set_interface(FX)
        self.lock.release()

        if new:
            for msg in entry.g_add():
                if msg[0] < 0: err = True
                self.lock.acquire()
                self.message_q.append((1, msg,))
                self.lock.release()
            if not err:
                self.lock.acquire()
                self.entry_changes_q.append((entry.vals.copy(), 'add'))
                entry.clear()
                self.lock.release()

        else: 
            for msg in entry.g_do_update():
                if msg[0] < 0: err = True
                self.lock.acquire()
                self.message_q.append((1, msg,))
                self.lock.release()
            if not err:
                self.lock.acquire()
                self.entry_changes_q.append((entry.vals.copy(), 'edit'))
                self.lock.release()

        self.lock.acquire()
        self.message_q.append((3, None))
        self.curr_actions['edit_entry'] = False
        self.lock.release()






    def on_del_entry(self, *args):
        """ Deletes selected entry"""
        if self.selection_res['id'] is None: return 0
        entry = EntryContainer(self.FX, id=self.selection_res['id'])
        if not entry.exists: return -1

        if entry['deleted'] != 1: 
            dialog = YesNoDialog(self, 'Delete Entry', f'Are you sure you want to delete <i><b>{esc_mu(entry.name())}</b></i>?')
        else:
            dialog = YesNoDialog(self, 'Delete Entry permanently', f'Are you sure you want to permanently delete <i><b>{esc_mu(entry.name())}</b></i> and associated rules?')
        dialog.run()
        if dialog.response == 1:
            err = False
            msg = entry.r_delete()
            if msg[0] < 0: err = True
            self.update_status(0, msg)
            if not err: self.upper_pages[self.curr_upper].apply_changes(entry.vals.copy(), 'edit')
        dialog.destroy()

    def on_restore_entry(self, *args):
        """ Restore entry """
        if self.selection_res['id'] is None: return 0
        entry = EntryContainer(self.FX, id=self.selection_res['id'])
        if not entry.exists or entry['deleted'] == 0: return -1

        dialog = YesNoDialog(self, 'Restore Entry', f'Are you sure you want to restore <i><b>{esc_mu(entry.name())}</b></i>?')
        dialog.run()
        if dialog.response == 1:
            err = False
            for msg in entry.g_update({'deleted': 0}): 
                if msg[0] < 0: err = True
                self.update_status(0, msg)
            if not err: self.upper_pages[self.curr_upper].apply_changes(entry.vals.copy(), 'edit')
        dialog.destroy()






    def on_change_category(self, *args):
        """ Changes feed's category from dialog """
        if self.selection_feed['id'] is None: return -1
        if self.selection_feed['is_category'] == 1: return 0
        feed = FeedContainer(self.FX, feed_id=self.selection_feed['id'])
        if not feed.exists: return -1
        dialog = ChangeCategory(self, feed)
        dialog.run()
        if dialog.response == 1:
            msg = feed.r_do_update(validate=True)
            self.update_status(0, msg)
            if msg[0] >= 0: self.feed_win.reload_feeds(load=True)
        dialog.destroy()
                

    def on_feed_cat(self, *args):
        """ Edit feed/category """
        action = args[-1]
        if action == 'new_category': 
            feed = self.new_category
            new = True
            dialog = EditCategory(self, feed, new=new)
        elif action == 'new_channel': 
            feed = self.new_feed
            new = True
            dialog = EditFeed(self, feed, new=new)
        elif action == 'edit':
            if self.selection_feed['id'] is None: return 0
            new = False
            feed = FeedContainer(self.FX, id=self.selection_feed['id'])
            if not feed.exists: return -1
            if feed['is_category'] == 1:
                dialog = EditCategory(self, feed, new=new)
            else:
                dialog = EditFeed(self, feed, new=new)

        dialog.run()

        if dialog.response == 1:

            if new: msg = feed.r_add(validate=False)
            else: 
                if feed['is_category'] == 1: msg = feed.r_do_update(validate=True)
                else: msg = feed.r_do_update(validate=False)
            self.update_status(0, msg)

            if msg[0] >= 0:
                if action == 'new_category': self.new_category.clear()
                elif action == 'new_channel': self.new_feed.clear()

                self.feed_win.reload_feeds(load=True)

        dialog.destroy()






    def on_del_feed(self, *args):
        """ Deletes feed or category """
        if self.selection_feed['id'] is None: return 0
        feed = FeedContainer(self.FX, id=self.selection_feed['id'])
        if not feed.exists: return -1

        if coalesce(feed['is_category'],0) == 0 and coalesce(feed['deleted'],0) == 0:
            dialog = YesNoDialog(self, 'Delete Channel', f'<b>Are you sure you want to delete <i>{esc_mu(feed.name())}</i>?</b>')

        elif coalesce(feed['is_category'],0) == 0 and coalesce(feed['deleted'],0) == 1:
            dialog = YesNoDialog(self, 'Delete Channel permanently', f'<b>Are you sure you want to permanently delete <i>{esc_mu(feed.name())}</i>?</b>')

        elif coalesce(feed['is_category'],0) == 1 and coalesce(feed['deleted'],0) == 0:
            dialog = YesNoDialog(self, 'Delete Category', f'<b>Are you sure you want to delete <i>{esc_mu(feed.name())}</i> Category?</b>')

        elif coalesce(feed['is_category'],0) == 1 and coalesce(feed['deleted'],0) == 1:
            dialog = YesNoDialog(self, 'Delete Category', f'<b>Are you sure you want to permanently delete <i>{esc_mu(feed.name())}</i> Category?</b>')

        dialog.run()
        if dialog.response == 1:
            msg = feed.r_delete()
            self.update_status(0, msg)
            if msg[0] >= 0: self.feed_win.reload_feeds(load=True)
        
        dialog.destroy()




    def on_restore_feed(self, *args):
        """ Restores selected feed/category """
        if self.selection_feed['id'] is None: return 0
        feed = FeedContainer(self.FX, id=self.selection_feed['id'])
        if not feed.exists: return -1

        if coalesce(feed['is_category'],0) == 1:
            dialog = YesNoDialog(self, 'Restore Category', f'<b>Restore <i>{esc_mu(feed.name())}</i> Category?</b>')
        else:
            dialog = YesNoDialog(self, 'Restore Channel', f'<b>Restore <i>{esc_mu(feed.name())}</i> Channel?</b>')
        
        dialog.run()

        if dialog.response == 1:
            msg = feed.r_update({'deleted': 0}) 
            self.update_status(0, msg)
            if msg[0] >= 0: self.feed_win.reload_feeds(load=True)
        
        dialog.destroy()





    def on_empty_trash(self, *args):
        """ Empt all Trash items """
        dialog = YesNoDialog(self, 'Empty Trash', f'<b>Do you really want to permanently remove Trash content?</b>')
        dialog.run()
        if dialog.response == 1:
            msg = self.FX.r_empty_trash() 
            self.update_status(0, msg)
            if msg[0] >= 0: self.feed_win.reload_feeds(load=True)
        dialog.destroy()

    def on_clear_history(self, *args):
        """ Clears search history """
        dialog = YesNoDialog(self, 'Clear Search History', f'Are you sure you want to clear <b>Search History</b>?')           
        dialog.run()
        if dialog.response == 1:
            msg = self.FX.r_clear_history()
            self.update_status(0, msg) 
            self._reload_rules()
        dialog.destroy()



    def on_mark_healthy(self, *args):
        """ Marks a feed as healthy -> zeroes the error count """
        if self.selection_feed['id'] is None: return 0
        feed = FeedContainer(self.FX, id=self.selection_feed['id'])
        if not feed.exists: return -1  
        msg = feed.r_update({'error': 0})
        self.update_status(0, msg)
        if msg[0] >= 0: self.feed_win.reload_feeds(load=True)




    def mark_recalc_thr(self, mode, *args):
        """ Marks entry as read """
        FX = Feeder(self.MC, config=self.config, debug=self.debug, ignore_images=self.config.get('ignore_images',False), gui=True)
        entry = EntryContainer(FX, id=self.selection_res['id'])
        if not entry.exists: 
            self.lock.acquire()
            self.curr_actions['edit_entry'] = False
            self.lock.release()
            return -1

        if mode == 'read': 
            if coalesce(entry['read'],0) < 0: idict = {'read': scast(entry['read'],int,0)+1}
            else: idict = {'read': scast(entry['read'],int,0)+1}
        elif mode == 'unimp': idict = {'read': -1}

        err = False
        for msg in entry.g_update(idict):
            if msg[0] < 0: err = True
            self.lock.acquire()
            self.message_q.append((1, msg))
            self.lock.release()

        self.lock.acquire()
        self.message_q.append((3, None))
        self.curr_actions['edit_entry'] = False
        if err: 
            self.lock.release()
            return -1
        self.entry_changes_q.append((entry.vals.copy(), 'edit'))
        self.lock.release()

    
    def on_mark_recalc(self, *args):
        if self.selection_res['id'] is None: return 0
        if self.curr_actions['edit_entry']: return 0
        self.update_status(1, 'Updating ...')
        self.curr_actions['edit_entry'] = True
        mode = args[-1]
        t = threading.Thread(target=self.mark_recalc_thr, args=(mode,))
        t.start()



    def on_mark(self, *args):
        """ Marks entry as unread """
        if self.selection_res['id'] is None: return 0        
        entry = EntryContainer(self.FX, id=self.selection_res['id'])
        if not entry.exists: return -1

        action = args[-1]
        if action == 'unread': idict = {'read': 0}
        elif action == 'unflag': idict = {'flag': 0}
        elif action in (1,2,3,4,5): idict = {'flag': action}
        else: return -1

        err = False
        for msg in entry.g_update(idict):
            if msg[0] < 0: err = True
            self.update_status(1, msg)
        self.update_status(3, None)
        if err: return -1
        self.upper_pages[self.curr_upper].apply_changes(entry.vals.copy(), 'edit')


    

    def on_del_rule(self, *args):
        """ Deletes rule - wrapper """
        if self.selection_rule['id'] is None: return 0
        rule = RuleContainer(self.FX, id=self.selection_rule['id'])
        if not rule.exists: return -1

        dialog = YesNoDialog(self, 'Delete Rule', f'Are you sure you want to permanently delete <b><i>{esc_mu(rule.name())}</i></b> Rule?')           
        dialog.run()
        if dialog.response == 1:
            msg = rule.r_delete() 
            self.update_status(0, msg) 
            if msg[0] >= 0: self._reload_rules()
        dialog.destroy()

        


    def on_edit_rule(self, *args):
        """ Edit / Add Rule with dialog """
        new = args[-1]

        if new: rule = self.new_rule
        else: 
            if self.selection_rule['id'] is None: return 0
            rule = RuleContainer(self.FX, id=self.selection_rule['id'])
            if not rule.exists: return -1

        dialog = EditRule(self, self.config, rule, new=new)
        dialog.run()

        if dialog.response == 1:
            if new:
                msg = rule.r_add(validate=False) 
                self.update_status(0, msg)
                if msg[0] >= 0: self.new_rule.clear()
            else:
                msg = rule.r_do_update(validate=False) 
                self.update_status(0, msg)

            if msg[0] >= 0: self._reload_rules()
        dialog.destroy()   



        
    def open_entry_thr(self, entry, *args):
        """ Wrappper for opening entry and learning in a separate thread """
        FX = Feeder(self.MC, config=self.config, debug=self.debug, ignore_images=True, gui=True, desktop_notify=False)
        self.lock.acquire()
        entry.set_interface(FX)
        self.lock.release()        

        for msg in entry.g_open():
            self.lock.acquire()
            self.message_q.append((1, msg,))
            self.lock.release()

        self.lock.acquire()
        self.entry_changes_q.append((entry.vals.copy(), 'edit'))
        self.message_q.append((0, 'Done...'))
        self.curr_actions['edit_entry'] = False
        self.lock.release()

    def on_activate_result(self, *args, **kargs):
        """ Run in browser and learn """
        if self.curr_actions['edit_entry']: return -2
        if self.selection_res['id'] is None: return 0
        entry = EntryContainer(self.FX, id=self.selection_res['id'])
        if not entry.exists: return -1
        self.update_status(1, 'Opening ...')
        self.curr_actions['edit_entry'] = True
        t = threading.Thread(target=self.open_entry_thr, args=(entry,))
        t.start()



    def on_go_home(self, *args):
        """ Executes browser on channel home page """
        if self.selection_feed['id'] is None: return 0
        feed = FeedContainer(self.FX, feed_id=self.selection_feed['id'])
        if not feed.exists: return -1
        msg = feed.r_open()
        self.update_status(0, msg)




    def on_prefs(self, *args):
        """ Run preferences dialog """
        dialog = PreferencesDialog(self, self.config)
        dialog.run()
        if dialog.response == 1:
            restart = dialog.result.get('restart',False)            
            reload = dialog.result.get('reload',False)            
            dialog.result.pop('restart')
            dialog.result.pop('reload')
            new_config = save_config(dialog.result, FEEDEX_CONFIG)
            if new_config == -1: self.update_status(0, (-1, 'Error saving configuration to %a', FEEDEX_CONFIG))
            else:
                if reload: 
                    self.FX.refresh_data()
                    if self.debug: print('Data reloaded...')
                if restart:
                    dialog2 = InfoDialog(self, 'Restart Required', 'Restart is required for all changes to be applied.')
                    dialog2.run()
                    dialog2.destroy()
                self.update_status(0, 'Configuration saved successfully')
                self.config = parse_config(None, config_str=new_config)
                if self.debug: print(self.config)
        dialog.destroy()



    def on_view_log(self, *args):
        """ Shows dialog for reviewing log """
        err = ext_open(self.config, 'text_viewer', self.config.get('log',None), file=True, debug=self.debug)
        if err != 0: self.update_status(0, err)




    def on_show_detailed(self, *args):
        """ Shows dialog with entry's detailed technical info """

        rules_str=self.FX.QP.rules_for_entry(self.selection_res.get('id'), to_var=True, print=False)
        if self.FX.db_error is not None:
            self.update_status(0, (-2, 'DB Error: %a', self.FX.db_error) )
            return 0
        det_str=f"""\n\n{self.selection_res.__str__()}\n\nMatched rules:\n{rules_str}\n\n"""

        tmp_file = f"""{FEEDEX_CACHE_PATH}{DIR_SEP}{self.MC.db_hash}{random_str(length=5)}_entry_details.txt"""
        with open(tmp_file, 'w') as f: f.write(det_str)

        err = ext_open(self.config, 'text_viewer', tmp_file, file=True, debug=self.debug)
        if err != 0: self.update_status(0, err)


    def on_feed_details(self, *args):
        """ Shows feed's techical details in a dialog """
        det_str=self.FX.QP.read_feed(self.selection_feed['id'], to_var=True)
        if self.FX.db_error is not None:
            self.update_status(0, (-2, 'DB Error: %a', self.FX.db_error) )
            return 0

        tmp_file = f"""{FEEDEX_CACHE_PATH}{DIR_SEP}{self.MC.db_hash}{random_str(length=5)}_feed_details.txt"""
        with open(tmp_file, 'w') as f: f.write(det_str)

        err = ext_open(self.config, 'text_viewer', tmp_file, file=True, debug=self.debug)
        if err != 0: self.update_status(0, err)

        

    def on_show_stats(self, *args):
        """ Shows dialog with SQLite DB statistics """
        stat_str = self.FX.db_stats(print=False, markup=True)
        dialog = DisplayWindow(self, "Database Statistics", stat_str, width=600, height=500, emblem=self.icons.get('db'))
        dialog.run()
        dialog.destroy()

    def on_show_about(self, *args):
        """ Shows 'About...' dialog """
        dialog = AboutDialog(self)
        dialog.run()
        dialog.destroy()

        
    def show_learned_rules(self, *args):
        """ Shows learned rules with weights in a separate window """
        self.FX.load_rules(no_limit=True)
        rule = SQLContainer('rules', RULES_SQL_TABLE)        
        rule_store = Gtk.ListStore(str, str, float, str, int)
        weight_sum = 0

        for r in self.FX.MC.rules:
            if r[rule.get_index('learned')] == 1:
                if r[rule.get_index('type')] == 5: qtype = 'Exact'
                else: qtype = 'Stemmed'
                name = r[1]
                string = r[5]
                weight = r[8]
                qtype = r[2]
                if qtype == 4: qtype = 'Stemmed'
                else: qtype = 'Exact' 
                context_id = r[12]
                rule_store.append( (name, string, weight, qtype, context_id) )
                weight_sum += r[rule.get_index('weight')]
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
            msg = self.FX.r_delete_learned_rules()
            self.update_status(0, msg)
        dialog.destroy()
        self.FX.load_rules(no_limit=False)        






    def on_show_keywords(self, *args, **kargs):
        """ Shows keywords for entry """
        title = f'Keywords for entry <b>{esc_mu(self.selection_res.name())}</b> (id: {self.selection_res["id"]})'
        keywords = self.FX.QP.terms_for_entry(self.selection_res.get('id'), rev=True)
        if self.FX.db_error is not None:
            self.update_status(0, (-2, 'DB Error: %a', self.FX.db_error) )
            return 0

        if len(keywords) == 0:
            self.update_status(0, 'Nothing to show')
            return 0

        kw_store = Gtk.ListStore(str, float)
        for kw in keywords:
            kw_store.append(kw)

        dialog = DisplayKeywords(self, title, kw_store, width=600, height=500)
        dialog.run()
        dialog.destroy()



    ####################################################
    # Porting
    #           Below are wrappers for porting data


    def _choose_file(self, *args, **kargs):
        """ File chooser for porting """
        if kargs.get('action') == 'save':
            dialog = Gtk.FileChooserDialog("Save as..", parent=self, action=Gtk.FileChooserAction.SAVE)
            dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_SAVE, Gtk.ResponseType.OK)
        else:
            dialog = Gtk.FileChooserDialog("Open file", parent=self, action=Gtk.FileChooserAction.OPEN)
            dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK)

        dialog.set_current_folder(kargs.get('start_dir', os.getcwd()))
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            filename = dialog.get_filename()
        else: filename = False
        dialog.destroy()

        if kargs.get('action') == 'save' and os.path.isfile(filename):
            dialog = YesNoDialog(self, f'Overwrite?', f'File <b>{filename}</b> already exists!   Do you want to overwrite it?')
            dialog.run()
            if dialog.response == 1: os.remove(filename)
            else: filename = False
        dialog.destroy()

        if filename in ('',None): filename = False

        return filename




    def export_feeds(self, *args):
        filename = self._choose_file(action='save')
        if filename == False: return 0

        msg = self.FX.r_port_data(True, filename, 'feeds')
        self.update_status(0, msg)

    def export_rules(self, *args):
        filename = self._choose_file(action='save')
        if filename == False: return 0

        msg = self.FX.r_port_data(True, filename, 'rules')
        self.update_status(0, msg)



    def import_feeds(self, *args):
        filename = self._choose_file(action='open')
        if filename == False: return 0

        msg = self.FX.r_port_data(False, filename, 'feeds')
        self.update_status(0, msg)
        if msg[0] >= 0: 
            self.feed_win.reload_feeds(load=True)

            dialog = YesNoDialog(self, f'Update Feed Data', f'New feed data has been imported. Download Metadata now?')
            dialog.run()
            if dialog.response == 1: self.on_update_feed_all()
            dialog.destroy()




    def import_rules(self, *args):
        filename = self._choose_file(action='open')
        if filename == False: return 0

        msg = self.FX.r_port_data(False, filename, 'rules')
        if msg[0] == 0: 
            if self.rules_tab != -1:
                self.upper_pages[self.rules_tab].create_rules_list()






    def export_results_csv(self, *args):
 
        if self.upper_pages[self.curr_upper].type == 'rules': return 0

        results = self.upper_pages[self.curr_upper].results
        if len(results) == 0:
            self.update_status(0, 'Nothing to save...')
            return 0

        filename = self._choose_file(action='save')
        if filename == False: return 0

 
        if self.upper_pages[self.curr_upper].type in ('places','search','similar','trash','feed'):
            columns = RESULTS_SQL_TABLE_PRINT
            mask = RESULTS_SHORT_PRINT1
        elif self.upper_pages[self.curr_upper].type == 'contexts':
            columns = RESULTS_SQL_TABLE_PRINT + ("Context",)
            mask = RESULTS_SHORT_PRINT1 + ("Context",)
        elif self.upper_pages[self.curr_upper].type == 'terms':
            columns = ('Term', 'Weight','Document Count')
            mask = columns
        elif self.upper_pages[self.curr_upper].type == 'time_series':
            columns = ('Time', 'Occurrence Count')
            mask = columns

        csv = to_csv(results, columns, mask)

        try:        
            with open(filename, 'w') as f:
                f.write(csv)
                
        except OSError as e:
            os.stderr.write(str(e))
            self.update_status(0,(-1, 'Error saving to %a', filename))
            return -1
        self.update_status(0, f'Results saved to {filename}...')       


#################################################
#       UTILITIES
#

    def quick_find_case_ins(self, model, column, key, rowiter, *args):
        """ Guick find 'equals' fundction - case insensitive """
        column=args[-1]
        row = model[rowiter]
        if key.lower() in scast(list(row)[column], str, '').lower(): return False
        return True



    def on_db_maint(self, *args):
        """ Dialog for manual DB maintenance """
        pass


    def startup_decor(self, *args):
        """ Decorate preview tab on startup """
        
        pb = GdkPixbuf.Pixbuf.new_from_file_at_size(f"{FEEDEX_SYS_ICON_PATH}/feedex.png", 64, 64)
        icon = Gtk.Image.new_from_pixbuf(pb)
        self.prev_images.pack_start(icon, True, True, 0)

        self.prev_title.set_markup(f'<b>FEEDEX {FEEDEX_VERSION}</b>')
        self.prev_cat.set_markup(f'<a href="{GObject.markup_escape_text(FEEDEX_WEBSITE)}">{GObject.markup_escape_text(FEEDEX_WEBSITE)}</a>')
        self.prev_auth.set_markup(f'<i>{FEEDEX_CONTACT}</i>')
        self.prev_desc.set_markup(f'{FEEDEX_AUTHOR}')
        self.prev_text.set_markup(FEEDEX_DESC)














def feedex_run_main_win(feedex_main_container, **args):
    """ Runs main Gtk loop with main Feedex window"""
    win = FeedexMainWin(feedex_main_container, **args)
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()
