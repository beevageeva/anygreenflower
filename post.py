import cgi
import os
import urllib
import json, hashlib

from google.appengine.ext import ndb

import webapp2,jinja2
import captcha


from google.appengine.ext.webapp import blobstore_handlers
from google.appengine.ext import blobstore

from base_handler import *
from forms import validateForm, minLength, lengthBetween 

from auth import login_required, admin_required

from user import UserModel
from math import ceil



FIELD_COND={'content': lengthBetween(4,500)}


class PostModel(ndb.Model):
	parent = ndb.KeyProperty('PostModel')
	content = ndb.TextProperty(indexed=True)
	creationdate = ndb.DateTimeProperty(auto_now_add=True)
	username = ndb.KeyProperty(UserModel)


	


class NewHandler(BaseHandler):
	
	@login_required
	def post(self):
		validation = validateForm(self.request.POST, FIELD_COND)
		if(not validation[0]):
			posts = PostModel.query(PostModel.parent == None).fetch()
			recursive_add(posts)
			template_values = {"posts": posts, "errors" : validation[1], "session": self.session}
			template = JINJA_ENVIRONMENT.get_template('/post/list.html')
			self.response.write(template.render(template_values))
		else:				
			post = PostModel(content=self.request.get('content'), username = ndb.Key('UserModel', self.session['username']))
			if(not self.request.get("parent_key") or self.request.get("parent_key")	== "NONE"):
				post.parent = None
			else:
				post.parent =ndb.Key(urlsafe=self.request.get("parent_key"))
			post.put()
			self.redirect('/')

	
def recursive_add(posts):
	for p in posts:
			#print "posts" 
			#print posts 
			#print "post content %s index %d"%(p.content, posts.index(p))
			toadd = PostModel.query(PostModel.parent == p.key).fetch()
			if(len(toadd)>0):
				posts[posts.index(p)+1:0] = toadd 
			print "post2" 
			print posts 


class ListHandler(BaseHandler):

	ITEMS_PAGE=5	


	@login_required
	def post(self):
		print "POST METHOD"
		template_values = {"session": self.session}
		page = 0
		sc=self.request.get("searchContent")
		if not sc and self.request.get("page"):
			page = int(self.request.get("page"))
		query = ndb.Query(kind = 'PostModel' , default_options=ndb.QueryOptions(offset= page * ListHandler.ITEMS_PAGE))
		queryCount = PostModel.query()
		if not sc:
			query = query.filter(PostModel.parent == None)
			queryCount = queryCount.filter(PostModel.parent == None)
		else:
			template_values['searchContent'] = sc
			query=query.filter(PostModel.content >= sc).filter(PostModel.content < sc + u'\ufffd') 
			query = query.order(PostModel.content)
			queryCount=queryCount.filter(PostModel.content >= sc).filter(PostModel.content < sc + u'\ufffd') 
		count = queryCount.count()
		numPages = int(ceil(float(count) / ListHandler.ITEMS_PAGE))
		query = query.order(-PostModel.creationdate)
		posts = query.fetch(ListHandler.ITEMS_PAGE)
		if sc:
			newposts = []
			for p in posts:
				while p.parent:
					p = p.parent.get()
				if not p in newposts:
					newposts.append(p)
			posts = newposts
				
		recursive_add(posts)
		template_values['posts'] = posts
		template_values['page'] = page
		template_values['numPages'] = numPages

		template = JINJA_ENVIRONMENT.get_template('post/list.html')
		self.response.write(template.render(template_values))

	

	@login_required
	def get(self):
		#print "GET METHOD"
		query = PostModel.query(PostModel.parent == None)
		count = query.count()
		print("count in get is %d"%count)
		numPages = int(ceil(float(count) / ListHandler.ITEMS_PAGE))
		query = query.order(-PostModel.creationdate)
		posts = query.fetch(ListHandler.ITEMS_PAGE)
		recursive_add(posts)
		template_values = {"session": self.session}
		template_values['posts'] = posts
		template_values['page'] = 0
		template_values['numPages'] = numPages
		template = JINJA_ENVIRONMENT.get_template('post/list.html')
		self.response.write(template.render(template_values))


class EditHandler(BaseHandler):

	@login_required
	def post(self):
		key= ndb.Key(urlsafe=self.request.get("key"))
		post = key.get()
		if self.session['usertype']=='Admin' or post.username.id() == self.session['username']: 
			validation = validateForm(self.request.POST, FIELD_COND)
			if(not validation[0]):
				posts = PostModel.query(PostModel.parent == None).fetch()
				recursive_add(posts)
				template_values = {"posts": posts, "errors" : validation[1], "session": self.session}
				template = JINJA_ENVIRONMENT.get_template('/post/list.html')
				self.response.write(template.render(template_values))
			else:				
				post.content = self.request.get('content')
				post.put()
			self.redirect('/')




class DeleteHandler(BaseHandler):
	@login_required
	def post(self):
		key= ndb.Key(urlsafe=self.request.get("key"))
		post = key.get()
		if self.session['usertype']=='Admin' or post.username.id() == self.session['username']: 
			for p in PostModel.query(PostModel.parent==key).fetch():
				p.parent = None
				p.put()
			key.delete()
		self.redirect('/')


class DeleteAllHandler(BaseHandler):
	@admin_required
	def get(self):
		ndb.delete_multi(PostModel.query().fetch(keys_only=True))
		self.redirect('/')


application = webapp2.WSGIApplication([
    ('/post/list', ListHandler),
    ('/post/new', NewHandler),
    ('/post/edit', EditHandler),
    ('/post/delete', DeleteHandler),
    ('/post/deleteAll', DeleteAllHandler),
], debug=True, config=session_config)
