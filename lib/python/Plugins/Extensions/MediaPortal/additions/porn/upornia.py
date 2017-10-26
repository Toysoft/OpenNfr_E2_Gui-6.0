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

agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36'
json_headers = {
	'Accept':'*/*',
	'Accept-Encoding':'deflate',
	'Accept-Language':'de,en-US;q=0.7,en;q=0.3',
	'X-Requested-With':'XMLHttpRequest',
	'Content-Type':'application/x-www-form-urlencoded'
	}
default_cover = "file://%s/upornia.png" % (config.mediaportal.iconcachepath.value + "logos")

class uporniaGenreScreen(MPScreen):

	def __init__(self, session):
		self.plugin_path = mp_globals.pluginPath
		self.skin_path = mp_globals.pluginPath + mp_globals.skinsPath
		path = "%s/%s/defaultGenreScreenCover.xml" % (self.skin_path, config.mediaportal.skin.value)
		if not fileExists(path):
			path = self.skin_path + mp_globals.skinFallback + "/defaultGenreScreenCover.xml"
		with open(path, "r") as f:
			self.skin = f.read()
			f.close()

		MPScreen.__init__(self, session)

		self["actions"] = ActionMap(["MP_Actions"], {
			"ok" : self.keyOK,
			"0" : self.closeAll,
			"cancel" : self.keyCancel,
			"up" : self.keyUp,
			"down" : self.keyDown,
			"right" : self.keyRight,
			"left" : self.keyLeft
		}, -1)

		self['title'] = Label("Upornia.com")
		self['ContentTitle'] = Label("Genre:")

		self.keyLocked = True
		self.suchString = ''

		self.genreliste = []
		self.ml = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
		self['liste'] = self.ml

		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self.keyLocked = True
		CoverHelper(self['coverArt']).getCover(default_cover)
		url = "http://www.upornia.com/categories/"
		getPage(url, agent=agent).addCallback(self.genreData).addErrback(self.dataError)

	def genreData(self, data):
		Cats = re.findall('class="item">.*?href="(.*?)".*?img\ssrc="(.*?)"\salt="(.*?)"', data, re.S)
		if Cats:
			for (Url, Image, Title) in Cats:
				self.genreliste.append((Title, Url, Image))
			self.genreliste.sort()
			self.genreliste.insert(0, ("Longest", "http://www.upornia.com/longest/", default_cover))
			self.genreliste.insert(0, ("Most Popular", "http://www.upornia.com/most-popular/", default_cover))
			self.genreliste.insert(0, ("Top Rated", "http://www.upornia.com/top-rated/", default_cover))
			self.genreliste.insert(0, ("Newest", "http://www.upornia.com/latest-updates/", default_cover))
			self.genreliste.insert(0, ("--- Search ---", "callSuchen", default_cover))
			self.ml.setList(map(self._defaultlistcenter, self.genreliste))
			self.ml.moveToIndex(0)
			self.keyLocked = False
			self.showInfos()

	def showInfos(self):
		Image = self['liste'].getCurrent()[0][2]
		CoverHelper(self['coverArt']).getCover(Image)

	def keyOK(self):
		if self.keyLocked:
			return
		Name = self['liste'].getCurrent()[0][0]
		if Name == "--- Search ---":
			self.session.openWithCallback(self.SuchenCallback, VirtualKeyBoardExt, title = (_("Enter search criteria")), text = self.suchString, is_dialog=True, auto_text_init=False, suggest_func=self.getSuggestions)
		else:
			Link = self['liste'].getCurrent()[0][1]
			self.session.open(uporniaFilmScreen, Link, Name)

	def SuchenCallback(self, callback = None, entry = None):
		if callback is not None and len(callback):
			Name = "--- Search ---"
			self.suchString = callback
			Link = self.suchString.replace(' ', '+')
			self.session.open(uporniaFilmScreen, Link, Name)

	def getSuggestions(self, text, max_res):
		url = "http://www.upornia.com/cloudsearch/suggesters.php?char=%s" % urllib.quote_plus(text)
		d = twAgentGetPage(url, agent=agent, headers=json_headers, timeout=5)
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

