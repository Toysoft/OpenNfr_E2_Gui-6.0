# -*- coding: utf-8 -*-
from Plugins.Extensions.MediaPortal.plugin import _
from Plugins.Extensions.MediaPortal.resources.imports import *

def google(self, data):
	stream_url = re.search('"fmt_stream_map".*?\|(.*?)\|', data, re.S)
	if stream_url:
		headers = '&Cookie=%s' % ','.join(['%s=%s' % (key, urllib.quote_plus(self.google_ck[key])) for key in self.google_ck])
		url = stream_url.group(1).replace("\u003d","=").replace("\u0026","&") + '#User-Agent='+mp_globals.player_agent+headers
		self._callback(url)
	else:
		self.stream_not_found()