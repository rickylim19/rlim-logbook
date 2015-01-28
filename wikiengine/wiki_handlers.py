#! /usr/bin/env python
# -*- coding: utf-8 -*-
from hashlib import sha1
from basehandler import basehandler
from libs.models.pagemodels import *
from libs.models.quotemodels import *
from libs.utils.utils import *
import logging
import urllib
from google.appengine.api import memcache
from google.appengine.api import users
from datetime import datetime, timedelta
import time
from libs.utils.markdown2 import *
import random
from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers
from hashlib import sha1
from google.appengine.api.images import get_serving_url
from google.appengine.ext.blobstore import BlobKey

def getRandomQuote():
    quotes = Quote.query().fetch(limit = None)
    if quotes:
        choosen_quote = random.choice(quotes)
        source = choosen_quote.source
        quote = choosen_quote.quote
    else:
        quote = "We share, because we are not alone"
        source = ""
    return (quote, source)

def getRecentPages(internal = False):

    if internal:
        page_paths = InternalPage.query(projection=["path"], distinct=True)
    else:
        page_paths = Page.query(projection=["path"], distinct=True)

    list_paths = [page.path for page in page_paths]

    pages = []
    for path in list_paths:
        if internal: recent_page = InternalPage._by_path(path).get() #get the most recent!
        else: recent_page = Page._by_path(path).get() #get the most recent!
        pages.append(recent_page)


    if pages:
        path_content = []
        for page in pages:
            if page is not None:
                if page.img:
                    path, last_modified, img_key = page.path, page.last_modified, page.img_id
                else:
                    path, last_modified, img_key = page.path, page.last_modified, None

                path_content.append((path, last_modified, img_key))
        path_content = sorted(path_content, key = lambda x:x[1], reverse = True)
    else:
        path_content = ''


    return path_content

def checkInternal(path):
    """
    returns True if path == '/admin/internal'
    """
    dir_name = os.path.dirname(path)
    if dir_name == '/internal':
        return True
    else: return False



class Home(basehandler.BaseHandler):
    def get(self):

        quote, source = getRandomQuote()
        path_content = getRecentPages()

        self.render("home.html",
                    quote = quote, source = source,
                    pages = path_content)

class InternalHome(basehandler.BaseHandler):
    def get(self):
        if self.useradmin:
            path_content = getRecentPages(internal = True)
            logging.error(path_content)
            self.render("internalhome.html",
                        pages = path_content)

class EditPage(basehandler.BaseHandler, blobstore_handlers.BlobstoreUploadHandler):
    def get(self, path):


        internal = checkInternal(path)
        if self.useradmin:
            #upload_url = blobstore.create_upload_url('/upload' + path )
            v = self.request.get('v')
            p = None
            if v:
                #logging.error('version: ' + v)
                if v.isdigit():
                    #logging.error("hit DB query")

                    if internal:
                        p = InternalPage._by_version(int(v), path).get()
                    else:
                        p = Page._by_version(int(v), path).get()

                if not p:
                    return self.notfound()
            
            else:
                if internal:
                    #logging.error('internal model accessed')
                    p = InternalPage._by_path(path).get()

                else:
                    p = Page._by_path(path).get()

            self.render("edit.html", path = path , page = p)

    def post(self, path):

        if not self.useradmin:
            self.error(400)
            return 

        content = self.request.get('content')
        internal = checkInternal(path)



        if path and content:
            if internal:
                old_page = InternalPage._by_path(path).get()
            else:
                old_page = Page._by_path(path).get()

            if old_page:
                img = old_page.img
                if img == '':
                    img = self.request.get('img')
            else:
                img = self.request.get('img')

            img_id = sha1(str(img)).hexdigest()



            update = False
            if not old_page:
                version = 1 # initialize the page with version 1
                update = True
            elif old_page.content == content:
                version = old_page.version
                old_page.img = img
                old_page.img_id = img_id
                old_page.put()
                update = False
            elif old_page.content != content:
                version  = old_page.version + 1
                old_page.img = img
                old.page.img_id = img_id
                update = True

            if update:
                if internal:
                    internal_p = InternalPage(parent = InternalPage._parent_key(path),
                                              username = self.uname,
                                              path = path,
                                              content = content,
                                              version = version,
                                              img = str(img),
                                              img_id = img_id
                                              )

                    internal_p.put()
                    self.redirect("/admin" + path)
                else:
                    p = Page(parent = Page._parent_key(path),
                             username = self.uname,
                             path = path,
                             content = content,
                             version = version,
                             img = str(img),
                             img_id = img_id
                             )
                    p.put()
                    self.redirect(path)
            else:
                if internal: self.redirect("/admin" + path)
                else: self.redirect(path)
        else:
            error = "content needed!"
            self.render("edit.html", path = path, error = error)

