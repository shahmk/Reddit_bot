#!/usr/bin/python3
import praw
import time
import json
import webbrowser
from peewee import *
from praw.errors import HTTPException, OAuthAppRequired
from tornado import gen, web
from tornado.ioloop import IOLoop
from tornado.httpserver import HTTPServer

db = SqliteDatabase('user.db')

class BaseModel(Model):
	class Meta:
		database = db

class User(BaseModel):
	username = CharField(unique=True)
	interests = TextField()

db.connect()
db.create_tables([User],safe=True)

def addUser(user, ints):
	User.create(username=user,interests=ints)

def updateInterest(user, ints):
	q = User.update(interests=ints).where(User.username==user)
	q.execute()

alreadySent = [] #store
waitTime = 60 #60 second wait time between refreshes
usersInterest = {}
user_agent = "PMInterestingLinks 0.2.0 by /u/brwnkid88"
r = praw.Reddit(user_agent = user_agent)

#This handles getting oauth token, or refreshing it
#credit goes to x89 on github https://github.com/x89/Shreddit/blob/master/get_secret.py
class Page(web.RequestHandler):
    def get(self):
        code = self.get_argument("code", default=None, strip=False)
        self.write("Success! Your code: %s<br> \
        It will now be appended to praw.ini and you \
                should be able to enjoy Shreddit without storing \
                your user / pass anywhere." % code)
        IOLoop.current().stop()
        self.login(code)

    def login(self, code):
        deets = r.get_access_information(code)
        print("oauth_refresh_token: %s" % deets['refresh_token'])
        r.set_access_credentials(**deets)
        with open('praw.ini', mode='a') as fh:
            fh.write('oauth_refresh_token = %s' % deets['refresh_token'])
            print("Refresh token written to praw.ini")

application = web.Application([(r"/", Page)])

try:
	r.refresh_access_information()
except HTTPException:
    url = r.get_authorize_url('uniqueKey', ['identity', 'privatemessages','read','vote','history'], True)
    try:
        print("Opening url: %s" % url)
        webbrowser.open(url, new=2)
    except NameError:
        warn('''Couldn't open URL: %s\n please do so manually''' % url)
    server = HTTPServer(application)
    server.listen(65010)
    IOLoop.current().start()

if r.user == None:
	print("Failed to log in. Something went wrong!")
else:
	print("Logged in as %s." % r.user)

subreddit = r.get_subreddit('all')

def loadUsers():
	print("Loading user database...")
	for user in User.select():
		print (user.username + ": " + user.interests)
		usersInterest[user.username] = json.loads(user.interests)

def checkMessages():
	for msg in r.get_unread(limit=None):
		usr = str(msg.author)
		subj = msg.subject.lower()
		text = msg.body.lower().split(',')
		if (subj == "stop"):
			if usr not in usersInterest:
				usersInterest[usr] = []
				addUser(usr,json.dumps(usersInterest[usr]))
			for word in text:
				print(usr + " removed " + word)
				usersInterest[usr].remove(word.strip(' ,.'))
				updateInterest(usr,json.dumps(usersInterest[usr]))
		elif(subj == "start"):
			if usr not in usersInterest:
				usersInterest[usr] = []
				addUser(usr,json.dumps(usersInterest[usr]))
			for word in text:
				print(usr + " added " + word)
				usersInterest[usr].append(word.strip(' ,.'))
				updateInterest(usr,json.dumps(usersInterest[usr]))
		elif(subj == "get"):
			message = "Your Subscribed to alerts for: \n"
			if usr in usersInterest:
				for i in usersInterest[usr]:
					message = message + i + "\n"
			else:
				message = "You aren't subscribed to any alerts"
			r.send_message(usr,'Subscriptions',message)
		msg.mark_as_read()

def sendPMs():
	for submission in subreddit.get_hot(limit=25):
		for user in usersInterest:
			has_interest =  any(word in submission.title.lower() for word in usersInterest[user])
			if  has_interest and (str(user) + submission.id) not in alreadySent :
				message = submission.title + "\n" + submission.url
				sub = 'Interest Alert'
				r.send_message(user,sub,message)
				print("Sent " + user + " a PM")
				alreadySent.append(str(user) + submission.id) 

#loads database if it's existing into local dictionary
loadUsers()

while True:
	print("running...")
	checkMessages()
	sendPMs()

  #purges read list if it starts to get too long. Should make this faster
	if len(alreadySent) > 500:
		print("purging...")
		alreadySent = alreadySent[-100:]
	#print("waiting...")
	time.sleep(waitTime) #checks every minute for updates to r/all
