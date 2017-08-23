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

baseurl = "http://www.servustv.com"
stvAgent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36'

class sTVGenreScreen(MPScreen):

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
			"ok"    : self.keyOK,
			"0" : self.closeAll,
			"cancel": self.keyCancel
		}, -1)

		self['title'] = Label("ServusTV")
		self['ContentTitle'] = Label("Genre:")

		self.genreliste = []
		self.ml = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
		self['liste'] = self.ml

		self.onLayoutFinish.append(self.layoutFinished)

	def layoutFinished(self):
		self.genreliste.append(("Aktuelles", "/de/Themen/Aktuelles"))
		self.genreliste.append(("Das Salzkammergut", "/de/Videos/Alle-Videos-zu-Sendungen/Das-Salzkammergut"))
		self.genreliste.append(("Die Frühstückerinnen", "/de/Videos/Alle-Videos-zu-Sendungen/Die-Fruehstueckerinnen"))
		self.genreliste.append(("Dokumentationen", "/de/Videos/Dokumentationen"))
		self.genreliste.append(("Kultur", "/de/Themen/Kultur"))
		self.genreliste.append(("Mei Tracht mei Gwand", "/de/Videos/Alle-Videos-zu-Sendungen/Mei-Tracht-mei-Gwand"))
		self.genreliste.append(("Natur", "/de/Themen/Natur"))
		self.genreliste.append(("Neueste", "/de/Videos/Neueste-Videos"))
		self.genreliste.append(("Sport", "/de/Themen/Sport"))
		self.genreliste.append(("Städte Trips", "/de/Videos/Alle-Videos-zu-Sendungen/Staedte-Trips"))
		self.genreliste.append(("Süsser am Morgen", "/de/Videos/Alle-Videos-zu-Sendungen/Suesser-am-Morgen"))
		self.genreliste.append(("Top Videos", "/de/Videos/Top-Videos"))
		self.genreliste.append(("Unterhaltung", "/de/Themen/Unterhaltung"))
		self.genreliste.append(("Volkskultur", "/de/Themen/Volkskultur"))
		self.genreliste.append(("Wissen", "/de/Themen/Wissen"))
		self.ml.setList(map(self._defaultlistcenter, self.genreliste))

	def keyOK(self):
		name = self['liste'].getCurrent()[0][0]
		url = self['liste'].getCurrent()[0][1]
		url = baseurl + url + "?page="
		self.session.open(sTVids,name,url)

class sTVids(MPScreen):

	def __init__(self, session,name,url):
		self.Link = url
		self.Name = name
		self.plugin_path = mp_globals.pluginPath
		self.skin_path = mp_globals.pluginPath + mp_globals.skinsPath

		path = "%s/%s/defaultListWideScreen.xml" % (self.skin_path, config.mediaportal.skin.value)
		if not fileExists(path):
			path = self.skin_path + mp_globals.skinFallback + "/defaultListWideScreen.xml"

		with open(path, "r") as f:
			self.skin = f.read()
			f.close()

		MPScreen.__init__(self, session)

		self["actions"] = ActionMap(["MP_Actions"], {
			"ok"    : self.keyOK,
			"0" : self.closeAll,
			"cancel": self.keyCancel,
			"up" : self.keyUp,
			"down" : self.keyDown,
			"right" : self.keyRight,
			"left" : self.keyLeft,
			"nextBouquet" : self.keyPageUp,
			"prevBouquet" : self.keyPageDown
		}, -1)

		self.keyLocked = True
		self['title'] = Label("ServusTV")
		self['ContentTitle'] = Label("Genre: %s" % self.Name)
		self['name'] = Label(_("Please wait..."))

		self['Page'] = Label(_("Page:"))
		self.page = 1
		self.lastpage = 1

		self.filmliste = []
		self.ml = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
		self['liste'] = self.ml

		self.onLayoutFinish.append(self.loadPage)

	def loadPage(self):
		self.keyLocked = True
		url = "%s%s" % (self.Link, str(self.page))
		getPage(url, agent=stvAgent).addCallback(self.loadPageData).addErrback(self.dataError)

	def loadPageData(self, data):
		self.getLastPage(data, 'class="org paging(.*?)</ul>', '.*page=(\d+)')
		raw = re.findall('block-(.*?)class="org\sFooter">', data, re.S)
		shows = re.findall('href="(/de/Medien/.*?)".*?src="(.*?)".*?videoleange">(.*?)<.*?<h4.*?">(.*?)</.*?subtitel">(.*?)<', raw[0], re.S)
		if shows:
			self.filmliste = []
			for (url,pic,leng,title,stitle) in shows:
				title = title.strip() + " - " + stitle.strip()
				pic = baseurl + pic
				self.filmliste.append((decodeHtml(title),url,pic,leng))
			self.ml.setList(map(self._defaultlistleft, self.filmliste))
			self.ml.moveToIndex(0)
			self.keyLocked = False
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
		self['name'] = Label(_("Please wait..."))
		url = baseurl + self['liste'].getCurrent()[0][1]
		getPage(url, agent=stvAgent).addCallback(self.getID).addErrback(self.dataError)

	def getID(self, data):
		id = re.findall('data-videoid="(.*?)"', data, re.S)[0]
		account = re.findall('data-account="(.*?)"', data, re.S)[0]
		url = "https://edge.api.brightcove.com/playback/v1/accounts/%s/videos/%s" % (account, id)
		getPage(url, agent=stvAgent, headers={'Accept':'application/json;pk=BCpkADawqM3hYrTRw2Gi3RgqoRH8EXAdhKTIf0ZYTeLzvF3i0Fns90ytp8xkt58hAXj8NHdlT5Zz2fosHIwHoGkobH6Y7UXotgwSAqCKR5GiZKtI7xkJnKKJ6c47s43U7dCYpDan1-KyDOpS'}).addCallback(self.getVideo).addErrback(self.dataError)

	def getVideo(self, data):
		video = re.findall('"width":\d+,"src":"(.*?)",', data, re.S)
		title = self['liste'].getCurrent()[0][0]
		self['name'].setText(title)
		self.keyLocked = False
		self.session.open(SimplePlayer, [(title, video[-1])], showPlaylist=False, ltype='servustv', forceGST=True)