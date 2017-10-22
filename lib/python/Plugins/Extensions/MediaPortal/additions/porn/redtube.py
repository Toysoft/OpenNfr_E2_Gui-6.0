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

agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/61.0.3163.100 Safari/537.36'
json_headers = {
	'Accept':'text/plain, */*; q=0.01',
	'Accept-Language':'de,en-US;q=0.7,en;q=0.3',
	'X-Requested-With':'XMLHttpRequest',
	'Content-Type':'application/x-www-form-urlencoded',
	'Referer':'https://www.redtube.com/',
	'Origin':'https://www.redtube.com/'
	}
default_cover = "file://%s/redtube.png" % (config.mediaportal.iconcachepath.value + "logos")

ufAC = ''

class redtubeGenreScreen(MPScreen):

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

		self['title'] = Label("RedTube.com")
		self['ContentTitle'] = Label("Genre:")

		self.keyLocked = True
		self.suchString = ''

		self.genreliste = []
		self.ml = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
		self['liste'] = self.ml

		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self.keyLocked = True
		url = "https://www.redtube.com/categories"
		getPage(url).addCallback(self.genreData).addErrback(self.dataError)

	def genreData(self, data):
		global ufAC
		ufAC = re.search('page_params.ufAC =.*?"(.*?)";', data, re.S).group(1)
		Cats = re.findall('class="video">.*?<a\shref="(.*?)"\stitle="(.*?)">.*?data-src="(.*?\.jpg).*?"', data, re.S)
		if Cats:
			for (Url, Title, Image) in Cats:
				Url = "https://www.redtube.com" + Url + '?page='
				Title = Title.replace('&amp;','&')
				if Image.startswith('//'):
					Image = 'http:' + Image
				self.genreliste.append((Title, Url, Image))
			self.genreliste.sort()
			self.genreliste.insert(0, ("Longest", "https://www.redtube.com/longest?period=alltime&page=", default_cover))
			self.genreliste.insert(0, ("Most Favorited", "https://www.redtube.com/mostfavored?period=alltime&page=", default_cover))
			self.genreliste.insert(0, ("Most Viewed", "https://www.redtube.com/mostviewed?period=alltime&page=", default_cover))
			self.genreliste.insert(0, ("Top Rated", "https://www.redtube.com/top?period=alltime&page=", default_cover))
			self.genreliste.insert(0, ("Trending", "https://www.redtube.com/hot?page=", default_cover))
			self.genreliste.insert(0, ("Newest", "https://www.redtube.com/newest?page=", default_cover))
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
			self.session.open(redtubeFilmScreen, Link, Name)

	def SuchenCallback(self, callback = None, entry = None):
		if callback is not None and len(callback):
			Name = "--- Search ---"
			self.suchString = callback
			Link = 'https://www.redtube.com/?search=%s&page=' % self.suchString.replace(' ', '+')
			self.session.open(redtubeFilmScreen, Link, Name)

	def getSuggestions(self, text, max_res):
		url = "https://www.redtube.com/searchsuggest?class=0&limit=10"
		postdata = {'term': text, 'ufAC': ufAC}
		d = twAgentGetPage(url, method='POST', postdata=urlencode(postdata), agent=agent, headers=json_headers, timeout=5)
		d.addCallback(self.gotSuggestions, max_res)
		d.addErrback(self.gotSuggestions, max_res, err=True)
		return d

	def gotSuggestions(self, suggestions, max_res, err=False):
		list = []
		if not err and type(suggestions) in (str, buffer):
			suggestions = json.loads(suggestions)
			for item in suggestions['data']['suggestions']:
				try:
					if item['type'] == 'video':
						li = item['label']
						list.append(str(li))
						max_res -= 1
						if not max_res: break
				except:
					pass
		elif err:
			printl(str(suggestions),self,'E')
		return list

