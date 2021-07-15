# -*- coding: utf-8 -*-
""" GUI dialog windows classes for FEEDEX """

from feedex_headers import *
from feedex_gui_utils import *





class InfoDialog(Gtk.Dialog):
    """Info Dialog - no choice """

    def __init__(self, parent, title, text, **args):

        self.response = 0

        Gtk.Dialog.__init__(self, title=title, transient_for=parent, flags=0)

        box = self.get_content_area()

        box1 = Gtk.Box()
        box1.set_orientation(Gtk.Orientation.VERTICAL)
        box1.set_homogeneous(False)
        box1.set_border_width(5)

        subt = args.get('subtitle',None)
        self.set_default_size(args.get('width',600), args.get('height',10))

        label = fxlabel(text,0,2,False,True, markup=True)
        box1.pack_start(label, False,False, 3)

        if subt != None:
            sublabel = fxlabel(subt,0,2,False,True, markup=True)
            box1.pack_start(sublabel, False, False, 3)        

        bbox = Gtk.Box()
        bbox.set_orientation(Gtk.Orientation.HORIZONTAL)
        bbox.set_homogeneous(False)
        bbox.set_border_width(5)

        close_button = fxbutton('Close','object-select-symbolic', self.on_close)

        bbox.pack_end(close_button, False, False, 3)

        box.add(box1)
        box.pack_end(bbox, False, False, 3)
    
        self.show_all()



    def on_close(self, *kargs):
        self.close()








class YesNoDialog(Gtk.Dialog):
    """ Yes/No Choice dialog """

    def __init__(self, parent, title, text, **args):

        self.response = 0 # This marks the user's main choice

        Gtk.Dialog.__init__(self, title=title, transient_for=parent, flags=0)

        box = self.get_content_area()

        box1 = Gtk.Box()
        box1.set_orientation(Gtk.Orientation.VERTICAL)
        box1.set_homogeneous(False)
        box1.set_border_width(5)

        subt = args.get('subtitle',None)
        self.set_default_size(args.get('width',600), args.get('height',10))

        label = fxlabel(text,0,2,False,True, markup=True)
        box1.pack_start(label, False,False, 3)

        if subt != None:
            sublabel = fxlabel(subt,0,2,False,True, markup=True)
            box1.pack_start(sublabel, False, False, 3)        

        bbox = Gtk.Box()
        bbox.set_orientation(Gtk.Orientation.HORIZONTAL)
        bbox.set_homogeneous(False)
        bbox.set_border_width(5)

        yes_button = fxbutton('Yes','object-select-symbolic', self.on_yes)
        no_button = fxbutton('No','action-unavailable-symbolic', self.on_no)

        bbox.pack_end(yes_button, False, False, 3)
        bbox.pack_start(no_button, False, False, 3)

        box.add(box1)
        box.pack_end(bbox, False, False, 3)
    
        self.show_all()



    def on_yes(self, *kargs):
        self.response = 1
        self.close()

    def on_no(self, *kargs):
        self.response = 0
        self.close()









class NewFromURL(Gtk.Dialog):
    """ Add from URL dialog with category and handler choice """
    def __init__(self, parent, config, fields, **args):

        self.config = config
        self.debug = args.get('debug',False)

        self.result = {} # This marks form content to be updated after user's response is 1

        Gtk.Dialog.__init__(self, title="Add Channel from URL", transient_for=parent, flags=0)
        self.set_border_width(10)
        self.set_default_size(args.get('width',800), args.get('height',100))
        box = self.get_content_area()

        self.url_entry = Gtk.Entry()
        self.url_entry.set_text(fields.get('url',''))

        self.cat_combo = feed_combo(parent.FX, tooltip="Choose Category to assign this Channel to\nCategories are useful for quick filtering and organizing Channels")
        self.cat_combo.set_active(fx_get_combo_id(self.cat_combo, fields.get('category')))

        self.handler_combo = handler_combo(0, no_local=True)
        self.handler_combo.set_active(fx_get_combo_id(self.handler_combo, fields.get('handler')))
        self.handler_combo.connect('changed',self.on_changed)

        self.add_button = fxbutton('Add','list-add-symbolic', self.on_add)
        self.cancel_button = fxbutton('Cancel','action-unavailable-symbolic', self.on_cancel)

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


    def on_changed(self, *kargs):
        handler = fx_get_combo(self.handler_combo)
        if handler == 'rss':
            self.url_entry.set_tooltip_markup('Enter Channel\'s <b>URL</b> here')
        elif handler == 'twitter':
            self.url_entry.set_tooltip_markup('Enter <b>#Hashtag</b>/<b>Twitter Profile</b> here')
        else: 
            self.url_entry.set_tooltip_markup('Enter Channel\'s <b>URL</b> here')

    def get_result(self):
        """ Populate result from form contents """
        handler = fx_get_combo(self.handler_combo)
        category = nullif(fx_get_combo(self.cat_combo), 0)
        self.result = {'url' : self.url_entry.get_text(), 'category' : category, 'handler': handler }

    def on_cancel(self, *kargs):
        self.response = 0
        self.get_result()
        self.close()

    def on_add(self, *kargs):
        self.response = 1
        self.get_result()
        self.close()





class EditCategory(Gtk.Dialog):
    """ Edit category dialog (change title and subtitle) """
    def __init__(self, parent, category, **args):

        self.name = scast(category.get('name',''), str, '')
        self.subtitle = scast(category.get('subtitle',''), str, '')

        if args.get('new',True):
            title = "Add New Category"
        else:
            title = f"Edit {self.name} Category"

        Gtk.Dialog.__init__(self, title=title, transient_for=parent, flags=0)
        self.set_border_width(10)
        self.set_default_size(args.get('width',800), args.get('height',100))
        box = self.get_content_area()

        name_label = fxlabel('Name:', None, 0, False, False)
        subtitle_label = fxlabel('Subtitle:', None, 0, False, False)
        self.name_entry = Gtk.Entry()
        self.name_entry.set_tooltip_markup('Enter Category name here')
        self.subtitle_entry = Gtk.Entry()
        self.subtitle_entry.set_tooltip_markup('Enter subtitle/description name here')

        save_button = fxbutton('Save','object-select-symbolic', self.on_save)
        cancel_button = fxbutton('Cancel','action-unavailable-symbolic', self.on_cancel)
        clear_button = fxbutton('Restore','edit-redo-rtl-symbolic', self.on_restore)
    
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

    def on_restore(self, *kargs):
        """ Restore data to defaults """
        self.result = {}
        self.name_entry.set_text(self.name)
        self.subtitle_entry.set_text(self.subtitle)

    def on_cancel(self, *kargs):
        self.response = 0
        self.result = {'name':nullif(self.name_entry.get_text(),''), 'subtitle': nullif(self.subtitle_entry.get_text(),'') }
        self.close()

    def on_save(self, *kargs):
        self.response = 1
        self.result = {'name':nullif(self.name_entry.get_text(),''), 'subtitle': nullif(self.subtitle_entry.get_text(),'') }
        self.close()





