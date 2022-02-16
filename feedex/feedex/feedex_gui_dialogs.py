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

        close_button = f_button('Close','object-select-symbolic', connect=self.on_close)

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


        yes_button = f_button('Yes','object-select-symbolic', connect=self.on_yes)
        no_button = f_button('No','action-unavailable-symbolic', connect=self.on_no)

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









class NewFromURL(Gtk.Dialog):
    """ Add from URL dialog with category and handler choice """
    def __init__(self, parent, feed, **kargs):

        if isinstance(feed, FeedContainer): self.feed = feed
        else: raise TypeError

        Gtk.Dialog.__init__(self, title="Add Channel from URL", transient_for=parent, flags=0)
        self.set_border_width(10)
        self.set_default_size(kargs.get('width',800), kargs.get('height',100))
        box = self.get_content_area()

        self.url_entry = Gtk.Entry()
        self.url_entry.set_text( scast(self.feed['url'], str, '')  )

        self.cat_combo = f_feed_combo(parent.FX, tooltip="Choose Category to assign this Channel to\nCategories are useful for quick filtering and organizing Channels")
        f_set_combo(self.cat_combo, self.feed['parent_id'])

        self.handler_combo = f_handler_combo(local=False, connect=self.on_changed )
        f_set_combo(self.handler_combo, self.feed['handler'])

        self.add_button = f_button('Add','list-add-symbolic', connect=self.on_add)
        self.cancel_button = f_button('Cancel','action-unavailable-symbolic', connect=self.on_cancel)

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
            self.url_entry.set_tooltip_markup('Enter Channel\'s <b>URL</b> here')
        else:
            self.url_entry.set_tooltip_markup('Enter Channel\'s <b>URL</b> here')

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
        if self.new: title = "Add New Category"
        else: title = f"Edit {self.category.name()} Category"

        Gtk.Dialog.__init__(self, title=title, transient_for=parent, flags=0)
        self.set_border_width(10)
        self.set_default_size(kargs.get('width',800), kargs.get('height',100))
        box = self.get_content_area()

        name_label = f_label('Name:', wrap=False)
        subtitle_label = f_label('Subtitle:', wrap=False)
        self.name_entry = Gtk.Entry()
        self.name_entry.set_tooltip_markup('Enter Category name here')
        self.subtitle_entry = Gtk.Entry()
        self.subtitle_entry.set_tooltip_markup('Enter subtitle/description name here')

        save_button = f_button('Save','object-select-symbolic', connect=self.on_save)
        cancel_button = f_button('Cancel','action-unavailable-symbolic', connect=self.on_cancel)
        clear_button = f_button('Restore','edit-redo-rtl-symbolic', connect=self.on_restore)
    
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

    def get_data(self):
        idict = {
        'name': nullif(self.name_entry.get_text(),''),
        'title': nullif(self.name_entry.get_text(),''),
        'subtitle': nullif(self.subtitle_entry.get_text(),''),
        'is_category': 1
        }
        self.category.add_to_update(idict)

    def on_cancel(self, *args):
        self.response = 0
        self.close()

    def on_save(self, *args):
        self.response = 1
        self.get_data()
        self.close()





class ChangeCategory(Gtk.Dialog):
    """ Change feed's category dialog """
    def __init__(self, parent, feed, **kargs):

        self.feed = feed
        self.response = 0

        Gtk.Dialog.__init__(self, title='Change Category', transient_for=parent, flags=0)
        self.set_default_size(kargs.get('width',700), kargs.get('height',100))
        box = self.get_content_area()

        self.set_border_width(10)
        self.set_resizable(False)
        self.set_position(Gtk.WindowPosition.CENTER)

        feed_label = f_label(f'Choose category for Channel <i><b>{esc_mu(self.feed.name())}</b></i>:', markup=True)
        self.cat_combo = f_feed_combo(parent.FX, tooltip="Choose category to assign this feed to")
        f_set_combo(self.cat_combo, self.feed['parent_id'])

        vbox = Gtk.Box()
        vbox.set_orientation(Gtk.Orientation.HORIZONTAL)
        vbox.set_homogeneous(False)
        vbox.set_border_width(5)

        save_button = f_button('Save','object-select-symbolic', connect=self.on_save)
        cancel_button = f_button('Cancel','action-unavailable-symbolic', connect=self.on_cancel)

        vbox.pack_start(cancel_button, False, False, 5)
        vbox.pack_end(save_button, False, False, 5)

        box.add(feed_label)
        box.add(self.cat_combo)
        box.add(vbox)
        self.show_all()

    def get_data(self):
        self.feed.add_to_update({'parent_id': nullif(f_get_combo(self.cat_combo), -1)})

    def on_save(self, *args):
        self.response = 1
        self.get_data()
        self.close()
    
    def on_cancel(self, *args):
        self.response = 0
        self.result = 0
        self.close()





