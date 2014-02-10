import cgi
import os
import urllib
import json, hashlib

from google.appengine.ext import ndb

import webapp2,jinja2
import captcha



from base_handler import *
from forms import validateForm, minLength, floatField

from auth import login_required, admin_required

from product import ProductModel
from product_group import ProductGroupModel
from user import UserModel

class OrderItemModel(ndb.Model):
	ref = ndb.KeyProperty() #no kind defined, may be ProductModel o ProductGroupModel (depending on oitype)
	qty = ndb.FloatProperty()

class OrderModel(ndb.Model):
	items = ndb.StructuredProperty(OrderItemModel, repeated=True)
	creationdate = ndb.DateTimeProperty(auto_now_add=True)
	username = ndb.KeyProperty(UserModel)
	obs = ndb.TextProperty()
	state = ndb.StringProperty()

	NEW_STATE = "new"
	CREATED_STATE = "created"
	APPROVED_STATE = "approved"

	@classmethod
	def getNewOrder(cls, username):
		resquery = OrderModel.query(OrderModel.username == ndb.Key('UserModel', username), OrderModel.state == OrderModel.NEW_STATE).fetch(1)
		if(resquery and len(resquery)>0):
			return resquery[0]
		return None	


	def removeByRefKey(self, refkey):
		item_key = ndb.Key(urlsafe=refkey)
		for item in self.items:
			if(item.ref == item_key):
				self.items.remove(item)
			

	def addOrderItem(self, refkey, qty):
		ritem = None	
		item_key = ndb.Key(urlsafe=refkey)
		for item in self.items:
			if(item.ref == item_key):
				ritem = item
		if ritem is None:
			ritem = OrderItemModel(ref = item_key, qty = 0)
			self.items.append(ritem)
		ritem.qty+=qty
		self.put()
		

	
class RemoveHandler(BaseHandler):
	@login_required
	def post(self):
		key= ndb.Key(urlsafe=self.request.get("key"))
		order = key.get()
		if(order):
			if order.state in ["new","created"] or self.session['usertype']=='Admin':
				order.removeByRefKey(self.request.get("refkey"))	
				order.put()
		self.redirect('/')

class AddHandler(BaseHandler):
	@login_required
	def post(self):
		validation = validateForm(self.request.POST, {"qty": floatField()})
		if(validation[0]):
			order = OrderModel.getNewOrder(self.session['username'])
			if not order:
				order = OrderModel(username = ndb.Key('UserModel', self.session['username']), state = OrderModel.NEW_STATE)
			order.addOrderItem(self.request.get("ref"), float(self.request.get("qty")))
		self.redirect('/product_group/list_visible')
	
class CreateHandler(BaseHandler):

	@login_required
	def get(self):
		order = OrderModel.getNewOrder(self.session['username'])
		template_values = {'session':self.session, "order": order}
		template = JINJA_ENVIRONMENT.get_template('order/create.html')
		self.response.write(template.render(template_values))


	@login_required
	def post(self):
		order = OrderModel.getNewOrder(self.session['username'])
		if(len(order.items)>0):
			order.obs=self.request.get("obs")
			order.state = OrderModel.CREATED_STATE
			order.put()
		self.redirect('/' )

class ApproveHandler(BaseHandler):

	@admin_required
	def post(self):
		key= ndb.Key(urlsafe=self.request.get("key"))
		order = key.get()
		order.state = OrderModel.APPROVED_STATE
		order.put()
		self.redirect('/' )
	


class ListHandler(BaseHandler):
	@admin_required
	def get(self):
		orders = OrderModel.query().order(-OrderModel.creationdate).fetch()
		template_values = {'orders': orders , "session": self.session}
		template = JINJA_ENVIRONMENT.get_template('order/list.html')
		self.response.write(template.render(template_values))

	
class ListByUsernameHandler(BaseHandler):
	@login_required
	def get(self, username):
		orders = OrderModel.query(OrderModel.username == ndb.Key('UserModel', username)).order(-OrderModel.creationdate).fetch()
		template_values = {'orders': orders , "session": self.session, "username": username}
		template = JINJA_ENVIRONMENT.get_template('order/list.html')
		self.response.write(template.render(template_values))

class ViewHandler(BaseHandler):
	@login_required
	def get(self, keyString):
		key= ndb.Key(urlsafe=keyString)
		order = key.get()
		template_values = {'order': order, 'session':self.session}
		template = JINJA_ENVIRONMENT.get_template('order/view.html')
		self.response.write(template.render(template_values))

class CurrentViewHandler(BaseHandler):
	@login_required
	def get(self):
		order = OrderModel.getNewOrder(self.session['username'])
		template_values = {'order': order, 'session':self.session}
		template = JINJA_ENVIRONMENT.get_template('order/view.html')
		self.response.write(template.render(template_values))


class EditHandler(BaseHandler):

	def checkEditPermission(self, order):
 		if order.state!="new" and (self.session["usertype"] == "Admin" or order.state ==  "created"):
			return True
		else:
			self.redirect("/user/login")
			return False


	@login_required
	def get(self, keyString):
		key= ndb.Key(urlsafe=keyString)
		order = key.get()
		if(self.checkEditPermission(order)):
			template_values = {'order': order, 'session':self.session}
			template = JINJA_ENVIRONMENT.get_template('order/edit.html')
			self.response.write(template.render(template_values))

	@login_required
	def post(self):
		key= ndb.Key(urlsafe=self.request.get("key"))
		order = key.get()
		if(self.checkEditPermission(order)):
			order.obs = self.request.get('obs')
			order.put()
			self.redirect('/')



class DeleteHandler(BaseHandler):

	@login_required
	def post(self):
		key= ndb.Key(urlsafe=self.request.get("key"))
		order = key.get()
 		if order.state!="new" and (self.session["usertype"] == "Admin" or order.state ==  "created"):
			key.delete()
		else:
			self.redirect("/user/login")
		self.redirect('/')




application = webapp2.WSGIApplication([
    ('/order/list', ListHandler),
    ('/order/list/(\w+)', ListByUsernameHandler),
    ('/order/add', AddHandler),
    ('/order/remove', RemoveHandler),
    ('/order/create', CreateHandler),
    ('/order/approve', ApproveHandler),
    ('/order/view', CurrentViewHandler),
    ('/order/view/(.+)', ViewHandler),
    ('/order/edit/(.+)', EditHandler),
    ('/order/edit', EditHandler),
    ('/order/delete', DeleteHandler),
], debug=True, config=session_config)
