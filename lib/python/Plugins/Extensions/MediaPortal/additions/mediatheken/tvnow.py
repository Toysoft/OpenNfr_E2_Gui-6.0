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
from Plugins.Extensions.MediaPortal.resources.imports import *
from Plugins.Extensions.MediaPortal.resources.twagenthelper import twAgentGetPage

BASE_URL = "http://api.tvnow.de/v3/"
nowAgent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36'
default_cover = "file://%s/tvnow.png" % (config.mediaportal.iconcachepath.value + "logos")

class tvnowFirstScreen(MPScreen, ThumbsHelper):

	def __init__(self, session):
		MPScreen.__init__(self, session, skin='MP_Plugin')
		ThumbsHelper.__init__(self)

		self["actions"] = ActionMap(["MP_Actions"], {
			"0"		: self.closeAll,
			"ok"	: self.keyOK,
			"cancel": self.keyCancel,
			"5" : self.keyShowThumb,
			"up" : self.keyUp,
			"down" : self.keyDown,
			"right" : self.keyRight,
			"left" : self.keyLeft
		}, -1)

		self['title'] = Label("TVNOW")
		self['ContentTitle'] = Label(_("Stations:"))
		self['name'] = Label(_("Selection:"))

		self.keyLocked = True
		self.senderliste = []
		self.ml = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
		self['liste'] = self.ml

		self.onLayoutFinish.append(self.genreData)

	def genreData(self):
		CoverHelper(self['coverArt']).getCover(default_cover)
		self.senderliste.append(("RTL", "rtl", default_cover))
		self.senderliste.append(("VOX", "vox", default_cover))
		self.senderliste.append(("RTL2", "rtl2", default_cover))
		self.senderliste.append(("NITRO", "nitro",  default_cover))
		self.senderliste.append(("SUPER RTL", "superrtl", default_cover))
		self.senderliste.append(("n-tv", "ntv", default_cover))
		self.senderliste.append(("RTLplus", "rtlplus",  default_cover))
		self.senderliste.append(("Watchbox", "watchbox",  "file://%s/watchbox.png" % (config.mediaportal.iconcachepath.value + "logos")))
		self.ml.setList(map(self._defaultlistcenter, self.senderliste))
		self.keyLocked = False
		self.th_ThumbsQuery(self.senderliste, 0, 1, 2, None, None, 1, 1, mode=1)
		self.showInfos()

	def showInfos(self):
		Image = self['liste'].getCurrent()[0][2]
		CoverHelper(self['coverArt']).getCover(Image)
		Name = self['liste'].getCurrent()[0][0]
		self['name'].setText(_("Selection:") + " " + Name)

	def keyOK(self):
		if self.keyLocked:
			return
		Name = self['liste'].getCurrent()[0][0]
		Link = self['liste'].getCurrent()[0][1]
		Image = self['liste'].getCurrent()[0][2]
		self.session.open(tvnowSubGenreScreen, Link, Name, Image)

