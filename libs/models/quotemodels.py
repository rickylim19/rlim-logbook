#! /usr/bin/env python
# -*- coding: utf-8 -*-

from google.appengine.ext import ndb
import random
from google.appengine.api import memcache
import logging

class Quote(ndb.Model):
    """
    Datastore for quotes
    """
    quote = ndb.TextProperty(required=True)
    source = ndb.StringProperty()
    username = ndb.StringProperty(required=True)
    created = ndb.DateTimeProperty(auto_now_add=True)
    last_modified = ndb.DateTimeProperty(auto_now=True)

    MEMCACHE_TIMEOUT = 0

    @staticmethod
    def _quote_memkey(key='quote_list'):
        return str(key)

    @classmethod
    def _get_all(cls):
        key = cls._quote_memkey()
        quotes = memcache.get(key)
        if quotes is None:
            quotes = list(Quote.query().fetch(limit = None))
            memcache.set(key, quotes, cls.MEMCACHE_TIMEOUT)
            #if not memcache.set(key, quotes, cls.MEMCACHE_TIMEOUT):
                #logging.error('Memcache set failed for key %s.', key)
        else:
            logging.info('Memcache hit for key %s.', key)
        return quotes

    # Save a quote and return it
    @classmethod
    def _save(cls, **kwargs):
        quote = cls(quote = kwargs['quote'],
                    source = kwargs['source'],
                    username = kwargs['username'],
                   )
        quote.put()
        # Modify memcache for this key
        quote._add_to_memcache()
        return quote

    # Add a new element to memcache
    def _add_to_memcache(self):
        data = memcache.get(self._quote_memkey())
        if data:
            #logging.info('Adding to Memcache for key %s.', self._quote_memkey())
            data.insert(0, self)
            memcache.set(self._quote_memkey(), data, self.MEMCACHE_TIMEOUT)
            #if not memcache.set(self._quote_memkey(), data, self.MEMCACHE_TIMEOUT):
            #    logging.error('Memcache set failed for key %s.', self._quote_memkey())

    def _as_dict(self):
        time_fmt = '%c'
        d = {'quote': self.quote,
             'source': self.source,
             'username': self.username,
             'created': self.created.strftime(time_fmt),
             'last_modified': self.created.strftime(time_fmt)}
        return d
