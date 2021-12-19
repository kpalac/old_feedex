# -*- coding: utf-8 -*-
""" GUI classes for FEEDEX """


from feedex_gui_utils import *









class FeedexMainWin(Gtk.Window):
    """ Main window for Feedex """

    def __init__(self, **kargs):
    
        #Maint. stuff
        self.config = kargs.get('config', DEFAULT_CONFIG)
        self.debug = kargs.get('debug',False)

        self.gui_attrs = validate_gui_attrs( load_json(FEEDEX_GUI_ATTR_CACHE, {}) )

        # Timer related ...
        self.sec_frac_counter = 0
        self.sec_counter = 0
        self.minute_counter = 0

        self.today = 0
        self._time()



        # Default fields for edit and new items
        self.default_search_filters = self.gui_attrs.get('default_search_filters', FEEDEX_GUI_DEFAULT_SEARCH_FIELDS).copy()
        self.new_from_url_fields = {}
        self.entry_fields = {}
        self.new_category_fields = {}
        self.new_feed_fields = {}
        self.new_rule_fields = {}

        # Containers for selected/processed items
        self.feed = SQLContainer('feeds', FEEDS_SQL_TABLE, replace_nones=True)
        self.result = SQLContainer('entries', RESULTS_SQL_TABLE, replace_nones=True)
        self.context = SQLContainer('entries', RESULTS_SQL_TABLE + ('context',), replace_nones=True)
        self.rule = SQLContainer('rules', RULES_SQL_TABLE, replace_nones=True)

        # Selection references
        self.selection_res = SQLContainer('entries', RESULTS_SQL_TABLE, replace_nones=True)
        self.selection_term = ''
        self.selection_feed = SQLContainer('feeds', FEEDS_SQL_TABLE, replace_nones=True)
        self.selection_rule = SQLContainer('rules', RULES_SQL_TABLE, replace_nones=True)

        # Main DB interface - init and check for lock and/or DB errors
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


        # Image handling
        self.icons = get_icons(self.FX.feeds, self.FX.icons)

        self.download_errors = [] #Error list to prevent multiple downloads from faulty links

        # Display queues for threading
        self.message_q = [(0, None)]
        self.images_q = []
        self.entry_changes_q = []
        self.processing_flags = {}

        # Actions and Places
        self.curr_actions = {'fetch':False, 'feed_update':False, 'edit_entry':False}
        self.prev_actions = self.curr_actions.copy()
        self.curr_place = 'last'

        # Start threading and main window
        Gdk.threads_init()
        Gtk.Window.__init__(self, title=f"Feedex {FEEDEX_VERSION}")
        
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
        
        if self.config.get('profile_name') != None:
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
        
        self.connect("destroy", self._save_gui_attrs)
        self.connect("key-press-event", self._on_key_press)

        self.add_tab({'type':'places'})
        self.upper_pages[0].query('startup',{})
        self.startup_decor()
 



    def _save_gui_attrs(self, *args):

        #(self.gui_attrs['win_width'], self.gui_attrs['win_height']) = self.get_size()

        self.gui_attrs['div_horiz'] = self.div_horiz.get_position()
        self.gui_attrs['div_vert'] = self.div_vert.get_position()

        err = save_json(FEEDEX_GUI_ATTR_CACHE, self.gui_attrs)
        if self.debug: 
            if err == 0: print('Saved GUI attributes: ', self.gui_attrs)





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




    def _on_key_press(self, widget, event):
        """ When keyboard is used ... """
        key = event.keyval
        key_name = Gdk.keyval_name(key)
        state = event.state
        ctrl = (state & Gdk.ModifierType.CONTROL_MASK)
        if ctrl and key_name == self.config.get('gui_key_search','s'): self.add_tab({'type':'search'}) 
        elif ctrl and key_name == self.config.get('gui_key_new_entry','n'): self.on_add_entry()
        elif ctrl and key_name == self.config.get('gui_key_new_rule','r'): self.on_add_rule()







    def _rbutton_press(self, widget, event, from_where):
        """ Button press event catcher and menu construction"""
        if event.button == 3:
            menu = None

            if from_where in ('results', 'contexts'):
                menu = Gtk.Menu()
                
                if not (self.curr_upper == 0 and self.curr_place == 'trash_bin'):
                    menu.append( f_menu_item(1, 'Add Entry', self.on_add_entry, icon='list-add-symbolic') )

                if self.selection_res['id'] != None:

                    if (not self.curr_actions['edit_entry']) and self.selection_res['deleted'] != 1 and not (self.curr_upper == 0 and self.curr_place == 'trash_bin'):

                        menu.append( f_menu_item(1, 'Mark as Read (+1)', self.on_mark_read, icon='bookmark-new-symbolic', tooltip="Number of reads if counted towards this entry keyword's weight when ranking incoming articles ") )
                        menu.append( f_menu_item(1, 'Mark as Unread', self.on_mark_unread, icon='edit-redo-rtl-symbolic', tooltip="Unread document does not contriute to ranking rules") )

                        flag_menu = Gtk.Menu()
                        flag_menu.append( f_menu_item(1, self.config.get('gui_flag_1_name','Flag 1'), self.on_mark_flag, kargs=1, color=self.config.get('gui_flag_1_color','blue') ) )
                        flag_menu.append( f_menu_item(1, self.config.get('gui_flag_2_name','Flag 2'), self.on_mark_flag, kargs=2, color=self.config.get('gui_flag_2_color','blue') ) )
                        flag_menu.append( f_menu_item(1, self.config.get('gui_flag_3_name','Flag 3'), self.on_mark_flag, kargs=3, color=self.config.get('gui_flag_3_color','blue') ) )
                        flag_menu.append( f_menu_item(1, self.config.get('gui_flag_4_name','Flag 4'), self.on_mark_flag, kargs=4, color=self.config.get('gui_flag_4_color','blue') ) )
                        flag_menu.append( f_menu_item(1, self.config.get('gui_flag_5_name','Flag 5'), self.on_mark_flag, kargs=5, color=self.config.get('gui_flag_5_color','blue') ) )

                        menu.append( f_menu_item(3, 'Flag Entry', flag_menu, icon='marker-symbolic', tooltip="Flag is a user's marker/bookmark for a given article independent of ranking\n<i>You can setup different flag colors in Preferences</i>") )
                        menu.append( f_menu_item(1, 'Unflag Entry', self.on_mark_unflag, icon='edit-redo-rtl-symbolic', tooltip="Flag is a user's marker/bookmark for a given article independent of ranking") )
                        menu.append( f_menu_item(1, 'Edit Entry', self.on_edit_entry, icon='edit-symbolic') )
                        

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

                menu.append( f_menu_item(0, 'SEPARATOR', None) )
                menu.append( f_menu_item(1, 'Clear Search History', self.on_clear_history, icon='edit-clear-symbolic') )
                if self.curr_upper == 0 and self.curr_place == 'trash_bin': menu.append( f_menu_item(1, 'Empty Trash', self.on_empty_trash, icon='edit-delete-symbolic') ) 
                menu.append( f_menu_item(0, 'SEPARATOR', None) )
                menu.append( f_menu_item(1, 'Save layout', self.upper_pages[self.curr_upper].save_layout, icon='view-column-symbolic', tooltip='Save column layout and sizing for current tab.\nIt will be used as default in the future' ) )
                if self.upper_pages[self.curr_upper].type in ('search', 'contexts'):
                    menu.append( f_menu_item(1, 'Save filters', self.upper_pages[self.curr_upper].save_filters, icon='gtk-find-and-replace', tooltip='Save current search filters as defaults for future' ) )


            elif from_where == 'rules':
                menu = Gtk.Menu()
                menu.append( f_menu_item(1, 'Add Rule', self.on_add_rule, icon='list-add-symbolic') )
                if self.selection_rule['id'] != None:
                    menu.append( f_menu_item(1, 'Edit Rule', self.on_edit_rule, icon='edit-symbolic') )
                    menu.append( f_menu_item(1, 'Delete Rule', self.on_del_rule, icon='edit-delete-symbolic') )
                #menu.append( f_menu_item(1, 'Delete Rules from Queries', self.on_del_query_rules, icon='edit-delete-symbolic') )
                menu.append( f_menu_item(1, 'Clear Search History', self.on_clear_history, icon='edit-clear-symbolic') )
                menu.append( f_menu_item(1, 'Show Learned Rules', self.show_learned_rules, icon='zoom-in-symbolic', tooltip='Display rules learned from User\'s habits along with weights') )
                menu.append( f_menu_item(1, 'Save layout', self.upper_pages[self.curr_upper].save_layout, icon='view-column-symbolic', tooltip='Save column layout and sizing for current tab.\nIt will be used as default in the future' ) )

            elif from_where  == 'terms':            
                menu = Gtk.Menu()
                menu.append( f_menu_item(1, 'Save results to CSV', self.export_results_csv, icon='x-office-spreadsheet-symbolic', tooltip='Save results from current tab'))  
                menu.append( f_menu_item(0, 'SEPARATOR', None) )
                menu.append( f_menu_item(1, 'Save layout', self.upper_pages[self.curr_upper].save_layout, icon='view-column-symbolic', tooltip='Save column layout and sizing for current tab.\nIt will be used as default in the future' ) )

            elif from_where  == 'time_series':            
                menu = Gtk.Menu()
                menu.append( f_menu_item(1, 'Save results to CSV', self.export_results_csv, icon='x-office-spreadsheet-symbolic', tooltip='Save results from current tab'))  
                menu.append( f_menu_item(0, 'SEPARATOR', None) )
                menu.append( f_menu_item(1, 'Save layout', self.upper_pages[self.curr_upper].save_layout, icon='view-column-symbolic', tooltip='Save column layout and sizing for current tab.\nIt will be used as default in the future' ) )
                menu.append( f_menu_item(1, 'Save filters', self.upper_pages[self.curr_upper].save_filters, icon='gtk-find-and-replace', tooltip='Save current search filters as defaults for future' ) )


            elif from_where == 'feeds':
                menu = Gtk.Menu()

                if self.selection_feed.get('id',0) > 0 and self.selection_feed['deleted'] != 1:
                    menu.append( f_menu_item(1, 'Show All from newest...', self.add_tab, kargs={'type':'feed'}, icon='edit-find-symbolic', tooltip="Show all articles for this Channel or Category sorted from newest") )

                if not self.curr_actions['feed_update']:
                    menu.append( f_menu_item(1, 'Add Channel', self.on_add_feed, icon='list-add-symbolic') )
                    menu.append( f_menu_item(1, 'Add Category', self.on_add_category, icon='folder-new-symbolic') )


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
                        menu.append( f_menu_item(1, 'Edit Channel', self.on_edit_feed_cat, icon='edit-symbolic') )
                        menu.append( f_menu_item(1, 'Mark Channel as healthy', self.on_mark_healthy, icon='go-jump-rtl-symbolic', tooltip="This will nullify error count for this Channel so it will not be ommited on next fetching") )
                        menu.append( f_menu_item(0, 'SEPARATOR', None) )
                        menu.append( f_menu_item(1, 'Remove Channel', self.on_del_feed, icon='edit-delete-symbolic') )
                        if self.debug: menu.append( f_menu_item(1, 'Technical details...', self.on_feed_details, icon='zoom-in-symbolic', tooltip="Show all technical information about this Channel") )

                    elif self.selection_feed['is_category'] == 1:
                        menu.append( f_menu_item(1, 'Edit Category', self.on_edit_feed_cat, icon='edit-symbolic') )
                        menu.append( f_menu_item(1, 'Remove Category', self.on_del_feed, icon='edit-delete-symbolic') )
                    

                elif self.feed_win.selected_feed_id < 0:
                    if self.feed_win.selected_feed_ids == 'trash_bin': 
                        menu.append( f_menu_item(1, 'Empty Trash', self.on_empty_trash, icon='edit-delete-symbolic') )
                
            if menu != None:
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
            if self.config.get('gui_fetch_periodically',False):
                self.on_load_news_background()

        # Show queued messages from threads
        if len(self.message_q) > 0:
            m = self.message_q[0]
            self.update_status(slist(m,0,3), slist(m,1,-1))
            del self.message_q[0]

        # Apply changes on tabs 
        if len(self.entry_changes_q) > 0:
            m = self.entry_changes_q[0]
            self._apply_changes(slist(m, 0, None), slist( m, 1, None), entry=slist( m, 3, None))
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
                self.icons = get_icons(self.FX.feeds, self.FX.icons)
                self.feed_win.reload_feeds(load=True)
                self.button_feeds_new.set_sensitive(True)
                self.button_feeds_download.set_sensitive(True)
                


        # Show images processed by threads
        if len(self.images_q) > 0:
            if self.selection_res['id'] == self.images_q[0]:
                self.handle_images(self.selection_res.get('id', None), self.selection_res.get('images',''))
            del self.images_q[0]

        # Check if any tab finished a search and finalize GUI if yes
        for i in self.processing_flags.keys():
            if self.upper_pages[i].processing_flag != self.processing_flags[i]:
                if self.upper_pages[i].processing_flag == False:
                    self.upper_pages[i].finish_search()

                self.processing_flags[i] = not self.processing_flags[i]


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
        if type == 'places': tab_id = 0
        else: tab_id = len(self.upper_pages)

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

        if type == 'feed': self.upper_pages[tab_id].query(feed_name(self.selection_feed), {'feed_or_cat':self.selection_feed['id'], 'deleted':False, 'sort':'-pubdate'} )
        elif type == 'rules': self.upper_pages[self.rules_tab].create_rules_list()
        elif type == 'similar': self.upper_pages[tab_id].query(self.selection_res, kargs.get('filters',{}))

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
        if self.rules_tab != -1: self.upper_pages[self.rules_tab].create_rules_list()



    def _apply_changes(self, id, action, **kargs):
        """ Apply entry changes for all relevant tabs (e.g. on edit, delete, new) """
        if id == None or action == None: return -1

        if action == 'add':
            self.upper_pages[self.curr_upper].apply_changes(id, action, entry=kargs.get('entry'))
        else:
            for tab in self.upper_pages: tab.apply_changes(id, action, entry=kargs.get('entry'))






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
            self.status_bar.set_markup(parse_message(msg))

 


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
        

    def handle_images(self, id:int, string:str, **kargs):
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

            if id != self.selection_res.get('id', None): continue

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
            t = threading.Thread(target=self.download_images, args=(self.selection_res['id'],download_q))
            t.start()

        for b in boxes:
            self.prev_images.pack_start(b, True, True, 3)















