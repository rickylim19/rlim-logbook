#! /usr/bin/env python
# -*- coding: utf-8 -*-

from google.appengine.api import memcache
from basehandler import basehandler

class Flush(basehandler.BaseHandler):
    def get(self):
        memcache.flush_all()
        self.redirect('/')
