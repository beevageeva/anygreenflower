import cgi
import os, re
import urllib
import json, hashlib

from google.appengine.api import users
from google.appengine.ext import ndb

import webapp2,jinja2
import captcha
from random import randint
from datetime import datetime
from base_handler import *
from forms import validateForm, minLength, intField 

from auth import login_required, admin_required

from user import UserModel
from product import ProductModel
from game import UserGameSettings, UserGameItem, UserMove




class UserFarm(ndb.Model):
	
	CREATED_STATE=0
	PREPARE_GROUND_STATE=1
	SEED_PLANT_STATE=2
	GROW_STATE = 3
	HARVEST_STATE = 4

	WAIT_TIME1=60 # seconds for state = 1
	WAIT_TIME2=60 # for state = 2
	WAIT_TIME3=60 # for state = 3
	WAIT_TIME4=60 # for state = 4
	

	username = ndb.KeyProperty(UserModel)
	product = ndb.KeyProperty(ProductModel)
	size = ndb.IntegerProperty()
	name = ndb.StringProperty()
	state = ndb.IntegerProperty()
	points = ndb.IntegerProperty()
	creationdate = ndb.DateTimeProperty(auto_now_add=True)
	#keep track of every state change date
	startdate1 = ndb.DateTimeProperty()
	startdate2 = ndb.DateTimeProperty()
	startdate3 = ndb.DateTimeProperty()
	startdate4 = ndb.DateTimeProperty()

	def getWaitTime(self, username):
		if self.state==0:
			return 0
		else:
			waitTime = UserGameSettings.getUserGameSetting(username, 'farmWaitTime%d' % self.state)
			if waitTime is None:
				waitTime =  eval('UserFarm.WAIT_TIME%d'% self.state) - (datetime.now() - eval('self.startdate%d'% self.state)).total_seconds() 
			return waitTime


class GameExplHandler(BaseHandler):
	@login_required
	def get(self):
		waitTime = UserMove.getWaitTimeAtStart(self.session['username'])
		template_values = {'session':self.session,'waitTime': waitTime}
		template = JINJA_ENVIRONMENT.get_template('farm/expl.html')
		self.response.write(template.render(template_values))
	

class ViewHandler(BaseHandler):
	@login_required
	def get(self, keyString):
		key= ndb.Key(urlsafe=keyString)
		farm = key.get()
		if(self.session['username']==farm.username.id()):
			template_values = {'session':self.session, 'farm': farm, 'waitTime': farm.getWaitTime(self.session['username'])}
			template = JINJA_ENVIRONMENT.get_template('farm/view.html')
			self.response.write(template.render(template_values))


class NextStateHandler(BaseHandler):
	@login_required
	def post(self):
		key= ndb.Key(urlsafe=self.request.get("key"))
		farm = key.get()
		if(farm.getWaitTime(self.session['username'])>0 ):
			print "try to go to next before"
			return
		#TODO hardcoded 5
		if(farm.state<4):
			farm.state+=1
			exec("farm.startdate%d = datetime.now()"%farm.state)
			farm.put()
			self.response.write(json.dumps({'waitTime': farm.getWaitTime(self.session['username']) }))
		else:
			self.response.write(json.dumps({'waitTime': -1 })) #this should never occur


