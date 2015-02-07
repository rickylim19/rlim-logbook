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
import urllib
from google.appengine.api import search


_INDEX_NAME = 'wiki'
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
                    path, uname, last_modified, img_key, content = page.path, page.username,\
                                                          page.last_modified, page.img_id,\
                                                          page.content
                else:
                    path, uname, last_modified, img_key, content = page.path, page.username,\
                                                          page.last_modified, None,\
                                                          page.content
                path_content.append((path, uname, last_modified, img_key, content))
        # sorted based on the last_modified from the most recent date
        path_content = sorted(path_content, key = lambda x:x[2], reverse = True)
    else:
        path_content = ''


    return path_content




class Home(basehandler.BaseHandler):
    def get(self):
        quote, source = self.getRandomQuote()
        path_content = getRecentPages()


        self.render("home.html",
                    quote = quote, source = source,
                    pages = path_content)

class InternalHome(basehandler.BaseHandler):
    def get(self):
        if self.useradmin:
            path_content = getRecentPages(internal = True)

            self.render("internalhome.html",
                            pages = path_content)

    def post(self):
        if self.useradmin:

            # for searching
            query = self.request.get('search').strip()
            if query:
                # sort results by date descending
                expr_list = [search.SortExpression(
                    expression='date', default_value=datetime(1999, 01, 01),
                    direction=search.SortExpression.DESCENDING)]
                # construct the sort options
                sort_opts = search.SortOptions(
                    expressions=expr_list)
                query_options = search.QueryOptions(
                    limit = 10,
                    snippeted_fields=['content'],
                    sort_options=sort_opts,
                    returned_fields = ['path'])

                query_obj = search.Query(query_string=query, options=query_options)
                results = search.Index(name=_INDEX_NAME).search(query=query_obj)
                len_results = len(results.results)

                self.render('internalhome.html', results = results,
                            len_results = len_results)

            else:
                self.redirect('/admin/internal')


class EditPage(basehandler.BaseHandler, blobstore_handlers.BlobstoreUploadHandler):
    def get(self, path):

        internal = self.isInternal(path)
        if self.useradmin:
            v = self.request.get('v')
            p = None
            if v:
                if v.isdigit():
                    if internal:
                        p = InternalPage._by_version(int(v), path).get()
                    else:
                        p = Page._by_version(int(v), path).get()

                if not p:
                    return self.notfound()
            
            else:
                if internal:
                    p = InternalPage._by_path(path).get()

                else:
                    p = Page._by_path(path).get()

            self.render("edit.html", path = path , page = p)

    def post(self, path):

        if not self.useradmin:
            self.error(400)
            return 

        content = self.request.get('content')
        internal = self.isInternal(path)

        if path and content:
            if internal:
                path_index = '/admin' + path
            else:
                path_index = path
            search.Index(name = _INDEX_NAME).put(CreateDocument(author = self.uname,
                                                                path = path_index,
                                                                content = content))
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
                old_page.img = str(img)
                old_page.img_id = img_id
                old_page.put()
                update = False
            elif old_page.content != content:
                version  = old_page.version + 1
                old_page.img = str(img)
                old_page.img_id = img_id
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

                    # add the index
                    self.redirect(path)
            else:
                if internal: self.redirect("/admin" + path)
                else: self.redirect(path)
        else:
            error = "content needed!"
            self.render("edit.html", path = path, error = error)

class HistoryPage(basehandler.BaseHandler):
    def get(self, path):
        internal = self.isInternal(path)
        if internal:
            q = InternalPage._by_path(path)
        else:
            q = Page._by_path(path)

        posts = q.fetch(limit = None)

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
        internal = self.isInternal(path)

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
                self.render("internalpage.html", content = content,
                            path = path, img_key = img_key)
            else:
                self.render("page.html", content = content, path = path,
                            img_key = img_key)
        else:
            self.redirect("/admin/_edit" + path)

class AddQuote(basehandler.BaseHandler):
    def get(self):
        if self.useradmin:
            self.render("addquote.html")

    def post(self):
        if self.useradmin:
            quote = self.request.get('content')
            source = self.request.get('source')

            if quote:
                q = Quote(parent = Quote._parent_key(),
                          quote=quote, source=source, 
                          username=self.useradmin.nickname())
                q.put()
                self.redirect("/")
            else:
                logging.error('No Content')
                error = "Add a quote please!"
                self.render("addquote.html", error=error)


class DeletePage(basehandler.BaseHandler):
    def get(self, path):
        v = self.request.get('v')
        internal = self.isInternal(path)


        if not self.useradmin and not v:
            self.error(400)
            return

        if self.useradmin and v.isdigit():
            if internal:
                key_ = InternalPage.query(InternalPage.path == path,
                                          InternalPage.version == int(v)).\
                                          fetch(keys_only = True)
            else:
                key_ = Page.query(Page.path == path, Page.version == int(v)).\
                                          fetch(keys_only = True)
            ndb.delete_multi(key_)
            self.redirect('/admin/_history' + path)

        if self.useradmin and not v:
            if internal: keys_ = InternalPage.query().filter(InternalPage.path == path).\
                                          fetch(keys_only = True)
            else: keys_ = Page.query().filter(Page.path == path).fetch(keys_only = True)
            ndb.delete_multi(keys_)
            self.redirect('/?')

class FrontImage(basehandler.BaseHandler):
    """
    Serve the image <src> for the thumbnail and post image (on the top)
    """
    def get(self, path):
        internal = self.isInternal(path)
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

def CreateDocument(author, path, content) :
    return search.Document(
        doc_id = path,
        fields = [search.TextField(name = 'author', value = author),
                  search.TextField(name = 'path', value = path),
                  search.HtmlField(name = 'content', value = content),
                  search.DateField(name = 'date', value = datetime.now().date())])
