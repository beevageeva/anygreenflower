import cgi
import os
import urllib
import json, hashlib

from google.appengine.ext import ndb

import webapp2,jinja2


from google.appengine.ext.webapp import blobstore_handlers
from google.appengine.ext import blobstore

from base_handler import *
from forms import validateForm, minLength, floatField 

from auth import login_required, admin_required

from category import CategoryModel




FIELD_COND={'description': minLength(4),'name': minLength(4), 'units': minLength(2), 'price': floatField() }


class ProductModel(ndb.Model):
	name = ndb.StringProperty(indexed=True)
	description = ndb.TextProperty()
	units = ndb.StringProperty()
	price = ndb.FloatProperty(indexed=True)
	visible = ndb.BooleanProperty(indexed=True)
	imgBlobKey = ndb.BlobKeyProperty(indexed=True) #indexed as I want to look for orpaned blobs so this will be in a query filter
	#I can also define in CategoryModel products as KeyProperty repeated=True	
	category=ndb.KeyProperty(CategoryModel)


	@classmethod
	def _post_delete_hook(cls, key, future):
		#delete items from order and product_group
		pass

	


class NewHandler(BaseHandler):
	@admin_required
	def get(self, category_key):
		template_values = {"session": self.session, "category_key": category_key}
		template = JINJA_ENVIRONMENT.get_template('product/new.html')
		self.response.write(template.render(template_values))
	
	@admin_required
	def post(self):
		validation = validateForm(self.request.POST, FIELD_COND)
		if(not validation[0]):
			template_values = {"category_key": self.request.get('category_key'), "errors" : validation[1], "session": self.session}
			template = JINJA_ENVIRONMENT.get_template('/product/new.html')
			self.response.write(template.render(template_values))
		else:				
			product = ProductModel(name=self.request.get('name'), description=self.request.get('description'), 
								units = self.request.get('units'), price = float(self.request.get('price')))
			product.category =ndb.Key(urlsafe=self.request.get("category_key"))
			product.visible = (self.request.get('visible') and self.request.get('visible')=="True")
			product.put()
			self.redirect('/')

	


class ListHandler(BaseHandler):
	@admin_required
	def get(self):
		products = ProductModel.query().fetch()
		template_values = {'products': products , "session": self.session}
		template = JINJA_ENVIRONMENT.get_template('product/list.html')
		self.response.write(template.render(template_values))

	

class ViewHandler(BaseHandler):
	@login_required
	def get(self,keyString):
		key= ndb.Key(urlsafe=keyString)
		product = key.get()
		template_values = {'product': product, 'session':self.session}
		template = JINJA_ENVIRONMENT.get_template('product/view.html')
		self.response.write(template.render(template_values))


class EditHandler(BaseHandler):
	@admin_required
	def get(self, keyString):
		key= ndb.Key(urlsafe=keyString)
		product = key.get()
		print("---------------Blob key in get edit")
		print(product.imgBlobKey)
		print("-----------Blob key in get edit END")
		template_values = {'product': product, 'session':self.session, 'categories': CategoryModel.query().fetch()}
		template = JINJA_ENVIRONMENT.get_template('product/edit.html')
		self.response.write(template.render(template_values))

	@admin_required
	def post(self):
		key= ndb.Key(urlsafe=self.request.get("key"))
		product = key.get()
		validation = validateForm(self.request.POST, FIELD_COND)
		if(not validation[0]):
			template_values = {"product": product, "errors" : validation[1], "session": self.session, 'categories': CategoryModel.query().fetch()}
			template = JINJA_ENVIRONMENT.get_template('/product/edit.html')
			self.response.write(template.render(template_values))
		else:				
			product.name = self.request.get('name')
			product.description = self.request.get('description')
			product.units = self.request.get('units')
			product.category = ndb.Key(urlsafe=self.request.get('category'))
			product.price = float(self.request.get('price'))
			product.visible = (self.request.get('visible') and self.request.get('visible')=="True")
			product.put()
			self.redirect('/')


class UploadImageHandler(BaseHandler, blobstore_handlers.BlobstoreUploadHandler):
  def get(self, key):
		template_values = {'upload_url': blobstore.create_upload_url('/product/upload_image'), 'key': key, 'session':self.session}
		template = JINJA_ENVIRONMENT.get_template('product/upload_image.html')
		self.response.write(template.render(template_values))


  def post(self):
		key= ndb.Key(urlsafe=self.request.get("key"))
		product = key.get()
		upload_files = self.get_uploads('file')  # 'file' is file upload field in the form
		blob_info = upload_files[0]
		product.imgBlobKey = blob_info.key();
		product.put()
		self.redirect('/product/view/%s' % self.request.get("key") )


class DeleteHandler(BaseHandler):
	@admin_required
	def post(self):
		key= ndb.Key(urlsafe=self.request.get("key"))
		key.delete()
		self.redirect('/')


class DeleteAllHandler(BaseHandler):
	@admin_required
	def get(self):
		ndb.delete_multi(ProductModel.query().fetch(keys_only=True))
		self.redirect('/')


application = webapp2.WSGIApplication([
    ('/product/list', ListHandler),
    ('/product/new/(.+)', NewHandler),
    ('/product/new', NewHandler),
    ('/product/upload_image/(.+)', UploadImageHandler),
    ('/product/upload_image', UploadImageHandler),
    ('/product/view/(.+)', ViewHandler),
    ('/product/edit/(.+)', EditHandler),
    ('/product/edit', EditHandler),
    ('/product/delete', DeleteHandler),
    ('/product/deleteAll', DeleteAllHandler),
], debug=True, config=session_config)