class tvnowSubGenreScreen(MPScreen, ThumbsHelper):

	def __init__(self, session, Link, Name, Image):
		self.Link = Link
		self.Name = Name
		self.Image = Image
		MPScreen.__init__(self, session, skin='MP_Plugin')
		ThumbsHelper.__init__(self)

		self["actions"] = ActionMap(["MP_Actions"], {
			"0"		: self.closeAll,
			"ok"	: self.keyOK,
			"cancel": self.keyCancel,
			"5" : self.keyShowThumb,
			"up" : self.keyUp,
			"down" : self.keyDown,
			"right" : self.keyRight,
			"left" : self.keyLeft
		}, -1)

		self['title'] = Label("TVNOW")
		self['ContentTitle'] = Label(_("Selection:"))
		self['name'] = Label(_("Selection:") + " " + self.Name)

		self.keyLocked = True
		self.filmliste = []
		self.ml = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
		self['liste'] = self.ml

		self.onLayoutFinish.append(self.loadPage)

	def loadPage(self):
		if self.Link == "watchbox":
			cats = "%22serie%22,%22film%22"
		else:
			cats = "%22serie%22,%22news%22"
		url = BASE_URL + "formats?fields=title,seoUrl,icon,defaultImage169Logo,defaultImage169Format&filter=%7B%22Station%22:%22" + self.Link + "%22,%22Disabled%22:%220%22,%22CategoryId%22:%7B%22containsIn%22:%5B" + cats + "%5D%7D%7D&maxPerPage=500&page=1"
		twAgentGetPage(url, agent=nowAgent).addCallback(self.parseData).addErrback(self.dataError)
		if self.Link == "watchbox":
			url = BASE_URL + "formats?fields=title,seoUrl,icon,defaultImage169Logo,defaultImage169Format&filter=%7B%22Station%22:%22" + self.Link + "%22,%22Disabled%22:%220%22,%22CategoryId%22:%7B%22containsIn%22:%5B" + cats + "%5D%7D%7D&maxPerPage=500&page=2"
			twAgentGetPage(url, agent=nowAgent).addCallback(self.parseData).addErrback(self.dataError)

	def parseData(self, data):
		nowdata = json.loads(data)
		for node in nowdata["items"]:
			if str(node["icon"]) == "new" or str(node["icon"]) == "free":
				image = str(node["defaultImage169Logo"])
				if image == "":
					image = str(node["defaultImage169Format"])
				if image == "":
					image = self.Image
				self.filmliste.append((str(node["title"]), str(node["seoUrl"]), image))
		self.filmliste.sort(key=lambda t : t[0].lower())
		self.ml.setList(map(self._defaultlistcenter, self.filmliste))
		self.keyLocked = False
		self.th_ThumbsQuery(self.filmliste, 0, 1, 2, None, None, 1, 1, mode=1)
		self.showInfos()

	def showInfos(self):
		Image = self['liste'].getCurrent()[0][2]
		CoverHelper(self['coverArt']).getCover(Image)
		Name = self['liste'].getCurrent()[0][0]
		self['name'].setText(_("Selection:") + " " + self.Name + ":" + Name)

	def keyOK(self):
		exist = self['liste'].getCurrent()
		if self.keyLocked or exist == None:
			return
		Name = self.Name + ":" + self['liste'].getCurrent()[0][0]
		Link = self['liste'].getCurrent()[0][1]
		Image = self['liste'].getCurrent()[0][2]
		self.session.open(tvnowStaffelScreen, Link, Name, Image)

class tvnowStaffelScreen(MPScreen):

	def __init__(self, session, Link, Name, Image):
		self.Link = Link
		self.Name = Name
		self.Image = Image
		MPScreen.__init__(self, session, skin='MP_Plugin')

		self["actions"] = ActionMap(["MP_Actions"], {
			"0"		: self.closeAll,
			"ok"	: self.keyOK,
			"cancel": self.keyCancel,
			"up" : self.keyUp,
			"down" : self.keyDown,
			"right" : self.keyRight,
			"left" : self.keyLeft
		}, -1)

		self['title'] = Label("TVNOW")
		self['ContentTitle'] = Label(_("Seasons:"))
		self['name'] = Label(_("Selection:") + " " + self.Name)

		self.keyLocked = True
		self.filmliste = []
		self.ml = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
		self['liste'] = self.ml

		self.onLayoutFinish.append(self.loadPage)

	def loadPage(self):
		url = BASE_URL + "formats/seo?fields=formatTabs.*&name=" + self.Link + ".php"
		twAgentGetPage(url, agent=nowAgent).addCallback(self.parseData).addErrback(self.dataError)

	def parseData(self, data):
		nowdata = json.loads(data)
		for node in nowdata["formatTabs"]["items"]:
			self.filmliste.append((str(node["headline"]), str(node["id"]), str(node["visible"]),str(node["tv"])))
		self.ml.setList(map(self._defaultlistcenter, self.filmliste))
		self.keyLocked = False
		CoverHelper(self['coverArt']).getCover(self.Image)
		self.showInfos()

	def showInfos(self):
		Name = self['liste'].getCurrent()[0][0]
		self['name'].setText(_("Selection:") + " " + self.Name + ":" + Name)

	def keyOK(self):
		exist = self['liste'].getCurrent()
		if self.keyLocked or exist == None:
			return
		Name = self.Name + ":" + self['liste'].getCurrent()[0][0]
		Link = self['liste'].getCurrent()[0][1]
		self.session.open(tvnowEpisodenScreen, Link, Name, self.Image)

