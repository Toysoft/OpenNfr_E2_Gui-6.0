# -*- coding: utf-8 -*-

import glob
from Plugins.Extensions.MediaPortal.plugin import _
from Plugins.Extensions.MediaPortal.resources.imports import *
from Plugins.Extensions.MediaPortal.resources.keyboardext import VirtualKeyBoardExt

# Globals
NL = "\n"
suchCache = ""	# Letzte Sucheingabe
AdT = " "		# Default: Anzahl der Treffer/Clips/Sendungen
BASE_URL = "https://www.zdf.de"
isLost = "Leider nicht (mehr) auf den ZDF-Servern vorhanden (oder ein anderer Grund)."
NoC = "Keine abspielbaren Inhalte verfügbar"
helpText2 = "Sendung"+":"+NL+"Clip-Datum"+":"+NL+"Dauer"+":"
bildchen = "file://%s/zdf.png" % (config.mediaportal.iconcachepath.value + "logos")

def soap(data,flag):
	data = re.sub('itemprop="image" content=""','',data,flags=re.S)
	data = re.sub('<footer.*?</html>','',data,flags=re.S)
	if "<article" in data:
		data = "<article" + re.sub('!DOCTYPE html>.*?\<article','',data,flags=re.S)
	else:
		return
	if flag == "Stream":
		try:
			data = re.sub('<div class="img-container x-large-8 x-column">','<source class="m-16-9" data-srcset="/static~Trash">',data, flags=re.S)
		except:
			pass
	data = data.split("</article>")
	y = 0
	for x in data:
		x = x.split("<article")
		if len(x) == 2:
			x = "<article"+x[1]
		else:
			x = "<article"+x[0]
		z = ("%03d") % y
		with open(config.mediaportal.storagepath.value + "zdf"+z+".soap", "w") as f:
			f.write(x+"</article>")
		y += 1

class ZDFGenreScreen(MPScreen):

	def __init__(self, session):
		self.keyLocked = True
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
			"0"		: self.closeAll,
			"ok"    : self.keyOK,
			"cancel": self.keyCancel,
			"up" : self.keyUp,
			"down" : self.keyDown,
			"right" : self.keyRight,
			"left" : self.keyLeft
		}, -1)

		self['title'] = Label("ZDF Mediathek")
		self['ContentTitle'] = Label("Genre")
		self['name'].setText("Auswahl")

		self.genreliste = []
		self.ml = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
		self['liste'] = self.ml
		self.prev = ""
		self.onLayoutFinish.append(self.loadPage)

	def loadPage(self):
		from os import listdir											# If crashed before...
		if fileExists(config.mediaportal.storagepath.value):			# ...clean up...
			for i in listdir(config.mediaportal.storagepath.value):		# ...to prevent...
				if "zdf" in i and ".soap" in i:							# ...the next...
					os.remove(config.mediaportal.storagepath.value+i)	# ...crash...

		self.keyLocked = True
		self.loadPageData()

	def loadPageData(self):
		self.genreliste = []
		self.genreliste.append(("Suche (alle Kanäle)", "1", "/"))
		self.genreliste.append(("Sendungen A bis Z (alle Kanäle)", "2", "/"))
		self.genreliste.append(("Sendung verpasst? (alle Kanäle)", "3", "/"))
		self.genreliste.append(("Podcasts", "4", "/"))
		self.genreliste.append(("Rubriken", "5", "/"))
		self.genreliste.append(("ZDF", "6", "/"))
		self.genreliste.append(("ZDFneo", "7", "https://www.zdf.de/assets/2400_ZDFneo-100~384x216"))
		self.genreliste.append(("ZDFinfo", "8", "https://www.zdf.de/assets/2400_ZDFinfo-100~384x216"))
		self.genreliste.append(("ZDFtivi", "9", "http://www.heute.de/ZDF/zdfportal/blob/25579432/1/data.jpg"))
		self.ml.setList(map(self._defaultlistleft, self.genreliste))
		self.keyLocked = False
		self.showInfos()

	def showInfos(self):
		cur = self['liste'].getCurrent()[0][1]
		streamPic = self['liste'].getCurrent()[0][2]
		if self.prev == "/" and streamPic == "/":
			return
		else:
			self.prev = streamPic
		if streamPic == "/":
			CoverHelper(self['coverArt']).getCover(bildchen)
		else:
			CoverHelper(self['coverArt']).getCover(streamPic)

	def keyOK(self):
		if self.keyLocked:
			return
		if " (alle Kanäle)" in self['liste'].getCurrent()[0][0]:
			genreName = self['liste'].getCurrent()[0][0].split(" (alle Kanäle)")[0]
		else:
			genreName = self['liste'].getCurrent()[0][0]
		genreFlag = self['liste'].getCurrent()[0][1]
		streamPic = self['liste'].getCurrent()[0][2]
		if genreFlag == "1": # Suche
			self.session.openWithCallback(self.searchCallback, VirtualKeyBoardExt, title = (_("Enter search criteria")), text = suchCache, is_dialog=True)
		elif genreFlag == "6":	# ZDF
			streamLink = "%s/suche?q=&from=&to=&sender=ZDF&attrs=&contentTypes=episode" % BASE_URL
			self.session.open(ZDFStreamScreen,streamLink,genreName,genreFlag,AdT,streamPic)
		elif genreFlag == "7":	# ZDFneo
			streamLink = "%s/suche?q=&from=&to=&sender=ZDFneo&attrs=&contentTypes=episode" % BASE_URL
			self.session.open(ZDFStreamScreen,streamLink,genreName,genreFlag,AdT,streamPic)
		elif genreFlag == "8":	# ZDFinfo
			streamLink = "%s/suche?q=&from=&to=&sender=ZDFinfo&attrs=&contentTypes=episode" % BASE_URL
			self.session.open(ZDFStreamScreen,streamLink,genreName,genreFlag,AdT,streamPic)
		elif genreFlag == "9":	# ZDFtivi
			streamLink = "http://www.tivi.de/tiviVideos/navigation?view=flashXml"
			self.session.open(ZDFPostSelect,genreName,genreFlag,streamPic,streamLink,AdT)
		else:
			self.session.open(ZDFPreSelect,genreName,genreFlag,streamPic)

	def searchCallback(self, callbackStr):
		genreFlag = self['liste'].getCurrent()[0][1]
		self.keyLocked = False
		if callbackStr is not None:
			global suchCache
			suchCache = callbackStr
			genreName = "Suche... ' %s '" % suchCache
			streamLink = "%s/suche?q=%s&from=&to=&sender=alle+Sender&attrs=" % (BASE_URL,callbackStr)
			self.session.open(ZDFStreamScreen,streamLink,genreName,genreFlag,AdT,bildchen)
		else:
			return

