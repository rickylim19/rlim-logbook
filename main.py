#! /usr/bin/env python
# -*- coding: utf-8 -*-

import os
import webapp2
import jinja2

from webapp2_extras import routes
from wikiengine import wiki_handlers
from users import users_handlers
from libs.flush import flush_handlers

DEBUG = os.environ.get('SERVER_SOFTWARE', '').startswith('Dev')

#PAGE_RE = r'(/.*)'
PAGE_RE = r'(/(?:[a-zA-Z0-9]+/?)*)'
app = webapp2.WSGIApplication([
       ('/upload' + PAGE_RE, wiki_handlers.EditPage),
       ('/img' + PAGE_RE, wiki_handlers.Image),
       ('/login', users_handlers.Login),
       ('/logout', users_handlers.Logout),
       ('/flush', flush_handlers.Flush),
       ('/pages.json', wiki_handlers.PageJson),
       ('/quotes.json', wiki_handlers.QuoteJson),
       ('/?', wiki_handlers.Home),
       (PAGE_RE, wiki_handlers.WikiPage),
      ], debug=DEBUG)
