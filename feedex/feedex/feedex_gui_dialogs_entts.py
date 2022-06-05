# -*- coding: utf-8 -*-
""" GUI dialog windows classes for FEEDEX """

from feedex_gui_utils import *





class NewFromURL(Gtk.Dialog):
    """ Add from URL dialog with category and handler choice """
    def __init__(self, parent, feed, **kargs):

        if isinstance(feed, FeedContainer): self.feed = feed
        else: raise TypeError

        Gtk.Dialog.__init__(self, title=_("Add Channel from URL"), transient_for=parent, flags=0)
        self.set_border_width(10)
        self.set_default_size(kargs.get('width',800), kargs.get('height',100))
        box = self.get_content_area()

        self.url_entry = Gtk.Entry()
        self.url_entry.set_text( scast(self.feed['url'], str, '')  )

        self.cat_combo = f_feed_combo(parent.FX, tooltip=_("Choose Category to assign this Channel to\nCategories are useful for quick filtering and organizing Channels") )
        f_set_combo(self.cat_combo, self.feed['parent_id'])

        self.handler_combo = f_handler_combo(local=False, connect=self.on_changed )
        f_set_combo(self.handler_combo, self.feed['handler'])

        self.add_button = f_button(_('Add'),'list-add-symbolic', connect=self.on_add)
        self.cancel_button = f_button(_('Cancel'),'action-unavailable-symbolic', connect=self.on_cancel)

        self.response = 0

        vbox = Gtk.Box()
        vbox.set_orientation(Gtk.Orientation.HORIZONTAL)
        vbox.set_homogeneous(False)
        vbox.set_border_width(5)
        vbox.pack_start(self.cat_combo, False, False, 5)
        vbox.pack_start(self.handler_combo, False, False, 5)

        vbox2 = Gtk.Box()
        vbox2.set_orientation(Gtk.Orientation.HORIZONTAL)
        vbox2.set_homogeneous(False)
        vbox2.set_border_width(5)

        vbox2.pack_start(self.cancel_button, False, False, 5)
        vbox2.pack_end(self.add_button, False, False, 5)
            
        box.add(self.url_entry)
        box.add(vbox)
        box.add(vbox2)
        self.show_all()
        self.on_changed()


    def on_changed(self, *args):
        handler = f_get_combo(self.handler_combo)
        if handler == 'rss':
            self.url_entry.set_tooltip_markup(_("Enter Channel's <b>URL</b> here"))
        else:
            self.url_entry.set_tooltip_markup(_("Enter Channel's <b>URL</b> here"))

    def get_data(self, *args):
        """ Populate result from form contents """
        handler = f_get_combo(self.handler_combo)
        category = f_get_combo(self.cat_combo)
        self.feed.clear()
        self.feed['handler'] = handler
        self.feed['parent_id'] = category
        self.feed['url'] = self.url_entry.get_text()

    def on_cancel(self, *args):
        self.response = 0
        self.get_data()
        self.close()

    def on_add(self, *args):
        self.response = 1
        self.get_data()
        self.close()





class EditCategory(Gtk.Dialog):
    """ Edit category dialog (change title and subtitle) """
    def __init__(self, parent, category, **kargs):

        self.category = category
        self.new = kargs.get('new',True)
        if self.new: title = _("Add New Category")
        else: title = f"{_('Edit ')}{self.category.name()}{ _('Category')}"

        Gtk.Dialog.__init__(self, title=title, transient_for=parent, flags=0)
        self.set_border_width(10)
        self.set_default_size(kargs.get('width',800), kargs.get('height',150))
        box = self.get_content_area()

        name_label = f_label(_('Name:'), wrap=False)
        subtitle_label = f_label(_('Subtitle:'), wrap=False)
        self.name_entry = Gtk.Entry()
        self.name_entry.set_tooltip_markup(_('Enter Category name here'))
        self.subtitle_entry = Gtk.Entry()
        self.subtitle_entry.set_tooltip_markup(_('Enter subtitle/description name here'))

        icon_label = f_label(_('Icon:'))
        icon_combo, self.icon_entry = f_feed_icon_combo(tooltip=_('Choose icon for this Category'))
        self.icon_button = f_button(None, 'folder-symbolic', connect=self._on_choose_icon, tooltip=_('Search local machine for icons'))        

        save_button = f_button(_('Save'),'object-select-symbolic', connect=self.on_save)
        cancel_button = f_button(_('Cancel'),'action-unavailable-symbolic', connect=self.on_cancel)
        clear_button = f_button(_('Restore'),'edit-redo-rtl-symbolic', connect=self.on_restore)
    
        self.response = 0
        self.result = {}

        grid = Gtk.Grid()
        grid.set_column_spacing(10)
        grid.set_row_spacing(10)
        grid.set_column_homogeneous(True)
        grid.set_row_homogeneous(True)
        
        grid.attach(name_label, 1,1, 3,1)
        grid.attach(subtitle_label, 1,2, 3,1)
        grid.attach(self.name_entry, 4,1, 12,1)
        grid.attach(self.subtitle_entry, 4,2, 12,1)
        grid.attach(icon_label, 1,3, 3,1)
        grid.attach(icon_combo, 4,3, 4,1)
        grid.attach(self.icon_button, 8,3, 1,1)
        
        vbox = Gtk.Box()
        vbox.set_orientation(Gtk.Orientation.HORIZONTAL)
        vbox.set_homogeneous(False)
        vbox.set_border_width(5)

        vbox.pack_start(cancel_button, False, False, 5)
        vbox.pack_start(clear_button, False, False, 5)
        vbox.pack_end(save_button, False, False, 5)
            
        box.add(grid)
        box.add(vbox)

        self.on_restore()
        self.show_all()


    def on_restore(self, *args):
        """ Restore data to defaults """
        self.name_entry.set_text(scast(self.category.backup_vals.get('name'), str, ''))
        self.subtitle_entry.set_text(scast(self.category.backup_vals.get('subtitle'), str, ''))
        self.icon_entry.set_text(scast(self.category.backup_vals.get('icon_name'), str, ''))

    def get_data(self):
        idict = {
        'name': nullif(self.name_entry.get_text(),''),
        'title': nullif(self.name_entry.get_text(),''),
        'subtitle': nullif(self.subtitle_entry.get_text(),''),
        'icon_name': nullif(self.icon_entry.get_text(),''),
        'is_category': 1
        }
        self.category.add_to_update(idict)


    def _choose_file(self, *args, **kargs):
        dialog = Gtk.FileChooserDialog(kargs.get('title',_("Choose file")), parent=self, action=Gtk.FileChooserAction.OPEN)
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK)

        dialog.set_current_folder(kargs.get('start_dir', os.getcwd()))
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            filename = dialog.get_filename()
        else: filename = False
        dialog.destroy()
        return filename

    def _on_choose_icon(self, *args, **kargs):
        sfile = scast(self.category.backup_vals.get('icon_name',''), str, '')
        if os.path.isfile(sfile):
            start_dir = os.path.dirname(sfile)
        else: start_dir = os.getcwd()

        filename = self._choose_file(title=_('Choose Image'), start_dir=start_dir)
        if filename is not False: self.icon_entry.set_text(filename)


    def on_cancel(self, *args):
        self.response = 0
        self.close()

    def on_save(self, *args):
        self.response = 1
        self.get_data()
        self.close()








