# -*- coding: utf-8 -*-
###############################################################################################
#
#    MediaPortal for Dreambox OS
#
#    Coded by MediaPortal Team (c) 2013-2017
#
#  This plugin is open source but it is NOT free software.
#
#  This plugin may only be distributed to and executed on hardware which
#  is licensed by Dream Property GmbH. This includes commercial distribution.
#  In other words:
#  It's NOT allowed to distribute any parts of this plugin or its source code in ANY way
#  to hardware which is NOT licensed by Dream Property GmbH.
#  It's NOT allowed to execute this plugin and its source code or even parts of it in ANY way
#  on hardware which is NOT licensed by Dream Property GmbH.
#
#  This applies to the source code as a whole as well as to parts of it, unless
#  explicitely stated otherwise.
#
#  If you want to use or modify the code or parts of it,
#  you have to keep OUR license and inform us about the modifications, but it may NOT be
#  commercially distributed other than under the conditions noted above.
#
#  As an exception regarding execution on hardware, you are permitted to execute this plugin on VU+ hardware
#  which is licensed by satco europe GmbH, if the VTi image is used on that hardware.
#
#  As an exception regarding modifcations, you are NOT permitted to remove
#  any copy protections implemented in this plugin or change them for means of disabling
#  or working around the copy protections, unless the change has been explicitly permitted
#  by the original authors. Also decompiling and modification of the closed source
#  parts is NOT permitted.
#
#  Advertising with this plugin is NOT allowed.
#  For other uses, permission from the authors is necessary.
#
###############################################################################################

from Plugins.Extensions.MediaPortal.plugin import _
from imports import *
import mp_globals
from keyboardext import VirtualKeyBoardExt
from userporn import Userporn
from packer import unpack, detect
from jsunpacker import cJsUnpacker
from debuglog import printlog as printl
from messageboxext import MessageBoxExt
from realdebrid import realdebrid_oauth2

try:
	import requests
except:
	requestsModule = False
else:
	requestsModule = True

# cookies
ck = {}
cj = {}
rdbcookies = {}
timeouttime = 15

def isSupportedHoster(linkOrHoster, check=False):
	if not check:
		return False
	if not linkOrHoster:
		return False

	printl("check hoster: %s" % linkOrHoster,'',"S")

	host = linkOrHoster.lower().strip()
	if re.search(mp_globals.hosters[0], host):
		printl("match1: %s" % linkOrHoster,'',"H")
		return True
	elif re.search(mp_globals.hosters[1], host):
		printl("match2: %s" % linkOrHoster,'',"H")
		return True

	printl("hoster not supported",'',"W")
	return False

