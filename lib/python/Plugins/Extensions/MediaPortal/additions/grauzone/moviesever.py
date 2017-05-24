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
import requests

glob_agent = 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:35.0) Gecko/20100101 Firefox/35.0'
premium = False
keckse = {}
BASE_URL = 'http://moviesever.com'

class movieseverMain(MPScreen):

	def __init__(self, session):
		self.plugin_path = mp_globals.pluginPath
		self.skin_path = mp_globals.pluginPath + mp_globals.skinsPath
		path = "%s/%s/defaultGenreScreen.xml" % (self.skin_path, config.mediaportal.skin.value)
		if not fileExists(path):
			path = self.skin_path + mp_globals.skinFallback + "/defaultGenreScreen.xml"
		with open(path, "r") as f:
			self.skin = f.read()
			f.close()

		MPScreen.__init__(self, session)

		self["actions"] = ActionMap(["MP_Actions"], {
			"0": self.closeAll,
			"ok" : self.keyOK,
			"cancel": self.keyCancel,
			"up" : self.keyUp,
			"down" : self.keyDown,
			"right" : self.keyRight,
			"left" : self.keyLeft
		}, -1)

		self['title'] = Label("MoviesEver")
		self['ContentTitle'] = Label(_("Genre Selection"))

		self.streamList = []
		self.ml = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
		self['liste'] = self.ml

		self.keyLocked = False
		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self.keyLocked = True
		self.streamList.append(("Filme", BASE_URL+'/filme/page/'))
		self.streamList.append(("Top iMDB 250", BASE_URL+'/top-imdb/'))
		self.ml.setList(map(self._defaultlistcenter, self.streamList))
		self.keyLocked = False
		self.showInfos()

	def keyOK(self):
		exist = self['liste'].getCurrent()
		if self.keyLocked or exist == None:
			return
		auswahl = self['liste'].getCurrent()[0][0]
		url = self['liste'].getCurrent()[0][1]
		self.session.open(movieseverParsing, auswahl, url)

	def keyCancel(self):
		self.close()

class movieseverParsing(MPScreen, ThumbsHelper):

	def __init__(self, session, genre, url):
		self.genre = genre
		self.url = url
		self.plugin_path = mp_globals.pluginPath
		self.skin_path = mp_globals.pluginPath + mp_globals.skinsPath
		path = "%s/%s/defaultListScreen.xml" % (self.skin_path, config.mediaportal.skin.value)
		if not fileExists(path):
			path = self.skin_path + mp_globals.skinFallback + "/defaultListScreen.xml"
		with open(path, "r") as f:
			self.skin = f.read()
			f.close()
		MPScreen.__init__(self, session)
		ThumbsHelper.__init__(self)

		self["actions"] = ActionMap(["MP_Actions"], {
			"0": self.closeAll,
			"5" : self.keyShowThumb,
			"ok" : self.keyOK,
			"cancel": self.keyCancel,
			"up" : self.keyUp,
			"down" : self.keyDown,
			"right" : self.keyRight,
			"left" : self.keyLeft,
			"nextBouquet" : self.keyPageUp,
			"prevBouquet" : self.keyPageDown
		}, -1)

		self['title'] = Label("MoviesEver")
		self['ContentTitle'] = Label("%s" % self.genre)
		self['Page'] = Label(_("Page:"))

		self.streamList = []
		self.ml = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
		self['liste'] = self.ml

		self.page = 1
		self.keyLocked = True
		self.onLayoutFinish.append(self.loadPage)

	def loadPage(self):
		if self.genre == "Filme":
			murl = '%s%s/' % (self.url, self.page)
		else:
			murl = self.url

		self.streamList = []
		self.streamList.append((_('Please wait...'), None))
		self.ml.setList(map(self._defaultlistcenter, self.streamList))
		self.streamList = []
		getPage(murl, agent=glob_agent).addCallback(self.parseData).addErrback(self.dataError)

	def parseData(self, data):
		self.getLastPage(data, '', 'class="pagination"><span>.*?von\s(.*?)</span>')

		if self.genre == "Filme":
			m = re.findall('<article id="post-.*?" class="item movies"><div class="poster"><a href="(.*?)"><img src="(.*?)" alt="(.*?)">', data)
			if m:
				for (url, bild, title) in m:
					self.streamList.append((decodeHtml(title), url, bild))
		else:
			m = re.findall('<div class="image"><div class="poster"><a href="http://moviesever.com/.*?"><img src="(.*?)"/>.*?</div><div class="title"><a href="(.*?)">(.*?)</a>', data)
			if m:
				for (bild, url, title) in m:
					self.streamList.append((decodeHtml(title), url, bild))

		if len(self.streamList) == 0:
			self.streamList.append((_('Parsing error!'), None))
			self.keyLocked = True
		else:
			self.keyLocked = False

		self.ml.setList(map(self._defaultlistleft, self.streamList))
		self.ml.moveToIndex(0)
		self.th_ThumbsQuery(self.streamList, 0, 1, 2, None, None, 1, 1)
		self.showInfos()

	def keyOK(self):
		exist = self['liste'].getCurrent()
		if self.keyLocked or exist == None:
			return
		stream_name = self['liste'].getCurrent()[0][0]
		movie_url = self['liste'].getCurrent()[0][1]
		cover_url = self['liste'].getCurrent()[0][2]
		self.session.open(movieseverStreams, stream_name, movie_url, cover_url)

	def showInfos(self):
		filmName = self['liste'].getCurrent()[0][0]
		self['name'].setText(filmName)
		coverUrl = self['liste'].getCurrent()[0][2]
		CoverHelper(self['coverArt']).getCover(coverUrl)

