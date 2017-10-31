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
from enigma import eLabel

headers = {'Accept': 'application/vnd.twitchtv.v5+json', 'Client-ID': '6r2dhbo9ek6mm1gab2snj0navo4sgqy'}
limit = 19

class twitchGames(MPScreen):

	def __init__(self, session):
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
			"prevBouquet" : self.keyPageDown,
			"green" : self.keyPageNumber
		}, -1)

		self['title'] = Label("Twitch")
		self['ContentTitle'] = Label("Games:")
		self['F2'] = Label(_("Page"))

		self['Page'] = Label(_("Page:"))
		self.keyLocked = True
		self.page = 1

		self.gameList = []
		self.ml = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
		self['liste'] = self.ml

		self.onLayoutFinish.append(self.loadPage)

	def loadPage(self):
		self.gameList = []
		url = "https://api.twitch.tv/kraken/games/top?limit=" + str(limit) + "&offset=" + str((self.page-1) * limit)
		getPage(url, headers=headers).addCallback(self.parseData).addErrback(self.dataError)

	def parseData(self, data):
		topGamesJson = json.loads(data)
		try:
			lastp = round((float(topGamesJson["_total"]) / limit) + 0.5)
			self.lastpage = int(lastp)
			self['page'].setText(str(self.page) + ' / ' + str(self.lastpage))
		except:
			self.lastpage = 999
			self['page'].setText(str(self.page))
		for node in topGamesJson["top"]:
			self.gameList.append((str(node["game"]["name"]), str(node["game"]["box"]["large"])));
		self.ml.moveToIndex(0)
		self.ml.setList(map(self._defaultlistleft, self.gameList))
		self.keyLocked = False
		self.showInfos()

	def showInfos(self):
		title = self['liste'].getCurrent()[0][0]
		pic = self['liste'].getCurrent()[0][1]
		self['name'].setText(title)
		CoverHelper(self['coverArt']).getCover(pic)

	def keyOK(self):
		if self.keyLocked or self['liste'].getCurrent() == None:
			return
		self.session.open(twitchChannels, self['liste'].getCurrent()[0][0])

class twitchChannels(MPScreen):

	def __init__(self, session, gameName):
		self.gameName = gameName
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
			"prevBouquet" : self.keyPageDown,
			"green" : self.keyPageNumber
		}, -1)

		self['title'] = Label("Twitch")
		self['ContentTitle'] = Label("Channels:")
		self['F2'] = Label(_("Page"))

		self['Page'] = Label(_("Page:"))
		self.keyLocked = True
		self.page = 1

		self.channelList = []
		self.ml = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
		self['liste'] = self.ml

		self.onLayoutFinish.append(self.loadPage)

	def loadPage(self):
		self.channelList = []
		url = "https://api.twitch.tv/kraken/search/streams?query=" + self.gameName.replace(" ", "%20") + "&limit=" + str(limit) + "&offset=" + str((self.page-1) * limit) + "&hls=true"
		getPage(url, headers=headers).addCallback(self.parseData).addErrback(self.dataError)

	def parseData(self, data):
		self.textRenderer = eLabel(self.instance)
		self.textRenderer.hide()
		topChannelsJson = json.loads(data)
		try:
			lastp = round((float(topChannelsJson["_total"]) / limit) + 0.5)
			self.lastpage = int(lastp)
			self['page'].setText(str(self.page) + ' / ' + str(self.lastpage))
		except:
			self.lastpage = 999
			self['page'].setText(str(self.page))
		for node in topChannelsJson["streams"]:
			length = self._calcTextWidth(str(node["channel"]["display_name"]))
			if length != -1:
				title = str(node["channel"]["display_name"])
			else:
				title = str(node["channel"]["name"])
			self.channelList.append((title, str(node["channel"]["name"]), str(node["preview"]["large"])))
		self.ml.moveToIndex(0)
		self.ml.setList(map(self._defaultlistleft, self.channelList))
		self.keyLocked = False
		self.showInfos()

	def _calcTextWidth(self, text, font=None, size=None):
		height = self['liste'].l.getItemSize().height()
		self.textRenderer.setFont(gFont(mp_globals.font, height - 2 * mp_globals.sizefactor))
		self.textRenderer.setText(text)
		return self.textRenderer.calculateSize().width()

	def showInfos(self):
		title = self['liste'].getCurrent()[0][0]
		pic = self['liste'].getCurrent()[0][2]
		self['name'].setText(title)
		CoverHelper(self['coverArt']).getCover(pic)

	def keyOK(self):
		if self.keyLocked or self['liste'].getCurrent() == None:
			return
		self.channelName = self['liste'].getCurrent()[0][1]
		url = "http://api.twitch.tv/api/channels/" + self.channelName + "/access_token"
		getPage(url, headers=headers).addCallback(self.parseAccessToken).addErrback(self.dataError)

	def parseAccessToken(self, data):
		token = json.loads(data)
		url = "http://usher.twitch.tv/api/channel/hls/{channel}.m3u8?player=twitchweb&&token={token}&sig={sig}&allow_audio_only=true&allow_source=true&type=any&p={random}'"
		url = url.replace("{random}", str(random.randint(1000000, 9999999)))
		url = url.replace("{sig}", str(token["sig"]))
		url = url.replace("{token}", str(token["token"]))
		url = url.replace("{channel}", str(self.channelName))
		getPage(url, headers={}).addCallback(self.parseM3U).addErrback(self.dataError)

	def parseM3U(self, data):
		self.session.open(twitchStreamQuality, data, self.channelName, self.gameName)

class twitchStreamQuality(MPScreen):

	def __init__(self, session, m3u8, channel, game):
		self.m3u8 = str(m3u8)
		self.channel = channel
		self.game = game
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
			"cancel": self.keyCancel
		}, -1)

		self['title'] = Label("Twitch")
		self['ContentTitle'] = Label("Quality:")

		self.qualityList = []
		self.ml = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
		self['liste'] = self.ml

		self.keyLocked = True
		self.onLayoutFinish.append(self.parseData)

	def parseData(self):
		result = re.findall('NAME="(.*?)".*?(http://.*?)\n', self.m3u8, re.S)
		for (quality, url) in result:
			if quality != "Mobile":
				self.qualityList.append((quality, url));
		self.ml.setList(map(self._defaultlistleft, self.qualityList))
		self.keyLocked = False

	def keyOK(self):
		if self.keyLocked or self['liste'].getCurrent() == None:
			return
		url = self['liste'].getCurrent()[0][1]
		title = self.game + " - " + self.channel
		self.session.open(SimplePlayer, [(title, url)], showPlaylist=False, ltype='twitch', forceGST=True)