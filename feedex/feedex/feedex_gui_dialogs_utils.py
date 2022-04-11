# -*- coding: utf-8 -*-
""" GUI dialog windows classes for FEEDEX """


from feedex_gui_utils import *







class InfoDialog(Gtk.Dialog):
    """Info Dialog - no choice """

    def __init__(self, parent, title, text, **kargs):

        self.response = 0

        Gtk.Dialog.__init__(self, title=title, transient_for=parent, flags=0)

        box = self.get_content_area()

        box1 = Gtk.Box()
        box1.set_orientation(Gtk.Orientation.VERTICAL)
        box1.set_homogeneous(False)
        box1.set_border_width(5)

        subt = kargs.get('subtitle',None)
        self.set_default_size(kargs.get('width',600), kargs.get('height',10))

        label = f_label(text, justify=FX_ATTR_JUS_CENTER, selectable=False, wrap=True, markup=True)
        box1.pack_start(label, False,False, 3)

        if subt is not None:
            sublabel = f_label(subt, justify=FX_ATTR_JUS_CENTER, selectable=False, wrap=True, markup=True)
            box1.pack_start(sublabel, False, False, 3)        

        bbox = Gtk.Box()
        bbox.set_orientation(Gtk.Orientation.HORIZONTAL)
        bbox.set_homogeneous(False)
        bbox.set_border_width(5)

        close_button = f_button(kargs.get('button_text',_('Close')),'object-select-symbolic', connect=self.on_close)

        bbox.pack_end(close_button, False, False, 3)

        box.add(box1)
        box.pack_end(bbox, False, False, 3)
    
        self.show_all()



    def on_close(self, *args):
        self.close()








class YesNoDialog(Gtk.Dialog):
    """ Yes/No Choice dialog """

    def __init__(self, parent, title, text, **kargs):

        self.response = 0 # This marks the user's main choice

        Gtk.Dialog.__init__(self, title=title, transient_for=parent, flags=0)

        box = self.get_content_area()

        subt = kargs.get('subtitle',None)
        self.set_default_size(kargs.get('width',600), kargs.get('height',10))

        label = f_label(text, justify=FX_ATTR_JUS_CENTER, selectable=False, wrap=True, markup=True)

        if subt is not None:
            sublabel = f_label(subt, justify=FX_ATTR_JUS_CENTER, selectable=False, wrap=True, markup=True)


        yes_button = f_button(_('Yes'),'object-select-symbolic', connect=self.on_yes)
        no_button = f_button(_('No'),'action-unavailable-symbolic', connect=self.on_no)

        main_box = Gtk.VBox(homogeneous = False, spacing = 0)
        top_box = Gtk.VBox(homogeneous = False, spacing = 0)
        bottom_box = Gtk.HBox(homogeneous = False, spacing = 0)

        box.add(main_box)
        box.pack_start(top_box, True, False, 0)
        box.pack_start(bottom_box, True, False, 0)

        bottom_box.pack_start(no_button, False, False, 5)
        bottom_box.pack_end(yes_button, False, False, 5)
        
        top_box.pack_start(label, False, False, 0)

        if subt is not None: top_box.pack_start(sublabel, False, False, 0)

        self.show_all()



    def on_yes(self, *args):
        self.response = 1
        self.close()

    def on_no(self, *args):
        self.response = 0
        self.close()







class DisplayRules(Gtk.Dialog):
    """ Display learned rules dialog """
    def __init__(self, parent, header, store, **kargs):

        Gtk.Dialog.__init__(self, title=_('Learned Rules'), transient_for=parent, flags=0)

        self.set_default_size(kargs.get('width',1000), kargs.get('height',500))
        self.set_border_width(10)
        box = self.get_content_area()

        self.response = 0

        grid = Gtk.Grid()
        grid.set_column_spacing(10)
        grid.set_row_spacing(10)
        grid.set_column_homogeneous(True)
        grid.set_row_homogeneous(True)

        header_label = f_label(header, justify=FX_ATTR_JUS_LEFT, wrap=True, markup=True)

        scwindow = Gtk.ScrolledWindow()

        self.rule_store = store
        self.rule_list = Gtk.TreeView(model=self.rule_store)
        self.rule_list.append_column( f_col(_('Name'),0 , 0, resizable=True, clickable=True, start_width=300) )
        self.rule_list.append_column( f_col(_('REGEX String'),0 , 1, resizable=True, clickable=True, start_width=300) )
        self.rule_list.append_column( f_col(_('Weight'),0 , 2, resizable=True, clickable=True, start_width=200) )
        self.rule_list.append_column( f_col(_('Query Type'),0 , 3, resizable=True, clickable=True, start_width=200) )
        self.rule_list.append_column( f_col(_('Context ID'),0 , 4, resizable=True, clickable=True, start_width=200) )

        
        self.rule_list.set_tooltip_markup(_("""List of Rules learned after <b>adding Entries</b> and <b>reading Articles</b>
<b>Name</b> - Displayed name, <i>not matched</i>, purely informational
<b>REGEX String</b> - Regular Expression matched against tokenized Entry with prefixes and case markers
<b>Weight</b> - Weight added to Entry when the rule is matched (rule weights are offset by Entry weight to avoid overvaluing very long articles
<b>Query Type</b> - Is rule matched against exact words or stems?
<b>Context ID</b> - ID of the Entry the rule was extracted from
Hit <b>Ctrl-F</b> for interactive search""") )

        self.rule_list.set_enable_search(True)
        self.rule_list.set_search_equal_func(parent.quick_find_case_ins, 0)        

        scwindow.add(self.rule_list)

        done_button = f_button(_('Done'),'object-select-symbolic', connect=self.on_done)
        delete_all_button = f_button(_('Delete all'), 'edit-delete-symbolic', connect=self.on_delete_all)
        delete_all_button.set_tooltip_markup(_("""Delete <b>All</b> learned rules
<i>This process is PERMANENT</i>
Rules can be relearned for all read entries by CLI command:
<i>feedex --relearn</i>""") )

        grid.attach(header_label, 1,1, 12,1)
        grid.attach(scwindow, 1,2, 12, 10)
        grid.attach(done_button, 1,12, 2,1)
        grid.attach(delete_all_button, 10,12, 2,1)

        box.add(grid)
        self.show_all()
        self.rule_list.columns_autosize()


    def on_delete_all(self, *args):
        """ Deletes all learned rules after prompt """
        dialog = YesNoDialog(self, _('Clear All Learned Rules?'), _('Are you sure you want to clear <b>all leraned rules</b>?'), subtitle=f"<i>{_('This action cannot be reversed!')}</i>")           
        dialog.run()
        if dialog.response == 1:
            dialog.destroy()
            dialog2 = YesNoDialog(self, _('Clear All Learned Rules?'), _('Are you <b>really sure</b>?'))
            dialog2.run()
            if dialog2.response == 1:
                self.response = 1
                dialog2.destroy()
                self.close()
            else: 
                self.response = 0
                dialog2.destroy()
        else: 
            self.response = 0
            dialog.destroy()

    def on_done(self, *args):
        self.response = 0
        self.close()






