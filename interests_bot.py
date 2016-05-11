#!/usr/bin/python3
import praw
import time
import webbrowser
from praw.errors import HTTPException, OAuthAppRequired
from tornado import gen, web
from tornado.ioloop import IOLoop
from tornado.httpserver import HTTPServer

alreadySent = [] #store
waitTime = 60
interests = {}
user_agent = "PMInterestingLinks 0.0.1 by /u/brwnkid88"
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
while True:
    print("running...")

    for msg in r.get_unread(limit=None):
        subj = msg.subject.lower()
        text = msg.body.lower().split(',')
        if (subj == "stop"):
            for i in text:
                if i not in interests:
                    continue
                print("interest removed")
                interests[i].remove(msg.author)
        elif(subj== "start"):
            for i in text:
                if i not in interests:
                    interests[i] = set()
                print("interest added")
                interests[i].add(msg.author)
        msg.mark_as_read()

    for submission in subreddit.get_hot(limit=25):
        for word in interests:
            if word in submission.title.lower():
                message = submission.title + "\n" + submission.url
                for user in interests[word]:
                    if (str(user) + submission.id) not in alreadySent:
                        r.send_message(user, 'Alert', message)
                        print("PM Sent")
                        alreadySent.append(str(user) + submission.id)

    #puges read list if it starts to get too long. Should make this faster
    if len(alreadySent) > 500:
        print("purging...")
        alreadySent = alreadySent[-100:]
    print("waiting...")
    time.sleep(waitTime) #checks every minute for updates to r/all
