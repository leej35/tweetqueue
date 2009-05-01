import cgi
import os

import datetime

from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app

class Profile(db.Model):
	name       = db.StringProperty()
	password   = db.StringProperty()

class Tweet(db.Model):
	profile    = db.ReferenceProperty(Profile)
	text       = db.StringProperty()
	date       = db.DateTimeProperty()
	posted     = db.BooleanProperty(required=True)
	postedDate = db.DateTimeProperty()

class ProfilesPage(webapp.RequestHandler):
	def get(self):
		profiles = db.GqlQuery("SELECT * FROM Profile")

		template_values = {
				"profiles": profiles,
		}

		path = os.path.join(os.path.dirname(__file__), 'profiles.html')
		self.response.out.write(template.render(path, template_values))

	def post(self):
		profile = Profile()
		profile.name = self.request.get("name")
		profile.password = self.request.get("password")
		profile.put()

		self.redirect('/profiles')

class TweetsPage(webapp.RequestHandler):
	def get(self, profileName):
		profile = db.GqlQuery("SELECT * FROM Profile WHERE name = :1", profileName).get()

		tweets = db.GqlQuery("SELECT * FROM Tweet WHERE profile = :1 ORDER BY date", profile)

		template_values = {
				"profile": profile,
				"tweets": tweets,
		}

		path = os.path.join(os.path.dirname(__file__), 'tweets.html')
		self.response.out.write(template.render(path, template_values))

	def post(self, profileName):
		profile = db.GqlQuery("SELECT * FROM Profile WHERE name = :1", profileName).get()


		tweet = Tweet(posted=False)
		tweet.profile = profile
		tweet.text = self.request.get("text")
		tweet.date = datetime.datetime.strptime(self.request.get("date"), "%Y-%m-%d %H:%M")
		tweet.posted = False
		tweet.put()

		self.redirect('/tweets/' + profile.name)

class UpdatePage(webapp.RequestHandler):
	def get(self):

		tweets = db.GqlQuery("SELECT * FROM Tweet WHERE date < :1 ORDER BY date", datetime.datetime.utcnow())

		self.response.headers["Content-Type"] = "text/plain"

		for tweet in tweets:
			self.response.out.write("Date: " + str(tweet.date) + "\n")
			self.response.out.write("Text: " + str(tweet.text) + "\n")
			self.response.out.write("Login: " + str(tweet.profile.name) + "\n")
			self.response.out.write("Password: " + str(tweet.profile.password) + "\n")
			self.response.out.write("Updated: " + str(tweet.postedDate) + "\n")
			self.response.out.write("\n")

	def post(self):

		tweets = db.GqlQuery("SELECT * FROM Tweet")

		self.response.headers["Content-Type"] = "text/plain"

		for tweet in tweets:
			tweet.posted = False
			tweet.put()
			self.response.out.write("Date: " + str(tweet.date) + "\n")
			self.response.out.write("Text: " + str(tweet.text) + "\n")
			self.response.out.write("Login: " + str(tweet.profile.name) + "\n")
			self.response.out.write("Password: " + str(tweet.profile.password) + "\n")
			self.response.out.write("Updated: " + str(tweet.updated) + "\n")
			self.response.out.write("\n")

