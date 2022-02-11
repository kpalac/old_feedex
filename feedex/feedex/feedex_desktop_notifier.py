# -*- coding: utf-8 -*-
""" Desktop notifier classes for FEEDEX """


import gi
gi.require_version('Notify', '0.7')
from gi.repository import Notify


from feedex_headers import *







class DesktopNotifier:
    """ Desktop notification handler for FEEDEX. Displays notifications given a result list """
    def __init__(self, **kargs):
        Notify.init("Feedex")
        self.entry = SQLContainer('entries', RESULTS_SQL_TABLE + ('sim','cnt','rank',))
        self.notif_list = []
        self.parent = kargs.get('parent')
        self.icons = kargs.get('icons',{})


    def show(self):
        """ Show all queued notifications """
        for n in self.notif_list:
            time.sleep(0.1)
            n.show()

    
    def notify_level_one(self, feed:list):
        """ Setup notofications for notify-level 1 (summary, grouped by channels)"""
        if len(feed) == 0:
            return -1
        feed_header = scast(feed[0], str, '<<unknown>>')
        e_all = scast(feed[1], str, '<<error>>')
        e_flagged = scast(feed[2], str, '<<error>>')
        feed_id = scast(feed[3], int, 0)

        if scast(e_flagged, int, 0) > 0:
            feed_header = f'! {feed_header}'

        n = Notify.Notification.new(feed_header, f'All: {e_all}, Flagged: {e_flagged}', icon=self.icons.get(feed_id))

        n.set_timeout(0)
        if scast(e_flagged, int, 0) > 0:
            n.set_urgency(2)
        else:
            n.set_urgency(1)

        self.notif_list.append(n)
        




    def notify_level_two(self, entry:list):
        """ Setup notificatins for levels 2,3 (result list) """
        self.entry.clear()
        self.entry.populate(entry)

        if scast(self.entry['flag'], int, 0) > 0:
            title = f"! {self.entry['feed_name']}"
        else:
            title = f"{self.entry['feed_name']}"
    
        n = Notify.Notification.new(title, f"{self.entry['title']}", icon=self.icons.get(self.entry['feed_id']))
        n.set_timeout(0)

        if scast(self.entry['flag'], int, 0) > 0:
            n.set_urgency(2)
        else:
            n.set_urgency(1)

        self.notif_list.append(n)


    def clear(self):
        self.notif_list = []


    def load(self, ilist:list, level:int, **kargs):
        """ Load result lists to use """
        
        total_number = kargs.get('total_number', 0)
        
        if level == 1:
            for f in ilist:
                self.notify_level_one(f)

        elif level in (2,3):
            for e in ilist:
                self.notify_level_two(e)


        elif total_number > 0:
            if total_number > level:
                for f in ilist:
                    self.notify_level_one(f)
            else:
                for e in ilist:
                    self.notify_level_two(e)