class ChangeCategory(Gtk.Dialog):
    """ Change feed's category dialog """
    def __init__(self, parent, feed_name, curr_category, **args):

        self.result = {}
        self.response = 0

        Gtk.Dialog.__init__(self, title='Change Category', transient_for=parent, flags=0)
        self.set_default_size(args.get('width',700), args.get('height',100))
        box = self.get_content_area()

        self.set_border_width(10)
        self.set_resizable(False)
        self.set_position(Gtk.WindowPosition.CENTER)

        feed_label = fxlabel('',None, 0, False, False)
        feed_label.set_markup(f'Choose category for Channel <i><b>{feed_name}</b></i>:')
        self.cat_combo = feed_combo(parent.FX, tooltip="Choose category to assign this feed to")
        self.cat_combo.set_active(fx_get_combo_id(self.cat_combo, curr_category))

        vbox = Gtk.Box()
        vbox.set_orientation(Gtk.Orientation.HORIZONTAL)
        vbox.set_homogeneous(False)
        vbox.set_border_width(5)

        save_button = fxbutton('Save','object-select-symbolic', self.on_save)
        cancel_button = fxbutton('Cancel','action-unavailable-symbolic', self.on_cancel)

        vbox.pack_start(cancel_button, False, False, 5)
        vbox.pack_end(save_button, False, False, 5)

        box.add(feed_label)
        box.add(self.cat_combo)
        box.add(vbox)
        self.show_all()


    def on_save(self, *kargs):
        self.response = 1
        self.result = nullif(fx_get_combo(self.cat_combo), 0)
        if self.result <= 0: self.result = None
        self.close()
    
    def on_cancel(self, *kargs):
        self.response = 0
        self.result = 0
        self.close()





class EditEntry(Gtk.Dialog):
    """ Edit Entry dialog """
    def __init__(self, parent, config, fields, **args):

        if args.get('new',False): 
            title = 'Add new Entry'
            restore_label = 'Clear'
            self.new = True
        else: 
            title = 'Edit Entry'
            restore_label = 'Restore'
            self.new = False

        self.config = config
        self.fields = fields

        Gtk.Dialog.__init__(self, title=title, transient_for=parent, flags=0)
        self.set_default_size(args.get('width',800), args.get('height',500))
        box = self.get_content_area()

        self.set_border_width(10)
        self.set_resizable(False)
        self.set_position(Gtk.WindowPosition.CENTER)

        self.result = {}
        self.response = 0
        
        self.cat_combo = feed_combo(parent.FX, with_feeds=True, no_empty=True, icons=parent.icons, tooltip="""Choose <b>Category</b> or <b>Channel</b> to assign this Entry to.
It is a good idea to have categories exclusively for manually added entries for quick access to notes, hilights etc.
<i>Every Entry needs to be assigned to a Category or a Channel</i>""")

        title_label = fxlabel('<b>Title:</b>', None, 0, False, False, markup=True)
        self.title_entry = Gtk.Entry()
        self.title_entry.set_tooltip_markup('Enter Entry\'s title here')

        desc_label = fxlabel('<b>Description:</b>', None, 0, False, False, markup=True)
        desc_sw = Gtk.ScrolledWindow()
        self.desc_text = Gtk.TextBuffer()
        desc_entry = Gtk.TextView(buffer=self.desc_text)
        desc_entry.set_tooltip_markup('Enter Entry\'s details/description here')
        desc_entry.set_wrap_mode(Gtk.WrapMode.WORD)
        desc_sw.add(desc_entry)

        text_label = fxlabel('<b>Additional text:</b>', None, 0, False, False, markup=True)
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

        self.save_button = fxbutton('  Save  ','object-select-symbolic', self.on_save, tooltip="Save Entry")
        self.cancel_button = fxbutton('Cancel','action-unavailable-symbolic', self.on_cancel)
        self.clear_button = fxbutton(restore_label ,'edit-undo-rtl-symbolic', self.on_restore)

        grid = Gtk.Grid()
        grid.set_column_spacing(10)
        grid.set_row_spacing(10)
        grid.set_column_homogeneous(True)
        grid.set_row_homogeneous(True)

        grid.attach(self.cat_combo, 1,1, 15,1)
        grid.attach(title_label, 1,2, 3,1)
        grid.attach(self.title_entry, 5,2, 10,1)
        grid.attach(desc_label, 1,3, 4,1)
        grid.attach(desc_sw, 1,4, 15,6)
        grid.attach(text_label, 1,11, 4,1)
        grid.attach(text_sw, 1,12, 15,4)
        if self.new:
            grid.attach(self.learn_button, 1, 16, 6,1)

        vbox = Gtk.Box()
        vbox.set_orientation(Gtk.Orientation.HORIZONTAL)
        vbox.set_homogeneous(False)
        vbox.set_border_width(5)

        vbox.pack_start(self.cancel_button, False, False, 5)
        vbox.pack_start(self.clear_button, False, False, 5)
        vbox.pack_end(self.save_button, False, False, 5)
            
        box.add(grid)
        box.add(vbox)
    
        self.on_restore(new=False)
        self.show_all()


    def get_result(self):
        self.result = { 'feed_id': nullif(fx_get_combo(self.cat_combo), 0),
                        'title': nullif(self.title_entry.get_text(),''), 
                        'desc': nullif(self.desc_text.get_text(self.desc_text.get_start_iter(), self.desc_text.get_end_iter(), False),''), 
                        'text': nullif(self.text_text.get_text(self.text_text.get_start_iter(), self.text_text.get_end_iter(), False),''), 
                        'learn': self.learn_button.get_active() }


    def on_restore(self, *kargs, **args):
        new = args.get('new',self.new)
        if new:
            self.cat_combo.set_active(0)
            self.title_entry.set_text('')
            self.desc_text.set_text('')
            self.text_text.set_text('')
            if self.config.get('learn_from_added_entries',True): self.learn_button.set_active(True)        
            else: self.learn_button.set_active(False) 
            self.get_result()
        else:
            self.cat_combo.set_active(fx_get_combo_id(self.cat_combo, self.fields.get('feed_id',0)))
            self.title_entry.set_text(scast(self.fields.get('title',''), str, ''))
            self.desc_text.set_text(scast(self.fields.get('desc',''), str, ''))
            self.text_text.set_text(scast(self.fields.get('text',''), str, ''))
            if self.config.get('learn_from_added_entries',True): self.learn_button.set_active(True)        
            else: self.learn_button.set_active(False)        



    def on_save(self, *kargs):
        self.response = 1
        self.get_result()
        self.close()

    def on_cancel(self, *kargs):
        self.response = 0
        self.get_result()
        self.close()