class DisplayWindow(Gtk.Dialog):
    """ General purpose display window (options are text, text with emblem and a picture (downloaded or from file) """
    def __init__(self, parent, title, text, **kargs):

        Gtk.Dialog.__init__(self, title=title, transient_for=parent, flags=0)

        self.set_default_size(kargs.get('width',1000), kargs.get('height',500))
        box = self.get_content_area()

        self.set_border_width(10)
        self.set_resizable(False)
        self.set_position(Gtk.WindowPosition.CENTER)

        if kargs.get('close_on_unfocus',False): self.connect('focus-out-event', self.on_close)

        else:
            self.set_resizable(False)
            self.mode = 'text'
            win = Gtk.ScrolledWindow()
            win.set_border_width(8)
            vbox = Gtk.Box()
            vbox.set_orientation(Gtk.Orientation.VERTICAL)
            vbox.set_homogeneous(False)

            emblem = kargs.get('emblem')
            image = kargs.get('image')
            if emblem is not None:
                image = Gtk.Image.new_from_pixbuf(emblem)
                vbox.pack_start(image, False, False, 0)

            elif image is not None:
                image = Gtk.Image.new_from_file(image)
                vbox.pack_start(image, False, False, 0)


            self.label = f_label(text, justify=FX_ATTR_JUS_LEFT, wrap=True, selectable=True, markup=kargs.get('markup',True))
        
            win.add(vbox)
            vbox.pack_start(self.label, False, False, 0)


        bbox = Gtk.Box()
        bbox.set_orientation(Gtk.Orientation.HORIZONTAL)
        bbox.set_homogeneous(False)
        bbox.set_border_width(5)

        done_button = f_button(_('  Done  '), None, connect=self.on_close)
        bbox.pack_start(done_button, False, False, 5)

        grid = Gtk.Grid()
        grid.set_column_spacing(10)
        grid.set_row_spacing(10)
        grid.set_column_homogeneous(True)
        grid.set_row_homogeneous(True)

        grid.attach(win, 1,1, 35, 12)
        grid.attach(bbox, 1, 13, 35, 1)    

        box.add(grid)        
        self.show_all()

        
    def on_close(self, *args): self.close()








class AboutDialog(Gtk.Dialog):
    """ Display "About..." dialog """
    def __init__(self, parent, **kargs):

        Gtk.Dialog.__init__(self, title=_("About FEEDEX"), transient_for=parent, flags=0)

        self.set_default_size(kargs.get('width',500), kargs.get('height',250))

        box = self.get_content_area()

        pb = GdkPixbuf.Pixbuf.new_from_file_at_size(f"{FEEDEX_SYS_ICON_PATH}{DIR_SEP}feedex.png", 64, 64)

        icon = Gtk.Image.new_from_pixbuf(pb)
        main_label = f_label(None, justify=FX_ATTR_JUS_CENTER, wrap=True, markup=True)
        secondary_label = f_label(None, justify=FX_ATTR_JUS_CENTER, wrap=True, markup=True)
        author_label = f_label(None, justify=FX_ATTR_JUS_CENTER, wrap=True, markup=True)
        website_label = f_label(None, justify=FX_ATTR_JUS_CENTER, wrap=True, markup=True)

        close_button = f_button(_('   Close   '), None, connect=self.on_close)
        lbox = Gtk.Box()
        lbox.set_orientation(Gtk.Orientation.HORIZONTAL)
        lbox.set_homogeneous(True)
        pad_box = Gtk.Box()
        pad_box2 = Gtk.Box()

        lbox.pack_start(pad_box, False, False, 5)
        lbox.pack_start(close_button, False, False, 5)
        lbox.pack_start(pad_box2, False, False, 5)

        main_label.set_markup(f"<b>FEEDEX v. {FEEDEX_VERSION}</b>")
        secondary_label.set_markup(f"""{FEEDEX_DESC}
{_('Release')}: {FEEDEX_RELEASE}""")
        author_label.set_markup(f"""<i>{_('Author')}: {FEEDEX_AUTHOR}
{FEEDEX_CONTACT}</i>""")

        website_label.set_markup(f"""{_('Website')}: <a href="{esc_mu(FEEDEX_WEBSITE)}">{esc_mu(FEEDEX_WEBSITE)}</a>""")

        box.set_orientation(Gtk.Orientation.VERTICAL)
        box.set_homogeneous(True)
        box.pack_start(icon, False, False, 5)
        box.pack_start(main_label, False, False, 5)
        box.pack_start(secondary_label, False, False, 5)
        box.pack_start(author_label, False, False, 5)
        box.pack_start(website_label, False, False, 5)
        box.pack_start(lbox, False, False, 5)
        
        self.show_all()

    def on_close(self, *kargs):
        self.close()





