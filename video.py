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



FIELD_COND={'content': lengthBetween(4,500), 'name': lengthBetween(4,50),}


class VideoModel(ndb.Model):
	videoBlobKey = ndb.BlobKeyProperty(indexed=True) #indexed as I want to look for orpaned blobs so this will be in a query filter
	content = ndb.TextProperty(indexed=True)
	name = ndb.StringProperty()
	creationdate = ndb.DateTimeProperty(auto_now_add=True)
	username = ndb.KeyProperty(UserModel)


class UploadVideoHandler(BaseHandler, blobstore_handlers.BlobstoreUploadHandler):
  def get(self, key):
		template_values = {'upload_url': blobstore.create_upload_url('/video/upload_video'), 'key': key, 'session':self.session}
		template = JINJA_ENVIRONMENT.get_template('video/upload_video.html')
		self.response.write(template.render(template_values))


  def post(self):
		key= ndb.Key(urlsafe=self.request.get("key"))
		video = key.get()
		upload_files = self.get_uploads('file')  # 'file' is file upload field in the form
		blob_info = upload_files[0]
		video.videoBlobKey = blob_info.key();
		video.put()
		#print "video blob key : "
		#print video.videoBlobKey
		self.redirect('/video/view/%s' % self.request.get("key") )
	


class NewHandler(BaseHandler):
	@login_required
	def get(self):
		template_values = {"session": self.session}
		template = JINJA_ENVIRONMENT.get_template('video/new.html')
		self.response.write(template.render(template_values))
	
	@login_required
	def post(self):
		validation = validateForm(self.request.POST, FIELD_COND)
		if(not validation[0]):
			template_values = {"errors" : validation[1], "session": self.session}
			template = JINJA_ENVIRONMENT.get_template('/video/new.html')
			self.response.write(template.render(template_values))
		else:				
			video = VideoModel(content=self.request.get('content'), name=self.request.get("name"), username = ndb.Key('UserModel', self.session['username']))
			video.put()
			self.redirect('/video/upload_video/%s' % video.key.urlsafe())

	

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
		query = ndb.Query(kind = 'VideoModel' , default_options=ndb.QueryOptions(offset= page * ListHandler.ITEMS_PAGE))
		queryCount = VideoModel.query()
		if sc:
			template_values['searchContent'] = sc
			query=query.filter(VideoModel.content >= sc).filter(VideoModel.content < sc + u'\ufffd') 
			query = query.order(VideoModel.content)
			queryCount=queryCount.filter(VideoModel.content >= sc).filter(VideoModel.content < sc + u'\ufffd') 
		count = queryCount.count()
		numPages = int(ceil(float(count) / ListHandler.ITEMS_PAGE))
		query = query.order(-VideoModel.creationdate)
		videos = query.fetch(ListHandler.ITEMS_PAGE)
		template_values['videos'] = videos
		template_values['page'] = page
		template_values['numPages'] = numPages

		template = JINJA_ENVIRONMENT.get_template('video/list.html')
		self.response.write(template.render(template_values))

	

	@login_required
	def get(self):
		#print "GET METHOD"
		query = VideoModel.query()
		count = query.count()
		print("count in get is %d"%count)
		numPages = int(ceil(float(count) / ListHandler.ITEMS_PAGE))
		query = query.order(-VideoModel.creationdate)
		videos = query.fetch(ListHandler.ITEMS_PAGE)
		template_values = {"session": self.session}
		template_values['videos'] = videos
		template_values['page'] = 0
		template_values['numPages'] = numPages
		template = JINJA_ENVIRONMENT.get_template('video/list.html')
		self.response.write(template.render(template_values))


class EditHandler(BaseHandler):

	@login_required
	def get(self, keyString):
		key= ndb.Key(urlsafe=keyString)
		video = key.get()
		if self.session['usertype']=='Admin' or video.username.id() == self.session['username']: 
			#print("---------------Blob key in get edit")
			#print(video.videoBlobKey)
			#print("-----------Blob key in get edit END")
			template_values = {'video': video, 'session':self.session}
			template = JINJA_ENVIRONMENT.get_template('video/edit.html')
			self.response.write(template.render(template_values))
		else:
			self.redirect('/')
			

	@login_required
	def post(self):
		key= ndb.Key(urlsafe=self.request.get("key"))
		video = key.get()
		if self.session['usertype']=='Admin' or video.username.id() == self.session['username']: 
			validation = validateForm(self.request.POST, FIELD_COND)
			if(not validation[0]):
				template_values = {"video": video, "errors" : validation[1], "session": self.session}
				template = JINJA_ENVIRONMENT.get_template('/video/edit.html')
				self.response.write(template.render(template_values))
			else:				
				video.content = self.request.get('content')
				video.name = self.request.get('name')
				video.put()
			self.redirect('/')




class DeleteHandler(BaseHandler):
	@login_required
	def post(self):
		key= ndb.Key(urlsafe=self.request.get("key"))
		video = key.get()
		if self.session['usertype']=='Admin' or video.username.id() == self.session['username']: 
			key.delete()
		self.redirect('/')


class DeleteAllHandler(BaseHandler):
	@admin_required
	def get(self):
		ndb.delete_multi(VideoModel.query().fetch(keys_only=True))
		self.redirect('/')

class ViewHandler(BaseHandler):
	@login_required
	def get(self,keyString):
		key= ndb.Key(urlsafe=keyString)
		video = key.get()
		template_values = {'video': video, 'session':self.session}
		template = JINJA_ENVIRONMENT.get_template('video/view.html')
		self.response.write(template.render(template_values))

application = webapp2.WSGIApplication([
    ('/video/list', ListHandler),
    ('/video/new', NewHandler),
    ('/video/view/(.+)', ViewHandler),
    ('/video/edit', EditHandler),
    ('/video/edit/(.+)', EditHandler),
    ('/video/delete', DeleteHandler),
    ('/video/deleteAll', DeleteAllHandler),
    ('/video/upload_video/(.+)', UploadVideoHandler),
    ('/video/upload_video', UploadVideoHandler),
], debug=True, config=session_config)