class ZDFPreSelect(MPScreen):

	def __init__(self,session,genreName,genreFlag,prePic):
		self.keyLocked = True
		self.gN = genreName
		self.gF = genreFlag
		self.pP = prePic
		self.PLS = False	# PicLoadStop: Nicht jedesmal das gleiche Bild laden
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
			"0"		: self.closeAll,
			"ok"    : self.keyOK,
			"cancel": self.keyCancel,
			"up" : self.keyUp,
			"down" : self.keyDown,
			"right" : self.keyRight,
			"left" : self.keyLeft
		}, -1)

		self['title'] = Label("ZDF Mediathek")

		self.genreliste = []
		self.ml = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
		self['liste'] = self.ml
		self.onLayoutFinish.append(self.loadPage)

	def loadPage(self):
		self.keyLocked = True
		url = ""
		self['name'].setText(_("Please wait..."))
		if self.gF != "4":
			self.loadPageData(self.pP)
		else:
			url = "%s/service-und-hilfe/podcast" % BASE_URL
			getPage(url).addCallback(self.loadPageData).addErrback(self.dataError)

	def loadPageData(self, data):

		self.genreliste = []
		if self.gF == "2":	# A-Z
			self['name'].setText("Buchstabe")
			self['ContentTitle'].setText(self.gN)
			for c in xrange(26):
				self.genreliste.append((chr(ord('A') + c)," "," ",self.pP,AdT))
			self.genreliste.insert(0, ('0-9'," "," ",self.pP,AdT))
		elif self.gF == "3":	# Sendung verpasst?
			self['name'].setText("Sendetag")
			self['ContentTitle'].setText(self.gN)
			for q in range (0,60,1):
				if q == 0:
					s1 = " - Heute"
				elif q == 1:
					s1 = " - Gestern"
				else:
					s1 = ""
				s2 = (datetime.date.today()+datetime.timedelta(days=-q)).strftime("%d.%m.%y")
				s3 = (datetime.date.today()+datetime.timedelta(days=-q)).strftime("20%y-%m-%d")
				self.genreliste.append((s2+s1,s3," ",self.pP,AdT))
		elif self.gF == "4":	# Podcast
			self['ContentTitle'].setText(self.gN)
			folgen = re.findall('<td headers="t-1">(.*?)</td>.*?"t-2">(.*?)</td.*?"t-3"><a href="(.*?)"', data, re.S)
			if folgen:
				for (title,info,assetId) in folgen:
					title = decodeHtml(title)
					self['name'].setText("Auswahl")
					handlung = "Media"+":\t"+info
					self.genreliste.append((title,assetId,handlung,bildchen,"-"))
		elif self.gF == "5":	# Rubriken
			self.genreliste.append(("Comedy", "1", "https://www.zdf.de/assets/comedy-100~384x216"))
			self.genreliste.append(("Doku/Wissen", "2", "https://www.zdf.de/assets/doku-wissen-102~384x216"))
			self.genreliste.append(("Filme/Serien", "3", "https://www.zdf.de/assets/film-serien-100~384x216"))
			self.genreliste.append(("Geschichte", "4", "https://www.zdf.de/assets/geschichte-106~384x216"))
			self.genreliste.append(("Gesellschaft", "5", "https://www.zdf.de/assets/gesellschaft-100~384x216"))
			self.genreliste.append(("Krimi", "6", "https://www.zdf.de/assets/krimi-100~384x216"))
			self.genreliste.append(("Kultur", "7", "https://www.zdf.de/assets/kultur-102~384x216"))
			self.genreliste.append(("Nachrichten", "8", "https://www.zdf.de/assets/nachrichten-100~384x216"))
			self.genreliste.append(("Politik", "9", "https://www.zdf.de/assets/politik-100~384x216"))
			self.genreliste.append(("Show", "10", "https://www.zdf.de/assets/show-100~384x216"))
			self.genreliste.append(("Sport", "11", "https://www.zdf.de/assets/zdfsport-logo-hintergrund-100~384x216"))
			self.genreliste.append(("Verbraucher", "12", "https://www.zdf.de/assets/verbraucher-100~384x216"))
			self['ContentTitle'].setText(self.gN)
		self.ml.setList(map(self._defaultlistleft, self.genreliste))
		self.keyLocked = False
		self.showInfos()

	def showInfos(self):
		if self.gF == "4":
			self['handlung'].setText(self['liste'].getCurrent()[0][2])
		if self.gF == "5":
			self['name'].setText("Auswahl")
			CoverHelper(self['coverArt']).getCover(self['liste'].getCurrent()[0][2])
		if self.PLS == False:
			self.PLS = True
			CoverHelper(self['coverArt']).getCover(bildchen)

	def keyOK(self):
		if self.keyLocked:
			return
		passThru = 0
		auswahl = self['liste'].getCurrent()[0][0]
		extra = self['liste'].getCurrent()[0][1]
		if self.gF == "2":	# A-Z
			if auswahl == "0-9":
				streamLink = "%s/sendungen-a-z?group=0+-+9" % BASE_URL
			else:
				streamLink = "%s/sendungen-a-z?group=%s" % (BASE_URL,auswahl.lower())
			if "(" in self.gN:
				self.gN = self.gN.split(" (")[0]
			self.gN = self.gN+" ( '"+auswahl+"' )"
		elif self.gF == "3":	# Sendung verpasst?
			streamLink = "%s/sendung-verpasst?airtimeDate=%s" % (BASE_URL,extra)
			passThru = 1
			if "(" in self.gN:
				self.gN = self.gN.split(" (")[0]
			self.gN = self.gN+" ("+auswahl+")"
			self.session.open(ZDFStreamScreen,streamLink,self.gN,self.gF,AdT,self.pP)
		elif self.gF == "4":	# Podcast
			passThru = 1
			if "(" in self.gN:
				self.gN = self.gN.split(" (")[0]
			self.gN = self.gN+" ('"+auswahl+"')"
			self.session.open(ZDFStreamScreen,extra,self.gN,self.gF,AdT,self.pP)
		elif self.gF == "5":	# Rubriken
			passThru = 1
			extra = self['liste'].getCurrent()[0][1]
			if extra == "1":
				streamLink = "%s/comedy" % BASE_URL
			if extra == "2":
				streamLink = "%s/doku-wissen" % BASE_URL
			if extra == "3":
				streamLink = "%s/filme-serien" % BASE_URL
			if extra == "4":
				streamLink = "%s/geschichte" % BASE_URL
			if extra == "5":
				streamLink = "%s/gesellschaft" % BASE_URL
			if extra == "6":
				streamLink = "%s/krimi" % BASE_URL
			if extra == "7":
				streamLink = "%s/kultur" % BASE_URL
			if extra == "8":
				streamLink = "%s/nachrichten" % BASE_URL
			if extra == "9":
				streamLink = "%s/politik" % BASE_URL
			if extra == "10":
				streamLink = "%s/show" % BASE_URL
			if extra == "11":
				streamLink = "%s/sport" % BASE_URL
			if extra == "12":
				streamLink = "%s/verbraucher" % BASE_URL
			if "(" in self.gN:
				self.gN = self.gN.split(" (")[0]
			self.gN = self.gN+" ("+auswahl+")"
			self.session.open(ZDFStreamScreen,streamLink,self.gN,self.gF,AdT,self.pP)
		else:
			return
		if passThru == 0 and self.gF == "1":
			self.session.open(ZDFPostSelect,self.gN,self.gF,self.pP,streamLink,"+")
		elif passThru == 0 and self.gF != "1":
			self.session.open(ZDFPostSelect,self.gN,self.gF,self.pP,streamLink,AdT)

