import cgi
import os
import urllib
import json, hashlib

from google.appengine.api import users
from google.appengine.ext import ndb


import webapp2,jinja2


from base_handler import *
from forms import validateForm, minLength, regExpMatch 

from auth import login_required, admin_required




FIELD_COND={'description': minLength(4),'name': minLength(4) }


class CategoryModel(ndb.Model):
	name = ndb.StringProperty(indexed=True)
	description = ndb.StringProperty(indexed=True)

	def get_products(self):
		from product import ProductModel
		return ProductModel.query(ProductModel.category == self.key).fetch()

	def get_products_visible(self):
		from product import ProductModel
		return ProductModel.query(ProductModel.category == self.key, ProductModel.visible == True).fetch()


class NewHandler(BaseHandler):


	@admin_required
	def get(self):
		template_values = {"session": self.session}
		template = JINJA_ENVIRONMENT.get_template('category/new.html')
		self.response.write(template.render(template_values))
	
	@admin_required
	def post(self):
		validation = validateForm(self.request.POST, FIELD_COND)
		if(not validation[0]):
			template_values = {"errors" : validation[1], "session": self.session}
			template = JINJA_ENVIRONMENT.get_template('/category/new.html')
			self.response.write(template.render(template_values))
		else:				
			category = CategoryModel(name=self.request.get('name'), description=self.request.get('description'))
			category.put()
			self.redirect('/')

	


class ListHandler(BaseHandler):
	@admin_required
	def get(self):
		categories = CategoryModel.query().fetch()
		template_values = {'categories': categories , "session": self.session}
		template = JINJA_ENVIRONMENT.get_template('category/list.html')
		self.response.write(template.render(template_values))

	

class ViewHandler(BaseHandler):
	@admin_required
	def get(self,keyString):
		key= ndb.Key(urlsafe=keyString)
		category = key.get()
		template_values = {'category': category, 'session':self.session}
		template = JINJA_ENVIRONMENT.get_template('category/view.html')
		self.response.write(template.render(template_values))


class EditHandler(BaseHandler):
	@admin_required
	def get(self, keyString):
		key= ndb.Key(urlsafe=keyString)
		category = key.get()
		template_values = {'category': category, 'session':self.session}
		template = JINJA_ENVIRONMENT.get_template('category/edit.html')
		self.response.write(template.render(template_values))

	@admin_required
	def post(self):
		key= ndb.Key(urlsafe=self.request.get("key"))
		category = key.get()
		validation = validateForm(self.request.POST, FIELD_COND)
		if(not validation[0]):
			template_values = {"category": user, "errors" : validation[1], "session": self.session}
			template = JINJA_ENVIRONMENT.get_template('/category/edit.html')
			self.response.write(template.render(template_values))
		else:				
			category.name = self.request.get('name')
			category.description = self.request.get('description')
			category.put()
			self.redirect('/')





class DeleteHandler(BaseHandler):
	@admin_required
	def post(self):
		key= ndb.Key(urlsafe=self.request.get("key"))
		key.delete()
		self.redirect('/')


class DeleteAllHandler(BaseHandler):
	@admin_required
	def get(self):
		ndb.delete_multi(CategoryModel.query().fetch(keys_only=True))
		self.redirect('/')


application = webapp2.WSGIApplication([
    ('/category/list', ListHandler),
    ('/category/new', NewHandler),
    ('/category/view/(.+)', ViewHandler),
    ('/category/edit/(.+)', EditHandler),
    ('/category/edit', EditHandler),
    ('/category/delete', DeleteHandler),
    ('/category/deleteAll', DeleteAllHandler),
], debug=True, config=session_config)