class EditEntry(Gtk.Dialog):
    """ Edit Entry dialog """
    def __init__(self, parent, config, entry, **kargs):

        self.entry = entry

        self.short = kargs.get('short',False)

        self.new = kargs.get('new',True)
        if self.new:
            title = _('Add new Entry')
            restore_label = _('Clear')
        else: 
            title = _('Edit Entry')
            restore_label = _('Restore')

        self.config = config

        Gtk.Dialog.__init__(self, title=title, transient_for=parent, flags=0)
        self.set_default_size(kargs.get('width',800), kargs.get('height',500))
        box = self.get_content_area()

        self.set_border_width(10)
        self.set_resizable(False)
        self.set_position(Gtk.WindowPosition.CENTER)

        self.result = {}
        self.response = 0
        
        self.cat_combo = f_feed_combo(parent.FX, with_feeds=True, no_empty=True, icons=parent.icons, tooltip=_("""Choose <b>Category</b> or <b>Channel</b> to assign this Entry to.
It is a good idea to have categories exclusively for manually added entries for quick access to notes, hilights etc.
<i>Every Entry needs to be assigned to a Category or a Channel</i>"""))

        self.note_combo = f_note_combo(search=False, tooltip=_("""How should this entry be classified?"""))

        title_label = f_label(f'<b>{_("Title")}:</b>', wrap=False, markup=True)
        self.title_entry = Gtk.Entry()
        self.title_entry.set_tooltip_markup(_("Enter Entry's title here"))

        author_label = f_label(f'<b>{_("Author")}:</b>', wrap=False, markup=True)
        self.author_entry = Gtk.Entry()

        publisher_label = f_label(f'<b>{_("Publisher")}:</b>', wrap=False, markup=True)
        self.publisher_entry = Gtk.Entry()

        contributors_label = f_label(f'<b>{_("Contributors")}:</b>', wrap=False, markup=True)
        self.contributors_entry = Gtk.Entry()

        comments_label = f_label(f'<b>{_("Comments")}:</b>', wrap=False, markup=True)
        self.comments_entry = Gtk.Entry()

        author_contact_label = f_label(f'<b>{_("Author contact")}:</b>', wrap=False, markup=True)
        self.author_contact_entry = Gtk.Entry()
        publisher_contact_label = f_label(f'<b>{_("Publisher contact")}:</b>', wrap=False, markup=True)
        self.publisher_contact_entry = Gtk.Entry()


        category_label = f_label(f'<b>{_("Category")}:</b>', wrap=False, markup=True)
        self.category_entry = Gtk.Entry()

        tags_label = f_label(f'<b>{_("Tags")}:</b>', wrap=False, markup=True)
        self.tags_entry = Gtk.Entry()

        link_label = f_label(f'<b>{_("Link")}:</b>', wrap=False, markup=True)
        self.link_entry = Gtk.Entry()



        desc_label = f_label(f'<b>{_("Description")}:</b>',  wrap=False, markup=True)
        desc_sw = Gtk.ScrolledWindow()
        self.desc_text = Gtk.TextBuffer()
        desc_entry = Gtk.TextView(buffer=self.desc_text)
        desc_entry.set_tooltip_markup(_("Enter Entry's details/description here"))
        desc_entry.set_wrap_mode(Gtk.WrapMode.WORD)
        desc_sw.add(desc_entry)

        text_label = f_label(f'<b>{_("Additional text")}:</b>',  wrap=False, markup=True)
        text_sw = Gtk.ScrolledWindow()
        self.text_text = Gtk.TextBuffer()
        text_entry = Gtk.TextView(buffer=self.text_text)
        text_entry.set_tooltip_markup(_('Enter additional text here'))
        text_entry.set_wrap_mode(Gtk.WrapMode.WORD)
        text_sw.add(text_entry)

        self.learn_button = Gtk.CheckButton.new_with_label(_('Learn rules?'))
        self.learn_button.set_tooltip_markup(_("""Should Feedex extract Rules from this entry for ranking incomming entries by importance?
See <b>Rules</b>->Right-Click-><b>Show learned rules</b> to see those and weights assigned to them
Rules are also learned automatically when any Entry/Article is opened in Browser""") )

        self.save_button = f_button(_('  Save  '),'object-select-symbolic', connect=self.on_save)
        self.cancel_button = f_button(_('Cancel'),'action-unavailable-symbolic', connect=self.on_cancel)
        self.clear_button = f_button(restore_label ,'edit-redo-rtl-symbolic', connect=self.on_restore)

        header_grid = Gtk.Grid()
        header_grid.set_column_spacing(1)
        header_grid.set_row_spacing(1)
        header_grid.set_column_homogeneous(True)
        header_grid.set_row_homogeneous(True)

        header_grid.attach(self.cat_combo, 1,1, 11, 1)
        header_grid.attach(self.note_combo, 13,1, 3, 1)

        header_grid.attach(title_label, 1,2, 3,1)
        header_grid.attach(self.title_entry, 4,2, 10,1)
        header_grid.attach(author_label, 1,3, 3,1)
        header_grid.attach(self.author_entry, 4,3, 10,1)
        header_grid.attach(category_label, 1,4, 3,1)
        header_grid.attach(self.category_entry, 4,4, 10,1)
        header_grid.attach(link_label, 1,5, 3,1)
        header_grid.attach(self.link_entry, 4,5, 10,1)
        header_grid.attach(tags_label, 1,6, 3,1)
        header_grid.attach(self.tags_entry, 4,6, 10,1)
        header_grid.attach(publisher_label, 1,7, 3,1)
        header_grid.attach(self.publisher_entry, 4,7, 10,1)
        header_grid.attach(contributors_label, 1,8, 3,1)
        header_grid.attach(self.contributors_entry, 4,8, 10,1)
        header_grid.attach(comments_label, 1,9, 3,1)
        header_grid.attach(self.comments_entry, 4,9, 10,1)
        header_grid.attach(author_contact_label, 1,10, 3,1)
        header_grid.attach(self.author_contact_entry, 4,10, 10,1)
        header_grid.attach(publisher_contact_label, 1,11, 3,1)
        header_grid.attach(self.publisher_contact_entry, 4,11, 10,1)


        scrbox_header = Gtk.ScrolledWindow()
        scrbox_header.add(header_grid)

        grid = Gtk.Grid()
        grid.set_column_spacing(3)
        grid.set_row_spacing(3)
        grid.set_column_homogeneous(True)
        grid.set_row_homogeneous(True)

        if self.short:
            grid.attach(scrbox_header, 1,1, 15, 3)

            grid.attach(desc_label, 1,4 , 4,1)
            grid.attach(desc_sw, 1,5, 15,12)
            grid.attach(text_label, 1,18, 4,1)
            grid.attach(text_sw, 1,19, 15,5)

        else:
            grid.attach(scrbox_header, 1,1, 15, 8)

            grid.attach(desc_label, 1,10 , 4,1)
            grid.attach(desc_sw, 1,11, 15,6)
            grid.attach(text_label, 1,18, 4,1)
            grid.attach(text_sw, 1,19, 15,5)

        if self.new:
            grid.attach(self.learn_button, 1, 25, 6,1)

        hbox_buttons = Gtk.Box()
        hbox_buttons.set_orientation(Gtk.Orientation.HORIZONTAL)
        hbox_buttons.set_homogeneous(False)
        hbox_buttons.set_border_width(5)

        hbox_buttons.pack_start(self.cancel_button, False, False, 5)
        hbox_buttons.pack_start(self.clear_button, False, False, 5)
        hbox_buttons.pack_end(self.save_button, False, False, 5)
            
        box.add(grid)
        self.err_label = f_label('', wrap=False, markup=True)
        box.add(self.err_label)
        box.add(hbox_buttons)
    
        self.on_restore()
        self.show_all()

        self.title_entry.grab_focus()




    def get_data(self):
        idict = { 'feed_or_cat': f_get_combo(self.cat_combo),
                    'notes': f_get_combo(self.note_combo),
                    'title': nullif(self.title_entry.get_text(),''), 

                    'author': nullif(self.author_entry.get_text(),''), 
                    'publisher': nullif(self.publisher_entry.get_text(),''), 
                    'contributors': nullif(self.contributors_entry.get_text(),''), 
                    'category': nullif(self.category_entry.get_text(),''), 
                    'tags': nullif(self.tags_entry.get_text(),''), 
                    'link': nullif(self.link_entry.get_text(),''), 

                    'comments': nullif(self.comments_entry.get_text(),''), 
                    'author_contact': nullif(self.author_contact_entry.get_text(),''), 
                    'publisher_contact': nullif(self.publisher_contact_entry.get_text(),''), 

                    'desc': nullif(self.desc_text.get_text(self.desc_text.get_start_iter(), self.desc_text.get_end_iter(), False),''), 
                    'text': nullif(self.text_text.get_text(self.text_text.get_start_iter(), self.text_text.get_end_iter(), False),'')}

        if self.learn_button.get_active(): self.entry.learn = True
        else: self.entry.learn = False

        if self.new: 
            idict['pubdate_str'] = datetime.now()
            self.entry.merge(idict)
        else: self.entry.add_to_update(idict)


    def on_restore(self, *args):
        f_set_combo(self.cat_combo, self.entry.backup_vals.get('feed_id'))
        f_set_combo(self.note_combo, self.entry.backup_vals.get('note'))
        self.title_entry.set_text(scast(self.entry.backup_vals.get('title'), str, ''))

        self.author_entry.set_text(scast(self.entry.backup_vals.get('author'), str, ''))
        self.publisher_entry.set_text(scast(self.entry.backup_vals.get('publisher'), str, ''))
        self.contributors_entry.set_text(scast(self.entry.backup_vals.get('contributors'), str, ''))
        self.category_entry.set_text(scast(self.entry.backup_vals.get('category'), str, ''))
        self.tags_entry.set_text(scast(self.entry.backup_vals.get('tags'), str, ''))
        self.link_entry.set_text(scast(self.entry.backup_vals.get('link'), str, ''))
        self.comments_entry.set_text(scast(self.entry.backup_vals.get('comments'), str, ''))
        self.author_contact_entry.set_text(scast(self.entry.backup_vals.get('author_contact'), str, ''))
        self.publisher_contact_entry.set_text(scast(self.entry.backup_vals.get('publisher_contact'), str, ''))

        self.desc_text.set_text(scast(self.entry.backup_vals.get('desc'), str, ''))
        self.text_text.set_text(scast(self.entry.backup_vals.get('text'), str, ''))
        if self.config.get('learn_from_added_entries',True): self.learn_button.set_active(True)        
        else: self.learn_button.set_active(False)

    def validate(self):
        err = self.entry.validate()
        if err != 0: 
            self.err_label.set_markup(gui_msg(err))
            return False                    
        return True

    def on_save(self, *args):
        self.get_data()
        if self.validate():
            self.response = 1
            self.close()

    def on_cancel(self, *args):
        self.response = 0
        self.get_data()
        self.close()