#########################################################3
# DIALOGS ADN ACTIONS FROM MENUS OR BUTTONS



        




    def on_load_news_feed(self, *args):
        t = threading.Thread(target=self.load_news, args=('feed',))
        t.start()
    def on_load_news_all(self, *args):
        t = threading.Thread(target=self.load_news, args=('all',))
        t.start()
    def on_load_news_background(self, *args):
        t = threading.Thread(target=self.load_news, args=('background',))
        t.start()
    def load_news(self, mode):
        """ Fetching news/articles from feeds """
        if self.curr_actions['fetch']: return -2
        self.curr_actions['fetch'] = True

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
            if self.selection_feed['is_category'] != 1:
                self.message_q.append((1,f'Checking <b>{feed_name(self.selection_feed)}</b> for news'))
                feed_id = self.selection_feed['id']
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
                fx_notifier.load(results, self.config.get('notify_level',1), total_number=FX.QP.total_result_number)
                fx_notifier.show()

        self.message_q.append((3,None))
        self.curr_actions['fetch'] = False




    def on_update_feed(self, *args):
        """ Wrapper for feed updating """
        if self.curr_actions['fetch'] or self.curr_actions['feed_update']: return -2
        self.curr_actions['fetch'] = True
        self.curr_actions['feed_update'] = True

        if self.selection_feed['is_category'] != 1:
            t = threading.Thread(target=self.update_feed, args=(self.selection_feed['id'],))
            t.start()

    def on_update_feed_all(self, *args):
        if self.curr_actions['fetch'] or self.curr_actions['feed_update']: return -2
        self.curr_actions['fetch'] = True
        self.curr_actions['feed_update'] = True
        t = threading.Thread(target=self.update_feed, args=(None,))
        t.start()


    def update_feed(self, *args):
        """ Updates metadata for all/selected feed """
        feed_id = args[-1]
        FX = Feeder(config=self.config, debug=self.debug, ignore_images=self.config.get('ignore_images',False), gui=True, timeout=1)
        for msg in FX.g_fetch(id=feed_id, update_only=True, force=True):
            self.message_q.append((1, msg,))
        self.icons = get_icons(FX.feeds, self.FX.icons)
        self.message_q.append((3, None,))
        self.curr_actions['fetch'] = False
        self.curr_actions['feed_update'] = False


    def add_from_url(self, url, handler, category):
        """ Add from URL - threading """
        FX = Feeder(config=self.config, debug=self.debug, ignore_images=self.config.get('ignore_images',False), gui=True, timeout=1, no_qp=True)
        err = False
        for msg in FX.g_add_feed_from_url(url, handler=handler, category=category):
            if slist(msg, 0, 0) < 0 or scast(msg, int, 0) < 0: err = True
            self.message_q.append((1, msg,))
        self.message_q.append((3, None,))
        self.curr_actions['fetch'] = False
        self.curr_actions['feed_update'] = False
        if not err: self.new_from_url_fields = {}

    def on_add_from_url(self, *args):
        """ Adds a new feed from URL - dialog """
        if self.curr_actions['fetch'] or self.curr_actions['feed_update']: return 0

        dialog = NewFromURL(self, self.config, self.new_from_url_fields, debug=self.debug)
        dialog.run()
        self.new_from_url_fields = dialog.result
        if dialog.response == 1:
            self.curr_actions['fetch'] = True
            self.curr_actions['feed_update'] = True
            t = threading.Thread(target=self.add_from_url, args=(dialog.result.get('url'), dialog.result.get('handler'), dialog.result.get('category') ))
            t.start()
        dialog.destroy()












    def on_add_entry(self, *args): self.edit_entry(None)
    def on_edit_entry(self, *args): self.edit_entry(self.selection_res)
    def edit_entry(self, entry, *args):
        """ Add / Edit Entry """
        if entry != None and self.curr_actions['edit_entry']: return 0

        if entry == None: dialog = EditEntry(self, self.config, self.entry_fields, new=True)
        else:
            if self.selection_res['id'] == None: return -1
            dialog = EditEntry(self, self.config, entry, new=False)
        dialog.run()
        if entry == None: self.entry_fields = dialog.result
        if dialog.response == 1:
            if entry == None: t = threading.Thread(target=self.edit_entry_thr, args=(None, dialog.result) )
            else: t = threading.Thread(target=self.edit_entry_thr, args=(self.selection_res['id'], dialog.result) )
            t.start()
        dialog.destroy()


    def edit_entry_thr(self, id, result, **kargs):
        """ Add/Edit Entry low-level interface for threading """
        err = False
        FX = Feeder(config=self.config, debug=self.debug, ignore_images=self.config.get('ignore_images',False), gui=True, wait_indef=True)
        if id == None:
            for msg in FX.g_add_entries(elist=(result,), learn=result.get('learn',False), ignore_lock=True): 
                if slist(msg, 0, 0) < 0 or scast(msg, int, 0) < 0: err = True
                else: err = False
                self.message_q.append((1, msg,))
            if not err: 
                self.entry_fields = {}
                self.entry_changes_q.append((FX.last_entry_id, 'add'))
        else:
            del result['learn']
            for msg in FX.g_edit_entry(id, result, ignore_lock=True):
                if slist(msg, 0, 0) < 0 or scast(msg, int, 0) < 0: err = True
                else: err = False
                self.message_q.append((1, msg))
            if not err: self.entry_changes_q.append((id, 'edit'))
        self.message_q.append((3, None))
        self.curr_actions['edit_entry'] = False





    def on_del_entry(self, *args):
        """ Deletes selected entry"""
        if self.selection_res['id'] == None: return 0
        if self.selection_res['deleted'] != 1: 
            dialog = YesNoDialog(self, 'Delete Entry', f'Are you sure you want to delete <i><b>{entry_name(self.selection_res)}</b></i>?')
        else:
            dialog = YesNoDialog(self, 'Delete Entry permanently', f'Are you sure you want to permanently delete <i><b>{entry_name(self.selection_res)}</b></i> and associated rules?')
        dialog.run()
        if dialog.response == 1:
            err = False
            for msg in self.FX.g_del_entry(self.selection_res['id'], ignore_lock=True): 
                if slist(msg, 0, 0) < 0 or scast(msg, int, 0) < 0: err = True
                self.update_status(1, msg)
            if not err: self._apply_changes(self.selection_res['id'], 'delete')
            self.update_status(3, None)
        dialog.destroy()

    def on_restore_entry(self, *args):
        """ Restore entry """
        if self.selection_res['id'] == None: return 0
        dialog = YesNoDialog(self, 'Restore Entry', f'Are you sure you want to restore <i><b>{entry_name(self.selection_res)}</b></i>?')
        dialog.run()
        if dialog.response == 1:
            err = False
            for msg in self.FX.g_edit_entry(self.selection_res['id'], {'deleted': 0}, ignore_lock=True): 
                if slist(msg, 0, 0) < 0 or scast(msg, int, 0) < 0: err = True
                self.update_status(1, msg)
            if not err: self._apply_changes(self.selection_res['id'], 'restore')
            self.update_status(3, None)
        dialog.destroy()






    def on_add_category(self, *args): self.edit_category(None)
    def on_add_feed(self, *args): self.edit_feed(None)

    def on_change_category(self, *args):
        """ Changes feed's category from dialog """
        if self.selection_feed['is_category'] == 1: return 0
        dialog = ChangeCategory(self, self.selection_feed.get('name', self.selection_feed.get('title', self.selection_feed.get('id','<<UNKNOWN?>>'))), self.selection_feed.get('parent_id',0))
        dialog.run()
        if dialog.response == 1:
            for msg in self.FX.g_edit_feed(self.selection_feed['id'], {'parent_id': dialog.result}, ignore_lock=True): self.update_status(1, msg)
            self.update_status(3, None)
            self.feed_win.reload_feeds(load=True)
        dialog.destroy()
                
    def on_edit_feed_cat(self, feed, *args):
        """ Edit feed/category - wrapper """
        if self.selection_feed['is_category'] == 1: self.edit_category(self.selection_feed)
        else: self.edit_feed(self.selection_feed)

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
            self.feed_win.reload_feeds(load=True)
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
            self.feed_win.reload_feeds(load=True)
        dialog.destroy()            


    def on_del_feed(self, *args):
        """ Deletes feed or category """
        if self.selection_feed['is_category'] != 1:
            if self.selection_feed['deleted'] == 1:
                dialog = YesNoDialog(self, 'Delete Feed permanently', f'<b>Are you sure you want to permanently delete <i>{feed_name(self.selection_feed)}</i> Feed?</b>')
            else:
                dialog = YesNoDialog(self, 'Delete Feed', f'<b>Are you sure you want to delete <i>{feed_name(self.selection_feed)}</i> Feed?</b>')
            dialog.run()
            if dialog.response == 1:
                for msg in self.FX.g_del_feed(self.selection_feed['id'], type='feed'): self.update_status(1, msg)
                self.update_status(3, None)
                self.feed_win.reload_feeds()
            dialog.destroy()
            
        else:
            if self.selection_feed['deleted'] == 1:
                dialog = YesNoDialog(self, 'Delete Category permanently', f'<b>Are you sure you want to permanently delete <i>{feed_name(self.selection_feed)}</i> Category?</b>')
            else:
                dialog = YesNoDialog(self, 'Delete Category', f'<b>Are you sure you want to delete <i>{feed_name(self.selection_feed)}</i> Category?</b>')
            dialog.run()
            if dialog.response == 1:
                for msg in self.FX.g_del_feed(self.selection_feed['id'], type='category'): self.update_status(1, msg)
                self.update_status(3, None)
                self.feed_win.reload_feeds(load=True)
            dialog.destroy()




    def on_restore_feed(self, *args):
        """ Restores selected feed/category """
        if self.feed['is_category'] == 1:
            dialog = YesNoDialog(self, 'Restore Category', f'<b>Restore <i>{feed_name(self.selection_feed)}</i> Category?</b>')
        else:
            dialog = YesNoDialog(self, 'Restore Feed', f'<b>Restore <i>{feed_name(self.selection_feed)}</i> Feed?</b>')
        dialog.run()
        if dialog.response == 1:
            for msg in self.FX.g_edit_feed(self.selection_feed['id'], {'deleted': 0}, ignore_lock=True): self.update_status(1, msg)
            self.update_status(3, None)
            self.feed_win.reload_feeds(load=True)
        dialog.destroy()


    def on_empty_trash(self, *args):
        """ Empt all Trash items """
        dialog = YesNoDialog(self, 'Empty Trash', f'<b>Do you really want to permanently remove Trash content?</b>')
        dialog.run()
        if dialog.response == 1:
            for msg in self.FX.g_empty_trash(): self.update_status(1, msg)
        self.update_status(3, None)
        self.feed_win.reload_feeds(load=True)
        dialog.destroy()



    def on_mark_healthy(self, *args):
        """ Marks a feed as healthy -> zeroes the error count """
        for msg in self.FX.g_edit_feed(self.selection_feed['id'], {'error': 0}, ignore_lock=True): self.update_status(1, msg)
        self.update_status(3, None)
        self.feed_win.reload_feeds(load=True)




    def mark_read(self, *args):
        """ Marks entry as read """
        self.curr_actions['edit_entry'] = True
        id = self.selection_res['id']
        read = scast(self.selection_res['read'], int, 0)
        err = False
        FX = Feeder(config=self.config, debug=self.debug, ignore_images=self.config.get('ignore_images',False), gui=True)
        for msg in FX.g_edit_entry(id, {'read': read+1}, ignore_lock=True):
            if slist(msg, 0, 0) < 0: err = True
            self.message_q.append((1, msg))
        self.message_q.append((3, None))
        self.curr_actions['edit_entry'] = False
        if err: return -1
        self.entry_changes_q.append((id, 'read'))

    def on_mark_read(self, *args):
        if self.selection_res['id'] == None: return 0
        if self.curr_actions['edit_entry']: return 0
        t = threading.Thread(target=self.mark_read)
        t.start()
        

    def on_mark_unread(self, *args):
        """ Marks entry as unread """
        if self.selection_res['id'] == None: return 0        
        err = False
        for msg in self.FX.g_edit_entry(self.selection_res['id'], {'read': 0}, ignore_lock=True):
            if slist(msg, 0, 0) < 0: err = True
            self.update_status(1, msg)
        self.update_status(3, None)
        if err: return -1
        self._apply_changes(self.selection_res['id'], 'unread')

    def on_mark_flag(self, *args):
        """ Marks entry as flagged """
        if self.selection_res['id'] == None: return 0        
        flag = slist(args,-1,0)
        err = False
        for msg in self.FX.g_edit_entry(self.selection_res['id'], {'flag': flag}, ignore_lock=True):
            if slist(msg, 0, 0) < 0: err = True
            self.update_status(1, msg)
        self.update_status(3, None)
        if err: return -1
        self._apply_changes(self.selection_res['id'], 'flag', entry=flag)

    def on_mark_unflag(self, *args):
        """ Marks entry as unflagged """
        if self.selection_res['id'] == None: return 0        
        err = False
        for msg in self.FX.g_edit_entry(self.selection_res['id'], {'flag': 0}, ignore_lock=True):
            if slist(msg, 0, 0) < 0: err = True
            self.update_status(1, msg)
        self.update_status(3, None)
        if err: return -1
        self._apply_changes(self.selection_res['id'], 'unflag')

    

    def on_del_rule(self, *args):
        """ Deletes rule - wrapper """
        dialog = YesNoDialog(self, 'Delete Rule', f'Are you sure you want to permanently delete <b><i>{rule_name(self.selection_rule)}</i></b> Rule?')           
        dialog.run()
        if dialog.response == 1:
            for msg in self.FX.g_del_rule(self.selection_rule['id'], ignore_lock=True): self.update_status(1, msg) 
            self.update_status(3, None)
            self._reload_rules()
        dialog.destroy()


    def on_del_query_rules(self, *args):
        """ Deletes all rules from queries """
        dialog = YesNoDialog(self, 'Delete Query Rules', f'Are you sure you want to permanently delete all <b>rules saved from queries</b>?')           
        dialog.run()
        if dialog.response == 1:
            for msg in self.FX.g_delete_query_rules(ignore_lock=True): self.update_status(1, msg) 
            self.update_status(3, None)
            self._reload_rules()
        dialog.destroy()
        

    def on_clear_history(self, *args):
        """ Clears search history """
        dialog = YesNoDialog(self, 'Clear Search History', f'Are you sure you want to clear <b>Search History</b>?')           
        dialog.run()
        if dialog.response == 1:
            for msg in self.FX.g_clear_history(ignore_lock=True): self.update_status(1, msg) 
            self.update_status(3, None)
            self._reload_rules()
        dialog.destroy()


    def on_add_rule(self, *args): self.edit_rule(None)
    def on_edit_rule(self, *args): self.edit_rule(self.selection_rule)
    def edit_rule(self, rule):
        """ Edit / Add Rule with dialog """
        if rule == None: 
            dialog = EditRule(self, self.config, self.new_rule_fields, new=True)
        else: 
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
            self._reload_rules()
        dialog.destroy()       



        
    def open_entry(self, id:int):
        """ Wrappper for opening entry and learning in a separate thread """
        self.curr_actions['edit_entry'] = True
        FX = Feeder(config=self.config, debug=self.debug, ignore_images=True, gui=True, desktop_notify=False)
        for msg in FX.g_run_entry(id=id):
            self.message_q.append((1, msg,))
        self.entry_changes_q.append((id, 'open'))
        self.message_q.append((0, 'Done...'))
        self.curr_actions['edit_entry'] = False

    def on_activate_result(self, *args, **kargs):
        """ Run in browser and learn """
        if self.curr_actions['edit_entry']: return -2
        t = threading.Thread(target=self.open_entry, args=(self.selection_res['id'],))
        t.start()


    def on_go_home(self, *args):
        """ Executes browser on channel home page """
        link = self.selection_feed['link']
        if link not in (None, ''):
            command = self.config.get('browser','firefox --new-tab %u').split()
            for idx, arg in enumerate(command):
                if arg in ('%u', '%U', '%f', '%F'):
                    command[idx] = link

            if self.debug: print(' '.join(command))
            subprocess.call(command)



    def on_prefs(self, *args):
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



    def on_view_log(self, *args):
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

    def on_show_detailed(self, *args):
        """ Shows dialog with entry's detailed technical info """
        rules_str=self.FX.QP.rules_for_entry(self.selection_res.get('id'), to_var=True, print=False)
        det_str=f"""\n\n{self.selection_res.__str__()}\n\nMatched rules:\n{rules_str}\n\n"""
        dialog = DisplayWindow(self, "Technical Details", GObject.markup_escape_text(det_str))
        dialog.run()
        dialog.destroy()

    def on_feed_details(self, *args):
        """ Shows feed's techical details in a dialog """
        det_str=self.FX.QP.read_feed(self.selection_feed['id'], to_var=True)
        dialog = DisplayWindow(self, "Channel's Technical Details", GObject.markup_escape_text(det_str))
        dialog.run()
        dialog.destroy()

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






    def on_show_keywords(self, *args, **kargs):
        """ Shows keywords for entry """
        title = f'Keywords for entry <b>{entry_name(self.selection_res)}</b> (id: {self.selection_res["id"]})'
        keywords = self.FX.QP.terms_for_entry(self.selection_res.get('id'), rev=True)

        if len(keywords) == 0:
            self.update_status(3, (74, self.selection_res.get('id')))
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

        err = self.FX.port_data(True, filename, 'feeds')

        if err == 0: self.update_status(0, 'Feeds data exported successfully')
        else: self.update_status(0, (-51, filename) )

    def export_rules(self, *args):
        filename = self._choose_file(action='save')
        if filename == False: return 0

        err = self.FX.port_data(True, filename, 'rules')

        if err == 0: self.update_status(0, 'Rules exported successfully')
        else: self.update_status(0, (-52, filename) )



    def import_feeds(self, *args):
        filename = self._choose_file(action='open')
        if filename == False: return 0

        err = self.FX.port_data(False, filename, 'feeds')

        if err == 0: 
            self.update_status(0, 'Feed data imported successfully')
            self.feed_win.reload_feeds(load=True)

            dialog = YesNoDialog(self, f'Update Feed Data', f'New feed data has been imported. Download Metadata now?')
            dialog.run()
            if dialog.response == 1: self.on_update_feed_all()
            dialog.destroy()
        else: self.update_status(0, (-35, filename) )




    def import_rules(self, *args):
        filename = self._choose_file(action='open')
        if filename == False: return 0

        err = self.FX.port_data(False, filename, 'rules')
        if err == 0: 
            if self.rules_tab != -1:
                self.upper_pages[self.rules_tab].create_rules_list()
            self.update_status(0, 'Rules imported successfully')
        else: self.update_status(0, (-36, filename) )





    def export_results_csv(self, *args):
        filename = self._choose_file(action='save')
        if filename == False: return 0

        if self.upper_pages[self.curr_upper].type == 'rules': return 0

        results = self.upper_pages[self.curr_upper].results

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

        except Exception as e:
            os.stderr.write(str(e))
            self.update_status(0,(-53, filename))
            return -1
        self.update_status(0, 'Results saved...')       






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














def feedex_run_main_win(**args):
    """ Runs main Gtk loop with main Feedex window"""
    win = FeedexMainWin(**args)
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()