class NewHandler(BaseHandler):

	FARM_SIZE_COLOR = 1 #see hsb

	@login_required
	def get(self):
		products = ProductModel.query().fetch() 
		maxSize =  UserGameItem.number_of_items(self.session['username'], NewHandler.FARM_SIZE_COLOR)
		print("maxsize %d" % maxSize)
		template_values = {'session': self.session, 'products': products, 'maxSize' : maxSize}
		template = JINJA_ENVIRONMENT.get_template('farm/new.html')
		self.response.write(template.render(template_values))

	@login_required
	def post(self):
		FIELD_COND={'name': minLength(4) }
		validation = validateForm(self.request.POST, FIELD_COND)
		if(not validation[0]):
			products = ProductModel.query().fetch() 
			maxSize =  UserGameItem.number_of_items(self.session['username'], NewHandler.FARM_SIZE_COLOR)
			template_values = {'session': self.session, 'products': products, 'maxSize' : maxSize, "errors": validation[1]}
			template = JINJA_ENVIRONMENT.get_template('farm/new.html')
			self.response.write(template.render(template_values))
		else:				
			size = int(self.request.get("size"))
			uf = UserFarm(name=self.request.get("name"), size = size, points=0, username = ndb.Key('UserModel', self.session['username']), state = UserFarm.CREATED_STATE)
			uf.product = ndb.Key(urlsafe=self.request.get('product'))	
			uf.put()
			rq = UserGameItem.query(UserGameItem.username == ndb.Key('UserModel', self.session['username']), UserGameItem.color == NewHandler.FARM_SIZE_COLOR).fetch(1)
			if(rq and len(rq)>0):
				rq[0].number-=size
				if(rq[0].number == 0):
					rq[0].key.delete()
				else:	
					rq[0].put()
			self.redirect("/")

class EditHandler(BaseHandler):


	@login_required
	def get(self, keystring):
		key= ndb.Key(urlsafe=keystring)
		farm = key.get()
		products = ProductModel.query().fetch() 
		template_values = {'session': self.session, 'products': products, 'farm':farm}
		template = JINJA_ENVIRONMENT.get_template('farm/edit.html')
		self.response.write(template.render(template_values))

	@login_required
	def post(self):
		FIELD_COND={'name': minLength(4) }
		if(self.session['usertype']=='Admin'):
			FIELD_COND['points']  = intField(); 	
		validation = validateForm(self.request.POST, FIELD_COND)
		key= ndb.Key(urlsafe=self.request.get("key"))
		uf = key.get()
		if(not validation[0]):
			products = ProductModel.query().fetch() 
			template_values = {'session': self.session, 'products': products,"farm" : uf, "errors": validation[1]}
			template = JINJA_ENVIRONMENT.get_template('farm/edit.html')
			self.response.write(template.render(template_values))
		else:				
			uf.name=self.request.get("name")
			uf.product = ndb.Key(urlsafe=self.request.get('product'))
			if self.session['usertype'] == 'Admin':	
				uf.points=int(self.request.get("points"))
				uf.state=int(self.request.get("state"))
			uf.put()
			self.redirect("/")

class ListHandler(BaseHandler):
	@login_required
	def get(self):
		farms = UserFarm.query(UserFarm.username == ndb.Key('UserModel', self.session['username'])).fetch() 
		template_values = {'session': self.session, 'farms': farms}
		template = JINJA_ENVIRONMENT.get_template('farm/list.html')
		self.response.write(template.render(template_values))

class ListByUsernameHandler(BaseHandler):
	@admin_required
	def get(self, username):
		farms = UserFarm.query(UserFarm.username == ndb.Key('UserModel', username)).fetch() 
		template_values = {'session': self.session, 'farms': farms, 'username': username}
		template = JINJA_ENVIRONMENT.get_template('farm/list.html')
		self.response.write(template.render(template_values))

class ListAllHandler(BaseHandler):
	@admin_required
	def get(self):
		farms = UserFarm.query().fetch() 
		template_values = {'session': self.session, 'farms': farms, 'username':'-'}
		template = JINJA_ENVIRONMENT.get_template('farm/list.html')
		self.response.write(template.render(template_values))

class DeleteHandler(BaseHandler):
	@login_required
	def post(self):
		key= ndb.Key(urlsafe=self.request.get("key"))
		key.delete()
		self.redirect('/')


application = webapp2.WSGIApplication([
    ('/farm/view/(.+)', ViewHandler),
    ('/farm/new', NewHandler),
    ('/farm/expl', GameExplHandler),
    ('/farm/edit', EditHandler),
    ('/farm/edit/(.+)', EditHandler),
    ('/farm/listAll', ListAllHandler),
    ('/farm/list/(\w+)', ListByUsernameHandler),
    ('/farm/list', ListHandler),
    ('/farm/delete', DeleteHandler),
    ('/farm/nextState', NextStateHandler),
], debug=True, config=session_config)
