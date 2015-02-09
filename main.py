#! /usr/bin/env python
# -*- coding: utf-8 -*-

import os
import webapp2
import jinja2

from webapp2_extras import routes
from wikiengine import wiki_handlers
from users import users_handlers
from libs.flush import flush_handlers
from basehandler import basehandler

DEBUG = os.environ.get('SERVER_SOFTWARE', '').startswith('Dev')

PAGE_RE = r'(/(?:[a-zA-Z0-9-_]+/?)*)'
app = webapp2.WSGIApplication([
       ('/upload' + PAGE_RE, wiki_handlers.EditPage),
       ('/img' + PAGE_RE, wiki_handlers.FrontImage),
       ('/login', users_handlers.Login),
       ('/logout', users_handlers.Logout),
       ('/flush', flush_handlers.Flush),
       ('/pages.json', wiki_handlers.PageJson),
       ('/quotes.json', wiki_handlers.QuoteJson),
       ('/?', wiki_handlers.Home),
       (PAGE_RE, wiki_handlers.WikiPage),
       ('/.*', basehandler.NotFound),
      ], debug=DEBUG)
