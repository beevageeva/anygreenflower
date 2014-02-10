import re
import urllib
import json, hashlib

from google.appengine.ext import ndb

import webapp2,jinja2
import captcha


from google.appengine.ext.webapp import blobstore_handlers
from google.appengine.ext import blobstore

from base_handler import *
from forms import validateForm, minLength, floatField 

from auth import login_required, admin_required

from product import ProductModel
from category import CategoryModel


#las cestas
class ProductGroupItemModel(ndb.Model):
	product = ndb.KeyProperty(ProductModel)
	qty = ndb.FloatProperty()
	
class ProductGroupModel(ndb.Model):
	name = ndb.StringProperty()
	items = ndb.StructuredProperty(ProductGroupItemModel, repeated=True)
	price = ndb.FloatProperty(indexed=True)
	visible = ndb.BooleanProperty(indexed=True)

	def getItemQty(self, product_key):
		for item in self.items:
			if item.product == ndb.Key(urlsafe=product_key):
				return item.qty
		return 0

#end las cestas


def getProductsFromParams(params):
	pregexp = re.compile("^products\[(.+)\]$")
	prparams = {}
	for paramname in params:
		m = pregexp.match(paramname)
		if m:
			val = params[paramname].strip() 
			if(val!=""):
				prparams[m.group(1)] = val
	return prparams	


FIELD_COND={'name': minLength(4) , 'price': floatField()}

class NewHandler(BaseHandler):
	@admin_required
	def get(self):
		template_values = {"session": self.session, "categories": CategoryModel.query().fetch()}
		template = JINJA_ENVIRONMENT.get_template('product_group/new.html')
		self.response.write(template.render(template_values))
	
	@admin_required
	def post(self):
		validation = validateForm(self.request.POST, FIELD_COND)
		if(not validation[0]):
			template_values = {"errors" : validation[1], "session": self.session, "categories": CategoryModel.query().fetch()}
			template = JINJA_ENVIRONMENT.get_template('/product_group/new.html')
			self.response.write(template.render(template_values))
		else:				
			product_group = ProductGroupModel(name=self.request.get('name'), price=float(self.request.get('price')))
			product_group.visible = (self.request.get('visible') and self.request.get('visible')=="True")
			product_group.items = []
			prod_params = getProductsFromParams(self.request.POST)
			#print("product params : " + str(prod_params))
			for prod_key in prod_params:
				try:
					qty = float(prod_params[prod_key])
				except ValueError:
					qty = 0
				if qty > 0:
					prod_group_item = ProductGroupItemModel(product=ndb.Key(urlsafe=prod_key), qty=qty)
					product_group.items.append(prod_group_item)	
			product_group.put()
			self.redirect('/product_group/view/%s' % product_group.key.urlsafe())

	


class ListHandler(BaseHandler):
	@admin_required
	def get(self):
		product_groups = ProductGroupModel.query().fetch()
		template_values = {'product_groups': product_groups , "session": self.session}
		template = JINJA_ENVIRONMENT.get_template('product_group/list.html')
		self.response.write(template.render(template_values))

class ListVisibleHandler(BaseHandler):
	@login_required
	def get(self):
		product_groups = ProductGroupModel.query(ProductGroupModel.visible == True).fetch()
		categories = CategoryModel.query().fetch()
		template_values = {'product_groups': product_groups , "session": self.session, "categories" : categories}
			
		template = JINJA_ENVIRONMENT.get_template('%s.html'% self.request.path[1:])
		self.response.write(template.render(template_values))
	

class ViewHandler(BaseHandler):
	@login_required
	def get(self,keyString):
		key= ndb.Key(urlsafe=keyString)
		product_group = key.get()
		mustsave=False
		#delete null items:
#		for item in product_group.items:
#			if item.product.get() is None:
#				print("item product key IS NONE-- product already deleted")
#				product_group.items.remove(item)
#				mustsave=True
#		if mustsave:
#			print("deleted items from product group -- SAVING")
#			product_group.put()
		template_values = {'product_group': product_group, 'session':self.session}
		template = JINJA_ENVIRONMENT.get_template('product_group/view.html')
		self.response.write(template.render(template_values))


class EditHandler(BaseHandler):
	@admin_required
	def get(self, keyString):
		key= ndb.Key(urlsafe=keyString)
		product_group = key.get()
		template_values = {'product_group': product_group, 'session':self.session, "categories": CategoryModel.query().fetch()}
		template = JINJA_ENVIRONMENT.get_template('product_group/edit.html')
		self.response.write(template.render(template_values))

	@admin_required
	def post(self):
		key= ndb.Key(urlsafe=self.request.get("key"))
		product_group = key.get()
		validation = validateForm(self.request.POST, FIELD_COND)
		if(not validation[0]):
			template_values = {"product_group": product_group, "errors" : validation[1], "session": self.session, "categories": CategoryModel.query().fetch()}
			template = JINJA_ENVIRONMENT.get_template('/product_group/edit.html')
			self.response.write(template.render(template_values))
		else:				
			product_group.name = self.request.get('name')
			product_group.price = float(self.request.get('price'))
			product_group.visible = (self.request.get('visible') and self.request.get('visible')=="True")
			product_group.items = []
			prod_params = getProductsFromParams(self.request.POST)
			for prod_key in prod_params:
				try:
					qty = float(prod_params[prod_key])
				except ValueError:
					qty = 0
				if qty > 0:
					prod_group_item = ProductGroupItemModel(product=ndb.Key(urlsafe=prod_key), qty=qty)
					product_group.items.append(prod_group_item)	
			product_group.put()
			self.redirect('/product_group/view/%s' % product_group.key.urlsafe())



class DeleteHandler(BaseHandler):
	@admin_required
	def post(self):
		key= ndb.Key(urlsafe=self.request.get("key"))
		key.delete()
		self.redirect('/')

class DeleteItemHandler(BaseHandler):
	@admin_required
	def post(self):
		pg= ndb.Key(urlsafe=self.request.get("key")).get()
		pkey= ndb.Key(urlsafe=self.request.get("pkey"))
		for item in pg.items:
			if(item.product==pkey):
				pg.items.remove(item)
				pg.put()
				self.redirect('/')

class DeleteAllHandler(BaseHandler):
	@admin_required
	def get(self):
		ndb.delete_multi(ProductGroupModel.query().fetch(keys_only=True))
		self.redirect('/')


application = webapp2.WSGIApplication([
    ('/product_group/list', ListHandler),
    ('/product_group/list_visible', ListVisibleHandler),
    ('/product_group/list_visible_treetable', ListVisibleHandler),
    ('/product_group/new', NewHandler),
    ('/product_group/view/(.+)', ViewHandler),
    ('/product_group/edit/(.+)', EditHandler),
    ('/product_group/edit', EditHandler),
    ('/product_group/delete', DeleteHandler),
    ('/product_group/deleteItem', DeleteItemHandler),
    ('/product_group/deleteAll', DeleteAllHandler),
], debug=True, config=session_config)