class get_stream_link:

	# hosters
	from hosters.auengine import auengine
	from hosters.bestreams import bestreams, bestreamsCalllater, bestreamsPostData
	from hosters.bitshare import bitshare, bitshare_start
	from hosters.datoporn import datoporn
	from hosters.divxpress import divxpress, divxpressPostdata
	from hosters.epornik import epornik
	from hosters.exashare import exashare
	from hosters.flyflv import flyflv, flyflvData
	from hosters.google import google
	from hosters.kodik import kodik, kodikData
	from hosters.letwatch import letwatch
	from hosters.mailru import mailru
	from hosters.mega3x import mega3x
	from hosters.movshare import movshare, movshare_code1, movshare_base36decode, movshare_xml
	from hosters.mp4upload import mp4upload
	from hosters.nowvideo import nowvideo, nowvideo_postData
	from hosters.okru import okru
	from hosters.openload import openloadApi
	from hosters.powvideo import powvideo
	from hosters.promptfile import promptfile, promptfilePost
	from hosters.rapidvideo import rapidvideo
	from hosters.rapidvideocom import rapidvideocom
	from hosters.streamango import streamango
	from hosters.streamin import streamin
	from hosters.trollvid import trollvid
	from hosters.uptostream import uptostream
	from hosters.videonest import videonest
	from hosters.videowood import videowood
	from hosters.vidlox import vidlox
	from hosters.vidspot import vidspot
	from hosters.vidwoot import vidwoot
	from hosters.vivo import vivo
	from hosters.vkme import vkme, vkmeHash, vkmeHashGet, vkmeHashData, vkPrivat, vkPrivatData
	from hosters.vidoza import vidoza
	from hosters.vidto import vidto
	from hosters.vidzi import vidzi
	from hosters.watchers import watchers
	from hosters.yourupload import yourupload
	from hosters.youwatch import youwatch, youwatchLink
	from.hosters.zstream import zstream

	def __init__(self, session):
		self._callback = None
		self.session = session
		useProxy = config.mediaportal.premiumize_use.value
		self.puser = config.mediaportal.premiumize_username.value
		self.ppass = config.mediaportal.premiumize_password.value
		self.papiurl = "https://api.premiumize.me/pm-api/v1.php?method=directdownloadlink&params[login]=%s&params[pass]=%s&params[link]=" % (self.puser, self.ppass)
		self.rdb = 0
		self.prz = 0
		self.fallback = False

	def grabpage(self, pageurl, method='GET', postdata={}):
		if requestsModule:
			try:
				import urlparse
				s = requests.session()
				url = urlparse.urlparse(pageurl)
				if method == 'GET':
					page = s.get(url.geturl())
				elif method == 'POST':
					page = s.post(url.geturl(), data=postdata)
				return page.content
			except:
				return "error"
		else:
			return "error"

	def callPremium(self, link):
		if self.prz == 1 and config.mediaportal.premiumize_use.value:
			r_getPage(self.papiurl+link).addCallback(self.papiCallback, link).addErrback(self.errorload)
		elif self.rdb == 1 and config.mediaportal.realdebrid_use.value:
			self.session.openWithCallback(self.rapiCallback, realdebrid_oauth2, str(link))

	def callPremiumYT(self, link, val):
		if val == "prz":
			r_getPage(self.papiurl+link).addCallback(self.papiCallback, link).addErrback(self.errorload)
		if val == "rdb":
			self.session.openWithCallback(self.rapiCallback, realdebrid_oauth2, str(link))

	def rapiCallback(self, stream_url, link):
		if stream_url:
				mp_globals.realdebrid = True
				mp_globals.premiumize = False
				self._callback(stream_url)
		elif self.prz == 1 and config.mediaportal.premiumize_use.value:
			self.rdb = 0
			r_getPage(self.papiurl+link).addCallback(self.papiCallback, link).addErrback(self.errorload)
		else:
			self.fallback = True
			self.check_link(self.link, self._callback)

	def papiCallback(self, data, link):
		if re.search('status":200', data):
			stream_url = re.findall('"stream_location":"(.*?)"', data, re.S|re.I)
			if not stream_url:
				stream_url = re.findall('"location":"(.*?)"', data, re.S|re.I)
			if stream_url:
				mp_globals.premiumize = True
				mp_globals.realdebrid = False
				self._callback(stream_url[0].replace('\\',''))
			else:
				self.fallback = True
				self.check_link(self.link, self._callback)
		elif self.rdb == 1 and config.mediaportal.realdebrid_use.value:
			self.prz = 0
			self.session.openWithCallback(self.rapiCallback, realdebrid_oauth2, str(link))
		else:
			if re.search('status":400', data):
				self.session.openWithCallback(self.papiCallback2, MessageBoxExt, _("premiumize: No valid link."), MessageBoxExt.TYPE_INFO, timeout=3)
			elif re.search('status":401', data):
				self.session.openWithCallback(self.papiCallback2, MessageBoxExt, _("premiumize: Login failed."), MessageBoxExt.TYPE_INFO, timeout=3)
			elif re.search('status":402', data):
				self.session.openWithCallback(self.papiCallback2, MessageBoxExt, _("premiumize: You are no Premium-User."), MessageBoxExt.TYPE_INFO, timeout=3)
			elif re.search('status":403', data):
				self.session.openWithCallback(self.papiCallback2, MessageBoxExt, _("premiumize: No Access."), MessageBoxExt.TYPE_INFO, timeout=3)
			elif re.search('status":404', data):
				self.session.openWithCallback(self.papiCallback2, MessageBoxExt, _("premiumize: File not found."), MessageBoxExt.TYPE_INFO, timeout=3)
			elif re.search('status":428', data):
				self.session.openWithCallback(self.papiCallback2, MessageBoxExt, _("premiumize: Hoster currently not available."), MessageBoxExt.TYPE_INFO, timeout=3)
			elif re.search('status":502', data):
				self.session.openWithCallback(self.papiCallback2, MessageBoxExt, _("premiumize: Unknown technical error."), MessageBoxExt.TYPE_INFO, timeout=3)
			elif re.search('status":503', data):
				self.session.openWithCallback(self.papiCallback2, MessageBoxExt, _("premiumize: Temporary technical error."), MessageBoxExt.TYPE_INFO, timeout=3)
			elif re.search('status":509', data):
				self.session.openWithCallback(self.papiCallback2, MessageBoxExt, _("premiumize: Fair use limit exhausted."), MessageBoxExt.TYPE_INFO, timeout=3)
			else:
				self.papiCallback2(True)

	def papiCallback2(self, answer):
		self.fallback = True
		self.check_link(self.link, self._callback)

	def check_link(self, data, got_link):
		self._callback = got_link
		self.link = data
		if data:
			if re.search("http://streamcloud.eu/", data, re.S):
				link = data
				if config.mediaportal.premiumize_use.value and not self.fallback:
					link = re.search("(http://streamcloud.eu/\w+)", data, re.S)
					if link:
						link = link.group(1)
					self.rdb = 0
					self.prz = 1
					self.callPremium(link)
				else:
					spezialagent = 'Mozilla/5.0 (Windows NT 10.0; WOW64; rv:53.0) Gecko/20100101 Firefox/53.0'
					getPage(link, cookies=ck, agent=spezialagent).addCallback(self.streamcloud).addErrback(self.errorload)

			elif re.search('rapidgator.net|rg.to', data, re.S):
				link = data
				if (config.mediaportal.premiumize_use.value or config.mediaportal.realdebrid_use.value) and not self.fallback:
					self.rdb = 1
					self.prz = 1
					self.callPremium(link)
				else:
					self.only_premium()

			elif re.search('turbobit.net', data, re.S):
				link = data
				if (config.mediaportal.premiumize_use.value or config.mediaportal.realdebrid_use.value) and not self.fallback:
					self.rdb = 1
					self.prz = 1
					self.callPremium(link)
				else:
					self.only_premium()

			elif re.search('4shared.com', data, re.S):
				link = data
				if config.mediaportal.realdebrid_use.value and not self.fallback:
					self.rdb = 1
					self.prz = 0
					self.callPremium(link)
				else:
					self.only_premium()

			elif re.search('uplea.com', data, re.S):
				link = data
				if (config.mediaportal.premiumize_use.value or config.mediaportal.realdebrid_use.value) and not self.fallback:
					self.rdb = 1
					self.prz = 1
					self.callPremium(link)
				else:
					self.only_premium()

			elif re.search('vimeo.com', data, re.S):
				link = data
				if (config.mediaportal.premiumize_use.value or config.mediaportal.realdebrid_use.value) and not self.fallback:
					self.rdb = 1
					self.prz = 1
					self.callPremium(link)
				else:
					self.only_premium()

			elif re.search('uptobox.com', data, re.S):
				link = data
				if (config.mediaportal.premiumize_use.value or config.mediaportal.realdebrid_use.value) and not self.fallback:
					self.rdb = 1
					self.prz = 1
					self.callPremium(link)
				else:
					self.only_premium()

			elif re.search('filerio.com|filerio.in', data, re.S):
				link = data
				if config.mediaportal.realdebrid_use.value and not self.fallback:
					self.rdb = 1
					self.prz = 0
					self.callPremium(link)
				else:
					self.only_premium()

			elif re.search('depfile.com', data, re.S):
				link = data
				if (config.mediaportal.premiumize_use.value or config.mediaportal.realdebrid_use.value) and not self.fallback:
					self.rdb = 1
					self.prz = 1
					self.callPremium(link)
				else:
					self.only_premium()

			elif re.search('filer.net', data, re.S):
				link = data
				if config.mediaportal.premiumize_use.value and not self.fallback:
					self.rdb = 0
					self.prz = 1
					self.callPremium(link)
				else:
					self.only_premium()

			elif re.search('extmatrix.com', data, re.S):
				link = data
				if config.mediaportal.realdebrid_use.value and not self.fallback:
					self.rdb = 1
					self.prz = 0
					self.callPremium(link)
				else:
					self.only_premium()

			elif re.search('mediafire.com', data, re.S):
				link = data
				if (config.mediaportal.premiumize_use.value or config.mediaportal.realdebrid_use.value) and not self.fallback:
					self.rdb = 1
					self.prz = 1
					self.callPremium(link)
				else:
					self.only_premium()

			elif re.search('filefactory.com', data, re.S):
				link = data
				if (config.mediaportal.premiumize_use.value or config.mediaportal.realdebrid_use.value) and not self.fallback:
					self.rdb = 1
					self.prz = 1
					self.callPremium(link)
				else:
					self.only_premium()

			elif re.search('gigapeta.com', data, re.S):
				link = data
				if config.mediaportal.realdebrid_use.value and not self.fallback:
					self.rdb = 1
					self.prz = 0
					self.callPremium(link)
				else:
					self.only_premium()

			elif re.search('salefiles.com', data, re.S):
				link = data
				if (config.mediaportal.premiumize_use.value or config.mediaportal.realdebrid_use.value) and not self.fallback:
					self.rdb = 1
					self.prz = 1
					self.callPremium(link)
				else:
					self.only_premium()

			elif re.search('uploadable.ch|bigfile.to', data, re.S):
				link = data
				if (config.mediaportal.premiumize_use.value or config.mediaportal.realdebrid_use.value) and not self.fallback:
					self.rdb = 1
					self.prz = 1
					self.callPremium(link)
				else:
					self.only_premium()

			elif re.search('uploadrocket.net', data, re.S):
				link = data
				if config.mediaportal.realdebrid_use.value and not self.fallback:
					self.rdb = 1
					self.prz = 0
					self.callPremium(link)
				else:
					self.only_premium()

			elif re.search('oboom.com', data, re.S):
				link = data
				if config.mediaportal.realdebrid_use.value and not self.fallback:
					self.rdb = 1
					self.prz = 0
					self.callPremium(link)
				else:
					self.only_premium()

			elif re.search('uploaded.net|uploaded.to|ul.to', data, re.S):
				link = data
				if (config.mediaportal.premiumize_use.value or config.mediaportal.realdebrid_use.value) and not self.fallback:
					self.rdb = 1
					self.prz = 1
					self.callPremium(link)
				else:
					self.only_premium()

			elif re.search('youtube.com', data, re.S):
				link = data
				if (config.mediaportal.premiumize_use.value or config.mediaportal.realdebrid_use.value) and not self.fallback:
					self.rdb = 1
					self.prz = 1
					if config.mediaportal.sp_use_yt_with_proxy.value == "rdb":
						self.callPremiumYT(link, "rdb")
					if config.mediaportal.sp_use_yt_with_proxy.value == "prz":
						self.callPremiumYT(link, "prz")
				else:
					self.only_premium()

			elif re.search('bangbrothers.net', data, re.S):
				link = data
				if config.mediaportal.premiumize_use.value and not self.fallback:
					self.rdb = 0
					self.prz = 1
					self.callPremium(link)
				else:
					self.only_premium()

			elif re.search('brazzers.com', data, re.S):
				link = data
				if config.mediaportal.premiumize_use.value and not self.fallback:
					self.rdb = 0
					self.prz = 1
					self.callPremium(link)
				else:
					self.only_premium()

			elif re.search('teamskeet.com', data, re.S):
				link = data
				if config.mediaportal.premiumize_use.value and not self.fallback:
					self.rdb = 0
					self.prz = 1
					self.callPremium(link)
				else:
					self.only_premium()

			elif re.search('naughtyamerica.com', data, re.S):
				link = data
				if config.mediaportal.premiumize_use.value and not self.fallback:
					self.rdb = 0
					self.prz = 1
					self.callPremium(link)
				else:
					self.only_premium()

			elif re.search('wicked.com', data, re.S):
				link = data
				if config.mediaportal.premiumize_use.value and not self.fallback:
					self.rdb = 0
					self.prz = 1
					self.callPremium(link)
				else:
					self.only_premium()

			elif re.search('digitalplayground.com', data, re.S):
				link = data
				if config.mediaportal.premiumize_use.value and not self.fallback:
					self.rdb = 0
					self.prz = 1
					self.callPremium(link)
				else:
					self.only_premium()

			elif re.search('mofos.com', data, re.S):
				link = data
				if config.mediaportal.premiumize_use.value and not self.fallback:
					self.rdb = 0
					self.prz = 1
					self.callPremium(link)
				else:
					self.only_premium()

			elif re.search('realitykings.com', data, re.S):
				link = data
				if config.mediaportal.premiumize_use.value and not self.fallback:
					self.rdb = 0
					self.prz = 1
					self.callPremium(link)
				else:
					self.only_premium()

			elif re.search('1fichier.com', data, re.S):
				link = data
				if (config.mediaportal.premiumize_use.value or config.mediaportal.realdebrid_use.value) and not self.fallback:
					self.rdb = 1
					self.prz = 1
					self.callPremium(link)
				else:
					self.only_premium()

			elif re.search('letitbit.net', data, re.S):
				link = data
				if config.mediaportal.realdebrid_use.value and not self.fallback:
					self.rdb = 1
					self.prz = 0
					self.callPremium(link)
				else:
					self.only_premium()

			elif re.search('nowvideo', data, re.S):
				if re.search('embed.nowvideo.', data, re.S):
					ID = re.search('http://embed.nowvideo.\w+/embed.php.*?[\?|&]v=(\w+)', data, re.S)
					if ID:
						data = 'http://www.nowvideo.sx/video/' + ID.group(1)
				link = data.replace('nowvideo.to','nowvideo.sx')
				if (config.mediaportal.premiumize_use.value or config.mediaportal.realdebrid_use.value) and not self.fallback:
					self.rdb = 1
					self.prz = 1
					self.callPremium(link)
				else:
					spezialagent = 'Mozilla/5.0 (Windows NT 10.0; WOW64; rv:53.0) Gecko/20100101 Firefox/53.0'
					getPage(link, agent=spezialagent, cookies=ck).addCallback(self.nowvideo, link, ck).addErrback(self.errorload)

			elif re.search('videoweed.es', data, re.S):
				link = data
				if (config.mediaportal.premiumize_use.value or config.mediaportal.realdebrid_use.value) and not self.fallback:
					self.rdb = 1
					self.prz = 1
					self.callPremium(link)
				else:
					ID = re.search('http://(www\.|embed\.|)videoweed.es/(?:mobile/video\.php\?id=|video/|file/|embed\.php\?.*?v=)([0-9a-z]+)', link)
					if ID:
						link = 'http://embed.videoweed.es/embed/?v=%s' % ID.group(2)
					getPage(link).addCallback(self.movshare, link, "videoweed").addErrback(self.errorload)

			elif re.search('novamov.com', data, re.S):
				link = data
				if (config.mediaportal.premiumize_use.value or config.mediaportal.realdebrid_use.value) and not self.fallback:
					self.rdb = 1
					self.prz = 1
					self.callPremium(link)
				else:
					ID = re.search('http://(www\.|embed\.|)novamov.com/(?:mobile/video\.php\?id=|video/|file/|embed\.php\?.*?v=)([0-9a-z]+)', link)
					if ID:
						link = 'http://embed.novamov.com/embed/?v=%s' % ID.group(2)
					getPage(link).addCallback(self.movshare, link, "novamov").addErrback(self.errorload)

			elif re.search('movshare.net|wholecloud.net', data, re.S):
				link = data.replace('movshare.net','wholecloud.net')
				if (config.mediaportal.premiumize_use.value or config.mediaportal.realdebrid_use.value) and not self.fallback:
					self.rdb = 1
					self.prz = 1
					self.callPremium(link)
				else:
					ID = re.search('http://(www\.|embed\.|)wholecloud.net/(?:mobile/video\.php\?id=|video/|file/|embed\.php\?.*?v=)([0-9a-z]+)', link)
					if ID:
						link = 'http://embed.wholecloud.net/embed/?v=%s' % ID.group(2)
					getPage(link).addCallback(self.movshare, link, "wholecloud").addErrback(self.errorload)

			elif re.search('auroravid.to', data, re.S):
				link = data
				if (config.mediaportal.premiumize_use.value or config.mediaportal.realdebrid_use.value) and not self.fallback:
					self.rdb = 1
					self.prz = 1
					self.callPremium(link)
				else:
					self.only_premium()

			elif re.search('bitvid.sx', data, re.S):
				link = data
				if (config.mediaportal.premiumize_use.value or config.mediaportal.realdebrid_use.value) and not self.fallback:
					self.rdb = 1
					self.prz = 1
					self.callPremium(link)
				else:
					self.only_premium()

			elif re.search('http://.*?bitshare.com', data, re.S):
				link = data
				getPage(link).addCallback(self.bitshare).addErrback(self.errorload)

			elif re.search('http://xvidstage.com', data, re.S):
				link = data
				getPage(link).addCallback(self.xvidstage_post, link).addErrback(self.errorload)

			elif re.search('epornik.com/', data, re.S):
				link = data
				getPage(link).addCallback(self.epornik).addErrback(self.errorload)

			elif re.search('(divxstage|cloudtime)', data, re.S):
				link = data
				if (config.mediaportal.premiumize_use.value or config.mediaportal.realdebrid_use.value) and not self.fallback:
					self.rdb = 1
					self.prz = 1
					self.callPremium(link)
				else:
					getPage(link).addCallback(self.movshare, link, "cloudtime").addErrback(self.errorload)

			elif re.search('flashx.tv|flashx.pw', data, re.S):
				link = data
				id = re.search('flashx.(tv|pw)/(embed-|dl\?|fxplay-|embed.php\?c=|)(\w+)', data)
				if id:
					link = "https://www.flashx.tv/%s.html" % id.group(3)
				if config.mediaportal.premiumize_use.value and not self.fallback:
					self.rdb = 0
					self.prz = 1
					self.callPremium(link)
				else:
					self.only_premium()

			elif re.search('userporn.com', data, re.S):
				link = data
				self.userporn_tv(link)

			elif re.search('ecostream.tv', data, re.S):
				link = data
				getPage(link, cookies=ck).addCallback(self.eco_read, link).addErrback(self.errorload)

			elif re.search('vk.com|vk.me', data, re.S):
				link = data
				getPage(link).addCallback(self.vkme, link).addErrback(self.errorload)

			elif re.search('mightyupload.com/embed', data, re.S):
				link = data
				getPage(link, timeout=timeouttime).addCallback(self.mightyupload).addErrback(self.errorload)

			elif re.search('mightyupload.com', data, re.S):
				link = data
				id = link.split('/')
				url = "http://www.mightyupload.com/embed-%s.html" % id[3]
				getPage(url, timeout=timeouttime).addCallback(self.mightyupload).addErrback(self.errorload)

			elif re.search('http://youwatch.org', data, re.S):
				link = data
				if (config.mediaportal.premiumize_use.value or config.mediaportal.realdebrid_use.value) and not self.fallback:
					self.rdb = 1
					self.prz = 0
					self.callPremium(link)
				else:
					id = link.split('org/')
					url = "http://youwatch.org/embed-%s.html" % id[1]
					getPage(url).addCallback(self.youwatch).addErrback(self.errorload)

			elif re.search('allmyvideos.net', data, re.S):
				link = data
				if re.search('allmyvideos.net/embed', link, re.S):
					getPage(link).addCallback(self.allmyvids).addErrback(self.errorload)
				else:
					id = re.findall('allmyvideos.net/(.*?)$', link)
					if id:
						new_link = "http://allmyvideos.net/embed-%s.html" % id[0]
						getPage(new_link).addCallback(self.allmyvids).addErrback(self.errorload)
					else:
						self.stream_not_found()

			elif re.search('promptfile.com', data, re.S):
				link = data
				if config.mediaportal.realdebrid_use.value and not self.fallback:
					self.rdb = 1
					self.prz = 0
					self.callPremium(link)
				else:
					twAgentGetPage(link, agent=None, headers=std_headers).addCallback(self.promptfile, link).addErrback(self.errorload)

			elif re.search("http://shared.sx", data, re.S):
				link = data
				getPage(link).addCallback(self.sharedsxData, link).addErrback(self.errorload)

			elif re.search("auengine.com", data, re.S):
				link = data
				getPage(link).addCallback(self.auengine).addErrback(self.errorload)

			elif re.search("mp4upload.com", data, re.S):
				link = data
				getPage(link).addCallback(self.mp4upload).addErrback(self.errorload)

			elif re.search("videonest.net", data, re.S):
				link = data
				getPage(link).addCallback(self.videonest).addErrback(self.errorload)

			elif re.search("mega3x.com|mega3x.net", data, re.S):
				link = data
				getPage(link).addCallback(self.mega3x).addErrback(self.errorload)

			elif re.search("dato.porn|datoporn.co", data, re.S):
				link = data
				getPage(link).addCallback(self.datoporn).addErrback(self.errorload)

			elif re.search("uptostream.com", data, re.S):
				link = data
				getPage(link).addCallback(self.uptostream).addErrback(self.errorload)

			elif re.search("vidwoot.com", data, re.S):
				link = data
				getPage(link).addCallback(self.vidwoot).addErrback(self.errorload)

			elif re.search("yourupload.com", data, re.S):
				link = data
				getPage(link).addCallback(self.yourupload).addErrback(self.errorload)

			elif re.search("trollvid.net", data, re.S):
				link = data
				getPage(link).addCallback(self.trollvid).addErrback(self.errorload)

			elif re.search("flyflv\.com", data, re.S):
				link = data
				getPage(link).addCallback(self.flyflv).addErrback(self.errorload)

			elif re.search("videowood\.tv", data, re.S):
				link = data
				if re.search('videowood\.tv/embed', data, re.S):
					link = data
				else:
					id = re.search('videowood\.tv/.*?/(\w+)', data)
					if id:
						link = "http://videowood.tv/embed/%s" % id.group(1)
				getPage(link).addCallback(self.videowood).addErrback(self.errorload)

			elif re.search("streamin\.to", data, re.S):
				if re.search('streamin\.to/embed', data, re.S):
					link = data
				else:
					data = data.replace('http://','')
					id = data.split('/')[1]
					if id:
						link = "http://streamin.to/embed-%s-640x360.html" % id
				if config.mediaportal.realdebrid_use.value and not self.fallback:
					link = data
					self.rdb = 1
					self.prz = 0
					self.callPremium(link)
				else:
					spezialagent = 'Mozilla/5.0 (Linux; Android 4.4; Nexus 5 Build/BuildID) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/30.0.0.0 Mobile Safari/537.36'
					getPage(link, cookies=ck, agent=spezialagent).addCallback(self.streamin).addErrback(self.errorload)

			elif re.search("vivo.sx", data, re.S):
				link = data.replace('http:','https:')
				if config.mediaportal.premiumize_use.value and not self.fallback:
					self.rdb = 0
					self.prz = 1
					self.callPremium(link)
				else:
					if mp_globals.isDreamOS or not mp_globals.requests:
						twAgentGetPage(link).addCallback(self.vivo, link).addErrback(self.errorload)
					else:
						data = self.grabpage(link)
						if data == "error":
							message = self.session.open(MessageBoxExt, _("Mandatory Python module python-requests is missing!"), MessageBoxExt.TYPE_ERROR)
						else:
							self.vivo(data, link)

			elif re.search('bestreams\.net/', data, re.S):
				link = data
				getPage(link, cookies=ck, headers={'Accept-Language': 'en-US,en;q=0.5'}).addCallback(self.bestreams, link, ck).addErrback(self.errorload)

			elif re.search('vidto\.me/', data, re.S):
				# http://vidto.me/embed-u1etw7z2o50u-640x360.html
				if re.search('vidto\.me/embed-', data, re.S):
					link = data
				else:
					id = re.search('vidto\.me/(\w+)', data)
					if id:
						link = "http://vidto.me/embed-%s-640x360.html" % id.group(1)
				if config.mediaportal.premiumize_use.value and not self.fallback:
					self.rdb = 0
					self.prz = 1
					self.callPremium(link)
				else:
					ck.update({'referer':'%s' % link })
					getPage(link, cookies=ck).addCallback(self.vidto).addErrback(self.errorload)


			elif re.search('vidoza\.net/', data, re.S):
				link = data.replace('https','http')
				getPage(link).addCallback(self.vidoza).addErrback(self.errorload)

			elif re.search('vidspot\.net/', data, re.S):
				if re.search('vidspot\.net/embed', data, re.S):
					link = data
				else:
					id = re.findall('vidspot\.net/(.*?)$', data)
					if id:
						link = "http://vidspot.net/embed-%s.html" % id[0]
				getPage(link).addCallback(self.vidspot).addErrback(self.errorload)

			elif re.search('kodik\.biz/', data, re.S):
				link = data
				getPage(link).addCallback(self.kodik).addErrback(self.errorload)

			elif re.search('(docs|drive)\.google\.com/|youtube\.googleapis\.com|googleusercontent.com', data, re.S):
				print "1"
				if 'youtube.googleapis.com' in data:
					docid = re.search('docid=([\w]+)', data)
					link = 'https://drive.google.com/file/d/%s/edit' % docid.groups(1)
				else:
					link = data
				mp_globals.player_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36'
				self.google_ck = {}
				if "googleusercontent.com" in link:
					import requests
					s = requests.session()
					page = s.head(link, allow_redirects=False)
					link = page.headers['Location']
					self.google_ck = requests.utils.dict_from_cookiejar(s.cookies)
					headers = '&Cookie=%s' % ','.join(['%s=%s' % (key, urllib.quote_plus(self.google_ck[key])) for key in self.google_ck])
					url = link.replace("\u003d","=").replace("\u0026","&") + '#User-Agent='+mp_globals.player_agent+headers
					self._callback(url)
				else:
					getPage(link, agent=mp_globals.player_agent, cookies=self.google_ck).addCallback(self.google).addErrback(self.errorload)

			elif re.search('rapidvideo\.ws', data, re.S):
				if re.search('rapidvideo\.ws/embed', data, re.S):
					link = data
				else:
					id = re.findall('rapidvideo\.ws/(.*?)$', data)
					if id:
						link = "http://rapidvideo.ws/embed-%s.html" % id[0]
				if config.mediaportal.premiumize_use.value and not self.fallback:
					if id:
						link = "http://rapidvideo.ws/%s" % id[0]
					self.rdb = 0
					self.prz = 1
					self.callPremium(link)
				else:
					getPage(link).addCallback(self.rapidvideo).addErrback(self.errorload)

			elif re.search('rapidvideo\.com', data, re.S):
				if re.search('rapidvideo\.com/(embed|e)/', data, re.S):
					link = data
				else:
					id = re.findall('rapidvideo\.com/v/(.*?)$', data)
					if id:
						link = "http://rapidvideo.com/embed/%s" % id[0]
				getPage(link).addCallback(self.rapidvideocom).addErrback(self.errorload)

			elif re.search('vid\.gg|vidgg\.to', data, re.S):
				data = data.replace('vid.gg','vidgg.to')
				if re.search('vidgg\.to/embed', data, re.S):
					link = data
				else:
					id = re.findall('vidgg\.to/video/(.*?)$', data)
					if id:
						link = "http://www.vidgg\.to/embed/?id=%s" % id[0]
				getPage(link).addCallback(self.movshare, link, "vidgg").addErrback(self.errorload)

			elif re.search('openload', data, re.S):
				link = data
				id = re.search('http[s]?://openload\...\/[^/]+\/(.*?)(\/.*?)?$', link, re.S)
				if id:
					link = 'https://openload.co/embed/' + id.group(1)
				if (config.mediaportal.premiumize_use.value or config.mediaportal.realdebrid_use.value) and not self.fallback:
					self.rdb = 1
					self.prz = 1
					self.callPremium(link)
				else:
					link = "https://api.openload.co/1/streaming/get?file=" + id.group(1)
					getPage(link).addCallback(self.openloadApi).addErrback(self.errorload)

			elif re.search('thevideo\.me', data, re.S):
				if (config.mediaportal.premiumize_use.value or config.mediaportal.realdebrid_use.value) and not self.fallback:
					if (re.search('thevideo\.me/embed-', data, re.S) or re.search('640x360.html', data, re.S)):
						id = re.findall('thevideo\.me/(?:embed-|)(.*?)(?:\.html|-\d+x\d+\.html)', data)
						if id:
							link = "https://www.thevideo.me/%s" % id[0]
					else:
						link = data
					self.rdb = 1
					self.prz = 1
					self.callPremium(link)
				else:
					self.only_premium()

			elif re.search('exashare\.com', data, re.S):
				if re.search('exashare\.com/embed-', data, re.S):
					link = data
				else:
					id = re.findall('exashare\.com/(.*?)$', data)
					if id:
						link = "http://www.exashare.com/embed-%s-620x330.html" % id[0]
				getPage(link).addCallback(self.exashare).addErrback(self.errorload)

			elif re.search('letwatch\.us|letwatch\.to', data, re.S):
				data = data.replace('letwatch.to','letwatch.us')
				if re.search('letwatch\.us/embed-', data, re.S):
					link = data
				else:
					id = re.findall('letwatch\.us/(.*?)$', data)
					if id:
						link = "http://letwatch.us/embed-%s-640x360.html" % id[0]
				getPage(link).addCallback(self.letwatch).addErrback(self.errorload)

			elif re.search('powvideo\.net/', data, re.S):
				id = re.search('powvideo\.net/(embed-|)(\w+)', data)
				if id:
					referer = "http://powvideo.net/embed-%s-954x562.html" % id.group(2)
					link = "http://powvideo.net/iframe-%s-954x562.html" % id.group(2)
					getPage(link, headers={'Referer':referer, 'Accept-Language': 'en-US,en;q=0.5'}).addCallback(self.powvideo).addErrback(self.errorload)

			elif re.search('divxpress\.com', data, re.S):
				if re.search('divxpress\.com/embed', data, re.S|re.I):
					id = re.search('divxpress.com/embed-(.*?)-', data)
					if id:
						link = "http://www.divxpress.com/%s" % id.group(1)
				else:
					link = data
				getPage(link).addCallback(self.divxpress, link).addErrback(self.errorload)

			elif re.search('my\.pcloud\.com', data, re.S):
				getPage(data).addCallback(self.mypcloud).addErrback(self.errorload)

			elif re.search('ok\.ru', data, re.S):
				id = data.split('/')[-1]
				url = "http://www.ok.ru/dk"
				mp_globals.player_agent = 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.111 Safari/537.36 OPR/34.0.2036.50'
				dataPost = {'cmd': 'videoPlayerMetadata', 'mid': str(id)}
				getPage(url, method='POST', agent=mp_globals.player_agent, cookies=ck, postdata=urlencode(dataPost), headers={'Content-Type':'application/x-www-form-urlencoded'}).addCallback(self.okru).addErrback(self.errorload)

			elif re.search('zstream\.to', data, re.S):
				link = data
				getPage(link).addCallback(self.zstream).addErrback(self.errorload)

			elif re.search('watchers\.to', data, re.S):
				link = data
				getPage(link).addCallback(self.watchers).addErrback(self.errorload)

			elif re.search('mail\.ru', data, re.S):
				# https://my.mail.ru/mail/kaki.haki/video/_myvideo/296.html
				id_raw = re.findall('mail.ru/.*?mail/(.*?)/.*?/(\d*)\.html', data)
				if id_raw:
					(m_user, m_id) = id_raw[0]
					url = "http://videoapi.my.mail.ru/videos/mail/%s/_myvideo/%s.json?ver=0.2.60" % (m_user, m_id)
					spezialagent = "Mozilla/5.0 (Windows NT 10.0; WOW64; rv:46.0) Gecko/20100101 Firefox/46.0"
					kekse = {}
					getPage(url, agent=spezialagent, cookies=kekse).addCallback(self.mailru, kekse).addErrback(self.errorload)
				else:
					self.stream_not_found()

			elif re.search('vidzi\.tv/', data, re.S):
				link = data
				getPage(link, cookies=ck).addCallback(self.vidzi).addErrback(self.errorload)

			elif re.search('vidlox\.tv/', data, re.S):
				if re.search('vidlox\.tv/embed-', data, re.S):
					link = data
				else:
					id = re.search('vidlox\.tv/(\w+)', data)
					if id:
						link = "https://vidlox.tv/embed-%s.html" % id.group(1)
				if mp_globals.isDreamOS or not mp_globals.requests:
					twAgentGetPage(link).addCallback(self.vidlox).addErrback(self.errorload)
				else:
					data = self.grabpage(link)
					if data == "error":
						message = self.session.open(MessageBoxExt, _("Mandatory Python module python-requests is missing!"), MessageBoxExt.TYPE_ERROR)
					else:
						self.vidlox(data)

			elif re.search('streamango\.com|streamcherry\.com', data, re.S):
				link = data.replace('https','http')
				spezialagent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.113 Safari/537.36"
				getPage(link, agent=spezialagent).addCallback(self.streamango).addErrback(self.errorload)

			else:
				message = self.session.open(MessageBoxExt, _("No supported Stream Hoster, try another one!"), MessageBoxExt.TYPE_INFO, timeout=5)
		else:
			message = self.session.open(MessageBoxExt, _("Invalid Stream link, try another Stream Hoster!"), MessageBoxExt.TYPE_INFO, timeout=5)
		self.fallback = False

	def stream_not_found(self):
		message = self.session.open(MessageBoxExt, _("Stream not found, try another Stream Hoster."), MessageBoxExt.TYPE_INFO, timeout=5)

	def only_premium(self):
		if not (config.mediaportal.premiumize_use.value or config.mediaportal.realdebrid_use.value):
			message = self.session.open(MessageBoxExt, _("This hoster is only working with enabled Premium support."), MessageBoxExt.TYPE_INFO, timeout=5)
		else:
			message = self.session.open(MessageBoxExt, _("This Stream link is currently not available via Premium, try another Stream Hoster."), MessageBoxExt.TYPE_INFO, timeout=5)

	def errorload(self, error):
		printl('[streams]: ' + str(error),'','E')
		message = self.session.open(MessageBoxExt, _("Unknown error, check MP logfile."), MessageBoxExt.TYPE_INFO, timeout=5)