class ZDFPostSelect(MPScreen, ThumbsHelper):

	def __init__(self,session,genreName,genreFlag,prePic,streamLink,anzahl):
		self.keyLocked = True
		self.gN = genreName
		self.gN = self.gN.split("(")
		if len(self.gN) == 3 or len(self.gN) == 2:
			self.gN = self.gN[0]+"("+self.gN[1]
		else:
			self.gN = self.gN[0]
		self.gF = genreFlag
		self.pP = prePic
		self.anzahl = anzahl
		self.streamLink = streamLink
		self.PLS = False	# PicLoadStop: Nicht jedesmal das gleiche Bild laden
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
			"ok"    : self.keyOK,
			"cancel": self.keyCancel,
			"5" : self.keyShowThumb,
			"up" : self.keyUp,
			"down" : self.keyDown,
			"right" : self.keyRight,
			"left" : self.keyLeft
		}, -1)

		self['title'] = Label("ZDF Mediathek")
		self['ContentTitle'] = Label("Sendung")
		self['name'] = Label(_("Please wait..."))

		self.genreliste = []
		self.ml = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
		self['liste'] = self.ml
		self.onLayoutFinish.append(self.loadPage)

	def loadPage(self):
		self.keyLocked = True
		self['name'].setText(_("Please wait..."))
		url = self.streamLink
		getPage(url).addCallback(self.loadPageData).addErrback(self.dataError)

	def loadPageData(self, data):
		if self.gF != "9":
			soap(data,"Post")
		if int(self.gF) > 5 and int(self.gF) != 9:	# ZDF, ZDFneo, ZDFinfo, ZDF.kultur
			self.genreliste = []
			treffer = re.findall('<div class="image">.*?<img src="(.*?)" title="(.*?)".*?<div class="text">.*?<a href=".*?<a href=".*?">(.*?)<.*?a href=".*?">(.*?) B.*?</div>', data, re.S)
			for (image,info,title,anzahl) in treffer:
				info = info.replace("\n"," ")
				info = decodeHtml(info)
				handlung = "Clips:\t%s\n" % anzahl
				title = decodeHtml(title)
				asset = image.split('/')
				assetId = asset[3]
				anzahl = anzahl.strip()
				image = image.replace("94x65","485x273")
				image = "%s%s" % ("http://www.zdf.de",image)
				handlung = "Clips:\t"+anzahl+"\n"+info
				self.genreliste.append((title,assetId,handlung,image,anzahl))
			self.gN = "Sendung"	# Überschreibe den Wert als Kennung für Sendungen statt Clips

		elif self.gF == "9":	# ZDFtivi
			self.genreliste = []
			folgen = re.findall('id=".*?" label="(.*?)".*?image="(.*?)" type=".*?">(.*?)<', data, re.S)
			if folgen:
				for (title,image,url) in folgen:
					title = decodeHtml(title)
					image = "http://www.tivi.de%s" % image
					image = image.replace("tiviNavBild","tiviTeaserbild")
					handlung = "Clips:\t"+"Keine Angaben"
					self.genreliste.append((title,url,handlung,image,AdT))
		else:
			self.genreliste = []
			tmp = sorted(glob.glob(config.mediaportal.storagepath.value + "*.soap"))
			if tmp:
				for x in tmp:
					with open(x, 'r') as f:
						data = f.read()
					os.remove(x)
					folgen = re.findall('picture class.*?data-srcset="(.*?)~.*?itemprop=\"genre\">(.*?)<.*?m-border\">(.*?) .*?data-plusbar-title=\"(.*?)\".*?data-plusbar-url=\"(.*?)\"', data, re.S)
					if folgen:
						for (image,genre,anzahl,title,url) in folgen:
							image += "~384x216"
							genre = decodeHtml(genre).strip().split("|")[0].strip()
							title = decodeHtml(title)
							handlung = "Clips:\t"+anzahl
							if genre:
								if genre != "":
									handlung = handlung + "\nKontext:\t"+genre
							self.genreliste.append((title,url,handlung,image,anzahl))
			else:
				self.genreliste.append((NoC,None,"",bildchen,None))
		self.ml.setList(map(self._defaultlistleft, self.genreliste))
		self.keyLocked = False
		self.th_ThumbsQuery(self.genreliste, 0, 1, 3, None, None, 1, 1, mode=1)
		self.showInfos()

	def showInfos(self):
		self['handlung'].setText(self['liste'].getCurrent()[0][2])
		if "(" in self.gN:
			self.gN = self.gN.split(" (")
			name = self.gN[0]+"\n\n("+self.gN[1]
			self['name'].setText(name)
			self.gN = self.gN[0]+" ("+self.gN[1]
		else:
			self['name'].setText(self.gN)
		if self.PLS == False and self.gF != "9" and self.gF != "2" and self.gF != "4":
			self.PLS = True
			CoverHelper(self['coverArt']).getCover(bildchen)
		elif self.gF == "9" or self.gF == "2":
			CoverHelper(self['coverArt']).getCover(self['liste'].getCurrent()[0][3])

	def keyOK(self):
		if self.keyLocked:
			return
		sendung = self['liste'].getCurrent()[0][0]
		if sendung == NoC:
			return
		anzahl = self['liste'].getCurrent()[0][4]
		image = self['liste'].getCurrent()[0][3]
		if self.gF == "9": #tivi
			streamLink = self['liste'].getCurrent()[0][1]
			self.session.open(ZDFStreamScreen,streamLink,self['liste'].getCurrent()[0][0],self.gF,anzahl," "," ")
		else:
			streamLink = self['liste'].getCurrent()[0][1]
			self.session.open(ZDFStreamScreen,streamLink,self.gN,self.gF,anzahl,image,sendung)