class EditEntry(Gtk.Dialog):
    """ Edit Entry dialog """
    def __init__(self, parent, config, entry, **kargs):

        self.entry = entry

        self.new = kargs.get('new',True)
        if self.new:
            title = 'Add new Entry'
            restore_label = 'Clear'
        else: 
            title = 'Edit Entry'
            restore_label = 'Restore'

        self.config = config

        Gtk.Dialog.__init__(self, title=title, transient_for=parent, flags=0)
        self.set_default_size(kargs.get('width',800), kargs.get('height',500))
        box = self.get_content_area()

        self.set_border_width(10)
        self.set_resizable(False)
        self.set_position(Gtk.WindowPosition.CENTER)

        self.result = {}
        self.response = 0
        
        self.cat_combo = f_feed_combo(parent.FX, with_feeds=True, no_empty=True, icons=parent.icons, tooltip="""Choose <b>Category</b> or <b>Channel</b> to assign this Entry to.
It is a good idea to have categories exclusively for manually added entries for quick access to notes, hilights etc.
<i>Every Entry needs to be assigned to a Category or a Channel</i>""")

        title_label = f_label('<b>Title:</b>', wrap=False, markup=True)
        self.title_entry = Gtk.Entry()
        self.title_entry.set_tooltip_markup('Enter Entry\'s title here')

        author_label = f_label('<b>Author:</b>', wrap=False, markup=True)
        self.author_entry = Gtk.Entry()

        publisher_label = f_label('<b>Publisher:</b>', wrap=False, markup=True)
        self.publisher_entry = Gtk.Entry()

        contributors_label = f_label('<b>Contributors:</b>', wrap=False, markup=True)
        self.contributors_entry = Gtk.Entry()

        comments_label = f_label('<b>Comments:</b>', wrap=False, markup=True)
        self.comments_entry = Gtk.Entry()

        author_contact_label = f_label('<b>Author contact:</b>', wrap=False, markup=True)
        self.author_contact_entry = Gtk.Entry()
        publisher_contact_label = f_label('<b>Publisher contact:</b>', wrap=False, markup=True)
        self.publisher_contact_entry = Gtk.Entry()


        category_label = f_label('<b>Category:</b>', wrap=False, markup=True)
        self.category_entry = Gtk.Entry()

        tags_label = f_label('<b>Tags:</b>', wrap=False, markup=True)
        self.tags_entry = Gtk.Entry()

        link_label = f_label('<b>Link:</b>', wrap=False, markup=True)
        self.link_entry = Gtk.Entry()



        desc_label = f_label('<b>Description:</b>',  wrap=False, markup=True)
        desc_sw = Gtk.ScrolledWindow()
        self.desc_text = Gtk.TextBuffer()
        desc_entry = Gtk.TextView(buffer=self.desc_text)
        desc_entry.set_tooltip_markup('Enter Entry\'s details/description here')
        desc_entry.set_wrap_mode(Gtk.WrapMode.WORD)
        desc_sw.add(desc_entry)

        text_label = f_label('<b>Additional text:</b>',  wrap=False, markup=True)
        text_sw = Gtk.ScrolledWindow()
        self.text_text = Gtk.TextBuffer()
        text_entry = Gtk.TextView(buffer=self.text_text)
        text_entry.set_tooltip_markup('Enter additional text here')
        text_entry.set_wrap_mode(Gtk.WrapMode.WORD)
        text_sw.add(text_entry)

        self.learn_button = Gtk.CheckButton.new_with_label('Learn rules?')
        self.learn_button.set_tooltip_markup("""Should Feedex extract Rules from this entry for ranking incomming entries by importance?
See <b>Rules</b>->Right-Click-><b>Show learned rules</b> to see those and weights assigned to them
Rules are also learned automatically when any Entry/Article is opened in Browser""")

        self.save_button = f_button('  Save  ','object-select-symbolic', connect=self.on_save)
        self.cancel_button = f_button('Cancel','action-unavailable-symbolic', connect=self.on_cancel)
        self.clear_button = f_button(restore_label ,'edit-undo-rtl-symbolic', connect=self.on_restore)

        header_grid = Gtk.Grid()
        header_grid.set_column_spacing(1)
        header_grid.set_row_spacing(1)
        header_grid.set_column_homogeneous(True)
        header_grid.set_row_homogeneous(True)

        header_grid.attach(self.cat_combo, 1,1, 15, 1)

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

        if self.new: self.entry.merge(idict)
        else: self.entry.add_to_update(idict)


    def on_restore(self, *args):
        f_set_combo(self.cat_combo, self.entry.backup_vals.get('feed_id'))
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





class EditRule(Gtk.Dialog):
    """ Rule Edit dialog """
    def __init__(self, parent, config, rule, **kargs):

        self.new = kargs.get('new',True)

        if self.new: title = 'Add new Rule'
        else: title = 'Edit Rule'

        self.config = config
        self.rule = rule

        Gtk.Dialog.__init__(self, title=title, transient_for=parent, flags=0)
        self.set_default_size(kargs.get('width',1000), kargs.get('height',400))
        box = self.get_content_area()

        self.set_border_width(10)
        self.set_resizable(False)
        self.set_position(Gtk.WindowPosition.CENTER)

        self.result = {}
        self.response = 0

        name_label = f_label('Name:', wrap=False)
        self.name_entry = Gtk.Entry()
        self.name_entry.set_tooltip_markup('Display name for this rule (<i>not used in matching</i>)')
        string_label = f_label('Search string:', wrap=False)
        self.string_entry = Gtk.Entry()
        self.string_entry.set_tooltip_markup("""String or Pattern used for search and matching
It is used according to <b>Type</b> and should be compatibile with it (e.g. REGEX string)""")

        type_label = f_label('Type:', wrap=False)
        self.type_combo = f_query_type_combo(connect=self.on_changed, rule=True)
        feed_label = f_label('Channel or Category:', wrap=False)
        self.feed_combo = f_feed_combo(parent.FX, icons=parent.icons, with_feeds=True, empty_label='-- Every Feed --', tooltip="Which Feed/Channel should this Rule filter?")
        field_label = f_label('Field:',wrap=False)
        self.field_combo = f_field_combo(connect=self.on_changed)
        lang_label = f_label('Language:', wrap=False)
        self.lang_combo = f_lang_combo(parent.FX, connect=self.on_changed, tooltip="Which language should this rule use for Full Text Search?")
        case_label = f_label('Case:', wrap=False)
        self.case_combo = f_dual_combo( ((0,"Case sensitive"),(1,"Case insensitive")), connect=self.on_changed, tooltip='Should this Rule be case sensitive?')

        weight_label = f_label('Weight:', wrap=False)
        self.weight_entry = Gtk.Entry()
        self.weight_entry.set_tooltip_markup("""Weight is used to increase article's <b>importance</b> when matched
Articles are then sorted by importance to keep the most important ones on top.
Weights from leaned rules as well as the ones from manually added ones sum up and position an Article""")
            
        self.flag_combo = f_flag_combo(self.config, filters=False, tooltip="""Main reason for manually added rules is to flag interesting incomming articles independently of importance ranking
Sometimes, however, a rule can simply increase importance by its <b>weight</b> without flagging""") 
        self.additive_button = Gtk.CheckButton.new_with_label('Are matches weights additive?')

        self.err_label = f_label('', wrap=False)

        self.save_button = f_button('Save','object-select-symbolic', connect=self.on_save)
        self.cancel_button = f_button('Cancel','action-unavailable-symbolic', connect=self.on_cancel)
        self.restore_button = f_button('Restore','edit-undo-rtl-symbolic', connect=self.on_restore)

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
                        'learned' : 0,
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






