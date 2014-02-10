import cgi
import re
import urllib, csv
import json, hashlib

from google.appengine.api import users
from google.appengine.ext import ndb

import webapp2,jinja2
import captcha
from google.appengine.ext.webapp import blobstore_handlers
from google.appengine.ext import blobstore


from base_handler import *
from forms import validateForm, minLength, regExpMatch 

from auth import login_required, admin_required






class UserModel(ndb.Model):
	username = ndb.StringProperty(indexed=True)
	usertype = ndb.StringProperty(indexed=True)
	password = ndb.StringProperty(indexed=False)
	name = ndb.StringProperty(indexed=True)
	email = ndb.StringProperty(indexed=True)
	phone = ndb.StringProperty(indexed=False)
	address = ndb.TextProperty(indexed=False)
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

	FIELD_COND={'username': [minLength(4), regExpMatch("^[a-zA-Z0-9_]+$")], 'password': minLength(4),'email': minLength(4),'name': minLength(4), 'phone': minLength(4),'address': minLength(4)}

	from recaptcha_settings import CAPTCHA_PUBLIC_KEY, CAPTCHA_PRIVATE_KEY, REMOTE_ADDR


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
						usertype = "User"
						user = UserModel(key=ndb.Key('UserModel', username), username=username, name=name, email=email, active=False, usertype=usertype, password=hashed_pass)
						user.phone =  self.request.get('phone')
						user.address =  self.request.get('address')
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
	NUMBER_ITEMS_PAGE = 10
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
	from admin_activate_key import ADMIN_USERNAME, KEY	
	def get(self,key):
		if(key==ActivateAdminHandler.KEY):		
			user = UserModel.find_by_username(ActivateAdminHandler.ADMIN_USERNAME)
			if(user):
				user.active = True
				user.usertype = 'Admin'
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
		FIELD_COND={'email': minLength(4),'name': minLength(4) , 'phone': minLength(4),'address': minLength(4)}
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
			user.phone =  self.request.get('phone')
			user.address =  self.request.get('address')
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
		FIELD_COND={'email': minLength(4),'name': minLength(4) , 'phone': minLength(4),'address': minLength(4)}
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
			user.phone =  self.request.get('phone')
			user.address =  self.request.get('address')
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

class CSVExportHandler(BaseHandler):
	@admin_required
	def get(self):
		users = UserModel.query().fetch()
		self.response.headers['Content-Type'] = 'text/csv'
		self.response.headers['Content-Disposition'] = 'attachment; filename=users.csv'
		writer = csv.writer(self.response.out,  quotechar='"', quoting=csv.QUOTE_ALL )
		writer.writerow(['username', 'usertype','password', 'name', 'email', 'phone', 'address', 'active', 'creationdate' ])
		for u in users:
			writer.writerow([u.username.encode("UTF-8"), u.usertype.encode("UTF-8"), u.password.encode("UTF-8"), '' if u.name is None else  u.name.encode("UTF-8"), '' if u.email is None else  u.email.encode("UTF-8"), '' if u.phone is None else  u.phone.encode("UTF-8"), '' if u.address is None else  u.address.encode("UTF-8"), u.active, u.creationdate.strftime('%Y-%m-%d %H:%M:%S')])
	
class CSVImportHandler(BaseHandler, blobstore_handlers.BlobstoreUploadHandler):

	@admin_required
	def get(self):
		template_values = {'upload_url': blobstore.create_upload_url('/user/csv_import'), 'session':self.session}
		template = JINJA_ENVIRONMENT.get_template('user/import_csv.html')
		self.response.write(template.render(template_values))

	@admin_required
	def post(self):
		from datetime import datetime
		upload_files = self.get_uploads('file')  # 'file' is file upload field in the form
		blob_info = upload_files[0]
		blob_reader = blob_info.open()
		first = True
		#TODO check if there is any multi put
		for line in blob_reader:
			if(first):
				first = False
			else:
				#TODO DELIMITER NO HARDCODE
				delimiter = ","
				#print " DEFAULT CSV DELIMITER %s" %csv.Dialect.delimiter 
				#delimiter = csv.Dialect.delimiter
				u = line.split(delimiter)
				if(len(u) == 9):
					username = u[0]
					user = ndb.Key("UserModel", username).get()
					if(user is None):
						user = UserModel(key=ndb.Key('UserModel', username), username=username)
					user.usertype = u[1]
					user.password = u[2]
					user.name = u[3]
					user.email = u[4]
					user.phone = u[5]
					user.address = u[6]
					user.active = (u[7].lower() == "true")
					#TODO
					#user.creationdate = datetime.strptime(u[8], '%Y-%m-%d %H:%M:%S')   
					user.creationdate = datetime.now() 
					user.put()
				else:
					print "length !=9 line is %s, split is: " % line
					print u
					print "end split"
		blob_reader.close()
		blob_info.delete()
		self.redirect('/user/list' )


application = webapp2.WSGIApplication([
    ('/user/list', ListHandler),
    ('/user/login', LoginHandler),
    ('/user/logout', LogoutHandler),
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
    ('/user/csv_export', CSVExportHandler),
    ('/user/csv_import', CSVImportHandler),
], debug=True, config=session_config)
