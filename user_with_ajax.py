import cgi
import re
import urllib
import json, hashlib

from google.appengine.api import users
from google.appengine.ext import ndb

import webapp2,jinja2
import captcha


from base_handler import *
from forms import validateForm, minLength, regExpMatch 

from auth import login_required, admin_required




REMOTE_ADDR = "173.194.78.141"
NUMBER_ITEMS_PAGE = 10
CAPTCHA_PUBLIC_KEY="6LdKT-oSAAAAAKHBgkfMXSTZVCr_5p57PvoE1lfH"
CAPTCHA_PRIVATE_KEY="6LdKT-oSAAAAAKuDuEJ5PWqIux85XOutfx6Ivhvd"


class UserModel(ndb.Model):
	username = ndb.StringProperty(indexed=True)
	usertype = ndb.StringProperty(indexed=True)
	password = ndb.StringProperty(indexed=False)
	name = ndb.StringProperty(indexed=True)
	email = ndb.StringProperty(indexed=True)
	active = ndb.BooleanProperty(indexed=True)
	creationdate = ndb.DateTimeProperty(auto_now_add=True)
	@classmethod
	def find_by_username(cls, username):
		user = None
		try:
			user = ndb.Key("UserModel", username).get()
		except Exception:
			qres=UserModel.query(UserModel.username == username).fetch(1)
			if(qres and len(qres >0)):
				user = qres[0]
				print("**********************USERFOUND")
		return user
		


class LoginHandler(BaseHandler):

	def get(self):
		template = JINJA_ENVIRONMENT.get_template('user/login.html')
		self.response.write(template.render({"session": self.session}))

	def post(self):
		username = self.request.get('username')
		password = self.request.get('password')
		user = UserModel.find_by_username(username)
	 	if(user and user.active and user.password  ==  hashlib.sha224(password).hexdigest()):
			self.session['username'] = user.username
			self.session['usertype'] = user.usertype
			self.redirect('/')
		else:
			template_values = {"errors" : ["Usuario y/o contrasena incorrectos o usuario no activo"], "session": self.session}
			template = JINJA_ENVIRONMENT.get_template('user/login.html')
			self.response.write(template.render(template_values))
			

class LogoutHandler(BaseHandler):

	@login_required
	def get(self):
		self.session.clear()  #username , usertype, order
		self.redirect('/')
			
			


class NewHandler(BaseHandler):

	FIELD_COND={'username': [minLength(4), regExpMatch("^[a-zA-Z0-9_]+$")], 'password': minLength(4),'email': minLength(4),'name': minLength(4) }

	def get(self):
		chtml = captcha.displayhtml(public_key = CAPTCHA_PUBLIC_KEY,use_ssl = False,error = None)
		template_values = {'captchahtml': chtml, "session": self.session}
		template = JINJA_ENVIRONMENT.get_template('user/new.html')
		self.response.write(template.render(template_values))
	
	def post(self):
		challenge = self.request.get('recaptcha_challenge_field')
		response  = self.request.get('recaptcha_response_field')
		cResponse = captcha.submit(challenge, response, CAPTCHA_PRIVATE_KEY, REMOTE_ADDR)
		valid = True
		errors=None
		if cResponse.is_valid:
			username = self.request.get('username')
			user = UserModel.find_by_username(username)
			if not (user is None):
				valid = False
				errors=["Usuario %s ya existe "% username]
			else:
				validation = validateForm(self.request.POST, NewHandler.FIELD_COND)

				if(not validation[0]):
					valid = False
					errors = validation[1]
				else:				
					password = self.request.get('password')
					passwordConfirmation = self.request.get('passwordConfirmation')
					if(password != passwordConfirmation):
						valid = False
						errors = ["Las contrasenas no coinciden"]
					else:
						hashed_pass = hashlib.sha224(password).hexdigest()
						name = self.request.get('name')
						email =  self.request.get('email')
						if(self.request.get('isadmin') and self.request.get('isadmin')=="True"):
							usertype="Admin"
						else:
							usertype = "User"
						user = UserModel(key=ndb.Key('UserModel', username), username=username, name=name, email=email, active=False, usertype=usertype, password=hashed_pass)
						user.put()
						self.redirect('/')
		else:
			valid= False
			errors = ["Captcha not valid"]
		if not valid:
			error = cResponse.error_code
			chtml = captcha.displayhtml(public_key = CAPTCHA_PUBLIC_KEY,use_ssl = False,error = None)
			template_values = {'captchahtml':chtml, "errors" : errors, "session": self.session}
			template = JINJA_ENVIRONMENT.get_template('/user/new.html')
			self.response.write(template.render(template_values))