class CalendarDialog(Gtk.Dialog):
    """ Date chooser for queries """
    def __init__(self, parent, **kargs):

        self.response = 0
        self.result = {'from_date':None,'to_date':None, 'date_string':None}

        Gtk.Dialog.__init__(self, title=_("Choose date range"), transient_for=parent, flags=0)
        self.set_default_size(kargs.get('width',400), kargs.get('height',200))
        box = self.get_content_area()

        from_label = f_label(_('  From:'), justify=FX_ATTR_JUS_LEFT, selectable=False, wrap=False)
        to_label = f_label(_('    To:'), justify=FX_ATTR_JUS_LEFT, selectable=False, wrap=False)

        self.from_clear_button = Gtk.CheckButton.new_with_label(_('Empty'))
        self.from_clear_button.connect('toggled', self.clear_from)
        self.to_clear_button = Gtk.CheckButton.new_with_label(_('Empty'))
        self.to_clear_button.connect('toggled', self.clear_to)

        accept_button = f_button(_('Accept'),'object-select-symbolic', connect=self.on_accept)
        cancel_button = f_button(_('Cancel'),'window-close-symbolic', connect=self.on_cancel)

        self.cal_from = Gtk.Calendar()
        self.cal_to = Gtk.Calendar()
        self.cal_from.connect('day-selected', self.on_from_selected)
        self.cal_to.connect('day-selected', self.on_to_selected)



        top_box = Gtk.HBox(homogeneous = False, spacing = 0)
        bottom_box = Gtk.HBox(homogeneous = False, spacing = 0)

        left_box = Gtk.VBox(homogeneous = False, spacing = 0)
        right_box = Gtk.VBox(homogeneous = False, spacing = 0)

        box.pack_start(top_box, False, False, 1)
        box.pack_start(bottom_box, False, False, 1)

        bottom_box.pack_start(cancel_button, False, False, 1)
        bottom_box.pack_end(accept_button, False, False, 1)

        top_box.pack_start(left_box, False, False, 1)
        top_box.pack_start(right_box, False, False, 1)

        left_box.pack_start(from_label, False, False, 1)
        left_box.pack_start(self.cal_from, False, False, 1)
        left_box.pack_start(self.from_clear_button, False, False, 1)

        right_box.pack_start(to_label, False, False, 1)
        right_box.pack_start(self.cal_to, False, False, 1)
        right_box.pack_start(self.to_clear_button, False, False, 1)

        self.show_all()
        self.on_to_selected()
        self.on_from_selected()

    def on_accept(self, *args):
        self.response = 1
        if not self.from_clear_button.get_active():
            (year, month, day) = self.cal_from.get_date()
            self.result['from_date'] = f'{scast(year,str,"")}/{scast(month+1,str,"")}/{scast(day,str,"")}'
        else: self.result['from_date'] = None

        if not self.to_clear_button.get_active():
            (year, month, day) = self.cal_to.get_date()
            self.result['to_date'] = f'{scast(year,str,"")}/{scast(month+1,str,"")}/{scast(day,str,"")}'
        else: self.result['to_date'] = None

        self.result['date_string'] = f"""{coalesce(self.result['from_date'], '...')} --- {coalesce(self.result['to_date'], '...')}"""
        self.close()

    def on_cancel(self, *args):
        self.response = 0
        self.result = {'from_date':None,'to_date':None, 'date_string':None}
        self.close()
        
    def clear_from(self, *args):

        if self.cal_from.get_sensitive():
            self.cal_from.set_sensitive(False)
        else:
            self.cal_from.set_sensitive(True)

    def clear_to(self, *args):
        if self.cal_to.get_sensitive():
            self.cal_to.set_sensitive(False)
        else:
            self.cal_to.set_sensitive(True)

    def on_from_selected(self, *args):
        (year, month, day) = self.cal_from.get_date()
        self.result['from_date'] = f'{scast(year,str,"")}/{scast(month+1,str,"")}/{scast(day,str,"")}'

    def on_to_selected(self, *args):
        (year, month, day) = self.cal_to.get_date()
        self.result['to_date'] = f'{scast(year,str,"")}/{scast(month+1,str,"")}/{scast(day,str,"")}'








