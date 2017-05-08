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

class arteFirstScreen(MPScreen):

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
			"0"		: self.closeAll,
			"ok"	: self.keyOK,
			"cancel": self.keyCancel
		}, -1)

		self['title'] = Label("arte Mediathek")
		self['ContentTitle'] = Label(_("Genre:"))
		self['name'] = Label(_("Selection:"))

		self.keyLocked = True
		self.filmliste = []
		self.ml = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
		self['liste'] = self.ml

		self.onLayoutFinish.append(self.genreData)


	def genreData(self):
		self.filmliste.append(("Neueste", "http://www.arte.tv/papi/tvguide/videos/plus7/program/D/L2/ALL/ALL/-1/AIRDATE_DESC/0/0/DE_FR.json"))
		self.filmliste.append(("Meistgesehen", "http://www.arte.tv/papi/tvguide/videos/plus7/program/D/L2/ALL/ALL/-1/VIEWS/0/0/DE_FR.json"))
		self.filmliste.append(("Letzte Chance", "http://www.arte.tv/papi/tvguide/videos/plus7/program/D/L2/ALL/ALL/-1/LAST_CHANCE/0/0/DE_FR.json"))
		self.filmliste.append(("Themen", "by_channel"))
		self.filmliste.append(("Datum", "by_date"))
		self.ml.setList(map(self._defaultlistcenter, self.filmliste))
		self.keyLocked = False

	def keyOK(self):
		if self.keyLocked:
			return
		Name = self['liste'].getCurrent()[0][0]
		Link = self['liste'].getCurrent()[0][1]
		if 'http://' in Link:
			self.session.open(arteSecondScreen, Link, Name)
		else:
			self.session.open(arteSubGenreScreen, Link, Name)

class arteSubGenreScreen(MPScreen):

	def __init__(self, session, Link, Name):
		self.Link = Link
		self.Name = Name
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
			"0"		: self.closeAll,
			"ok"	: self.keyOK,
			"cancel": self.keyCancel
		}, -1)

		self['title'] = Label("arte Mediathek")
		self['ContentTitle'] = Label(_("Genre:") + " %s" % Name)
		self['name'] = Label(_("Selection:"))

		self.keyLocked = True
		self.filmliste = []
		self.ml = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
		self['liste'] = self.ml

		self.onLayoutFinish.append(self.loadPage)

	def loadPage(self):
		if self.Name == "Datum":
			today = datetime.date.today()
			for daynr in range(0,7):
				day1 = today -datetime.timedelta(days=daynr)
				dateselect =  day1.strftime('%Y-%m-%d')
				link = 'http://www.arte.tv/papi/tvguide/videos/plus7/program/D/L2/ALL/ALL/-1/AIRDATE_DESC/0/0/DE_FR/%s.json' % dateselect
				self.filmliste.append((dateselect, link))
		elif self.Name == "Themen":
			link = 'http://www.arte.tv/papi/tvguide/videos/plus7/program/D/L2/%s/ALL/-1/AIRDATE_DESC/0/0/DE_FR.json'
			self.filmliste.append(('Aktuelles & Gesellschaft', link % 'ACT'))
			self.filmliste.append(('Fernsehfilme & Serien', link % 'FIC'))
			self.filmliste.append(('Kino', link % 'CIN'))
			self.filmliste.append(('Kunst & Kultur', link % 'ART'))
			self.filmliste.append(('Popkultur & Alternativ', link % 'CUL'))
			self.filmliste.append(('Entdeckung', link % 'DEC'))
			self.filmliste.append(('Geschichte', link % 'HIS'))
			self.filmliste.append(('Junior', link % 'JUN'))
		self.ml.setList(map(self._defaultlistcenter, self.filmliste))
		self.keyLocked = False

	def keyOK(self):
		exist = self['liste'].getCurrent()
		if self.keyLocked or exist == None:
			return
		Name = self['liste'].getCurrent()[0][0]
		Link = self['liste'].getCurrent()[0][1]
		self.session.open(arteSecondScreen, Link, Name)

class arteSecondScreen(MPScreen, ThumbsHelper):

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
			"0"		: self.closeAll,
			"ok"	: self.keyOK,
			"cancel": self.keyCancel,
			"5" : self.keyShowThumb,
			"up" : self.keyUp,
			"down" : self.keyDown,
			"right" : self.keyRight,
			"left" : self.keyLeft,
			"blue" :  self.keyTxtPageDown,
			"red" :  self.keyTxtPageUp
		}, -1)

		self['title'] = Label("arte Mediathek")
		self['ContentTitle'] = Label(_("Selection:") + " %s" % self.Name)
		self['F1'] = Label(_("Text-"))
		self['F4'] = Label(_("Text+"))

		self.page = 1
		self.lastpage = 1
		self.keyLocked = True
		self.filmliste = []
		self.ml = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
		self['liste'] = self.ml
		self.onLayoutFinish.append(self.loadPage)

	def loadPage(self):
		self['name'].setText(_('Please wait...'))
		url = self.Link
		getPage(url, agent=std_headers, headers={'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest', 'Referer': self.Link}).addCallback(self.parseData).addErrback(self.dataError)

	def parseData(self, data):
		try:
			player = json.loads(data)
			try:
				if player.has_key('programDEList'):
					for node in player["programDEList"]:
						subtitle = node.get('STL', '')
						if subtitle:
							title = "%s - %s" % (node.get('TIT'), node.get('STL', ''))
						else:
							title = node.get('TIT')
						handlung = "%s min\n%s" % (str(int(node['VDO'].get('videoDurationSeconds', ''))/60), node.get('DTW', ''))
						self.filmliste.append((title.encode('utf-8'),node['VDO'].get('videoStreamUrl', '').encode('utf-8'),node['VDO'].get('programImage', '').encode('utf-8'),handlung.encode('utf-8')))
			except:
				pass
		except:
			pass
		if len(self.filmliste) == 0:
			self.filmliste.append((_("No videos found!"), '','','','',''))
		self.ml.setList(map(self._defaultlistleft, self.filmliste))
		self.keyLocked = False
		self.th_ThumbsQuery(self.filmliste, 0, 1, 2, None, None, self.page, self.lastpage, mode=1)
		self.showInfos()

	def showInfos(self):
		title = self['liste'].getCurrent()[0][0]
		self.ImageUrl = self['liste'].getCurrent()[0][2]
		handlung = self['liste'].getCurrent()[0][3]
		self['name'].setText(_(title))
		self['handlung'].setText(handlung)
		CoverHelper(self['coverArt']).getCover(self.ImageUrl)

	def keyOK(self):
		exist = self['liste'].getCurrent()
		if self.keyLocked or exist == None:
			return
		self.title = self['liste'].getCurrent()[0][0]
		link = self['liste'].getCurrent()[0][1]
		getPage(link, headers={'Content-Type': 'application/json', 'X-Requested-With': 'XMLHttpRequest'}).addCallback(self.getStream).addErrback(self.dataError)

	def getStream(self, data):
		streamSQ = re.findall('"HBBTV","VQU":"SQ","VMT":"mp4","VUR":"(.*?)"', data)
		if streamSQ:
			self.playStream(streamSQ[0])
		else:
			streamEQ = re.findall('"HBBTV","VQU":"EQ","VMT":"mp4","VUR":"(.*?)"', data)
			if streamEQ:
				self.playStream(streamEQ[0])

	def playStream(self, url):
		self.session.open(SimplePlayer, [(self.title, url, self.ImageUrl)], showPlaylist=False, ltype='arte')