class DisplayRules(Gtk.Dialog):
    """ Display learned rules dialog """
    def __init__(self, parent, header, store, **kargs):

        Gtk.Dialog.__init__(self, title='Learned Rules', transient_for=parent, flags=0)

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
        self.rule_list.append_column( f_col('Name',0 , 0, resizable=True, clickable=True, start_width=300) )
        self.rule_list.append_column( f_col('REGEX String',0 , 1, resizable=True, clickable=True, start_width=300) )
        self.rule_list.append_column( f_col('Weight',0 , 2, resizable=True, clickable=True, start_width=200) )
        self.rule_list.append_column( f_col('Query Type',0 , 3, resizable=True, clickable=True, start_width=200) )
        self.rule_list.append_column( f_col('Context ID',0 , 4, resizable=True, clickable=True, start_width=200) )

        
        self.rule_list.set_tooltip_markup("""List of Rules learned after <b>adding Entries</b> and <b>reading Articles</b>
<b>Name</b> - Displayed name, <i>not matched</i>, purely informational
<b>REGEX String</b> - Regular Expression matched against tokenized Entry with prefixes and case markers
<b>Weight</b> - Weight added to Entry when the rule is matched (rule weights are offset by Entry weight to avoid overvaluing very long articles
<b>Query Type</b> - Is rule matched against exact words or stems?
<b>Context ID</b> - ID of the Entry the rule was extracted from
Hit <b>Ctrl-F</b> for interactive search""")

        self.rule_list.set_enable_search(True)
        self.rule_list.set_search_equal_func(parent.quick_find_case_ins, 0)        

        scwindow.add(self.rule_list)

        done_button = f_button('Done','object-select-symbolic', connect=self.on_done)
        delete_all_button = f_button('Delete all', 'edit-delete-symbolic', connect=self.on_delete_all)
        delete_all_button.set_tooltip_markup("""Delete <b>All</b> learned rules
<i>This process is PERMANENT</i>
Rules can be relearned for all read entries by CLI command:
<i>feedex --relearn</i>""")

        grid.attach(header_label, 1,1, 12,1)
        grid.attach(scwindow, 1,2, 12, 10)
        grid.attach(done_button, 1,12, 2,1)
        grid.attach(delete_all_button, 10,12, 2,1)

        box.add(grid)
        self.show_all()
        self.rule_list.columns_autosize()


    def on_delete_all(self, *args):
        """ Deletes all learned rules after prompt """
        dialog = YesNoDialog(self, 'Clear All Learned Rules?', f'Are you sure you want to clear <b>all leraned rules</b>?', subtitle="<i>This action cannot be reversed!</i>")           
        dialog.run()
        if dialog.response == 1:
            dialog.destroy()
            dialog2 = YesNoDialog(self, 'Clear All Learned Rules?', f'Are you <b>really sure</b>?')
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

        done_button = f_button('  Done  ', None, connect=self.on_close)
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

        Gtk.Dialog.__init__(self, title="About FEEDEX", transient_for=parent, flags=0)

        self.set_default_size(kargs.get('width',500), kargs.get('height',250))

        box = self.get_content_area()

        pb = GdkPixbuf.Pixbuf.new_from_file_at_size(f"{FEEDEX_SYS_ICON_PATH}{DIR_SEP}feedex.png", 64, 64)

        icon = Gtk.Image.new_from_pixbuf(pb)
        main_label = f_label(None, justify=FX_ATTR_JUS_CENTER, wrap=True, markup=True)
        secondary_label = f_label(None, justify=FX_ATTR_JUS_CENTER, wrap=True, markup=True)
        author_label = f_label(None, justify=FX_ATTR_JUS_CENTER, wrap=True, markup=True)
        website_label = f_label(None, justify=FX_ATTR_JUS_CENTER, wrap=True, markup=True)

        close_button = f_button('   Close   ', None, connect=self.on_close)
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
Release: {FEEDEX_RELEASE}""")
        author_label.set_markup(f"""<i>Author: {FEEDEX_AUTHOR}
{FEEDEX_CONTACT}</i>""")

        website_label.set_markup(f"""Website: <a href="{esc_mu(FEEDEX_WEBSITE)}">{esc_mu(FEEDEX_WEBSITE)}</a>""")

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

        Gtk.Dialog.__init__(self, title="Choose date range", transient_for=parent, flags=0)
        self.set_default_size(kargs.get('width',400), kargs.get('height',200))
        box = self.get_content_area()

        from_label = f_label('  From:', justify=FX_ATTR_JUS_LEFT, selectable=False, wrap=False)
        to_label = f_label('    To:', justify=FX_ATTR_JUS_LEFT, selectable=False, wrap=False)

        self.from_clear_button = Gtk.CheckButton.new_with_label('Empty')
        self.from_clear_button.connect('toggled', self.clear_from)
        self.to_clear_button = Gtk.CheckButton.new_with_label('Empty')
        self.to_clear_button.connect('toggled', self.clear_to)

        accept_button = f_button('Accept','object-select-symbolic', connect=self.on_accept)
        cancel_button = f_button('Cancel','window-close-symbolic', connect=self.on_cancel)

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










class EditFeed(Gtk.Dialog):    
    """ Edit Feed dialog """
    def __init__(self, parent, feed, **kargs):

        self.new = kargs.get('new',True)

        self.response = 0
        self.config = kargs.get('config',DEFAULT_CONFIG)

        self.feed = feed

        if self.new: title = 'Add new Feed'
        else: title = title = f'Edit {self.feed.name(id=False)} Chanel'

        Gtk.Dialog.__init__(self, title=title, transient_for=parent, flags=0)
        self.set_default_size(kargs.get('width',1000), kargs.get('height',500))
        box = self.get_content_area()

        self.cat_combo = f_feed_combo(self.feed.FX, tooltip="""Choose <b>Category</b> to assign this Feed to
Categories are useful for bulk-filtering and general organizing""")

        self.handler_combo = f_handler_combo(connect=self.on_changed, local=True)
        
        name_label = f_label('Name:')
        self.name_entry = Gtk.Entry() 
        self.name_entry.set_tooltip_markup("Display name for this Channel")        

        title_label = f_label('Title:')
        self.title_entry = Gtk.Entry()
        self.title_entry.set_tooltip_markup("This is a title given by publisher and downloaded from Feed's page")        

        subtitle_label = f_label('Subtitle:')
        self.subtitle_entry = Gtk.Entry()

        url_label = f_label('URL:')
        self.url_entry = Gtk.Entry()
        
        home_label = f_label('Homepage:')
        self.home_entry = Gtk.Entry()
        self.home_entry.set_tooltip_markup("URL to Channel's Homepage")

        self.autoupdate_button = Gtk.CheckButton.new_with_label('Autoupdate metadata?')
        self.autoupdate_button.set_tooltip_markup("""Should Channel's metadata be updated everytime news are fetched from it?
