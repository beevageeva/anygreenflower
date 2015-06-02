#import urllib

import webapp2,jinja2,os
from base_handler import *
from auth import login_required, admin_required

from google.appengine.ext import blobstore
from google.appengine.ext.blobstore import BlobInfo

class CheckBlobsHandler(BaseHandler):

	@admin_required
	def get(self):
		from product import ProductModel
		from video import VideoModel
		blobs = BlobInfo.all().fetch(500)
		blob_products = {}
		blob_videos = {}
		for blob in blobs:
			res = ProductModel.query().filter(ProductModel.imgBlobKey == blob.key()).fetch(1)
			if(res and len(res)>0):
				blob_products[blob] =  res[0]
			else:
				res1 = VideoModel.query().filter(VideoModel.videoBlobKey == blob.key()).fetch(1)
				print "res1"
				print res1
				if(res1 and len(res1)>0):
					blob_videos[blob] =  res1[0]


		template_values = {"blobs": blobs, "blob_products" : blob_products, "blob_videos" : blob_videos,  "session": self.session}
		template = JINJA_ENVIRONMENT.get_template('/check/blob/list.html')
		self.response.write(template.render(template_values))
    		



class CheckBlobDeleteHandler(BaseHandler):

	@admin_required
	def post(self):
		#need to urllib unquote, this comes in post param
		#blob_key= urllib.unquote(self.request.get("blob_key"))
		blob_key= self.request.get("blob_key")
		blob_info = blobstore.BlobInfo.get(blob_key)
		blob_info.delete()
		self.redirect('/check/blobs')

application = webapp2.WSGIApplication([
    ('/check/blobs', CheckBlobsHandler),
    ('/check/blob/delete', CheckBlobDeleteHandler),
], debug=True, config=session_config)
