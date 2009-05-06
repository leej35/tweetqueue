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

from django.utils import simplejson

import auth
import auth_controller
import auth_models

class Profile(db.Model):
	screenname = db.StringProperty()
	password   = db.StringProperty()
	fullname   = db.StringProperty()
	imageref   = db.StringProperty()
	lastupdate = db.DateTimeProperty()
	owner      = db.ReferenceProperty(auth_models.User)

class Tweet(db.Model):
	profile    = db.ReferenceProperty(Profile)
	text       = db.StringProperty()
	date       = db.DateTimeProperty()
	posted     = db.BooleanProperty(required=True)
	postedDate = db.DateTimeProperty()

class ProfilesPage(webapp.RequestHandler):

	@auth.authorizationRequired
	def get(self):
		profiles = db.GqlQuery("SELECT * FROM Profile")

		template_values = {
				"profiles": profiles,
		}

		path = os.path.join(os.path.dirname(__file__), 'profiles.html')
		self.response.out.write(template.render(path, template_values))

	@auth.authorizationRequired
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

	@auth.authorizationRequired
	def get(self, profileName):
		profile = db.GqlQuery("SELECT * FROM Profile WHERE screenname = :1", profileName).get()

		# We need this to associate profiles from older version that don't have owners
		#   with their new owners. Bad idea? Yes. Works? Yes.
		if profile.owner == None:
			profile.owner = self.request.authorized_user
			profile.put()

		if str(profile.owner.key()) != str(self.request.authorized_user.key()):
			auth.report_unauthorized(self.response, message="You are not the owner of this profile.")
			return

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

	@auth.authorizationRequired
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

	@auth.authorizationRequired
	def get(self, profileName):
		profile = db.GqlQuery("SELECT * FROM Profile WHERE screenname = :1", profileName).get()

		if self.request.get("mode", "") == "add":

			template_values = {
					"profile": profile,
			}

			path = os.path.join(os.path.dirname(__file__), 'tweet-add.html')
			self.response.out.write(template.render(path, template_values))
		else:

			count = 5
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
							"readable": tweet.date.strftime("at %I:%M %p (UTC) on %b %d, %Y"),
							"system": tweet.date.strftime("%Y-%m-%d %H:%M"),
						}
					}
					for tweet in tweetsQuery
			]

			template_values = {
					"profile": profile,
					"tweets": tweets,
			}

			if page > 1:
				template_values["prevpage"] = "/%s/tweets?page=%i" % (profile.screenname, page - 1)
	
			if len(tweets) == count:
				template_values["nextpage"] = "/%s/tweets?page=%i" % (profile.screenname, page + 1)
	
			path = os.path.join(os.path.dirname(__file__), 'tweets.html')
			self.response.out.write(template.render(path, template_values))

	@auth.authorizationRequired
	def post(self, profileName):
		profile = db.GqlQuery("SELECT * FROM Profile WHERE screenname = :1", profileName).get()

		if self.request.headers['Content-Type'] == 'application/json':
			input = {}
			try:
				input = simplejson.loads(self.request.body)
			except:
				self.response.set_status(400)
				self.response.headers['Content-Type'] = "text/plain"
				self.response.out.write("Cannot parse JSON")
				return

			def makeTweet(dict):
				tweet = Tweet(posted=False)
				tweet.profile = profile
				tweet.text = dict["text"]
				datestring = dict["date"]
				try:
					tweet.date = datetime.datetime.strptime(datestring, "%Y-%m-%d %H:%M")
				except:
					raise KeyError("date")
				tweet.posted = False
				tweet.put()

			if input.has_key("tweets"):
				for tweet in input["tweets"]:
					makeTweet(tweet)

			else:
				makeTweet(input)
		else:
			tweet = Tweet(posted=False)
			tweet.profile = profile
			tweet.text = self.request.get("text")
			tweet.date = datetime.datetime.strptime(self.request.get("date"), "%Y-%m-%d %H:%M")
			tweet.posted = False
			tweet.put()

		self.redirect('/%s/tweets' % profile.screenname)

class RecentTweetsPage(webapp.RequestHandler):

	@auth.authorizationRequired
	def get(self, profileName):
		profile = db.GqlQuery("SELECT * FROM Profile WHERE screenname = :1", profileName).get()

		count = 5
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
						"readable": tweet.postedDate.strftime("at %I:%M %p (UTC) on %b %d, %Y"),
						"system": tweet.postedDate.strftime("%Y-%m-%d %H:%M"),
					}
				}
				for tweet in tweetsQuery
		]

		template_values = {
				"profile": profile,
				"tweets": tweets,
		}

		if page > 1:
			template_values["prevpage"] = "/%s/tweets?page=%i" % (profile.screenname, page - 1)

		if len(tweets) == count:
			template_values["nextpage"] = "/%s/tweets?page=%i" % (profile.screenname, page + 1)

		path = os.path.join(os.path.dirname(__file__), 'recenttweets.html')
		self.response.out.write(template.render(path, template_values))

class TweetPage(webapp.RequestHandler):

	@auth.authorizationRequired
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

	@auth.authorizationRequired
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
		# User admin
		('/users', auth_controller.Users),
		('/user/([^/]*)', auth_controller.User),
		('/token-requests', auth_controller.TokenRequest),

		# The rest
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