class redtubeFilmScreen(MPScreen, ThumbsHelper):

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

		self['title'] = Label("RedTube.com")
		self['ContentTitle'] = Label("Genre: %s" % self.Name)
		self['F2'] = Label(_("Page"))

		self['Page'] = Label(_("Page:"))
		self.keyLocked = True
		self.page = 1

		self.filmliste = []
		self.ml = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
		self['liste'] = self.ml

		self.onLayoutFinish.append(self.loadPage)

	def loadPage(self):
		self.keyLocked = True
		self['name'].setText(_('Please wait...'))
		self.filmliste = []
		url = "%s%s" % (self.Link, str(self.page))
		getPage(url).addCallback(self.loadData).addErrback(self.dataError)

	def loadData(self, data):
		lastp = re.search('<h1>.*?\s\((.*?)\)</h1>', data, re.S)
		if lastp:
			lastp = lastp.group(1).replace(',','')
			cat = self.Link
			lastp = round((float(lastp) / 24) + 0.5)
			self.lastpage = int(lastp)
		else:
			self.lastpage = 1230
		self['page'].setText(str(self.page) + ' / ' + str(self.lastpage))
		if "home_page_section_e" in data:
			parse = re.search('home_page_section_e(.*?)home_page_section_f', data, re.S)
			if parse:
				data = parse.group(1)
		Movies = re.findall('class="widget-video-holder">.*?<a\shref="(\/\d+)"\stitle="(.*?)"(?:\sclass="video-thumb|).*?video-duration.*?>(.*?)<.*?data-src="(.*?)".*?views">(.*?)</span>', data, re.S)
		if Movies:
			for (Url, Title, Runtime, Image, Views) in Movies:
				if Image.startswith('//'):
					Image = 'http:' + Image
				Views = Views.replace(',','').replace(' views','')
				Runtime = Runtime.strip()
				self.filmliste.append((decodeHtml(Title), Url, Image, Runtime, Views))
		else:
			Movies = re.findall('class="widget-video-holder (?:videoPreviewBg|)">.*?<a\shref="(\/\d+)"\stitle="(.*?)"(?:\sclass="video-thumb|).*?data-src="(.*?)".*?video-duration.*?>(.*?)<.*?views">(.*?)</span>', data, re.S)
			if Movies:
				for (Url, Title, Image, Runtime, Views) in Movies:
					if Image.startswith('//'):
						Image = 'http:' + Image
					Views = Views.replace(',','').replace(' views','')
					Runtime = Runtime.strip()
					self.filmliste.append((decodeHtml(Title), Url, Image, Runtime, Views))
		if len(self.filmliste) == 0:
			self.filmliste.append((_('No videos found!'), '', None, '', ''))
		self.ml.setList(map(self._defaultlistleft, self.filmliste))
		self.ml.moveToIndex(0)
		self.keyLocked = False
		self.th_ThumbsQuery(self.filmliste, 0, 1, 2, None, None, self.page, self.lastpage, mode=1)
		self.showInfos()

	def showInfos(self):
		title = self['liste'].getCurrent()[0][0]
		pic = self['liste'].getCurrent()[0][2]
		runtime = self['liste'].getCurrent()[0][3]
		views = self['liste'].getCurrent()[0][4]
		self['name'].setText(title)
		self['handlung'].setText("Runtime: %s\nViews: %s" % (runtime, views))
		CoverHelper(self['coverArt']).getCover(pic)

	def keyOK(self):
		if self.keyLocked:
			return
		Link = 'http://www.redtube.com' + self['liste'].getCurrent()[0][1]
		self.keyLocked = True
		getPage(Link).addCallback(self.getVideoPage).addErrback(self.dataError)

	def getVideoPage(self, data):
		videoPage = re.findall('<source\ssrc="(.*?)"\stype="video/mp4">', data, re.S)
		if videoPage:
			url = videoPage[-1]
			url = url.replace('\/','/').replace('&amp;','&')
			if url.startswith('//'):
				url = 'http:' + url
			self.keyLocked = False
			Title = self['liste'].getCurrent()[0][0]
			self.session.open(SimplePlayer, [(Title, url.replace('%2F','%252F').replace('%3D','%253D').replace('%2B','%252B'))], showPlaylist=False, ltype='redtube')