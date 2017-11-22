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
from Plugins.Extensions.MediaPortal.resources.twagenthelper import twAgentGetPage

agent='Mozilla/5.0 (Windows NT 6.1; rv:44.0) Gecko/20100101 Firefox/44.0'
headers = {
	'Accept-Language':'de,en-US;q=0.7,en;q=0.3',
	'X-Requested-With':'XMLHttpRequest',
	}
default_cover = "file://%s/hclips.png" % (config.mediaportal.iconcachepath.value + "logos")

class hclipsGenreScreen(MPScreen):

	def __init__(self, session):
		MPScreen.__init__(self, session, skin='MP_Plugin')

		self["actions"] = ActionMap(["MP_Actions"], {
			"ok" : self.keyOK,
			"0" : self.closeAll,
			"cancel" : self.keyCancel,
			"up" : self.keyUp,
			"down" : self.keyDown,
			"right" : self.keyRight,
			"left" : self.keyLeft
		}, -1)

		self['title'] = Label("HClips.com")
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
		url = "https://www.hclips.com/categories/"
		getPage(url, agent=agent).addCallback(self.genreData).addErrback(self.dataError)

	def genreData(self, data):
		parse = re.search('class="thumb_holder(.*?)class="cat-text">', data, re.S)
		Cats = re.findall('<a\shref="(https://www.hclips.com/categories/.*?)".*?class="img"\ssrc="(.*?)".*?class="title">(.*?)</strong', parse.group(1), re.S)
		if Cats:
			for (Url, Image, Title) in Cats:
				self.genreliste.append((Title, Url, Image))
			self.genreliste.sort()
			self.genreliste.insert(0, ("Longest", "https://www.hclips.com/longest/", default_cover))
			self.genreliste.insert(0, ("Most Popular", "https://www.hclips.com/most-popular/", default_cover))
			self.genreliste.insert(0, ("Top Rated", "https://www.hclips.com/top-rated/", default_cover))
			self.genreliste.insert(0, ("Most Recent", "https://www.hclips.com/latest-updates/", default_cover))
			self.genreliste.insert(0, ("--- Search ---", "", default_cover))
			self.ml.setList(map(self._defaultlistcenter, self.genreliste))
			self.keyLocked = False
		self.showInfos()

	def showInfos(self):
		Image = self['liste'].getCurrent()[0][2]
		CoverHelper(self['coverArt']).getCover(Image)

	def keyOK(self):
		if self.keyLocked:
			return
		Name = self['liste'].getCurrent()[0][0]
		Link = self['liste'].getCurrent()[0][1]
		if re.search('--- Search', Name):
			self.session.openWithCallback(self.SuchenCallback, VirtualKeyBoardExt, title = (_("Enter search criteria")), text = self.suchString, is_dialog=True, auto_text_init=False, suggest_func=self.getSuggestions)
		else:
			self.session.open(hclipsFilmScreen, Link, Name)

	def SuchenCallback(self, callback):
		if callback is not None and len(callback):
			Name = "--- Search ---"
			self.suchString = callback
			Link = callback
			self.session.open(hclipsFilmScreen, Link, Name)

	def getSuggestions(self, text, max_res):
		url = "https://www.hclips.com/cloudsearch/suggesters.php?char=%s" % urllib.quote_plus(text)
		d = twAgentGetPage(url, agent=agent, headers=headers, timeout=5)
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