class HistoryPage(basehandler.BaseHandler):
    def get(self, path):
        internal = checkInternal(path)
        if internal:
            q = InternalPage._by_path(path)
        else:
            q = Page._by_path(path)

        posts = q.fetch(limit = None)

        #posts = list(q)
        if posts:
            self.render("history.html", path=path, posts=posts)
        else:
            if internal:
                self.redirect("/admin/internal/_edit" + path)
            else:
                self.redirect("/admin/_edit" + path)


class WikiPage(basehandler.BaseHandler):
    def get(self, path):
        v = self.request.get('v') # get the requested version
        p = None
        internal = checkInternal(path)

        if v:
            if v.isdigit():
                if internal:
                    page = InternalPage._by_version(int(v), path)
                    p = page.get()
                else:
                    page = Page._by_version(int(v), path)
                    p = page.get()

                if not p: return self.notfound()
                content = markdown(p.content)
                if p.img:
                    #img_key = p.key.urlsafe()
                    img_key = p.img_id
                else: img_key = None

        else:
            if internal:
                page = InternalPage._by_path(path)
                p = page.get()
            else:
                page = Page._by_path(path)
                p = page.get()
            if p:
                if p.img:
                    #img_key = p.key.urlsafe()
                    img_key = p.img_id
                else: img_key = None
                content = markdown(p.content)
            else:
                content = p

        if p:
            if internal:
                self.render("internalpage.html", content = content, path = path, img_key = img_key)
            else:
                self.render("page.html", content = content, path = path, img_key = img_key)
        else:
            self.redirect("/admin/_edit" + path)

class InternalWikiPage(basehandler.BaseHandler):
    def get(self, path):
        path = '/internal'+ path
        if self.user or self.isadmin:  
            v = self.request.get('v') # get the requested version
            p = None
            if v:
                if v.isdigit():
                    logging.error("version:"+ v)
                    p = InternalPage._by_version(int(v), path).get()
                    content = markdown(p.content)
                if not p:
                    return self.notfound()
            else:
                p = InternalPage._by_path(path).get()
                if p:
                    content = markdown(p.content)
                else:
                    content = p

            if p:
                self.render("internalpage.html", content=content,
                             path=path)
            else:
                self.redirect("/admin/_edit" + path)
        else:
            self.redirect("/login")

class AddQuote(basehandler.BaseHandler):
    def get(self):
        if self.useradmin:
            self.render("addquote.html")

    def post(self):
        if self.useradmin:
            quote = self.request.get('content')
            source = self.request.get('source')

            if quote:
                q = Quote(parent=quote_key(), 
                          quote=quote, source=source, 
                          username=self.useradmin.nickname())
                q.put()
                time.sleep(1)
                front_pages(update=True)
                self.redirect("/")
            else:
                logging.error('No Content')
                error = "Add a quote please!"
                self.render("addquote.html", error=error)

class PageJson(basehandler.BaseHandler):
    def get(self):
        pages, quotes, age = front_pages()
        pages_json = [p._as_dict() for p in pages]
        return self.render_json(pages_json)

class InternalPageJson(basehandler.BaseHandler):
    def get(self):
        if self.user or self.isadmin:
            pages, age = internal_pages()
            pages_json = [p._as_dict() for p in pages]
            return self.render_json(pages_json)
        else:
            self.redirect('/login')

class QuoteJson(basehandler.BaseHandler):
    def get(self):
        pages, quotes, age = front_pages()
        quotes_json= [q._as_dict() for q in quotes]
        return self.render_json(quotes_json)

class DeletePage(basehandler.BaseHandler):
    def get(self, path):
        v = self.request.get('v')
        internal = checkInternal(path)


        if not self.useradmin and not v:
            self.error(400)
            return

        if self.useradmin and v.isdigit():
            if internal:
                key_ = InternalPage.query(InternalPage.path == path, InternalPage.version == int(v)).fetch(keys_only = True)
            else:
                key_ = Page.query(Page.path == path, Page.version == int(v)).fetch(keys_only = True)
            ndb.delete_multi(key_)
            self.redirect('/admin/_history' + path)

        if self.useradmin and not v:
            if internal: keys_ = InternalPage.query().filter(InternalPage.path == path).fetch(keys_only = True)
            else: keys_ = Page.query().filter(Page.path == path).fetch(keys_only = True)
            ndb.delete_multi(keys_)
            self.redirect('/?')

class Image(basehandler.BaseHandler):
    def get(self, path):
        internal = checkInternal(path)
        img_id = self.request.get('img_id')
        logging.error(img_id)

        if internal:
            page = InternalPage._by_img_id(img_id, path).get()
        else:
            page = Page._by_img_id(img_id, path).get()
        #img_key = ndb.Key(urlsafe = self.request.get('img_id'))
        #page = img_key.get()
        logging.error(page)
        if page:
            self.response.headers['Content-Type'] = 'image/png'
            self.response.out.write(page.img)
        else:
            self.response.out.write('No image')
