from google.appengine.ext import db

class User(db.Model):
	name       = db.StringProperty()
	email      = db.StringProperty()
	password   = db.StringProperty()
	salt       = db.StringProperty()
	roles      = db.StringListProperty()

class AuthToken(db.Model):
	token      = db.StringProperty()
	user       = db.ReferenceProperty(User)
	createDate = db.DateTimeProperty()
	expireDate = db.DateTimeProperty()
	# mode: 1 - Rolling Window
	mode       = db.IntegerProperty()