class movieseverStreams(MPScreen):

	def __init__(self, session, genre, url, cover):
		self.genre = genre
		self.url = url
		self.cover = cover
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
			"0": self.closeAll,
			"ok" : self.keyOK,
			"cancel": self.keyCancel
		}, -1)

		self['title'] = Label("MoviesEver")
		self['ContentTitle'] = Label("%s" % self.genre)

		self.streamList = []
		self.ml = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
		self['liste'] = self.ml

		self.keyLocked = True
		self.onLayoutFinish.append(self.loadPage)

	def loadPage(self):
		CoverHelper(self['coverArt']).getCover(self.cover)
		self.streamList.append((_('Please wait...'), None))
		self.ml.setList(map(self._defaultlistcenter, self.streamList))
		getPage(self.url, agent=glob_agent).addCallback(self.parseData).addErrback(self.dataError)

	def parseData(self, data):
		self.streamList = []
		links = re.findall('"link":"(.*?)"', data, re.S)
		prem = re.findall('class="options" href="#option-\d.*?</b>\s{0,10}(.*?)\s{0,10}<span', data, re.S)
		if links and prem:
			stream_count = 1
			stream_label = 1
			for link in links:
				if not "Premium" in str(prem[stream_count-1]):
					self.streamList.append(('Stream '+str(stream_label), links[stream_count-1].replace('\/','/')))
					stream_label += 1
				stream_count += 1
		if len(self.streamList) == 0:
			self.streamList.append((_('No supported streams found!'), None))
		self.ml.setList(map(self._defaultlistcenter, self.streamList))
		self.keyLocked = False

	def keyOK(self):
		if self.keyLocked:
			return
		stream_name = self['liste'].getCurrent()[0][0]
		movie_crypt = self['liste'].getCurrent()[0][1]
		if not movie_crypt: return
		post_data = {'link': movie_crypt}
		spezialagent = {'User-agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64; rv:53.0) Gecko/20100101 Firefox/53.0'}
		raw_data = requests.post('http://play.seriesever.net/me/moviesever.php', data=post_data, headers=spezialagent)
		data = (raw_data.text)
		streams = re.findall('"link":"(http.*?)"', data, re.S)
		if streams:
			stream_url = str(streams[-1].replace('\/','/'))
			self.session.open(SimplePlayer, [(self.genre, stream_url, self.cover)], cover=True, showPlaylist=False, ltype='moviesever')
		else:
			self.session.open(MessageBoxExt, _("Stream not found, try another Stream Hoster."), MessageBoxExt.TYPE_INFO, timeout=5)