class tvnowEpisodenScreen(MPScreen, ThumbsHelper):

	def __init__(self, session, Link, Name, Image):
		self.Link = Link
		self.Name = Name
		self.Image = Image
		MPScreen.__init__(self, session, skin='MP_PluginDescr')
		ThumbsHelper.__init__(self)

		self["actions"] = ActionMap(["MP_Actions"], {
			"0"		: self.closeAll,
			"ok"	: self.keyOK,
			"cancel": self.keyCancel,
			"5" : self.keyShowThumb,
			"up" : self.keyUp,
			"down" : self.keyDown,
			"right" : self.keyRight,
			"left" : self.keyLeft
		}, -1)

		self['title'] = Label("TVNOW")
		self['ContentTitle'] = Label(_("Episodes:"))
		self['name'] = Label(_("Selection:") + " " + self.Name)

		self.keyLocked = True
		self.filmliste = []
		self.ml = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
		self['liste'] = self.ml

		self.onLayoutFinish.append(self.loadPage)

	def loadPage(self):
		url = BASE_URL + "formatlists/" + self.Link + "?fields=*,formatTabPages.*,formatTabPages.container.movies.*,formatTabPages.container.movies.format.*,formatTabPages.container.movies.livestreamEvent.*,formatTabPages.container.movies.pictures,formatTabPages.container.movies.files.*"
		twAgentGetPage(url, agent=nowAgent).addCallback(self.parseData).addErrback(self.dataError)

	def parseData(self, data):
		nowdata = json.loads(data)
		for node in nowdata["formatTabPages"]["items"]:
			try:
				for nodex in node["container"]["movies"]["items"]:
					try:
						if nodex["free"] and not nodex["isDrm"]:
							try:
								image = "http://ais.tvnow.de/rtlnow/%s/660x660/formatimage.jpg" % nodex["pictures"]["default"][0]["id"]
							except:
								image = self.Image
							try:
								file = str(nodex["files"]["items"][0]["path"])
								file = re.sub(r'/(.+)/((\d+)/(.*))', r'/\1/videos/\2', file)
								file = file.strip('/')
							except:
								file = None
							self.filmliste.append((str(nodex["title"]), str(nodex["id"]), str(nodex["articleLong"]), image, file))
					except:
						continue
			except:
				continue
		if len(self.filmliste) == 0:
			self.filmliste.append((_('Currently no free episodes available!'), None, None, None))
		self.ml.setList(map(self._defaultlistcenter, self.filmliste))
		self.keyLocked = False
		self.th_ThumbsQuery(self.filmliste, 0, 1, 2, None, None, 1, 1, mode=1)
		self.showInfos()

	def showInfos(self):
		Descr = self['liste'].getCurrent()[0][2]
		Image = self['liste'].getCurrent()[0][3]
		self['handlung'].setText(decodeHtml(Descr))
		CoverHelper(self['coverArt']).getCover(Image)
		Name = self['liste'].getCurrent()[0][0]
		self['name'].setText(_("Selection:") + " " + self.Name + ":" + Name)

	def keyOK(self):
		exist = self['liste'].getCurrent()
		if self.keyLocked or exist == None:
			return
		id = self['liste'].getCurrent()[0][1]
		if not id:
			return
		url = 'http://api.tvnow.de/v3/movies/%s?fields=manifest' % id
		getPage(url, agent=nowAgent).addCallback(self.get_stream).addErrback(self.dataError)

	def get_stream(self, data):
		nowdata = json.loads(data)
		format = None
		dashclear = nowdata["manifest"]["dashclear"]
		url = str(dashclear.replace('dash', 'hls').replace('.mpd','fairplay.m3u8'))
		getPage(url, agent=nowAgent).addCallback(self.loadplaylist, url).addErrback(self.dataError)

	def loadplaylist(self, data, baseurl):
		videoPrio = int(config.mediaportal.videoquali_others.value)
		if videoPrio == 2:
			bw = 3000000
		elif videoPrio == 1:
			bw = 950000
		else:
			bw = 600000
		self.bandwith_list = []
		match_sec_m3u8=re.findall('BANDWIDTH=(\d+).*?\n(.*?m3u8)', data, re.S)
		for each in match_sec_m3u8:
			bandwith,url = each
			self.bandwith_list.append((int(bandwith),url))
		_, best = min((abs(int(x[0]) - bw), x) for x in self.bandwith_list)

		url = baseurl.replace('fairplay.m3u8', '') + best[1]
		Name = self['liste'].getCurrent()[0][0]
		mp_globals.player_agent = nowAgent
		self.session.open(SimplePlayer, [(Name, url)], showPlaylist=False, ltype='tvnow', forceGST=True)