class EditRule(Gtk.Dialog):
    """ Rule Edit dialog """
    def __init__(self, parent, config, fields, **args):
        if args.get('new',True): title = 'Add new Rule'
        else: title = 'Edit Rule'

        self.config = config
        self.fields = fields

        Gtk.Dialog.__init__(self, title=title, transient_for=parent, flags=0)
        self.set_default_size(args.get('width',1000), args.get('height',400))
        box = self.get_content_area()

        self.set_border_width(10)
        self.set_resizable(False)
        self.set_position(Gtk.WindowPosition.CENTER)

        self.result = {}
        self.response = 0

        name_label = fxlabel('Name:', None, 0, False, False)
        self.name_entry = Gtk.Entry()
        self.name_entry.set_tooltip_markup('Display name for this rule (<i>not used in matching</i>)')
        string_label = fxlabel('Search string:', None, 0, False, False)
        self.string_entry = Gtk.Entry()
        self.string_entry.set_tooltip_markup("""String or Pattern used for search and matching
It is used according to <b>Type</b> and should be compatibile with it (e.g. REGEX string)""")

        type_label = fxlabel('Type:', None, 0, False, False)
        self.type_combo = qtype_combo(self.on_changed, rule=True)
        feed_label = fxlabel('Feed or Category:', None, 0, False, False)
        self.feed_combo = feed_combo(parent.FX, icons=parent.icons, with_feeds=True, empty_label='-- Every Feed --', tooltip="Which Feed/Channel should this Rule filter?")
        field_label = fxlabel('Field:', None, 0, False, False)
        self.field_combo = qfield_combo(self.on_changed)
        lang_label = fxlabel('Language:', None, 0, False, False)
        self.lang_combo = lang_combo(parent.FX, self.on_changed, tooltip="Which language should this rule use for Full Text Search?")
        case_label = fxlabel('Case:', None, 0, False, False)
        self.case_combo = fxcombo(self.on_changed, ("Case sensitive","Case insensitive"), 'Should this Rule be case sensitive?')

        weight_label = fxlabel('Weight:', None, 0, False, False)
        self.weight_entry = Gtk.Entry()
        self.weight_entry.set_tooltip_markup("""Weight is used to increase article's <b>importance</b> when matched
Articles are then sorted by importance to keep the most important ones on top.
Weights from leaned rules as well as the ones from manually added ones sum up and position an Article""")
            
        self.flag_combo = flag_combo(self.config, filters=False, tooltip="""Main reason for manually added rules is to flag interesting incomming articles independently of importance ranking
Sometimes, however, a rule can simply increase importance by its <b>weight</b> without flagging""") 
        self.additive_button = Gtk.CheckButton.new_with_label('Are matches weights additive?')

        self.err_label = fxlabel('', None, 0, False, False)

        self.save_button = fxbutton('Save','object-select-symbolic', self.on_save, tooltip="Save Rule")
        self.cancel_button = fxbutton('Cancel','action-unavailable-symbolic', self.on_cancel)
        self.restore_button = fxbutton('Restore','edit-undo-rtl-symbolic', self.on_restore)

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



    def on_restore(self, *kargs):
        self.name_entry.set_text(coalesce(self.fields.get('name',''),''))
        self.string_entry.set_text(coalesce(self.fields.get('string',''),''))

        self.type_combo.set_active(fx_get_combo_id(self.type_combo, self.fields.get('type',None)) )
        self.field_combo.set_active(fx_get_combo_id(self.field_combo, self.fields.get('field_id',None)) )
        self.feed_combo.set_active(fx_get_combo_id(self.feed_combo, self.fields.get('feed_id',None)) )
        self.lang_combo.set_active(fx_get_combo_id(self.lang_combo, self.fields.get('lang',None)) )
        self.case_combo.set_active(fx_get_combo_id(self.case_combo, self.fields.get('case_insensitive',0)) )

        self.weight_entry.set_text( scast( scast(self.fields.get('weight', None), float, self.config.get('default_rule_weight',2)), str, '2'  ))

        
        if self.fields.get('flag',None) in (0,None): self.flag_combo.set_active(0)
        else: self.flag_combo.set_active( fx_get_combo_id(self.flag_combo, self.fields.get('flag',0)))

        if self.fields.get('additive',1) == 1: self.additive_button.set_active(True)
        else: self.additive_button.set_active(False)
        

    def on_changed(self, *kargs):
        if fx_get_combo(self.type_combo) in (1,2): self.lang_combo.set_sensitive(True)
        else: self.lang_combo.set_sensitive(False)
        

    def validate_entries(self):
        weight = self.weight_entry.get_text()
        matches = re.findall(FLOAT_VALIDATE_RE, weight)
        if matches in (None, (), [], (None,)):
            self.err_label.set_markup('<span foreground="red">Weight must be a number!</span>')
            return False
        if self.string_entry.get_text() == '':
            self.err_label.set_markup('<span foreground="red">Search string cannot be empty!</span>')
            return False                    
        if fx_get_combo(self.type_combo) == 3 and not check_if_regex(self.string_entry.get_text()):
            self.err_label.set_markup('<span foreground="red">Invalid REGEX string!</span>')
            return False                    

        return True


    def get_result(self):
        weight = scast(self.weight_entry.get_text(), float, self.config.get('default_rule_weight',2))

        self.result = { 'name': nullif(self.name_entry.get_text().strip(),''),
                        'string': nullif(self.string_entry.get_text(),''), 
                        'type': fx_get_combo(self.type_combo),
                        'field_id': fx_get_combo(self.field_combo), 
                        'feed_id': nullif(fx_get_combo(self.feed_combo), 0), 
                        'lang': fx_get_combo(self.lang_combo),
                        'case_insensitive': self.case_combo.get_active(),
                        'weight' : scast(self.weight_entry.get_text(), float, self.config.get('default_rule_weight',2)),
                        'learned' : 0,
                        'flag' : fx_get_combo(self.flag_combo)
                        }

        if self.additive_button.get_active(): self.result['additive'] = 1
        else: self.result['additive'] = 0
    

    def on_save(self, *kargs):
        if self.validate_entries():
            self.response = 1
            self.get_result()            
            self.close()

    def on_cancel(self, *kargs):
        self.response = 0
        self.get_result()
        self.close()






class DisplayRules(Gtk.Dialog):
    """ Display learned rules dialog """
    def __init__(self, parent, header, store, **args):

        Gtk.Dialog.__init__(self, title='Learned Rules', transient_for=parent, flags=0)

        self.set_default_size(args.get('width',1000), args.get('height',500))
        self.set_border_width(10)
        box = self.get_content_area()

        self.response = 0

        grid = Gtk.Grid()
        grid.set_column_spacing(10)
        grid.set_row_spacing(10)
        grid.set_column_homogeneous(True)
        grid.set_row_homogeneous(True)

        header_label = fxlabel(None, '', args.get('justify',0), True, True)
        header_label.set_markup(header)

        scwindow = Gtk.ScrolledWindow()

        self.rule_store = store
        self.rule_list = Gtk.TreeView(model=self.rule_store)
        self.rule_list.append_column( fxcol('Name',0 , 1, resizable=True, clickable=True, start_width=300) )
        self.rule_list.append_column( fxcol('REGEX String',0 , 2, resizable=True, clickable=True, start_width=300) )
        self.rule_list.append_column( fxcol('Weight',0 , 3, resizable=True, clickable=True, start_width=200) )
        self.rule_list.append_column( fxcol('Query Type',0 , 4, resizable=True, clickable=True, start_width=200) )
        
        self.rule_list.set_tooltip_markup("""List of Rules learned after <b>adding Entries</b> and <b>reading Articles</b>
<b>Name</b> - Displayed name, <i>not matched</i>, purely informational
<b>REGEX String</b> - Regular Expression matched against tokenized Entry with prefixes and case markers
<b>Weight</b> - Weight added to Entry when the rule is matched (rule weights are offset by Entry weight to avoid overvaluing very long articles
<b>Query Type</b> - Is rule matched against exact words or stems?""")

        scwindow.add(self.rule_list)

        done_button = fxbutton('Done','object-select-symbolic', self.on_done)
        delete_all_button = fxbutton('Delete all', 'edit-delete-symbolic', self.on_delete_all)
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


    def on_delete_all(self, *kargs):
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

    def on_done(self, *kargs):
        self.response = 0
        self.close()