class uporniaFilmScreen(MPScreen, ThumbsHelper):

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

		self['title'] = Label("Upornia.com")
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
		if re.match(".*Search", self.Name):
			url = "http://upornia.com/search/"
			postdata = {
			'mode':'async',
			'function':'get_block',
			'block_id':'list_videos_videos_list_search_result',
			'sort_by':'post_date',
			'q':self.Link,
			'category_ids':'',
			'from_videos':str(self.page),
			'from_albums':str(self.page),
			}
			getPage(url, method='POST', agent=agent, postdata=urlencode(postdata), headers=json_headers).addCallback(self.loadData).addErrback(self.dataError)
		else:
			if self.page == 1:
				url = self.Link
			else:
				url = "%s%s/" % (self.Link, str(self.page))
			getPage(url, agent=agent).addCallback(self.loadData).addErrback(self.dataError)

	def loadData(self, data):
		self.getLastPage(data, '<li class="last">(.*?)</a>', '.*((?:\d+.)\d+)')
		Movies = re.findall('data-video-id=.*?href="(.*?)".*?img\ssrc="(.*?)"\s{0,1}alt="(.*?)(?:"|,).*?class="thumbnail__info__right">(.*?)</div', data, re.S)
		if Movies:
			for (Url, Image, Title, Runtime) in Movies:
				if not Url.startswith('http'):
					Url = 'http://www.upornia.com' + Url
				self.filmliste.append((decodeHtml(Title), Url, Image, Runtime))
		if len(self.filmliste) == 0:
			self.filmliste.append((_('No videos found!'), None, None, ''))
		self.ml.setList(map(self._defaultlistleft, self.filmliste))
		self.ml.moveToIndex(0)
		self.keyLocked = False
		self.th_ThumbsQuery(self.filmliste, 0, 1, 2, None, None, self.page, self.lastpage, mode=1)
		self.showInfos()

	def showInfos(self):
		title = self['liste'].getCurrent()[0][0]
		pic = self['liste'].getCurrent()[0][2]
		runtime = self['liste'].getCurrent()[0][3]
		self['name'].setText(title)
		self['handlung'].setText("Runtime: %s" % runtime)
		CoverHelper(self['coverArt']).getCover(pic)

	def keyOK(self):
		if self.keyLocked:
			return
		Link = self['liste'].getCurrent()[0][1]
		if Link:
			self.keyLocked = True
			getPage(Link, agent=agent).addCallback(self.getVideoPage).addErrback(self.dataError)

	def getVideoPage(self, data):
		try:
			import execjs
			node = execjs.get("Node")
		except:
			printl('nodejs not found',self,'E')
			self.session.open(MessageBoxExt, _("This plugin requires packages python-pyexecjs and nodejs."), MessageBoxExt.TYPE_INFO)
			return
		decstring = re.findall('sources\[\d\]={type:\'mp4\',file:([a-zA-Z0-9]+)\(', data, re.S)
		decoder = re.findall('(%s=function.*?};)' % decstring[0], data, re.S)
		if decoder:
			video_url = re.findall('(var video_url.*?;)', data, re.S)
			js = decoder[0] + "\n" + video_url[0] + "\n" + "vidurl = (%s(video_url));" % decstring[0] + "\n" + "return vidurl;"
		else:
			decoder = re.findall('(var (_0x[A-Za-z0-9]+)=.*?)var (?:m3u8|video)_url', data, re.S)
			video_url = re.findall('(var video_url.*?;)', data, re.S)
			js = decoder[0][0].replace('window[%s[1]]' % decoder[0][1],'%s[1]' % decoder[0][1])  + "\n" + video_url[0] + "\n" + "vidurl = (%s[1](video_url));" % decoder[0][1] + "\n" + "return vidurl;"
		url = str(node.exec_(js))
		self.keyLocked = False
		Title = self['liste'].getCurrent()[0][0]
		self.session.open(SimplePlayer, [(Title, url)], showPlaylist=False, ltype='upornia')