class ZDFStreamScreen(MPScreen, ThumbsHelper):

	def __init__(self, session,streamLink,genreName,genreFlag,anzahl,image,sendung="---"):
		self.keyLocked = True
		self.streamL = streamLink
		self.gN = genreName
		self.gF = genreFlag
		self.anzahl = anzahl
		self.PLS = False	# PicLoadStop: Prevent always loading the same Pic
		self.sendung = sendung
		self.image = image
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
			"ok"    : self.keyOK,
			"cancel": self.keyCancel,
			"5" : self.keyShowThumb,
			"up" : self.keyUp,
			"down" : self.keyDown,
			"right" : self.keyRight,
			"left" : self.keyLeft,
			"nextBouquet" : self.keyPageUp,
			"prevBouquet" : self.keyPageDown
			}, -1)

		self['title'] = Label("ZDF Mediathek")
		self['ContentTitle'] = Label("Clip")
		self['name'] = Label(_("Please wait..."))

		self['Page'] = Label(_("Page:"))
		self.page = 1
		self.lastpage = 1
		self.filmliste = []
		self.dur = "0:00"
		self.ml = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
		self['liste'] = self.ml
		self.onLayoutFinish.append(self.loadPage)

	def loadPage(self):
		self.keyLocked = True
		self.keyLocked = True
		if self.gF == "9":
			self.streamLink = "%s%s" % ("http://www.tivi.de",self.streamL)
		elif self.gF == "1" or self.gF == "6" or self.gF == "7" or self.gF == "8":
			self.streamLink = self.streamL + "&page=" + str(self.page)
		else:
			self.streamLink = self.streamL
		self['page'].setText(str(self.page)+' / '+str(self.lastpage))
		self['name'].setText(_("Please wait..."))
		getPage(self.streamLink).addCallback(self.loadPageData).addErrback(self.dataError)

	def loadPageData(self, data):
		pages = re.search('result-count="(.*?)"',data)
		if pages != None and pages.group(1) != None:
			self.lastpage = int(int(pages.group(1)))/24+1
		if self.lastpage == 0:
			self.lastpage = 1
		self['page'].setText(str(self.page)+' / '+str(self.lastpage))

		if self.gF != "9":	# tivi
			soap(data,"Stream")

		self.filmliste = []
		typ,image,title,info,assetId,sender,sendung,dur = "","","","","","","",""
		if self.gF == "3": # Sendung verpasst?
			self['page'].setText('1 / 1')
			genre = ""
			tmp = sorted(glob.glob(config.mediaportal.storagepath.value + "*.soap"))
			for x in tmp:
				with open(x, 'r') as f:
					data = f.read()
				os.remove(x)
				treffer = re.findall('<article.*?itemprop=\"image\" content=\"(.*?)\".*?\"teaser-label\".*?</span>(.*?)<strong>(.*?)<.*?title=\"(.*?)\".*?teaser-info.*?>(.*?)<.*?data-plusbar-id=\"(.*?)\"', data, re.S)
				if treffer:
					for (image,airtime,clock,title,dur,assetId) in treffer:
						if "/static" in image:
							try:
								if "m-16-9" in data:
									image = re.search('<source class=\"m-16-9\".*?data-srcset=\"(.*?)\"',data)
								if image:
									image = image.group(1)
							except:
								image = "ToBeParsed~xyz"
						if "?layout" in image:
							image = image.split("=")[0]+"="
						else:
							image = image.split("~")[0]
						if image == "ToBeParsed":
							image = self.image
						elif image[-1] == "=":
							image += "384x216"
						else:
							image += "~384x216"
						title = decodeHtml(title)
						handlung = "Clip-Datum"+":\t"+airtime+clock+NL+"Dauer"+":\t"+dur
						self.dur = dur
						assetId = "https://api.zdf.de/content/documents/"+assetId+".json?profile=player"
						if 'itemprop="genre"' in data:
							try:
								genre = re.search("itemprop=\"genre\">(.*?)<",data,re.S).group(1).strip()
							except:
								pass
							if genre != "":
									handlung = handlung + "\nKontext:\t"+genre
						self.filmliste.append((title,assetId,handlung,image,title))
		elif self.gF == "4": # Podcast
			self['page'].setText("1 / 1")
			image = re.search('<itunes:image href="(.*?)"',data).group(1)
			treffer = re.findall('<item>.*?<title>(.*?)</ti.*?<itunes:summary>(.*?)</itunes.*?<enclosure url="(.*?)".*?<pubDate>(.*?)</pub.*?<itunes:duration>(.*?)</it', data, re.S)
			if treffer:
				for (title,info,streamLink,airtime,dur) in treffer:
					info = info.replace("\n"," ")
					info = decodeHtml(info)
					airtime = airtime.split(" +")[0]
					title = decodeHtml(title)
					dur = int(dur)
					self.dur = str(int(dur/60))+" min"
					handlung = "Kanal"+":\tPodcast"+NL+"Clip-Datum"+":\t"+airtime+NL+"Dauer"+":\t"+self.dur+NL+info
					self.filmliste.append((title,streamLink,handlung,image,title))
		elif self.gF == "9":	# ZDFtivi
			treffer = re.findall('<ns3:video-teaser>.*?<ns3:headline>(.*?)</ns3:he.*?<ns3:image>(.*?)</ns3:im.*?<ns3:page>(.*?)</ns3:pa.*?<ns3:text>(.*?)</ns3:te.*?<ns3:duration>.*?T(.*?)</ns3:du', data, re.S)
			if treffer:
				for (name,image,url,inf,dur) in treffer:
					info = ""
					if inf != None:
						info = inf.replace("\n"," ")
						info = decodeHtml(info)
					url = "http://www.tivi.de%s" % url
					image = "http://www.tivi.de%s" % image
					stdP = dur.split("H")
					minP = stdP[1].split("M")
					secP = minP[1].split(".")
					std = stdP[0]
					min = minP[0]
					sec = secP[0]
					if int(std) < 10:
						std = "0"+std
					if int(min) < 10:
						min = "0"+min
					if int(sec) < 10:
						sec = "0"+sec
					dur = "%s:%s:%s" % (std,min,sec)
					handlung = "Kanal:\tZDFtivi (ZDF)\nDauer:\t"+dur+NL+info
					self.dur = dur
					self.filmliste.append((decodeHtml(name),url,handlung,image,self.gN))
		else:
			tmp = sorted(glob.glob(config.mediaportal.storagepath.value + "*.soap"))
			for x in tmp:
				with open(x, 'r') as f:
					data = f.read()
				os.remove(x)
				if not "<article" in data:
					continue
				airtime = ""
				dur = ""
				sender = ""
				assetId = ""
				title = ""
				image = ""
				info = ""
				genre = ""
				if "<time datetime" in data and not "m-border" in data:
					continue
				if "Beiträge" in data:
					continue
				elif "m-border\">" in data:
					airtime = re.search('time datetime=.*?>(.*?)<',data)
				if airtime != "":
					airtime = airtime.group(1)
				if airtime == "":
					continue
				if "m-border\">" in data:
					dur = re.search('m-border\">(.*?)<',data).group(1)
				else:
					continue
				if "data-station" in data:
					sender = re.search('data-station="(.*?)"',data).group(1)
				else:
					sender = "---"
				if not "data-plusbar-id=" in data:
					continue
				else:
					assetId = re.search('data-plusbar-id="(.*?)"',data).group(1)
				if '<source class="m-16-9"' in data:
					image = re.search('<source class=\"m-16-9\".*?data-srcset=\"(.*?)[,\"]',data)
					if image:
						image = image.group(1)
						if "?layout" in image:
							image = image.split("=")[0]+"="
						else:
							image = image.split("~")[0]
				if image != "":
					if "/static" in image:
						try:
							if "https:\/\/www.zdf.de\/assets\/" in data:
								image = re.search('https:\\\/\\\/www.zdf.de\\\/assets\\\/(.*?)~',data)
							if image:
								image = image.group(1)
								image = "https://www.zdf.de/assets/"+image
						except:
							image = "ToBeParsed~xyz"
							image = image.split("~")[0]
							try:
								image = re.search("data-zdfplayer-teaser-image-overwrite=\'\{(.*?)\&#",data)
								if image:
									image = image.group(1)+"="
									image = image.replace("\/","/")
									image = "https"+image.split("https")[1]
							except:
								image = "ToBeParsed"
								pass
					if image == None:
						image = "ToBeParsed"
					if image == "ToBeParsed":
						image = bildchen
					elif image[-1] == "=":
						image += "384x216"
					else:
						image += "~384x216"
				else:
					image = bildchen
				if not 'data-plusbar-title=' in data or "Aktuell im EPG" in data:
					continue
				else:
					title = re.search('data-plusbar-title="(.*?)"',data).group(1)
				if 'description">' in data and not 'description"><' in data:
					info = re.findall('description">(.*?)<',data,re.S)[0]
					info = decodeHtml(stripAllTags(info).strip())
				if '<span class="teaser-cat' in data:
					sendung = re.findall('<span class="teaser-cat.*?>(.*?)</span>',data,re.S)[0]
					sendung = decodeHtml(sendung)
					sendung = sendung.split("|")[-1].strip()
				else:
					sendung = "---"
				if self.gF != "1" and sendung == "---":
					sendung = self.sendung
				if 'itemprop="genre"' in data:
					try:
						genre = " ("+re.search("itemprop=\"genre\">(.*?)<",data,re.S).group(1).strip().split("|")[0].strip()+")"
					except:
						pass
				handlung = "Sendung"+":\t"+sendung+genre+NL+"Clip-Datum"+":\t"+airtime+NL+"Dauer"+":\t"+dur+"\n"+info
				assetId = "https://api.zdf.de/content/documents/"+assetId+".json?profile=player"
				self.filmliste.append((decodeHtml(title),assetId,handlung,image,sendung))
			if self.filmliste == []:
				self.filmliste.append((NoC,None,"",self.image,None))

		self.ml.setList(map(self._defaultlistleft, self.filmliste))
		self.ml.moveToIndex(0)
		self.keyLocked = False
		self.th_ThumbsQuery(self.filmliste, 0, 1, 3, None, None, self.page, self.lastpage, mode=1)
		self.showInfos()

	def showInfos(self):
		if self['liste'].getCurrent()[0][3] == "" or self['liste'].getCurrent()[0][3] == "/":
			CoverHelper(self['coverArt']).getCover(bildchen)
		elif self['liste'].getCurrent()[0][0] == NoC:
			self['name'].setText("- - -")
			CoverHelper(self['coverArt']).getCover(bildchen)
		else:
			self.streamPic = self['liste'].getCurrent()[0][3]
			if self.gF == "1":	# Suche
				self['name'].setText("Suche"+ "' "+suchCache+" '")
			elif self.gF == "9":	# tivi
				self['name'].setText("Sendung / Thema"+"\n' "+self.gN+" '")
			elif NoC in self['liste'].getCurrent()[0][0]:	# Nichts gefunden
				self['name'].setText(NoC)
			else:
				if "(" in self.gN:
					self.gN = self.gN.split(" (")
					name = self.gN[0]+"\n\n("+self.gN[1]
					self['name'].setText(name)
					self.gN = self.gN[0]+" ("+self.gN[1]
				else:
					self['name'].setText(self.gN)
			self['handlung'].setText(self['liste'].getCurrent()[0][2])
			if self.PLS == False:
				CoverHelper(self['coverArt']).getCover(self.streamPic)
			if self.gF == "4":	# Podcast
				self.PLS = True
		self.keyLocked = False

	def keyOK(self):
		if self.keyLocked:
			return
		self['name'].setText(_("Please wait..."))
		streamName = self['liste'].getCurrent()[0][0]
		streamLink = self['liste'].getCurrent()[0][1]
		if streamName == NoC:	# Nichts gefunden
			self.loadPage()
		elif self.gF == "4":	# Podcast
			playlist = []
			playlist.append((streamName, streamLink))
			self.session.open(SimplePlayer, playlist, showPlaylist=False, ltype='zdf')
			self['name'].setText(self['liste'].getCurrent()[0][4])
		else:
			if self.gF == "9":	# tivi
				url = self['liste'].getCurrent()[0][1]
				getPage(url).addCallback(self.getTivi).addErrback(self.dataError)
			else:
				getPage(streamLink, headers={'Api-Auth':'Bearer d2726b6c8c655e42b68b0db26131b15b22bd1a32', 'Accept':'application/vnd.de.zdf.v1.0+json'}).addCallback(self.getTemplateJson).addErrback(self.dataError)

	def getTemplateJson(self,data):
		a = json.loads(data)
		b = a['mainVideoContent']['http://zdf.de/rels/target']['http://zdf.de/rels/streams/ptmd-template']
		if b:
			b = b.replace('{playerId}','ngplayer_2_3')
			b = "https://api.zdf.de"+b
			getPage(str(b), headers={'Api-Auth':'Bearer d2726b6c8c655e42b68b0db26131b15b22bd1a32', 'Accept':'application/vnd.de.zdf.v1.0+json'}).addCallback(self.getContentJson).addErrback(self.dataError)
		else:
			return

	def getContentJson(self,data):
		a = json.loads(data)
		b = []
		for x in range (0,5,1):
			try:
				b.append((a['priorityList'][1]['formitaeten'][0]['qualities'][x]['audio']['tracks'][0]['uri']))
			except:
				break
		self.keyLocked = False
		streamName = self['liste'].getCurrent()[0][0]
		c = b[0]
		c = c.replace("1496k","3296k")
		c = c.replace("p13v13","p15v13")
		url = str(c).replace("https","http")
		if '.f4m' in url:
			b = []
			for x in range (0,5,1):
				try:
					b.append((a['priorityList'][0]['formitaeten'][0]['qualities'][x]['audio']['tracks'][0]['uri']))
				except:
					break
			self.keyLocked = False
			streamName = self['liste'].getCurrent()[0][0]
			url = str(b[0])
		playlist = []
		playlist.append((streamName, url))
		try:
			self.session.open(SimplePlayer, playlist, showPlaylist=False, ltype='zdf', forceGST=True)
		except Exception,e:
			print str(e)
			self.keyCancel()
		if self.gF == "1":
			self['name'].setText("Suche"+ "' "+suchCache+" '")
		else:
			if "(" in self.gN:
				self.gN = self.gN.split(" (")
				name = self.gN[0]+"\n\n("+self.gN[1]
				self['name'].setText(name)
				self.gN = self.gN[0]+" ("+self.gN[1]
			else:
				self['name'].setText(self.gN)

	def getTivi(self, data):
		self.keyLocked = True
		streamName = self['liste'].getCurrent()[0][0]
		streamQ = re.findall('basetype="h264_aac_mp4_http.*?quality>veryhigh</.*?quality>.*?url>(http://[nrodl|rodl].*?)</.*?url>', data, re.S)
		if streamQ:
			streamLink = streamQ[0]
		self.keyLocked = False
		if streamLink:
			playlist = []
			playlist.append((streamName, streamLink))
			self.session.open(SimplePlayer, playlist, showPlaylist=False, ltype='zdf')
			self['name'].setText("Sendung / Thema"+"\n' "+self['liste'].getCurrent()[0][4]+" '")