class EditFlag(Gtk.Dialog):
    """ Rule Edit dialog """
    def __init__(self, parent, config, flag, **kargs):

        self.new = kargs.get('new',True)

        if self.new: title = _('Add new Flag')
        else: title = _('Edit Flag')

        self.config = config
        self.flag = flag

        self.parent = parent

        Gtk.Dialog.__init__(self, title=title, transient_for=parent, flags=0)
        self.set_default_size(kargs.get('width',500), kargs.get('height',200))
        box = self.get_content_area()

        self.set_border_width(10)
        self.set_resizable(False)
        self.set_position(Gtk.WindowPosition.CENTER)

        self.result = {}
        self.response = 0

        name_label = f_label(_('Name:'), wrap=False)
        self.name_entry = Gtk.Entry()
        self.name_entry.set_tooltip_markup(_('Display name for this Flag used in Queries etc.'))
        desc_label = f_label('Description:', wrap=False)
        self.desc_entry = Gtk.Entry()

        color_label = f_label(_('Color:'))
        color = Gdk.color_parse( coalesce( self.parent.FX.get_flag_color(self.flag['id']), self.config.get('gui_default_flag_color','blue') )  )
        self.color_button = Gtk.ColorButton(color=color)

        color_cli_label = f_label(_('Color (CLI):'))
        self.color_cli_combo = f_cli_color_combo()

        id_label = f_label(_('ID:'), wrap=False)
        self.id_entry = Gtk.Entry()
        self.id_entry.set_tooltip_markup(_("""Sometimes it is useful to set up ID manually e.g. to add description to flag deleted before""") )

        self.err_label = f_label('', wrap=False)

        self.save_button = f_button(_('Save'),'object-select-symbolic', connect=self.on_save)
        self.cancel_button = f_button(_('Cancel'),'action-unavailable-symbolic', connect=self.on_cancel)
        self.restore_button = f_button(_('Restore'),'edit-redo-rtl-symbolic', connect=self.on_restore)

        grid = Gtk.Grid()
        grid.set_column_spacing(2)
        grid.set_row_spacing(2)
        grid.set_column_homogeneous(True)
        grid.set_row_homogeneous(True)
 
        grid.attach(name_label, 1,1, 2,1)
        grid.attach(self.name_entry, 4,1, 5,1)
        grid.attach(desc_label, 1,2, 2,1)
        grid.attach(self.desc_entry, 4,2, 5,1)

        grid.attach(color_label, 1,3, 2,1)
        grid.attach(self.color_button, 4,3, 1,1)

        grid.attach(color_cli_label, 1,4, 2,1)
        grid.attach(self.color_cli_combo, 4,4, 2,1)

        grid.attach(id_label, 1,5, 3,1)
        grid.attach(self.id_entry, 4,5, 2,1)
 
        grid.attach(self.err_label, 1,6, 8,1)

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
        self.show_all()

        self.name_entry.grab_focus()




    def on_restore(self, *args):
        self.name_entry.set_text(coalesce(self.flag.backup_vals.get('name',''),''))
        self.desc_entry.set_text(coalesce(self.flag.backup_vals.get('desc',''),''))
        f_set_combo(self.color_cli_combo, self.flag.backup_vals.get('color_cli'))
        color = Gdk.color_parse( coalesce(self.flag.backup_vals.get('color'), self.config.get('gui_default_flag_color','blue')))
        self.color_button.set_color(color)
        self.id_entry.set_text( scast(coalesce(self.flag.backup_vals.get('id',''),''), str, ''))


    def validate(self):
        err = self.flag.validate()
        if err != 0: 
            self.err_label.set_markup(gui_msg(err))
            return False                    
        return True


    def get_data(self):
        idict = {   'name': nullif(self.name_entry.get_text().strip(),''),
                    'desc': nullif(self.desc_entry.get_text(),''), 
                    'color_cli': f_get_combo(self.color_cli_combo),
                    'id' : scast(nullif(self.id_entry.get_text().strip(),''), int, None)
                    }
        color = self.color_button.get_color()
        idict['color'] = color.to_string()

        if self.new: self.flag.merge(idict)
        else: self.flag.add_to_update(idict, allow_id=True)
    

    def on_save(self, *args):
        self.get_data()            
        if self.validate():
            self.response = 1
            self.close()

    def on_cancel(self, *args):
        self.response = 0
        self.get_data()
        self.close()










