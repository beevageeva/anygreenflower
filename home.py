import webapp2,jinja2,os
from base_handler import *


class MainPage(BaseHandler):

    def get(self):
			template = JINJA_ENVIRONMENT.get_template('home.html')
			self.response.write(template.render({"session": self.session}))


application = webapp2.WSGIApplication([
    ('/', MainPage),
], debug=True, config=session_config)
