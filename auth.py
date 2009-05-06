import base64
import cgi
import datetime
import random
import sha
import string

from google.appengine.ext import db

import auth_models

def hash_password(password, salt):
	joined = password + '$1$' + salt
	hashed = sha.sha(joined).digest()
	encoded = base64.encodestring(hashed)
	trimmed = encoded.strip()
	return trimmed

def generate_salt(length=8):
	saltChars = './' + string.ascii_letters + string.digits
	saltCharsLength = len(saltChars)
	salt = ""
	for i in range(1,length):
		salt += saltChars[random.randint(0,saltCharsLength - 1)]
	return salt

def authorize_basic(self):
	if not self.request.headers.has_key("Authorization"):
		return None
	
	authorizeHeader = self.request.headers["Authorization"]

	if not authorizeHeader.startswith("Basic "):
		return None

	base64encoded = authorizeHeader.replace("Basic ", "", 1)
	decoded = base64.decodestring(base64encoded)
	if decoded.find(":") < 0:
		# If we don't have a colon, we can't split the user
		#   and the password, which means something is wrong.
		#   By default, when something is wrong, do not
		#   authorize.
		return None

	[email, password] = decoded.split(":", 1)

	query = db.GqlQuery("SELECT * FROM User WHERE email = :1", email)
	user = query.get()
	if user == None:
		return None

	if hash_password(password, user.salt) != user.password:
		return None

	return user

def authorize_token(self):
	if not self.request.headers.has_key("X-Authentication-Token"):
		return None

	token = self.request.headers["X-Authentication-Token"]

	query = db.GqlQuery("SELECT * FROM AuthToken WHERE token = :1 AND expireDate > :2", token, datetime.datetime.utcnow())
	dbToken = query.get()

	if dbToken == None:
		return None

	if dbToken.mode == 1:
		dbToken.expireDate = datetime.datetime.utcnow() + datetime.timedelta(minutes=20)
		dbToken.put()

	return dbToken.user

def authorize_cookie(self):
	if not self.request.cookies.has_key("Authentication-Token"):
		return None

	token = self.request.cookies["Authentication-Token"]

	query = db.GqlQuery("SELECT * FROM AuthToken WHERE token = :1 AND expireDate > :2", token, datetime.datetime.utcnow())
	dbToken = query.get()

	if dbToken == None:
		return None

	if dbToken.mode == 1:
		dbToken.expireDate = datetime.datetime.utcnow() + datetime.timedelta(minutes=20)
		dbToken.put()

	return dbToken.user

def authorize(self):
	user = authorize_basic(self)
	if user == None:
		user = authorize_token(self)
	if user == None:
		user = authorize_cookie(self)
	return user

def authorizationOptional(func):
	def wrapper(self, *args, **kw):
		user = authorize(self)
		self.request.authorized_user = user
		func(self, *args, **kw)
	return wrapper

def authorizationRequired(func):
	def wrapper(self, *args, **kw):
		user = authorize(self)
		if user == None:
			report_unauthorized(self.response)
		else:
			self.request.authorized_user = user
			func(self, *args, **kw)
	return wrapper

def roleRequired(role):
	def authorizationRequired(func):
		def wrapper(self, *args, **kw):
			user = authorize(self)
			if user == None or not user_in_role(user, role):
				report_unauthorized(self.response)
			else:
				self.request.authorized_user = user
				func(self, *args, **kw)
		return wrapper
	return authorizationRequired

def user_in_role(user, role):
	for user_role in user.roles:
		if user_role == role:
			return True
	return False

def report_unauthorized(response, status=401, message="Unauthorized", realm="TweetQueue"):
	response.set_status(status)
	response.headers['Content-Type'] = 'text/plain'
	response.headers['WWW-Authenticate'] = 'Basic realm="' + realm + '"'
	response.out.write(message)