class hclipsFilmScreen(MPScreen, ThumbsHelper):

	def __init__(self, session, Link, Name):
		self.Link = Link
		self.Name = Name
		MPScreen.__init__(self, session, skin='MP_PluginDescr')
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

		self['title'] = Label("HClips.com")
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
		if not re.search('Search', self.Name):
			url = "%s%s/" % (self.Link, str(self.page))
		else:
			key = "AIzaSyCVAXiUzRYsML1Pv6RwSG1gunmMikTzQqY"
			start = (self.page-1)*20
			cx = "007041593788150376897:8pvxilcjx8e"
			q = "%s%s" % (self.Link,"%20inurl%3A%2F")
			url = "https://www.googleapis.com/customsearch/v1element?key=%s&num=20&hl=en&prettyPrint=false&cx=%s&q=%s&filter=0&start=%s"%(key,cx,q,start)
		twAgentGetPage(url, agent=agent, gzip_decoding=True).addCallback(self.loadData).addErrback(self.dataError)

	def loadData(self, data):
		if not re.search('Search', self.Name):
			self.getLastPage(data, 'class="pagination(.*?)</div>')
			parse = re.search('class="thumb_holder">(.*?)class="heading"', data, re.S)
			Movies = re.findall('<a\shref="(https://www.hclips.com/videos/.*?)"\sclass="thumb">.*?<img\ssrc="(.*?)".*?class="dur">(.*?)</span>.*?class="title">(.*?)</strong>.*?small_views">Views:\s(\d+)</span>.*?small_added-date">Added:\s(.*?)</span>', parse.group(1), re.S)
			if Movies:
				for (Url, Image, Runtime, Title, Views, Added) in Movies:
					self.filmliste.append((decodeHtml(Title), Url, Image, Runtime, Views, Added))
		else:
			if ('results' in data):
				data = json.loads(data)
				try: self.lastpage = data['cursor']['pages'][-1]['label']
				except KeyError: lastpage = 1
				self['page'].setText(str(self.page) + ' / ' + str(self.lastpage))
				for e in data['results']:
					Url = e['unescapedUrl'].encode('utf-8')
					Title = e['titleNoFormatting'].split("|")[0].encode('utf-8')
					Content = e.get('contentNoFormatting','None').encode('utf-8').replace("\\n","").replace("\n","")
					try: Image = e['richSnippet']['cseImage']['src'].encode('utf-8')
					except KeyError: Image = None
					items = re.findall('Duration: (.*?)\sViews: (\d+)\s+Added:\s(.*?\s\w+\sago)', Content, re.S)
					if items:
						Runtime, Views, Added = items[0]
					else:
						Runtime, Views, Added = "", "", ""
					self.filmliste.append((Title, Url, Image, Runtime, Views, Added))
		if len(self.filmliste) == 0:
			self.filmliste.append((_('No movies found!'), None, None, None, None, None))
		self.ml.setList(map(self._defaultlistleft, self.filmliste))
		self.ml.moveToIndex(0)
		self.keyLocked = False
		self.th_ThumbsQuery(self.filmliste, 0, 1, 2, None, None, self.page, self.lastpage, mode=1)
		self.showInfos()

	def showInfos(self):
		Url = self['liste'].getCurrent()[0][1]
		if Url == None:
			return
		title = self['liste'].getCurrent()[0][0]
		pic = self['liste'].getCurrent()[0][2]
		runtime = self['liste'].getCurrent()[0][3]
		views = self['liste'].getCurrent()[0][4]
		added = self['liste'].getCurrent()[0][5]
		self['name'].setText(title)
		self['handlung'].setText("Runtime: %s\nViews: %s\nAdded: %s" % (runtime, views, added))
		CoverHelper(self['coverArt']).getCover(pic)

	def keyOK(self):
		if self.keyLocked:
			return
		Link = self['liste'].getCurrent()[0][1]
		if Link == None:
			return
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
		decstring = re.findall('video_url=(.*?)\(', data, re.S)
		decoder = re.findall('(%s=function.*?};)' % decstring[0], data, re.S)
		if decoder:
			video_url = re.findall('(var video_url.*?;)', data, re.S)
			js = decoder[0] + "\n" + video_url[0] + "return video_url;"
		url = str(node.exec_(js))
		self.keyLocked = False
		Title = self['liste'].getCurrent()[0][0]
		self.session.open(SimplePlayer, [(Title, url)], showPlaylist=False, ltype='hclips')