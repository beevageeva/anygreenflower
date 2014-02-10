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
from forms import validateForm, minLength, regExpMatch 

from auth import login_required, admin_required

from user import UserModel

class UserGameSettings(ndb.Model):
	username = ndb.KeyProperty(UserModel)
	propname = ndb.StringProperty()
	propvalue = ndb.StringProperty()

	@classmethod
	def getUserGameSetting(cls, username, propname):
		res = UserGameSettings.query(UserGameSettings.username == ndb.Key('UserModel',username), UserGameSettings.propname == propname).fetch(1)
		if(res and len(res)>0):
			return res[0]
		return None


class UserGameItem(ndb.Model):
	username = ndb.KeyProperty(UserModel)
	color = ndb.IntegerProperty() #for now from 1 to 8 see raphael hsb
	level = ndb.IntegerProperty()
	number = ndb.IntegerProperty()

	@classmethod	
	def find_user_gameitems(cls, username):
		return UserGameItem.query(UserGameItem.username == ndb.Key('UserModel', username)).order(-UserGameItem.level).fetch()

	@classmethod	
	def number_of_items(cls, username, color):
		resq = UserGameItem.query(UserGameItem.username == ndb.Key('UserModel', username), UserGameItem.color == color).fetch(1)
		if(resq and len(resq)>0):
			return resq[0].number
		return 0

class UserMove(ndb.Model):
	username = ndb.KeyProperty(UserModel)
	coordinates = ndb.StringProperty()
	creationdate = ndb.DateTimeProperty(auto_now_add=True)
	
	MAX_COORD = 100
	#wait time TODO change value to greater than 10 sec
	DEFAULT_WAIT_TIME = 60   #sec



	@classmethod
	def getLastCoordinates(cls, username):
		#this also creates new coordinates if none exists
		res = UserMove.query(UserMove.username == ndb.Key('UserModel', username)).order(-UserMove.creationdate).fetch(1)
		if(res and len(res)>0):
			return res[0].coordinates
		coord = "%d|%d" % (randint(int(UserMove.MAX_COORD/2), UserMove.MAX_COORD), randint(int(UserMove.MAX_COORD/2), UserMove.MAX_COORD))
		um = UserMove(username = ndb.Key('UserModel', username), coordinates = coord)
		um.put()
		return coord
		
	@classmethod
	def getWaitTimeAtStart(cls, username):
		waitTime = UserGameSettings.getUserGameSetting(username, 'waitTime')
		if(waitTime is None):
			waitTime = UserMove.DEFAULT_WAIT_TIME
		return waitTime	

	@classmethod
	def getWaitTime(cls, username):
		query =UserMove.query(UserMove.username == ndb.Key('UserModel', username))
		count = query.count()
		if(count <=0):
			return -1 
		reslast = query.order(-UserMove.creationdate).fetch(1)[0]
		waitTime = UserMove.getWaitTimeAtStart(username)
		return waitTime - (datetime.now() - reslast.creationdate).total_seconds() 
	

class ViewHandler(BaseHandler):
	def get(self):
		user_gameitems = UserGameItem.find_user_gameitems(self.session['username'])
		waitTime = UserMove.getWaitTime(self.session['username'])
		coordinates = UserMove.getLastCoordinates(self.session['username'])
		#print("invitems:" + str(user_gameitems))
		template_values = {'session':self.session, 'game_items': user_gameitems, 'wait_time': waitTime, 'coordinates': coordinates}
		template = JINJA_ENVIRONMENT.get_template('game/view.html')
		self.response.write(template.render(template_values))


class MoveHandler(BaseHandler):
	def post(self):
		if(UserMove.getWaitTime(self.session['username'])>0 ):
			return
		self.response.headers['Content-Type'] = 'application/json'   
		color = randint(1,8)
		ugi = UserGameItem.query(UserGameItem.username == ndb.Key('UserModel', self.session['username']), UserGameItem.level == 1, UserGameItem.color == color).fetch()
		if(ugi is None or len(ugi) == 0):
			ugi = UserGameItem(username = ndb.Key('UserModel', self.session['username']), level = 1, color = color, number=0)
		else:
			ugi = ugi[0]	
		ugi.number+=1
		ugi.put()
		coordinates = self.request.get("coord")
		if(coordinates and coordinates!=""):
			um =UserMove(username = ndb.Key('UserModel', self.session['username']), coordinates=coordinates)
			um.put()
		waitTime = UserGameSettings.getUserGameSetting(self.session['username'], 'waitTime')
		if(waitTime is None):
			waitTime = UserMove.DEFAULT_WAIT_TIME
		self.response.write(json.dumps({'color': color , 'wait_time': waitTime}))





application = webapp2.WSGIApplication([
    ('/game/view', ViewHandler),
    ('/game/move', MoveHandler),
], debug=True, config=session_config)