class EditRule(Gtk.Dialog):
    """ Rule Edit dialog """
    def __init__(self, parent, config, rule, **kargs):

        self.new = kargs.get('new',True)

        if self.new: title = _('Add new Rule')
        else: title = _('Edit Rule')

        self.config = config
        self.rule = rule

        self.FX = parent.FX

        Gtk.Dialog.__init__(self, title=title, transient_for=parent, flags=0)
        self.set_default_size(kargs.get('width',1000), kargs.get('height',400))
        box = self.get_content_area()

        self.set_border_width(10)
        self.set_resizable(False)
        self.set_position(Gtk.WindowPosition.CENTER)

        self.result = {}
        self.response = 0

        name_label = f_label(_('Name:'), wrap=False)
        self.name_entry = Gtk.Entry()
        self.name_entry.set_tooltip_markup(_('Display name for this rule (<i>not used in matching</i>)'))
        string_label = f_label(_('Search string:'), wrap=False)
        self.string_entry = Gtk.Entry()
        self.string_entry.set_tooltip_markup(_("""String or Pattern used for search and matching
It is used according to <b>Type</b> and should be compatibile with it (e.g. REGEX string)""") )

        type_label = f_label(_('Type:'), wrap=False)
        self.type_combo = f_query_type_combo(connect=self.on_changed, rule=True)
        feed_label = f_label(_('Channel or Category:'), wrap=False)
        self.feed_combo = f_feed_combo(parent.FX, icons=parent.icons, with_feeds=True, empty_label=_('-- Every Feed --'), tooltip=_("Which Feed/Channel should this Rule filter?") )
        field_label = f_label(_('Field:'),wrap=False)
        self.field_combo = f_field_combo(connect=self.on_changed)
        lang_label = f_label(_('Language:'), wrap=False)
        self.lang_combo = f_lang_combo(parent.FX, connect=self.on_changed, tooltip=_("Which language should this rule use for Full Text Search?") )
        case_label = f_label(_('Case:'), wrap=False)
        self.case_combo = f_dual_combo( ((0,_("Case sensitive")),(1,_("Case insensitive"))), connect=self.on_changed, tooltip=_('Should this Rule be case sensitive?') )

        weight_label = f_label(_('Weight:'), wrap=False)
        self.weight_entry = Gtk.Entry()
        self.weight_entry.set_tooltip_markup(_("""Weight is used to increase article's <b>importance</b> when matched
Articles are then sorted by importance to keep the most important ones on top.
Weights from leaned rules as well as the ones from manually added ones sum up and position an Article""") )
            
        self.flag_combo = f_flag_combo(self.FX, filters=False, tooltip=_("""Main reason for manually added rules is to flag interesting incomming articles independently of importance ranking
Sometimes, however, a rule can simply increase importance by its <b>weight</b> without flagging""") ) 
        self.additive_button = Gtk.CheckButton.new_with_label(_('Are matches weights additive?'))

        self.err_label = f_label('', wrap=False)

        self.save_button = f_button(_('Save'),'object-select-symbolic', connect=self.on_save)
        self.cancel_button = f_button(_('Cancel'),'action-unavailable-symbolic', connect=self.on_cancel)
        self.restore_button = f_button(_('Restore'),'edit-redo-rtl-symbolic', connect=self.on_restore)

        grid = Gtk.Grid()
        grid.set_column_spacing(10)
        grid.set_row_spacing(10)
        grid.set_column_homogeneous(True)
        grid.set_row_homogeneous(True)
 
        grid.attach(name_label, 1,1, 3,1)
        grid.attach(self.name_entry, 4,1, 10,1)
        grid.attach(string_label, 1,2, 3,1)
        grid.attach(self.string_entry, 4,2, 10,1)
        grid.attach(type_label, 1,3, 3,1)        
        grid.attach(self.type_combo, 4,3, 4,1)
        grid.attach(feed_label, 1,4, 3,1)        
        grid.attach(self.feed_combo, 4,4, 10,1)
        grid.attach(field_label, 1,5, 3,1)        
        grid.attach(self.field_combo, 4,5, 5,1)
        grid.attach(case_label, 1,6, 3,1)        
        grid.attach(self.case_combo, 4,6, 4,1)
        grid.attach(lang_label, 1,7, 3,1)        
        grid.attach(self.lang_combo, 4,7, 4,1)
        grid.attach(weight_label, 1,8, 3,1)
        grid.attach(self.weight_entry, 4,8, 3,1)
        grid.attach(self.flag_combo, 1,9, 4,1)
        grid.attach(self.additive_button, 5,9, 4,1)
        grid.attach(self.err_label, 1, 10, 10, 1) 

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

        self.name_entry.grab_focus()




    def on_restore(self, *args):
        self.name_entry.set_text(coalesce(self.rule.backup_vals.get('name',''),''))
        self.string_entry.set_text(coalesce(self.rule.backup_vals.get('string',''),''))

        f_set_combo(self.type_combo, self.rule.backup_vals.get('type'))
        f_set_combo(self.field_combo, self.rule.backup_vals.get('field_id'))
        f_set_combo(self.feed_combo, self.rule.backup_vals.get('feed_id'))
        f_set_combo(self.lang_combo, self.rule.backup_vals.get('lang'), null_val=None)
        f_set_combo(self.case_combo, self.rule.backup_vals.get('case_insensitive'))

        self.weight_entry.set_text( scast( scast(self.rule.backup_vals.get('weight', None), float, self.config.get('default_rule_weight',2)), str, '2'  ))
        
        f_set_combo(self.flag_combo, self.rule.backup_vals.get('flag',-1))

        if self.rule.backup_vals.get('additive',1) == 1: self.additive_button.set_active(True)
        else: self.additive_button.set_active(False)
        

    def on_changed(self, *args):
        if f_get_combo(self.type_combo) in (1,2): self.lang_combo.set_sensitive(True)
        else: self.lang_combo.set_sensitive(False)
        

    def validate(self):
        err = self.rule.validate()
        if err != 0: 
            self.err_label.set_markup(gui_msg(err))
            return False                    
        return True


    def get_data(self):
        idict = { 'name': nullif(self.name_entry.get_text().strip(),''),
                        'string': nullif(self.string_entry.get_text(),''), 
                        'type': f_get_combo(self.type_combo),
                        'field_id': f_get_combo(self.field_combo), 
                        'feed_id': nullif(f_get_combo(self.feed_combo), 0), 
                        'lang': f_get_combo(self.lang_combo),
                        'case_insensitive': f_get_combo(self.case_combo),
                        'weight' : scast(self.weight_entry.get_text(), float, self.config.get('default_rule_weight',2)),
                        'flag' : f_get_combo(self.flag_combo)
                    }

        if self.additive_button.get_active(): idict['additive'] = 1
        else: idict['additive'] = 0

        if self.new: self.rule.merge(idict)
        else: self.rule.add_to_update(idict)
    

    def on_save(self, *args):
        self.get_data()            
        if self.validate():
            self.response = 1
            self.close()

    def on_cancel(self, *args):
        self.response = 0
        self.get_data()
        self.close()