class PreferencesDialog(Gtk.Dialog):
    """ Edit preferences dialog """
    def __init__(self, parent, config, **kargs):

        self.config = config
        self.config_def = config

        Gtk.Dialog.__init__(self, title=_('FEEDEX Preferences'), transient_for=parent, flags=0)
        box = self.get_content_area()

        self.set_border_width(10)
        self.set_resizable(False)
        self.set_position(Gtk.WindowPosition.CENTER)


        self.result = {}
        self.response = 0        

        self.desktop_notify_button = Gtk.CheckButton.new_with_label(_('Enable desktop notifications?') )
        self.desktop_notify_button.connect('clicked', self.on_changed)
        self.desktop_notify_button.set_tooltip_markup(_('Should Feedex send desktop notifications on incomming news?') )
        self.fetch_in_background_button = Gtk.CheckButton.new_with_label(_('Fetch news in the background?') )
        self.fetch_in_background_button.set_tooltip_markup(_('News will be checked in background and downloaded if Channels\'s fetching interval is exceeded'))
        
        default_interval_label = f_label(_('Default check interval:'))
        self.default_interval_entry = Gtk.Entry()
        self.default_interval_entry.set_tooltip_markup(_('Default fetching interval for newly added feeds'))
        
        rule_limit_label = f_label(_('Ranking rules limit:'))
        self.rule_limit_entry = Gtk.Entry()
        self.rule_limit_entry.set_tooltip_markup(_("""When ranking incomming news you can 
limit the number of rules to match.
Only those with N top weight will be checked.
This can help avoid unimportant terms influencing ranking
and prevent scaling problems for large datasets
Enter <b>0</b> for <b>no rule limit</b> (every rule will be checked)"""))

        self.learn_button = Gtk.CheckButton.new_with_label(_('Enable Keyword learning?'))
        self.learn_button.set_tooltip_markup(_("""If enabled, keywords are extracted and learned 
every time an article is read or marked as read.
Incomming news are then ranked agains the rules from those extracted keywords.
Feedex uses this ranking to get articles most likely interesting to you on top.
If disabled, no learning will take place and ranking will be done only against rules
that were manually added by user."""))


        self.notify_group_combo = f_group_combo(with_empty=True, connect=self.on_changed, tooltip=_("Should incoming news be grouped? How?") )

        self.notify_depth_combo = f_depth_combo(tooltip=_("""How many results should be shown for each grouping?
If no grouping is selected, it will simply show top results"""))

        default_entry_weight_label = f_label(_('New Entry default weight:'))
        self.default_entry_weight_entry = Gtk.Entry()
        self.default_entry_weight_entry.set_tooltip_markup(_('Default weight for manually added Entries for rule learning'))

        self.learn_from_added_button = Gtk.CheckButton.new_with_label(_('Learn from added Entries?'))
        self.learn_from_added_button.set_tooltip_markup(_('Should Feedex learn rules/keywords from manually added entries?\nUseful for utilizing highlights and notes for news ranking'))

        default_rule_weight_label = f_label(_('Rule default weight:'))
        self.default_rule_weight_entry = Gtk.Entry()
        self.default_rule_weight_entry.set_tooltip_markup(_('Default weight assigned to manually added rule (if not provided)'))

        default_similar_wieght_label = f_label(_('Weight for similarity search:'))
        self.default_similar_weight_entry = Gtk.Entry()
        self.default_similar_weight_entry.set_tooltip_markup(_('How much weight for ranking should items for which similar ones are searched for be given. Zero to disable'))
        
        new_color_label = f_label(_('Added entry color:'))
        new_color = Gdk.color_parse(self.config.get('gui_new_color','#0FDACA'))
        self.new_color_button = Gtk.ColorButton(color=new_color)

        del_color_label = f_label(_('Deleted color:'))
        del_color = Gdk.color_parse(self.config.get('gui_deleted_color','grey'))
        self.del_color_button = Gtk.ColorButton(color=del_color)

        hl_color_label = f_label(_('Search hilight color:'))
        hl_color = Gdk.color_parse(self.config.get('gui_deleted_color','grey'))
        self.hl_color_button = Gtk.ColorButton(color=hl_color)

        def_flag_color_label = f_label(_('Default flag color:'))
        def_flag_color = Gdk.color_parse(self.config.get('gui_default_flag_color','blue'))
        self.def_flag_color_button = Gtk.ColorButton(color=def_flag_color)


        key_search_label = f_label(_('Hotkey, open new Search Tab: Ctrl + '))
        self.key_search_entry = Gtk.Entry()

        key_new_entry_label = f_label(_('Hotkey, add New Entry: Ctrl + '))
        self.key_new_entry_entry = Gtk.Entry()

        key_new_rule_label = f_label(_('Hotkey, add New Rule: Ctrl + '))
        self.key_new_rule_entry = Gtk.Entry()

        layout_label = f_label(_('Layout:'))
        self.layout_combo = f_layout_combo(tooltip=_('How main window panes should be displayed? Requires restart'))

        orientation_label = f_label(_('Orientation:'))
        self.orientation_combo = f_orientation_combo(tooltip=_('Pane horizontal sequence'))

        lang_label = f_label(_('Language:'))
        self.lang_combo = f_loc_combo()


        self.ignore_images_button = Gtk.CheckButton.new_with_label(_('Ignore Images?'))
        self.ignore_images_button.set_tooltip_markup(_('Should images and icons be ignored alltogether? Ueful for better performance'))

        browser_label = f_label(_('Default WWW browser:'))
        self.browser_entry = Gtk.Entry()
        self.browser_entry.set_tooltip_markup(_('Command for opening in browser. Use <b>u%</b> symbol to substitute for URL'))
        browser_application_button = f_button(None,'view-app-grid-symbolic', connect=self.on_app_choose_browser, tooltip=_("Choose from installed applications"))

        self.external_iv_application_button = f_button(None,'view-app-grid-symbolic', connect=self.on_app_choose_iv, tooltip=_("Choose from installed applications"))
        external_iv_label = f_label(_('External image viewer:'))
        self.external_iv_entry = Gtk.Entry()
        self.external_iv_entry.set_tooltip_markup(_('Command for viewing images by clicking on them.\nUse <b>%u</b> symbol to substitute for temp filename\n<b>%t</b> symbol will be replaced by <b>title</b>\n<b>%a</b> symbol will be replaced by <b>alt</b> field'))

        self.external_txtv_application_button = f_button(None,'view-app-grid-symbolic', connect=self.on_app_choose_txtv, tooltip=_("Choose from installed applications"))
        external_txtv_label = f_label(_('External text file viewer:'))
        self.external_txtv_entry = Gtk.Entry()
        self.external_txtv_entry.set_tooltip_markup(_('Command for viewing text files.\nUse <b>%u</b> symbol to substitute for temp filename'))

        search_engine_label = f_label(_('Default WWW search engine:'))
        search_engine_combo, self.search_engine_entry = f_search_engine_combo()
        

        similarity_limit_label = f_label(_('Similarity query limit:'))
        self.similarity_limit_entry = Gtk.Entry()
        self.similarity_limit_entry.set_tooltip_markup(_('Limit similarity query items for improved query performance'))

        max_context_length_label = f_label(_('Max context length:'))
        self.max_context_length_entry = Gtk.Entry()
        self.max_context_length_entry.set_tooltip_markup(_('If the length of a context/snippet is greater than this number, it will not be shown in query results. Needed to avoid long snippets for wildcard searches'))

        default_depth_label = f_label(_('Default grouping depth:'))
        self.default_depth_entry = Gtk.Entry()
        self.default_depth_entry.set_tooltip_markup(_('How many results to show when grouping in a tree? If <b>0</b>, every result will be displayed'))


        error_threshold_label = f_label(_('Error threshold:'))
        self.error_threshold_entry = Gtk.Entry()
        self.error_threshold_entry.set_tooltip_markup(_('After how many download errors should a Channel be marked as unhealthy and ignored while fetching?'))

        self.ignore_modified_button = Gtk.CheckButton.new_with_label(_('Ignore modified Tags?'))
        self.ignore_modified_button.set_tooltip_markup(_('Should ETags and Modified fields be ignored while fetching? If yes, Feedex will fetch news even when publisher suggest not to (e.g. no changes where made to feed)'))

        clear_cache_label = f_label(_('Clear cached files older than how many days?'))
        self.clear_cache_entry = Gtk.Entry()
        self.clear_cache_entry.set_tooltip_markup(_('Files in cache include thumbnails and images. It is good to keep them but older items should release space'))

        db_label = f_label(_('Database:'))
        db_choose_button = f_button(None,'folder-symbolic', connect=self.on_file_choose_db, tooltip=_("Search filesystem"))
        self.db_entry = Gtk.Entry()
        self.db_entry.set_tooltip_markup(f"{_('Database file to be used for storage.')}\n<i>{_('Changes require application restart')}</i>")

        log_label = f_label('Log file:')
        log_choose_button = f_button(None,'folder-symbolic', connect=self.on_file_choose_log, tooltip=_("Search filesystem"))
        self.log_entry = Gtk.Entry()
        self.log_entry.set_tooltip_markup(_("Path to log file"))

        user_agent_label = f_label(_('User Agent:'))
        user_agent_combo, self.user_agent_entry = f_user_agent_combo(tooltip=f"""{_('User Agent string to be used when requesting URLs. Be careful, as some publishers are very strict about that.')} 
{_('Default is:')} {FEEDEX_USER_AGENT}
<b>{_('Changing this tag is not recommended and for debugging purposes only')}</b>""")

        self.do_redirects_button = Gtk.CheckButton.new_with_label(_('Redirect?'))
        self.do_redirects_button.set_tooltip_markup(_('Should HTTP redirects (codes:301, 302) be followed when fetching?'))

        self.save_redirects_button = Gtk.CheckButton.new_with_label(_('Save permanent redirects?'))
        self.save_redirects_button.set_tooltip_markup(_('Should permanent HTTP redirects (code: 301) be saved to DB?'))

        self.mark_deleted_button = Gtk.CheckButton.new_with_label(_('Mark deleted channels as unhealthy?'))
        self.mark_deleted_button.set_tooltip_markup(_('Should deleted channels (HTTP code 410) be marked as unhealthy to avoid fetching in the future?'))

        self.no_history_button = Gtk.CheckButton.new_with_label(_('Do not save queries in History?'))
        self.no_history_button.set_tooltip_markup(_('Should saving search phrases to History be ommitted?'))


        self.err_label = f_label('', markup=True)

        self.save_button = f_button(_('Save'),'object-select-symbolic', connect=self.on_save, tooltip=_("Save configuration") )
        self.cancel_button = f_button(_('Cancel'),'action-unavailable-symbolic', connect=self.on_cancel)
        self.restore_button = f_button(_('Restore'),'edit-redo-rtl-symbolic', connect=self.on_restore, tooltip=_("Restore preferences to defaults") )


        def create_grid():
            grid = Gtk.Grid()
            grid.set_column_spacing(8)
            grid.set_row_spacing(8)
            grid.set_column_homogeneous(False)
            grid.set_row_homogeneous(False)
            grid.set_border_width(5)
            return grid
        
        interface_grid = create_grid()    
        interface_grid.attach(lang_label, 1, 1, 3, 1)
        interface_grid.attach(self.lang_combo, 4, 1, 4,1)        
        interface_grid.attach(layout_label, 1, 2, 3, 1)
        interface_grid.attach(self.layout_combo, 4, 2, 4,1)        
        interface_grid.attach(orientation_label, 1, 3, 3, 1)
        interface_grid.attach(self.orientation_combo, 4, 3, 4,1)        
        interface_grid.attach(self.ignore_images_button, 1,4, 5,1)
        interface_grid.attach(new_color_label, 1,5, 3,1)
        interface_grid.attach(self.new_color_button, 4,5, 1,1)
        interface_grid.attach(del_color_label, 1,6, 3,1)
        interface_grid.attach(self.del_color_button, 4,6, 1,1)
        interface_grid.attach(hl_color_label, 1,7, 3,1)
        interface_grid.attach(self.hl_color_button, 4,7, 1,1)
        interface_grid.attach(def_flag_color_label, 1,8, 3,1)
        interface_grid.attach(self.def_flag_color_button, 4,8, 1,1)
        interface_grid.attach(key_search_label, 7, 5, 3, 1)
        interface_grid.attach(self.key_search_entry, 10, 5, 1,1)
        interface_grid.attach(key_new_entry_label, 7, 6, 3, 1)
        interface_grid.attach(self.key_new_entry_entry, 10, 6, 1,1)
        interface_grid.attach(key_new_rule_label, 7, 7, 3, 1)
        interface_grid.attach(self.key_new_rule_entry, 10, 7, 1,1)        

        fetching_grid = create_grid()
        fetching_grid.attach(self.desktop_notify_button, 1,1, 4,1)
        fetching_grid.attach(self.notify_group_combo, 5,1, 5,1)
        fetching_grid.attach(self.notify_depth_combo, 11,1, 4,1)
        fetching_grid.attach(self.fetch_in_background_button, 1,2, 4,1)
        fetching_grid.attach(default_interval_label, 1,3, 2,1)
        fetching_grid.attach(self.default_interval_entry, 4,3, 3,1)
        fetching_grid.attach(self.do_redirects_button, 1,4, 4,1)
        fetching_grid.attach(self.save_redirects_button , 1,5, 4,1)
        fetching_grid.attach(self.mark_deleted_button, 1,6, 4,1)
        fetching_grid.attach(self.ignore_modified_button, 1,7, 5,1)
        fetching_grid.attach(error_threshold_label, 1,8, 2,1)
        fetching_grid.attach(self.error_threshold_entry, 4,8, 3,1)
        fetching_grid.attach(user_agent_label, 1,9, 2,1)
        fetching_grid.attach(user_agent_combo, 4,9, 3,1)


        learn_grid = create_grid()
        learn_grid.attach(self.learn_button, 1,1, 6,1)
        learn_grid.attach(rule_limit_label, 1,2, 3,1)
        learn_grid.attach(self.rule_limit_entry, 4,2, 3,1)
        learn_grid.attach(self.learn_from_added_button, 1,3, 6,1)
        learn_grid.attach(similarity_limit_label, 1,5, 4,1)
        learn_grid.attach(self.similarity_limit_entry, 5,5, 3,1)
        learn_grid.attach(max_context_length_label, 1,6,4,1)
        learn_grid.attach(self.max_context_length_entry, 5,6,3,1)
        learn_grid.attach(default_depth_label, 1,7,4,1)
        learn_grid.attach(self.default_depth_entry, 5,7,2,1)
        
        learn_grid.attach(default_entry_weight_label, 1,8, 3,1)
        learn_grid.attach(self.default_entry_weight_entry, 4,8, 3,1)
        learn_grid.attach(default_rule_weight_label, 1, 9, 3,1)
        learn_grid.attach(self.default_rule_weight_entry, 4, 9, 3,1)
        learn_grid.attach(default_similar_wieght_label, 1,10,4,1)
        learn_grid.attach(self.default_similar_weight_entry, 5, 10, 3,1)


        system_grid = create_grid()
        system_grid.attach(clear_cache_label, 1,1, 5,1)
        system_grid.attach(self.clear_cache_entry, 7,1, 3,1)
        system_grid.attach(db_label, 1,2, 3,1)
        system_grid.attach(db_choose_button, 4,2, 1,1)
        system_grid.attach(self.db_entry, 5,2, 10,1)
        system_grid.attach(log_label, 1,3, 3,1)
        system_grid.attach(log_choose_button, 4,3, 1,1)
        system_grid.attach(self.log_entry, 5,3, 10,1)
        system_grid.attach(self.no_history_button, 1,5, 7,1)

        system_grid.attach(browser_label, 1,6, 4,1)
        system_grid.attach(browser_application_button, 5,6, 1,1)
        system_grid.attach(self.browser_entry, 6,6, 20,1)
        system_grid.attach(external_iv_label, 1,7, 4,1)
        system_grid.attach(self.external_iv_application_button, 5,7, 1,1)
        system_grid.attach(self.external_iv_entry, 6,7, 20,1)
        system_grid.attach(external_txtv_label, 1,8, 4,1)
        system_grid.attach(self.external_txtv_application_button, 5,8, 1,1)
        system_grid.attach(self.external_txtv_entry, 6,8, 20,1)
        system_grid.attach(search_engine_label, 1,9, 4,1)
        system_grid.attach(search_engine_combo, 6,9, 20,1)

        self.notebook = Gtk.Notebook()
        self.notebook.append_page(interface_grid, Gtk.Label(label=_("Interface")))
        self.notebook.append_page(fetching_grid, Gtk.Label(label=_("Fetching")))    
        self.notebook.append_page(learn_grid, Gtk.Label(label=_("Learning and Ranking")))
        self.notebook.append_page(system_grid, Gtk.Label(label=_("System")))    
    
        grid = create_grid()
        grid.attach(self.notebook, 1,1, 18,13)
        grid.attach(self.err_label, 1,14, 16,1)

        vbox = Gtk.Box()
        vbox.set_orientation(Gtk.Orientation.HORIZONTAL)
        vbox.set_homogeneous(False)
        vbox.set_border_width(5)

        vbox.pack_start(self.cancel_button, False, False, 5)
        vbox.pack_start(self.restore_button, False, False, 5)
        vbox.pack_end(self.save_button, False, False, 5)
            
        box.add(grid)
        box.add(vbox)

        self.on_restore()
        self.on_changed()

        self.show_all()



    def on_changed(self, *args):
        if self.desktop_notify_button.get_active(): 
            self.notify_group_combo.set_sensitive(True)
            self.notify_depth_combo.set_sensitive(True)
        else:
            self.notify_group_combo.set_sensitive(False)
            self.notify_depth_combo.set_sensitive(False)



    def on_file_choose_db(self, *args): self.file_choose('db')
    def on_file_choose_log(self, *args): self.file_choose('log')
    def file_choose(self, target, *args):
        if target == 'db':
            heading = _('Choose Database')
            if os.path.isfile(self.config.get('db_path')):
                start_dir = os.path.dirname(self.config.get('db_path'))
            else: start_dir = os.getcwd()
        elif target == 'log':
            heading = _('Choose Log File')
            if os.path.isfile(self.config.get('log')):
                start_dir = os.path.dirname(self.config.get('log'))
            else: start_dir = os.getcwd()

        dialog = Gtk.FileChooserDialog(heading, parent=self, action=Gtk.FileChooserAction.OPEN)
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
        dialog.set_current_folder(start_dir)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            filename = dialog.get_filename()
            if target == 'db': self.db_entry.set_text(filename)
            elif target == 'log': self.log_entry.set_text(filename)            
        dialog.destroy()




    def on_app_choose_browser(self, *args): self.app_choose('browser')
    def on_app_choose_iv(self, *args): self.app_choose('iv')
    def on_app_choose_txtv(self, *args): self.app_choose('txtv')


    def app_choose(self, target):

        if target == 'browser':
            heading = _("Choose Default Browser")
            content_type = "text/html"
        elif target == 'iv':
            heading = _("Choose Image Viewer")
            content_type = "image/jpeg"
        elif target == 'txtv':
            heading = _("Choose Text File Viewer")
            content_type = "text/plain"

        dialog = Gtk.AppChooserDialog(parent=self, content_type=content_type)
        dialog.set_heading(heading)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            app = dialog.get_app_info()
            command = app.get_string('Exec')
            if type(command) is str:
                if target == 'browser':
                    self.browser_entry.set_text(command)
                elif target == 'iv':
                    self.external_iv_entry.set_text(command)
                elif target == 'txtv':
                    self.external_txtv_entry.set_text(command)
        dialog.destroy()





    def on_restore(self, *args):

        if self.config.get('use_keyword_learning', True): self.learn_button.set_active(True)
        else: self.learn_button.set_active(False)

        self.rule_limit_entry.set_text(scast(self.config.get('rule_limit', 50000), str, _('<<ERROR>>')))

        if self.config.get('gui_desktop_notify',True): self.desktop_notify_button.set_active(True)
        else: self.desktop_notify_button.set_active(False)

        f_set_combo(self.notify_group_combo, self.config.get('gui_notify_group',None))
        f_set_combo(self.notify_depth_combo, self.config.get('gui_notify_depth',0))

        if self.config.get('gui_fetch_periodically',False): self.fetch_in_background_button.set_active(True)
        else: self.fetch_in_background_button.set_active(False)

        if self.config.get('do_redirects', False): self.do_redirects_button.set_active(True)
        else: self.do_redirects_button.set_active(False)

        if self.config.get('save_perm_redirects', False): self.save_redirects_button.set_active(True)
        else: self.save_redirects_button.set_active(False)

        if self.config.get('mark_deleted', False): self.mark_deleted_button.set_active(True)
        else: self.mark_deleted_button.set_active(False)


        self.default_interval_entry.set_text(scast(self.config.get('default_interval',45), str, _('<<ERROR>>')))

        self.default_entry_weight_entry.set_text(scast(self.config.get('default_entry_weight',2), str, _('<<ERROR>>')))

        if self.config.get('learn_from_added_entries',True): self.learn_from_added_button.set_active(True)
        else: self.learn_from_added_button.set_active(False)

        self.default_rule_weight_entry.set_text(scast(self.config.get('default_rule_weight',2), str, _('<<ERROR>>')))

        self.default_similar_weight_entry.set_text(scast(self.config.get('default_similar_weight',2), str, _('<<ERROR>>')))

        self.max_context_length_entry.set_text(scast(self.config.get('max_context_length',500), str, _('<<ERROR>>')))
        self.default_depth_entry.set_text(scast(self.config.get('default_depth',5), str, _('<<ERROR>>')))


        new_color = Gdk.color_parse(self.config.get('gui_new_color','#0FDACA'))
        self.new_color_button.set_color(new_color)
        del_color = Gdk.color_parse(self.config.get('gui_deleted_color','grey'))
        self.del_color_button.set_color(del_color)
        hl_color = Gdk.color_parse(self.config.get('gui_hilight_color','blue'))
        self.hl_color_button.set_color(hl_color)
        def_flag_color = Gdk.color_parse(self.config.get('gui_default_flag_color','blue'))
        self.def_flag_color_button.set_color(def_flag_color)

        f_set_combo(self.layout_combo, self.config.get('gui_layout',0))        
        f_set_combo(self.orientation_combo, self.config.get('gui_orientation',0))        
        f_set_combo(self.lang_combo, self.config.get('lang'))        
        
        if self.config.get('ignore_images',False): self.ignore_images_button.set_active(True)
        else: self.ignore_images_button.set_active(False)

        self.key_search_entry.set_text(coalesce(self.config.get('gui_key_search','s'), ''))
        self.key_new_entry_entry.set_text(coalesce(self.config.get('gui_key_new_entry','n'), ''))
        self.key_new_rule_entry.set_text(coalesce(self.config.get('gui_key_new_rule','r'), ''))

        self.browser_entry.set_text(coalesce(self.config.get('browser',''),''))
        self.external_iv_entry.set_text(coalesce(self.config.get('image_viewer',''),''))
        self.external_txtv_entry.set_text(coalesce(self.config.get('text_viewer',''),''))
        self.search_engine_entry.set_text(coalesce(self.config.get('search_engine',''),''))

        self.similarity_limit_entry.set_text(scast(self.config.get('default_similarity_limit',''),str,_('<<ERROR>>')))

        self.error_threshold_entry.set_text(scast(self.config.get('error_threshold',''), str,_('<<ERROR>>')))

        self.clear_cache_entry.set_text(scast(self.config.get('gui_clear_cache',30),str,_('<<ERROR>>')))

        if self.config.get('ignore_modified',True): self.ignore_modified_button.set_active(True)
        else: self.ignore_modified_button.set_active(False)

        self.db_entry.set_text(scast(self.config.get('db_path',''), str, _('<<ERROR>>')))
        self.log_entry.set_text(scast(self.config.get('log',''), str, _('<<ERROR>>')))

        self.user_agent_entry.set_text(scast(self.config.get('user_agent'), str, FEEDEX_USER_AGENT))

        if self.config.get('no_history', False): self.no_history_button.set_active(True)
        else: self.no_history_button.set_active(False)

        self.on_changed()


    def validate_entries(self, *args):
        self.get_data()
        err = validate_config(self.result, msg=True, old_config=self.config)
        if err != 0:
            self.err_label.set_markup(gui_msg(err))
            return False
        else:
            return True


    def get_data(self, *args):

        if self.learn_button.get_active(): self.result['use_keyword_learning'] = True
        else: self.result['use_keyword_learning'] = False

        self.result['rule_limit'] = nullif(self.rule_limit_entry.get_text(),'')

        if self.desktop_notify_button.get_active(): self.result['gui_desktop_notify'] = True
        else: self.result['gui_desktop_notify'] = False
        if self.fetch_in_background_button.get_active(): self.result['gui_fetch_periodically'] = True
        else: self.result['gui_fetch_periodically'] = False

        self.result['default_interval'] = nullif(self.default_interval_entry.get_text(),'')

        self.result['gui_notify_group'] = f_get_combo(self.notify_group_combo)
        self.result['gui_notify_depth'] = f_get_combo(self.notify_depth_combo)

        self.result['default_entry_weight'] = nullif(self.default_entry_weight_entry.get_text(),'')
       
        if self.learn_from_added_button.get_active(): self.result['learn_from_added_entries'] = True
        else: self.result['learn_from_added_entries'] = False

        if self.do_redirects_button.get_active(): self.result['do_redirects'] = True
        else: self.result['do_redirects'] = False

        if self.save_redirects_button.get_active(): self.result['save_perm_redirects'] = True
        else: self.result['save_perm_redirects'] = False

        if self.mark_deleted_button.get_active(): self.result['mark_deleted'] = True
        else: self.result['mark_deleted'] = False

        self.result['default_rule_weight'] = nullif(self.default_rule_weight_entry.get_text(),'')

        self.result['default_similar_weight'] = nullif(self.default_similar_weight_entry.get_text(),'')

        self.result['max_context_length'] = nullif(self.max_context_length_entry.get_text(),'')
        self.result['default_depth'] = nullif(self.default_depth_entry.get_text(),'')

        color = self.new_color_button.get_color()
        self.result['gui_new_color'] = color.to_string()
        color = self.del_color_button.get_color()
        self.result['gui_deleted_color'] = color.to_string()
        color = self.hl_color_button.get_color()
        self.result['gui_hilight_color'] = color.to_string()
        color = self.def_flag_color_button.get_color()
        self.result['gui_default_flag_color'] = color.to_string()

        self.result['gui_key_search'] = self.key_search_entry.get_text()
        self.result['gui_key_new_entry'] = self.key_new_entry_entry.get_text()
        self.result['gui_key_new_rule'] = self.key_new_rule_entry.get_text()

        self.result['gui_layout'] = f_get_combo(self.layout_combo)
        self.result['gui_orientation'] = f_get_combo(self.orientation_combo)
        self.result['lang'] = f_get_combo(self.lang_combo)

        self.result['browser'] = nullif(self.browser_entry.get_text(),'')
        self.result['image_viewer'] = nullif(self.external_iv_entry.get_text(),'')
        self.result['text_viewer'] = nullif(self.external_txtv_entry.get_text(),'')
        self.result['search_engine'] = nullif(self.search_engine_entry.get_text(),'')

        self.result['default_similarity_limit'] = nullif(self.similarity_limit_entry.get_text(),'')
        self.result['error_threshold'] = nullif(self.error_threshold_entry.get_text(),'')
        self.result['gui_clear_cache'] = nullif(self.clear_cache_entry.get_text(),'')

        if self.ignore_modified_button.get_active(): self.result['ignore_modified'] = True
        else: self.result['ignore_modified'] = False

        if self.ignore_images_button.get_active(): self.result['ignore_images'] = True
        else: self.result['ignore_images'] = False

        self.result['db_path'] = nullif(self.db_entry.get_text(),'')
        self.result['log'] = nullif(self.log_entry.get_text(),'')
        self.result['user_agent'] = coalesce(nullif(self.user_agent_entry.get_text(),''), FEEDEX_USER_AGENT)

        if self.no_history_button.get_active(): self.result['no_history'] = True
        else: self.result['no_history'] = False



    def on_save(self, *args):
        if self.validate_entries():
            self.response = 1
            self.close()

    def on_cancel(self, *args):
        self.response = 0
        self.result = {}
        self.close()