class DisplayWindow(Gtk.Dialog):
    """ General purpose display window (options are text, text with emblem and a picture (downloaded or from file) """
    def __init__(self, parent, title, text, **args):

        Gtk.Dialog.__init__(self, title=title, transient_for=parent, flags=0)

        self.set_default_size(args.get('width',1000), args.get('height',500))
        box = self.get_content_area()

        self.set_border_width(10)
        self.set_resizable(False)
        self.set_position(Gtk.WindowPosition.CENTER)

        if args.get('close_on_unfocus',False):
            self.connect('focus-out-event', self.on_close)

        image = args.get('image')
        image_url = args.get('image_url')


        if image != None:
            self.set_resizable(True)
            win = Gtk.ScrolledWindow()
            image = Gtk.Image.new_from_file(image)
            image.set_tooltip_markup(text)            
            image.show()
            win.add(image)

        elif image_url != None:
            self.mode = 'image'
            self.set_resizable(True)
            win = Gtk.ScrolledWindow()
            headers = {'User-Agent' : 'UniversalFeedParser/5.0.1 +http://feedparser.org/'}
            try:
                req = urllib.request.Request(image_url, None, headers)
                response = urllib.request.urlopen(req)
                if response.status == 200:
                    img_data = BytesIO(response.read())
                    self.img = Image.open(img_data)
                    image = Gtk.Image.new_from_pixbuf( image2pixbuf(self.img) )
                    image.set_tooltip_markup(text)            
                    image.show()
                    win.add(image)

            except Exception as e:
                sys.stderr.write(f'Could not download image at {image_url}! ({e})')
                return None

        else:
            self.set_resizable(False)
            self.mode = 'text'
            win = Gtk.ScrolledWindow()
            win.set_border_width(8)
            vbox = Gtk.Box()
            vbox.set_orientation(Gtk.Orientation.VERTICAL)
            vbox.set_homogeneous(False)

            emblem = args.get('emblem')
            if emblem != None:
                image = Gtk.Image.new_from_pixbuf(emblem)
                vbox.pack_start(image, False, False, 0)

            self.label = fxlabel(None, '', args.get('justify',0), True, True)
            if args.get('markup',True):
                self.label.set_markup(text)
            else:
                self.label.set_text(text)
        
            win.add(vbox)
            vbox.pack_start(self.label, False, False, 0)


        bbox = Gtk.Box()
        bbox.set_orientation(Gtk.Orientation.HORIZONTAL)
        bbox.set_homogeneous(False)
        bbox.set_border_width(5)

        done_button = fxbutton('  Done  ', None, self.on_close)
        bbox.pack_start(done_button, False, False, 5)

        if args.get('save_as',False):
            save_as_button = fxbutton('', 'document-save-symbolic', self.on_save_as, tooltip='Save as...')
            bbox.pack_end(save_as_button, False, False, 5)

        grid = Gtk.Grid()
        grid.set_column_spacing(10)
        grid.set_row_spacing(10)
        grid.set_column_homogeneous(True)
        grid.set_row_homogeneous(True)

        grid.attach(win, 1,1, 35, 12)
        grid.attach(bbox, 1, 13, 35, 1)    

        box.add(grid)        
        self.show_all()

        
    def on_close(self, *kargs):
        self.close()


    def on_save_as(self, *kargs):
        dialog = Gtk.FileChooserDialog("Save as..", parent=self, action=Gtk.FileChooserAction.SAVE)
        dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_SAVE, Gtk.ResponseType.OK)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            filename = dialog.get_filename()
            if self.mode == 'image':
                self.img.save(filename)
            elif self.mode == 'text':
                text_to_save = self.label.get_text()
                with open(filename, "wb") as write_file:
                    write_file.write(text_to_save)

        dialog.destroy()







class AboutDialog(Gtk.Dialog):
    """ Display "About..." dialog """
    def __init__(self, parent, **args):
        Gtk.Dialog.__init__(self, title="About FEEDEX", transient_for=parent, flags=0)
        self.set_default_size(args.get('width',500), args.get('height',250))
        box = self.get_content_area()
        pb = GdkPixbuf.Pixbuf.new_from_file_at_size(f"{FEEDEX_SYS_ICON_PATH}/feedex.png", 64, 64)
        icon = Gtk.Image.new_from_pixbuf(pb)
        main_label = fxlabel('',0,2,False, False)
        secondary_label = fxlabel('',0,2,False, False)
        author_label = fxlabel('',0,2,False, False)
        website_label = fxlabel('',0,2,False, False)

        close_button = fxbutton('   Close   ',None, self.on_close)
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

        website_label.set_markup(f"""Website: <a href="{GObject.markup_escape_text(FEEDEX_WEBSITE)}">{GObject.markup_escape_text(FEEDEX_WEBSITE)}</a>""")

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