class ListHandler(BaseHandler):
	@admin_required
	def get(self):
		#users = UserModel.query().order(-UserModel.creationdate).fetch(NUMBER_ITEMS_PAGE)
		#TODO pagination
		users = UserModel.query().order(-UserModel.creationdate).fetch()
		#print "users :" + str(users)	
		#print "length users :" + str(len(users))	
		template_values = {'users': users , "session": self.session}
		template = JINJA_ENVIRONMENT.get_template('user/list.html')
		self.response.write(template.render(template_values))

class ListAjaxHandler(BaseHandler):
	def post(self):
		q = UserModel.query()
		filterregexp = re.compile("^filter\[(\w+)\]$")
		sortregexp = re.compile("^sort\[(\w+)\]$")
		filterparams = {}
		sortparams = {}
		for paramname in self.request.POST:
			m = filterregexp.match(paramname)
			if m:
				val = self.request.POST[paramname].strip() 
				if(val!=""):
					filterparams[m.group(1)] = val
			m = sortregexp.match(paramname)
			if m:
				sortparams[m.group(1)] = self.request.POST[paramname]
		#filter
		for fp in filterparams:
				#print("filter by %s = %s " %(fp, filterparams[fp]))
				q=q.filter( eval("UserModel.%s" % fp) >=  filterparams[fp] ).filter(eval("UserModel.%s" % fp)<  filterparams[fp] +  u'\ufffd')
		#first order by filter properties restrictions
		if(len(sortparams)>0):
			for fp in filterparams:
				if(fp in sortparams):
					if (sortparams[fp] == 'asc'):
						#print(" ASCENDING")
						q=q.order(eval("UserModel.%s" % fp))
					else:
						q=q.order(eval("-UserModel.%s" % fp))
						#print(" DESCENDING")
					del sortparams[fp]

			for sp in sortparams:
				if (sortparams[sp] == 'asc'):
					#print(" ASCENDING")
					q=q.order(eval("UserModel.%s" % sp))
				else:
					q=q.order(eval("-UserModel.%s" % sp))
					#print(" DESCENDING")
		#TODO paginate
		#page =int(self.request.get('page',default_value="0"))
		#items = q.fetch(NUMBER_ITEMS_PAGE, offset=page)
		items = q.fetch()
	
		#define here the function depending on the fields in the view
		def to_json(u):
			return {'username': u.username, 'name': u.name, 'email': u.email, 'active': u.active}

		items = map(to_json, items)
		print("results :")
		print(items)
		self.response.headers['Content-Type'] = 'application/json'   
		self.response.write(json.dumps({'users': items }))
	
class ChangeThemeHandler(BaseHandler):
	def post(self):
		print("params path")
		print(self.request.get('path'))
		print("params end")
		self.session['theme'] = self.request.get('theme')	
		self.redirect(self.request.get('path'))

class ViewHandler(BaseHandler):
	@admin_required
	def get(self,username):
		user = UserModel.find_by_username(username)
		template_values = {'user': user, 'session':self.session}
		template = JINJA_ENVIRONMENT.get_template('user/view.html')
		self.response.write(template.render(template_values))

class ChangeActiveHandler(BaseHandler):
	@admin_required
	def get(self,username):
		user = UserModel.find_by_username(username)
		if(user):
			user.active = not user.active
			user.put()
		self.redirect('/')

class ActivateAdminHandler(BaseHandler):
	ADMIN_USERNAME="admin123"
	KEY="loTG8f6l71YB2yVDpcmf"
	def get(self,key):
		if(key==ActivateAdminHandler.KEY):		
			user = UserModel.find_by_username(ActivateAdminHandler.ADMIN_USERNAME)
			if(user):
				user.active = True
				user.put()
				print("user found and activated")
			else:
				print("user NOT found")
						
		self.redirect('/')


class EditHandler(BaseHandler):
	@admin_required
	def get(self, username):
		user = UserModel.find_by_username(username)
		template_values = {'user': user, 'session':self.session}
		template = JINJA_ENVIRONMENT.get_template('user/edit.html')
		self.response.write(template.render(template_values))

	@admin_required
	def post(self):
		FIELD_COND={'email': minLength(4),'name': minLength(4) }
		user = UserModel.find_by_username(self.request.get('username'))
		validation = validateForm(self.request.POST, FIELD_COND)
		if(not validation[0]):
			template_values = {"user": user, "errors" : validation[1], "session": self.session}
			template = JINJA_ENVIRONMENT.get_template('/user/edit.html')
			self.response.write(template.render(template_values))
		else:				
			name = self.request.get('name')
			email =  self.request.get('email')
			if(self.request.get('isadmin') and self.request.get('isadmin')=="True"):
					usertype="Admin"
			else:
				usertype = "User"
			user.name = name
			user.email = email
			user.usertype = usertype
			user.put()
			self.redirect('/')