class DisplayKeywords(Gtk.Dialog):
    """ Display keywords for an Entry """

    def __init__(self, parent, header, store, **kargs):

        Gtk.Dialog.__init__(self, title=_('Keywords'), transient_for=parent, flags=0)

        self.set_default_size(kargs.get('width',1000), kargs.get('height',500))
        self.set_border_width(10)
        box = self.get_content_area()

        self.response = 0

        grid = Gtk.Grid()
        grid.set_column_spacing(10)
        grid.set_row_spacing(10)
        grid.set_column_homogeneous(True)
        grid.set_row_homogeneous(True)

        header_label = f_label(header, justify=FX_ATTR_JUS_LEFT, wrap=True, markup=True)

        scwindow = Gtk.ScrolledWindow()

        self.rule_store = store
        self.rule_list = Gtk.TreeView(model=self.rule_store)
        self.rule_list.append_column( f_col(_('Keyword'),0 , 0, resizable=True, clickable=True, start_width=300) )
        self.rule_list.append_column( f_col(_('Weight'),0 , 1, resizable=True, clickable=True, start_width=300) )

        self.rule_list.set_tooltip_markup(_("""Keywords extracted from entry
Hit <b>Ctrl-F</b> for interactive search"""))

        self.rule_list.set_enable_search(True)
        self.rule_list.set_search_equal_func(parent.quick_find_case_ins, 0)
        
        scwindow.add(self.rule_list)

        done_button = f_button(_('Done'),'object-select-symbolic', connect=self.on_done)
        grid.attach(header_label, 1,1, 12,1)
        grid.attach(scwindow, 1,2, 12, 10)
        grid.attach(done_button, 1,12, 2,1)

        box.add(grid)
        self.show_all()
        self.rule_list.columns_autosize()

    def on_done(self, *args):
        self.response = 0
        self.close()





