# -*- coding: utf-8 -*-
""" Clipboard and window support for FEEDEX """


import gi
gi.require_version('Gtk', '3.0')
gi.require_version('Wnck', '3.0')

from gi.repository import Gtk, Gdk, Wnck

from feedex_headers import *






class Clipper:
    """ Clipboard and Window support. Gets selection and window name."""
    def __init__(self, **kargs) -> None:

        self.config = kargs.get('config', DEFAULT_CONFIG)
        self.error = None



    def process_args(self, *args):
        """ Get selections and window names and substitute them to an argument """
        cb = Gtk.Clipboard.get(Gdk.SELECTION_PRIMARY)
        selection = cb.wait_for_text()
            
        if selection in (None, ''): 
            self.error = _('Empty selection!')
            cli_msg(-1, _('Empty selection!'))

        scr = Wnck.Screen.get_default()
        scr.force_update()
        window = scr.get_active_window().get_name()
        # Exclude phrases (to avoid littering database with rowser headers etc...)...
        exclude = scast(self.config.get('window_name_exclude'), str, '')
        for excl in exclude.split(','): window = window.replace(excl,'')

        arg_list = []
        for a in args: 
            if type(a) is str: arg_list.append(self.parse_for_clipboard(a, selection, window)) 
            else: arg_list.append(None)

        return tuple(arg_list)




    def parse_for_clipboard(self, text:str, selection:str, window:str):
        """ Parse string for clipboard parameters """
        rstr = random_str(string=text)
        text = text.replace('%%', rstr)
        text = text.replace('%s', selection)
        text = text.replace('%w', window)
        text = text.replace(rstr, '%')
        return text


