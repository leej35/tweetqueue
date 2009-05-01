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
	screenname = db.StringProperty()
	password   = db.StringProperty()
	fullname   = db.StringProperty()
	imageref   = db.StringProperty()
	lastupdate = db.DateTimeProperty()

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
		profile.screenname = self.request.get("screenname")
		profile.password = self.request.get("password")
		profile.fullname = self.request.get("screenname")
		profile.imageref = "http://static.twitter.com/images/default_profile_normal.png"
		profile.lastupdate = datetime.datetime.min
		profile.put()

		self.redirect('/profiles')

class ProfilePage(webapp.RequestHandler):
	def get(self, profileName):
		profile = db.GqlQuery("SELECT * FROM Profile WHERE screenname = :1", profileName).get()

		if self.request.get("mode", "") == "edit":

			template_values = {
					"profile": profile,
			}

			path = os.path.join(os.path.dirname(__file__), 'profile-edit.html')
			self.response.out.write(template.render(path, template_values))

		else:

			template_values = {
					"profile": profile,
			}
	
			path = os.path.join(os.path.dirname(__file__), 'profile.html')
			self.response.out.write(template.render(path, template_values))

	def post(self, profileName):
		profile = db.GqlQuery("SELECT * FROM Profile WHERE screenname = :1", profileName).get()

		if not self.request.get("Delete", default_value=None) == None:
			profile.delete()
			self.redirect('/profiles')
		else:
			profile.screenname = self.request.get("screenname")
			profile.password = self.request.get("password")
			profile.fullname = self.request.get("fullname")
			profile.imageref = self.request.get("imageref")
			profile.put()

			self.redirect('/' + profile.screenname)

class TweetsPage(webapp.RequestHandler):
	def get(self, profileName):
		profile = db.GqlQuery("SELECT * FROM Profile WHERE screenname = :1", profileName).get()

		if self.request.get("mode", "") == "add":

			template_values = {
					"profile": profile,
			}

			path = os.path.join(os.path.dirname(__file__), 'tweet-add.html')
			self.response.out.write(template.render(path, template_values))
		else:

			count = 10
			page = 1
			try:
				page = int(self.request.get("page", 1))
				if page < 1:
					page = 1
			except:
				page = 1
			offset = (page - 1) * count
	
			tweetsQuery = Tweet.all().filter("profile =", profile).filter("posted = ", False).order("date").fetch(count, offset=offset)
			tweets = [
					{
						"text": tweet.text,
						"key": str(tweet.key()),
						"date": {
							"readable": tweet.date.strftime("at %I:%M %p on %b %d, %Y"),
							"system": tweet.date.strftime("%Y-%m-%d %H:%M"),
						}
					}
					for tweet in tweetsQuery
			]

			template_values = {
					"profile": profile,
					"tweets": tweets,
					"page": page,
			}
	
			path = os.path.join(os.path.dirname(__file__), 'tweets.html')
			self.response.out.write(template.render(path, template_values))

	def post(self, profileName):
		profile = db.GqlQuery("SELECT * FROM Profile WHERE screenname = :1", profileName).get()

		tweet = Tweet(posted=False)
		tweet.profile = profile
		tweet.text = self.request.get("text")
		tweet.date = datetime.datetime.strptime(self.request.get("date"), "%Y-%m-%d %H:%M")
		tweet.posted = False
		tweet.put()

		self.redirect('/%s/tweets' % profile.screenname)

class RecentTweetsPage(webapp.RequestHandler):
	def get(self, profileName):
		profile = db.GqlQuery("SELECT * FROM Profile WHERE screenname = :1", profileName).get()

		count = 10
		page = 1
		try:
			page = int(self.request.get("page", 1))
			if page < 1:
				page = 1
		except:
			page = 1
		offset = (page - 1) * count

		tweetsQuery = Tweet.all().filter("profile =", profile).filter("posted = ", True).order("-date").fetch(count, offset=offset)
		tweets = [
				{
					"text": tweet.text,
					"key": str(tweet.key()),
					"date": {
						"readable": tweet.postedDate.strftime("at %I:%M %p on %b %d, %Y"),
						"system": tweet.postedDate.strftime("%Y-%m-%d %H:%M"),
					}
				}
				for tweet in tweetsQuery
		]

		template_values = {
				"profile": profile,
				"tweets": tweets,
				"page": page,
		}

		path = os.path.join(os.path.dirname(__file__), 'recenttweets.html')
		self.response.out.write(template.render(path, template_values))

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
			self.redirect('/%s/tweets' % tweet.profile.screenname)
		else:
			tweet.text = self.request.get("text")
			tweet.date = datetime.datetime.strptime(self.request.get("date"), "%Y-%m-%d %H:%M")
			tweet.put()
			self.redirect('/%s/tweets' + tweet.profile.screenname)

class UpdatePage(webapp.RequestHandler):
	def get(self):

		tweets = db.GqlQuery("SELECT * FROM Tweet WHERE date < :1 AND posted = :2 ORDER BY date", datetime.datetime.utcnow(), False)

		self.response.headers["Content-Type"] = "text/plain"

		url = "http://twitter.com/statuses/update.json"
		

		for tweet in tweets:
			self.response.out.write("Text: " + str(tweet.text) + "\n")
			self.response.out.write("Login: " + str(tweet.profile.screenname) + "\n")
			self.response.out.write("Password: " + str(tweet.profile.password) + "\n")
			self.response.out.write("Updated: " + str(tweet.postedDate) + "\n")
			try:
				encodedAuthentication = base64.encodestring(tweet.profile.screenname + ":" + tweet.profile.password).strip()
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
		('/([^/]*)', ProfilePage),
		('/([^/]*)/tweets', TweetsPage),
		('/([^/]*)/tweets/recent', RecentTweetsPage),
		('/tweet/([^/]*)', TweetPage),
		('/util/update', UpdatePage),
	],
	debug=True)

def main():
	run_wsgi_app(application)

if __name__ == "__main__":
	main()