class DateChoose(Gtk.Dialog):
    """ Date chooser for main window queries """
    def __init__(self, parent, **args):

        self.response = 0
        self.rng = [None, None]

        Gtk.Dialog.__init__(self, title="Choose date range", transient_for=parent, flags=0)
        self.set_default_size(args.get('width',400), args.get('height',200))
        box = self.get_content_area()
        grid = Gtk.Grid()
        grid.set_column_spacing(3)
        grid.set_row_spacing(3)
        grid.set_column_homogeneous(True)
        grid.set_row_homogeneous(True)

        from_label = fxlabel('  From:', 'normal', 0, False, False)
        to_label = fxlabel('    To:', 'normal', 0, False, False)

        from_clear_button = Gtk.CheckButton.new_with_label('Empty')
        from_clear_button.connect('toggled', self.clear_from)
        to_clear_button = Gtk.CheckButton.new_with_label('Empty')
        to_clear_button.connect('toggled', self.clear_to)

        accept_button = fxbutton('Accept','object-select-symbolic', self.accept)
        cancel_button = fxbutton('Cancel','window-close-symbolic', self.cancel)

        self.cal_from = Gtk.Calendar()
        self.cal_to = Gtk.Calendar()
        self.cal_from.connect('day-selected', self.on_from_selected)
        self.cal_to.connect('day-selected', self.on_to_selected)

        grid.attach(from_label,1,0,3,1)
        grid.attach(to_label,7,0,3,1)
        grid.attach(self.cal_from,0,1,5,5)
        grid.attach(self.cal_to,6,1,5,5)
        grid.attach(from_clear_button,0,6,1,1)
        grid.attach(to_clear_button,6,6,1,1)
        grid.attach(cancel_button,0,10,3,1)
        grid.attach(accept_button,8,10,3,1)

        box.add(grid)
        self.show_all()
        self.on_to_selected()
        self.on_from_selected()

    def accept(self, *kargs):
        self.response = 1        
        self.close()

    def cancel(self, *kargs):
        self.response = 0
        self.close()
        
    def clear_from(self, *kargs):
        self.rng[0] = None
        if self.cal_from.get_sensitive():
            self.cal_from.set_sensitive(False)
        else:
            self.cal_from.set_sensitive(True)

    def clear_to(self, *kargs):
        self.rng[1] = None        
        if self.cal_to.get_sensitive():
            self.cal_to.set_sensitive(False)
        else:
            self.cal_to.set_sensitive(True)

    def on_from_selected(self, *kargs):
        (year, month, day) = self.cal_from.get_date()
        self.rng[0] = f'{scast(year,str,"")}/{scast(month+1,str,"")}/{scast(day,str,"")}'

    def on_to_selected(self, *kargs):
        (year, month, day) = self.cal_to.get_date()
        self.rng[1] = f'{scast(year,str,"")}/{scast(month+1,str,"")}/{scast(day,str,"")}'







class EditFeed(Gtk.Dialog):    
    """ Edit Feed dialog """
    def __init__(self, parent, fields, FX, **args):

        self.result = {}
        self.response = 0
        self.config = args.get('config',DEFAULT_CONFIG)

        self.fields = fields

        name = fields.get('name', fields.get('title', fields.get('id','<<UNKNOWN>>')))
        if args.get('new',False): title = 'Add new Feed'
        else: title = f'Edit {name} Chanel'

        Gtk.Dialog.__init__(self, title=title, transient_for=parent, flags=0)
        self.set_default_size(args.get('width',1000), args.get('height',500))
        box = self.get_content_area()

        self.cat_combo = feed_combo(FX, tooltip="""Choose <b>Category</b> to assign this Feed to
Categories are useful for bulk-filtering and general organizing""")

        self.handler_combo = handler_combo(0)
        self.handler_combo.connect('changed', self.on_changed)
        
        name_label = fxlabel('Name:','normal',0,False,False)
        self.name_entry = Gtk.Entry() 
        self.name_entry.set_tooltip_markup("Display name for this Channel")        

        title_label = fxlabel('Title:','normal',0,False,False)
        self.title_entry = Gtk.Entry()
        self.title_entry.set_tooltip_markup("This is a title given by publisher and downloaded from Feed's page")        

        subtitle_label = fxlabel('Subtitle:','normal',0,False,False)
        self.subtitle_entry = Gtk.Entry()

        url_label = fxlabel('URL:','normal',0,False,False)
        self.url_entry = Gtk.Entry()
        
        home_label = fxlabel('Homepage:','normal',0,False,False)
        self.home_entry = Gtk.Entry()
        self.home_entry.set_tooltip_markup("URL to Channel's Homepage")

        self.autoupdate_button = Gtk.CheckButton.new_with_label('Autoupdate metadata?')
        self.autoupdate_button.set_tooltip_markup("""Should Channel's metadata be updated everytime news are fetched from it?
<i>Updating on every fetch can cause unnecessary overhead</i>""")

        interval_label = fxlabel('Fetch interval:','normal',0,False,False)
        self.interval_entry = Gtk.Entry()
        self.interval_entry.set_tooltip_markup('Set news checking/fetching interval for this Channel.\nEnter <b>0</b> to disable fetching for this Channel alltogether')

        author_label = fxlabel('Author:', 'normal', 0, False, False)
        self.author_entry = Gtk.Entry()

        author_contact_label = fxlabel('Author contact:', 'normal', 0, False, False)
        self.author_contact_entry = Gtk.Entry()

        publisher_label = fxlabel('Publisher:', 'normal', 0, False, False)
        self.publisher_entry = Gtk.Entry()

        publisher_contact_label = fxlabel('Publisher contact:', 'normal', 0, False, False)
        self.publisher_contact_entry = Gtk.Entry()

        contributors_label = fxlabel('Contributors:', 'normal', 0, False, False)
        self.contributors_entry = Gtk.Entry()

        category_label = fxlabel('Category:', 'normal', 0, False, False)
        self.category_entry = Gtk.Entry()
        
        tags_label = fxlabel('Tags:', 'normal', 0, False, False)
        self.tags_entry = Gtk.Entry()
                
        self.err_label = fxlabel('', 'normal', 0, False, False)


        self.save_button = fxbutton('Save','object-select-symbolic', self.on_save, tooltip="Save Entry")
        self.cancel_button = fxbutton('Cancel','action-unavailable-symbolic', self.on_cancel)
        self.restore_defaults_button = fxbutton('Restore','edit-redo-rtl-symbolic', self.on_restore, tooltip="Restore preferences to defaults")
    
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

        grid.attach(self.err_label, 1, 13, 12,1)

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


    def on_changed(self, *kargs):
        handler = fx_get_combo(self.handler_combo)
        if handler == 'rss':
            self.url_entry.set_tooltip_markup("Valid <b>URL</b> to Channel")
        elif handler == 'twitter':
            self.url_entry.set_tooltip_markup("<b>#Hashtag</b> or <b>Twitter Username</b> to Channel")
        elif handler == 'local':
            self.url_entry.set_tooltip_markup("""For <b>local</b> feeds this can be any string, as it is not used
Local feeds are updated only by scripts or CLI (<i>--add-entry</i>, <i>--add-entries-from-file</i>, or <i>--add-entries-from-pipe</i> options)""")

    def on_restore(self, *kargs):

        self.cat_combo.set_active(fx_get_combo_id(self.cat_combo, self.fields.get('parent_id',0)))
        self.handler_combo.set_active(fx_get_combo_id(self.handler_combo, self.fields.get('handler','rss')) )

        self.name_entry.set_text(coalesce(self.fields.get('name',''),''))
        self.title_entry.set_text(coalesce(self.fields.get('title',''),''))
        self.subtitle_entry.set_text(coalesce(self.fields.get('subtitle',''),''))
        self.url_entry.set_text(coalesce(self.fields.get('url',''),''))
        self.home_entry.set_text(coalesce(self.fields.get('link',''),''))
        if self.fields.get('autoupdate',0) == 1: self.autoupdate_button.set_active(True)
        else: self.autoupdate_button.set_active(False)
        self.interval_entry.set_text(scast(self.fields.get('interval', self.config.get('default_interval',45)), str, ''))        
        self.author_entry.set_text(coalesce(self.fields.get('author',''),''))
        self.author_contact_entry.set_text(coalesce(self.fields.get('author_contact',''),''))
        self.publisher_entry.set_text(coalesce(self.fields.get('publisher',''),''))
        self.publisher_contact_entry.set_text(coalesce(self.fields.get('publisher_contact',''),''))
        self.contributors_entry.set_text(coalesce(self.fields.get('contributors',''),''))
        self.category_entry.set_text(coalesce(self.fields.get('category',''),''))
        self.tags_entry.set_text(coalesce(self.fields.get('tags',''),''))


    def validate_entries(self, *kargs):
        if not self.interval_entry.get_text().isdigit():
            self.err_label.set_markup('<span foreground="red">Interval must be a number!</span>')
            return False
        if self.home_entry.get_text().strip() != '' and not check_url(self.home_entry.get_text()):
            self.err_label.set_markup('<span foreground="red">Invalid Home URL!</span>')
            return False
        if not check_url(self.url_entry.get_text()) and fx_get_combo(self.handler_combo) in ('rss',):
            self.err_label.set_markup('<span foreground="red">Invalid URL!</span>')
            return False

        return True
    

    def get_result(self, *kargs):
        self.result['parent_id'] = nullif(fx_get_combo(self.cat_combo), 0)
        self.result['handler'] = fx_get_combo(self.handler_combo)
        self.result['name'] = nullif(self.name_entry.get_text(),'')
        self.result['title'] = nullif(self.title_entry.get_text(),'')
        self.result['subtitle'] = nullif(self.subtitle_entry.get_text(),'')
        self.result['url'] = nullif(self.url_entry.get_text(),'')
        self.result['link'] = nullif(self.home_entry.get_text(),'')
        if self.autoupdate_button.get_active(): self.result['autoupdate'] = 1
        else: self.result['autoupdate'] = 0
        self.result['interval'] = nullif(self.interval_entry.get_text(),'')
        self.result['author'] = nullif(self.author_entry.get_text(),'')
        self.result['author_contact'] = nullif(self.author_contact_entry.get_text(),'')
        self.result['publisher'] = nullif(self.publisher_entry.get_text(),'')
        self.result['publisher_contact'] = nullif(self.publisher_contact_entry.get_text(),'')
        self.result['contributors'] = nullif(self.contributors_entry.get_text(),'')
        self.result['category'] = nullif(self.category_entry.get_text(),'')
        self.result['tags'] = nullif(self.tags_entry.get_text(),'')
            


    def on_save(self, *kargs):
        if self.validate_entries():
            self.response = 1
            self.get_result()
            self.close()

    def on_cancel(self, *kargs):
        self.response = 0
        self.get_result()
        self.close()
    






