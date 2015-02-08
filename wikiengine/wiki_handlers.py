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


# index name for search feature
_INDEX_NAME = 'wiki'
def getRecentPages(internal = False):
    """
    returns a sorted tuple of path_content
    path_content = (path, uname, last_modified, img_key, content_preview))
    sorting from the most recent last_modified (descending)

    # path: path of the wiki (wikipage directory)
    # uname: username
    # last_modified: date when wiki was recently modified
    # img_key: unique img_id to query the img in the DB

    # there two DBs that this function could get:
    # InternalPage: wikipage for internal directory (only for admins)
    # Page: wikipage for home directory (for public)
    """

    if internal:
        page_paths = InternalPage.query(projection=["path"], distinct=True)
    else:
        page_paths = Page.query(projection=["path"], distinct=True)

    list_paths = [page.path for page in page_paths]

    # a list of most recent wikipage entity
    pages = []
    for path in list_paths:
        # get the most recent from InternalPage!
        if internal:
            recent_page = InternalPage._by_path(path).get()
        else:
            recent_page = Page._by_path(path).get() #get the most recent from page!
        pages.append(recent_page)

    if pages:
        path_content = []
        for page in pages:
            if page is not None:
                (path, uname, last_modified, img_key, content) = page.path, page.username,\
                                                                 page.last_modified, page.img_id,\
                                                                 page.content
                # get the first 5 words of the content
                content_preview = ' '.join(content.split()[:5])
                path_content.append((path, uname, last_modified, img_key, content_preview))

        # sorted based on the last_modified from the most recent date
        path_content = sorted(path_content, key = lambda x:x[2], reverse = True)
    else:
        path_content = ''

    return path_content

class Home(basehandler.BaseHandler):
    """
    handles the get request for '/' or home directory
    """
    def get(self):
        quotes = Quote._get_all()
        if quotes:
            choosen_quote = random.choice(quotes)
            source = choosen_quote.source
            quote = choosen_quote.quote
        else:
            quote = "We share, because we are not alone"
            source = ""

        path_content = getRecentPages()
        self.render("home.html",
                    quote = quote, source = source,
                    pages = path_content)

class InternalHome(basehandler.BaseHandler):
    """
    handles the get and post requests for '/admin/internal'

    get request:
    - display the wikipages published for internal
    - display the search form (full-text search)

    post request:
    - handles the search query results (limit to 10)

    """
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
                    returned_fields = ['path_link'])

                query_obj = search.Query(query_string=query, options=query_options)
                results = search.Index(name=_INDEX_NAME).search(query=query_obj)
                len_results = len(results.results)

                self.render('internalhome.html', results = results,
                            len_results = len_results, query = query)

            else:
                self.redirect('/admin/internal')


class EditPage(basehandler.BaseHandler, blobstore_handlers.BlobstoreUploadHandler):
    """
    Handles the editor of the wiki
    """
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
                path_link = '/admin' + path
            else:
                path_link = path

            # create the index document for full-text search
            search.Index(name = _INDEX_NAME).put(CreateDocument(path = path,
                                                                path_link = path_link,
                                                                author = self.uname,
                                                                content = content))
            if internal:
                old_page = InternalPage._by_path(path).get()
            else:
                old_page = Page._by_path(path).get()

            img = self.request.get('img')

            # sha1 digest of the img file as img_id
            # this is unique and contains only URL characters
            img_id = ''
            if img:
                img_id = sha1(str(img)).hexdigest()
            else:
                if old_page:
                    # if the previous wikipage already contained img
                    img_id = old_page.img_id
                    img = old_page.img

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
                    self.redirect(path)
            else:
                if internal: self.redirect("/admin" + path)
                else: self.redirect(path)
        else:
            error = "content needed!"
            self.render("edit.html", path = path, error = error)

class HistoryPage(basehandler.BaseHandler):
    """
    Handles the history, to keep track of the wikipage versions
    """
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
    """
    Handles the display of wikipage
    """
    def get(self, path):
        v = self.request.get('v') # get the requested version
        p = None
        internal = self.isInternal(path)

        if v.isdigit():
            if internal:
                p = InternalPage._by_version(int(v), path).get()
            else:
                p = Page._by_version(int(v), path).get()

            if not p: return self.notfound()
            content = markdown(p.content)
            if p.img:
                img_key = p.img_id
            else: img_key = None

        else:
            if internal:
                p = InternalPage._by_path(path).get()
            else:
                p = Page._by_path(path).get()
            if p:
                if p.img:
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
                self.render("page.html", content = content,
                            path = path, img_key = img_key)
        else:
            self.redirect("/admin/_edit" + path)

class AddQuote(basehandler.BaseHandler):
    """
    Handles the addition of quotes to be displayed in the home jumbotron
    """
    def get(self):
        if self.useradmin:
            self.render("addquote.html")

    def post(self):
        if self.useradmin:
            quote = self.request.get('content')
            source = self.request.get('source')

            if quote:
                # put quote into datastore and added to memcache
                Quote._save(quote = quote,
                            source = source,
                            username = self.useradmin.nickname())
                self.redirect("/")
            else:
                error = "Add a quote please!"
                self.render("addquote.html", error=error)


class DeletePage(basehandler.BaseHandler):
    """
    Handles wikipage deletion given its path and/or version
    and delete the document index as well (given the docID which the path)
    Note: document index is used for full-text search
    """
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

            # delete the document index
            doc_index = search.Index(name = _INDEX_NAME)
            doc_index.delete(path)
            if internal: self.redirect('/admin/internal/?')
            else: self.redirect('/?')

class FrontImage(basehandler.BaseHandler):
    """
    Serve the image <src> for the thumbnail and post image (on the top)
    e.g:
    src='/img/test1?img_id=98c132370976b4e283e2d545e396ad2c2fb78da3
    """
    def get(self, path):
        internal = self.isInternal(path)
        img_id = self.request.get('img_id')

        if internal:
            page = InternalPage._by_img_id(img_id, path).get()
        else:
            page = Page._by_img_id(img_id, path).get()
        if page:
            self.response.headers['Content-Type'] = 'image/png'
            self.response.out.write(page.img)

def CreateDocument(author, path, path_link, content) :
    return search.Document(
        doc_id = path,
        fields = [search.TextField(name = 'author', value = author),
                  search.TextField(name = 'path', value = path),
                  search.TextField(name = 'path_link', value = path_link),
                  search.HtmlField(name = 'content', value = content),
                  search.DateField(name = 'date', value = datetime.now().date())])


#### API ###

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

