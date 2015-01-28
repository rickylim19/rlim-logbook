#! /usr/bin/env python
# -*- coding: utf-8 -*-

from google.appengine.ext import ndb
from libs.utils.markdown2 import *

class Page(ndb.Model):
    path = ndb.StringProperty(required=True)
    username = ndb.StringProperty(required=True)
    content = ndb.TextProperty(required=True)
    version = ndb.IntegerProperty(required = True)
    #blob_key = ndb.BlobKeyProperty()
    img = ndb.BlobProperty()
    img_id = ndb.StringProperty()
    created = ndb.DateTimeProperty(auto_now_add=True)
    last_modified = ndb.DateTimeProperty(auto_now=True)

    @staticmethod
    def _parent_key(path):
        return ndb.Key('/root' + path, 'wikipages')

    @classmethod
    def _by_path(cls, path):
        q = cls.query(ancestor = cls._parent_key(path))
        q = q.order(-cls.version)
        return q

    @classmethod
    def _by_id(cls, page_id, path):
        return cls.get_by_id(page_id, cls._parent_key(path))

    @classmethod
    def _by_version(cls, version, path):
        q = cls.query(ancestor = cls._parent_key(path))
        q = q.filter(cls.version == version)
        return q

    @classmethod
    def _by_img_id(cls, img_id, path):
        q = cls.query(ancestor = cls._parent_key(path))
        q = q.filter(cls.img_id == img_id)
        return q

    def _as_dict(self):
        time_fmt = '%c'
        d = {'path': self.path,
             'username': self.username,
             'content': markdown(self.content),
             'version': self.version,
             'created': self.created.strftime(time_fmt),
             'last_modified': self.created.strftime(time_fmt)}
        return d

class InternalPage(Page):

    @staticmethod
    def _parent_key(path):
        return ndb.Key('/root' + path, 'internalpages')
