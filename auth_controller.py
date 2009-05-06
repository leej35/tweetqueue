import cgi
import os

import auth
import auth_models

import base64
import uuid
import datetime

from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

from django.utils import simplejson

class Users(webapp.RequestHandler):

	@auth.roleRequired("user_admin")
	def get(self):
		usersGql = db.GqlQuery("SELECT * FROM User")

		users = []
		for user in usersGql:
			users.append({
					"name": user.name,
					"email": user.email,
					"password": user.password,
					"salt": user.salt,
					"roles": user.roles,
					"uri": "/user/" + str(user.key()),
				})
			
		self.response.headers["Content-Type"] = "application/json"
		self.response.out.write(simplejson.dumps({ "users": users }, indent=2))

	@auth.roleRequired("user_admin")
	def post(self):
		user = auth_models.User()
		input = simplejson.loads(self.request.body)

		missing_fields = []

		if input.has_key("name"):
			user.name = input["name"]
		else:
			missing_fields.append("name")

		if input.has_key("email"):
			user.email = input["email"]
		else:
			missing_fields.append("email")

		if input.has_key("password"):
			salt = auth.generate_salt(length=8)
			password = input["password"]
			user.password = auth.hash_password(password, salt)
			user.salt = salt
		else:
			missing_fields.append("password")

		if input.has_key("roles"):
			user.roles = input["roles"]
		else:
			user.roles = []

		self.response.headers["Content-Type"] = "application/json"

		if len(missing_fields) > 0:
			self.response.set_status(403)
			self.response.out.write(simplejson.dumps({ "result": "Failure", "reason": "Not all required fields were supplied", "missing_fields": missing_fields }))
			return

		user.put()
		self.response.out.write(simplejson.dumps({ "result": "Success" }))

class User(webapp.RequestHandler):

	@auth.authorizationRequired
	def get(self, key):
		user = None
		try:
			user = db.get(db.Key(key))
		except:
			pass

		if user == None:
			self.response.set_status(404)
			return

		authUser = self.request.authorized_user
		if authUser.key() == user.key() or auth.user_in_role(authUser, "user_admin"):
			pass
		else:
			auth.report_unauthorized(self.response)
			return

		user = {
					"name": user.name,
					"email": user.email,
					"password": user.password,
					"salt": user.salt,
					"roles": user.roles,
					"uri": "/user/" + str(user.key()),
				}
			
		self.response.headers["Content-Type"] = "application/json"
		self.response.out.write(simplejson.dumps(user, indent=2))

	@auth.authorizationRequired
	def post(self, key):
		user = None
		try:
			user = db.get(db.Key(key))
		except:
			pass

		if user == None:
			self.response.set_status(404)
			return

		authUser = self.request.authorized_user
		if authUser.key() == user.key() or auth.user_in_role(authUser, "user_admin"):
			pass
		else:
			auth.report_unauthorized(self.response)
			return

		input = simplejson.loads(self.request.body)

		if input.has_key("name"):
			user.name = input["name"]
		if input.has_key("email"):
			user.email = input["email"]
		if input.has_key("password"):
			user.password = auth.hash_password(input["password"], user.salt)
		if input.has_key("roles"):
			user.roles = input["roles"]

		user.put()

		self.response.headers["Content-Type"] = "application/json"
		self.response.out.write(simplejson.dumps({ "result": "Success" }))

	@auth.authorizationRequired
	def delete(self, key):
		user = None
		try:
			user = db.get(db.Key(key))
		except:
			pass

		if user == None:
			self.response.set_status(404)
			return

		authUser = self.request.authorized_user
		if authUser.key() == user.key() or auth.user_in_role(authUser, "user_admin"):
			pass
		else:
			auth.report_unauthorized(self.response)
			return

		user.delete()

class TokenRequest(webapp.RequestHandler):

	@auth.roleRequired('admin')
	def get(self):
		tokensGql = db.GqlQuery("SELECT * FROM AuthToken WHERE expireDate > :1", datetime.datetime.utcnow())

		tokens = []
		for token in tokensGql:
			tokens.append({
					"token": token.token,
					"userEmail": token.user.email,
					"user": "/user/" + str(token.user.key()),
					"createDate": str(token.createDate),
					"expireDate": None if token.expireDate == None else str(token.expireDate),
					"mode": token.mode,
				})
			
		self.response.headers["Content-Type"] = "application/json"
		self.response.out.write(simplejson.dumps({ "tokens": tokens }, indent=2))
		

	@auth.authorizationRequired
	def post(self):
		token = auth_models.AuthToken()
		input = simplejson.loads(self.request.body)

		missing_fields = []

		if input.has_key("mode"):
			token.mode = int(input["mode"])
		else:
			missing_fields.append("mode")

		token.createDate = datetime.datetime.utcnow()
		token.expireDate = datetime.datetime.utcnow() + datetime.timedelta(minutes=20)
		token.user = self.request.authorized_user
		token.token = base64.urlsafe_b64encode(uuid.uuid4().bytes).rstrip('=')

		self.response.headers["Content-Type"] = "application/json"

		if len(missing_fields) > 0:
			self.response.set_status(403)
			self.response.out.write(simplejson.dumps({ "result": "Failure", "reason": "Not all required fields were supplied", "missing_fields": missing_fields }))
			return

		token.put()

		self.response.headers["X-Authentication-Token"] = token.token
		self.response.out.write(simplejson.dumps({ "result": "Success", "payload": { "token": token.token } }))