class DisplayMatchedRules(Gtk.Dialog):
    """ Display rules matched for Entry """

    def __init__(self, parent, footer, store, **kargs):

        Gtk.Dialog.__init__(self, title=_('Matched Rules'), transient_for=parent, flags=0)

        self.set_default_size(kargs.get('width',1000), kargs.get('height',500))
        self.set_border_width(10)
        box = self.get_content_area()

        self.response = 0

        grid = Gtk.Grid()
        grid.set_column_spacing(10)
        grid.set_row_spacing(10)
        grid.set_column_homogeneous(True)
        grid.set_row_homogeneous(True)

        footer_label = f_label(footer, justify=FX_ATTR_JUS_LEFT, wrap=True, markup=True)

        scwindow = Gtk.ScrolledWindow()
        ftwindow = Gtk.ScrolledWindow()
        ftwindow.add(footer_label)

        self.rule_store = store
        self.rule_list = Gtk.TreeView(model=self.rule_store)
        self.rule_list.append_column( f_col(_('Name'),0 , 0, resizable=True, clickable=True, start_width=300) )
        self.rule_list.append_column( f_col(_('String'),0 , 1, resizable=True, clickable=True, start_width=300) )
        self.rule_list.append_column( f_col(_('Matched'),0 , 2, resizable=True, clickable=True, start_width=100) )
        self.rule_list.append_column( f_col(_('Learned?'),0 , 3, resizable=True, clickable=True, start_width=50) )
        self.rule_list.append_column( f_col(_('Case insensitive?'),0 , 4, resizable=True, clickable=True, start_width=50) )
        self.rule_list.append_column( f_col(_('Query type'),0 , 5, resizable=True, clickable=True, start_width=100) )
        self.rule_list.append_column( f_col(_('Field'),0 , 6, resizable=True, clickable=True, start_width=100) )
        self.rule_list.append_column( f_col(_('Feed/Category'),0 , 7, resizable=True, clickable=True, start_width=200) )
        self.rule_list.append_column( f_col(_('Language'),0 , 8, resizable=True, clickable=True, start_width=100) )
        self.rule_list.append_column( f_col(_('Weight'),0 , 9, resizable=True, clickable=True, start_width=100) )
        self.rule_list.append_column( f_col(_('Flag ID'),0 , 10, resizable=True, clickable=True, start_width=50) )
        self.rule_list.append_column( f_col(_('Flag name'),0 , 11, resizable=True, clickable=True, start_width=200) )
        self.rule_list.append_column( f_col(_('Additive?'),0 , 12, resizable=True, clickable=True, start_width=50) )
        self.rule_list.append_column( f_col(_('Context ID'),0 , 13, resizable=True, clickable=True, start_width=100) )

        self.rule_list.set_tooltip_markup(_("""Rules matched for this Entry
Hit <b>Ctrl-F</b> for interactive search"""))

        self.rule_list.set_enable_search(True)
        self.rule_list.set_search_equal_func(parent.quick_find_case_ins, 0)
        
        scwindow.add(self.rule_list)

        done_button = f_button(_('Done'),'object-select-symbolic', connect=self.on_done)
        grid.attach(scwindow, 1,1, 12, 10)
        grid.attach(ftwindow, 1,13, 12, 3)
        
        grid.attach(done_button, 1,18, 2,1)

        box.add(grid)
        self.show_all()
        self.rule_list.columns_autosize()

    def on_done(self, *args):
        self.response = 0
        self.close()










