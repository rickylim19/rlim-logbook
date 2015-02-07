#! /usr/bin/env python
# -*- coding: utf-8 -*-

from google.appengine.ext import ndb
import random

class Quote(ndb.Model):
    quote = ndb.TextProperty(required=True)
    source = ndb.StringProperty()
    username = ndb.StringProperty(required=True)
    created = ndb.DateTimeProperty(auto_now_add=True)
    last_modified = ndb.DateTimeProperty(auto_now=True)

    @staticmethod
    def _parent_key(name="default"):
        return ndb.Key('quotes', name)

    def as_dict(self):
        time_fmt = '%c'
        d = {'quote': self.quote,
             'source': self.source,
             'username': self.username,
             'created': self.created.strftime(time_fmt),
             'last_modified': self.created.strftime(time_fmt)}
        return d