class ChangePassHandler(BaseHandler):
	@admin_required
	def get(self, username):
		template_values = {'username': username, 'session':self.session}
		template = JINJA_ENVIRONMENT.get_template('user/change_pass.html')
		self.response.write(template.render(template_values))

	@admin_required
	def post(self):
		password = self.request.get('password')
		passwordConfirmation = self.request.get('passwordConfirmation')
		if(password != passwordConfirmation):
			template_values = {"errors" : ["Las contraseas no coinciden"], "session": self.session, "username" : self.request.get('username')}
			template = JINJA_ENVIRONMENT.get_template('user/change_pass.html')
			self.response.write(template.render(template_values))
		else:				
			user = UserModel.find_by_username(self.request.get('username'))
			if(user):
				hashed_pass = hashlib.sha224(self.request.get('password')).hexdigest()
				user.password = hashed_pass
				user.put()
			self.redirect('/')


class ProfileHandler(BaseHandler):
	@login_required
	def get(self):
		user = UserModel.find_by_username(self.session["username"])
		template_values = {'user':user, 'session':self.session}
		template = JINJA_ENVIRONMENT.get_template('user/profile.html')
		self.response.write(template.render(template_values))

	@login_required
	def post(self):
		FIELD_COND={'email': minLength(4),'name': minLength(4) }
		user = UserModel.find_by_username(self.session['username'])
		validation = validateForm(self.request.POST, FIELD_COND)
		if(not validation[0]):
			template_values = {"errors" : validation[1], "session": self.session, "user": user}
			template = JINJA_ENVIRONMENT.get_template('/user/profile.html')
			self.response.write(template.render(template_values))
		else:				
			name = self.request.get('name')
			email =  self.request.get('email')
			#usertype will not be changed in profile!!
			user.name = name
			user.email = email
			user.put()
			self.redirect('/')


class ProfilePassHandler(BaseHandler):
	@login_required
	def get(self):
		template_values = {'session':self.session}
		template = JINJA_ENVIRONMENT.get_template('user/profile_pass.html')
		self.response.write(template.render(template_values))

	@login_required
	def post(self):
		password = self.request.get('password')
		passwordConfirmation = self.request.get('passwordConfirmation')
		if(password != passwordConfirmation):
			template_values = {"errors" : ["Las contraseas no coinciden"], "session": self.session}
			template = JINJA_ENVIRONMENT.get_template('user/profile_pass.html')
			self.response.write(template.render(template_values))
		else:				
			user = UserModel.find_by_username(self.session["username"])
			hashed_pass = hashlib.sha224(self.request.get('password')).hexdigest()
			user.password = hashed_pass
			user.put()
			self.redirect('/')



class DeleteHandler(BaseHandler):
	@admin_required
	def post(self):
		user = UserModel.find_by_username(self.request.get('username'))
		user.key.delete()
		self.redirect('/')


class DeleteAllHandler(BaseHandler):
	@admin_required
	def get(self):
		ndb.delete_multi(UserModel.query().fetch(keys_only=True))
		self.redirect('/')


application = webapp2.WSGIApplication([
    ('/user/list', ListHandler),
    ('/user/login', LoginHandler),
    ('/user/logout', LogoutHandler),
    ('/user/listajax', ListAjaxHandler),
    ('/user/new', NewHandler),
    ('/user/view/(\w+)', ViewHandler),
    ('/user/change_active/(\w+)', ChangeActiveHandler),
    ('/user/edit/(\w+)', EditHandler),
    ('/user/edit', EditHandler),
    ('/user/change_pass/(\w+)', ChangePassHandler),
    ('/user/change_pass', ChangePassHandler),
    ('/user/profile', ProfileHandler),
    ('/user/profile_pass', ProfilePassHandler),
    ('/user/delete', DeleteHandler),
    ('/user/deleteAll', DeleteAllHandler),
    ('/user/change_theme', ChangeThemeHandler),
    ('/user/admin_activate/(\w+)', ActivateAdminHandler),
], debug=True, config=session_config)
