# -*- coding: utf-8 -*-
from Plugins.Extensions.MediaPortal.plugin import _
from Plugins.Extensions.MediaPortal.resources.imports import *

def streamango(self, data):
	stream_url = re.findall('type:"video/mp4",src:"(//streamango.com.*?)"', data)
	if stream_url:
		url = 'http:'+stream_url[0]
		self._callback(url)
	else:
		self.stream_not_found()