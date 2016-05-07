#!/usr/bin/env python
#
# Copyright 2007 Google Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
import webapp2
from google.appengine.api import mail
SENDER = 'TicTacToe admin <possible-arbor-125505@appspot.gserviceaccount.com>'


class MainHandler(webapp2.RequestHandler):
    """Default class that prints a simple hello world message"""
    def get(self):
        self.response.write('Hello world!')


class Mailer(webapp2.RequestHandler):
    """Send emails to players informing them about their move

    """
    def post(self):
    """Method to send email to player after a move from opponent has been 
    successfully recorded
    """
        message = mail.EmailMessage()
        message.to = self.request.POST['to']
        message.sender = SENDER
        message.subject = 'Your move pending in tictactoe !'
        message.body = "Your opponent just made their move. Your turn ! "
        if self.request.POST['state'] == "win":
            message.body += "Result: Game over ! %s wins" % self.request.POST['opponent']
        elif self.request.POST['state'] == "draw":
            message.body += "Result: Game drawn"
        else:
            message.body += "It is now your turn !"
        message.send()

app = webapp2.WSGIApplication([
    ('/SendMoveNotification', Mailer), ('/', MainHandler)
], debug=True)