class EditFeedRegex(Gtk.Dialog):
    """ Edit REGEX strings for parsing HTML input """
    def __init__(self, parent, FX, regexes, ifeed, **kargs):
        
        self.response = 0
        self.result = {}

        self.FX = FX
        self.parent = parent

        self.regexes = regexes
        self.ifeed = FeedContainer(self.FX, replace_nones=True)
        self.ifeed.merge(ifeed)
        self.ifeed.merge(self.regexes)

        self.short = kargs.get('short',False)       

        if self.short: 
            self.handler = FeedexRSSHandler(self.FX)
            title = _('Custom REGEX string for resource link extraction')
            height = 200
        else: 
            self.handler = FeedexHTMLHandler(self.FX)
            title = _("REGEX strings for HTML parsing")
            height = 500

        Gtk.Dialog.__init__(self, title=title, transient_for=parent, flags=0)
        self.set_default_size(kargs.get('width',1000), kargs.get('height',height))
        box = self.get_content_area()

        if self.short:

            images_label = f_label(f'<b>{_("REGEX for extracting Images:")}</b>', markup=True)
            self.images_entry = Gtk.Entry()
            self.images_entry.set_tooltip_markup(_("""This REGEX will extract links to images from Description and Contents instead of builtin""") )
            links_label = f_label(f'<b>{_("REGEX for extracting Links:")}</b>', markup=True)
            self.links_entry = Gtk.Entry()
            self.links_entry.set_tooltip_markup(_("""This REGEX will extract additional links to resources from Description and Contents instead of builtin"""))

            edit_grid = Gtk.Grid()
            edit_grid.set_column_spacing(8)
            edit_grid.set_row_spacing(8)
            edit_grid.set_column_homogeneous(True)
            edit_grid.set_row_homogeneous(True)        

            edit_grid.attach(images_label, 1,1, 3,1)
            edit_grid.attach(self.images_entry, 4,1, 10,1)
            edit_grid.attach(links_label, 1,2, 3,1)
            edit_grid.attach(self.links_entry, 4,2, 10,1)


        else:
            entries_label = f_label(f'<b>{_("Entries:")}</b>', markup=True)
            self.entries_entry = Gtk.Entry()
            self.entries_entry.set_tooltip_markup(_("""This REGEX should extract list of strings for Entries to be parsed by entry-specific REGEXes
Parsing will be done match by match with each REGEX below""" ))
        
            title_label = f_label(_('Title:'))
            self.title_entry = Gtk.Entry()
            link_label = f_label(_('Link:'))
            self.link_entry = Gtk.Entry()
            self.link_entry.set_tooltip_markup(_("""Link to entry. If exctracted link is a relative URL, i.e. it starts with a '/' symbol, Channel's homepage will be prepended to it automatically"""))
            desc_label = f_label(_('Description:'))
            self.desc_entry = Gtk.Entry()
            author_label = f_label(_('Author:'))
            self.author_entry = Gtk.Entry()
            category_label = f_label(_('Category:'))
            self.category_entry = Gtk.Entry()
            text_label = f_label(_('Additional Text:'))
            self.text_entry = Gtk.Entry()
            images_label = f_label(_('Images:'))
            self.images_entry = Gtk.Entry()
            pubdate_label = f_label(_('Published Date:'))
            self.pubdate_entry = Gtk.Entry()

            title_feed_label = f_label(_("Feed's Title:"))
            self.title_feed_entry = Gtk.Entry()
            pubdate_feed_label = f_label(_("Feed's: Published Date:"))
            self.pubdate_feed_entry = Gtk.Entry()
            image_feed_label = f_label(_("Feed's Image:"))
            self.image_feed_entry = Gtk.Entry()
            charset_feed_label = f_label(_("Feed's Encoding:"))
            self.charset_feed_entry = Gtk.Entry()
            lang_feed_label = f_label(_("Feed's Language:"))
            self.lang_feed_entry = Gtk.Entry()


            edit_grid = Gtk.Grid()
            edit_grid.set_column_spacing(8)
            edit_grid.set_row_spacing(8)
            edit_grid.set_column_homogeneous(True)
            edit_grid.set_row_homogeneous(True)        


            edit_grid.attach(title_feed_label, 1,1, 3,1)
            edit_grid.attach(self.title_feed_entry, 4,1, 10,1)
            edit_grid.attach(pubdate_feed_label, 1,2, 3,1)
            edit_grid.attach(self.pubdate_feed_entry, 4,2, 10,1)
            edit_grid.attach(image_feed_label, 1,3, 3,1)
            edit_grid.attach(self.image_feed_entry, 4,3, 10,1)
            edit_grid.attach(charset_feed_label, 1,4, 3,1)
            edit_grid.attach(self.charset_feed_entry, 4,4, 10,1)
            edit_grid.attach(lang_feed_label, 1,5, 3,1)
            edit_grid.attach(self.lang_feed_entry, 4,5, 10,1)

            edit_grid.attach(entries_label, 1,6, 3,1)
            edit_grid.attach(self.entries_entry, 4,6, 10,1)
        
            edit_grid.attach(title_label, 1,7, 3,1)
            edit_grid.attach(self.title_entry, 4,7, 10,1)
            edit_grid.attach(link_label, 1,8, 3,1)
            edit_grid.attach(self.link_entry, 4,8, 10,1)
            edit_grid.attach(desc_label, 1,9, 3,1)
            edit_grid.attach(self.desc_entry, 4,9, 10,1)
            edit_grid.attach(author_label, 1,10, 3,1)
            edit_grid.attach(self.author_entry, 4,10, 10,1)
            edit_grid.attach(category_label, 1,11, 3,1)
            edit_grid.attach(self.category_entry, 4,11, 10,1)
            edit_grid.attach(text_label, 1,12, 3,1)
            edit_grid.attach(self.text_entry, 4,12, 10,1)
            edit_grid.attach(images_label, 1,13, 3,1)
            edit_grid.attach(self.images_entry, 4,13, 10,1)
            edit_grid.attach(pubdate_label, 1,14, 3,1)
            edit_grid.attach(self.pubdate_entry, 4,14, 10,1)

        self.edit_window = Gtk.ScrolledWindow()
        self.edit_window.add(edit_grid)

        self.prev_box_html = Gtk.ScrolledWindow()
        self.prev_box_parsed = Gtk.ScrolledWindow()
        self.prev_label_html = f_label('', justify=FX_ATTR_JUS_LEFT, selectable=True, wrap=False, markup=False, xalign=2)
        self.prev_label_parsed = f_label('', justify=FX_ATTR_JUS_LEFT, selectable=True, wrap=False, markup=True, xalign=2)

        self.prev_box_html.add(self.prev_label_html)
        self.prev_box_parsed.add(self.prev_label_parsed)

        self.prev_notebook = Gtk.Notebook()
        self.prev_notebook.set_scrollable(True)

        self.prev_notebook.append_page(self.prev_box_html, f_label(_("HTML")))
        self.prev_notebook.append_page(self.prev_box_parsed, f_label(_("Parsing Preview")))

        self.load_from_button = f_button(_('Load from...'),'object-select-symbolic', connect=self.on_load_from, tooltip=_("Load REGEXes from other Chanel"))
        if self.short: self.feed_combo = f_feed_combo(self.FX, no_empty=True, with_categories=False, with_feeds=True, with_short_templates=True) 
        else: self.feed_combo = f_feed_combo(self.FX, no_empty=True, with_categories=False, with_feeds=True, with_templates=True)

        self.err_label = f_label('', markup=True)

        self.save_button = f_button(_('Accept'),'object-select-symbolic', connect=self.on_save)
        self.cancel_button = f_button(_('Cancel'),'action-unavailable-symbolic', connect=self.on_cancel)
        self.restore_defaults_button = f_button(_('Restore'),'edit-redo-rtl-symbolic', connect=self.on_restore)

        self.test_button = f_button(_('Test REGEXes'),'system-run-symbolic', connect=self.on_test_regex, tooltip=_("Download resource and test your search string"))

        grid = Gtk.Grid()
        grid.set_column_spacing(8)
        grid.set_row_spacing(8)
        grid.set_column_homogeneous(True)
        grid.set_row_homogeneous(True)

        if self.short:
            grid.attach(self.edit_window, 1,1, 20,2)
            grid.attach(self.prev_notebook, 1,3, 20, 8)
            grid.attach(self.load_from_button, 1,11, 2,1)
            grid.attach(self.feed_combo, 3,11, 6,1)
            grid.attach(self.err_label, 1, 12, 10, 1)

        else:
            grid.attach(self.edit_window, 1,1, 20,10)
            grid.attach(self.prev_notebook, 1,11, 20, 8)
            grid.attach(self.load_from_button, 1,20, 2,1)
            grid.attach(self.feed_combo, 3,20, 6,1)
            grid.attach(self.err_label, 1, 21, 20, 1)

        gridbox = Gtk.Box()
        gridbox.set_border_width(5)
        gridbox.set_orientation(Gtk.Orientation.HORIZONTAL)
        gridbox.set_homogeneous(True)
        gridbox.add(grid)

        vbox = Gtk.Box()
        vbox.set_orientation(Gtk.Orientation.HORIZONTAL)
        vbox.set_homogeneous(False)
        vbox.set_border_width(5)

        vbox.pack_start(self.cancel_button, False, False, 5)
        vbox.pack_start(self.restore_defaults_button, False, False, 5)
        vbox.pack_start(self.test_button, False, False, 15)
        vbox.pack_end(self.save_button, False, False, 5)
            
        box.add(gridbox)
        box.add(vbox)
        self.on_restore()
        self.show_all()








    def on_test_regex(self, *args, **kargs):
        if self.ifeed.get('url') in ('',None):
            self.err_label.set_markup(gui_msg( (-1, _('Link URL is empty. Cannot download resource') ) ))
            return -1

        self.get_data()
        if not self.validate_entries(): return -1
        self.ifeed.merge(self.result)
        self.handler.set_feed(self.ifeed)
        
        if self.short: self.test_regex_short()
        else: self.test_regex()




    def test_regex_short(self, *args, **kargs):
        if self.handler.feed_raw == {}: downloaded = False
        else: downloaded = True

        if not downloaded:
            err = self.handler.download()
            if err != 0: 
                self.err_label.set_markup(gui_msg( (-1, f'{_("Handler error:")} {err}') ))
                return -1

        prev_str = ''
        feed_prev_str = ''
        rx_images = self.result.get('rx_images')
        rx_links = self.result.get('rx_link')
        if rx_images is not None: rx_images = re.compile(rx_images, re.DOTALL)
        if rx_links is not None: rx_links = re.compile(rx_links, re.DOTALL)
        
        for e in self.handler.feed_raw.get('entries',()):

            prev_str = f"""{prev_str}\n\n------------------------------------------------------------\n"""
            feed_prev_str = f"""{feed_prev_str}\n\n------------------------------------------------------------\n"""
            title = e.get('title','')
            desc, im, ls = strip_markup(e.get('description'), rx_images=rx_images, rx_links=rx_links, test=True)
            feed_prev_str = f"""{feed_prev_str}<b>{esc_mu(title)}</b>
{esc_mu(desc)}"""
            for i in im:
                if i is not None and i != '': prev_str = f"""{prev_str}{_('Image:')} <b>{esc_mu(i)}</b>\n"""
            for l in ls:
                if l is not None and i != '': prev_str = f"""{prev_str}{_('Link:')} <b>{esc_mu(l)}</b>\n"""

            text = ''
            content = e.get('content')
            if content is not None:
                for c in content:
                    txt, im, ls = strip_markup(c.get('value'), html=True, rx_images=rx_images, rx_links=rx_links, test=True)
                    feed_prev_str = f"""{feed_prev_str}\n\n{esc_mu(txt)}\n"""
                    if txt not in (None, ''):
                        for i in im:
                            if i is not None and i != '': prev_str = f"""{prev_str}{_('Image:')} <b>{esc_mu(i)}</b>\n"""
                        for l in ls:
                            if l is not None and i != '': prev_str = f"""{prev_str}{_('Link:')} <b>{esc_mu(l)}</b>\n"""


        self.prev_label_parsed.set_markup(prev_str)
        self.prev_label_html.set_markup(feed_prev_str)





    def test_regex(self, *args, **kargs):
        if self.handler.feed_raw.get('raw_html') is None: downloaded = False
        else: downloaded = True
        
        feed_title, feed_pubdate, feed_img, feed_charset, feed_lang, entry_sample, entries = self.handler.test_download(force=True)
        if not downloaded: self.prev_label_html.set_text(scast(self.handler.feed_raw.get('raw_html'), str, ''))
        if self.handler.error:
            self.err_label.set_markup(gui_msg( (-1, f'{_("Handler error:")} {self.handler.error_str}') ))
            return -1

        demo_string = f"""
        
        
{_('Feed title')}: <b>{esc_mu(feed_title)}</b>
{_('Feed Published Date')}: <b>{esc_mu(feed_pubdate)}</b>
{_('Feed Image Link')}: <b>{esc_mu(feed_img)}</b>
{_('Feed Character Encoding')}: <b>{esc_mu(feed_charset)}</b>
{_('Feed Language Code')}: <b>{esc_mu(feed_lang)}</b>
------------------------------------------------------------------------------------------------------------------------------
{_('Extracted entries')} ({len(entries)}):
"""
        for e in entries:

            demo_string = f"""{demo_string}
    ------------------------------------------------------------------
    {_('Title')}: <b>{esc_mu(e.get('title'))}</b>
    {_('Link')}: <b>{esc_mu(e.get('link'))}</b>
    {_('GUID')}: <b>{esc_mu(e.get('guid'))}</b>
    {_('Published')}: <b>{esc_mu(e.get('updated'))}</b>
    {_('Description')}: <b>{esc_mu(e.get('description'))}</b>
    {_('Category')}: <b>{esc_mu(e.get('category'))}</b>
    {_('Author')}: <b>{esc_mu(e.get('author'))}</b>
    {_('Additional Text')}: <b>{esc_mu(e.get('content',{}).get('value',''))}</b>
    {_('Image HREFs')}: <b>{esc_mu(e.get('images'))}</b>"""

        demo_string = f"""{demo_string}
------------------------------------------------------------------------------------------------------------------------------
<i><b>{_('Entry samples')}:</b></i>
{esc_mu(entry_sample)}
"""

        self.prev_label_parsed.set_markup(scast(demo_string, str, ''))







    def on_restore(self, *args, **kargs): self._do_restore()
    def on_load_from(self, *args, **kargs):
        """ Loads REGEXes from existing channel """
        feed_id = f_get_combo(self.feed_combo, null_val=None)
        if feed_id < 0:
            if self.short: feed_dict = FEEDEX_REGEX_HTML_TEMPLATES_SHORT.copy()
            else: feed_dict = FEEDEX_REGEX_HTML_TEMPLATES.copy()
            feed = feed_dict.get(-feed_id).copy()
            del feed['name']
            self._do_restore(feed=feed)
            return 0

        feed = FeedContainerBasic()
        for f in self.FX.MC.feeds:
            feed.populate(f)
            if feed['id'] == feed_id:
                self._do_restore(feed=feed)
                break 
        return 0


    def _do_restore(self, *args, **kargs):
        regexes = kargs.get('feed', self.regexes)

        if self.short:
            self.images_entry.set_text(scast(regexes.get('rx_images'), str,''))
            self.links_entry.set_text(scast(regexes.get('rx_link'), str,''))

        else:
            self.title_feed_entry.set_text(scast(regexes.get('rx_title_feed'), str,''))
            self.pubdate_feed_entry.set_text(scast(regexes.get('rx_pubdate_feed'), str,''))
            self.image_feed_entry.set_text(scast(regexes.get('rx_image_feed'), str,''))
            self.charset_feed_entry.set_text(scast(regexes.get('rx_charset_feed'), str,''))
            self.lang_feed_entry.set_text(scast(regexes.get('rx_lang_feed'), str,''))

            self.entries_entry.set_text(scast(regexes.get('rx_entries'), str,''))

            self.title_entry.set_text(scast(regexes.get('rx_title'), str,''))
            self.link_entry.set_text(scast(regexes.get('rx_link'), str,''))
            self.desc_entry.set_text(scast(regexes.get('rx_desc'), str,''))
            self.author_entry.set_text(scast(regexes.get('rx_author'), str,''))
            self.category_entry.set_text(scast(regexes.get('rx_category'), str,''))
            self.text_entry.set_text(scast(regexes.get('rx_text'), str,''))
            self.images_entry.set_text(scast(regexes.get('rx_images'), str,''))
            self.pubdate_entry.set_text(scast(regexes.get('rx_pubdate'), str,''))




    def get_data(self, *args):
        if self.short:
            self.result = {
            'rx_images': nullif(self.images_entry.get_text(),''),
            'rx_link': nullif(self.links_entry.get_text(),'')
            }

        else:
            self.result = {
            'rx_title_feed': nullif(self.title_feed_entry.get_text(),''),
            'rx_pubdate_feed': nullif(self.pubdate_feed_entry.get_text(),''),
            'rx_image_feed': nullif(self.image_feed_entry.get_text(),''),
            'rx_charset_feed': nullif(self.charset_feed_entry.get_text(),''),
            'rx_lang_feed': nullif(self.lang_feed_entry.get_text(),''),

            'rx_entries': nullif(self.entries_entry.get_text(),''),
        
            'rx_title': nullif(self.title_entry.get_text(),''),
            'rx_link': nullif(self.link_entry.get_text(),''),
            'rx_desc': nullif(self.desc_entry.get_text(),''),
            'rx_author': nullif(self.author_entry.get_text(),''),
            'rx_category': nullif(self.category_entry.get_text(),''),
            'rx_text': nullif(self.text_entry.get_text(),''),
            'rx_images': nullif(self.images_entry.get_text(),''),
            'rx_pubdate': nullif(self.pubdate_entry.get_text(),'')
            }


    def validate_entries(self, *args):
        self.ifeed.merge(self.result)
        if self.short: err = self.ifeed.validate_regexes2()
        else: err = self.ifeed.validate_regexes()
        if err != 0:
            self.err_label.set_markup(gui_msg(err))
            return False
        return True

    def on_save(self, *args):
        self.get_data()
        if self.validate_entries():
            self.response = 1
            self.close()

    def on_cancel(self, *args):
        self.response = 0
        self.get_data()
        self.close()








