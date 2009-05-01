import base64
import cgi
import os

import datetime
import urllib

from google.appengine.api import urlfetch
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

		tweets = db.GqlQuery("SELECT * FROM Tweet WHERE profile = :1 AND posted = :2 ORDER BY date", profile, False)

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

class TweetPage(webapp.RequestHandler):
	def get(self, key):
		tweet = db.get(db.Key(key))

		template_values = {
				"profile": tweet.profile,
				"tweet": {
					"text": tweet.text,
					"key": str(tweet.key()),
					"date": tweet.date.strftime("%Y-%m-%d %H:%M"),
				},
		}

		path = os.path.join(os.path.dirname(__file__), 'tweet.html')
		self.response.out.write(template.render(path, template_values))

	def post(self, key):
		tweet = db.get(db.Key(key))

		if not self.request.get("Delete", default_value=None) == None:
			tweet.delete()
			self.redirect('/tweets/' + tweet.profile.name)
		else:
			tweet.text = self.request.get("text")
			tweet.date = datetime.datetime.strptime(self.request.get("date"), "%Y-%m-%d %H:%M")
			tweet.put()
			self.redirect('/tweets/' + tweet.profile.name)

class UpdatePage(webapp.RequestHandler):
	def get(self):

		tweets = db.GqlQuery("SELECT * FROM Tweet WHERE date < :1 AND posted = :2 ORDER BY date", datetime.datetime.utcnow(), False)

		self.response.headers["Content-Type"] = "text/plain"

		url = "http://twitter.com/statuses/update.json"
		

		for tweet in tweets:
			self.response.out.write("Text: " + str(tweet.text) + "\n")
			self.response.out.write("Login: " + str(tweet.profile.name) + "\n")
			self.response.out.write("Password: " + str(tweet.profile.password) + "\n")
			self.response.out.write("Updated: " + str(tweet.postedDate) + "\n")
			try:
				encodedAuthentication = base64.encodestring(tweet.profile.name + ":" + tweet.profile.password).strip()
				form_fields = {
	  				"status": tweet.text,
				}
				form_data = urllib.urlencode(form_fields)
				result = urlfetch.fetch(
						url = url,
						payload = form_data,
						method = urlfetch.POST,
						headers = {
							#'Content-Type': 'application/x-www-form-urlencoded',
							'Authorization': 'Basic ' + encodedAuthentication})
				if result.status_code == 200:
					tweet.posted = True
					tweet.postedDate = datetime.datetime.utcnow()
					tweet.put()
				else:
					self.response.out.write("FAILED! Code: " + str(result.status_code) + "\n")
					self.response.out.write(result.content + "\n")
			except Exception, e:
				self.response.out.write("FAILED! " + str(e) + "\n")
			self.response.out.write("\n")


application = webapp.WSGIApplication(
	[
		('/', ProfilesPage),
		('/profiles', ProfilesPage),
		('/tweets/([^/]*)', TweetsPage),
		('/tweet/([^/]*)', TweetPage),
		('/util/update', UpdatePage),
	],
	debug=True)

def main():
	run_wsgi_app(application)

if __name__ == "__main__":
	main()
