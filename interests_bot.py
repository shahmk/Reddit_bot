#!/usr/bin/python3
import praw
import time
import webbrowser
from praw.errors import HTTPException, OAuthAppRequired
from tornado import gen, web
from tornado.ioloop import IOLoop
from tornado.httpserver import HTTPServer

alreadyPMd = []

interests = ["elon", "musk", "tesla", "space x", "google", "facebook", "syria"]

user_agent = "test script by /u/brwnkid88"
r = praw.Reddit(user_agent = user_agent)

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
while True:
	for submission in subreddit.get_hot(limit=25):
		hasInterst = any(word in submission.title.lower() for word in interests)
		if submission.id not in alreadyPMd and hasInterst:
			message = submission.title + "\n" + submission.url
			r.send_message('brwnkid88', 'Alert', message)
			alreadyPMd.append(submission.id)

	for msg in r.get_unread(limit=None):
		subj = msg.subject.lower()
		text = msg.body.lower().split(',')
		if (subj == "stop"):
			for i in text:
				interests.remove(i)
		elif(subj== "start"):
			for i in text:
				interests.append(i)

	time.sleep(60) #checks every minute for updates to r/all