<i>Updating on every fetch can cause unnecessary overhead</i>""")

        interval_label = f_label('Fetch interval:')
        self.interval_entry = Gtk.Entry()
        self.interval_entry.set_tooltip_markup('Set news checking/fetching interval for this Channel.\nEnter <b>0</b> to disable fetching for this Channel alltogether')

        author_label = f_label('Author:')
        self.author_entry = Gtk.Entry()

        author_contact_label = f_label('Author contact:')
        self.author_contact_entry = Gtk.Entry()

        publisher_label = f_label('Publisher:')
        self.publisher_entry = Gtk.Entry()

        publisher_contact_label = f_label('Publisher contact:')
        self.publisher_contact_entry = Gtk.Entry()

        contributors_label = f_label('Contributors:')
        self.contributors_entry = Gtk.Entry()

        category_label = f_label('Category:')
        self.category_entry = Gtk.Entry()
        
        tags_label = f_label('Tags:')
        self.tags_entry = Gtk.Entry()

        self.auth_combo = f_auth_combo(connect=self.on_changed)

        domain_label = f_label('Domain:')
        self.domain_entry = Gtk.Entry()
        self.domain_entry.set_tooltip_markup("""Domain used in authentication process""")

        login_label = f_label('Login:')
        self.login_entry = Gtk.Entry()
        self.login_entry.set_tooltip_markup("""Login used in authentication process""")

        password_label = f_label('Password:')
        self.password_entry = Gtk.Entry()
        self.password_entry.set_visibility(False)
        self.password_entry.set_tooltip_markup("""Password used in authentication process""")


        user_agent_label = f_label('Custom User Agent:')
        self.user_agent_entry = Gtk.Entry()
        self.user_agent_entry.set_tooltip_markup("""Sometimes it is needed to change user anger tag if the publisher does not allow download (e.g. 403 HTTP response)
<b>Changing this tag is not recommended and for debugging purposes only</b>""")


        self.err_label = f_label('', markup=True)


        self.save_button = f_button('Save','object-select-symbolic', connect=self.on_save, tooltip="Save Entry")
        self.cancel_button = f_button('Cancel','action-unavailable-symbolic', connect=self.on_cancel)
        self.restore_defaults_button = f_button('Restore','edit-redo-rtl-symbolic', connect=self.on_restore, tooltip="Restore preferences to defaults")
    
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

        grid.attach(self.auth_combo, 1, 13, 7,1)
        grid.attach(domain_label, 10, 13, 3,1)
        grid.attach(self.domain_entry, 13, 13, 5,1)
        
        grid.attach(login_label, 1, 14, 3,1)
        grid.attach(self.login_entry, 4, 14, 5,1)
        grid.attach(password_label, 10, 14, 3,1)
        grid.attach(self.password_entry, 13, 14, 5,1)

        grid.attach(user_agent_label, 1,15, 3,1)
        grid.attach(self.user_agent_entry, 4,15, 14,1)

        grid.attach(self.err_label, 1, 16, 12,1)

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
        vbox.pack_end(self.save_button, False, False, 5)
            
        box.add(gridbox)
        box.add(vbox)
        self.on_restore()
        self.on_changed()
        self.show_all()


    def on_changed(self, *args):
        handler = f_get_combo(self.handler_combo)
        if handler == 'rss':
            self.url_entry.set_tooltip_markup("Valid <b>URL</b> to Channel")
        elif handler == 'local':
            self.url_entry.set_tooltip_markup("""For <b>local</b> feeds this can be any string, as it is not used
Local feeds are updated only by scripts or CLI (<i>--add-entry</i>, <i>--add-entries-from-file</i>, or <i>--add-entries-from-pipe</i> options)""")

        auth = f_get_combo(self.auth_combo)
        if auth is None:
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



    def validate_entries(self, *args):
        err = self.feed.validate()
        if err != 0:
            self.err_label.set_markup(gui_msg(err))
            return False
        return True
    
    def get_data(self, *args):
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
    






class PreferencesDialog(Gtk.Dialog):
    """ Edit preferences dialog """
    def __init__(self, parent, config, **kargs):

        self.config = config
        self.config_def = config

        Gtk.Dialog.__init__(self, title='FEEDEX Preferences', transient_for=parent, flags=0)
        #self.set_default_size(args.get('width',1000), args.get('height',400))
        box = self.get_content_area()

        self.set_border_width(10)
        self.set_resizable(False)
        self.set_position(Gtk.WindowPosition.CENTER)


        self.result = {}
        self.response = 0        

        self.desktop_notify_button = Gtk.CheckButton.new_with_label('Enable desktop notifications?')
        self.desktop_notify_button.connect('clicked', self.on_changed)
        self.desktop_notify_button.set_tooltip_markup('Should Feedex send desktop notifications on incomming news?')
        self.fetch_in_background_button = Gtk.CheckButton.new_with_label('Fetch news in the background?')
        self.fetch_in_background_button.set_tooltip_markup('News will be checked in background and downloaded if Channels\'s fetching interval is exceeded')
        
        default_interval_label = f_label('Default check interval:')
        self.default_interval_entry = Gtk.Entry()
        self.default_interval_entry.set_tooltip_markup('Default fetching interval for newly added feeds')
        
        rule_limit_label = f_label('Ranking rules limit:')
        self.rule_limit_entry = Gtk.Entry()
        self.rule_limit_entry.set_tooltip_markup("""When ranking incomming news you can 
limit the number of rules to match.
Only those with N top weight will be checked.
This can help avoid unimportant terms influencing ranking
and prevent scaling problems for large datasets
Enter <b>0</b> for <b>no rule limit</b> (every rule will be checked)""")

        self.learn_button = Gtk.CheckButton.new_with_label('Enable Keyword learning?')
        self.learn_button.set_tooltip_markup("""If enabled, keywords are extracted and learned 
