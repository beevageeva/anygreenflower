from google.appengine.ext import blobstore
from google.appengine.ext.webapp import blobstore_handlers
import webapp2,jinja2,urllib
from auth import login_required, admin_required
from base_handler import *

class DownloadHandler(BaseHandler, blobstore_handlers.BlobstoreDownloadHandler):
	@login_required
	def get(self, resource):
		resource = str(urllib.unquote(resource))
		blob_info = blobstore.BlobInfo.get(resource)
		self.send_blob(blob_info)

application = webapp2.WSGIApplication([
    ('/download/(.+)', DownloadHandler),
], debug=True, config=session_config)