class ArchiveDialog(Gtk.Dialog):
    """ Dialog for setting up archiving options """
    def __init__(self, parent, config, **kargs):

        self.config = config

        self.response = 0
        self.results = {}

        Gtk.Dialog.__init__(self, title=_('Archive...'), transient_for=parent, flags=0)
        box = self.get_content_area()

        self.set_border_width(10)
        self.set_resizable(False)
        self.set_position(Gtk.WindowPosition.CENTER)

        self.time_combo = f_archive_time_combo(tooltip=_("""Which Entries should be archived?"""))

        target_db_label = f_label(_('Target Database:'))
        self.target_db_entry = Gtk.Entry()
        self.target_db_entry.set_tooltip_markup(_("Database in which entries should be archived"))
        self.target_db_button = f_button(None,'folder-symbolic', connect=self.file_choose, tooltip=_("Search filesystem"))

        self.with_rules_button = Gtk.CheckButton.new_with_label(_('Archive Rules as well?'))
        self.with_rules_button.set_tooltip_markup(_('Should old rules be archived? If yes, they will no longer be used in ranking'))
        self.with_rules_button.set_active(False)

        self.no_read_button = Gtk.CheckButton.new_with_label(_('Keep read Entries?'))
        self.no_read_button.set_tooltip_markup(_('If checked, read Entries will be kept in current database and not archived'))
        self.no_read_button.set_active(False)

        self.no_flag_button = Gtk.CheckButton.new_with_label(_('Keep flagged Entries?'))
        self.no_flag_button.set_tooltip_markup(_('If checked, read Entries will be kept in current database and not archived'))
        self.no_flag_button.set_active(False)


        self.archive_button = f_button(_('Archive'),'object-select-symbolic', connect=self.on_archive, tooltip=_("Start archiving"))
        self.cancel_button = f_button(_('Cancel'),'action-unavailable-symbolic', connect=self.on_cancel)

        grid = Gtk.Grid()
        grid.set_column_spacing(3)
        grid.set_row_spacing(3)
        grid.set_column_homogeneous(True)
        grid.set_row_homogeneous(True)

        grid.attach(self.time_combo, 1,1, 9,1)
        grid.attach(target_db_label, 1,2, 3,1)
        grid.attach(self.target_db_entry, 4,2, 5,1)
        grid.attach(self.target_db_button, 9,2, 1,1)
        grid.attach(self.with_rules_button, 1,3, 5,1)
        grid.attach(self.no_read_button, 1,4, 5,1)
        grid.attach(self.no_flag_button, 1,5, 5,1)

        vbox = Gtk.Box()
        vbox.set_orientation(Gtk.Orientation.HORIZONTAL)
        vbox.set_homogeneous(False)
        vbox.set_border_width(5)

        vbox.pack_start(self.cancel_button, False, False, 5)
        vbox.pack_end(self.archive_button, False, False, 5)
            
        box.add(grid)
        box.add(vbox)

        self.show_all()


    def on_cancel(self, *args, **kargs): 
        self.response = 0
        self.close()

    def file_choose(self, target, *args):
        """ File-chooser dialog for target DB"""
        dialog = Gtk.FileChooserDialog(_('Choose Archive DB'), parent=self, action=Gtk.FileChooserAction.SAVE)
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_SAVE, Gtk.ResponseType.OK)
        dialog.set_current_folder(os.environ['HOME'])
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            filename = dialog.get_filename()
            self.target_db_entry.set_text(filename)
        dialog.destroy()


    def on_archive(self, *args, **kargs):
        """ Accept archiving """
        dialog = YesNoDialog(self, _('Archive DB'), _('Are you sure you want to archive old Entries? This operation may take a long time.') )
        dialog.run()
        if dialog.response == 1:
            target_db = self.target_db_entry.get_text()
            time = f_get_combo(self.time_combo)
            if self.with_rules_button.get_active() is True: with_rules = True
            else: with_rules = False
            if self.no_read_button.get_active() is True: no_read = True
            else: no_read = False
            if self.no_flag_button.get_active() is True: no_flag = True
            else: no_flag = False

            self.results['target_db'] = target_db
            self.results['time'] = time
            self.results['with_rules'] = with_rules
            self.results['no_read'] = no_read
            self.results['no_flagged'] = no_flag
            
            self.response = 1

            self.close()
        else:
            self.response = 0
        dialog.destroy()