class PreferencesDialog(Gtk.Dialog):
    """ Edit preferences dialog """
    def __init__(self, parent, config, **args):

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
        
        default_interval_label = fxlabel('Default check interval:', None, 0, False, False)
        self.default_interval_entry = Gtk.Entry()
        self.default_interval_entry.set_tooltip_markup('Default fetching interval for newly added feeds')
        
        rule_limit_label = fxlabel('Ranking rules limit:', None, 0, False, False)
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


        self.notify_level_combo = fxcombo(self.on_changed, ((1, 'Summary'), (2, 'All new entries'), (3, 'Only flagged entries'),), "How should Feedex notify?")

        default_entry_weight_label = fxlabel('New Entry default weight:', None, 0, False, False)
        self.default_entry_weight_entry = Gtk.Entry()
        self.default_entry_weight_entry.set_tooltip_markup('Default weight for manually added Entries for rule learning')

        self.learn_from_added_button = Gtk.CheckButton.new_with_label('Learn from added Entries?')
        self.learn_from_added_button.set_tooltip_markup('Should Feedex learn rules/keywords from manually added entries?\nUseful for utilizing highlights and notes for news ranking')

        default_rule_weight_label = fxlabel('Rule default weight:', None, 0, False, False)
        self.default_rule_weight_entry = Gtk.Entry()
        self.default_rule_weight_entry.set_tooltip_markup('Default weight assigned to manually added rule (if not provided)')

        self.learn_queries_button = Gtk.CheckButton.new_with_label('Save queries as rules?')
        self.learn_queries_button.set_tooltip_markup('Should executed queries be saved as rules? Useful for utilizing search habits for news ranking')

        query_rule_weight_label = fxlabel('Default Query weight:', None, 0, False,False)
        self.query_rule_weight_entry = Gtk.Entry()
        self.query_rule_weight_entry.set_tooltip_markup('Weight ascribed to rules earned from queries')
        
        flag_color_label_1 = fxlabel('Flag 1 color:', None, 0, False,False)
        flag_color = Gdk.color_parse(self.config.get('gui_flag_1_color','blue'))
        self.flag_color_button_1 = Gtk.ColorButton(color=flag_color)
        flag_name_label_1 = fxlabel('    Flag 1 name:', None, 0, False,False)
        self.flag_name_entry_1 = Gtk.Entry()

        flag_color_label_2 = fxlabel('Flag 2 color:', None, 0, False,False)
        flag_color = Gdk.color_parse(self.config.get('gui_flag_2_color','blue'))
        self.flag_color_button_2 = Gtk.ColorButton(color=flag_color)
        flag_name_label_2 = fxlabel('    Flag 2 name:', None, 0, False,False)
        self.flag_name_entry_2 = Gtk.Entry()

        flag_color_label_3 = fxlabel('Flag 3 color:', None, 0, False,False)
        flag_color = Gdk.color_parse(self.config.get('gui_flag_3_color','blue'))
        self.flag_color_button_3 = Gtk.ColorButton(color=flag_color)
        flag_name_label_3 = fxlabel('    Flag 3 name:', None, 0, False,False)
        self.flag_name_entry_3 = Gtk.Entry()

        flag_color_label_4 = fxlabel('Flag 4 color:', None, 0, False,False)
        flag_color = Gdk.color_parse(self.config.get('gui_flag_4_color','blue'))
        self.flag_color_button_4 = Gtk.ColorButton(color=flag_color)
        flag_name_label_4 = fxlabel('    Flag 4 name:', None, 0, False,False)
        self.flag_name_entry_4 = Gtk.Entry()

        flag_color_label_5 = fxlabel('Flag 5 color:', None, 0, False,False)
        flag_color = Gdk.color_parse(self.config.get('gui_flag_5_color','blue'))
        self.flag_color_button_5 = Gtk.ColorButton(color=flag_color)
        flag_name_label_5 = fxlabel('    Flag 5 name:', None, 0, False,False)
        self.flag_name_entry_5 = Gtk.Entry()

        new_color_label = fxlabel('Added entry color:', None, 0, False,False)
        new_color = Gdk.color_parse(self.config.get('gui_new_color','#0FDACA'))
        self.new_color_button = Gtk.ColorButton(color=new_color)

        del_color_label = fxlabel('Deleted color:', None, 0, False,False)
        del_color = Gdk.color_parse(self.config.get('gui_deleted_color','grey'))
        self.del_color_button = Gtk.ColorButton(color=del_color)
        
        self.ignore_images_button = Gtk.CheckButton.new_with_label('Ignore Images?')
        self.ignore_images_button.set_tooltip_markup('Should images and icons be ignored alltogether? Ueful for better performance')

        browser_label = fxlabel('Default WWW browser:', None, 0, False, False)
        self.browser_entry = Gtk.Entry()
        self.browser_entry.set_tooltip_markup('Command for opening in browser. Use <b>u%</b> symbol to substitute for URL')
        browser_application_button = fxbutton('','view-app-grid-symbolic', self.on_app_choose_browser, tooltip="Choose from installed applications")

        self.external_iv_application_button = fxbutton('','view-app-grid-symbolic', self.on_app_choose_iv, tooltip="Choose from installed applications")
        external_iv_label = fxlabel('External image viewer:', None, 0, False, False)
        self.external_iv_entry = Gtk.Entry()
        self.external_iv_entry.set_tooltip_markup('Command for viewing images by right-clicking on them.\nUse <b>%u</b> symbol to substitute for temp filename\n<b>%t</b> symbol will be replaced by <b>title</b>\n<b>%a</b> symbol will be replaced by <b>alt</b> field')

        similarity_limit_label = fxlabel('Similarity query limit:', None, 0, False, False)
        self.similarity_limit_entry = Gtk.Entry()
        self.similarity_limit_entry.set_tooltip_markup('Limit similarity query items for improved query performance')

        error_threshold_label = fxlabel('Error threshold:', None, 0, False, False)
        self.error_threshold_entry = Gtk.Entry()
        self.error_threshold_entry.set_tooltip_markup('After how many download errors should a Channel be marked as unhealthy and ignored while fetching?')

        self.ignore_modified_button = Gtk.CheckButton.new_with_label('Ignore modified Tags?')
        self.ignore_modified_button.set_tooltip_markup('Should ETags and Modified fields be ignored while fetching? If yes, Feedex will fetch news even when publisher suggest not to (e.g. no changes where made to feed)')

        clear_cache_label = fxlabel('Clear cached files older than how many days?', None, 0, False, False)
        self.clear_cache_entry = Gtk.Entry()
        self.clear_cache_entry.set_tooltip_markup('Files in cache include thumbnails and images. It is good to keep them but older items should release space')

        db_label = fxlabel('Database:', None, 0, False, False)
        db_choose_button = fxbutton('','folder-symbolic', self.on_file_choose_db, tooltip="Search filesystem")
        self.db_entry = Gtk.Entry()
        self.db_entry.set_tooltip_markup("Database file to be used for storage.\n<i>Changes require application restart</i>")

        log_label = fxlabel('Log file:', None, 0, False, False)
        log_choose_button = fxbutton('','folder-symbolic', self.on_file_choose_log, tooltip="Search filesystem")
        self.log_entry = Gtk.Entry()
        self.log_entry.set_tooltip_markup("Log file to be used.\n<i>Requires application restart for the changes to take place</i>")

        self.err_label = fxlabel('', None,0, False, False)

        self.save_button = fxbutton('Save','object-select-symbolic', self.on_save, tooltip="Save configuration")
        self.cancel_button = fxbutton('Cancel','action-unavailable-symbolic', self.on_cancel)
        self.restore_button = fxbutton('Restore','edit-redo-rtl-symbolic', self.on_restore, tooltip="Restore preferences to defaults")


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
        fetching_grid.attach(self.ignore_modified_button, 1,3, 5,1)
        fetching_grid.attach(error_threshold_label, 1,4, 2,1)
        fetching_grid.attach(self.error_threshold_entry, 4,4, 3,1)
        fetching_grid.attach(default_interval_label, 1,5, 2,1)
        fetching_grid.attach(self.default_interval_entry, 4,5, 3,1)

        interface_grid = create_grid()    
        interface_grid.attach(self.ignore_images_button, 1,1, 5,1)
        interface_grid.attach(new_color_label, 1,2, 3,1)
        interface_grid.attach(self.new_color_button, 4,2, 1,1)
        interface_grid.attach(del_color_label, 1,3, 3,1)
        interface_grid.attach(self.del_color_button, 4,3, 1,1)

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
        weights_grid.attach(query_rule_weight_label, 1, 2, 3,1)
        weights_grid.attach(self.query_rule_weight_entry, 4,2, 3,1)
        weights_grid.attach(default_rule_weight_label, 1, 3, 3,1)
        weights_grid.attach(self.default_rule_weight_entry, 4, 3, 3,1)

        learn_grid = create_grid()
        learn_grid.attach(self.learn_button, 1,1, 6,1)
        learn_grid.attach(rule_limit_label, 1,2, 3,1)
        learn_grid.attach(self.rule_limit_entry, 4,2, 3,1)
        learn_grid.attach(self.learn_from_added_button, 1,3, 6,1)
        learn_grid.attach(self.learn_queries_button, 1,4, 6,1)
        learn_grid.attach(similarity_limit_label, 1,5, 4,1)
        learn_grid.attach(self.similarity_limit_entry, 5,5, 3,1)

        commands_grid = create_grid()
        commands_grid.attach(browser_label, 1,1, 4,1)
        commands_grid.attach(browser_application_button, 5,1, 1,1)
        commands_grid.attach(self.browser_entry, 6,1, 10,1)
        commands_grid.attach(external_iv_label, 1,2, 4,1)
        commands_grid.attach(self.external_iv_application_button, 5,2, 1,1)
        commands_grid.attach(self.external_iv_entry, 6,2, 10,1)
        
        system_grid = create_grid()
        system_grid.attach(clear_cache_label, 1,1, 5,1)
        system_grid.attach(self.clear_cache_entry, 7,1, 3,1)
        system_grid.attach(db_label, 1,2, 3,1)
        system_grid.attach(db_choose_button, 4,2, 1,1)
        system_grid.attach(self.db_entry, 5,2, 10,1)
        system_grid.attach(log_label, 1,3, 3,1)
        system_grid.attach(log_choose_button, 4,3, 1,1)
        system_grid.attach(self.log_entry, 5,3, 10,1)
        
    
        self.notebook = Gtk.Notebook()
        self.notebook.append_page(fetching_grid, Gtk.Label(label="Fetching"))    
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



    def on_changed(self, *kargs):
        if self.desktop_notify_button.get_active(): self.notify_level_combo.set_sensitive(True)
        else: self.notify_level_combo.set_sensitive(False)



    def on_file_choose_db(self, *kargs): self.file_choose('db')
    def on_file_choose_log(self, *kargs): self.file_choose('log')
    def file_choose(self, target, *kargs):
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




    def on_app_choose_browser(self, *kargs):
        self.app_choose('browser')
    def on_app_choose_iv(self, *kargs):
        self.app_choose('iv')
    def app_choose(self, target):

        if target == 'browser':
            heading = "Choose Default Browser"
            content_type = "text/html"
        elif target == 'iv':
            heading = "Choose Image Viewer"
            content_type = "image/jpeg"

        dialog = Gtk.AppChooserDialog(parent=self, content_type=content_type)
        dialog.set_heading(heading)
        response = dialog.run()
        if response == Gtk.ResponseType.OK:
            app = dialog.get_app_info()
            command = app.get_string('Exec')
            if type(command) == str:
                if target == 'browser':
                    self.browser_entry.set_text(command)
                elif target == 'iv':
                    self.external_iv_entry.set_text(command)
        dialog.destroy()





    def on_restore(self, *kargs):

        if self.config.get('use_keyword_learning', True): self.learn_button.set_active(True)
        else: self.learn_button.set_active(False)

        self.rule_limit_entry.set_text(scast(self.config.get('rule_limit', 50000), str, '<<ERROR>>'))

        if self.config.get('gui_desktop_notify',True): self.desktop_notify_button.set_active(True)
        else: self.desktop_notify_button.set_active(False)
        self.notify_level_combo.set_active(self.config.get('notify_level',1)-1)

        if self.config.get('gui_fetch_periodically',False): self.fetch_in_background_button.set_active(True)
        else: self.fetch_in_background_button.set_active(False)

        self.default_interval_entry.set_text(scast(self.config.get('default_interval',45), str, '<<ERROR>>'))

        self.default_entry_weight_entry.set_text(scast(self.config.get('default_entry_weight',2), str, '<<ERROR>>'))

        if self.config.get('learn_from_added_entries',True): self.learn_from_added_button.set_active(True)
        else: self.learn_from_added_button.set_active(False)

        self.default_rule_weight_entry.set_text(scast(self.config.get('default_rule_weight',2), str, '<<ERROR>>'))

        if self.config.get('gui_learn_queries',False): self.learn_queries_button.set_active(True)
        else: self.learn_queries_button.set_active(False)

        self.query_rule_weight_entry.set_text(scast(self.config.get('query_rule_weight',20), str, '<<ERROR>>'))
        #gui_flag_3_color

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
        
        if self.config.get('ignore_images',False): self.ignore_images_button.set_active(True)
        else: self.ignore_images_button.set_active(False)

        self.browser_entry.set_text(coalesce(self.config.get('browser',''),''))
        self.external_iv_entry.set_text(coalesce(self.config.get('image_viewer',''),''))

        self.similarity_limit_entry.set_text(scast(self.config.get('default_similarity_limit',50000),str,'<<ERROR>>'))
        self.error_threshold_entry.set_text(scast(self.config.get('error_threshold',10), str,'<<ERROR>>'))

        self.clear_cache_entry.set_text(scast(self.config.get('gui_clear_cache',30),str,'<<ERROR>>'))

        if self.config.get('ignore_modified',True): self.ignore_modified_button.set_active(True)
        else: self.ignore_modified_button.set_active(False)

        self.db_entry.set_text(scast(self.config.get('db_path',''), str, '<<ERROR>>'))
        self.log_entry.set_text(scast(self.config.get('log',''), str, '<<ERROR>>'))
        
        self.on_changed()


    def validate_entries(self, *kargs):
        matches = re.findall(FLOAT_VALIDATE_RE, self.default_entry_weight_entry.get_text())
        if matches in (None, (), [], (None,)):
            self.err_label.set_markup('<span foreground="red">Weight must be a number!</span>')
            return False
        matches = re.findall(FLOAT_VALIDATE_RE, self.default_rule_weight_entry.get_text())
        if matches in (None, (), [], (None,)):
            self.err_label.set_markup('<span foreground="red">Weight must be a number!</span>')
            return False
        matches = re.findall(FLOAT_VALIDATE_RE, self.query_rule_weight_entry.get_text())
        if matches in (None, (), [], (None,)):
            self.err_label.set_markup('<span foreground="red">Weight must be a number!</span>')
            return False
        if not self.similarity_limit_entry.get_text().isdigit():
            self.err_label.set_markup('<span foreground="red">Similarity Limit must be an integer number!</span>')
            return False
        if not self.error_threshold_entry.get_text().isdigit():
            self.err_label.set_markup('<span foreground="red">Error Threshold must be an integer number!</span>')
            return False
        if not self.clear_cache_entry.get_text().isdigit():
            self.err_label.set_markup('<span foreground="red">Cache clearing days must be an integer number!</span>')
            return False
        if not self.default_interval_entry.get_text().isdigit():
            self.err_label.set_markup('<span foreground="red">Default interval be an integer number!</span>')
            return False
        if not self.rule_limit_entry.get_text().isdigit():
            self.err_label.set_markup('<span foreground="red">Rule limit must be an integer number!</span>')
            return False

        if not os.path.isfile(self.db_entry.get_text()):
            self.err_label.set_markup('<span foreground="red">Database file not found!</span>')
            return False
        
        return True




    def get_result(self, *kargs):

        if self.learn_button.get_active(): self.result['use_keyword_learning'] = True
        else: self.result['use_keyword_learning'] = False

        self.result['rule_limit'] = nullif(self.rule_limit_entry.get_text(),'')

        if self.desktop_notify_button.get_active(): self.result['gui_desktop_notify'] = True
        else: self.result['gui_desktop_notify'] = False
        if self.fetch_in_background_button.get_active(): self.result['gui_fetch_periodically'] = True
        else: self.result['gui_fetch_periodically'] = False

        self.result['default_interval'] = nullif(self.default_interval_entry.get_text(),'')

        self.result['notify_level'] = self.notify_level_combo.get_active()+1

        self.result['default_entry_weight'] = nullif(self.default_entry_weight_entry.get_text(),'')

        if self.learn_from_added_button.get_active(): self.result['learn_from_added_entries'] = True
        else: self.result['learn_from_added_entries'] = False

        self.result['default_rule_weight'] = nullif(self.default_rule_weight_entry.get_text(),'')

        if self.learn_queries_button.get_active(): self.result['gui_learn_queries'] = True
        else: self.result['gui_learn_queries'] = False

        self.result['query_rule_weight'] = nullif(self.query_rule_weight_entry.get_text(),'')

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
        
        self.result['browser'] = nullif(self.browser_entry.get_text(),'')
        self.result['image_viewer'] = nullif(self.external_iv_entry.get_text(),'')

        self.result['default_similarity_limit'] = nullif(self.similarity_limit_entry.get_text(),'')
        self.result['error_threshold'] = nullif(self.error_threshold_entry.get_text(),'')
        self.result['gui_clear_cache'] = nullif(self.clear_cache_entry.get_text(),'')

        if self.ignore_modified_button.get_active(): self.result['ignore_modified'] = True
        else: self.result['ignore_modified'] = False

        if self.ignore_images_button.get_active(): self.result['ignore_images'] = True
        else: self.result['ignore_images'] = False

        self.result['db_path'] = nullif(self.db_entry.get_text(),'')
        self.result['log'] = nullif(self.log_entry.get_text(),'')

    def on_save(self, *kargs):
        if self.validate_entries():
            self.response = 1
            self.get_result()
            self.get_result()
            self.close()

    def on_cancel(self, *kargs):
        self.response = 0
        self.get_result()
        self.result = {}
        self.close()
