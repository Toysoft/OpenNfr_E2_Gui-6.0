# -*- coding: utf-8 -*-
from Plugins.Extensions.MediaPortal.plugin import _
from Plugins.Extensions.MediaPortal.resources.imports import *
from Plugins.Extensions.MediaPortal.resources.messageboxext import MessageBoxExt

def nowvideo(self, data, url, ck):
	dataPost = {}
	r = re.findall('input type="hidden".*?name="(.*?)".*?value="(.*?)"', data, re.S)
	if r:
		for name, value in r:
			dataPost[name] = value
			dataPost['submit'] = 'submit'
		spezialagent = 'Mozilla/5.0 (Windows NT 10.0; WOW64; rv:53.0) Gecko/20100101 Firefox/53.0'
		getPage(url, method='POST', agent=spezialagent, cookies=ck, postdata=urlencode(dataPost), headers={'Content-Type':'application/x-www-form-urlencoded'}).addCallback(self.nowvideo_postData).addErrback(self.errorload)
	else:
		self.stream_not_found()
		

def nowvideo_postData(self, data):
	stream_url = re.findall('<source src="(.*?\.mp4)" type=\'video/mp4\'>', data)
	if stream_url:
		print stream_url
		self._callback(stream_url[-1])
	else:
		self.stream_not_found()