#class Guests(webapp.RequestHandler):
#	@loginRequired
#	def get(self):
#
#		queryArguments = []
#		requestArguments = []
#		for arg in self.request.arguments():
#			requestArguments.append(arg.lower())
#
#		whereClauses = []
#		whereClausesTransformed = []
#
#		if "address" in requestArguments:
#			queryArguments.append(self.request.get("address"))
#			whereClauses.append("address = :1")
#
#		if "rsvpstatus" in requestArguments:
#			queryArguments.append(self.request.get("rsvpstatus"))
#			whereClauses.append("rsvpstatus = :1")
#
#		iCounter = 1
#
#		for whereClause in whereClauses:
#			whereClausesTransformed.append(whereClause.replace(":1", ":" + str(iCounter)))
#			iCounter = iCounter + 1
#
#		whereClause = ""
#		if len(whereClausesTransformed) > 0:
#			whereClause = "WHERE " + " AND ".join(whereClausesTransformed)
#
#		guests = db.GqlQuery("SELECT * FROM Guest " + whereClause + " ORDER BY side, type, lastname, name", *queryArguments)
#
#		template_values = {
#			'logout_url': users.create_logout_url('/wedding'),
#			'guests': guests,
#		}
#
#		path = os.path.join(os.path.dirname(__file__), 'guests.html')
#
#		if (self.request.headers['Accept'] == "text/xml" or self.request.path.endswith(".xml")):
#			path = os.path.join(os.path.dirname(__file__), 'guests.xml')
#			self.response.headers['Content-Type'] = 'text/xml'
#
#		self.response.out.write(template.render(path, template_values))
#
#class GuestR(webapp.RequestHandler):
#	@loginRequired
#	def get(self, key):
#		
#		if (self.request.get('mode') == 'edit'):
#			self.getEdit(key)
#		else:
#			self.getView(key)
#
#	def getView(self, key):
#		guest = db.get(db.Key(key))
#
#		template_values = {
#			'guest': guest,
#		}
#
#		path = os.path.join(os.path.dirname(__file__), 'guest.html')
#		self.response.out.write(template.render(path, template_values))
#	
#	def getEdit(self, key):
#		guest = db.get(db.Key(key))
#
#		template_values = {
#			'guest': guest,
#		}
#
#		path = os.path.join(os.path.dirname(__file__), 'edit.html')
#		self.response.out.write(template.render(path, template_values))
#
#	@loginRequired
#	def post(self, key):
#		guest = db.get(db.Key(key))
#
#		edit = self.request.get('edit', default_value = None)
#		delete = self.request.get('delete', default_value = None)
#
#		if (not(delete == None)):
#			self.delete(key)
#			return
#
#		name = self.request.get('name', default_value = None)
#		lastname = self.request.get('lastname', default_value = None)
#		children = self.request.get('children', default_value = None)
#		address = self.request.get('address', default_value = None)
#		side = self.request.get('side', default_value = None)
#		type = self.request.get('type', default_value = None)
#		invited = self.request.get('invited', default_value = None)
#		expected = self.request.get('expected', default_value = None)
#		rsvpstatus = self.request.get('rsvpstatus', default_value = None)
#		rsvpcount = self.request.get('rsvpcount', default_value = None)
#
#		if (not(name == None)):
#			guest.name = name
#		if (not(lastname == None)):
#			guest.lastname = lastname
#		if (not(children == None)):
#			guest.children = children
#		if (not(address == None)):
#			guest.address = address
#		if (not(side == None)):
#			guest.side = side
#		if (not(type == None)):
#			guest.type = type
#		if (not(invited == None)):
#			try:
#				guest.invited = int(invited)
#			except:
#				pass
#		if (not(expected == None)):
#			try:
#				guest.expected = int(expected)
#			except:
#				pass
#		if (not(rsvpstatus == None)):
#			guest.rsvpstatus = rsvpstatus
#		if (not(rsvpcount == None)):
#			try:
#				guest.rsvpcount = int(rsvpcount)
#			except:
#				pass
#
#		guest.put()
#
#		self.redirect('/wedding/guest/' + key)
#
#	@loginRequired
#	def delete(self, key):
#		guest = db.get(db.Key(key))
#		guest.delete()
#
#		self.redirect('/wedding/guests')
#
#class AddGuest(webapp.RequestHandler):
#	@loginRequired
#	def get(self):
#		path = os.path.join(os.path.dirname(__file__), 'guests-add.html')
#		self.response.out.write(template.render(path, {}))
#
#	@loginRequired
#	def post(self):
#		guest = Guest()
#
#		name = self.request.get('name', default_value = None)
#		lastname = self.request.get('lastname', default_value = None)
#		children = self.request.get('children', default_value = None)
#		address = self.request.get('address', default_value = None)
#		side = self.request.get('side', default_value = None)
#		type = self.request.get('type', default_value = None)
#		invited = self.request.get('invited', default_value = None)
#		expected = self.request.get('expected', default_value = None)
#		rsvpstatus = self.request.get('rsvpstatus', default_value = None)
#		rsvpcount = self.request.get('rsvpcount', default_value = None)
#
#		if (not(name == None)):
#			guest.name = name
#		if (not(lastname == None)):
#			guest.lastname = lastname
#		if (not(children == None)):
#			guest.children = children
#		if (not(address == None)):
#			guest.address = address
#		if (not(side == None)):
#			guest.side = side
#		if (not(type == None)):
#			guest.type = type
#		if (not(invited == None)):
#			try:
#				guest.invited = int(invited)
#			except:
#				pass
#		if (not(expected == None)):
#			try:
#				guest.expected = int(expected)
#			except:
#				pass
#		if (not(rsvpstatus == None)):
#			guest.rsvpstatus = rsvpstatus
#		if (not(rsvpcount == None)):
#			try:
#				guest.rsvpcount = int(rsvpcount)
#			except:
#				pass
#
#		guest.put()
#		self.redirect('/wedding/guests')
#
#class Statistics(webapp.RequestHandler):
#	@loginRequired
#	def get(self):
#
#		guests = db.GqlQuery("SELECT * FROM Guest")
#
#		totalEntities = 0
#		totalExpected = 0
#		totalInvited = 0
#
#		rsvpPositiveEntities = 0
#		rsvpPositiveExpected = 0
#		rsvpPositiveCount = 0
#
#		rsvpNegativeEntities = 0
#		rsvpNegativeExpected = 0
#		rsvpNegativeCount = 0
#
#		nonRsvpEntities = 0
#		nonRsvpExpected = 0
#		nonRsvpInvited = 0
#
#		for guest in guests:
#
#			totalEntities += 1
#			totalExpected += guest.expected
#			totalInvited += guest.invited
#
#			if guest.rsvpstatus == "Yes":
#				if guest.rsvpcount == 0:
#					rsvpNegativeEntities += 1
#					rsvpNegativeExpected += guest.expected
#				else:
#					rsvpPositiveEntities += 1
#					rsvpPositiveCount += guest.rsvpcount
#					rsvpPositiveExpected += guest.expected
#			else:
#				nonRsvpEntities += 1
#				nonRsvpInvited += guest.invited
#				nonRsvpExpected += guest.expected
#
#		rsvpCount = rsvpPositiveCount + rsvpNegativeCount
#		rsvpExpected = rsvpPositiveExpected + rsvpNegativeExpected
#
#		template_values = {
#			'totalEntities': totalEntities,
#			'totalExpected': totalExpected,
#			'totalInvited': totalInvited,
#			'rsvpEntities': rsvpPositiveEntities + rsvpNegativeEntities,
#			'rsvpPositiveEntities': rsvpPositiveEntities,
#			'rsvpPositiveExpected': rsvpPositiveExpected,
#			'rsvpPositiveCount': rsvpPositiveCount,
#			'rsvpPositiveDiff': rsvpPositiveCount - rsvpPositiveExpected,
#			'rsvpNegativeEntities': rsvpNegativeEntities,
#			'rsvpNegativeExpected': rsvpNegativeExpected,
#			'rsvpNegativeCount': rsvpNegativeCount,
#			'rsvpNegativeDiff': rsvpNegativeCount - rsvpNegativeExpected,
#			'rsvpDiff': rsvpCount - rsvpExpected,
#			'nonRsvpEntities': nonRsvpEntities,
#			'nonRsvpExpected': nonRsvpExpected,
#			'nonRsvpInvited': nonRsvpInvited,
#			'currentExpected': rsvpCount + nonRsvpExpected,
#			'currentInvited': rsvpCount + nonRsvpInvited,
#		}
#
#		path = os.path.join(os.path.dirname(__file__), 'statistics.html')
#
#		self.response.out.write(template.render(path, template_values))

application = webapp.WSGIApplication(
	[
		('/', ProfilesPage),
		('/profiles', ProfilesPage),
		('/tweets/([^/]*)', TweetsPage),
		('/util/update', UpdatePage),
#		('/wedding/guests(?:\.xml)?', Guests),
#		('/wedding/guest/([^/]*)', GuestR),
#		('/wedding/guests/add', AddGuest),
#		('/wedding/statistics', Statistics),
	],
	debug=True)

def main():
	run_wsgi_app(application)

if __name__ == "__main__":
	main()