###############################################################################################

	def mypcloud(self, data):
		m = re.search('publink.set_download_link\(\'(.*?)\'\)', data)
		if m and m.group(1):
			self._callback(unquote(m.group(1)))
		else:
			self.stream_not_found()

	def sharedsxData(self, data, url):
		p1 = re.search('type="hidden" name="hash".*?value="(.*?)"', data)
		p2 = re.search('type="hidden" name="expires".*?value="(.*?)"', data)
		p3 = re.search('type="hidden" name="timestamp".*?value="(.*?)"', data)
		if p1 and p2 and p3:
			info = urlencode({'hash': p1.group(1),
							'expires': p2.group(1),
							'timestamp': p3.group(1)})
			reactor.callLater(3, self.sharedsxCalllater, url, method='POST', cookies=ck, postdata=info, headers={'Content-Type':'application/x-www-form-urlencoded', 'Accept-Language': 'en-gb, en;q=0.9, de;q=0.8'})
			message = self.session.open(MessageBoxExt, _("Stream starts in 3 sec."), MessageBoxExt.TYPE_INFO, timeout=3)
		else:
			self.stream_not_found()

	def sharedsxCalllater(self, *args, **kwargs):
		getPage(*args, **kwargs).addCallback(self.sharedsxPostData).addErrback(self.errorload)

	def sharedsxPostData(self, data):
		stream_url = re.search('data-url="(.*?)"', data)
		if stream_url:
			self._callback(stream_url.group(1))
		else:
			self.stream_not_found()

	def allmyvids(self, data):
		stream_url = re.findall('file"\s:\s"(.*?)",', data)
		if stream_url:
			self._callback(stream_url[0])
		else:
			self.stream_not_found()

	def mightyupload(self, data):
		stream_url = re.findall("file:\s'(.*?)'", data)
		if stream_url:
			self._callback(stream_url[0])
		else:
			get_packedjava = re.findall("<script type=.text.javascript.>eval.function(.*?)</script>", data, re.S)
			if get_packedjava:
				if len(get_packedjava) > 1:
					sJavascript = get_packedjava[1]
					sUnpacked = cJsUnpacker().unpackByString(sJavascript)
					if sUnpacked:
						if re.search('type="video/divx', sUnpacked):
							stream_url = re.findall('type="video/divx"src="(.*?)"', sUnpacked)
							if stream_url:
								self._callback(stream_url[0])
								return
						elif re.search("file", sUnpacked):
							stream_url = re.findall("file','(.*?)'", sUnpacked)
							if stream_url:
								self._callback(stream_url[0])
								return
			self.stream_not_found()

	def eco_read(self, data, kurl):
		id = re.findall('<div id="play" data-id="(.*?)">', data, re.S)
		analytics = re.findall("anlytcs='(.*?)'", data, re.S)
		footerhash = re.findall("var footerhash='(.*?)'", data, re.S)
		superslots = re.findall("var superslots='(.*?)'", data, re.S)
		if id and footerhash and superslots:
			tpm = footerhash[0] + superslots[0]
			postString = {'id': id[0], 'tpm':tpm}
			url = "http://www.ecostream.tv/js/ecoss.js"
			getPage(url, headers={'Content-Type': 'application/x-www-form-urlencoded'}).addCallback(self.eco_get_api_url, postString, kurl).addErrback(self.errorload)

	def eco_get_api_url(self, data, postString, kurl):
		api_url = re.findall('post\(\'(.*?)\'.*?#play', data)
		api_url = 'http://www.ecostream.tv'+api_url[-1]
		getPage(api_url, method='POST', cookies=ck, postdata=urlencode(postString), headers={'Content-Type': 'application/x-www-form-urlencoded', 'Referer': kurl, 'X-Requested-With': 'XMLHttpRequest'}).addCallback(self.eco_data).addErrback(self.errorload)

	def eco_data(self, data):
		stream_url = re.findall('"url":"(.*?)"', data, re.S)
		if stream_url:
			stream_url = "http://www.ecostream.tv%s" % stream_url[0]
			self._callback(stream_url)
		else:
			self.stream_not_found()

	def streamcloud(self, data):
		id = re.findall('<input type="hidden" name="id".*?value="(.*?)">', data)
		fname = re.findall('<input type="hidden" name="fname".*?alue="(.*?)">', data)
		if id and fname:
			url = "http://streamcloud.eu/%s" % id[0]
			post_data = urllib.urlencode({'op': 'download1', 'usr_login': '', 'id': id[0], 'fname': fname[0], 'referer': url, 'hash': '', 'imhuman':'Weiter zum Video'})
			reactor.callLater(10, self.streamcloud_getpage, url, post_data)
			message = self.session.open(MessageBoxExt, _("Stream starts in 10 sec."), MessageBoxExt.TYPE_INFO, timeout=10)
		else:
			self.stream_not_found()

	def streamcloud_getpage(self, url, post_data):
		spezialagent = 'Mozilla/5.0 (Windows NT 10.0; WOW64; rv:53.0) Gecko/20100101 Firefox/53.0'
		getPage(url, method='POST', cookies=ck, agent=spezialagent, postdata=post_data, headers={'Content-Type':'application/x-www-form-urlencoded', 'Referer': url, 'Origin':'http://streamcloud.eu'}).addCallback(self.streamcloud_data).addErrback(self.errorload)

	def streamcloud_data(self, data):
		stream_url = re.findall('file:\s"(.*?)",', data)
		if stream_url:
			self._callback(stream_url[0])
		elif re.search('This video is encoding now', data, re.S):
			self.session.open(MessageBoxExt, _("This video is encoding now. Please check back later."), MessageBoxExt.TYPE_INFO, timeout=10)
		else:
			self.stream_not_found()

	def xvidstage_post(self, data, url):
		op = re.findall('type="hidden" name="op".*?value="(.*?)"', data, re.S)
		id = re.findall('type="hidden" name="id".*?value="(.*?)"', data, re.S)
		fname = re.findall('type="hidden" name="fname".*?value="(.*?)"', data, re.S)
		referer = re.findall('type="hidden" name="referer".*?value="(.*?)"', data, re.S)
		if op and id and fname and referer:
			info = urlencode({
				'fname': fname[0],
				'id': id[0],
				'method_free': "Weiter zu Video / Stream Video",
				'op': "download1",
				'referer': "",
				'usr_login': ""})
			getPage(url, method='POST', postdata=info, headers={'Content-Type':'application/x-www-form-urlencoded'}).addCallback(self.xvidstage_data).addErrback(self.errorload)
		else:
			self.xvidstage_data(data)

	def xvidstage_data(self, data):
		get_packedjava = re.findall("<script type=.text.javascript.>eval.function(.*?)</script>", data, re.S)
		if get_packedjava:
			sJavascript = get_packedjava[1]
			sUnpacked = cJsUnpacker().unpackByString(sJavascript)
			if sUnpacked:
				stream_url = re.search('type="video/divx"src="(.*?)"', sUnpacked)
				if not stream_url:
					stream_url = re.search("'file','(.*?)'", sUnpacked)
				if stream_url:
					self._callback(stream_url.group(1))
					return

		self.stream_not_found()

	def userporn_tv(self, link):
		fx = Userporn()
		stream_url = fx.get_media_url(link)
		if stream_url:
			self._callback(stream_url)
		else:
			self.stream_not_found()