every time an article is read or marked as read.
Incomming news are then ranked agains the rules from those extracted keywords.
Feedex uses this ranking to get articles most likely interesting to you on top.
If disabled, no learning will take place and ranking will be done only against rules
that were manually added by user.        
""")


        self.notify_level_combo = f_dual_combo( ((1, 'Summary'), (2, 'All new entries'), (3, 'Only flagged entries'), (10, 'Summary if more than 10'), (50, 'Summary if more than 50'),),  
                                                connect=self.on_changed, tooltip="How should Feedex notify?")

        default_entry_weight_label = f_label('New Entry default weight:')
        self.default_entry_weight_entry = Gtk.Entry()
        self.default_entry_weight_entry.set_tooltip_markup('Default weight for manually added Entries for rule learning')

        self.learn_from_added_button = Gtk.CheckButton.new_with_label('Learn from added Entries?')
        self.learn_from_added_button.set_tooltip_markup('Should Feedex learn rules/keywords from manually added entries?\nUseful for utilizing highlights and notes for news ranking')

        default_rule_weight_label = f_label('Rule default weight:')
        self.default_rule_weight_entry = Gtk.Entry()
        self.default_rule_weight_entry.set_tooltip_markup('Default weight assigned to manually added rule (if not provided)')

        default_similar_wieght_label = f_label('Weight for similarity search:')
        self.default_similar_weight_entry = Gtk.Entry()
        self.default_similar_weight_entry.set_tooltip_markup('How much weight for ranking should items for which similar ones are searched for be given. Zero to disable')
        
        flag_color_label_1 = f_label('Flag 1 color:')
        flag_color = Gdk.color_parse(self.config.get('gui_flag_1_color','blue'))
        self.flag_color_button_1 = Gtk.ColorButton(color=flag_color)
        flag_name_label_1 = f_label('    Flag 1 name:')
        self.flag_name_entry_1 = Gtk.Entry()

        flag_color_label_2 = f_label('Flag 2 color:')
        flag_color = Gdk.color_parse(self.config.get('gui_flag_2_color','blue'))
        self.flag_color_button_2 = Gtk.ColorButton(color=flag_color)
        flag_name_label_2 = f_label('    Flag 2 name:')
        self.flag_name_entry_2 = Gtk.Entry()

        flag_color_label_3 = f_label('Flag 3 color:')
        flag_color = Gdk.color_parse(self.config.get('gui_flag_3_color','blue'))
        self.flag_color_button_3 = Gtk.ColorButton(color=flag_color)
        flag_name_label_3 = f_label('    Flag 3 name:')
        self.flag_name_entry_3 = Gtk.Entry()

        flag_color_label_4 = f_label('Flag 4 color:')
        flag_color = Gdk.color_parse(self.config.get('gui_flag_4_color','blue'))
        self.flag_color_button_4 = Gtk.ColorButton(color=flag_color)
        flag_name_label_4 = f_label('    Flag 4 name:')
        self.flag_name_entry_4 = Gtk.Entry()

        flag_color_label_5 = f_label('Flag 5 color:')
        flag_color = Gdk.color_parse(self.config.get('gui_flag_5_color','blue'))
        self.flag_color_button_5 = Gtk.ColorButton(color=flag_color)
        flag_name_label_5 = f_label('    Flag 5 name:')
        self.flag_name_entry_5 = Gtk.Entry()

        new_color_label = f_label('Added entry color:')
        new_color = Gdk.color_parse(self.config.get('gui_new_color','#0FDACA'))
        self.new_color_button = Gtk.ColorButton(color=new_color)

        del_color_label = f_label('Deleted color:')
        del_color = Gdk.color_parse(self.config.get('gui_deleted_color','grey'))
        self.del_color_button = Gtk.ColorButton(color=del_color)

        hl_color_label = f_label('Search hilight color:')
        hl_color = Gdk.color_parse(self.config.get('gui_deleted_color','grey'))
        self.hl_color_button = Gtk.ColorButton(color=hl_color)


        key_search_label = f_label('Hokey, open new Search Tab: Ctrl + ')
        self.key_search_entry = Gtk.Entry()

        key_new_entry_label = f_label('Hokey, add New Entry: Ctrl + ')
        self.key_new_entry_entry = Gtk.Entry()

        key_new_rule_label = f_label('Hokey, add New Rule: Ctrl + ')
        self.key_new_rule_entry = Gtk.Entry()

        self.ignore_images_button = Gtk.CheckButton.new_with_label('Ignore Images?')
        self.ignore_images_button.set_tooltip_markup('Should images and icons be ignored alltogether? Ueful for better performance')

        browser_label = f_label('Default WWW browser:')
        self.browser_entry = Gtk.Entry()
        self.browser_entry.set_tooltip_markup('Command for opening in browser. Use <b>u%</b> symbol to substitute for URL')
        browser_application_button = f_button(None,'view-app-grid-symbolic', connect=self.on_app_choose_browser, tooltip="Choose from installed applications")

        self.external_iv_application_button = f_button(None,'view-app-grid-symbolic', connect=self.on_app_choose_iv, tooltip="Choose from installed applications")
        external_iv_label = f_label('External image viewer:')
        self.external_iv_entry = Gtk.Entry()
        self.external_iv_entry.set_tooltip_markup('Command for viewing images by clicking on them.\nUse <b>%u</b> symbol to substitute for temp filename\n<b>%t</b> symbol will be replaced by <b>title</b>\n<b>%a</b> symbol will be replaced by <b>alt</b> field')

        self.external_txtv_application_button = f_button(None,'view-app-grid-symbolic', connect=self.on_app_choose_txtv, tooltip="Choose from installed applications")
        external_txtv_label = f_label('External text file viewer:')
        self.external_txtv_entry = Gtk.Entry()
        self.external_txtv_entry.set_tooltip_markup('Command for viewing text files.\nUse <b>%u</b> symbol to substitute for temp filename\n<b>%t</b>')

        search_engine_label = f_label('Default WWW search engine:')
        self.search_engine_entry = Gtk.Entry()
        self.search_engine_entry.set_tooltip_markup('Search engine to use for browser searches. Use <b>Q%</b> symbol to substitute for query')
        

        similarity_limit_label = f_label('Similarity query limit:')
        self.similarity_limit_entry = Gtk.Entry()
        self.similarity_limit_entry.set_tooltip_markup('Limit similarity query items for improved query performance')

        max_context_length_label = f_label('Max context length:')
        self.max_context_length_entry = Gtk.Entry()
        self.max_context_length_entry.set_tooltip_markup('If the length of a context/snippet is greater than this number, it will not be shown in query results. Needed to avoid long snippets for wildcard searches')


        error_threshold_label = f_label('Error threshold:')
        self.error_threshold_entry = Gtk.Entry()
        self.error_threshold_entry.set_tooltip_markup('After how many download errors should a Channel be marked as unhealthy and ignored while fetching?')

        self.ignore_modified_button = Gtk.CheckButton.new_with_label('Ignore modified Tags?')
        self.ignore_modified_button.set_tooltip_markup('Should ETags and Modified fields be ignored while fetching? If yes, Feedex will fetch news even when publisher suggest not to (e.g. no changes where made to feed)')

        clear_cache_label = f_label('Clear cached files older than how many days?')
        self.clear_cache_entry = Gtk.Entry()
        self.clear_cache_entry.set_tooltip_markup('Files in cache include thumbnails and images. It is good to keep them but older items should release space')

        db_label = f_label('Database:')
        db_choose_button = f_button(None,'folder-symbolic', connect=self.on_file_choose_db, tooltip="Search filesystem")
        self.db_entry = Gtk.Entry()
        self.db_entry.set_tooltip_markup("Database file to be used for storage.\n<i>Changes require application restart</i>")

        log_label = f_label('Log file:')
        log_choose_button = f_button(None,'folder-symbolic', connect=self.on_file_choose_log, tooltip="Search filesystem")
        self.log_entry = Gtk.Entry()
        self.log_entry.set_tooltip_markup("Path to log file")

        user_agent_label = f_label('User Agent:')
        self.user_agent_entry = Gtk.Entry()
        self.user_agent_entry.set_tooltip_markup(f"""User Agent string to be used when requesting URLs. Be careful, as some publishers are very strict about that. 