class EditFeed(Gtk.Dialog):    
    """ Edit Feed dialog """
    def __init__(self, parent, feed, **kargs):

        self.new = kargs.get('new',True)

        self.response = 0
        self.config = kargs.get('config',DEFAULT_CONFIG)
        self.parent = parent

        self.feed = feed
        self.regexes = {}
        for r in FEEDS_REGEX_HTML_PARSERS: self.regexes[r] = self.feed.get(r)

        if self.new: title = _('Add new Feed')
        else: title = title = f'{_("Edit ")}{self.feed.name(id=False)}{_(" Channel")}'

        Gtk.Dialog.__init__(self, title=title, transient_for=parent, flags=0)
        self.set_default_size(kargs.get('width',1000), kargs.get('height',500))
        box = self.get_content_area()

        self.cat_combo = f_feed_combo(self.feed.FX, tooltip=_("""Choose <b>Category</b> to assign this Feed to
Categories are useful for bulk-filtering and general organizing""") )

        self.handler_combo = f_handler_combo(connect=self.on_changed, local=True)
        
        name_label = f_label(_('Name:'))
        self.name_entry = Gtk.Entry() 
        self.name_entry.set_tooltip_markup(_("Display name for this Channel"))        

        title_label = f_label(_('Title:'))
        self.title_entry = Gtk.Entry()
        self.title_entry.set_tooltip_markup(_("This is a title given by publisher and downloaded from Feed's page") )        

        subtitle_label = f_label(_('Subtitle:'))
        self.subtitle_entry = Gtk.Entry()

        url_label = f_label(_('URL:'))
        self.url_entry = Gtk.Entry()
        
        home_label = f_label(_('Homepage:'))
        self.home_entry = Gtk.Entry()
        self.home_entry.set_tooltip_markup(_("URL to Channel's Homepage"))

        self.autoupdate_button = Gtk.CheckButton.new_with_label(_('Autoupdate metadata?'))
        self.autoupdate_button.set_tooltip_markup(f"""{_("Should Channel's metadata be updated everytime news are fetched from it?")}
<i>{_("Updating on every fetch can cause unnecessary overhead")}</i>""")

        self.fetch_button = Gtk.CheckButton.new_with_label(_('Fetch News?'))
        self.fetch_button.set_tooltip_markup(_("""If disabled, Channel's news will not be fetched unless manually requested"""))


        interval_label = f_label(_('Fetch interval:'))
        self.interval_entry = Gtk.Entry()
        self.interval_entry.set_tooltip_markup(_('Set news checking/fetching interval for this Channel'))

        author_label = f_label(_('Author:'))
        self.author_entry = Gtk.Entry()

        author_contact_label = f_label(_('Author contact:'))
        self.author_contact_entry = Gtk.Entry()

        publisher_label = f_label(_('Publisher:'))
        self.publisher_entry = Gtk.Entry()

        publisher_contact_label = f_label(_('Publisher contact:'))
        self.publisher_contact_entry = Gtk.Entry()

        contributors_label = f_label(_('Contributors:'))
        self.contributors_entry = Gtk.Entry()

        category_label = f_label(_('Category:'))
        self.category_entry = Gtk.Entry()
        
        tags_label = f_label(_('Tags:'))
        self.tags_entry = Gtk.Entry()

        self.auth_combo = f_auth_combo(connect=self.on_changed)

        domain_label = f_label(_('Domain:'))
        self.domain_entry = Gtk.Entry()
        self.domain_entry.set_tooltip_markup(_("""Domain used in authentication process"""))

        login_label = f_label(_('Login:'))
        self.login_entry = Gtk.Entry()
        self.login_entry.set_tooltip_markup(_("""Login used in authentication process"""))

        password_label = f_label(_('Password:'))
        self.password_entry = Gtk.Entry()
        self.password_entry.set_visibility(False)
        self.password_entry.set_tooltip_markup(_("""Password used in authentication process"""))


        user_agent_label = f_label(_('Custom User Agent:'))
        user_agent_combo, self.user_agent_entry = f_user_agent_combo()

        script_file_label = f_label(_('Fetching script:'))
        self.script_entry = Gtk.Entry()
        self.script_entry.set_tooltip_markup(_("""Script/command to be executed to fetch entries for this Channel. 
This script should return a <b>JSON string</b>
See <b><i>feedex --help-scripting</i></b> for detailed specification"""))
        self.script_button = f_button(None, 'system-run-symbolic', connect=self._on_choose_script, tooltip=_('Search local machine for script file') )

        icon_label = f_label(_('Icon:'))
        icon_combo, self.icon_entry = f_feed_icon_combo()
        self.icon_button = f_button(None, 'folder-symbolic', connect=self._on_choose_icon, tooltip=_('Search local machine for icons') )

        self.regex_button = f_button(_('REGEX'),None, connect=self._on_define_regex, tooltip=_("Define <b>REGEX strings</b> for <b>HTML</b> parsing") )

        self.err_label = f_label('', markup=True)


        self.save_button = f_button(_('Save'),'object-select-symbolic', connect=self.on_save)
        self.cancel_button = f_button(_('Cancel'),'action-unavailable-symbolic', connect=self.on_cancel)
        self.restore_defaults_button = f_button(_('Restore'),'edit-redo-rtl-symbolic', connect=self.on_restore)
    
        grid = Gtk.Grid()
        grid.set_column_spacing(8)
        grid.set_row_spacing(8)
        grid.set_column_homogeneous(True)
        grid.set_row_homogeneous(True)

        grid.attach(self.cat_combo, 1,1, 5,1)
        grid.attach(self.handler_combo, 14,1, 4,1)        
        grid.attach(name_label, 1,2, 3,1)
        grid.attach(self.name_entry, 4,2, 14,1)
        grid.attach(title_label, 1,3, 3,1)
        grid.attach(self.title_entry, 4,3, 14,1)
        grid.attach(subtitle_label, 1,4, 3,1)
        grid.attach(self.subtitle_entry, 4,4, 14,1)
        grid.attach(url_label, 1,5, 3,1)
        grid.attach(self.url_entry, 4,5, 14,1)
        grid.attach(home_label, 1,6, 3,1)
        grid.attach(self.home_entry, 4,6, 14,1)

        grid.attach(author_label, 1,7, 3,1)
        grid.attach(self.author_entry, 4,7, 5,1)
        grid.attach(author_contact_label, 10,7, 3,1)
        grid.attach(self.author_contact_entry, 13,7, 5,1)
        grid.attach(publisher_label, 1,8, 3,1)
        grid.attach(self.publisher_entry, 4,8, 5,1)
        grid.attach(publisher_contact_label, 10,8, 3,1)
        grid.attach(self.publisher_contact_entry, 13,8, 5,1)

        grid.attach(contributors_label, 1,9, 3,1)
        grid.attach(self.contributors_entry, 4,9, 14,1)
        grid.attach(category_label, 1,10, 3,1)
        grid.attach(self.category_entry, 4,10, 14,1)
        grid.attach(tags_label, 1,11, 3,1)
        grid.attach(self.tags_entry, 4,11, 14,1)

        grid.attach(interval_label, 1,12, 3,1)
        grid.attach(self.interval_entry, 4,12, 3,1)

        grid.attach(self.autoupdate_button, 8,12, 4,1)
        grid.attach(self.fetch_button, 13,12, 4,1)

        grid.attach(self.auth_combo, 1, 13, 7,1)
        grid.attach(domain_label, 10, 13, 3,1)
        grid.attach(self.domain_entry, 13, 13, 5,1)
        
        grid.attach(login_label, 1, 14, 3,1)
        grid.attach(self.login_entry, 4, 14, 5,1)
        grid.attach(password_label, 10, 14, 3,1)
        grid.attach(self.password_entry, 13, 14, 5,1)

        grid.attach(user_agent_label, 1,15, 3,1)
        grid.attach(user_agent_combo, 4,15, 14,1)

        grid.attach(script_file_label, 1,16, 3,1)
        grid.attach(self.script_entry, 4,16, 5,1)
        grid.attach(self.script_button, 9,16, 1,1)

        grid.attach(icon_label, 10,16, 3,1)
        grid.attach(icon_combo, 13,16, 4,1)
        grid.attach(self.icon_button, 17,16, 1,1)


        grid.attach(self.err_label, 1, 17, 12,1)

        gridbox = Gtk.Box()
        gridbox.set_border_width(5)
        gridbox.set_orientation(Gtk.Orientation.HORIZONTAL)
        gridbox.set_homogeneous(True)
        gridbox.add(grid)

        vbox = Gtk.Box()
        vbox.set_orientation(Gtk.Orientation.HORIZONTAL)
        vbox.set_homogeneous(False)
        vbox.set_border_width(5)

        vbox.pack_start(self.cancel_button, False, False, 5)
        vbox.pack_start(self.restore_defaults_button, False, False, 5)
        vbox.pack_start(self.regex_button, False, False, 15)
        vbox.pack_end(self.save_button, False, False, 5)
            
        box.add(gridbox)
        box.add(vbox)
        self.on_restore()
        self.on_changed()
        self.show_all()




    def _on_define_regex(self, *args, **kargs):
        """ Run new window for defining REGEXes"""
        handler = f_get_combo(self.handler_combo)
        if handler == 'html': dialog = EditFeedRegex(self, self.parent.FX, self.regexes, self.get_data(for_regex=True))
        else: dialog = EditFeedRegex(self, self.parent.FX, self.regexes, self.get_data(for_regex=True), short=True)
        dialog.run()
        if dialog.response == 1: self.regexes = dialog.result.copy()
        dialog.destroy()


    def _choose_file(self, *args, **kargs):
        dialog = Gtk.FileChooserDialog(kargs.get('title',_("Choose file")), parent=self, action=Gtk.FileChooserAction.OPEN)
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK)

        dialog.set_current_folder(kargs.get('start_dir', os.getcwd()))
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            filename = dialog.get_filename()
        else: filename = False
        dialog.destroy()
        return filename



    def _on_choose_script(self, *args, **kargs):
        sfile = scast(self.feed.backup_vals.get('script_file',''), str, '')
        if os.path.isfile(sfile):
            start_dir = os.path.dirname(sfile)
        else: start_dir = os.getcwd()

        filename = self._choose_file(title=_('Choose Script File'), start_dir=start_dir)
        if filename is not False: self.script_entry.set_text(filename)

    def _on_choose_icon(self, *args, **kargs):
        sfile = scast(self.feed.backup_vals.get('icon_name',''), str, '')
        if os.path.isfile(sfile):
            start_dir = os.path.dirname(sfile)
        else: start_dir = os.getcwd()

        filename = self._choose_file(title=_('Choose Image'), start_dir=start_dir)
        if filename is not False: self.icon_entry.set_text(filename)






    def on_changed(self, *args):
        handler = f_get_combo(self.handler_combo)
        if handler == 'rss':
            self.url_entry.set_tooltip_markup(_("Valid <b>URL</b> to Channel"))
        elif handler == 'html':
            self.url_entry.set_tooltip_markup(_("""Valid <b>URL</b> to WWW page to be parsed. 
For HTML parsing it is good to use Webpages with as little JavaScript as possible""") )
        elif handler in ('local', 'script'):
            self.url_entry.set_tooltip_markup(_("""For <b>local</b> and <b>script</b> feeds this can be any string, as it is not used
Local feeds are updated only by scripts or CLI (<i>--add-entry</i>, <i>--add-entries-from-file</i>, or <i>--add-entries-from-pipe</i> options)
Scripted feeds are updated by script defined below during fetching""") )

        if handler == 'script': 
            self.script_entry.set_sensitive(True)
            self.script_button.set_sensitive(True)
        else: 
            self.script_entry.set_sensitive(False)
            self.script_button.set_sensitive(False)


        if handler in ('html','rss',): self.regex_button.set_sensitive(True)
        else: self.regex_button.set_sensitive(False)

        auth = f_get_combo(self.auth_combo)
        if auth is None or handler not in ('rss','html'):
            self.domain_entry.set_sensitive(False)
            self.login_entry.set_sensitive(False)
            self.password_entry.set_sensitive(False)
        else:
            self.domain_entry.set_sensitive(True)
            self.login_entry.set_sensitive(True)
            self.password_entry.set_sensitive(True)
            



    def on_restore(self, *args):

        f_set_combo(self.cat_combo, self.feed.backup_vals.get('parent_id'))
        f_set_combo(self.handler_combo, self.feed.backup_vals.get('handler','rss'))
        f_set_combo(self.auth_combo, self.feed.backup_vals.get('auth'))

        self.name_entry.set_text(coalesce(self.feed.backup_vals.get('name',''),''))
        self.title_entry.set_text(coalesce(self.feed.backup_vals.get('title',''),''))
        self.subtitle_entry.set_text(coalesce(self.feed.backup_vals.get('subtitle',''),''))
        self.url_entry.set_text(coalesce(self.feed.backup_vals.get('url',''),''))
        self.home_entry.set_text(coalesce(self.feed.backup_vals.get('link',''),''))
        if self.feed.backup_vals.get('autoupdate',0) == 1: self.autoupdate_button.set_active(True)
        else: self.autoupdate_button.set_active(False)
        if self.feed.backup_vals.get('fetch',0) == 1: self.fetch_button.set_active(True)
        else: self.fetch_button.set_active(False)
        self.interval_entry.set_text(scast(self.feed.backup_vals.get('interval', self.config.get('default_interval',45)), str, ''))        
        self.author_entry.set_text(coalesce(self.feed.backup_vals.get('author',''),''))
        self.author_contact_entry.set_text(coalesce(self.feed.backup_vals.get('author_contact',''),''))
        self.publisher_entry.set_text(coalesce(self.feed.backup_vals.get('publisher',''),''))
        self.publisher_contact_entry.set_text(coalesce(self.feed.backup_vals.get('publisher_contact',''),''))
        self.contributors_entry.set_text(coalesce(self.feed.backup_vals.get('contributors',''),''))
        self.category_entry.set_text(coalesce(self.feed.backup_vals.get('category',''),''))
        self.tags_entry.set_text(coalesce(self.feed.backup_vals.get('tags',''),''))

        self.domain_entry.set_text(coalesce(self.feed.backup_vals.get('domain',''),''))
        self.login_entry.set_text(coalesce(self.feed.backup_vals.get('login',''),''))
        self.password_entry.set_text(coalesce(self.feed.backup_vals.get('passwd',''),''))

        self.user_agent_entry.set_text(coalesce(self.feed.backup_vals.get('user_agent',''),''))
        self.script_entry.set_text(coalesce(self.feed.backup_vals.get('script_file',''),''))
        self.icon_entry.set_text(coalesce(self.feed.backup_vals.get('icon_name',''),''))



    def validate_entries(self, *args):
        err = self.feed.validate()
        if err != 0:
            self.err_label.set_markup(gui_msg(err))
            return False
        return True
    
    def get_data(self, *args, **kargs):
        idict = {}
        idict['parent_id'] = f_get_combo(self.cat_combo)
        idict['handler'] = f_get_combo(self.handler_combo)
        idict['auth'] = f_get_combo(self.auth_combo)
        idict['name'] = nullif(self.name_entry.get_text(),'')
        idict['title'] = nullif(self.title_entry.get_text(),'')
        idict['subtitle'] = nullif(self.subtitle_entry.get_text(),'')
        idict['url'] = nullif(self.url_entry.get_text(),'')
        idict['link'] = nullif(self.home_entry.get_text(),'')
        if self.autoupdate_button.get_active(): idict['autoupdate'] = 1
        else: idict['autoupdate'] = 0
        if self.fetch_button.get_active(): idict['fetch'] = 1
        else: idict['fetch'] = 0
        idict['interval'] = self.interval_entry.get_text()
        idict['author'] = nullif(self.author_entry.get_text(),'')
        idict['author_contact'] = nullif(self.author_contact_entry.get_text(),'')
        idict['publisher'] = nullif(self.publisher_entry.get_text(),'')
        idict['publisher_contact'] = nullif(self.publisher_contact_entry.get_text(),'')
        idict['contributors'] = nullif(self.contributors_entry.get_text(),'')
        idict['category'] = nullif(self.category_entry.get_text(),'')
        idict['tags'] = nullif(self.tags_entry.get_text(),'')

        idict['domain'] = nullif(self.domain_entry.get_text(),'')
        idict['login'] = nullif(self.login_entry.get_text(),'')
        idict['passwd'] = nullif(self.password_entry.get_text(),'')

        idict['user_agent'] = nullif(scast(self.user_agent_entry.get_text(), str, '').strip(),'')
        idict['script_file'] = nullif(scast(self.script_entry.get_text(), str, '').strip(),'')
        idict['icon_name'] = nullif(scast(self.icon_entry.get_text(), str, '').strip(),'')

        if kargs.get('for_regex',False): return idict

        for k,v in self.regexes.items(): idict[k] = v

        if self.new: self.feed.merge(idict)
        else: self.feed.add_to_update(idict)


    def on_save(self, *args):
        self.get_data()
        if self.validate_entries():
            self.response = 1
            self.close()

    def on_cancel(self, *args):
        self.response = 0
        self.get_data()
        self.close()
    








