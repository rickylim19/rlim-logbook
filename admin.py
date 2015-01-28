#! /usr/bin/env python
# -*- coding: utf-8 -*-

import os
import webapp2
import jinja2

from webapp2_extras import routes
from wikiengine import wiki_handlers
from users import users_handlers
from wikiengine import guestbook

DEBUG = os.environ.get('SERVER_SOFTWARE', '').startswith('Dev')

PAGE_RE = r'(/(?:[a-zA-Z0-9-_ !?]+/?)*)'

app = webapp2.WSGIApplication([
         ('/admin/?', wiki_handlers.Home),
         ('/admin/internal/?', wiki_handlers.InternalHome),
         ('/admin/tmp/?', wiki_handlers.Tmp),
         ('/admin/_delete' + PAGE_RE, wiki_handlers.DeletePage),
         ('/admin/signup', users_handlers.Signup),
         ('/admin/addquote', wiki_handlers.AddQuote),
         ('/admin/_edit' + PAGE_RE, wiki_handlers.EditPage),
         ('/admin/_history' + PAGE_RE, wiki_handlers.HistoryPage),
         ('/admin' + PAGE_RE, wiki_handlers.WikiPage),
         ], debug=DEBUG)