Default is: {FEEDEX_USER_AGENT}
<b>Changing this tag is not recommended and for debugging purposes only</b>""")

        self.do_redirects_button = Gtk.CheckButton.new_with_label('Redirect?')
        self.do_redirects_button.set_tooltip_markup('Should HTTP redirects (codes:301, 302) be followed when fetching?')

        self.save_redirects_button = Gtk.CheckButton.new_with_label('Save permanent redirects?')
        self.save_redirects_button.set_tooltip_markup('Should permanent HTTP redirects (code: 301) be saved to DB?')

        self.mark_deleted_button = Gtk.CheckButton.new_with_label('Mark deleted channels as unhealthy?')
        self.mark_deleted_button.set_tooltip_markup('Should deleted channels (HTTP code 410) be marked as unhealthy to avoid fetching in the future?')

        self.no_history_button = Gtk.CheckButton.new_with_label('Do not save queries in History?')
        self.no_history_button.set_tooltip_markup('Should saving search phrases to History be ommitted?')


        self.err_label = f_label('', markup=True)

        self.save_button = f_button('Save','object-select-symbolic', connect=self.on_save, tooltip="Save configuration")
        self.cancel_button = f_button('Cancel','action-unavailable-symbolic', connect=self.on_cancel)
        self.restore_button = f_button('Restore','edit-redo-rtl-symbolic', connect=self.on_restore, tooltip="Restore preferences to defaults")


        def create_grid():
            grid = Gtk.Grid()
            grid.set_column_spacing(8)
            grid.set_row_spacing(8)
            grid.set_column_homogeneous(False)
            grid.set_row_homogeneous(False)
            grid.set_border_width(5)
            return grid


        fetching_grid = create_grid()
        fetching_grid.attach(self.desktop_notify_button, 1,1, 4,1)
        fetching_grid.attach(self.notify_level_combo, 5,1, 5,1)
        fetching_grid.attach(self.fetch_in_background_button, 1,2, 4,1)
        fetching_grid.attach(default_interval_label, 1,3, 2,1)
        fetching_grid.attach(self.default_interval_entry, 4,3, 3,1)

        rss_grid = create_grid()
        rss_grid.attach(self.do_redirects_button, 1,1, 4,1)
        rss_grid.attach(self.save_redirects_button , 1,2, 4,1)
        rss_grid.attach(self.mark_deleted_button, 1,3, 4,1)
        rss_grid.attach(self.ignore_modified_button, 1,4, 5,1)
        rss_grid.attach(error_threshold_label, 1,5, 2,1)
        rss_grid.attach(self.error_threshold_entry, 4,5, 3,1)
        
        interface_grid = create_grid()    
        interface_grid.attach(self.ignore_images_button, 1,1, 5,1)
        interface_grid.attach(new_color_label, 1,2, 3,1)
        interface_grid.attach(self.new_color_button, 4,2, 1,1)
        interface_grid.attach(del_color_label, 1,3, 3,1)
        interface_grid.attach(self.del_color_button, 4,3, 1,1)
        interface_grid.attach(hl_color_label, 1,4, 3,1)
        interface_grid.attach(self.hl_color_button, 4,4, 1,1)
        interface_grid.attach(key_search_label, 7, 2, 3, 1)
        interface_grid.attach(self.key_search_entry, 10, 2, 1,1)
        interface_grid.attach(key_new_entry_label, 7, 3, 3, 1)
        interface_grid.attach(self.key_new_entry_entry, 10, 3, 1,1)
        interface_grid.attach(key_new_rule_label, 7, 4, 3, 1)
        interface_grid.attach(self.key_new_rule_entry, 10, 4, 1,1)

        flag_grid = create_grid()
        flag_grid.attach(flag_color_label_1, 1,1, 3,1)
        flag_grid.attach(self.flag_color_button_1, 4,1, 1,1)
        flag_grid.attach(flag_name_label_1, 8,1, 3,1)
        flag_grid.attach(self.flag_name_entry_1, 12,1, 4,1)

        flag_grid.attach(flag_color_label_2, 1,2, 3,1)
        flag_grid.attach(self.flag_color_button_2, 4,2, 1,1)
        flag_grid.attach(flag_name_label_2, 8,2, 3,1)
        flag_grid.attach(self.flag_name_entry_2, 12,2, 4,1)

        flag_grid.attach(flag_color_label_3, 1,3, 3,1)
        flag_grid.attach(self.flag_color_button_3, 4,3, 1,1)
        flag_grid.attach(flag_name_label_3, 8,3, 3,1)
        flag_grid.attach(self.flag_name_entry_3, 12,3, 4,1)

        flag_grid.attach(flag_color_label_4, 1,4, 3,1)
        flag_grid.attach(self.flag_color_button_4, 4,4, 1,1)
        flag_grid.attach(flag_name_label_4, 8,4, 3,1)
        flag_grid.attach(self.flag_name_entry_4, 12,4, 4,1)

        flag_grid.attach(flag_color_label_5, 1,5, 3,1)
        flag_grid.attach(self.flag_color_button_5, 4,5, 1,1)
        flag_grid.attach(flag_name_label_5, 8,5, 3,1)
        flag_grid.attach(self.flag_name_entry_5, 12,5, 4,1)
        

        
        weights_grid = create_grid()    
        weights_grid.attach(default_entry_weight_label, 1,1, 3,1)
        weights_grid.attach(self.default_entry_weight_entry, 4,1, 3,1)
        weights_grid.attach(default_rule_weight_label, 1, 2, 3,1)
        weights_grid.attach(self.default_rule_weight_entry, 4, 2, 3,1)
        weights_grid.attach(default_similar_wieght_label, 1,3,4,1)
        weights_grid.attach(self.default_similar_weight_entry, 5, 3, 3,1)

        learn_grid = create_grid()
        learn_grid.attach(self.learn_button, 1,1, 6,1)
        learn_grid.attach(rule_limit_label, 1,2, 3,1)
        learn_grid.attach(self.rule_limit_entry, 4,2, 3,1)
        learn_grid.attach(self.learn_from_added_button, 1,3, 6,1)
        learn_grid.attach(similarity_limit_label, 1,5, 4,1)
        learn_grid.attach(self.similarity_limit_entry, 5,5, 3,1)
        learn_grid.attach(max_context_length_label, 1,6,4,1)
        learn_grid.attach(self.max_context_length_entry, 5,6,3,1)

        commands_grid = create_grid()
        commands_grid.attach(browser_label, 1,1, 4,1)
        commands_grid.attach(browser_application_button, 5,1, 1,1)
        commands_grid.attach(self.browser_entry, 6,1, 10,1)
        commands_grid.attach(external_iv_label, 1,2, 4,1)
        commands_grid.attach(self.external_iv_application_button, 5,2, 1,1)
        commands_grid.attach(self.external_iv_entry, 6,2, 10,1)
        commands_grid.attach(external_txtv_label, 1,3, 4,1)
        commands_grid.attach(self.external_txtv_application_button, 5,3, 1,1)
        commands_grid.attach(self.external_txtv_entry, 6,3, 10,1)
        commands_grid.attach(search_engine_label, 1,4, 4,1)
        commands_grid.attach(self.search_engine_entry, 6,4, 10,1)

        system_grid = create_grid()
        system_grid.attach(clear_cache_label, 1,1, 5,1)
        system_grid.attach(self.clear_cache_entry, 7,1, 3,1)
        system_grid.attach(db_label, 1,2, 3,1)
        system_grid.attach(db_choose_button, 4,2, 1,1)
        system_grid.attach(self.db_entry, 5,2, 10,1)
        system_grid.attach(log_label, 1,3, 3,1)
        system_grid.attach(log_choose_button, 4,3, 1,1)
        system_grid.attach(self.log_entry, 5,3, 10,1)
        system_grid.attach(user_agent_label, 1,4, 3,1)
        system_grid.attach(self.user_agent_entry, 5,4, 10,1)
        system_grid.attach(self.no_history_button, 1,5, 7,1)
        
        self.notebook = Gtk.Notebook()
        self.notebook.append_page(fetching_grid, Gtk.Label(label="Fetching"))    
        self.notebook.append_page(rss_grid, Gtk.Label(label="RSS Settings"))    
        self.notebook.append_page(interface_grid, Gtk.Label(label="Interface"))
        self.notebook.append_page(flag_grid, Gtk.Label(label="Flags"))
        self.notebook.append_page(weights_grid, Gtk.Label(label="Weights"))
        self.notebook.append_page(learn_grid, Gtk.Label(label="Learning and Ranking"))
        self.notebook.append_page(commands_grid, Gtk.Label(label="Commands"))
        self.notebook.append_page(system_grid, Gtk.Label(label="System"))    
    
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
        if self.desktop_notify_button.get_active(): self.notify_level_combo.set_sensitive(True)
        else: self.notify_level_combo.set_sensitive(False)



    def on_file_choose_db(self, *args): self.file_choose('db')
    def on_file_choose_log(self, *args): self.file_choose('log')
    def file_choose(self, target, *args):
        if target == 'db':
            heading = 'Choose Database'
            start_dir = os.path.dirname(self.config.get('db_path'))
        elif target == 'log':
            heading = 'Choose Log File'
            start_dir = os.path.dirname(self.config.get('log'))

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
            heading = "Choose Default Browser"
            content_type = "text/html"
        elif target == 'iv':
            heading = "Choose Image Viewer"
            content_type = "image/jpeg"
        elif target == 'txtv':
            heading = "Choose Text File Viewer"
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

        self.rule_limit_entry.set_text(scast(self.config.get('rule_limit', 50000), str, '<<ERROR>>'))

        if self.config.get('gui_desktop_notify',True): self.desktop_notify_button.set_active(True)
        else: self.desktop_notify_button.set_active(False)

        f_set_combo(self.notify_level_combo, self.config.get('notify_level',1))

        if self.config.get('gui_fetch_periodically',False): self.fetch_in_background_button.set_active(True)
        else: self.fetch_in_background_button.set_active(False)

        if self.config.get('do_redirects', False): self.do_redirects_button.set_active(True)
        else: self.do_redirects_button.set_active(False)

        if self.config.get('save_perm_redirects', False): self.save_redirects_button.set_active(True)
        else: self.save_redirects_button.set_active(False)

        if self.config.get('mark_deleted', False): self.mark_deleted_button.set_active(True)
        else: self.mark_deleted_button.set_active(False)


        self.default_interval_entry.set_text(scast(self.config.get('default_interval',45), str, '<<ERROR>>'))

        self.default_entry_weight_entry.set_text(scast(self.config.get('default_entry_weight',2), str, '<<ERROR>>'))

        if self.config.get('learn_from_added_entries',True): self.learn_from_added_button.set_active(True)
        else: self.learn_from_added_button.set_active(False)

        self.default_rule_weight_entry.set_text(scast(self.config.get('default_rule_weight',2), str, '<<ERROR>>'))

        self.default_similar_weight_entry.set_text(scast(self.config.get('default_similar_weight',2), str, '<<ERROR>>'))

        self.max_context_length_entry.set_text(scast(self.config.get('max_context_length',500), str, '<<ERROR>>'))

        flag_color = Gdk.color_parse(self.config.get('gui_flag_1_color','blue'))
        self.flag_color_button_1.set_color(flag_color)
        self.flag_name_entry_1.set_text(self.config.get('gui_flag_1_name','Flag 1'))
        flag_color = Gdk.color_parse(self.config.get('gui_flag_2_color','blue'))
        self.flag_color_button_2.set_color(flag_color)
        self.flag_name_entry_2.set_text(self.config.get('gui_flag_2_name','Flag 2'))
        flag_color = Gdk.color_parse(self.config.get('gui_flag_3_color','blue'))
        self.flag_color_button_3.set_color(flag_color)
        self.flag_name_entry_3.set_text(self.config.get('gui_flag_3_name','Flag 3'))
        flag_color = Gdk.color_parse(self.config.get('gui_flag_4_color','blue'))
        self.flag_color_button_4.set_color(flag_color)
        self.flag_name_entry_4.set_text(self.config.get('gui_flag_4_name','Flag 4'))
        flag_color = Gdk.color_parse(self.config.get('gui_flag_5_color','blue'))
        self.flag_color_button_5.set_color(flag_color)
        self.flag_name_entry_5.set_text(self.config.get('gui_flag_5_name','Flag 5'))

        new_color = Gdk.color_parse(self.config.get('gui_new_color','#0FDACA'))
        self.new_color_button.set_color(new_color)
        del_color = Gdk.color_parse(self.config.get('gui_deleted_color','grey'))
        self.del_color_button.set_color(del_color)
        hl_color = Gdk.color_parse(self.config.get('gui_hilight_color','blue'))
        self.hl_color_button.set_color(hl_color)
        
        if self.config.get('ignore_images',False): self.ignore_images_button.set_active(True)
        else: self.ignore_images_button.set_active(False)

        self.key_search_entry.set_text(coalesce(self.config.get('gui_key_search','s'), ''))
        self.key_new_entry_entry.set_text(coalesce(self.config.get('gui_key_new_entry','n'), ''))
        self.key_new_rule_entry.set_text(coalesce(self.config.get('gui_key_new_rule','r'), ''))

        self.browser_entry.set_text(coalesce(self.config.get('browser',''),''))
        self.external_iv_entry.set_text(coalesce(self.config.get('image_viewer',''),''))
        self.external_txtv_entry.set_text(coalesce(self.config.get('text_viewer',''),''))
        self.search_engine_entry.set_text(coalesce(self.config.get('search_engine',''),''))

        self.similarity_limit_entry.set_text(scast(self.config.get('default_similarity_limit',''),str,'<<ERROR>>'))

        self.error_threshold_entry.set_text(scast(self.config.get('error_threshold',''), str,'<<ERROR>>'))

        self.clear_cache_entry.set_text(scast(self.config.get('gui_clear_cache',30),str,'<<ERROR>>'))

        if self.config.get('ignore_modified',True): self.ignore_modified_button.set_active(True)
        else: self.ignore_modified_button.set_active(False)

        self.db_entry.set_text(scast(self.config.get('db_path',''), str, '<<ERROR>>'))
        self.log_entry.set_text(scast(self.config.get('log',''), str, '<<ERROR>>'))

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

        self.result['notify_level'] = f_get_combo(self.notify_level_combo)

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

        color = self.flag_color_button_1.get_color()
        self.result['gui_flag_1_color'] = color.to_string()
        color = self.flag_color_button_2.get_color()
        self.result['gui_flag_2_color'] = color.to_string()
        color = self.flag_color_button_3.get_color()
        self.result['gui_flag_3_color'] = color.to_string()
        color = self.flag_color_button_4.get_color()
        self.result['gui_flag_4_color'] = color.to_string()
        color = self.flag_color_button_5.get_color()
        self.result['gui_flag_5_color'] = color.to_string()

        self.result['gui_flag_1_name'] = self.flag_name_entry_1.get_text()
        self.result['gui_flag_2_name'] = self.flag_name_entry_2.get_text()
        self.result['gui_flag_3_name'] = self.flag_name_entry_3.get_text()
        self.result['gui_flag_4_name'] = self.flag_name_entry_4.get_text()
        self.result['gui_flag_5_name'] = self.flag_name_entry_5.get_text()

        color = self.new_color_button.get_color()
        self.result['gui_new_color'] = color.to_string()
        color = self.del_color_button.get_color()
        self.result['gui_deleted_color'] = color.to_string()
        color = self.hl_color_button.get_color()
        self.result['gui_hilight_color'] = color.to_string()

        self.result['gui_key_search'] = self.key_search_entry.get_text()
        self.result['gui_key_new_entry'] = self.key_new_entry_entry.get_text()
        self.result['gui_key_new_rule'] = self.key_new_rule_entry.get_text()

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

        Gtk.Dialog.__init__(self, title='Keywords', transient_for=parent, flags=0)

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
        self.rule_list.append_column( f_col('Keyword',0 , 0, resizable=True, clickable=True, start_width=300) )
        self.rule_list.append_column( f_col('Weight',0 , 1, resizable=True, clickable=True, start_width=300) )

        self.rule_list.set_tooltip_markup("""Keywords extracted from entry
Hit <b>Ctrl-F</b> for interactive search""")

        self.rule_list.set_enable_search(True)
        self.rule_list.set_search_equal_func(parent.quick_find_case_ins, 0)
        
        scwindow.add(self.rule_list)

        done_button = f_button('Done','object-select-symbolic', connect=self.on_done)
        grid.attach(header_label, 1,1, 12,1)
        grid.attach(scwindow, 1,2, 12, 10)
        grid.attach(done_button, 1,12, 2,1)

        box.add(grid)
        self.show_all()
        self.rule_list.columns_autosize()

    def on_done(self, *args):
        self.response = 0
        self.close()






