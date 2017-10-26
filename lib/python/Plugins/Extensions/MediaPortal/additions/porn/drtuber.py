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
from Plugins.Extensions.MediaPortal.resources.keyboardext import VirtualKeyBoardExt

BASE_URL = "http://www.drtuber.com"
dtAgent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36"
default_cover = "file://%s/drtuber.png" % (config.mediaportal.iconcachepath.value + "logos")
ck = {}
json_headers = {
	'Accept':'application/json',
	'Accept-Language':'en,en-US;q=0.7,en;q=0.3',
	'X-Requested-With':'XMLHttpRequest',
	'Content-Type':'application/x-www-form-urlencoded',
	}

class drtuberGenreScreen(MPScreen):

	def __init__(self, session):
		self.session = session
		self.plugin_path = mp_globals.pluginPath
		self.skin_path = mp_globals.pluginPath + mp_globals.skinsPath
		path = "%s/%s/defaultGenreScreenCover.xml" % (self.skin_path, config.mediaportal.skin.value)
		if not fileExists(path):
			path = self.skin_path + mp_globals.skinFallback + "/defaultGenreScreenCover.xml"
		with open(path, "r") as f:
			self.skin = f.read()
			f.close()
		MPScreen.__init__(self, session)
		self.scope = 0
		self.scopeText = ['Straight', 'Gays', 'Transsexual']

		self["actions"] = ActionMap(["MP_Actions"], {
			"ok" : self.keyOK,
			"0": self.closeAll,
			"cancel" : self.keyCancel,
			"yellow" : self.keyScope
		}, -1)

		self['title'] = Label('DrTuber.com')
		self['ContentTitle'] = Label('Genre:')
		self['F3'] = Label(_('Scope'))

		self.keyLocked = True
		self.suchString = ''
		self.genreliste = []
		self.ml = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
		self['liste'] = self.ml

		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self.keyLocked = True
		CoverHelper(self['coverArt']).getCover(default_cover)
		url = "%s/categories" % BASE_URL
		getPage(url, agent=dtAgent, cookies=ck).addCallback(self.genreData).addErrback(self.dataError)

	def genreData(self, data):
		parse = re.search('<h2>%s</h2>(.*?)</div></div>' % self.scopeText[self.scope], data, re.S)
		if parse:
			genre = re.findall('<a\shref="(.*?)"\sdata-catFilter_category>(.*?)\s{0,1}<span>', parse.group(1), re.S)
			if genre:
				for genreurl, genrename in genre:
					genreurl = BASE_URL + genreurl
					self.genreliste.append((genrename, genreurl))
		self.genreliste.sort()
		self.genreliste.insert(0, ("Longest", "longest"))
		self.genreliste.insert(0, ("Most Commented (All Time)", "comments_all"))
		self.genreliste.insert(0, ("Most Commented (Monthly)", "comments_month"))
		self.genreliste.insert(0, ("Most Commented (Weekly)", "comments_week"))
		self.genreliste.insert(0, ("Most Commented (Daily)", "comments_day"))
		self.genreliste.insert(0, ("Top Rated (All Time)", "like_sum"))
		self.genreliste.insert(0, ("Top Rated (Monthly)", "rating_month"))
		self.genreliste.insert(0, ("Top Rated (Weekly)", "rating_week"))
		self.genreliste.insert(0, ("Top Rated (Daily)", "rating_day"))
		self.genreliste.insert(0, ("Newest", "addtime"))
		self.genreliste.insert(0, ("--- Search ---", "callSuchen"))
		self.ml.setList(map(self._defaultlistcenter, self.genreliste))
		self.keyLocked = False

	def keyOK(self):
		if self.keyLocked:
			return
		Name = self['liste'].getCurrent()[0][0]
		if Name == "--- Search ---":
			self.session.openWithCallback(self.SuchenCallback, VirtualKeyBoardExt, title = (_("Enter search criteria")), text = self.suchString, is_dialog=True, auto_text_init=False, suggest_func=self.getSuggestions)
		else:
			Link = self['liste'].getCurrent()[0][1]
			if Link.startswith('http'):
				ck.update({'index_filter_sort':''})
			else:
				ck.update({'index_filter_sort':Link})
				Link = BASE_URL + "/videos"
			self.session.open(drtuberFilmScreen, Link, Name)

	def SuchenCallback(self, callback = None, entry = None):
		if callback is not None and len(callback):
			self.suchString = callback
			Name = "--- Search ---"
			Link = BASE_URL + '/search/videos/%s' % self.suchString.replace(' ', '%20')
			self.session.open(drtuberFilmScreen, Link, Name)

	def getSuggestions(self, text, max_res):
		url = BASE_URL + "/ajax/search_suggest?q=%s" % urllib.quote_plus(text)
		d = twAgentGetPage(url, agent=dtAgent, headers=json_headers, timeout=5)
		d.addCallback(self.gotSuggestions, max_res)
		d.addErrback(self.gotSuggestions, max_res, err=True)
		return d

	def gotSuggestions(self, suggestions, max_res, err=False):
		list = []
		if not err and type(suggestions) in (str, buffer):
			suggestions = json.loads(suggestions)
			for item in suggestions:
				li = item
				list.append(str(li))
				max_res -= 1
				if not max_res: break
		elif err:
			printl(str(suggestions),self,'E')
		return list

	def keyScope(self):
		self.genreliste = []
		if self.scope == 0:
			self.scope = 1
		elif self.scope == 1:
			self.scope = 2
		else:
			self.scope = 0
		self['ContentTitle'].setText('Genre:   (Scope - %s)' % self.scopeText[self.scope])
		self.layoutFinished()

class drtuberFilmScreen(MPScreen, ThumbsHelper):

	def __init__(self, session, Link, Name):
		self.Link = Link
		self.Name = Name
		self.plugin_path = mp_globals.pluginPath
		self.skin_path = mp_globals.pluginPath + mp_globals.skinsPath
		path = "%s/%s/defaultListWideScreen.xml" % (self.skin_path, config.mediaportal.skin.value)
		if not fileExists(path):
			path = self.skin_path + mp_globals.skinFallback + "/defaultListWideScreen.xml"
		with open(path, "r") as f:
			self.skin = f.read()
			f.close()
		MPScreen.__init__(self, session)
		ThumbsHelper.__init__(self)

		self["actions"] = ActionMap(["MP_Actions"], {
			"ok" : self.keyOK,
			"0" : self.closeAll,
			"cancel" : self.keyCancel,
			"5" : self.keyShowThumb,
			"up" : self.keyUp,
			"down" : self.keyDown,
			"right" : self.keyRight,
			"left" : self.keyLeft,
			"nextBouquet" : self.keyPageUp,
			"prevBouquet" : self.keyPageDown,
			"green" : self.keyPageNumber
		}, -1)

		self['title'] = Label("DrTuber.com")
		self['ContentTitle'] = Label("Genre: %s" % self.Name)
		self['F2'] = Label(_("Page"))
		self['Page'] = Label(_("Page:"))

		self.keyLocked = True
		self.page = 1
		self.lastpage = 1
		self.filmliste = []
		self.ml = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
		self['liste'] = self.ml

		self.onLayoutFinish.append(self.loadPage)

	def loadPage(self):
		self.keyLocked = True
		self['name'].setText(_('Please wait...'))
		self.filmliste = []
		url = "%s/%s" % (self.Link, str(self.page))
		print url
		getPage(url, agent=dtAgent, cookies=ck).addCallback(self.loadData).addErrback(self.dataError)

	def loadData(self, data):
		self.getLastPage(data, '<ul class="pagination"(.*?)<div class="holder">')
		Movies = re.findall('><a\shref="(/video/.*?)"\sclass="th\sch-video.*?src="(.*?)"\salt="(.*?)".*?<em>(\d+:\d+)<', data, re.S)
		if Movies:
			for (Url, Image, Title, Runtime) in Movies:
				Url = '%s%s' % (BASE_URL, Url)
				self.filmliste.append((decodeHtml(Title), Url, Image, Runtime))
		if len(self.filmliste) == 0:
			self.filmliste.append((_('No videos found!'), '', '', ''))
		self.ml.setList(map(self._defaultlistleft, self.filmliste))
		self.ml.moveToIndex(0)
		self.keyLocked = False
		self.th_ThumbsQuery(self.filmliste, 0, 1, 2, None, None, self.page, self.lastpage, mode=1)
		self.showInfos()

	def showInfos(self):
		title = self['liste'].getCurrent()[0][0]
		pic = self['liste'].getCurrent()[0][2]
		runtime = self['liste'].getCurrent()[0][3]
		self['handlung'].setText("Runtime: %s" % runtime)
		self['name'].setText(title)
		CoverHelper(self['coverArt']).getCover(pic)

	def keyOK(self):
		if self.keyLocked:
			return
		Link = self['liste'].getCurrent()[0][1]
		if not Link == None:
			url = '%s' % Link
			self.keyLocked = True
			getPage(url, agent=dtAgent, cookies=ck).addCallback(self.getVideoPage).addErrback(self.dataError)

	def getVideoPage(self, data):
		params = re.findall('params\s\+=\s\'h=(.*?)\'.*?params\s\+=\s\'%26t=(.*?)\'.*?params\s\+=\s\'%26vkey=\'\s\+\s\'(.*?)\'', data, re.S)
		if params:
			for (x, y, z) in params:
				self.getVideoUrl(x, y, z, self.gotVideoPage)

	def getVideoUrl(self, param1, param2, param3, callback):
		self.param1 = param1
		self.param2 = param2
		self.param3 = param3
		import base64
		hash = hashlib.md5(self.param3 + base64.b64decode('UFQ2bDEzdW1xVjhLODI3')).hexdigest()
		url = '%s/player_config/?h=%s&t=%s&vkey=%s&pkey=%s&aid=' % (BASE_URL, self.param1, self.param2, self.param3, hash)
		getPage(url, agent=dtAgent, cookies=ck).addCallback(self.getData, callback).addErrback(self.dataError, callback)

	def getData(self, data, callback):
		url = re.findall('video_file>.*?(http.*?\.(?:mp4|flv).*?)\]{0,2}>{0,1}<\/video_file', data, re.S)
		if url:
			url = str(url[0]).replace("&amp;","&")
			callback(url)

	def gotVideoPage(self, data):
		if data != None:
			self.keyLocked = False
			Title = self['liste'].getCurrent()[0][0]
			self.session.open(SimplePlayer, [(Title, data)], showPlaylist=False, ltype='drtuber')