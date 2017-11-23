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

SHOW_HANG_STAT = False

# General imports
from . import _
from Tools.BoundFunction import boundFunction
from base64 import b64decode as bsdcd
from resources.imports import *
from resources.update import *
from resources.simplelist import *
from resources.simpleplayer import SimplePlaylistIO
from resources.twagenthelper import twAgentGetPage, twDownloadPage
from resources.configlistext import ConfigListScreenExt
from resources.pininputext import PinInputExt
from resources.decrypt import *
from resources.realdebrid import realdebrid_oauth2
try:
	from Components.config import ConfigPassword
except ImportError:
	ConfigPassword = ConfigText

from twisted.internet import task
from resources.twisted_hang import HangWatcher

CONFIG = "/usr/lib/enigma2/python/Plugins/Extensions/MediaPortal/additions/additions.xml"

desktopSize = getDesktop(0).size()
if desktopSize.width() == 1920:
	mp_globals.videomode = 2
	mp_globals.fontsize = 30
	mp_globals.sizefactor = 3

try:
	from enigma import eMediaDatabase
	mp_globals.isDreamOS = True
except:
	mp_globals.isDreamOS = False

try:
	from Components.ScreenAnimations import *
	mp_globals.animations = True
	sa = ScreenAnimations()
	sa.fromXML(resolveFilename(SCOPE_PLUGINS, "Extensions/MediaPortal/resources/animations.xml"))
except:
	mp_globals.animations = False

try:
	from Components.CoverCollection import CoverCollection
	if mp_globals.isDreamOS:
		mp_globals.covercollection = True
	else:
		mp_globals.covercollection = False
except:
	mp_globals.covercollection = False

try:
	from enigma import eWall, eWallPythonMultiContent, BT_SCALE
	from Components.BaseWall import BaseWall
	class CoverWall(BaseWall):
		def setentry(self, entry):
			res = [entry]
			res.append((eWallPythonMultiContent.TYPE_COVER, eWallPythonMultiContent.SHOW_ALWAYS, loadPNG(entry[2]), BT_SCALE))
			return res
	mp_globals.isVTi = True
except:
	mp_globals.isVTi = False

try:
	from enigma import getVTiVersionString
	mp_globals.fakeScale = True
except:
	try:
		import boxbranding
		mp_globals.fakeScale = True
	except:
		if fileExists("/etc/.box"):
			mp_globals.fakeScale = True
		else:
			mp_globals.fakeScale = False

try:
	import requests
except:
	requestsModule = False
else:
	requestsModule = True

try:
	from Plugins.Extensions.MediaInfo.plugin import MediaInfo
	MediaInfoPresent = True
except:
	try:
		from Plugins.Extensions.mediainfo.plugin import mediaInfo
		MediaInfoPresent = True
	except:
		MediaInfoPresent = False

def lastMACbyte():
	try:
		return int(open('/sys/class/net/eth0/address').readline().strip()[-2:], 16)
	except:
		return 256

def calcDefaultStarttime():
	try:
		# Use the last MAC byte as time offset (half-minute intervals)
		offset = lastMACbyte() * 30
	except:
		offset = 7680
	return (5 * 60 * 60) + offset

def downloadPage(url, path):
	agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.82 Safari/537.36"
	return twDownloadPage(url, path, timeout=30, agent=agent)

def grabpage(pageurl, method='GET', postdata={}):
	agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/48.0.2564.82 Safari/537.36"
	if requestsModule:
		try:
			import urlparse
			s = requests.session()
			url = urlparse.urlparse(pageurl)
			if method == 'GET':
				headers = {'User-Agent': agent}
				page = s.get(url.geturl(), headers=headers)
			return page.content
		except:
			return None
	else:
		return None

from Components.config import ConfigClock, ConfigSequence

class ConfigPORNPIN(ConfigInteger):
        def __init__(self, default, len = 4, censor = ""):
                ConfigSequence.__init__(self, seperator = ":", limits = [(1000, (10**len)-1)], censor_char = censor, default = default)

config.mediaportal = ConfigSubsection()

# Fake entry fuer die Kategorien
config.mediaportal.fake_entry = NoSave(ConfigNothing())

# EPG Import
config.mediaportal.epg_enabled = ConfigOnOff(default = False)
config.mediaportal.epg_runboot = ConfigOnOff(default = False)
config.mediaportal.epg_wakeupsleep = ConfigOnOff(default = False)
config.mediaportal.epg_wakeup = ConfigClock(default = calcDefaultStarttime())
config.mediaportal.epg_deepstandby = ConfigSelection(default = "skip", choices = [
		("wakeup", _("Wake up and import")),
		("skip", _("Skip the import"))
		])

# Allgemein
config.mediaportal.version = NoSave(ConfigText(default="2017112201"))
config.mediaportal.autoupdate = ConfigYesNo(default = True)

config.mediaportal.retries = ConfigSubsection()

config.mediaportal.pincode = ConfigPIN(default = 0000)
config.mediaportal.retries.pincode = ConfigSubsection()
config.mediaportal.retries.pincode.tries = ConfigInteger(default = 3)
config.mediaportal.retries.pincode.time = ConfigInteger(default = 0)

config.mediaportal.adultpincode = ConfigPORNPIN(default = random.randint(1,999), len = 4)
config.mediaportal.retries.adultpin = ConfigSubsection()
config.mediaportal.retries.adultpin.tries = ConfigInteger(default = 3)
config.mediaportal.retries.adultpin.time = ConfigInteger(default = 0)

config.mediaportal.showporn = ConfigYesNo(default = False)
config.mediaportal.showuseradditions = ConfigYesNo(default = False)
config.mediaportal.pinuseradditions = ConfigYesNo(default = False)
config.mediaportal.ena_suggestions = ConfigYesNo(default = True)

config.mediaportal.animation_coverart = ConfigSelection(default = "mp_crossfade_fast", choices = [("mp_crossfade_fast", _("Crossfade (fast)")),("mp_crossfade_slow", _("Crossfade (slow)"))])
config.mediaportal.animation_label = ConfigSelection(default = "mp_crossfade_fast", choices = [("mp_crossfade_fast", _("Crossfade (fast)")),("mp_crossfade_slow", _("Crossfade (slow)"))])
config.mediaportal.animation_simpleplayer = ConfigSelection(default = "mp_player_animation", choices = [("mp_player_animation", _("Slide from bottom")),("mp_crossfade_slow", _("Crossfade"))])

skins = []
if mp_globals.videomode == 2:
	mp_globals.skinsPath = "/skins_1080"
	for skin in os.listdir("/usr/lib/enigma2/python/Plugins/Extensions/MediaPortal/skins_1080/"):
		if os.path.isdir(os.path.join("/usr/lib/enigma2/python/Plugins/Extensions/MediaPortal/skins_1080/", skin)):
			skins.append(skin)
	config.mediaportal.skin = ConfigSelection(default = "clean_fhd", choices = skins)
	mp_globals.skinFallback = "/clean_fhd"
else:
	mp_globals.skinsPath = "/skins_720"
	for skin in os.listdir("/usr/lib/enigma2/python/Plugins/Extensions/MediaPortal/skins_720/"):
		if os.path.isdir(os.path.join("/usr/lib/enigma2/python/Plugins/Extensions/MediaPortal/skins_720/", skin)):
			skins.append(skin)
	config.mediaportal.skin = ConfigSelection(default = "original", choices = skins)
	mp_globals.skinFallback = "/original"

if mp_globals.covercollection:
	config.mediaportal.ansicht = ConfigSelection(default = "wall2", choices = [("wall2", _("Wall 2.0")), ("wall", _("Wall")), ("liste", _("List"))])
elif mp_globals.videomode == 2 and mp_globals.isVTi:
	config.mediaportal.ansicht = ConfigSelection(default = "wall_vti", choices = [("wall_vti", _("Wall VTi")), ("wall", _("Wall")), ("liste", _("List"))])
elif mp_globals.videomode == 2 and mp_globals.fakeScale:
	config.mediaportal.ansicht = ConfigSelection(default = "wall", choices = [("wall", _("Wall")), ("liste", _("List"))])
elif mp_globals.videomode == 2 and not mp_globals.isDreamOS:
	config.mediaportal.ansicht = ConfigSelection(default = "liste", choices = [("liste", _("List"))])
else:
	config.mediaportal.ansicht = ConfigSelection(default = "wall", choices = [("wall", _("Wall")), ("liste", _("List"))])
config.mediaportal.wallmode = ConfigSelection(default = "color", choices = [("color", _("Color")),("bw", _("Black&White")),("color_zoom", _("Color (Zoom)")),("bw_zoom", _("Black&White (Zoom)"))])
config.mediaportal.wall2mode = ConfigSelection(default = "color", choices = [("color", _("Color")),("bw", _("Black&White"))])
config.mediaportal.selektor = ConfigSelection(default = "white", choices = [("blue", _("Blue")),("green", _("Green")),("red", _("Red")),("turkis", _("Aqua")),("white", _("White"))])
config.mediaportal.use_hls_proxy = ConfigYesNo(default = False)
config.mediaportal.hls_proxy_ip = ConfigIP(default = [127,0,0,1], auto_jump = True)
config.mediaportal.hls_proxy_port = ConfigInteger(default = 0, limits = (0,65535))
config.mediaportal.hls_buffersize = ConfigInteger(default = 32, limits = (1,64))
config.mediaportal.storagepath = ConfigText(default="/tmp/mediaportal/tmp/", fixed_size=False)
config.mediaportal.iconcachepath = ConfigText(default="/usr/lib/enigma2/python/Plugins/Extensions/MediaPortal/", fixed_size=False)
config.mediaportal.autoplayThreshold = ConfigInteger(default = 50, limits = (1,100))
config.mediaportal.filter = ConfigSelection(default = "ALL", choices = ["ALL", "Mediathek", "User-additions", "Fun", "NewsDoku", "Sport", "Music", "Porn"])
config.mediaportal.youtubeenablevp9 = ConfigYesNo(default = False)
config.mediaportal.youtubeenabledash = ConfigYesNo(default = False)
config.mediaportal.youtubeprio = ConfigSelection(default = "2", choices = [("0", "360p"),("1", "480p"),("2", "720p"),("3", "1080p"),("4", "1440p"),("5", "2160p")])
config.mediaportal.videoquali_others = ConfigSelection(default = "2", choices = [("0", _("Low")),("1", _("Medium")),("2", _("High"))])
config.mediaportal.youtube_max_items_pp = ConfigInteger(default = 19, limits = (10,50))
config.mediaportal.pornpin = ConfigYesNo(default = True)
config.mediaportal.pornpin_cache = ConfigSelection(default = "0", choices = [("0", _("never")), ("5", _("5 minutes")), ("15", _("15 minutes")), ("30", _("30 minutes")), ("60", _("60 minutes"))])
config.mediaportal.kidspin = ConfigYesNo(default = False)
config.mediaportal.setuppin = ConfigYesNo(default = False)
config.mediaportal.watchlistpath = ConfigText(default="/etc/enigma2/", fixed_size=False)
config.mediaportal.sortplugins = ConfigSelection(default = "abc", choices = [("hits", "Hits"), ("abc", "ABC"), ("user", "User")])
config.mediaportal.pagestyle = ConfigSelection(default="Graphic", choices = ["Graphic", "Text"])
config.mediaportal.debugMode = ConfigSelection(default="Silent", choices = ["High", "Normal", "Silent"])
config.mediaportal.font = ConfigSelection(default = "1", choices = [("1", "Mediaportal 1")])
config.mediaportal.showAsThumb = ConfigYesNo(default = False)
config.mediaportal.restorelastservice = ConfigSelection(default = "1", choices = [("1", _("after SimplePlayer quits")),("2", _("after MediaPortal quits"))])
config.mediaportal.backgroundtv = ConfigYesNo(default = False)
config.mediaportal.minitv = ConfigYesNo(default = True)
config.mediaportal.simplelist_key = ConfigSelection(default = "showMovies", choices = [("showMovies", _("PVR/VIDEO")),("instantRecord", _("RECORD"))])

# Konfiguration erfolgt in SimplePlayer
config.mediaportal.sp_playmode = ConfigSelection(default = "forward", choices = [("forward", _("Forward")),("backward", _("Backward")),("random", _("Random")),("endless", _("Endless"))])
config.mediaportal.sp_scrsaver = ConfigSelection(default = "off", choices = [("on", _("On")),("off", _("Off")),("automatic", _("Automatic"))])
config.mediaportal.sp_on_movie_stop = ConfigSelection(default = "ask", choices = [("ask", _("Ask user")), ("quit", _("Return to previous service"))])
config.mediaportal.sp_on_movie_eof = ConfigSelection(default = "ask", choices = [("ask", _("Ask user")), ("quit", _("Return to previous service")), ("pause", _("Pause movie at end"))])
config.mediaportal.sp_seekbar_sensibility = ConfigInteger(default = 10, limits = (1,50))
config.mediaportal.sp_infobar_cover_off = ConfigYesNo(default = False)
config.mediaportal.sp_use_number_seek = ConfigYesNo(default = True)
config.mediaportal.sp_pl_number = ConfigInteger(default = 1, limits = (1,99))
config.mediaportal.sp_mi_key = ConfigSelection(default = "instantRecord", choices = [("displayHelp", _("HELP")),("showMovies", _("PVR/VIDEO")),("instantRecord", _("RECORD"))])
config.mediaportal.sp_use_yt_with_proxy = ConfigSelection(default = "no", choices = [("no", _("No")), ("prz", "with Premiumize"), ("rdb", "with Real-Debrid"), ("proxy", "with a HTTP Proxy")])
config.mediaportal.sp_on_movie_start = ConfigSelection(default = "ask", choices = [("start", _("Start from the beginning")), ("ask", _("Ask user")), ("resume", _("Resume from last position"))])
config.mediaportal.sp_save_resumecache = ConfigYesNo(default = False)
config.mediaportal.premiumize_yt_buffering_opt = ConfigSelection(default = "off", choices = [("off", _("Off")), ("smart", _("Smart")), ("all", _("Always"))])
config.mediaportal.premiumize_use_yt_buffering_size = ConfigSelection(default = "2", choices = [("0", _("Whole file size")), ("1", "1MB"), ("2", "2MB"), ("5", "5MB"), ("10", "10MB")])
config.mediaportal.sp_imdb_key = ConfigSelection(default = "info", choices = [("displayHelp", _("HELP")),("showMovies", _("PVR/VIDEO")),("info", _("EPG/INFO"))])
config.mediaportal.yt_proxy_username = ConfigText(default="user!", fixed_size=False)
config.mediaportal.yt_proxy_password = ConfigPassword(default="pass!", fixed_size=False)
config.mediaportal.yt_proxy_host = ConfigText(default = "example_proxy.com!", fixed_size = False)
config.mediaportal.yt_proxy_port = ConfigInteger(default = 8080, limits = (0,65535))
config.mediaportal.hlsp_proxy_username = ConfigText(default="user!", fixed_size=False)
config.mediaportal.hlsp_proxy_password = ConfigPassword(default="pass!", fixed_size=False)
config.mediaportal.hlsp_proxy_host = ConfigText(default = "example_proxy.com!", fixed_size = False)
config.mediaportal.hlsp_proxy_port = ConfigInteger(default = 8080, limits = (0,65535))
config.mediaportal.sp_use_hlsp_with_proxy = ConfigSelection(default = "no", choices = [("no", _("No")), ("always", "Use it always"), ("plset", "Set in the playlist")])

# premiumize.me
config.mediaportal.premiumize_use = ConfigYesNo(default = False)
config.mediaportal.premiumize_username = ConfigText(default="user!", fixed_size=False)
config.mediaportal.premiumize_password = ConfigPassword(default="pass!", fixed_size=False)
config.mediaportal.premiumize_proxy_config_url = ConfigText(default="", fixed_size=False)

# real-debrid.com
config.mediaportal.realdebrid_use = ConfigYesNo(default = False)
config.mediaportal.realdebrid_accesstoken = ConfigText(default="", fixed_size=False)
config.mediaportal.realdebrid_refreshtoken = ConfigText(default="", fixed_size=False)
config.mediaportal.realdebrid_rclient_id = ConfigText(default="", fixed_size=False)
config.mediaportal.realdebrid_rclient_secret = ConfigText(default="", fixed_size=False)

# Premium Hosters
config.mediaportal.premium_color = ConfigSelection(default="0xFFFF00", choices = [("0xFF0000",_("Red")),("0xFFFF00",_("Yellow")),("0x00FF00",_("Green")),("0xFFFFFF",_("White")),("0x00ccff",_("Light Blue")),("0x66ff99",_("Light Green"))])

# Userchannels Help
config.mediaportal.show_userchan_help = ConfigYesNo(default = True)

# SimpleList
config.mediaportal.simplelist_gcoversupp = ConfigYesNo(default = True)

# Radio
config.mediaportal.is_radio = ConfigYesNo(default=False)

mp_globals.bsp = bsdcd(bsdcd(bsdcd(decrypt('Sz/1Vnx8fHysl9jsO32INqWDtQEsyyDPYlBc56P675cPRhMtaLEseb91C9KBEFa3EZ+PMz9EDz6zBc8t9jzgepxFy3B/XABw6bVPLEDyQJ7AUhDMlMtawA==', CONFIG, 256))))
mp_globals.yt_a = bsdcd(bsdcd(bsdcd(decrypt('kj8yV97e3t4fDPdo3ca07O6kKsuY9oZkvUqpBPJPkvzRYyzeAuLofAra3HKWsJmhvQ8EsGMDfnziGjqj3047WS8bojGewMj+in3daO4hlTSA6GUSwft7LNFdibC0hxTppR1VLXaRvKs=', CONFIG, 256))))
mp_globals.yt_i = bsdcd(bsdcd(bsdcd(decrypt('6T8yV5mZmZkf3mpGhQOBtEl8qSHI314cYq7dLTlEswoOTaaMktY5N37bfxUXGzUcKMBVEjMRiiTOSkNBaOzfKLy3tPmUvE3dYv2CAmayBgrftcOkb7hMaz6Y/jAQym1oT6E/X7P7tpComuUMFWJhDhSuYYt1o3CFx3j53vFgAdUdsWNlN96bgwCEUaJr4JeuaCh+4mMZbN0mDHb0D8jscSZ1MJ97En2ZMRbanG5O/e/3d3kvxN4dU0PaVy4qRUQ9UEhO0XL1E0eV2S4dORGFqXeLTvs=', CONFIG, 256))))
mp_globals.yt_s = bsdcd(bsdcd(bsdcd(decrypt('LUAyV6SkpKS3bO2Io81BlkONIwZfjHfCJgDdZMqw47QAGmIZT7tupMulXgbH+EkiOqKf84cqJX4T0EJYyhfiWF2Fy3Tb/nRdkzlcv5GgCF8rXFo1rFTW5ibXzsHu5HCmqRLW5meGHTo=', CONFIG, 256))))
mp_globals.bdmt = bsdcd(bsdcd(bsdcd(decrypt('Q8fFWGdnZ2djFfvOea2AHqS5bqR9nO0b8bxJ433nOffxa5nD1ELvd/Nm9sdojTjgz0knJTFI2jl0RYrtf4c5YnqSS3hkiq+CjpnV3uQG4Kr5wZZ91zKE3A==', CONFIG, 256))))

# Global variable
autoStartTimer = None
_session = None

# eUriResolver Imports for DreamOS
###############################################################################################
try:
	from enigma import eUriResolver

	from resources.MPYoutubeUriResolver import MPYoutubeUriResolver
	MPYoutubeUriResolver.instance = MPYoutubeUriResolver()
	eUriResolver.addResolver(MPYoutubeUriResolver.instance)

	from resources.MPHLSPUriResolver import MPHLSPUriResolver
	MPHLSPUriResolver.instance = MPHLSPUriResolver()
	eUriResolver.addResolver(MPHLSPUriResolver.instance)

	from resources.MPEuronewsUriResolver import MPEuronewsUriResolver
	MPEuronewsUriResolver.instance = MPEuronewsUriResolver()
	eUriResolver.addResolver(MPEuronewsUriResolver.instance)

except ImportError:
	pass
###############################################################################################


conf = xml.etree.cElementTree.parse(CONFIG)
for x in conf.getroot():
	if x.tag == "set" and x.get("name") == 'additions':
		root =  x
		for x in root:
			if x.tag == "plugin":
				if x.get("type") == "mod":
					modfile = x.get("modfile")
					if fileExists('/etc/enigma2/mp_override/'+modfile.split('.')[1]+'.py'):
						sys.path.append('/etc/enigma2/mp_override')
						exec("from "+modfile.split('.')[1]+" import *")
					else:
						exec("from additions."+modfile+" import *")
					exec("config.mediaportal."+x.get("confopt")+" = ConfigYesNo(default = "+x.get("default")+")")

xmlpath = resolveFilename(SCOPE_PLUGINS, "Extensions/MediaPortal/additions/")
for file in os.listdir(xmlpath):
	if file.endswith(".xml") and file != "additions.xml":
		useraddition = xmlpath + file

		conf = xml.etree.cElementTree.parse(useraddition)
		for x in conf.getroot():
			if x.tag == "set" and x.get("name") == 'additions_user':
				root =  x
				for x in root:
					if x.tag == "plugin":
						if x.get("type") == "mod":
							modfile = x.get("modfile")
							if fileExists('/etc/enigma2/mp_override/'+modfile.split('.')[1]+'.py'):
								sys.path.append('/etc/enigma2/mp_override')
								exec("from "+modfile.split('.')[1]+" import *")
							else:
								exec("from additions."+modfile+" import *")
							exec("config.mediaportal."+x.get("confopt")+" = ConfigYesNo(default = "+x.get("default")+")")

class CheckPathes:

	def __init__(self, session):
		self.session = session
		self.cb = None

	def checkPathes(self, cb):
		self.cb = cb
		res, msg = SimplePlaylistIO.checkPath(config.mediaportal.watchlistpath.value, '', True)
		if not res:
			self.session.openWithCallback(self._callback, MessageBoxExt, msg, MessageBoxExt.TYPE_ERROR)

		res, msg = SimplePlaylistIO.checkPath(config.mediaportal.storagepath.value, '', True)
		if not res:
			self.session.openWithCallback(self._callback, MessageBoxExt, msg, MessageBoxExt.TYPE_ERROR)

		if mp_globals.pluginPath in config.mediaportal.iconcachepath.value:
			config.mediaportal.iconcachepath.value = "/usr/lib/enigma2/python/Plugins/Extensions/MediaPortal/"
			config.mediaportal.iconcachepath.save()
			configfile.save()
		elif "/tmp/" in config.mediaportal.iconcachepath.value:
			config.mediaportal.iconcachepath.value = "/usr/lib/enigma2/python/Plugins/Extensions/MediaPortal/"
			config.mediaportal.iconcachepath.save()
			configfile.save()
		elif "/usr/lib/enigma2/" in config.mediaportal.iconcachepath.value:
			config.mediaportal.iconcachepath.value = "/usr/lib/enigma2/python/Plugins/Extensions/MediaPortal/"
			config.mediaportal.iconcachepath.save()
			configfile.save()
		elif "/var/share/" in config.mediaportal.iconcachepath.value:
			config.mediaportal.iconcachepath.value = "/usr/lib/enigma2/python/Plugins/Extensions/MediaPortal/"
			config.mediaportal.iconcachepath.save()
			configfile.save()

		res, msg = SimplePlaylistIO.checkPath(config.mediaportal.iconcachepath.value + "icons/", '', True)
		if not res:
			self.session.openWithCallback(self._callback, MessageBoxExt, msg, MessageBoxExt.TYPE_ERROR)

		res, msg = SimplePlaylistIO.checkPath(config.mediaportal.iconcachepath.value + "icons_bw/", '', True)
		if not res:
			self.session.openWithCallback(self._callback, MessageBoxExt, msg, MessageBoxExt.TYPE_ERROR)

		res, msg = SimplePlaylistIO.checkPath(config.mediaportal.iconcachepath.value + "icons_zoom/", '', True)
		if not res:
			self.session.openWithCallback(self._callback, MessageBoxExt, msg, MessageBoxExt.TYPE_ERROR)

		res, msg = SimplePlaylistIO.checkPath(config.mediaportal.iconcachepath.value + "logos/", '', True)
		if not res:
			self.session.openWithCallback(self._callback, MessageBoxExt, msg, MessageBoxExt.TYPE_ERROR)

	def _callback(self, answer):
		if self.cb:
			self.cb()

class PinCheck:

	def __init__(self):
		self.pin_entered = False
		self.timer = eTimer()
		if mp_globals.isDreamOS:
			self.timer_conn = self.timer.timeout.connect(self.lock)
		else:
			self.timer.callback.append(self.lock)

	def pinEntered(self):
		self.pin_entered = True
		self.timer.start(60000*int(config.mediaportal.pornpin_cache.value), 1)

	def lock(self):
		self.pin_entered = False

pincheck = PinCheck()

class CheckPremiumize:

	def __init__(self, session):
		self.session = session

	def premiumize(self):
		if config.mediaportal.premiumize_use.value:
			self.puser = config.mediaportal.premiumize_username.value
			self.ppass = config.mediaportal.premiumize_password.value
			url = "https://api.premiumize.me/pm-api/v1.php?method=accountstatus&params[login]=%s&params[pass]=%s" % (self.puser, self.ppass)
			r_getPage(url, timeout=15).addCallback(self.premiumizeData).addErrback(self.dataError)
		else:
			self.session.open(MessageBoxExt, _("premiumize.me is not activated."), MessageBoxExt.TYPE_ERROR)

	def premiumizeData(self, data):
		if re.search('status":200', data):
			infos = re.findall('"account_name":"(.*?)","type":"(.*?)","expires":(.*?),".*?trafficleft_gigabytes":(.*?)}', data, re.S|re.I)
			if infos:
				(a_name, a_type, a_expires, a_left) = infos[0]
				deadline = datetime.datetime.fromtimestamp(int(a_expires)).strftime('%d-%m-%Y')
				pmsg = "premiumize.me\n\nUser:\t%s\nType:\t%s\nExpires:\t%s\nPoints left:\t%4.2f" % (a_name, a_type, deadline, float(a_left))
				self.session.open(MessageBoxExt, pmsg , MessageBoxExt.TYPE_INFO)
			else:
				self.session.open(MessageBoxExt, _("premiumize.me failed."), MessageBoxExt.TYPE_ERROR)
		elif re.search('status":401', data):
			self.session.open(MessageBoxExt, _("premiumize: Login failed."), MessageBoxExt.TYPE_INFO, timeout=3)

	def premiumizeProxyConfig(self, msgbox=True):
		return
		url = config.mediaportal.premiumize_proxy_config_url.value
		if re.search('^https://.*?\.pac', url):
			r_getPage(url, method="GET", timeout=15).addCallback(self.premiumizeProxyData, msgbox).addErrback(self.dataError)
		else:
			self.premiumize()

	def premiumizeProxyData(self, data, msgbox):
		m = re.search('PROXY (.*?):(\d{2}); PROXY', data)
		if m:
			mp_globals.premium_yt_proxy_host = m.group(1)
			mp_globals.premium_yt_proxy_port = int(m.group(2))
			print 'YT-Proxy:',m.group(1), ':', mp_globals.premium_yt_proxy_port
			if msgbox:
				self.session.open(MessageBoxExt, _("premiumize: YT ProxyHost found."), MessageBoxExt.TYPE_INFO)
		else:
			if msgbox:
				self.session.open(MessageBoxExt, _("premiumize: YT ProxyHost not found!"), MessageBoxExt.TYPE_ERROR)

	def dataError(self, error):
		from debuglog import printlog as printl
		printl(error,self,"E")

class MPSetup(Screen, CheckPremiumize, ConfigListScreenExt):

	def __init__(self, session):

		self.skin_path = mp_globals.pluginPath + mp_globals.skinsPath

		path = "%s/%s/MP_Setup.xml" % (self.skin_path, config.mediaportal.skin.value)
		if not fileExists(path):
			path = self.skin_path + mp_globals.skinFallback + "/MP_Setup.xml"

		with open(path, "r") as f:
			self.skin = f.read()
			f.close()

		self["hidePig"] = Boolean()
		self["hidePig"].setBoolean(config.mediaportal.minitv.value)

		Screen.__init__(self, session)

		self.configlist = []

		ConfigListScreenExt.__init__(self, self.configlist, on_change = self._onKeyChange)

		skins = []
		if mp_globals.videomode == 2:
			mp_globals.skinsPath = "/skins_1080"
			for skin in os.listdir("/usr/lib/enigma2/python/Plugins/Extensions/MediaPortal/skins_1080/"):
				if os.path.isdir(os.path.join("/usr/lib/enigma2/python/Plugins/Extensions/MediaPortal/skins_1080/", skin)):
					skins.append(skin)
			config.mediaportal.skin.setChoices(skins, "clean_fhd")
		else:
			mp_globals.skinsPath = "/skins_720"
			for skin in os.listdir("/usr/lib/enigma2/python/Plugins/Extensions/MediaPortal/skins_720/"):
				if os.path.isdir(os.path.join("/usr/lib/enigma2/python/Plugins/Extensions/MediaPortal/skins_720/", skin)):
					skins.append(skin)
			config.mediaportal.skin.setChoices(skins, "original")

		self._getConfig()

		self['title'] = Label(_("Setup"))
		self['F1'] = Label("Premium")
		self['F2'] = Label("")
		self['F3'] = Label("")
		self['F4'] = Label("")

		self["actions"] = ActionMap(["MP_Actions2", "MP_Actions"], {
			"ok"    : self.keySave,
			"cancel": self.keyCancel,
			"up": self.keyUp,
			"down": self.keyDown,
			"nextBouquet": self.keyPreviousSection,
			"prevBouquet": self.keyNextSection,
			"red" : self.premium
		}, -1)

	def _separator(self):
		if mp_globals.isDreamOS:
			pass
		else:
			self.configlist.append(getConfigListEntry(400 * "¯", ))

	def _spacer(self):
		self.configlist.append(getConfigListEntry("", config.mediaportal.fake_entry, False))

	def _getConfig(self):
		self.configlist = []
		self.sport = []
		self.music = []
		self.fun = []
		self.newsdoku = []
		self.mediatheken = []
		self.porn = []
		self.useradditions = []
		### Allgemein
		self.configlist.append(getConfigListEntry(_("GENERAL"), ))
		self._separator()
		self.configlist.append(getConfigListEntry(_("Automatic Update Check:"), config.mediaportal.autoupdate, False))
		self.configlist.append(getConfigListEntry(_("Mainview Style:"), config.mediaportal.ansicht, True))
		if config.mediaportal.ansicht.value == "wall":
			self.configlist.append(getConfigListEntry(_("Wall Mode:"), config.mediaportal.wallmode, True))
		if config.mediaportal.ansicht.value == "wall2":
			self.configlist.append(getConfigListEntry(_("Wall 2.0 Mode:"), config.mediaportal.wall2mode, False))
		if (config.mediaportal.ansicht.value == "wall" or config.mediaportal.ansicht.value == "wall2" or config.mediaportal.ansicht.value == "wall_vti"):
			self.configlist.append(getConfigListEntry(_("Wall-Selector-Color:"), config.mediaportal.selektor, False))
			self.configlist.append(getConfigListEntry(_("Page Display Style:"), config.mediaportal.pagestyle, False))
		self.configlist.append(getConfigListEntry(_("Skin:"), config.mediaportal.skin, False))
		self.configlist.append(getConfigListEntry(_("ShowAsThumb as Default:"), config.mediaportal.showAsThumb, False))
		self.configlist.append(getConfigListEntry(_("Disable Background-TV:"), config.mediaportal.backgroundtv, True))
		if not config.mediaportal.backgroundtv.value:
			self.configlist.append(getConfigListEntry(_("Restore last service:"), config.mediaportal.restorelastservice, False))
			self.configlist.append(getConfigListEntry(_("Disable Mini-TV:"), config.mediaportal.minitv, False))
		self.configlist.append(getConfigListEntry(_("Enable search suggestions:"), config.mediaportal.ena_suggestions, False))
		if mp_globals.animations:
			self.configlist.append(getConfigListEntry(_("Coverart animation")+":", config.mediaportal.animation_coverart, False))
			self.configlist.append(getConfigListEntry(_("Label animation")+":", config.mediaportal.animation_label, False))
			self.configlist.append(getConfigListEntry(_("SimplePlayer animation")+":", config.mediaportal.animation_simpleplayer, False))
		self._spacer()
		self.configlist.append(getConfigListEntry(_("YOUTH PROTECTION"), ))
		self._separator()
		self.configlist.append(getConfigListEntry(_("Setup PIN:"), config.mediaportal.pincode, False))
		self.configlist.append(getConfigListEntry(_("Setup PIN Query:"), config.mediaportal.setuppin, False))
		self.configlist.append(getConfigListEntry(_("Kids PIN Query:"), config.mediaportal.kidspin, False))
		self.configlist.append(getConfigListEntry(_("Adult PIN:"), config.mediaportal.adultpincode, False))
		self.configlist.append(getConfigListEntry(_("Adult PIN Query:"), config.mediaportal.pornpin, False))
		self.configlist.append(getConfigListEntry(_("Remember Adult PIN:"), config.mediaportal.pornpin_cache, False))
		self._spacer()
		self.configlist.append(getConfigListEntry(_("OTHER"), ))
		self._separator()
		self.configlist.append(getConfigListEntry(_("Use HLS-Player:"), config.mediaportal.use_hls_proxy, True))
		if config.mediaportal.use_hls_proxy.value:
			self.configlist.append(getConfigListEntry(_("HLS-Player buffersize [MB]:"), config.mediaportal.hls_buffersize, False))
			#self.configlist.append(getConfigListEntry(_("HLS-Player IP:"), config.mediaportal.hls_proxy_ip, False))
			#self.configlist.append(getConfigListEntry(_("HLS-Player Port:"), config.mediaportal.hls_proxy_port, False))
			self.configlist.append(getConfigListEntry(_('Use HLS-Player Proxy:'), config.mediaportal.sp_use_hlsp_with_proxy, False))
			self.configlist.append(getConfigListEntry(_("HLSP-HTTP-Proxy Host or IP:"), config.mediaportal.hlsp_proxy_host, False))
			self.configlist.append(getConfigListEntry(_("HLSP-Proxy Port:"), config.mediaportal.hlsp_proxy_port, False))
			self.configlist.append(getConfigListEntry(_("HLSP-Proxy username:"), config.mediaportal.hlsp_proxy_username, False))
			self.configlist.append(getConfigListEntry(_("HLSP-Proxy password:"), config.mediaportal.hlsp_proxy_password, False))
		self.configlist.append(getConfigListEntry(_("Temporary Cachepath:"), config.mediaportal.storagepath, False))
		self.configlist.append(getConfigListEntry(_("Icon Cachepath:"), config.mediaportal.iconcachepath, False))
		self.configlist.append(getConfigListEntry(_("Videoquality:"), config.mediaportal.videoquali_others, False))
		self.configlist.append(getConfigListEntry(_("Watchlist/Playlist/Userchan path:"), config.mediaportal.watchlistpath, False))
		self.configlist.append(getConfigListEntry(_("Show USER-Channels Help:"), config.mediaportal.show_userchan_help, False))
		self.configlist.append(getConfigListEntry(_('SimpleList on key:'), config.mediaportal.simplelist_key, False))
		if MediaInfoPresent:
			self.configlist.append(getConfigListEntry(_('MediaInfo on key:'), config.mediaportal.sp_mi_key, False))
		self._spacer()
		self.configlist.append(getConfigListEntry(_("YOUTUBE"), ))
		self._separator()
		self.configlist.append(getConfigListEntry(_("Highest resolution for playback:"), config.mediaportal.youtubeprio, False))
		self.configlist.append(getConfigListEntry(_("Enable DASH format:"), config.mediaportal.youtubeenabledash, True))
		if config.mediaportal.youtubeenabledash.value:
			self.configlist.append(getConfigListEntry(_("Enable VP9 codec:"), config.mediaportal.youtubeenablevp9, False))
		self.configlist.append(getConfigListEntry(_("Max. count results/page:"), config.mediaportal.youtube_max_items_pp, False))
		self.configlist.append(getConfigListEntry(_('Use Proxy:'), config.mediaportal.sp_use_yt_with_proxy, True))
		if config.mediaportal.sp_use_yt_with_proxy.value == "proxy":
			self.configlist.append(getConfigListEntry(_("HTTP-Proxy Host or IP:"), config.mediaportal.yt_proxy_host, False))
			self.configlist.append(getConfigListEntry(_("HTTP-Proxy Port:"), config.mediaportal.yt_proxy_port, False))
			self.configlist.append(getConfigListEntry(_("HTTP-Proxy username:"), config.mediaportal.yt_proxy_username, False))
			self.configlist.append(getConfigListEntry(_("HTTP-Proxy password:"), config.mediaportal.yt_proxy_password, False))
		#self._spacer()
		#self.configlist.append(getConfigListEntry("MP-EPG-IMPORTER", ))
		#self._separator()
		#self.configlist.append(getConfigListEntry(_("Enable import:"), config.mediaportal.epg_enabled, True))
		#if config.mediaportal.epg_enabled.value:
		#	self.configlist.append(getConfigListEntry(_("Automatic start time:"), config.mediaportal.epg_wakeup, False))
		#	self.configlist.append(getConfigListEntry(_("Standby at startup:"), config.mediaportal.epg_wakeupsleep, False))
		#	self.configlist.append(getConfigListEntry(_("When in deep standby:"), config.mediaportal.epg_deepstandby, False))
		#	self.configlist.append(getConfigListEntry(_("Start import after booting up:"), config.mediaportal.epg_runboot, False))
		self._spacer()
		self.configlist.append(getConfigListEntry("PREMIUMIZE.ME", ))
		self._separator()
		self.configlist.append(getConfigListEntry(_("Activate premiumize.me:"), config.mediaportal.premiumize_use, True))
		if config.mediaportal.premiumize_use.value:
			self.configlist.append(getConfigListEntry(_("Customer ID:"), config.mediaportal.premiumize_username, False))
			self.configlist.append(getConfigListEntry(_("PIN:"), config.mediaportal.premiumize_password, False))
			#self.configlist.append(getConfigListEntry(_("Autom. Proxy-Config.-URL:"), config.mediaportal.premiumize_proxy_config_url, False))
		self._spacer()
		self.configlist.append(getConfigListEntry("REAL-DEBRID.COM", ))
		self._separator()
		self.configlist.append(getConfigListEntry(_("Activate Real-Debrid.com:"), config.mediaportal.realdebrid_use, True))
		if config.mediaportal.premiumize_use.value or config.mediaportal.realdebrid_use.value:
			self._spacer()
			self.configlist.append(getConfigListEntry("PREMIUM", ))
			self._separator()
			self.configlist.append(getConfigListEntry(_("Streammarkercolor:"), config.mediaportal.premium_color, False))

		conf = xml.etree.cElementTree.parse(CONFIG)
		for x in conf.getroot():
			if x.tag == "set" and x.get("name") == 'additions':
				root =  x
				for x in root:
					if x.tag == "plugin":
						if x.get("type") == "mod":
							modfile = x.get("modfile")
							gz = x.get("gz")
							if not config.mediaportal.showuseradditions.value and gz == "1":
								pass
							else:
								exec("self."+x.get("confcat")+".append(getConfigListEntry(\""+x.get("name").replace("&amp;","&")+"\", config.mediaportal."+x.get("confopt")+", False))")

		xmlpath = resolveFilename(SCOPE_PLUGINS, "Extensions/MediaPortal/additions/")
		for file in os.listdir(xmlpath):
			if file.endswith(".xml") and file != "additions.xml":
				useraddition = xmlpath + file

				conf = xml.etree.cElementTree.parse(useraddition)
				for x in conf.getroot():
					if x.tag == "set" and x.get("name") == 'additions_user':
						root =  x
						for x in root:
							if x.tag == "plugin":
								if x.get("type") == "mod":
									modfile = x.get("modfile")
									gz = x.get("gz")
									if not config.mediaportal.showuseradditions.value and gz == "1":
										pass
									else:
										exec("self."+x.get("confcat")+".append(getConfigListEntry(\""+x.get("name").replace("&amp;","&")+"\", config.mediaportal."+x.get("confopt")+", False))")

		self._spacer()
		self.configlist.append(getConfigListEntry(_("LIBRARIES"), ))
		self._separator()
		self.mediatheken.sort(key=lambda t : t[0].lower())
		for x in self.mediatheken:
			self.configlist.append((_("Show ")+x[0]+":",x[1], False))

		self._spacer()
		self.configlist.append(getConfigListEntry(_("NEWS&DOCUMENTARY"), ))
		self._separator()
		self.newsdoku.sort(key=lambda t : t[0].lower())
		for x in self.newsdoku:
			self.configlist.append((_("Show ")+x[0]+":",x[1], False))

		self._spacer()
		self.configlist.append(getConfigListEntry(_("FUN"), ))
		self._separator()
		self.fun.sort(key=lambda t : t[0].lower())
		for x in self.fun:
			self.configlist.append((_("Show ")+x[0]+":",x[1], False))

		self._spacer()
		self.configlist.append(getConfigListEntry(_("SPORTS"), ))
		self._separator()
		self.sport.sort(key=lambda t : t[0].lower())
		for x in self.sport:
			self.configlist.append((_("Show ")+x[0]+":",x[1], False))

		self._spacer()
		self.configlist.append(getConfigListEntry(_("MUSIC"), ))
		self._separator()
		self.music.sort(key=lambda t : t[0].lower())
		for x in self.music:
			self.configlist.append((_("Show ")+x[0]+":",x[1], False))

		if config.mediaportal.showporn.value:
			self._spacer()
			self.configlist.append(getConfigListEntry(_("PORN"), ))
			self._separator()
			self.porn.sort(key=lambda t : t[0].lower())
			for x in self.porn:
				self.configlist.append((_("Show ")+x[0]+":",x[1], False))

		test = resolveFilename(SCOPE_PLUGINS, "Extensions/MediaPortal/additions/useradditions/")

		if len(os.listdir(test)) > 2:
			if config.mediaportal.showuseradditions.value:
				self._spacer()
				self.configlist.append(getConfigListEntry(_("USER-ADDITIONS"), ))
				self._separator()
				self.useradditions.sort(key=lambda t : t[0].lower())
				for x in self.useradditions:
					self.configlist.append((_("Show ")+x[0]+":",x[1], False))

		self._spacer()
		self.configlist.append(getConfigListEntry("DEBUG", ))
		self._separator()
		self.configlist.append(getConfigListEntry("Debug-Mode:", config.mediaportal.debugMode, False))
		if len(os.listdir(test)) > 2:
			self.configlist.append(getConfigListEntry(_("Activate User-additions:"), config.mediaportal.showuseradditions, False))

		self["config"].list = self.configlist
		self["config"].setList(self.configlist)

	def _onKeyChange(self):
		try:
			cur = self["config"].getCurrent()
			if cur and cur[2]:
				self._getConfig()
		except:
			pass

	def keyOK(self):
		if self["config"].current:
			self["config"].current[1].onDeselect(self.session)
		if config.mediaportal.watchlistpath.value[0] != '/':
			config.mediaportal.watchlistpath.value = '/' + config.mediaportal.watchlistpath.value
		if config.mediaportal.watchlistpath.value[-1] != '/':
			config.mediaportal.watchlistpath.value = config.mediaportal.watchlistpath.value + '/'
		if config.mediaportal.storagepath.value[0] != '/':
			config.mediaportal.storagepath.value = '/' + config.mediaportal.storagepath.value
		if config.mediaportal.storagepath.value[-1] != '/':
			config.mediaportal.storagepath.value = config.mediaportal.storagepath.value + '/'
		if config.mediaportal.storagepath.value[-4:] != 'tmp/':
			config.mediaportal.storagepath.value = config.mediaportal.storagepath.value + 'tmp/'
		if config.mediaportal.iconcachepath.value[0] != '/':
			config.mediaportal.iconcachepath.value = '/' + config.mediaportal.iconcachepath.value
		if config.mediaportal.iconcachepath.value[-1] != '/':
			config.mediaportal.iconcachepath.value = config.mediaportal.iconcachepath.value + '/'
		if (config.mediaportal.showporn.value == False and config.mediaportal.filter.value == 'Porn'):
			config.mediaportal.filter.value = 'ALL'
		if (config.mediaportal.showuseradditions.value == False and config.mediaportal.filter.value == 'User-additions'):
			config.mediaportal.filter.value = 'ALL'

		CheckPathes(self.session).checkPathes(self.cb_checkPathes)

		if (config.mediaportal.showuseradditions.value and not config.mediaportal.pinuseradditions.value):
			self.a = str(random.randint(1,9))
			self.b = str(random.randint(0,9))
			self.c = str(random.randint(0,9))
			self.d = str(random.randint(0,9))
			code = "%s %s %s %s" % (self.a,self.b,self.c,self.d)
			message = _("Some of the plugins may not be legally used in your country!\n\nIf you accept this then enter the following code now:\n\n%s" % (code))
			self.session.openWithCallback(self.keyOK2, MessageBoxExt, message, MessageBoxExt.TYPE_YESNO)
		else:
			if not config.mediaportal.showuseradditions.value:
				config.mediaportal.pinuseradditions.value = False
				config.mediaportal.pinuseradditions.save()
			self.keySave()

	def premium(self):
		if config.mediaportal.realdebrid_use.value:
			if mp_globals.isDreamOS:
				self.session.open(realdebrid_oauth2, None, calltype='user', is_dialog=True)
			else:
				self.session.open(realdebrid_oauth2, None, calltype='user')
		else:
			self.session.open(MessageBoxExt, _("Real-Debrid.com is not activated."), MessageBoxExt.TYPE_ERROR)
		self.premiumize()

	def cb_checkPathes(self):
		pass

	def keyOK2(self, answer):
		if answer is True:
			self.session.openWithCallback(self.validcode, PinInputExt, pinList = [(int(self.a+self.b+self.c+self.d))], triesEntry = config.mediaportal.retries.pincode, title = _("Please enter the correct code"), windowTitle = _("Enter code"))
		else:
			config.mediaportal.showuseradditions.value = False
			config.mediaportal.showuseradditions.save()
			config.mediaportal.pinuseradditions.value = False
			config.mediaportal.pinuseradditions.save()
			self.keySave()

	def validcode(self, code):
		if code:
			config.mediaportal.pinuseradditions.value = True
			config.mediaportal.pinuseradditions.save()
			self.keySave()
		else:
			config.mediaportal.showuseradditions.value = False
			config.mediaportal.showuseradditions.save()
			config.mediaportal.pinuseradditions.value = False
			config.mediaportal.pinuseradditions.save()
			self.keySave()

class MPList(Screen, HelpableScreen):

	def __init__(self, session, lastservice):
		self.lastservice = mp_globals.lastservice = lastservice

		self.skin_path = mp_globals.pluginPath + mp_globals.skinsPath

		path = "%s/%s/MP_List.xml" % (self.skin_path, config.mediaportal.skin.value)
		if not fileExists(path):
			path = self.skin_path + mp_globals.skinFallback + "/MP_List.xml"
		with open(path, "r") as f:
			self.skin = f.read()
			f.close()

		self["hidePig"] = Boolean()
		self["hidePig"].setBoolean(config.mediaportal.minitv.value)

		Screen.__init__(self, session)

		addFont(resolveFilename(SCOPE_PLUGINS, "Extensions/MediaPortal/resources/") + "mediaportal1.ttf", "mediaportal", 100, False)

		if config.mediaportal.backgroundtv.value:
			config.mediaportal.minitv.value = True
			config.mediaportal.minitv.save()
			config.mediaportal.restorelastservice.value = "2"
			config.mediaportal.restorelastservice.save()
			configfile.save()
			session.nav.stopService()

		self["actions"] = ActionMap(["MP_Actions"], {
			"up"    : self.keyUp,
			"down"  : self.keyDown,
			"left"  : self.keyRight,
			"right" : self.keyRight,
			"info"  : self.showPorn
		}, -1)
		self["MP_Actions"] = HelpableActionMap(self, "MP_Actions", {
			"red"   : (self.keySimpleList, _("Open SimpleList")),
			"ok"    : (self.keyOK, _("Open selected Plugin")),
			"cancel": (self.keyCancel, _("Exit MediaPortal")),
			"prevBouquet" :	(self.keyPageDown, _("Next page")),
			"nextBouquet" :	(self.keyPageUp, _("Previous page")),
			"menu" : (self.keySetup, _("MediaPortal Setup")),
			config.mediaportal.simplelist_key.value: (self.keySimpleList, _("Open SimpleList"))
		}, -1)

		self['title'] = Label("MediaPortal")
		self['version'] = Label(config.mediaportal.version.value[0:8])

		self['name'] = Label("")

		self['red'] = Label("SimpleList")

		self['PVR'] = Label(_("PVR"))
		self['Menu'] = Label(_("Menu"))
		self['Help'] = Label(_("Help"))
		self['Exit'] = Label(_("Exit"))

		self.chooseMenuList1 = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
		self.chooseMenuList1.l.setFont(0, gFont(mp_globals.font, mp_globals.fontsize + 2 * mp_globals.sizefactor))
		if mp_globals.videomode == 2:
			self.chooseMenuList1.l.setItemHeight(90)
		else:
			self.chooseMenuList1.l.setItemHeight(62)
		self['mediatheken'] = self.chooseMenuList1
		self['Mediatheken'] = Label(_("Libraries"))

		self.chooseMenuList2 = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
		self.chooseMenuList2.l.setFont(0, gFont(mp_globals.font, mp_globals.fontsize + 2 * mp_globals.sizefactor))
		if mp_globals.videomode == 2:
			self.chooseMenuList2.l.setItemHeight(90)
		else:
			self.chooseMenuList2.l.setItemHeight(62)
		self['fun'] = self.chooseMenuList2
		self['Fun'] = Label(_("Fun"))

		self.chooseMenuList3 = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
		self.chooseMenuList3.l.setFont(0, gFont(mp_globals.font, mp_globals.fontsize + 2 * mp_globals.sizefactor))
		if mp_globals.videomode == 2:
			self.chooseMenuList3.l.setItemHeight(90)
		else:
			self.chooseMenuList3.l.setItemHeight(62)
		self['music'] = self.chooseMenuList3
		self['Music'] = Label(_("Music"))

		self.chooseMenuList4 = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
		self.chooseMenuList4.l.setFont(0, gFont(mp_globals.font, mp_globals.fontsize + 2 * mp_globals.sizefactor))
		if mp_globals.videomode == 2:
			self.chooseMenuList4.l.setItemHeight(90)
		else:
			self.chooseMenuList4.l.setItemHeight(62)
		self['sport'] = self.chooseMenuList4
		self['Sport'] = Label(_("Sports"))

		self.chooseMenuList5 = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
		self.chooseMenuList5.l.setFont(0, gFont(mp_globals.font, mp_globals.fontsize + 2 * mp_globals.sizefactor))
		if mp_globals.videomode == 2:
			self.chooseMenuList5.l.setItemHeight(90)
		else:
			self.chooseMenuList5.l.setItemHeight(62)
		self['newsdoku'] = self.chooseMenuList5
		self['NewsDoku'] = Label(_("News&Documentary"))

		self.chooseMenuList6 = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
		self.chooseMenuList6.l.setFont(0, gFont(mp_globals.font, mp_globals.fontsize + 2 * mp_globals.sizefactor))
		if mp_globals.videomode == 2:
			self.chooseMenuList6.l.setItemHeight(90)
		else:
			self.chooseMenuList6.l.setItemHeight(62)
		self['porn'] = self.chooseMenuList6
		self['Porn'] = Label(_("Porn"))

		self.chooseMenuList7 = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
		self.chooseMenuList7.l.setFont(0, gFont(mp_globals.font, mp_globals.fontsize + 2 * mp_globals.sizefactor))
		if mp_globals.videomode == 2:
			self.chooseMenuList7.l.setItemHeight(90)
		else:
			self.chooseMenuList7.l.setItemHeight(62)
		self['useradditions'] = self.chooseMenuList7
		self['Useradditions'] = Label("User-Additions")

		self.currentlist = "porn"
		self.picload = ePicLoad()

		HelpableScreen.__init__(self)
		self.onLayoutFinish.append(self.layoutFinished)
		self.onFirstExecBegin.append(self.checkPathes)
		self.onFirstExecBegin.append(self.status)

	def layoutFinished(self):
		_hosters()

		self.icon_url = getIconUrl()
		icons_hashes = grabpage(self.icon_url+"icons/hashes")
		if icons_hashes:
			self.icons_data = re.findall('(.*?)\s\*(.*?\.png)', icons_hashes)
		else:
			self.icons_data = None

		logo_hashes = grabpage(self.icon_url+"logos/hashes")
		if logo_hashes:
			self.logo_data = re.findall('(.*?)\s\*(.*?\.png)', logo_hashes)
		else:
			self.logo_data = None

		if not mp_globals.start:
			self.close(self.session, True, self.lastservice)
		if config.mediaportal.autoupdate.value:
			checkupdate(self.session).checkforupdate()

		self.mediatheken = []
		self.fun = []
		self.music = []
		self.sport = []
		self.newsdoku = []
		self.porn = []
		self.useradditions = []

		conf = xml.etree.cElementTree.parse(CONFIG)
		for x in conf.getroot():
			if x.tag == "set" and x.get("name") == 'additions':
				root =  x
				for x in root:
					if x.tag == "plugin":
						if x.get("type") == "mod":
							modfile = x.get("modfile")
							confcat = x.get("confcat")
							if not config.mediaportal.showporn.value and confcat == "porn":
								pass
							else:
								gz = x.get("gz")
								if not config.mediaportal.showuseradditions.value and gz == "1":
									pass
								else:
									mod = eval("config.mediaportal." + x.get("confopt") + ".value")
									if mod:
										exec("self."+x.get("confcat")+".append(self.hauptListEntry(\""+x.get("name").replace("&amp;","&")+"\", \""+x.get("icon")+"\", \""+x.get("modfile")+"\"))")

		xmlpath = resolveFilename(SCOPE_PLUGINS, "Extensions/MediaPortal/additions/")
		for file in os.listdir(xmlpath):
			if file.endswith(".xml") and file != "additions.xml":
				useraddition = xmlpath + file

				conf = xml.etree.cElementTree.parse(useraddition)
				for x in conf.getroot():
					if x.tag == "set" and x.get("name") == 'additions_user':
						root =  x
						for x in root:
							if x.tag == "plugin":
								if x.get("type") == "mod":
									modfile = x.get("modfile")
									confcat = x.get("confcat")
									if not config.mediaportal.showporn.value and confcat == "porn":
										pass
									else:
										gz = x.get("gz")
										if not config.mediaportal.showuseradditions.value and gz == "1":
											pass
										else:
											mod = eval("config.mediaportal." + x.get("confopt") + ".value")
											if mod:
												exec("self."+x.get("confcat")+".append(self.hauptListEntry(\""+x.get("name").replace("&amp;","&")+"\", \""+x.get("icon")+"\", \""+x.get("modfile")+"\"))")

		self.mediatheken.sort(key=lambda t : t[0][0].lower())
		self.fun.sort(key=lambda t : t[0][0].lower())
		self.music.sort(key=lambda t : t[0][0].lower())
		self.sport.sort(key=lambda t : t[0][0].lower())
		self.newsdoku.sort(key=lambda t : t[0][0].lower())
		self.porn.sort(key=lambda t : t[0][0].lower())
		self.useradditions.sort(key=lambda t : t[0][0].lower())

		self.chooseMenuList1.setList(self.mediatheken)
		self.chooseMenuList2.setList(self.fun)
		self.chooseMenuList3.setList(self.music)
		self.chooseMenuList4.setList(self.sport)
		self.chooseMenuList5.setList(self.newsdoku)
		self.chooseMenuList6.setList(self.porn)
		self.chooseMenuList7.setList(self.useradditions)
		self.keyRight()

	def checkPathes(self):
		CheckPathes(self.session).checkPathes(self.cb_checkPathes)

	def cb_checkPathes(self):
		self.session.openWithCallback(self.restart, MPSetup)

	def status(self):
		update_agent = getUserAgent()
		update_url = getUpdateUrl()
		twAgentGetPage(update_url, agent=update_agent, timeout=30).addCallback(self.checkstatus)

	def checkstatus(self, html):
		if re.search(".*?<html", html):
			return
		self.html = html
		tmp_infolines = html.splitlines()
		statusurl = tmp_infolines[4]
		update_agent = getUserAgent()
		twAgentGetPage(statusurl, agent=update_agent, timeout=30).addCallback(_status).addCallback(self.markDefect)

	def markDefect(self, dummy=None):
		reloadit = False
		for defitem in mp_globals.status:
			if int(config.mediaportal.version.value) < int(defitem[1]):
				for confcatitem in [self.mediatheken, self.fun, self.music, self.sport, self.newsdoku, self.porn, self.useradditions]:
					lst = list(confcatitem)
					for n,i in enumerate(lst):
						if i[0][2] == defitem[0]:
							modlst = list(lst[n][2])
							reloadit = True
							try:
								if int(defitem[1]) > 999:
									modlst[8] = 16711680
								else:
									modlst[8] = 16776960
							except:
								pass
							lst[n][2] = tuple(modlst)
					confcatitem = tuple(lst)
		if reloadit:
			self.chooseMenuList1.setList(self.mediatheken)
			self.chooseMenuList2.setList(self.fun)
			self.chooseMenuList3.setList(self.music)
			self.chooseMenuList4.setList(self.sport)
			self.chooseMenuList5.setList(self.newsdoku)
			self.chooseMenuList6.setList(self.porn)
			self.chooseMenuList7.setList(self.useradditions)

	def hauptListEntry(self, name, icon, modfile=None):
		res = [(name, icon, modfile)]
		poster_path = "%s/%s.png" % (config.mediaportal.iconcachepath.value + "icons", icon)
		url = self.icon_url+"icons/" + icon + ".png"
		remote_hash = ""
		ds = defer.DeferredSemaphore(tokens=5)
		if not fileExists(poster_path):
			if self.icons_data:
				for x,y in self.icons_data:
					if y == icon+'.png':
						ds.run(downloadPage, url, poster_path)
			poster_path = "%s/images/comingsoon.png" % mp_globals.pluginPath
		else:
			local_hash = hashlib.md5(open(poster_path, 'rb').read()).hexdigest()
			if self.icons_data:
				for x,y in self.icons_data:
					if y == icon+'.png': remote_hash = x
				if remote_hash != local_hash:
					ds.run(downloadPage, url, poster_path)
					poster_path = "%s/images/comingsoon.png" % mp_globals.pluginPath

		logo_path = "%s/%s.png" % (config.mediaportal.iconcachepath.value + "logos", icon)
		url = self.icon_url+"logos/" + icon + ".png"
		if not fileExists(logo_path):
			if self.logo_data:
				for x,y in self.logo_data:
					if y == icon+'.png':
						ds.run(downloadPage, url, logo_path)
		else:
			local_hash = hashlib.md5(open(logo_path, 'rb').read()).hexdigest()
			if self.logo_data:
				for x,y in self.logo_data:
					if y == icon+'.png': remote_hash = x
				if remote_hash != local_hash:
					ds.run(downloadPage, url, logo_path)

		scale = AVSwitch().getFramebufferScale()
		if mp_globals.videomode == 2:
			self.picload.setPara((150, 80, scale[0], scale[1], False, 1, "#FF000000"))
		else:
			self.picload.setPara((105, 56, scale[0], scale[1], False, 1, "#FF000000"))
		if mp_globals.isDreamOS:
			self.picload.startDecode(poster_path, False)
		else:
			self.picload.startDecode(poster_path, 0, 0, False)
		pngthumb = self.picload.getData()
		if mp_globals.videomode == 2:
			res.append(MultiContentEntryPixmapAlphaBlend(pos=(0, 5), size=(150, 80), png=pngthumb))
			res.append(MultiContentEntryText(pos=(165, 0), size=(800, 90), font=0, text=name, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER))
		else:
			res.append(MultiContentEntryPixmapAlphaBlend(pos=(0, 3), size=(105, 56), png=pngthumb))
			res.append(MultiContentEntryText(pos=(115, 0), size=(600, 62), font=0, text=name, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER))
		return res

	def showPorn(self):
		if config.mediaportal.showporn.value:
			config.mediaportal.showporn.value = False
			config.mediaportal.showporn.save()
			configfile.save()
			self.restart()
		else:
			self.session.openWithCallback(self.showPornOK, PinInputExt, pinList = [(config.mediaportal.adultpincode.value)], triesEntry = config.mediaportal.retries.adultpin, title = _("Please enter the correct PIN"), windowTitle = _("Enter adult PIN"))

	def showPornOK(self, pincode):
		if pincode:
			pincheck.pinEntered()
			config.mediaportal.showporn.value = True
			config.mediaportal.showporn.save()
			configfile.save()
			self.restart()

	def keySetup(self):
		if config.mediaportal.setuppin.value:
			self.session.openWithCallback(self.pinok, PinInputExt, pinList = [(config.mediaportal.pincode.value)], triesEntry = config.mediaportal.retries.pincode, title = _("Please enter the correct PIN"), windowTitle = _("Enter setup PIN"))
		else:
			self.session.openWithCallback(self.restart, MPSetup)

	def keySimpleList(self):
		mp_globals.activeIcon = "simplelist"
		self.session.open(simplelistGenreScreen)

	def pinok(self, pincode):
		if pincode:
			self.session.openWithCallback(self.restart, MPSetup)

	def keyUp(self):
		exist = self[self.currentlist].getCurrent()
		if exist == None:
			return
		self[self.currentlist].up()
		auswahl = self[self.currentlist].getCurrent()[0][0]
		self.title = auswahl
		self['name'].setText(auswahl)

	def keyDown(self):
		exist = self[self.currentlist].getCurrent()
		if exist == None:
			return
		self[self.currentlist].down()
		auswahl = self[self.currentlist].getCurrent()[0][0]
		self.title = auswahl
		self['name'].setText(auswahl)

	def keyPageUp(self):
		self[self.currentlist].pageUp()

	def keyPageDown(self):
		self[self.currentlist].pageDown()

	def keyRight(self):
		self.cur_idx = self[self.currentlist].getSelectedIndex()
		self["mediatheken"].hide()
		self["Mediatheken"].hide()
		self["fun"].hide()
		self["Fun"].hide()
		self["music"].hide()
		self["Music"].hide()
		self["sport"].hide()
		self["Sport"].hide()
		self["newsdoku"].hide()
		self["NewsDoku"].hide()
		self["porn"].hide()
		self["Porn"].hide()
		self["useradditions"].hide()
		self["Useradditions"].hide()
		if self.currentlist == "mediatheken":
			if len(self.fun) > 0:
				self["fun"].show()
				self["Fun"].show()
				self.currentlist = "fun"
				cnt_tmp_ls = len(self.fun)
			elif len(self.music) > 0:
				self["music"].show()
				self["Music"].show()
				self.currentlist = "music"
				cnt_tmp_ls = len(self.music)
			elif len(self.sport) > 0:
				self["sport"].show()
				self["Sport"].show()
				self.currentlist = "sport"
				cnt_tmp_ls = len(self.sport)
			elif len(self.newsdoku) > 0:
				self["newsdoku"].show()
				self["NewsDoku"].show()
				self.currentlist = "newsdoku"
				cnt_tmp_ls = len(self.newsdoku)
			elif len(self.porn) > 0:
				self["porn"].show()
				self["Porn"].show()
				self.currentlist = "porn"
				cnt_tmp_ls = len(self.porn)
			elif len(self.useradditions) > 0:
				self["useradditions"].show()
				self["Useradditions"].show()
				self.currentlist = "useradditions"
				cnt_tmp_ls = len(self.useradditions)
			else:
				self["mediatheken"].show()
				self["Mediatheken"].show()
				self.currentlist = "mediatheken"
				cnt_tmp_ls = len(self.mediatheken)
		elif self.currentlist == "fun":
			if len(self.music) > 0:
				self["music"].show()
				self["Music"].show()
				self.currentlist = "music"
				cnt_tmp_ls = len(self.music)
			elif len(self.sport) > 0:
				self["sport"].show()
				self["Sport"].show()
				self.currentlist = "sport"
				cnt_tmp_ls = len(self.sport)
			elif len(self.newsdoku) > 0:
				self["newsdoku"].show()
				self["NewsDoku"].show()
				self.currentlist = "newsdoku"
				cnt_tmp_ls = len(self.newsdoku)
			elif len(self.porn) > 0:
				self["porn"].show()
				self["Porn"].show()
				self.currentlist = "porn"
				cnt_tmp_ls = len(self.porn)
			elif len(self.useradditions) > 0:
				self["useradditions"].show()
				self["Useradditions"].show()
				self.currentlist = "useradditions"
				cnt_tmp_ls = len(self.useradditions)
			elif len(self.mediatheken) > 0:
				self["mediatheken"].show()
				self["Mediatheken"].show()
				self.currentlist = "mediatheken"
				cnt_tmp_ls = len(self.mediatheken)
			else:
				self["fun"].show()
				self["Fun"].show()
				self.currentlist = "fun"
				cnt_tmp_ls = len(self.fun)
		elif self.currentlist == "music":
			if len(self.sport) > 0:
				self["sport"].show()
				self["Sport"].show()
				self.currentlist = "sport"
				cnt_tmp_ls = len(self.sport)
			elif len(self.newsdoku) > 0:
				self["newsdoku"].show()
				self["NewsDoku"].show()
				self.currentlist = "newsdoku"
				cnt_tmp_ls = len(self.newsdoku)
			elif len(self.porn) > 0:
				self["porn"].show()
				self["Porn"].show()
				self.currentlist = "porn"
				cnt_tmp_ls = len(self.porn)
			elif len(self.useradditions) > 0:
				self["useradditions"].show()
				self["Useradditions"].show()
				self.currentlist = "useradditions"
				cnt_tmp_ls = len(self.useradditions)
			elif len(self.mediatheken) > 0:
				self["mediatheken"].show()
				self["Mediatheken"].show()
				self.currentlist = "mediatheken"
				cnt_tmp_ls = len(self.mediatheken)
			elif len(self.fun) > 0:
				self["fun"].show()
				self["Fun"].show()
				self.currentlist = "fun"
				cnt_tmp_ls = len(self.fun)
			else:
				self["music"].show()
				self["Music"].show()
				self.currentlist = "music"
				cnt_tmp_ls = len(self.music)
		elif self.currentlist == "sport":
			if len(self.newsdoku) > 0:
				self["newsdoku"].show()
				self["NewsDoku"].show()
				self.currentlist = "newsdoku"
				cnt_tmp_ls = len(self.newsdoku)
			elif len(self.porn) > 0:
				self["porn"].show()
				self["Porn"].show()
				self.currentlist = "porn"
				cnt_tmp_ls = len(self.porn)
			elif len(self.useradditions) > 0:
				self["useradditions"].show()
				self["Useradditions"].show()
				self.currentlist = "useradditions"
				cnt_tmp_ls = len(self.useradditions)
			elif len(self.mediatheken) > 0:
				self["mediatheken"].show()
				self["Mediatheken"].show()
				self.currentlist = "mediatheken"
				cnt_tmp_ls = len(self.mediatheken)
			elif len(self.fun) > 0:
				self["fun"].show()
				self["Fun"].show()
				self.currentlist = "fun"
				cnt_tmp_ls = len(self.fun)
			elif len(self.music) > 0:
				self["music"].show()
				self["Music"].show()
				self.currentlist = "music"
				cnt_tmp_ls = len(self.music)
			else:
				self["sport"].show()
				self["Sport"].show()
				self.currentlist = "sport"
				cnt_tmp_ls = len(self.sport)
		elif self.currentlist == "newsdoku":
			if len(self.porn) > 0:
				self["porn"].show()
				self["Porn"].show()
				self.currentlist = "porn"
				cnt_tmp_ls = len(self.porn)
			elif len(self.useradditions) > 0:
				self["useradditions"].show()
				self["Useradditions"].show()
				self.currentlist = "useradditions"
				cnt_tmp_ls = len(self.useradditions)
			elif len(self.mediatheken) > 0:
				self["mediatheken"].show()
				self["Mediatheken"].show()
				self.currentlist = "mediatheken"
				cnt_tmp_ls = len(self.mediatheken)
			elif len(self.fun) > 0:
				self["fun"].show()
				self["Fun"].show()
				self.currentlist = "fun"
				cnt_tmp_ls = len(self.fun)
			elif len(self.music) > 0:
				self["music"].show()
				self["Music"].show()
				self.currentlist = "music"
				cnt_tmp_ls = len(self.music)
			elif len(self.sport) > 0:
				self["sport"].show()
				self["Sport"].show()
				self.currentlist = "sport"
				cnt_tmp_ls = len(self.sport)
			else:
				self["newsdoku"].show()
				self["NewsDoku"].show()
				self.currentlist = "newsdoku"
				cnt_tmp_ls = len(self.newsdoku)
		elif self.currentlist == "porn":
			if len(self.useradditions) > 0:
				self["useradditions"].show()
				self["Useradditions"].show()
				self.currentlist = "useradditions"
				cnt_tmp_ls = len(self.useradditions)
			elif len(self.mediatheken) > 0:
				self["mediatheken"].show()
				self["Mediatheken"].show()
				self.currentlist = "mediatheken"
				cnt_tmp_ls = len(self.mediatheken)
			elif len(self.fun) > 0:
				self["fun"].show()
				self["Fun"].show()
				self.currentlist = "fun"
				cnt_tmp_ls = len(self.fun)
			elif len(self.music) > 0:
				self["music"].show()
				self["Music"].show()
				self.currentlist = "music"
				cnt_tmp_ls = len(self.music)
			elif len(self.sport) > 0:
				self["sport"].show()
				self["Sport"].show()
				self.currentlist = "sport"
				cnt_tmp_ls = len(self.sport)
			elif len(self.newsdoku) > 0:
				self["newsdoku"].show()
				self["NewsDoku"].show()
				self.currentlist = "newsdoku"
				cnt_tmp_ls = len(self.newsdoku)
			else:
				self["porn"].show()
				self["Porn"].show()
				self.currentlist = "porn"
				cnt_tmp_ls = len(self.porn)
		elif self.currentlist == "useradditions":
			if len(self.mediatheken) > 0:
				self["mediatheken"].show()
				self["Mediatheken"].show()
				self.currentlist = "mediatheken"
				cnt_tmp_ls = len(self.mediatheken)
			elif len(self.fun) > 0:
				self["fun"].show()
				self["Fun"].show()
				self.currentlist = "fun"
				cnt_tmp_ls = len(self.fun)
			elif len(self.music) > 0:
				self["music"].show()
				self["Music"].show()
				self.currentlist = "music"
				cnt_tmp_ls = len(self.music)
			elif len(self.sport) > 0:
				self["sport"].show()
				self["Sport"].show()
				self.currentlist = "sport"
				cnt_tmp_ls = len(self.sport)
			elif len(self.newsdoku) > 0:
				self["newsdoku"].show()
				self["NewsDoku"].show()
				self.currentlist = "newsdoku"
				cnt_tmp_ls = len(self.newsdoku)
			elif len(self.porn) > 0:
				self["porn"].show()
				self["Porn"].show()
				self.currentlist = "porn"
				cnt_tmp_ls = len(self.porn)
			else:
				self["useradditions"].show()
				self["Useradditions"].show()
				self.currentlist = "useradditions"
				cnt_tmp_ls = len(self.useradditions)

		cnt_tmp_ls = int(cnt_tmp_ls)
		if int(self.cur_idx) < int(cnt_tmp_ls):
			self[self.currentlist].moveToIndex(int(self.cur_idx))
		else:
			idx = int(cnt_tmp_ls) -1
			self[self.currentlist].moveToIndex(int(idx))

		if cnt_tmp_ls > 0:
			auswahl = self[self.currentlist].getCurrent()[0][0]
			self.title = auswahl
			self['name'].setText(auswahl)

	def keyOK(self):
		if not testWebConnection():
			self.session.open(MessageBoxExt, _('No connection to the Internet available.'), MessageBoxExt.TYPE_INFO, timeout=3)
			return

		exist = self[self.currentlist].getCurrent()
		if exist == None:
			return
		auswahl = self[self.currentlist].getCurrent()[0][0]
		icon = self[self.currentlist].getCurrent()[0][1]
		mp_globals.activeIcon = icon

		self.pornscreen = None
		self.par1 = ""
		self.par2 = ""

		conf = xml.etree.cElementTree.parse(CONFIG)
		for x in conf.getroot():
			if x.tag == "set" and x.get("name") == 'additions':
				root =  x
				for x in root:
					if x.tag == "plugin":
						if x.get("type") == "mod":
							confcat = x.get("confcat")
							if auswahl ==  x.get("name").replace("&amp;","&"):
								status = [item for item in mp_globals.status if item[0] == x.get("modfile")]
								if status:
									if int(config.mediaportal.version.value) < int(status[0][1]):
										if status[0][1] == "9999":
											self.session.open(MessageBoxExt, _("This Plugin has been marked as \"not working\" by the developers.\n\nCurrent developer status of this Plugin is:\n\"%s\"\n\nIf someone else is willing to provide a fix for this Plugin then please get in contact with us.") % status[0][2], MessageBoxExt.TYPE_INFO)
										else:
											self.session.open(MessageBoxExt, _("This Plugin has been marked as \"not working\" by the developers.\n\nCurrent developer status of this Plugin is:\n\"%s\"") % status[0][2], MessageBoxExt.TYPE_INFO)
										if not config.mediaportal.debugMode.value == "High":
											return
								param = ""
								param1 = x.get("param1")
								param2 = x.get("param2")
								kids = x.get("kids")
								if param1 != "":
									param = ", \"" + param1 + "\""
									exec("self.par1 = \"" + x.get("param1") + "\"")
								if param2 != "":
									param = param + ", \"" + param2 + "\""
									exec("self.par2 = \"" + x.get("param2") + "\"")
								if confcat == "porn":
									exec("self.pornscreen = " + x.get("screen") + "")
								elif kids != "1" and config.mediaportal.kidspin.value:
									exec("self.pornscreen = " + x.get("screen") + "")
								else:
									exec("self.session.open(" + x.get("screen") + param + ")")

		xmlpath = resolveFilename(SCOPE_PLUGINS, "Extensions/MediaPortal/additions/")
		for file in os.listdir(xmlpath):
			if file.endswith(".xml") and file != "additions.xml":
				useraddition = xmlpath + file

				conf = xml.etree.cElementTree.parse(useraddition)
				for x in conf.getroot():
					if x.tag == "set" and x.get("name") == 'additions_user':
						root =  x
						for x in root:
							if x.tag == "plugin":
								if x.get("type") == "mod":
									confcat = x.get("confcat")
									if auswahl ==  x.get("name").replace("&amp;","&"):
										status = [item for item in mp_globals.status if item[0] == x.get("modfile")]
										if status:
											if int(config.mediaportal.version.value) < int(status[0][1]):
												if status[0][1] == "9999":
													self.session.open(MessageBoxExt, _("This Plugin has been marked as \"not working\" by the developers.\n\nCurrent developer status of this Plugin is:\n\"%s\"\n\nIf someone else is willing to provide a fix for this Plugin then please get in contact with us.") % status[0][2], MessageBoxExt.TYPE_INFO)
												else:
													self.session.open(MessageBoxExt, _("This Plugin has been marked as \"not working\" by the developers.\n\nCurrent developer status of this Plugin is:\n\"%s\"") % status[0][2], MessageBoxExt.TYPE_INFO)
												if not config.mediaportal.debugMode.value == "High":
													return
										param = ""
										param1 = x.get("param1")
										param2 = x.get("param2")
										kids = x.get("kids")
										if param1 != "":
											param = ", \"" + param1 + "\""
											exec("self.par1 = \"" + x.get("param1") + "\"")
										if param2 != "":
											param = param + ", \"" + param2 + "\""
											exec("self.par2 = \"" + x.get("param2") + "\"")
										if confcat == "porn":
											exec("self.pornscreen = " + x.get("screen") + "")
										elif kids != "1" and config.mediaportal.kidspin.value:
											exec("self.pornscreen = " + x.get("screen") + "")
										else:
											exec("self.session.open(" + x.get("screen") + param + ")")

		if self.pornscreen:
			if config.mediaportal.pornpin.value:
				if pincheck.pin_entered == False:
					self.session.openWithCallback(self.pincheckok, PinInputExt, pinList = [(config.mediaportal.adultpincode.value)], triesEntry = config.mediaportal.retries.adultpin, title = _("Please enter the correct PIN"), windowTitle = _("Enter adult PIN"))
				else:
					if self.par1 == "":
						self.session.open(self.pornscreen)
					elif self.par2 == "":
						self.session.open(self.pornscreen, self.par1)
					else:
						self.session.open(self.pornscreen, self.par1, self.par2)
			else:
				if self.par1 == "":
					self.session.open(self.pornscreen)
				elif self.par2 == "":
					self.session.open(self.pornscreen, self.par1)
				else:
					self.session.open(self.pornscreen, self.par1, self.par2)

	def pincheckok(self, pincode):
		if pincode:
			pincheck.pinEntered()
			if self.par1 == "":
				self.session.open(self.pornscreen)
			elif self.par2 == "":
				self.session.open(self.pornscreen, self.par1)
			else:
				self.session.open(self.pornscreen, self.par1, self.par2)

	def keyCancel(self):
		self.close(self.session, True, self.lastservice)

	def restart(self):
		if autoStartTimer is not None:
			autoStartTimer.update()
		self.close(self.session, False, self.lastservice)

class MPpluginSort(Screen):

	def __init__(self, session):

		self.skin_path = mp_globals.pluginPath + mp_globals.skinsPath

		path = "%s/%s/MP_Sort.xml" % (self.skin_path, config.mediaportal.skin.value)
		if not fileExists(path):
			path = self.skin_path + mp_globals.skinFallback + "/MP_Sort.xml"
		with open(path, "r") as f:
			self.skin = f.read()
			f.close()

		self["hidePig"] = Boolean()
		self["hidePig"].setBoolean(config.mediaportal.minitv.value)

		Screen.__init__(self, session)

		self.list = []
		self.chooseMenuList = MenuList([], enableWrapAround=True, content=eListboxPythonMultiContent)
		self.chooseMenuList.l.setFont(0, gFont(mp_globals.font, mp_globals.fontsize))
		self.chooseMenuList.l.setItemHeight(mp_globals.fontsize + 2 * mp_globals.sizefactor)
		self["config2"] = self.chooseMenuList
		self.selected = False

		self["actions"] = ActionMap(["MP_Actions"], {
			"ok":	self.select,
			"cancel": self.keyCancel
		}, -1)

		self.readconfig()

	def select(self):
		if not self.selected:
			self.last_newidx = self["config2"].getSelectedIndex()
			self.last_plugin_name = self["config2"].getCurrent()[0][0]
			self.last_plugin_pic = self["config2"].getCurrent()[0][1]
			self.last_plugin_genre = self["config2"].getCurrent()[0][2]
			self.last_plugin_hits = self["config2"].getCurrent()[0][3]
			self.last_plugin_msort = self["config2"].getCurrent()[0][4]
			print "Select:", self.last_plugin_name, self.last_newidx
			self.selected = True
			self.readconfig()
		else:
			self.now_newidx = self["config2"].getSelectedIndex()
			self.now_plugin_name = self["config2"].getCurrent()[0][0]
			self.now_plugin_pic = self["config2"].getCurrent()[0][1]
			self.now_plugin_genre = self["config2"].getCurrent()[0][2]
			self.now_plugin_hits = self["config2"].getCurrent()[0][3]
			self.now_plugin_msort = self["config2"].getCurrent()[0][4]

			count_move = 0
			config_tmp = open("/etc/enigma2/mp_pluginliste.tmp" , "w")
			# del element from list
			del self.config_list_select[int(self.last_newidx)];
			# add element to list at the right place
			self.config_list_select.insert(int(self.now_newidx), (self.last_plugin_name, self.last_plugin_pic, self.last_plugin_genre, self.last_plugin_hits, self.now_newidx));

			# liste neu nummerieren
			for (name, pic, genre, hits, msort) in self.config_list_select:
				count_move += 1
				config_tmp.write('"%s" "%s" "%s" "%s" "%s"\n' % (name, pic, genre, hits, count_move))

			print "change:", self.last_newidx+1, "with", self.now_newidx+1, "total:", len(self.config_list_select)

			config_tmp.close()
			shutil.move("/etc/enigma2/mp_pluginliste.tmp", "/etc/enigma2/mp_pluginliste")
			self.selected = False
			self.readconfig()

	def readconfig(self):
		config_read = open("/etc/enigma2/mp_pluginliste","r")
		self.config_list = []
		self.config_list_select = []
		print "Filter:", config.mediaportal.filter.value
		for line in config_read.readlines():
			ok = re.findall('"(.*?)" "(.*?)" "(.*?)" "(.*?)" "(.*?)"', line, re.S)
			if ok:
				(name, pic, genre, hits, msort) = ok[0]
				if config.mediaportal.filter.value != "ALL":
					if genre == config.mediaportal.filter.value:
						self.config_list_select.append((name, pic, genre, hits, msort))
						self.config_list.append(self.show_menu(name, pic, genre, hits, msort))
				else:
					self.config_list_select.append((name, pic, genre, hits, msort))
					self.config_list.append(self.show_menu(name, pic, genre, hits, msort))

		self.config_list.sort(key=lambda x: int(x[0][4]))
		self.config_list_select.sort(key=lambda x: int(x[4]))
		self.chooseMenuList.setList(self.config_list)
		config_read.close()

	def show_menu(self, name, pic, genre, hits, msort):
		res = [(name, pic, genre, hits, msort)]
		if mp_globals.videomode == 2:
			res.append(MultiContentEntryText(pos=(80, 0), size=(500, 30), font=0, text=name, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER))
			if self.selected and name == self.last_plugin_name:
				res.append(MultiContentEntryPixmapAlphaBlend(pos=(45, 3), size=(24, 24), png=loadPNG("/usr/lib/enigma2/python/Plugins/Extensions/MediaPortal/images/select.png")))
		else:
			res.append(MultiContentEntryText(pos=(80, 0), size=(500, 23), font=0, text=name, flags=RT_HALIGN_LEFT | RT_VALIGN_CENTER))
			if self.selected and name == self.last_plugin_name:
				res.append(MultiContentEntryPixmapAlphaBlend(pos=(45, 2), size=(21, 21), png=loadPNG("/usr/lib/enigma2/python/Plugins/Extensions/MediaPortal/images/select.png")))
		return res

	def keyCancel(self):
		config.mediaportal.sortplugins.value = "user"
		self.close()

class MPWall(Screen, HelpableScreen):

	def __init__(self, session, lastservice, filter):
		self.lastservice = mp_globals.lastservice = lastservice
		self.wallbw = False
		self.wallzoom = False

		self.plugin_liste = []

		conf = xml.etree.cElementTree.parse(CONFIG)
		for x in conf.getroot():
			if x.tag == "set" and x.get("name") == 'additions':
				root =  x
				for x in root:
					if x.tag == "plugin":
						if x.get("type") == "mod":
							modfile = x.get("modfile")
							confcat = x.get("confcat")
							if not config.mediaportal.showporn.value and confcat == "porn":
								pass
							else:
								gz = x.get("gz")
								if not config.mediaportal.showuseradditions.value and gz == "1":
									pass
								else:
									mod = eval("config.mediaportal." + x.get("confopt") + ".value")
									if mod:
										y = eval("self.plugin_liste.append((\"" + x.get("name").replace("&amp;","&") + "\", \"" + x.get("icon") + "\", \"" + x.get("filter") + "\"))")

		xmlpath = resolveFilename(SCOPE_PLUGINS, "Extensions/MediaPortal/additions/")
		for file in os.listdir(xmlpath):
			if file.endswith(".xml") and file != "additions.xml":
				useraddition = xmlpath + file

				conf = xml.etree.cElementTree.parse(useraddition)
				for x in conf.getroot():
					if x.tag == "set" and x.get("name") == 'additions_user':
						root =  x
						for x in root:
							if x.tag == "plugin":
								if x.get("type") == "mod":
									modfile = x.get("modfile")
									confcat = x.get("confcat")
									if not config.mediaportal.showporn.value and confcat == "porn":
										pass
									else:
										gz = x.get("gz")
										if not config.mediaportal.showuseradditions.value and gz == "1":
											pass
										else:
											mod = eval("config.mediaportal." + x.get("confopt") + ".value")
											if mod:
												y = eval("self.plugin_liste.append((\"" + x.get("name").replace("&amp;","&") + "\", \"" + x.get("icon") + "\", \"" + x.get("filter") + "\"))")

		if len(self.plugin_liste) == 0:
			self.plugin_liste.append(("","","Mediathek"))

		# Porn
		if (config.mediaportal.showporn.value == False and config.mediaportal.filter.value == 'Porn'):
			config.mediaportal.filter.value = 'ALL'

		# User-additions
		if (config.mediaportal.showuseradditions.value == False and config.mediaportal.filter.value == 'User-additions'):
			config.mediaportal.filter.value = 'ALL'

		# Plugin Sortierung
		if config.mediaportal.sortplugins != "default":

			# Erstelle Pluginliste falls keine vorhanden ist.
			self.sort_plugins_file = "/etc/enigma2/mp_pluginliste"
			if not fileExists(self.sort_plugins_file):
				print "Erstelle Wall-Pluginliste."
				open(self.sort_plugins_file,"w").close()

			pluginliste_leer = os.path.getsize(self.sort_plugins_file)
			if pluginliste_leer == 0:
				print "1st time - Schreibe Wall-Pluginliste."
				first_count = 0
				read_pluginliste = open(self.sort_plugins_file,"a")
				for name,picname,genre in self.plugin_liste:
					read_pluginliste.write('"%s" "%s" "%s" "%s" "%s"\n' % (name, picname, genre, "0", str(first_count)))
					first_count += 1
				read_pluginliste.close()
				print "Wall-Pluginliste wurde erstellt."

			# Lese Pluginliste ein.
			if fileExists(self.sort_plugins_file):

				count_sort_plugins_file = len(open(self.sort_plugins_file).readlines())
				count_plugin_liste = len(self.plugin_liste)

				if int(count_plugin_liste) != int(count_sort_plugins_file):
					print "Ein Plugin wurde aktiviert oder deaktiviert.. erstelle neue pluginliste."

					read_pluginliste_tmp = open(self.sort_plugins_file+".tmp","w")
					read_pluginliste = open(self.sort_plugins_file,"r")
					p_dupeliste = []

					for rawData in read_pluginliste.readlines():
						data = re.findall('"(.*?)" "(.*?)" "(.*?)" "(.*?)" "(.*?)"', rawData, re.S)

						if data:
							(p_name, p_picname, p_genre, p_hits, p_sort) = data[0]
							pop_count = 0
							for pname, ppic, pgenre in self.plugin_liste:
								if p_name not in p_dupeliste:
									if p_name == pname:
										read_pluginliste_tmp.write('"%s" "%s" "%s" "%s" "%s"\n' % (p_name, p_picname, pgenre, p_hits, p_sort))
										p_dupeliste.append((p_name))
										self.plugin_liste.pop(int(pop_count))

									pop_count += 1

					if len(self.plugin_liste) != 0:
						for pname, ppic, pgenre in self.plugin_liste:
							read_pluginliste_tmp.write('"%s" "%s" "%s" "%s" "%s"\n' % (pname, ppic, pgenre, "0", "99"))

					read_pluginliste.close()
					read_pluginliste_tmp.close()
					shutil.move(self.sort_plugins_file+".tmp", self.sort_plugins_file)

				self.new_pluginliste = []
				read_pluginliste = open(self.sort_plugins_file,"r")
				for rawData in read_pluginliste.readlines():
					data = re.findall('"(.*?)" "(.*?)" "(.*?)" "(.*?)" "(.*?)"', rawData, re.S)
					if data:
						(p_name, p_picname, p_genre, p_hits, p_sort) = data[0]
						self.new_pluginliste.append((p_name, p_picname, p_genre, p_hits, p_sort))
				read_pluginliste.close()

			# Sortieren nach hits
			if config.mediaportal.sortplugins.value == "hits":
				self.new_pluginliste.sort(key=lambda x: int(x[3]))
				self.new_pluginliste.reverse()

			# Sortieren nach abcde..
			elif config.mediaportal.sortplugins.value == "abc":
				self.new_pluginliste.sort(key=lambda x: str(x[0]).lower())

			elif config.mediaportal.sortplugins.value == "user":
				self.new_pluginliste.sort(key=lambda x: int(x[4]))

			self.plugin_liste = self.new_pluginliste

		skincontent = ""

		if config.mediaportal.wallmode.value == "bw":
			self.wallbw = True
		elif config.mediaportal.wallmode.value == "bw_zoom":
			self.wallbw = True
			self.wallzoom = True
		elif config.mediaportal.wallmode.value == "color_zoom":
			self.wallzoom = True

		if mp_globals.videomode == 2:
			screenwidth = 1920
			posxstart = 85
			posxplus = 220
			posystart = 310
			posyplus = 122
			iconsize = "210,112"
			iconsizezoom = "308,190"
			zoomoffsetx = 49
			zoomoffsety = 39
		else:
			screenwidth = 1280
			posxstart = 22
			posxplus = 155
			posystart = 210
			posyplus = 85
			iconsize = "150,80"
			iconsizezoom = "220,136"
			zoomoffsetx = 35
			zoomoffsety = 28
		posx = posxstart
		posy = posystart
		for x in range(1,len(self.plugin_liste)+1):
			skincontent += "<widget name=\"zeile" + str(x) + "\" position=\"" + str(posx) + "," + str(posy) + "\" size=\"" + iconsize + "\" zPosition=\"1\" transparent=\"1\" alphatest=\"blend\" />"
			if self.wallzoom:
				skincontent += "<widget name=\"zeile_bw" + str(x) + "\" position=\"" + str(posx-zoomoffsetx) + "," + str(posy-zoomoffsety) + "\" size=\"" + iconsizezoom + "\" zPosition=\"2\" transparent=\"1\" alphatest=\"blend\" />"
			elif self.wallbw:
				skincontent += "<widget name=\"zeile_bw" + str(x) + "\" position=\"" + str(posx) + "," + str(posy) + "\" size=\"" + iconsize + "\" zPosition=\"1\" transparent=\"1\" alphatest=\"blend\" />"
			posx += posxplus
			if x in [8, 16, 24, 32, 48, 56, 64, 72, 88, 96, 104, 112, 128, 136, 144, 152, 168, 176, 184, 192]:
				posx = posxstart
				posy += posyplus
			elif x in [40, 80, 120, 160, 200]:
				posx = posxstart
				posy = posystart

		# Page Style
		if config.mediaportal.pagestyle.value == "Graphic":
			self.dump_liste_page_tmp = self.plugin_liste
			if config.mediaportal.filter.value != "ALL":
				self.plugin_liste_page_tmp = []
				self.plugin_liste_page_tmp = [x for x in self.dump_liste_page_tmp if re.search(config.mediaportal.filter.value, x[2])]
			else:
				self.plugin_liste_page_tmp = self.plugin_liste

			if len(self.plugin_liste_page_tmp) != 0:
				self.counting_pages = int(round(float((len(self.plugin_liste_page_tmp)-1) / 40) + 0.5))
				print "COUNTING PAGES:", self.counting_pages
				pagebar_size = self.counting_pages * 26 + (self.counting_pages-1) * 4
				start_pagebar = int(screenwidth / 2 - pagebar_size / 2)

				for x in range(1,self.counting_pages+1):
					if mp_globals.videomode == 2:
						normal = 960
					elif config.mediaportal.skin.value == "original":
						normal = 650
					else:
						normal = 669
					skincontent += "<widget name=\"page_empty" + str(x) + "\" position=\"" + str(start_pagebar) + "," + str(normal) + "\" size=\"26,26\" zPosition=\"2\" transparent=\"1\" alphatest=\"blend\" />"
					skincontent += "<widget name=\"page_sel" + str(x) + "\" position=\"" + str(start_pagebar) + "," + str(normal) + "\" size=\"26,26\" zPosition=\"2\" transparent=\"1\" alphatest=\"blend\" />"
					start_pagebar += 30

		self.skin_dump = ""
		if self.wallzoom:
			pass
		else:
			self.skin_dump += "<widget name=\"frame\" position=\"" + str(posxstart) + "," + str(posystart) + "\" size=\"" + iconsize + "\" zPosition=\"3\" transparent=\"1\" alphatest=\"blend\" />"
		self.skin_dump += skincontent
		self.skin_dump += "</screen>"

		self.skin_path = mp_globals.pluginPath + mp_globals.skinsPath

		self.images_path = "%s/%s/images" % (self.skin_path, config.mediaportal.skin.value)
		if not fileExists(self.images_path):
			self.images_path = self.skin_path + mp_globals.skinFallback + "/images"

		path = "%s/%s/MP_Wall.xml" % (self.skin_path, config.mediaportal.skin.value)
		if not fileExists(path):
			path = self.skin_path + mp_globals.skinFallback + "/MP_Wall.xml"
		with open(path, "r") as f:
			self.skin_dump2 = f.read()
			self.skin_dump2 += self.skin_dump
			self.skin = self.skin_dump2
			f.close()

		self["hidePig"] = Boolean()
		self["hidePig"].setBoolean(config.mediaportal.minitv.value)

		Screen.__init__(self, session)

		addFont(resolveFilename(SCOPE_PLUGINS, "Extensions/MediaPortal/resources/") + "mediaportal1.ttf", "mediaportal", 100, False)

		if config.mediaportal.backgroundtv.value:
			config.mediaportal.minitv.value = True
			config.mediaportal.minitv.save()
			config.mediaportal.restorelastservice.value = "2"
			config.mediaportal.restorelastservice.save()
			configfile.save()
			session.nav.stopService()

		self["actions"] = ActionMap(["MP_Actions"], {
			"up"    : self.keyUp,
			"down"  : self.keyDown,
			"left"  : self.keyLeft,
			"right" : self.keyRight,
			"info"  : self.showPorn,
			"0": boundFunction(self.gotFilter, "ALL"),
			"1": boundFunction(self.gotFilter, "Mediathek"),
			"2": boundFunction(self.gotFilter, "Fun"),
			"3": boundFunction(self.gotFilter, "Music"),
			"4": boundFunction(self.gotFilter, "Sport"),
			"5": boundFunction(self.gotFilter, "NewsDoku"),
			"6": boundFunction(self.gotFilter, "Porn"),
			"7": boundFunction(self.gotFilter, "User-additions")
		}, -1)
		self["MP_Actions"] = HelpableActionMap(self, "MP_Actions", {
			"blue"  : (self.changeFilter, _("Change filter")),
			"green" : (self.chSort, _("Change sort order")),
			"yellow": (self.manuelleSortierung, _("Manual sorting")),
			"red"   : (self.keySimpleList, _("Open SimpleList")),
			"ok"    : (self.keyOK, _("Open selected Plugin")),
			"cancel": (self.keyCancel, _("Exit MediaPortal")),
			"nextBouquet" :	(self.page_next, _("Next page")),
			"prevBouquet" :	(self.page_back, _("Previous page")),
			"menu" : (self.keySetup, _("MediaPortal Setup")),
			config.mediaportal.simplelist_key.value: (self.keySimpleList, _("Open SimpleList"))
		}, -1)

		self['name'] = Label("")
		self['version'] = Label(config.mediaportal.version.value[0:8])
		self['red'] = Label("SimpleList")
		self['green'] = Label("")
		self['yellow'] = Label(_("Sort"))
		self['blue'] = Label("")
		self['CH+'] = Label(_("CH+"))
		self['CH-'] = Label(_("CH-"))
		self['PVR'] = Label(_("PVR"))
		self['Exit'] = Label(_("Exit"))
		self['Help'] = Label(_("Help"))
		self['Menu'] = Label(_("Menu"))
		self['page'] = Label("")
		self["frame"] = MovingPixmap()

		for x in range(1,len(self.plugin_liste)+1):
			if self.wallbw or self.wallzoom:
				self["zeile"+str(x)] = Pixmap()
				self["zeile"+str(x)].show()
				self["zeile_bw"+str(x)] = Pixmap()
				self["zeile_bw"+str(x)].hide()
			else:
				self["zeile"+str(x)] = Pixmap()
				self["zeile"+str(x)].show()

		# Apple Page Style
		if config.mediaportal.pagestyle.value == "Graphic" and len(self.plugin_liste_page_tmp) != 0:
			for x in range(1,self.counting_pages+1):
				self["page_empty"+str(x)] = Pixmap()
				self["page_empty"+str(x)].show()
				self["page_sel"+str(x)] = Pixmap()
				self["page_sel"+str(x)].show()

		self.selektor_index = 1
		self.select_list = 0
		self.picload = ePicLoad()

		HelpableScreen.__init__(self)
		self.onFirstExecBegin.append(self._onFirstExecBegin)
		self.onFirstExecBegin.append(self.checkPathes)
		self.onFirstExecBegin.append(self.status)

	def checkPathes(self):
		CheckPathes(self.session).checkPathes(self.cb_checkPathes)

	def cb_checkPathes(self):
		self.session.openWithCallback(self.restart, MPSetup)

	def status(self):
		update_agent = getUserAgent()
		update_url = getUpdateUrl()
		twAgentGetPage(update_url, agent=update_agent, timeout=30).addCallback(self.checkstatus)

	def checkstatus(self, html):
		if re.search(".*?<html", html):
			return
		self.html = html
		tmp_infolines = html.splitlines()
		statusurl = tmp_infolines[4]
		update_agent = getUserAgent()
		twAgentGetPage(statusurl, agent=update_agent, timeout=30).addCallback(_status)

	def manuelleSortierung(self):
		if config.mediaportal.filter.value == 'ALL':
			self.session.openWithCallback(self.restart, MPpluginSort)
		else:
			self.session.open(MessageBoxExt, _('Ordering is only possible with filter "ALL".'), MessageBoxExt.TYPE_INFO, timeout=3)

	def hit_plugin(self, pname):
		if fileExists(self.sort_plugins_file):
			read_pluginliste = open(self.sort_plugins_file,"r")
			read_pluginliste_tmp = open(self.sort_plugins_file+".tmp","w")
			for rawData in read_pluginliste.readlines():
				data = re.findall('"(.*?)" "(.*?)" "(.*?)" "(.*?)" "(.*?)"', rawData, re.S)
				if data:
					(p_name, p_picname, p_genre, p_hits, p_sort) = data[0]
					if pname == p_name:
						new_hits = int(p_hits)+1
						read_pluginliste_tmp.write('"%s" "%s" "%s" "%s" "%s"\n' % (p_name, p_picname, p_genre, str(new_hits), p_sort))
					else:
						read_pluginliste_tmp.write('"%s" "%s" "%s" "%s" "%s"\n' % (p_name, p_picname, p_genre, p_hits, p_sort))
			read_pluginliste.close()
			read_pluginliste_tmp.close()
			shutil.move(self.sort_plugins_file+".tmp", self.sort_plugins_file)

	def _onFirstExecBegin(self):
		_hosters()
		if not mp_globals.start:
			self.close(self.session, True, self.lastservice)
		if config.mediaportal.autoupdate.value:
			checkupdate(self.session).checkforupdate()

		if config.mediaportal.filter.value == "ALL":
			name = _("ALL")
		elif config.mediaportal.filter.value == "Mediathek":
			name = _("Libraries")
		elif config.mediaportal.filter.value == "User-additions":
			name = _("User-additions")
		elif config.mediaportal.filter.value == "Fun":
			name = _("Fun")
		elif config.mediaportal.filter.value == "NewsDoku":
			name = _("News&Documentary")
		elif config.mediaportal.filter.value == "Music":
			name = _("Music")
		elif config.mediaportal.filter.value == "Sport":
			name = _("Sports")
		elif config.mediaportal.filter.value == "Porn":
			name = _("Porn")
		self['blue'].setText(name)
		self.sortplugin = config.mediaportal.sortplugins.value
		if self.sortplugin == "hits":
			self.sortplugin = "Hits"
		elif self.sortplugin == "abc":
			self.sortplugin = "ABC"
		elif self.sortplugin == "user":
			self.sortplugin = "User"
		self['green'].setText(self.sortplugin)
		self.dump_liste = self.plugin_liste
		if config.mediaportal.filter.value != "ALL":
			self.plugin_liste = []
			self.plugin_liste = [x for x in self.dump_liste if re.search(config.mediaportal.filter.value, x[2])]
		if len(self.plugin_liste) == 0:
			self.chFilter()
			if config.mediaportal.filter.value == "ALL":
				name = _("ALL")
			elif config.mediaportal.filter.value == "Mediathek":
				name = _("Libraries")
			elif config.mediaportal.filter.value == "User-additions":
				name = _("User-additions")
			elif config.mediaportal.filter.value == "Fun":
				name = _("Fun")
			elif config.mediaportal.filter.value == "NewsDoku":
				name = _("News&Documentary")
			elif config.mediaportal.filter.value == "Music":
				name = _("Music")
			elif config.mediaportal.filter.value == "Sport":
				name = _("Sports")
			elif config.mediaportal.filter.value == "Porn":
				name = _("Porn")
			self['blue'].setText(name)

		if config.mediaportal.sortplugins.value == "hits":
			self.plugin_liste.sort(key=lambda x: int(x[3]))
			self.plugin_liste.reverse()
		elif config.mediaportal.sortplugins.value == "abc":
			self.plugin_liste.sort(key=lambda t : t[0].lower())
		elif config.mediaportal.sortplugins.value == "user":
			self.plugin_liste.sort(key=lambda x: int(x[4]))

		poster_path = "/usr/lib/enigma2/python/Plugins/Extensions/MediaPortal/images/Selektor_%s.png" % config.mediaportal.selektor.value

		scale = AVSwitch().getFramebufferScale()
		if mp_globals.videomode == 2:
			self.picload.setPara((210, 112, scale[0], scale[1], True, 1, "#FF000000"))
		else:
			self.picload.setPara((150, 80, scale[0], scale[1], True, 1, "#FF000000"))
		if mp_globals.isDreamOS:
			self.picload.startDecode(poster_path, False)
		else:
			self.picload.startDecode(poster_path, 0, 0, False)

		self["frame"].instance.setPixmap(gPixmapPtr())
		pic = self.picload.getData()
		if pic != None:
			self["frame"].instance.setPixmap(pic)

		icon_url = getIconUrl()
		if self.wallbw:
			icons_hashes = grabpage(icon_url+"icons_bw/hashes")
		else:
			icons_hashes = grabpage(icon_url+"icons/hashes")
		if icons_hashes:
			icons_data = re.findall('(.*?)\s\*(.*?\.png)', icons_hashes)
		else:
			icons_data = None


		icons_data_zoom = None
		if self.wallzoom:
			icons_hashes_zoom = grabpage(icon_url+"icons_zoom/hashes")
			if icons_hashes_zoom:
				icons_data_zoom = re.findall('(.*?)\s\*(.*?\.png)', icons_hashes_zoom)

		logo_hashes = grabpage(icon_url+"logos/hashes")
		if logo_hashes:
			logo_data = re.findall('(.*?)\s\*(.*?\.png)', logo_hashes)
		else:
			logo_data = None

		for x in range(1,len(self.plugin_liste)+1):
			postername = self.plugin_liste[int(x)-1][1]
			remote_hash = ""
			ds = defer.DeferredSemaphore(tokens=5)
			if self.wallbw:
				poster_path = "%s/%s.png" % (config.mediaportal.iconcachepath.value + "icons_bw", postername)
				url = icon_url+"icons_bw/" + postername + ".png"
				if not fileExists(poster_path):
					if icons_data:
						for a,b in icons_data:
							if b == postername+'.png':
								ds.run(downloadPage, url, poster_path)
					poster_path = "%s/images/comingsoon.png" % mp_globals.pluginPath
				else:
					local_hash = hashlib.md5(open(poster_path, 'rb').read()).hexdigest()
					if icons_data:
						for a,b in icons_data:
							if b == postername+'.png': remote_hash = a
						if remote_hash != local_hash:
							ds.run(downloadPage, url, poster_path)
							poster_path = "%s/images/comingsoon.png" % mp_globals.pluginPath
			else:
				poster_path = "%s/%s.png" % (config.mediaportal.iconcachepath.value + "icons", postername)
				url = icon_url+"icons/" + postername + ".png"
				if not fileExists(poster_path):
					if icons_data:
						for a,b in icons_data:
							if b == postername+'.png':
								ds.run(downloadPage, url, poster_path)
					poster_path = "%s/images/comingsoon.png" % mp_globals.pluginPath
				else:
					local_hash = hashlib.md5(open(poster_path, 'rb').read()).hexdigest()
					if icons_data:
						for a,b in icons_data:
							if b == postername+'.png': remote_hash = a
						if remote_hash != local_hash:
							ds.run(downloadPage, url, poster_path)
							poster_path = "%s/images/comingsoon.png" % mp_globals.pluginPath

			logo_path = "%s/%s.png" % (config.mediaportal.iconcachepath.value + "logos", postername)
			url = icon_url+"logos/" + postername + ".png"
			if not fileExists(logo_path):
				if logo_data:
					for a,b in logo_data:
						if b == postername+'.png':
							ds.run(downloadPage, url, logo_path)
			else:
				local_hash = hashlib.md5(open(logo_path, 'rb').read()).hexdigest()
				if logo_data:
					for a,b in logo_data:
						if b == postername+'.png': remote_hash = a
					if remote_hash != local_hash:
						ds.run(downloadPage, url, logo_path)

			scale = AVSwitch().getFramebufferScale()
			if mp_globals.videomode == 2:
				self.picload.setPara((210, 112, scale[0], scale[1], True, 1, "#FF000000"))
			else:
				self.picload.setPara((150, 80, scale[0], scale[1], True, 1, "#FF000000"))
			if mp_globals.isDreamOS:
				self.picload.startDecode(poster_path, False)
			else:
				self.picload.startDecode(poster_path, 0, 0, False)

			self["zeile"+str(x)].instance.setPixmap(gPixmapPtr())
			self["zeile"+str(x)].hide()
			pic = self.picload.getData()
			if pic != None:
				self["zeile"+str(x)].instance.setPixmap(pic)
				if x <= 40:
					self["zeile"+str(x)].show()

			if self.wallzoom:
				poster_path = "%s/%s.png" % (config.mediaportal.iconcachepath.value + "icons_zoom", postername)
				url = icon_url+"icons_zoom/" + postername + ".png"
				if not fileExists(poster_path):
					if icons_data_zoom:
						for a,b in icons_data_zoom:
							if b == postername+'.png':
								ds.run(downloadPage, url, poster_path)
					poster_path = "%s/images/comingsoon_zoom.png" % mp_globals.pluginPath
				else:
					local_hash = hashlib.md5(open(poster_path, 'rb').read()).hexdigest()
					if icons_data_zoom:
						for a,b in icons_data_zoom:
							if b == postername+'.png': remote_hash = a
						if remote_hash != local_hash:
							ds.run(downloadPage, url, poster_path)
							poster_path = "%s/images/comingsoon_zoom.png" % mp_globals.pluginPath
				scale = AVSwitch().getFramebufferScale()
				if mp_globals.videomode == 2:
					self.picload.setPara((308, 190, scale[0], scale[1], True, 1, "#FF000000"))
				else:
					self.picload.setPara((220, 136, scale[0], scale[1], True, 1, "#FF000000"))
				if mp_globals.isDreamOS:
					self.picload.startDecode(poster_path, False)
				else:
					self.picload.startDecode(poster_path, 0, 0, False)

				self["zeile_bw"+str(x)].instance.setPixmap(gPixmapPtr())
				self["zeile_bw"+str(x)].hide()
				pic = self.picload.getData()
				if pic != None:
					self["zeile_bw"+str(x)].instance.setPixmap(pic)
					if x <= 40:
						self["zeile_bw"+str(x)].hide()
			elif self.wallbw:
				poster_path = "%s/%s.png" % (config.mediaportal.iconcachepath.value + "icons", postername)
				if not fileExists(poster_path):
					poster_path = "%s/images/comingsoon.png" % mp_globals.pluginPath

				scale = AVSwitch().getFramebufferScale()
				if mp_globals.videomode == 2:
					self.picload.setPara((210, 112, scale[0], scale[1], True, 1, "#FF000000"))
				else:
					self.picload.setPara((150, 80, scale[0], scale[1], True, 1, "#FF000000"))
				if mp_globals.isDreamOS:
					self.picload.startDecode(poster_path, False)
				else:
					self.picload.startDecode(poster_path, 0, 0, False)

				self["zeile_bw"+str(x)].instance.setPixmap(gPixmapPtr())
				self["zeile_bw"+str(x)].hide()
				pic = self.picload.getData()
				if pic != None:
					self["zeile_bw"+str(x)].instance.setPixmap(pic)
					if x <= 40:
						self["zeile_bw"+str(x)].hide()

		if config.mediaportal.pagestyle.value == "Graphic" and len(self.plugin_liste_page_tmp) != 0:
			for x in range(1,self.counting_pages+1):
				poster_path = "%s/page_select.png" % (self.images_path)
				self["page_sel"+str(x)].instance.setPixmap(gPixmapPtr())
				self["page_sel"+str(x)].hide()
				pic = LoadPixmap(cached=True, path=poster_path)
				if pic != None:
					self["page_sel"+str(x)].instance.setPixmap(pic)
					if x == 1:
						self["page_sel"+str(x)].show()

			for x in range(1,self.counting_pages+1):
				poster_path = "%s/page.png" % (self.images_path)
				self["page_empty"+str(x)].instance.setPixmap(gPixmapPtr())
				self["page_empty"+str(x)].hide()
				pic = LoadPixmap(cached=True, path=poster_path)
				if pic != None:
					self["page_empty"+str(x)].instance.setPixmap(pic)
					if x > 1:
						self["page_empty"+str(x)].show()

		self.widget_list()

	def widget_list(self):
		count = 1
		counting = 1
		self.mainlist = []
		list_dummy = []
		self.plugin_counting = len(self.plugin_liste)

		for x in range(1,int(self.plugin_counting)+1):
			if count == 40:
				count += 1
				counting += 1
				list_dummy.append(x)
				self.mainlist.append(list_dummy)
				count = 1
				list_dummy = []
			else:
				count += 1
				counting += 1
				list_dummy.append(x)
				if int(counting) == int(self.plugin_counting)+1:
					self.mainlist.append(list_dummy)

		if config.mediaportal.pagestyle.value == "Graphic":
			pageinfo = ""
		else:
			pageinfo = _("Page") + " %s / %s" % (self.select_list+1, len(self.mainlist))
		self['page'].setText(pageinfo)
		select_nr = self.mainlist[int(self.select_list)][int(self.selektor_index)-1]
		plugin_name = self.plugin_liste[int(select_nr)-1][0]
		self['name'].setText(plugin_name)
		self.hideshow2()

	def move_selector(self):
		select_nr = self.mainlist[int(self.select_list)][int(self.selektor_index)-1]
		plugin_name = self.plugin_liste[int(select_nr)-1][0]
		self['name'].setText(plugin_name)
		if not self.wallzoom:
			position = self["zeile"+str(self.selektor_index)].instance.position()
			self["frame"].moveTo(position.x(), position.y(), 1)
			self["frame"].show()
			self["frame"].startMoving()

	def keyOK(self):
		if not testWebConnection():
			self.session.open(MessageBoxExt, _('No connection to the Internet available.'), MessageBoxExt.TYPE_INFO, timeout=3)
			return

		if self.check_empty_list():
			return

		select_nr = self.mainlist[int(self.select_list)][int(self.selektor_index)-1]
		auswahl = self.plugin_liste[int(select_nr)-1][0]
		icon = self.plugin_liste[int(select_nr)-1][1]
		mp_globals.activeIcon = icon
		print "Plugin:", auswahl

		self.pornscreen = None
		self.par1 = ""
		self.par2 = ""
		self.hit_plugin(auswahl)

		conf = xml.etree.cElementTree.parse(CONFIG)
		for x in conf.getroot():
			if x.tag == "set" and x.get("name") == 'additions':
				root =  x
				for x in root:
					if x.tag == "plugin":
						if x.get("type") == "mod":
							confcat = x.get("confcat")
							if auswahl ==  x.get("name").replace("&amp;","&"):
								status = [item for item in mp_globals.status if item[0] == x.get("modfile")]
								if status:
									if int(config.mediaportal.version.value) < int(status[0][1]):
										if status[0][1] == "9999":
											self.session.open(MessageBoxExt, _("This Plugin has been marked as \"not working\" by the developers.\n\nCurrent developer status of this Plugin is:\n\"%s\"\n\nIf someone else is willing to provide a fix for this Plugin then please get in contact with us.") % status[0][2], MessageBoxExt.TYPE_INFO)
										else:
											self.session.open(MessageBoxExt, _("This Plugin has been marked as \"not working\" by the developers.\n\nCurrent developer status of this Plugin is:\n\"%s\"") % status[0][2], MessageBoxExt.TYPE_INFO)
										if not config.mediaportal.debugMode.value == "High":
											return
								param = ""
								param1 = x.get("param1")
								param2 = x.get("param2")
								kids = x.get("kids")
								if param1 != "":
									param = ", \"" + param1 + "\""
									exec("self.par1 = \"" + x.get("param1") + "\"")
								if param2 != "":
									param = param + ", \"" + param2 + "\""
									exec("self.par2 = \"" + x.get("param2") + "\"")
								if confcat == "porn":
									exec("self.pornscreen = " + x.get("screen") + "")
								elif kids != "1" and config.mediaportal.kidspin.value:
									exec("self.pornscreen = " + x.get("screen") + "")
								else:
									exec("self.session.open(" + x.get("screen") + param + ")")

		xmlpath = resolveFilename(SCOPE_PLUGINS, "Extensions/MediaPortal/additions/")
		for file in os.listdir(xmlpath):
			if file.endswith(".xml") and file != "additions.xml":
				useraddition = xmlpath + file

				conf = xml.etree.cElementTree.parse(useraddition)
				for x in conf.getroot():
					if x.tag == "set" and x.get("name") == 'additions_user':
						root =  x
						for x in root:
							if x.tag == "plugin":
								if x.get("type") == "mod":
									confcat = x.get("confcat")
									if auswahl ==  x.get("name").replace("&amp;","&"):
										status = [item for item in mp_globals.status if item[0] == x.get("modfile")]
										if status:
											if int(config.mediaportal.version.value) < int(status[0][1]):
												if status[0][1] == "9999":
													self.session.open(MessageBoxExt, _("This Plugin has been marked as \"not working\" by the developers.\n\nCurrent developer status of this Plugin is:\n\"%s\"\n\nIf someone else is willing to provide a fix for this Plugin then please get in contact with us.") % status[0][2], MessageBoxExt.TYPE_INFO)
												else:
													self.session.open(MessageBoxExt, _("This Plugin has been marked as \"not working\" by the developers.\n\nCurrent developer status of this Plugin is:\n\"%s\"") % status[0][2], MessageBoxExt.TYPE_INFO)
												if not config.mediaportal.debugMode.value == "High":
													return
										param = ""
										param1 = x.get("param1")
										param2 = x.get("param2")
										kids = x.get("kids")
										if param1 != "":
											param = ", \"" + param1 + "\""
											exec("self.par1 = \"" + x.get("param1") + "\"")
										if param2 != "":
											param = param + ", \"" + param2 + "\""
											exec("self.par2 = \"" + x.get("param2") + "\"")
										if confcat == "porn":
											exec("self.pornscreen = " + x.get("screen") + "")
										elif kids != "1" and config.mediaportal.kidspin.value:
											exec("self.pornscreen = " + x.get("screen") + "")
										else:
											exec("self.session.open(" + x.get("screen") + param + ")")

		if self.pornscreen:
			if config.mediaportal.pornpin.value:
				if pincheck.pin_entered == False:
					self.session.openWithCallback(self.pincheckok, PinInputExt, pinList = [(config.mediaportal.adultpincode.value)], triesEntry = config.mediaportal.retries.adultpin, title = _("Please enter the correct PIN"), windowTitle = _("Enter adult PIN"))
				else:
					if self.par1 == "":
						self.session.open(self.pornscreen)
					elif self.par2 == "":
						self.session.open(self.pornscreen, self.par1)
					else:
						self.session.open(self.pornscreen, self.par1, self.par2)
			else:
				if self.par1 == "":
					self.session.open(self.pornscreen)
				elif self.par2 == "":
					self.session.open(self.pornscreen, self.par1)
				else:
					self.session.open(self.pornscreen, self.par1, self.par2)

	def pincheckok(self, pincode):
		if pincode:
			pincheck.pinEntered()
			if self.par1 == "":
				self.session.open(self.pornscreen)
			elif self.par2 == "":
				self.session.open(self.pornscreen, self.par1)
			else:
				self.session.open(self.pornscreen, self.par1, self.par2)

	def hideshow(self):
		if self.wallbw or self.wallzoom:
			test = self.mainlist[int(self.select_list)][int(self.selektor_index)-1]
			self["zeile_bw"+str(test)].hide()
			self["zeile"+str(test)].show()

	def hideshow2(self):
		if self.wallbw or self.wallzoom:
			test = self.mainlist[int(self.select_list)][int(self.selektor_index)-1]
			self["zeile_bw"+str(test)].show()
			self["zeile"+str(test)].hide()

	def keyLeft(self):
		if self.check_empty_list():
			return
		if self.selektor_index > 1:
			self.hideshow()
			self.selektor_index -= 1
			self.move_selector()
			self.hideshow2()
		else:
			self.page_back()

	def keyRight(self):
		if self.check_empty_list():
			return
		if self.selektor_index < 40 and self.selektor_index != len(self.mainlist[int(self.select_list)]):
			self.hideshow()
			self.selektor_index += 1
			self.move_selector()
			self.hideshow2()
		else:
			self.page_next()

	def keyUp(self):
		if self.check_empty_list():
			return
		if self.selektor_index-8 > 1:
			self.hideshow()
			self.selektor_index -=8
			self.move_selector()
			self.hideshow2()
		else:
			self.hideshow()
			self.selektor_index = 1
			self.move_selector()
			self.hideshow2()

	def keyDown(self):
		if self.check_empty_list():
			return
		if self.selektor_index+8 <= len(self.mainlist[int(self.select_list)]):
			self.hideshow()
			self.selektor_index +=8
			self.move_selector()
			self.hideshow2()
		else:
			self.hideshow()
			self.selektor_index = len(self.mainlist[int(self.select_list)])
			self.move_selector()
			self.hideshow2()

	def page_next(self):
		if self.check_empty_list():
			return
		if self.select_list < len(self.mainlist)-1:
			self.hideshow()
			self.paint_hide()
			self.select_list += 1
			self.paint_new()

	def page_back(self):
		if self.check_empty_list():
			return
		if self.select_list > 0:
			self.hideshow()
			self.paint_hide()
			self.select_list -= 1
			self.paint_new_last()

	def check_empty_list(self):
		if len(self.plugin_liste) == 0:
			self['name'].setText('Keine Plugins der Kategorie %s aktiviert!' % config.mediaportal.filter.value)
			self["frame"].hide()
			return True
		else:
			return False

	def paint_hide(self):
		for x in self.mainlist[int(self.select_list)]:
			self["zeile"+str(x)].hide()

	def paint_new_last(self):
		if config.mediaportal.pagestyle.value == "Graphic":
			pageinfo = ""
		else:
			pageinfo = _("Page") + " %s / %s" % (self.select_list+1, len(self.mainlist))
		self['page'].setText(pageinfo)
		self.selektor_index = len(self.mainlist[int(self.select_list)])
		self.move_selector()
		# Apple Page Style
		if config.mediaportal.pagestyle.value == "Graphic" and len(self.plugin_liste_page_tmp) != 0:
			self.refresh_apple_page_bar()

		for x in self.mainlist[int(self.select_list)]:
			self["zeile"+str(x)].show()

		self.hideshow2()

	def paint_new(self):
		if config.mediaportal.pagestyle.value == "Graphic":
			pageinfo = ""
		else:
			pageinfo = _("Page") + " %s / %s" % (self.select_list+1, len(self.mainlist))
		self['page'].setText(pageinfo)
		self.selektor_index = 1
		self.move_selector()
		# Apple Page Style
		if config.mediaportal.pagestyle.value == "Graphic" and len(self.plugin_liste_page_tmp) != 0:
			self.refresh_apple_page_bar()

		for x in self.mainlist[int(self.select_list)]:
			self["zeile"+str(x)].show()

		self.hideshow2()

	# Apple Page Style
	def refresh_apple_page_bar(self):
		for x in range(1,len(self.mainlist)+1):
			if x == self.select_list+1:
				self["page_empty"+str(x)].hide()
				self["page_sel"+str(x)].show()
			else:
				self["page_sel"+str(x)].hide()
				self["page_empty"+str(x)].show()

	def keySetup(self):
		if config.mediaportal.setuppin.value:
			self.session.openWithCallback(self.pinok, PinInputExt, pinList = [(config.mediaportal.pincode.value)], triesEntry = config.mediaportal.retries.pincode, title = _("Please enter the correct PIN"), windowTitle = _("Enter setup PIN"))
		else:
			self.session.openWithCallback(self.restart, MPSetup)

	def keySimpleList(self):
		mp_globals.activeIcon = "simplelist"
		self.session.open(simplelistGenreScreen)

	def pinok(self, pincode):
		if pincode:
			self.session.openWithCallback(self.restart, MPSetup)

	def chSort(self):
		print "Sort: %s" % config.mediaportal.sortplugins.value

		if config.mediaportal.sortplugins.value == "hits":
			config.mediaportal.sortplugins.value = "abc"
		elif config.mediaportal.sortplugins.value == "abc":
			config.mediaportal.sortplugins.value = "user"
		elif config.mediaportal.sortplugins.value == "user":
			config.mediaportal.sortplugins.value = "hits"

		print "Sort changed:", config.mediaportal.sortplugins.value
		self.restart()

	def changeFilter(self):
		self.startChoose()

	def chFilter(self):
		print "Filter:", config.mediaportal.filter.value

		if config.mediaportal.filter.value == "ALL":
			config.mediaportal.filter.value = "Mediathek"
		elif config.mediaportal.filter.value == "Mediathek":
			config.mediaportal.filter.value = "User-additions"
		elif config.mediaportal.filter.value == "User-additions":
			config.mediaportal.filter.value = "Sport"
		elif config.mediaportal.filter.value == "Sport":
			config.mediaportal.filter.value = "Music"
		elif config.mediaportal.filter.value == "Music":
			config.mediaportal.filter.value = "Fun"
		elif config.mediaportal.filter.value == "Fun":
			config.mediaportal.filter.value = "NewsDoku"
		elif config.mediaportal.filter.value == "NewsDoku":
			config.mediaportal.filter.value = "Porn"
		elif config.mediaportal.filter.value == "Porn":
			config.mediaportal.filter.value = "ALL"

		print "Filter changed:", config.mediaportal.filter.value
		self.restartAndCheck()

	def restartAndCheck(self):
		if config.mediaportal.filter.value != "ALL":
			dump_liste2 = self.dump_liste
			self.plugin_liste = []
			self.plugin_liste = [x for x in dump_liste2 if re.search(config.mediaportal.filter.value, x[2])]
			if len(self.plugin_liste) == 0:
				print "Filter ist deaktviert.. recheck..: %s" % config.mediaportal.filter.value
				self.chFilter()
			else:
				print "Mediaportal restart."
				config.mediaportal.filter.save()
				configfile.save()
				self.close(self.session, False, self.lastservice)
		else:
			print "Mediaportal restart."
			config.mediaportal.filter.save()
			configfile.save()
			self.close(self.session, False, self.lastservice)

	def showPorn(self):
		if config.mediaportal.showporn.value:
			config.mediaportal.showporn.value = False
			if config.mediaportal.filter.value == "Porn":
				self.chFilter()
			config.mediaportal.showporn.save()
			config.mediaportal.filter.save()
			configfile.save()
			self.restart()
		else:
			self.session.openWithCallback(self.showPornOK, PinInputExt, pinList = [(config.mediaportal.adultpincode.value)], triesEntry = config.mediaportal.retries.adultpin, title = _("Please enter the correct PIN"), windowTitle = _("Enter adult PIN"))

	def showPornOK(self, pincode):
		if pincode:
			pincheck.pinEntered()
			config.mediaportal.showporn.value = True
			config.mediaportal.showporn.save()
			configfile.save()
			self.restart()

	def keyCancel(self):
		config.mediaportal.filter.save()
		configfile.save()
		self.close(self.session, True, self.lastservice)

	def restart(self):
		config.mediaportal.filter.save()
		config.mediaportal.sortplugins.save()
		configfile.save()
		if autoStartTimer is not None:
			autoStartTimer.update()
		self.close(self.session, False, self.lastservice)

	def startChoose(self):
		if mp_globals.isDreamOS:
			self.session.openWithCallback(self.gotFilter, MPchooseFilter, self.dump_liste, config.mediaportal.filter.value, is_dialog=True)
		else:
			self.session.openWithCallback(self.gotFilter, MPchooseFilter, self.dump_liste, config.mediaportal.filter.value)

	def gotFilter(self, filter):
		if not config.mediaportal.showporn.value and filter == "Porn":
			return
		elif not config.mediaportal.showuseradditions.value and filter == "User-additions":
			return
		elif filter != True:
			config.mediaportal.filter.value = filter
			self.restartAndCheck()

class MPWall2(Screen, HelpableScreen):

	def __init__(self, session, lastservice, filter):
		self.lastservice = mp_globals.lastservice = lastservice
		self.wallbw = False
		self.plugin_liste = []
		self.skin_path = mp_globals.pluginPath + mp_globals.skinsPath

		self.images_path = "%s/%s/images" % (self.skin_path, config.mediaportal.skin.value)
		if not fileExists(self.images_path):
			self.images_path = self.skin_path + mp_globals.skinFallback + "/images"

		conf = xml.etree.cElementTree.parse(CONFIG)
		for x in conf.getroot():
			if x.tag == "set" and x.get("name") == 'additions':
				root =  x
				for x in root:
					if x.tag == "plugin":
						if x.get("type") == "mod":
							modfile = x.get("modfile")
							confcat = x.get("confcat")
							if not config.mediaportal.showporn.value and confcat == "porn":
								pass
							else:
								gz = x.get("gz")
								if not config.mediaportal.showuseradditions.value and gz == "1":
									pass
								else:
									mod = eval("config.mediaportal." + x.get("confopt") + ".value")
									if mod:
										y = eval("self.plugin_liste.append((\"" + x.get("name").replace("&amp;","&") + "\", \"" + x.get("icon") + "\", \"" + x.get("filter") + "\"))")

		xmlpath = resolveFilename(SCOPE_PLUGINS, "Extensions/MediaPortal/additions/")
		for file in os.listdir(xmlpath):
			if file.endswith(".xml") and file != "additions.xml":
				useraddition = xmlpath + file

				conf = xml.etree.cElementTree.parse(useraddition)
				for x in conf.getroot():
					if x.tag == "set" and x.get("name") == 'additions_user':
						root =  x
						for x in root:
							if x.tag == "plugin":
								if x.get("type") == "mod":
									modfile = x.get("modfile")
									confcat = x.get("confcat")
									if not config.mediaportal.showporn.value and confcat == "porn":
										pass
									else:
										gz = x.get("gz")
										if not config.mediaportal.showuseradditions.value and gz == "1":
											pass
										else:
											mod = eval("config.mediaportal." + x.get("confopt") + ".value")
											if mod:
												y = eval("self.plugin_liste.append((\"" + x.get("name").replace("&amp;","&") + "\", \"" + x.get("icon") + "\", \"" + x.get("filter") + "\"))")

		if len(self.plugin_liste) == 0:
			self.plugin_liste.append(("","","Mediathek"))

		# Porn
		if (config.mediaportal.showporn.value == False and config.mediaportal.filter.value == 'Porn'):
			config.mediaportal.filter.value = 'ALL'

		# User-additions
		if (config.mediaportal.showuseradditions.value == False and config.mediaportal.filter.value == 'User-additions'):
			config.mediaportal.filter.value = 'ALL'

		# Plugin Sortierung
		if config.mediaportal.sortplugins != "default":

			# Erstelle Pluginliste falls keine vorhanden ist.
			self.sort_plugins_file = "/etc/enigma2/mp_pluginliste"
			if not fileExists(self.sort_plugins_file):
				print "Erstelle Wall-Pluginliste."
				open(self.sort_plugins_file,"w").close()

			pluginliste_leer = os.path.getsize(self.sort_plugins_file)
			if pluginliste_leer == 0:
				print "1st time - Schreibe Wall-Pluginliste."
				first_count = 0
				read_pluginliste = open(self.sort_plugins_file,"a")
				for name,picname,genre in self.plugin_liste:
					read_pluginliste.write('"%s" "%s" "%s" "%s" "%s"\n' % (name, picname, genre, "0", str(first_count)))
					first_count += 1
				read_pluginliste.close()
				print "Wall-Pluginliste wurde erstellt."

			# Lese Pluginliste ein.
			if fileExists(self.sort_plugins_file):

				count_sort_plugins_file = len(open(self.sort_plugins_file).readlines())
				count_plugin_liste = len(self.plugin_liste)

				if int(count_plugin_liste) != int(count_sort_plugins_file):
					print "Ein Plugin wurde aktiviert oder deaktiviert.. erstelle neue pluginliste."

					read_pluginliste_tmp = open(self.sort_plugins_file+".tmp","w")
					read_pluginliste = open(self.sort_plugins_file,"r")
					p_dupeliste = []

					for rawData in read_pluginliste.readlines():
						data = re.findall('"(.*?)" "(.*?)" "(.*?)" "(.*?)" "(.*?)"', rawData, re.S)

						if data:
							(p_name, p_picname, p_genre, p_hits, p_sort) = data[0]
							pop_count = 0
							for pname, ppic, pgenre in self.plugin_liste:
								if p_name not in p_dupeliste:
									if p_name == pname:
										read_pluginliste_tmp.write('"%s" "%s" "%s" "%s" "%s"\n' % (p_name, p_picname, pgenre, p_hits, p_sort))
										p_dupeliste.append((p_name))
										self.plugin_liste.pop(int(pop_count))

									pop_count += 1

					if len(self.plugin_liste) != 0:
						for pname, ppic, pgenre in self.plugin_liste:
							read_pluginliste_tmp.write('"%s" "%s" "%s" "%s" "%s"\n' % (pname, ppic, pgenre, "0", "99"))

					read_pluginliste.close()
					read_pluginliste_tmp.close()
					shutil.move(self.sort_plugins_file+".tmp", self.sort_plugins_file)

				self.new_pluginliste = []
				read_pluginliste = open(self.sort_plugins_file,"r")
				for rawData in read_pluginliste.readlines():
					data = re.findall('"(.*?)" "(.*?)" "(.*?)" "(.*?)" "(.*?)"', rawData, re.S)
					if data:
						(p_name, p_picname, p_genre, p_hits, p_sort) = data[0]
						self.new_pluginliste.append((p_name, p_picname, p_genre, p_hits, p_sort))
				read_pluginliste.close()

			# Sortieren nach hits
			if config.mediaportal.sortplugins.value == "hits":
				self.new_pluginliste.sort(key=lambda x: int(x[3]))
				self.new_pluginliste.reverse()

			# Sortieren nach abcde..
			elif config.mediaportal.sortplugins.value == "abc":
				self.new_pluginliste.sort(key=lambda x: str(x[0]).lower())

			elif config.mediaportal.sortplugins.value == "user":
				self.new_pluginliste.sort(key=lambda x: int(x[4]))

			self.plugin_liste = self.new_pluginliste

		if config.mediaportal.wall2mode.value == "bw":
			self.wallbw = True

		if mp_globals.videomode == 2:
			self.perpage = 48
			pageiconwidth = 36
			pageicondist = 8
			screenwidth = 1920
			screenheight = 1080
		else:
			self.perpage = 40
			pageiconwidth = 26
			pageicondist = 4
			screenwidth = 1280
			screenheight = 720

		path = "%s/%s/MP_Wall2.xml" % (self.skin_path, config.mediaportal.skin.value)
		if not fileExists(path):
			path = self.skin_path + mp_globals.skinFallback + "/MP_Wall2.xml"
		with open(path, "r") as f:
			self.skin = f.read()
			f.close()

		# Page Style
		if config.mediaportal.pagestyle.value == "Graphic":
			skincontent = ""
			self.skin = self.skin.replace('</screen>', '')
			self.dump_liste_page_tmp = self.plugin_liste
			if config.mediaportal.filter.value != "ALL":
				self.plugin_liste_page_tmp = []
				self.plugin_liste_page_tmp = [x for x in self.dump_liste_page_tmp if re.search(config.mediaportal.filter.value, x[2])]
			else:
				self.plugin_liste_page_tmp = self.plugin_liste

			if len(self.plugin_liste_page_tmp) != 0:
				self.counting_pages = int(round(float((len(self.plugin_liste_page_tmp)-1) / self.perpage) + 0.5))
				pagebar_size = self.counting_pages * pageiconwidth + (self.counting_pages-1) * pageicondist
				start_pagebar = int(screenwidth / 2 - pagebar_size / 2)

				for x in range(1,self.counting_pages+1):
					normal = screenheight - 2 * pageiconwidth
					if config.mediaportal.skin.value == "original":
						normal = normal - 20
					if mp_globals.videomode == 2:
						normal = normal - 30
					skincontent += "<widget name=\"page_empty" + str(x) + "\" position=\"" + str(start_pagebar) + "," + str(normal) + "\" size=\"" + str(pageiconwidth) + "," + str(pageiconwidth) + "\" zPosition=\"2\" transparent=\"1\" alphatest=\"blend\" />"
					skincontent += "<widget name=\"page_sel" + str(x) + "\" position=\"" + str(start_pagebar) + "," + str(normal) + "\" size=\"" + str(pageiconwidth) + "," + str(pageiconwidth) + "\" zPosition=\"2\" transparent=\"1\" alphatest=\"blend\" />"
					start_pagebar += pageiconwidth + pageicondist

			self.skin += skincontent
			self.skin += "</screen>"

		self["hidePig"] = Boolean()
		self["hidePig"].setBoolean(config.mediaportal.minitv.value)

		Screen.__init__(self, session)

		addFont(resolveFilename(SCOPE_PLUGINS, "Extensions/MediaPortal/resources/") + "mediaportal1.ttf", "mediaportal", 100, False)

		if config.mediaportal.backgroundtv.value:
			config.mediaportal.minitv.value = True
			config.mediaportal.minitv.save()
			config.mediaportal.restorelastservice.value = "2"
			config.mediaportal.restorelastservice.save()
			configfile.save()
			session.nav.stopService()

		self["actions"] = ActionMap(["MP_Actions"], {
			"up"    : self.keyUp,
			"down"  : self.keyDown,
			"left"  : self.keyLeft,
			"right" : self.keyRight,
			"info"  : self.showPorn,
			"0": boundFunction(self.gotFilter, "ALL"),
			"1": boundFunction(self.gotFilter, "Mediathek"),
			"2": boundFunction(self.gotFilter, "Fun"),
			"3": boundFunction(self.gotFilter, "Music"),
			"4": boundFunction(self.gotFilter, "Sport"),
			"5": boundFunction(self.gotFilter, "NewsDoku"),
			"6": boundFunction(self.gotFilter, "Porn"),
			"7": boundFunction(self.gotFilter, "User-additions")
		}, -1)
		self["MP_Actions"] = HelpableActionMap(self, "MP_Actions", {
			"blue"  : (self.changeFilter, _("Change filter")),
			"green" : (self.chSort, _("Change sort order")),
			"yellow": (self.manuelleSortierung, _("Manual sorting")),
			"red"   : (self.keySimpleList, _("Open SimpleList")),
			"ok"    : (self.keyOK, _("Open selected Plugin")),
			"cancel": (self.keyCancel, _("Exit MediaPortal")),
			"nextBouquet" :	(self.page_next, _("Next page")),
			"prevBouquet" :	(self.page_back, _("Previous page")),
			"menu" : (self.keySetup, _("MediaPortal Setup")),
			config.mediaportal.simplelist_key.value: (self.keySimpleList, _("Open SimpleList"))
		}, -1)

		self['name'] = Label("")
		self['version'] = Label(config.mediaportal.version.value[0:8])
		self['red'] = Label("SimpleList")
		self['green'] = Label("")
		self['yellow'] = Label(_("Sort"))
		self['blue'] = Label("")
		self['CH+'] = Label(_("CH+"))
		self['CH-'] = Label(_("CH-"))
		self['PVR'] = Label(_("PVR"))
		self['Exit'] = Label(_("Exit"))
		self['Help'] = Label(_("Help"))
		self['Menu'] = Label(_("Menu"))
		self['page'] = Label("")
		self["covercollection"] = CoverCollection()

		# Apple Page Style
		if config.mediaportal.pagestyle.value == "Graphic" and len(self.plugin_liste_page_tmp) != 0:
			for x in range(1,self.counting_pages+1):
				self["page_empty"+str(x)] = Pixmap()
				self["page_empty"+str(x)].show()
				self["page_sel"+str(x)] = Pixmap()
				self["page_sel"+str(x)].show()

		HelpableScreen.__init__(self)
		self.onFirstExecBegin.append(self._onFirstExecBegin)
		self.onFirstExecBegin.append(self.checkPathes)
		self.onFirstExecBegin.append(self.status)

	def checkPathes(self):
		CheckPathes(self.session).checkPathes(self.cb_checkPathes)

	def cb_checkPathes(self):
		self.session.openWithCallback(self.restart, MPSetup)

	def status(self):
		update_agent = getUserAgent()
		update_url = getUpdateUrl()
		twAgentGetPage(update_url, agent=update_agent, timeout=30).addCallback(self.checkstatus)

	def checkstatus(self, html):
		if re.search(".*?<html", html):
			return
		self.html = html
		tmp_infolines = html.splitlines()
		statusurl = tmp_infolines[4]
		update_agent = getUserAgent()
		twAgentGetPage(statusurl, agent=update_agent, timeout=30).addCallback(_status)

	def manuelleSortierung(self):
		if config.mediaportal.filter.value == 'ALL':
			self.session.openWithCallback(self.restart, MPpluginSort)
		else:
			self.session.open(MessageBoxExt, _('Ordering is only possible with filter "ALL".'), MessageBoxExt.TYPE_INFO, timeout=3)

	def hit_plugin(self, pname):
		if fileExists(self.sort_plugins_file):
			read_pluginliste = open(self.sort_plugins_file,"r")
			read_pluginliste_tmp = open(self.sort_plugins_file+".tmp","w")
			for rawData in read_pluginliste.readlines():
				data = re.findall('"(.*?)" "(.*?)" "(.*?)" "(.*?)" "(.*?)"', rawData, re.S)
				if data:
					(p_name, p_picname, p_genre, p_hits, p_sort) = data[0]
					if pname == p_name:
						new_hits = int(p_hits)+1
						read_pluginliste_tmp.write('"%s" "%s" "%s" "%s" "%s"\n' % (p_name, p_picname, p_genre, str(new_hits), p_sort))
					else:
						read_pluginliste_tmp.write('"%s" "%s" "%s" "%s" "%s"\n' % (p_name, p_picname, p_genre, p_hits, p_sort))
			read_pluginliste.close()
			read_pluginliste_tmp.close()
			shutil.move(self.sort_plugins_file+".tmp", self.sort_plugins_file)

	def _onFirstExecBegin(self):
		_hosters()
		if not mp_globals.start:
			self.close(self.session, True, self.lastservice)
		if config.mediaportal.autoupdate.value:
			checkupdate(self.session).checkforupdate()

		# load plugin icons
		print "Set Filter:", config.mediaportal.filter.value
		if config.mediaportal.filter.value == "ALL":
			name = _("ALL")
		elif config.mediaportal.filter.value == "Mediathek":
			name = _("Libraries")
		elif config.mediaportal.filter.value == "User-additions":
			name = _("User-additions")
		elif config.mediaportal.filter.value == "Fun":
			name = _("Fun")
		elif config.mediaportal.filter.value == "NewsDoku":
			name = _("News&Documentary")
		elif config.mediaportal.filter.value == "Music":
			name = _("Music")
		elif config.mediaportal.filter.value == "Sport":
			name = _("Sports")
		elif config.mediaportal.filter.value == "Porn":
			name = _("Porn")
		self['blue'].setText(name)
		self.sortplugin = config.mediaportal.sortplugins.value
		if self.sortplugin == "hits":
			self.sortplugin = "Hits"
		elif self.sortplugin == "abc":
			self.sortplugin = "ABC"
		elif self.sortplugin == "user":
			self.sortplugin = "User"
		self['green'].setText(self.sortplugin)
		self.dump_liste = self.plugin_liste
		if config.mediaportal.filter.value != "ALL":
			self.plugin_liste = []
			self.plugin_liste = [x for x in self.dump_liste if re.search(config.mediaportal.filter.value, x[2])]
		if len(self.plugin_liste) == 0:
			self.chFilter()
			if config.mediaportal.filter.value == "ALL":
				name = _("ALL")
			elif config.mediaportal.filter.value == "Mediathek":
				name = _("Libraries")
			elif config.mediaportal.filter.value == "User-additions":
				name = _("User-additions")
			elif config.mediaportal.filter.value == "Fun":
				name = _("Fun")
			elif config.mediaportal.filter.value == "NewsDoku":
				name = _("News&Documentary")
			elif config.mediaportal.filter.value == "Music":
				name = _("Music")
			elif config.mediaportal.filter.value == "Sport":
				name = _("Sports")
			elif config.mediaportal.filter.value == "Porn":
				name = _("Porn")
			self['blue'].setText(name)

		if config.mediaportal.sortplugins.value == "hits":
			self.plugin_liste.sort(key=lambda x: int(x[3]))
			self.plugin_liste.reverse()

		# Sortieren nach abcde..
		elif config.mediaportal.sortplugins.value == "abc":
			self.plugin_liste.sort(key=lambda t : t[0].lower())

		elif config.mediaportal.sortplugins.value == "user":
			self.plugin_liste.sort(key=lambda x: int(x[4]))

		itemList = []
		posterlist = []
		icon_url = getIconUrl()
		if self.wallbw:
			icons_hashes = grabpage(icon_url+"icons_bw/hashes")
		else:
			icons_hashes = grabpage(icon_url+"icons/hashes")
		if icons_hashes:
			icons_data = re.findall('(.*?)\s\*(.*?\.png)', icons_hashes)
		else:
			icons_data = None

		logo_hashes = grabpage(icon_url+"logos/hashes")
		if logo_hashes:
			logo_data = re.findall('(.*?)\s\*(.*?\.png)', logo_hashes)
		else:
			logo_data = None

		for p_name, p_picname, p_genre, p_hits, p_sort in self.plugin_liste:
			remote_hash = ""
			ds = defer.DeferredSemaphore(tokens=5)
			row = []
			itemList.append(((row),))
			if self.wallbw:
				poster_path = "%s/%s.png" % (config.mediaportal.iconcachepath.value + "icons_bw", p_picname)
				url = icon_url+"icons_bw/" + p_picname + ".png"
				if not fileExists(poster_path):
					if icons_data:
						for x,y in icons_data:
							if y == p_picname+'.png':
								ds.run(downloadPage, url, poster_path)
					poster_path = "%s/images/comingsoon.png" % mp_globals.pluginPath
				else:
					local_hash = hashlib.md5(open(poster_path, 'rb').read()).hexdigest()
					if icons_data:
						for x,y in icons_data:
							if y == p_picname+'.png': remote_hash = x
						if remote_hash != local_hash:
							ds.run(downloadPage, url, poster_path)
							poster_path = "%s/images/comingsoon.png" % mp_globals.pluginPath
			else:
				poster_path = "%s/%s.png" % (config.mediaportal.iconcachepath.value + "icons", p_picname)
				url = icon_url+"icons/" + p_picname + ".png"
				if not fileExists(poster_path):
					if icons_data:
						for x,y in icons_data:
							if y == p_picname+'.png':
								ds.run(downloadPage, url, poster_path)
					poster_path = "%s/images/comingsoon.png" % mp_globals.pluginPath
				else:
					local_hash = hashlib.md5(open(poster_path, 'rb').read()).hexdigest()
					if icons_data:
						for x,y in icons_data:
							if y == p_picname+'.png': remote_hash = x
						if remote_hash != local_hash:
							ds.run(downloadPage, url, poster_path)
							poster_path = "%s/images/comingsoon.png" % mp_globals.pluginPath

			logo_path = "%s/%s.png" % (config.mediaportal.iconcachepath.value + "logos", p_picname)
			url = icon_url+"logos/" + p_picname + ".png"
			if not fileExists(logo_path):
				if logo_data:
					for x,y in logo_data:
						if y == p_picname+'.png':
							ds.run(downloadPage, url, logo_path)
			else:
				local_hash = hashlib.md5(open(logo_path, 'rb').read()).hexdigest()
				if logo_data:
					for x,y in logo_data:
						if y == p_picname+'.png': remote_hash = x
					if remote_hash != local_hash:
						ds.run(downloadPage, url, logo_path)

			row.append((p_name, p_picname, poster_path, p_genre, p_hits, p_sort))
			posterlist.append(poster_path)
		self["covercollection"].setList(itemList,posterlist)

		if config.mediaportal.pagestyle.value == "Graphic" and len(self.plugin_liste_page_tmp) != 0:
			for x in range(1,self.counting_pages+1):
				poster_path = "%s/page_select.png" % (self.images_path)
				self["page_sel"+str(x)].instance.setPixmap(gPixmapPtr())
				self["page_sel"+str(x)].hide()
				pic = LoadPixmap(cached=True, path=poster_path)
				if pic != None:
					self["page_sel"+str(x)].instance.setPixmap(pic)
					if x == 1:
						self["page_sel"+str(x)].show()

			for x in range(1,self.counting_pages+1):
				poster_path = "%s/page.png" % (self.images_path)
				self["page_empty"+str(x)].instance.setPixmap(gPixmapPtr())
				self["page_empty"+str(x)].hide()
				pic = LoadPixmap(cached=True, path=poster_path)
				if pic != None:
					self["page_empty"+str(x)].instance.setPixmap(pic)
					if x > 1:
						self["page_empty"+str(x)].show()
		self.setInfo()

	def keyOK(self):
		if not testWebConnection():
			self.session.open(MessageBoxExt, _('No connection to the Internet available.'), MessageBoxExt.TYPE_INFO, timeout=3)
			return

		if self["covercollection"].getCurrentIndex() >=0:
			item = self["covercollection"].getCurrent()
			(p_name, p_picname, p_picpath, p_genre, p_hits, p_sort) = item[0]

		mp_globals.activeIcon = p_picname
		print "Plugin:", p_name

		self.pornscreen = None
		self.par1 = ""
		self.par2 = ""
		self.hit_plugin(p_name)

		conf = xml.etree.cElementTree.parse(CONFIG)
		for x in conf.getroot():
			if x.tag == "set" and x.get("name") == 'additions':
				root =  x
				for x in root:
					if x.tag == "plugin":
						if x.get("type") == "mod":
							confcat = x.get("confcat")
							if p_name ==  x.get("name").replace("&amp;","&"):
								status = [item for item in mp_globals.status if item[0] == x.get("modfile")]
								if status:
									if int(config.mediaportal.version.value) < int(status[0][1]):
										if status[0][1] == "9999":
											self.session.open(MessageBoxExt, _("This Plugin has been marked as \"not working\" by the developers.\n\nCurrent developer status of this Plugin is:\n\"%s\"\n\nIf someone else is willing to provide a fix for this Plugin then please get in contact with us.") % status[0][2], MessageBoxExt.TYPE_INFO)
										else:
											self.session.open(MessageBoxExt, _("This Plugin has been marked as \"not working\" by the developers.\n\nCurrent developer status of this Plugin is:\n\"%s\"") % status[0][2], MessageBoxExt.TYPE_INFO)
										if not config.mediaportal.debugMode.value == "High":
											return
								param = ""
								param1 = x.get("param1")
								param2 = x.get("param2")
								kids = x.get("kids")
								if param1 != "":
									param = ", \"" + param1 + "\""
									exec("self.par1 = \"" + x.get("param1") + "\"")
								if param2 != "":
									param = param + ", \"" + param2 + "\""
									exec("self.par2 = \"" + x.get("param2") + "\"")
								if confcat == "porn":
									exec("self.pornscreen = " + x.get("screen") + "")
								elif kids != "1" and config.mediaportal.kidspin.value:
									exec("self.pornscreen = " + x.get("screen") + "")
								else:
									exec("self.session.open(" + x.get("screen") + param + ")")

		xmlpath = resolveFilename(SCOPE_PLUGINS, "Extensions/MediaPortal/additions/")
		for file in os.listdir(xmlpath):
			if file.endswith(".xml") and file != "additions.xml":
				useraddition = xmlpath + file

				conf = xml.etree.cElementTree.parse(useraddition)
				for x in conf.getroot():
					if x.tag == "set" and x.get("name") == 'additions_user':
						root =  x
						for x in root:
							if x.tag == "plugin":
								if x.get("type") == "mod":
									confcat = x.get("confcat")
									if p_name ==  x.get("name").replace("&amp;","&"):
										status = [item for item in mp_globals.status if item[0] == x.get("modfile")]
										if status:
											if int(config.mediaportal.version.value) < int(status[0][1]):
												if status[0][1] == "9999":
													self.session.open(MessageBoxExt, _("This Plugin has been marked as \"not working\" by the developers.\n\nCurrent developer status of this Plugin is:\n\"%s\"\n\nIf someone else is willing to provide a fix for this Plugin then please get in contact with us.") % status[0][2], MessageBoxExt.TYPE_INFO)
												else:
													self.session.open(MessageBoxExt, _("This Plugin has been marked as \"not working\" by the developers.\n\nCurrent developer status of this Plugin is:\n\"%s\"") % status[0][2], MessageBoxExt.TYPE_INFO)
												if not config.mediaportal.debugMode.value == "High":
													return
										param = ""
										param1 = x.get("param1")
										param2 = x.get("param2")
										kids = x.get("kids")
										if param1 != "":
											param = ", \"" + param1 + "\""
											exec("self.par1 = \"" + x.get("param1") + "\"")
										if param2 != "":
											param = param + ", \"" + param2 + "\""
											exec("self.par2 = \"" + x.get("param2") + "\"")
										if confcat == "porn":
											exec("self.pornscreen = " + x.get("screen") + "")
										elif kids != "1" and config.mediaportal.kidspin.value:
											exec("self.pornscreen = " + x.get("screen") + "")
										else:
											exec("self.session.open(" + x.get("screen") + param + ")")

		if self.pornscreen:
			if config.mediaportal.pornpin.value:
				if pincheck.pin_entered == False:
					self.session.openWithCallback(self.pincheckok, PinInputExt, pinList = [(config.mediaportal.adultpincode.value)], triesEntry = config.mediaportal.retries.adultpin, title = _("Please enter the correct PIN"), windowTitle = _("Enter adult PIN"))
				else:
					if self.par1 == "":
						self.session.open(self.pornscreen)
					elif self.par2 == "":
						self.session.open(self.pornscreen, self.par1)
					else:
						self.session.open(self.pornscreen, self.par1, self.par2)
			else:
				if self.par1 == "":
					self.session.open(self.pornscreen)
				elif self.par2 == "":
					self.session.open(self.pornscreen, self.par1)
				else:
					self.session.open(self.pornscreen, self.par1, self.par2)

	def pincheckok(self, pincode):
		if pincode:
			pincheck.pinEntered()
			if self.par1 == "":
				self.session.open(self.pornscreen)
			elif self.par2 == "":
				self.session.open(self.pornscreen, self.par1)
			else:
				self.session.open(self.pornscreen, self.par1, self.par2)

	def setInfo(self):
		if self["covercollection"].getCurrentIndex() >=0:
			item = self["covercollection"].getCurrent()
			(p_name, p_picname, p_picpath, p_genre, p_hits, p_sort) = item[0]
			try:
				self['name'].instance.setShowHideAnimation(config.mediaportal.animation_label.value)
			except:
				pass
			self['name'].setText(p_name)
			if config.mediaportal.pagestyle.value == "Graphic":
				self.refresh_apple_page_bar()
			else:
				currentPage = self["covercollection"].getCurrentPage()
				totalPages = self["covercollection"].getTotalPages()
				pageinfo = _("Page") + " %s / %s" % (currentPage, totalPages)
				self['page'].setText(pageinfo)

	def keyLeft(self):
		self["covercollection"].MoveLeft()
		self.setInfo()

	def keyRight(self):
		self["covercollection"].MoveRight()
		self.setInfo()

	def keyUp(self):
		self["covercollection"].MoveUp()
		self.setInfo()

	def keyDown(self):
		self["covercollection"].MoveDown()
		self.setInfo()

	def page_next(self):
		self["covercollection"].NextPage()
		self.setInfo()

	def page_back(self):
		self["covercollection"].PreviousPage()
		self.setInfo()

	def check_empty_list(self):
		if len(self.plugin_liste) == 0:
			self['name'].setText('Keine Plugins der Kategorie %s aktiviert!' % config.mediaportal.filter.value)
			return True
		else:
			return False

	# Apple Page Style
	def refresh_apple_page_bar(self):
		if config.mediaportal.pagestyle.value == "Graphic":
			if self["covercollection"].getCurrentIndex() >=0:
				currentPage = self["covercollection"].getCurrentPage()
				totalPages = self["covercollection"].getTotalPages()
				for x in range(1,totalPages+1):
					if x == currentPage:
						self["page_empty"+str(x)].hide()
						self["page_sel"+str(x)].show()
					else:
						self["page_sel"+str(x)].hide()
						self["page_empty"+str(x)].show()

	def keySetup(self):
		if config.mediaportal.setuppin.value:
			self.session.openWithCallback(self.pinok, PinInputExt, pinList = [(config.mediaportal.pincode.value)], triesEntry = config.mediaportal.retries.pincode, title = _("Please enter the correct PIN"), windowTitle = _("Enter setup PIN"))
		else:
			self.session.openWithCallback(self.restart, MPSetup)

	def keySimpleList(self):
		mp_globals.activeIcon = "simplelist"
		self.session.open(simplelistGenreScreen)

	def pinok(self, pincode):
		if pincode:
			self.session.openWithCallback(self.restart, MPSetup)

	def chSort(self):
		print "Sort: %s" % config.mediaportal.sortplugins.value

		if config.mediaportal.sortplugins.value == "hits":
			config.mediaportal.sortplugins.value = "abc"
		elif config.mediaportal.sortplugins.value == "abc":
			config.mediaportal.sortplugins.value = "user"
		elif config.mediaportal.sortplugins.value == "user":
			config.mediaportal.sortplugins.value = "hits"

		print "Sort changed:", config.mediaportal.sortplugins.value
		self.restart()

	def changeFilter(self):
		self.startChoose()

	def chFilter(self):
		print "Filter:", config.mediaportal.filter.value

		if config.mediaportal.filter.value == "ALL":
			config.mediaportal.filter.value = "Mediathek"
		elif config.mediaportal.filter.value == "Mediathek":
			config.mediaportal.filter.value = "User-additions"
		elif config.mediaportal.filter.value == "User-additions":
			config.mediaportal.filter.value = "Sport"
		elif config.mediaportal.filter.value == "Sport":
			config.mediaportal.filter.value = "Music"
		elif config.mediaportal.filter.value == "Music":
			config.mediaportal.filter.value = "Fun"
		elif config.mediaportal.filter.value == "Fun":
			config.mediaportal.filter.value = "NewsDoku"
		elif config.mediaportal.filter.value == "NewsDoku":
			config.mediaportal.filter.value = "Porn"
		elif config.mediaportal.filter.value == "Porn":
			config.mediaportal.filter.value = "ALL"

		print "Filter changed:", config.mediaportal.filter.value
		self.restartAndCheck()

	def restartAndCheck(self):
		if config.mediaportal.filter.value != "ALL":
			dump_liste2 = self.dump_liste
			self.plugin_liste = []
			self.plugin_liste = [x for x in dump_liste2 if re.search(config.mediaportal.filter.value, x[2])]
			if len(self.plugin_liste) == 0:
				print "Filter ist deaktviert.. recheck..: %s" % config.mediaportal.filter.value
				self.chFilter()
			else:
				print "Mediaportal restart."
				config.mediaportal.filter.save()
				configfile.save()
				self.close(self.session, False, self.lastservice)
		else:
			print "Mediaportal restart."
			config.mediaportal.filter.save()
			configfile.save()
			self.close(self.session, False, self.lastservice)

	def showPorn(self):
		if config.mediaportal.showporn.value:
			config.mediaportal.showporn.value = False
			if config.mediaportal.filter.value == "Porn":
				self.chFilter()
			config.mediaportal.showporn.save()
			config.mediaportal.filter.save()
			configfile.save()
			self.restart()
		else:
			self.session.openWithCallback(self.showPornOK, PinInputExt, pinList = [(config.mediaportal.adultpincode.value)], triesEntry = config.mediaportal.retries.adultpin, title = _("Please enter the correct PIN"), windowTitle = _("Enter adult PIN"))

	def showPornOK(self, pincode):
		if pincode:
			pincheck.pinEntered()
			config.mediaportal.showporn.value = True
			config.mediaportal.showporn.save()
			configfile.save()
			self.restart()

	def keyCancel(self):
		config.mediaportal.filter.save()
		configfile.save()
		self.close(self.session, True, self.lastservice)

	def restart(self):
		config.mediaportal.filter.save()
		config.mediaportal.sortplugins.save()
		configfile.save()
		if autoStartTimer is not None:
			autoStartTimer.update()
		self.close(self.session, False, self.lastservice)

	def startChoose(self):
		if mp_globals.isDreamOS:
			self.session.openWithCallback(self.gotFilter, MPchooseFilter, self.dump_liste, config.mediaportal.filter.value, is_dialog=True)
		else:
			self.session.openWithCallback(self.gotFilter, MPchooseFilter, self.dump_liste, config.mediaportal.filter.value)

	def gotFilter(self, filter):
		if not config.mediaportal.showporn.value and filter == "Porn":
			return
		elif not config.mediaportal.showuseradditions.value and filter == "User-additions":
			return
		elif filter != True:
			config.mediaportal.filter.value = filter
			self.restartAndCheck()

class MPWallVTi(Screen, HelpableScreen):

	def __init__(self, session, lastservice, filter):
		self.lastservice = mp_globals.lastservice = lastservice
		self.wallbw = False
		self.plugin_liste = []
		self.skin_path = mp_globals.pluginPath + mp_globals.skinsPath

		self.images_path = "%s/%s/images" % (self.skin_path, config.mediaportal.skin.value)
		if not fileExists(self.images_path):
			self.images_path = self.skin_path + mp_globals.skinFallback + "/images"

		conf = xml.etree.cElementTree.parse(CONFIG)
		for x in conf.getroot():
			if x.tag == "set" and x.get("name") == 'additions':
				root =  x
				for x in root:
					if x.tag == "plugin":
						if x.get("type") == "mod":
							modfile = x.get("modfile")
							confcat = x.get("confcat")
							if not config.mediaportal.showporn.value and confcat == "porn":
								pass
							else:
								gz = x.get("gz")
								if not config.mediaportal.showuseradditions.value and gz == "1":
									pass
								else:
									mod = eval("config.mediaportal." + x.get("confopt") + ".value")
									if mod:
										y = eval("self.plugin_liste.append((\"" + x.get("name").replace("&amp;","&") + "\", \"" + x.get("icon") + "\", \"" + x.get("filter") + "\"))")

		xmlpath = resolveFilename(SCOPE_PLUGINS, "Extensions/MediaPortal/additions/")
		for file in os.listdir(xmlpath):
			if file.endswith(".xml") and file != "additions.xml":
				useraddition = xmlpath + file

				conf = xml.etree.cElementTree.parse(useraddition)
				for x in conf.getroot():
					if x.tag == "set" and x.get("name") == 'additions_user':
						root =  x
						for x in root:
							if x.tag == "plugin":
								if x.get("type") == "mod":
									modfile = x.get("modfile")
									confcat = x.get("confcat")
									if not config.mediaportal.showporn.value and confcat == "porn":
										pass
									else:
										gz = x.get("gz")
										if not config.mediaportal.showuseradditions.value and gz == "1":
											pass
										else:
											mod = eval("config.mediaportal." + x.get("confopt") + ".value")
											if mod:
												y = eval("self.plugin_liste.append((\"" + x.get("name").replace("&amp;","&") + "\", \"" + x.get("icon") + "\", \"" + x.get("filter") + "\"))")

		if len(self.plugin_liste) == 0:
			self.plugin_liste.append(("","","Mediathek"))

		# Porn
		if (config.mediaportal.showporn.value == False and config.mediaportal.filter.value == 'Porn'):
			config.mediaportal.filter.value = 'ALL'

		# User-additions
		if (config.mediaportal.showuseradditions.value == False and config.mediaportal.filter.value == 'User-additions'):
			config.mediaportal.filter.value = 'ALL'

		# Plugin Sortierung
		if config.mediaportal.sortplugins != "default":

			# Erstelle Pluginliste falls keine vorhanden ist.
			self.sort_plugins_file = "/etc/enigma2/mp_pluginliste"
			if not fileExists(self.sort_plugins_file):
				print "Erstelle Wall-Pluginliste."
				open(self.sort_plugins_file,"w").close()

			pluginliste_leer = os.path.getsize(self.sort_plugins_file)
			if pluginliste_leer == 0:
				print "1st time - Schreibe Wall-Pluginliste."
				first_count = 0
				read_pluginliste = open(self.sort_plugins_file,"a")
				for name,picname,genre in self.plugin_liste:
					read_pluginliste.write('"%s" "%s" "%s" "%s" "%s"\n' % (name, picname, genre, "0", str(first_count)))
					first_count += 1
				read_pluginliste.close()
				print "Wall-Pluginliste wurde erstellt."

			# Lese Pluginliste ein.
			if fileExists(self.sort_plugins_file):

				count_sort_plugins_file = len(open(self.sort_plugins_file).readlines())
				count_plugin_liste = len(self.plugin_liste)

				if int(count_plugin_liste) != int(count_sort_plugins_file):
					print "Ein Plugin wurde aktiviert oder deaktiviert.. erstelle neue pluginliste."

					read_pluginliste_tmp = open(self.sort_plugins_file+".tmp","w")
					read_pluginliste = open(self.sort_plugins_file,"r")
					p_dupeliste = []

					for rawData in read_pluginliste.readlines():
						data = re.findall('"(.*?)" "(.*?)" "(.*?)" "(.*?)" "(.*?)"', rawData, re.S)

						if data:
							(p_name, p_picname, p_genre, p_hits, p_sort) = data[0]
							pop_count = 0
							for pname, ppic, pgenre in self.plugin_liste:
								if p_name not in p_dupeliste:
									if p_name == pname:
										read_pluginliste_tmp.write('"%s" "%s" "%s" "%s" "%s"\n' % (p_name, p_picname, pgenre, p_hits, p_sort))
										p_dupeliste.append((p_name))
										self.plugin_liste.pop(int(pop_count))

									pop_count += 1

					if len(self.plugin_liste) != 0:
						for pname, ppic, pgenre in self.plugin_liste:
							read_pluginliste_tmp.write('"%s" "%s" "%s" "%s" "%s"\n' % (pname, ppic, pgenre, "0", "99"))

					read_pluginliste.close()
					read_pluginliste_tmp.close()
					shutil.move(self.sort_plugins_file+".tmp", self.sort_plugins_file)

				self.new_pluginliste = []
				read_pluginliste = open(self.sort_plugins_file,"r")
				for rawData in read_pluginliste.readlines():
					data = re.findall('"(.*?)" "(.*?)" "(.*?)" "(.*?)" "(.*?)"', rawData, re.S)
					if data:
						(p_name, p_picname, p_genre, p_hits, p_sort) = data[0]
						self.new_pluginliste.append((p_name, p_picname, p_genre, p_hits, p_sort))
				read_pluginliste.close()

			# Sortieren nach hits
			if config.mediaportal.sortplugins.value == "hits":
				self.new_pluginliste.sort(key=lambda x: int(x[3]))
				self.new_pluginliste.reverse()

			# Sortieren nach abcde..
			elif config.mediaportal.sortplugins.value == "abc":
				self.new_pluginliste.sort(key=lambda x: str(x[0]).lower())

			elif config.mediaportal.sortplugins.value == "user":
				self.new_pluginliste.sort(key=lambda x: int(x[4]))

			self.plugin_liste = self.new_pluginliste

		if config.mediaportal.wall2mode.value == "bw":
			self.wallbw = True

		if mp_globals.videomode == 2:
			self.perpage = 35
			pageiconwidth = 36
			pageicondist = 20
			screenwidth = 1920
			screenheight = 1080
		else:
			self.perpage = 21
			pageiconwidth = 26
			pageicondist = 20
			screenwidth = 1280
			screenheight = 720

		path = "%s/%s/MP_WallVTi.xml" % (self.skin_path, config.mediaportal.skin.value)
		if not fileExists(path):
			path = self.skin_path + mp_globals.skinFallback + "/MP_WallVTi.xml"
		with open(path, "r") as f:
			self.skin = f.read()
			f.close()

		# Page Style
		if config.mediaportal.pagestyle.value == "Graphic":
			skincontent = ""
			self.skin = self.skin.replace('</screen>', '')
			self.dump_liste_page_tmp = self.plugin_liste
			if config.mediaportal.filter.value != "ALL":
				self.plugin_liste_page_tmp = []
				self.plugin_liste_page_tmp = [x for x in self.dump_liste_page_tmp if re.search(config.mediaportal.filter.value, x[2])]
			else:
				self.plugin_liste_page_tmp = self.plugin_liste

			if len(self.plugin_liste_page_tmp) != 0:
				self.counting_pages = int(round(float((len(self.plugin_liste_page_tmp)-1) / self.perpage) + 0.5))
				pagebar_size = self.counting_pages * pageiconwidth + (self.counting_pages-1) * pageicondist
				start_pagebar = int(screenwidth / 2 - pagebar_size / 2)

				for x in range(1,self.counting_pages+1):
					normal = screenheight - 2 * pageiconwidth
					if config.mediaportal.skin.value == "original":
						normal = normal - 20
					if mp_globals.videomode == 2:
						normal = normal - 30
					skincontent += "<widget name=\"page_empty" + str(x) + "\" position=\"" + str(start_pagebar) + "," + str(normal) + "\" size=\"" + str(pageiconwidth) + "," + str(pageiconwidth) + "\" zPosition=\"2\" transparent=\"1\" alphatest=\"blend\" />"
					skincontent += "<widget name=\"page_sel" + str(x) + "\" position=\"" + str(start_pagebar) + "," + str(normal) + "\" size=\"" + str(pageiconwidth) + "," + str(pageiconwidth) + "\" zPosition=\"2\" transparent=\"1\" alphatest=\"blend\" />"
					start_pagebar += pageiconwidth + pageicondist

			self.skin += skincontent
			self.skin += "</screen>"

		self["hidePig"] = Boolean()
		self["hidePig"].setBoolean(config.mediaportal.minitv.value)

		Screen.__init__(self, session)

		addFont(resolveFilename(SCOPE_PLUGINS, "Extensions/MediaPortal/resources/") + "mediaportal1.ttf", "mediaportal", 100, False)

		if config.mediaportal.backgroundtv.value:
			config.mediaportal.minitv.value = True
			config.mediaportal.minitv.save()
			config.mediaportal.restorelastservice.value = "2"
			config.mediaportal.restorelastservice.save()
			configfile.save()
			session.nav.stopService()

		self["actions"] = ActionMap(["MP_Actions"], {
			"up"    : self.keyUp,
			"down"  : self.keyDown,
			"left"  : self.keyLeft,
			"right" : self.keyRight,
			"info"  : self.showPorn,
			"0": boundFunction(self.gotFilter, "ALL"),
			"1": boundFunction(self.gotFilter, "Mediathek"),
			"2": boundFunction(self.gotFilter, "Fun"),
			"3": boundFunction(self.gotFilter, "Music"),
			"4": boundFunction(self.gotFilter, "Sport"),
			"5": boundFunction(self.gotFilter, "NewsDoku"),
			"6": boundFunction(self.gotFilter, "Porn"),
			"7": boundFunction(self.gotFilter, "User-additions")
		}, -1)
		self["MP_Actions"] = HelpableActionMap(self, "MP_Actions", {
			"blue"  : (self.changeFilter, _("Change filter")),
			"green" : (self.chSort, _("Change sort order")),
			"yellow": (self.manuelleSortierung, _("Manual sorting")),
			"red"   : (self.keySimpleList, _("Open SimpleList")),
			"ok"    : (self.keyOK, _("Open selected Plugin")),
			"cancel": (self.keyCancel, _("Exit MediaPortal")),
			"nextBouquet" :	(self.page_next, _("Next page")),
			"prevBouquet" :	(self.page_back, _("Previous page")),
			"menu" : (self.keySetup, _("MediaPortal Setup")),
			config.mediaportal.simplelist_key.value: (self.keySimpleList, _("Open SimpleList"))
		}, -1)

		self['name'] = Label("")
		self['version'] = Label(config.mediaportal.version.value[0:8])
		self['red'] = Label("SimpleList")
		self['green'] = Label("")
		self['yellow'] = Label(_("Sort"))
		self['blue'] = Label("")
		self['CH+'] = Label(_("CH+"))
		self['CH-'] = Label(_("CH-"))
		self['PVR'] = Label(_("PVR"))
		self['Exit'] = Label(_("Exit"))
		self['Help'] = Label(_("Help"))
		self['Menu'] = Label(_("Menu"))
		self['page'] = Label("")

		self['list'] = CoverWall()
		self['list'].l.setViewMode(eWallPythonMultiContent.MODE_WALL)

		# Apple Page Style
		if config.mediaportal.pagestyle.value == "Graphic" and len(self.plugin_liste_page_tmp) != 0:
			for x in range(1,self.counting_pages+1):
				self["page_empty"+str(x)] = Pixmap()
				self["page_empty"+str(x)].show()
				self["page_sel"+str(x)] = Pixmap()
				self["page_sel"+str(x)].show()

		HelpableScreen.__init__(self)
		self.onFirstExecBegin.append(self._onFirstExecBegin)
		self.onFirstExecBegin.append(self.checkPathes)
		self.onFirstExecBegin.append(self.status)

	def checkPathes(self):
		CheckPathes(self.session).checkPathes(self.cb_checkPathes)

	def cb_checkPathes(self):
		self.session.openWithCallback(self.restart, MPSetup)

	def status(self):
		update_agent = getUserAgent()
		update_url = getUpdateUrl()
		twAgentGetPage(update_url, agent=update_agent, timeout=30).addCallback(self.checkstatus)

	def checkstatus(self, html):
		if re.search(".*?<html", html):
			return
		self.html = html
		tmp_infolines = html.splitlines()
		statusurl = tmp_infolines[4]
		update_agent = getUserAgent()
		twAgentGetPage(statusurl, agent=update_agent, timeout=30).addCallback(_status)

	def manuelleSortierung(self):
		if config.mediaportal.filter.value == 'ALL':
			self.session.openWithCallback(self.restart, MPpluginSort)
		else:
			self.session.open(MessageBoxExt, _('Ordering is only possible with filter "ALL".'), MessageBoxExt.TYPE_INFO, timeout=3)

	def hit_plugin(self, pname):
		if fileExists(self.sort_plugins_file):
			read_pluginliste = open(self.sort_plugins_file,"r")
			read_pluginliste_tmp = open(self.sort_plugins_file+".tmp","w")
			for rawData in read_pluginliste.readlines():
				data = re.findall('"(.*?)" "(.*?)" "(.*?)" "(.*?)" "(.*?)"', rawData, re.S)
				if data:
					(p_name, p_picname, p_genre, p_hits, p_sort) = data[0]
					if pname == p_name:
						new_hits = int(p_hits)+1
						read_pluginliste_tmp.write('"%s" "%s" "%s" "%s" "%s"\n' % (p_name, p_picname, p_genre, str(new_hits), p_sort))
					else:
						read_pluginliste_tmp.write('"%s" "%s" "%s" "%s" "%s"\n' % (p_name, p_picname, p_genre, p_hits, p_sort))
			read_pluginliste.close()
			read_pluginliste_tmp.close()
			shutil.move(self.sort_plugins_file+".tmp", self.sort_plugins_file)

	def _onFirstExecBegin(self):
		_hosters()
		if not mp_globals.start:
			self.close(self.session, True, self.lastservice)
		if config.mediaportal.autoupdate.value:
			checkupdate(self.session).checkforupdate()

		# load plugin icons
		print "Set Filter:", config.mediaportal.filter.value
		if config.mediaportal.filter.value == "ALL":
			name = _("ALL")
		elif config.mediaportal.filter.value == "Mediathek":
			name = _("Libraries")
		elif config.mediaportal.filter.value == "User-additions":
			name = _("User-additions")
		elif config.mediaportal.filter.value == "Fun":
			name = _("Fun")
		elif config.mediaportal.filter.value == "NewsDoku":
			name = _("News&Documentary")
		elif config.mediaportal.filter.value == "Music":
			name = _("Music")
		elif config.mediaportal.filter.value == "Sport":
			name = _("Sports")
		elif config.mediaportal.filter.value == "Porn":
			name = _("Porn")
		self['blue'].setText(name)
		self.sortplugin = config.mediaportal.sortplugins.value
		if self.sortplugin == "hits":
			self.sortplugin = "Hits"
		elif self.sortplugin == "abc":
			self.sortplugin = "ABC"
		elif self.sortplugin == "user":
			self.sortplugin = "User"
		self['green'].setText(self.sortplugin)
		self.dump_liste = self.plugin_liste
		if config.mediaportal.filter.value != "ALL":
			self.plugin_liste = []
			self.plugin_liste = [x for x in self.dump_liste if re.search(config.mediaportal.filter.value, x[2])]
		if len(self.plugin_liste) == 0:
			self.chFilter()
			if config.mediaportal.filter.value == "ALL":
				name = _("ALL")
			elif config.mediaportal.filter.value == "Mediathek":
				name = _("Libraries")
			elif config.mediaportal.filter.value == "User-additions":
				name = _("User-additions")
			elif config.mediaportal.filter.value == "Fun":
				name = _("Fun")
			elif config.mediaportal.filter.value == "NewsDoku":
				name = _("News&Documentary")
			elif config.mediaportal.filter.value == "Music":
				name = _("Music")
			elif config.mediaportal.filter.value == "Sport":
				name = _("Sports")
			elif config.mediaportal.filter.value == "Porn":
				name = _("Porn")
			self['blue'].setText(name)

		if config.mediaportal.sortplugins.value == "hits":
			self.plugin_liste.sort(key=lambda x: int(x[3]))
			self.plugin_liste.reverse()

		# Sortieren nach abcde..
		elif config.mediaportal.sortplugins.value == "abc":
			self.plugin_liste.sort(key=lambda t : t[0].lower())

		elif config.mediaportal.sortplugins.value == "user":
			self.plugin_liste.sort(key=lambda x: int(x[4]))

		itemList = []
		posterlist = []
		icon_url = getIconUrl()
		if self.wallbw:
			icons_hashes = grabpage(icon_url+"icons_bw/hashes")
		else:
			icons_hashes = grabpage(icon_url+"icons/hashes")
		if icons_hashes:
			icons_data = re.findall('(.*?)\s\*(.*?\.png)', icons_hashes)
		else:
			icons_data = None

		logo_hashes = grabpage(icon_url+"logos/hashes")
		if logo_hashes:
			logo_data = re.findall('(.*?)\s\*(.*?\.png)', logo_hashes)
		else:
			logo_data = None

		for p_name, p_picname, p_genre, p_hits, p_sort in self.plugin_liste:
			remote_hash = ""
			ds = defer.DeferredSemaphore(tokens=5)
			row = []
			itemList.append(((row),))
			if self.wallbw:
				poster_path = "%s/%s.png" % (config.mediaportal.iconcachepath.value + "icons_bw", p_picname)
				url = icon_url+"icons_bw/" + p_picname + ".png"
				if not fileExists(poster_path):
					if icons_data:
						for x,y in icons_data:
							if y == p_picname+'.png':
								ds.run(downloadPage, url, poster_path)
					poster_path = "%s/images/comingsoon.png" % mp_globals.pluginPath
				else:
					local_hash = hashlib.md5(open(poster_path, 'rb').read()).hexdigest()
					if icons_data:
						for x,y in icons_data:
							if y == p_picname+'.png': remote_hash = x
						if remote_hash != local_hash:
							ds.run(downloadPage, url, poster_path)
							poster_path = "%s/images/comingsoon.png" % mp_globals.pluginPath
			else:
				poster_path = "%s/%s.png" % (config.mediaportal.iconcachepath.value + "icons", p_picname)
				url = icon_url+"icons/" + p_picname + ".png"
				if not fileExists(poster_path):
					if icons_data:
						for x,y in icons_data:
							if y == p_picname+'.png':
								ds.run(downloadPage, url, poster_path)
					poster_path = "%s/images/comingsoon.png" % mp_globals.pluginPath
				else:
					local_hash = hashlib.md5(open(poster_path, 'rb').read()).hexdigest()
					if icons_data:
						for x,y in icons_data:
							if y == p_picname+'.png': remote_hash = x
						if remote_hash != local_hash:
							ds.run(downloadPage, url, poster_path)
							poster_path = "%s/images/comingsoon.png" % mp_globals.pluginPath

			logo_path = "%s/%s.png" % (config.mediaportal.iconcachepath.value + "logos", p_picname)
			url = icon_url+"logos/" + p_picname + ".png"
			if not fileExists(logo_path):
				if logo_data:
					for x,y in logo_data:
						if y == p_picname+'.png':
							ds.run(downloadPage, url, logo_path)
			else:
				local_hash = hashlib.md5(open(logo_path, 'rb').read()).hexdigest()
				if logo_data:
					for x,y in logo_data:
						if y == p_picname+'.png': remote_hash = x
					if remote_hash != local_hash:
						ds.run(downloadPage, url, logo_path)

			row.append(((p_name, p_picname, poster_path, p_genre, p_hits, p_sort),))
			posterlist.append(((p_name, p_picname, poster_path, p_genre, p_hits, p_sort),))

		self['list'].setlist(posterlist)

		if config.mediaportal.pagestyle.value == "Graphic" and len(self.plugin_liste_page_tmp) != 0:
			for x in range(1,self.counting_pages+1):
				poster_path = "%s/page_select.png" % (self.images_path)
				self["page_sel"+str(x)].instance.setPixmap(gPixmapPtr())
				self["page_sel"+str(x)].hide()
				pic = LoadPixmap(cached=True, path=poster_path)
				if pic != None:
					self["page_sel"+str(x)].instance.setPixmap(pic)
					if x == 1:
						self["page_sel"+str(x)].show()

			for x in range(1,self.counting_pages+1):
				poster_path = "%s/page.png" % (self.images_path)
				self["page_empty"+str(x)].instance.setPixmap(gPixmapPtr())
				self["page_empty"+str(x)].hide()
				pic = LoadPixmap(cached=True, path=poster_path)
				if pic != None:
					self["page_empty"+str(x)].instance.setPixmap(pic)
					if x > 1:
						self["page_empty"+str(x)].show()
		self.setInfo()

	def keyOK(self):
		if not testWebConnection():
			self.session.open(MessageBoxExt, _('No connection to the Internet available.'), MessageBoxExt.TYPE_INFO, timeout=3)
			return

		if self["list"].getCurrentIndex() >=0:
			item = self['list'].getcurrentselection()
			(p_name, p_picname, p_picpath, p_genre, p_hits, p_sort) = item

		mp_globals.activeIcon = p_picname
		print "Plugin:", p_name

		self.pornscreen = None
		self.par1 = ""
		self.par2 = ""
		self.hit_plugin(p_name)

		conf = xml.etree.cElementTree.parse(CONFIG)
		for x in conf.getroot():
			if x.tag == "set" and x.get("name") == 'additions':
				root =  x
				for x in root:
					if x.tag == "plugin":
						if x.get("type") == "mod":
							confcat = x.get("confcat")
							if p_name ==  x.get("name").replace("&amp;","&"):
								status = [item for item in mp_globals.status if item[0] == x.get("modfile")]
								if status:
									if int(config.mediaportal.version.value) < int(status[0][1]):
										if status[0][1] == "9999":
											self.session.open(MessageBoxExt, _("This Plugin has been marked as \"not working\" by the developers.\n\nCurrent developer status of this Plugin is:\n\"%s\"\n\nIf someone else is willing to provide a fix for this Plugin then please get in contact with us.") % status[0][2], MessageBoxExt.TYPE_INFO)
										else:
											self.session.open(MessageBoxExt, _("This Plugin has been marked as \"not working\" by the developers.\n\nCurrent developer status of this Plugin is:\n\"%s\"") % status[0][2], MessageBoxExt.TYPE_INFO)
										if not config.mediaportal.debugMode.value == "High":
											return
								param = ""
								param1 = x.get("param1")
								param2 = x.get("param2")
								kids = x.get("kids")
								if param1 != "":
									param = ", \"" + param1 + "\""
									exec("self.par1 = \"" + x.get("param1") + "\"")
								if param2 != "":
									param = param + ", \"" + param2 + "\""
									exec("self.par2 = \"" + x.get("param2") + "\"")
								if confcat == "porn":
									exec("self.pornscreen = " + x.get("screen") + "")
								elif kids != "1" and config.mediaportal.kidspin.value:
									exec("self.pornscreen = " + x.get("screen") + "")
								else:
									exec("self.session.open(" + x.get("screen") + param + ")")

		xmlpath = resolveFilename(SCOPE_PLUGINS, "Extensions/MediaPortal/additions/")
		for file in os.listdir(xmlpath):
			if file.endswith(".xml") and file != "additions.xml":
				useraddition = xmlpath + file

				conf = xml.etree.cElementTree.parse(useraddition)
				for x in conf.getroot():
					if x.tag == "set" and x.get("name") == 'additions_user':
						root =  x
						for x in root:
							if x.tag == "plugin":
								if x.get("type") == "mod":
									confcat = x.get("confcat")
									if p_name ==  x.get("name").replace("&amp;","&"):
										status = [item for item in mp_globals.status if item[0] == x.get("modfile")]
										if status:
											if int(config.mediaportal.version.value) < int(status[0][1]):
												if status[0][1] == "9999":
													self.session.open(MessageBoxExt, _("This Plugin has been marked as \"not working\" by the developers.\n\nCurrent developer status of this Plugin is:\n\"%s\"\n\nIf someone else is willing to provide a fix for this Plugin then please get in contact with us.") % status[0][2], MessageBoxExt.TYPE_INFO)
												else:
													self.session.open(MessageBoxExt, _("This Plugin has been marked as \"not working\" by the developers.\n\nCurrent developer status of this Plugin is:\n\"%s\"") % status[0][2], MessageBoxExt.TYPE_INFO)
												if not config.mediaportal.debugMode.value == "High":
													return
										param = ""
										param1 = x.get("param1")
										param2 = x.get("param2")
										kids = x.get("kids")
										if param1 != "":
											param = ", \"" + param1 + "\""
											exec("self.par1 = \"" + x.get("param1") + "\"")
										if param2 != "":
											param = param + ", \"" + param2 + "\""
											exec("self.par2 = \"" + x.get("param2") + "\"")
										if confcat == "porn":
											exec("self.pornscreen = " + x.get("screen") + "")
										elif kids != "1" and config.mediaportal.kidspin.value:
											exec("self.pornscreen = " + x.get("screen") + "")
										else:
											exec("self.session.open(" + x.get("screen") + param + ")")

		if self.pornscreen:
			if config.mediaportal.pornpin.value:
				if pincheck.pin_entered == False:
					self.session.openWithCallback(self.pincheckok, PinInputExt, pinList = [(config.mediaportal.adultpincode.value)], triesEntry = config.mediaportal.retries.adultpin, title = _("Please enter the correct PIN"), windowTitle = _("Enter adult PIN"))
				else:
					if self.par1 == "":
						self.session.open(self.pornscreen)
					elif self.par2 == "":
						self.session.open(self.pornscreen, self.par1)
					else:
						self.session.open(self.pornscreen, self.par1, self.par2)
			else:
				if self.par1 == "":
					self.session.open(self.pornscreen)
				elif self.par2 == "":
					self.session.open(self.pornscreen, self.par1)
				else:
					self.session.open(self.pornscreen, self.par1, self.par2)

	def pincheckok(self, pincode):
		if pincode:
			pincheck.pinEntered()
			if self.par1 == "":
				self.session.open(self.pornscreen)
			elif self.par2 == "":
				self.session.open(self.pornscreen, self.par1)
			else:
				self.session.open(self.pornscreen, self.par1, self.par2)

	def setInfo(self):
		if self["list"].getCurrentIndex() >=0:
			item = self['list'].getcurrentselection()
			(p_name, p_picname, p_picpath, p_genre, p_hits, p_sort) = item
			self['name'].setText(p_name)
			if config.mediaportal.pagestyle.value == "Graphic":
				self.refresh_apple_page_bar()
			else:
				currentPage = self["list"].getCurrentPage()
				totalPages = self["list"].getPageCount()
				pageinfo = _("Page") + " %s / %s" % (currentPage, totalPages)
				self['page'].setText(pageinfo)

	def keyLeft(self):
		self['list'].left()
		self.setInfo()

	def keyRight(self):
		self['list'].right()
		self.setInfo()

	def keyUp(self):
		self['list'].up()
		self.setInfo()

	def keyDown(self):
		self['list'].down()
		self.setInfo()

	def page_next(self):
		self['list'].nextPage()
		self.setInfo()

	def page_back(self):
		self['list'].prevPage()
		self.setInfo()

	def check_empty_list(self):
		if len(self.plugin_liste) == 0:
			self['name'].setText('Keine Plugins der Kategorie %s aktiviert!' % config.mediaportal.filter.value)
			return True
		else:
			return False

	# Apple Page Style
	def refresh_apple_page_bar(self):
		if config.mediaportal.pagestyle.value == "Graphic":
			if self["list"].getCurrentIndex() >=0:
				currentPage = self["list"].getCurrentPage()
				totalPages = self["list"].getPageCount()
				print currentPage, totalPages
				for x in range(1,totalPages+1):
					if x == currentPage:
						self["page_empty"+str(x)].hide()
						self["page_sel"+str(x)].show()
					else:
						self["page_sel"+str(x)].hide()
						self["page_empty"+str(x)].show()

	def keySetup(self):
		if config.mediaportal.setuppin.value:
			self.session.openWithCallback(self.pinok, PinInputExt, pinList = [(config.mediaportal.pincode.value)], triesEntry = config.mediaportal.retries.pincode, title = _("Please enter the correct PIN"), windowTitle = _("Enter setup PIN"))
		else:
			self.session.openWithCallback(self.restart, MPSetup)

	def keySimpleList(self):
		mp_globals.activeIcon = "simplelist"
		self.session.open(simplelistGenreScreen)

	def pinok(self, pincode):
		if pincode:
			self.session.openWithCallback(self.restart, MPSetup)

	def chSort(self):
		print "Sort: %s" % config.mediaportal.sortplugins.value

		if config.mediaportal.sortplugins.value == "hits":
			config.mediaportal.sortplugins.value = "abc"
		elif config.mediaportal.sortplugins.value == "abc":
			config.mediaportal.sortplugins.value = "user"
		elif config.mediaportal.sortplugins.value == "user":
			config.mediaportal.sortplugins.value = "hits"

		print "Sort changed:", config.mediaportal.sortplugins.value
		self.restart()

	def changeFilter(self):
		self.startChoose()

	def chFilter(self):
		print "Filter:", config.mediaportal.filter.value

		if config.mediaportal.filter.value == "ALL":
			config.mediaportal.filter.value = "Mediathek"
		elif config.mediaportal.filter.value == "Mediathek":
			config.mediaportal.filter.value = "User-additions"
		elif config.mediaportal.filter.value == "User-additions":
			config.mediaportal.filter.value = "Sport"
		elif config.mediaportal.filter.value == "Sport":
			config.mediaportal.filter.value = "Music"
		elif config.mediaportal.filter.value == "Music":
			config.mediaportal.filter.value = "Fun"
		elif config.mediaportal.filter.value == "Fun":
			config.mediaportal.filter.value = "NewsDoku"
		elif config.mediaportal.filter.value == "NewsDoku":
			config.mediaportal.filter.value = "Porn"
		elif config.mediaportal.filter.value == "Porn":
			config.mediaportal.filter.value = "ALL"

		print "Filter changed:", config.mediaportal.filter.value
		self.restartAndCheck()

	def restartAndCheck(self):
		if config.mediaportal.filter.value != "ALL":
			dump_liste2 = self.dump_liste
			self.plugin_liste = []
			self.plugin_liste = [x for x in dump_liste2 if re.search(config.mediaportal.filter.value, x[2])]
			if len(self.plugin_liste) == 0:
				print "Filter ist deaktviert.. recheck..: %s" % config.mediaportal.filter.value
				self.chFilter()
			else:
				print "Mediaportal restart."
				config.mediaportal.filter.save()
				configfile.save()
				self.close(self.session, False, self.lastservice)
		else:
			print "Mediaportal restart."
			config.mediaportal.filter.save()
			configfile.save()
			self.close(self.session, False, self.lastservice)

	def showPorn(self):
		if config.mediaportal.showporn.value:
			config.mediaportal.showporn.value = False
			if config.mediaportal.filter.value == "Porn":
				self.chFilter()
			config.mediaportal.showporn.save()
			config.mediaportal.filter.save()
			configfile.save()
			self.restart()
		else:
			self.session.openWithCallback(self.showPornOK, PinInputExt, pinList = [(config.mediaportal.adultpincode.value)], triesEntry = config.mediaportal.retries.adultpin, title = _("Please enter the correct PIN"), windowTitle = _("Enter adult PIN"))

	def showPornOK(self, pincode):
		if pincode:
			pincheck.pinEntered()
			config.mediaportal.showporn.value = True
			config.mediaportal.showporn.save()
			configfile.save()
			self.restart()

	def keyCancel(self):
		config.mediaportal.filter.save()
		configfile.save()
		self.close(self.session, True, self.lastservice)

	def restart(self):
		config.mediaportal.filter.save()
		config.mediaportal.sortplugins.save()
		configfile.save()
		if autoStartTimer is not None:
			autoStartTimer.update()
		self.close(self.session, False, self.lastservice)

	def startChoose(self):
		self.session.openWithCallback(self.gotFilter, MPchooseFilter, self.dump_liste, config.mediaportal.filter.value)

	def gotFilter(self, filter):
		if not config.mediaportal.showporn.value and filter == "Porn":
			return
		elif not config.mediaportal.showuseradditions.value and filter == "User-additions":
			return
		elif filter != True:
			config.mediaportal.filter.value = filter
			self.restartAndCheck()

class MPchooseFilter(Screen):

	def __init__(self, session, plugin_liste, old_filter):
		self.plugin_liste = plugin_liste
		self.old_filter = old_filter

		self.dupe = []
		self.dupe.append("ALL")
		for (pname, iname, filter, hits, count) in self.plugin_liste:
			#check auf mehrere filter
			if re.search('/', filter):
				mfilter_raw = re.split('/', filter)
				for mfilter in mfilter_raw:
					if not mfilter in self.dupe:
						self.dupe.append(mfilter)
			else:
				if not filter in self.dupe:
					self.dupe.append(filter)

		self.dupe.sort()

		hoehe = 197
		breite = 531
		skincontent = ""
		for x in range(1,len(self.dupe)+1):
			skincontent += "<widget name=\"menu" + str(x) + "\" position=\"" + str(breite) + "," + str(hoehe) + "\" size=\"218,38\" zPosition=\"1\" transparent=\"1\" alphatest=\"blend\" />"
			hoehe += 48

		self.skin_dump = ""
		self.skin_dump += "<widget name=\"frame\" position=\"531,197\" size=\"218,38\" pixmap=\"/usr/lib/enigma2/python/Plugins/Extensions/MediaPortal/images/category_selector_%s.png\" zPosition=\"2\" transparent=\"1\" alphatest=\"blend\" />" % config.mediaportal.selektor.value
		self.skin_dump += skincontent
		self.skin_dump += "</screen>"

		self.skin_path = mp_globals.pluginPath + mp_globals.skinsPath

		path = "%s/%s/MP_Category.xml" % (self.skin_path, config.mediaportal.skin.value)
		if not fileExists(path):
			path = self.skin_path + mp_globals.skinFallback + "/MP_Category.xml"

		with open(path, "r") as f:
			self.skin_dump2 = f.read()
			self.skin_dump2 += self.skin_dump
			self.skin = self.skin_dump2
			f.close()

		self["hidePig"] = Boolean()
		self["hidePig"].setBoolean(config.mediaportal.minitv.value)

		Screen.__init__(self, session)

		self["actions"] = ActionMap(["MP_Actions"], {
			"ok": self.keyOk,
			"cancel": self.keyCancel,
			"up": self.keyup,
			"down": self.keydown
		}, -1)

		self["frame"] = MovingPixmap()
		self["frame"].hide()

		self['F1'] = Label("")
		self['F2'] = Label("")
		self['F3'] = Label("")
		self['F4'] = Label("")
		self['F5'] = Label("")
		self['F6'] = Label("")
		self['F7'] = Label("")
		self['F8'] = Label("")

		for x in range(1,len(self.dupe)+1):
			self["menu"+str(x)] = Pixmap()
			self["menu"+str(x)].show()

		self.onFirstExecBegin.append(self.loadPage)

	def loadPage(self):
		for x in range(1,len(self.dupe)+1):
			if self.dupe[int(x)-1] == self.old_filter:
				position = self["menu"+str(x)].instance.position()
				self["frame"].moveTo(position.x(), position.y(), 1)
				self["frame"].show()
				self["frame"].startMoving()
				self.selektor_index = x
			filtername = self.dupe[int(x)-1]
			if filtername == "ALL":
				name = _("ALL")
			elif filtername == "Mediathek":
				name = _("Libraries")
			elif filtername == "User-additions":
				name = _("User-additions")
			elif filtername == "Fun":
				name = _("Fun")
			elif filtername == "NewsDoku":
				name = _("News&Documentary")
			elif filtername == "Music":
				name = _("Music")
			elif filtername == "Sport":
				name = _("Sports")
			elif filtername == "Porn":
				name = _("Porn")
			self['F'+str(x)].setText(name)
			poster_path = "%s/images/category_selector_button.png" % mp_globals.pluginPath
			if fileExists(poster_path):
				self["menu"+str(x)].instance.setPixmap(gPixmapPtr())
				self["menu"+str(x)].hide()
				pic = LoadPixmap(cached=True, path=poster_path)
				if pic != None:
					self["menu"+str(x)].instance.setPixmap(pic)
					self["menu"+str(x)].show()

	def moveframe(self):
		position = self["menu"+str(self.selektor_index)].instance.position()
		self["frame"].moveTo(position.x(), position.y(), 1)
		self["frame"].show()
		self["frame"].startMoving()

	def keyOk(self):
		self.close(self.dupe[self.selektor_index-1])

	def keyup(self):
		if int(self.selektor_index) != 1:
			self.selektor_index -= 1
			self.moveframe()

	def keydown(self):
		if int(self.selektor_index) != len(self.dupe):
			self.selektor_index += 1
			self.moveframe()

	def keyCancel(self):
		self.close(True)

def exit(session, result, lastservice):
	global lc_stats
	if not result:
		if config.mediaportal.premiumize_use.value:
			if not mp_globals.premium_yt_proxy_host:
				CheckPremiumize(session).premiumizeProxyConfig(False)

		if config.mediaportal.ansicht.value == "liste":
			session.openWithCallback(exit, MPList, lastservice)
		elif config.mediaportal.ansicht.value == "wall":
			session.openWithCallback(exit, MPWall, lastservice, config.mediaportal.filter.value)
		elif config.mediaportal.ansicht.value == "wall2":
			session.openWithCallback(exit, MPWall2, lastservice, config.mediaportal.filter.value)
		elif config.mediaportal.ansicht.value == "wall_vti":
			session.openWithCallback(exit, MPWallVTi, lastservice, config.mediaportal.filter.value)
	else:
		try:
			if mp_globals.animationfix:
				getDesktop(0).setAnimationsEnabled(False)
				mp_globals.animationfix = False
		except:
			pass
		session.nav.playService(lastservice)
		_stylemanager(0)
		reactor.callLater(1, export_lru_caches)
		reactor.callLater(5, clearTmpBuffer)
		watcher.stop()
		if SHOW_HANG_STAT:
			lc_stats.stop()
			del lc_stats

def _stylemanager(mode):
	desktopSize = getDesktop(0).size()
	if desktopSize.height() == 1080:
		mp_globals.videomode = 2
		mp_globals.fontsize = 30
		mp_globals.sizefactor = 3
	else:
		mp_globals.videomode = 1
		mp_globals.fontsize = 23
		mp_globals.sizefactor = 1
	try:
		from enigma import eWindowStyleManager, eWindowStyleSkinned, eSize, eListboxPythonStringContent, eListboxPythonConfigContent
		try:
			from enigma import eWindowStyleScrollbar
		except:
			pass
		from skin import parseSize, parseFont, parseColor
		try:
			from skin import parseValue
		except:
			pass

		stylemgr = eWindowStyleManager.getInstance()
		desktop = getDesktop(0)
		styleskinned = eWindowStyleSkinned()

		try:
			stylescrollbar = eWindowStyleScrollbar()
			skinScrollbar = True
		except:
			skinScrollbar = False

		if mode == 0:
			skin_path = resolveFilename(SCOPE_CURRENT_SKIN) + "skin_user_colors.xml"
			if not fileExists(skin_path):
				skin_path = resolveFilename(SCOPE_CURRENT_SKIN) + "skin.xml"
			file_path = resolveFilename(SCOPE_SKIN)
		else:
			skin_path = mp_globals.pluginPath + mp_globals.skinsPath + "/" + config.mediaportal.skin.value + "/skin.xml"
			if not fileExists(skin_path):
				skin_path = mp_globals.pluginPath + mp_globals.skinsPath + mp_globals.skinFallback + "/skin.xml"
			file_path = mp_globals.pluginPath + "/"

		if fileExists(skin_path):
			conf = xml.etree.cElementTree.parse(skin_path)
			for x in conf.getroot():
				if x.tag == "fonts" and mode == 0:
					fonts = x
					for x in fonts:
						if x.tag == "font":
							replacement = x.get("replacement")
							if replacement == "1":
								filename = x.get("filename")
								name = x.get("name")
								scale = x.get("scale")
								if scale:
									scale = int(scale)
								else:
									scale = 100
								resolved_font = resolveFilename(SCOPE_FONTS, filename, path_prefix='')
								if not fileExists(resolved_font): #when font is not available look at current skin path
									skin_path = resolveFilename(SCOPE_CURRENT_SKIN, filename)
									if fileExists(skin_path):
										resolved_font = skin_path
								addFont(resolved_font, name, scale, True)
				elif x.tag == "windowstylescrollbar":
					if skinScrollbar:
						windowstylescrollbar =  x
						for x in windowstylescrollbar:
							if x.tag == "value":
								if x.get("name") == "BackgroundPixmapTopHeight":
									stylescrollbar.setBackgroundPixmapTopHeight(int(x.get("value")))
								elif x.get("name") == "BackgroundPixmapBottomHeight":
									stylescrollbar.setBackgroundPixmapBottomHeight(int(x.get("value")))
								elif x.get("name") == "ValuePixmapTopHeight":
									stylescrollbar.setValuePixmapTopHeight(int(x.get("value")))
								elif x.get("name") == "ValuePixmapBottomHeight":
									stylescrollbar.setValuePixmapBottomHeight(int(x.get("value")))
								elif x.get("name") == "ScrollbarWidth":
									stylescrollbar.setScrollbarWidth(int(x.get("value")))
								elif x.get("name") == "ScrollbarBorderWidth":
									stylescrollbar.setScrollbarBorderWidth(int(x.get("value")))
							if x.tag == "pixmap":
								if x.get("name") == "BackgroundPixmap":
									stylescrollbar.setBackgroundPixmap(LoadPixmap(file_path + x.get("filename"), desktop))
								elif x.get("name") == "ValuePixmap":
									stylescrollbar.setValuePixmap(LoadPixmap(file_path + x.get("filename"), desktop))
				elif x.tag == "windowstyle" and x.get("id") == "0":
					font = gFont("Regular", 20)
					offset = eSize(20, 5)
					windowstyle = x
					for x in windowstyle:
						if x.tag == "title":
							font = parseFont(x.get("font"), ((1,1),(1,1)))
							offset = parseSize(x.get("offset"), ((1,1),(1,1)))
						elif x.tag == "color":
							colorType = x.get("name")
							color = parseColor(x.get("color"))
							try:
								styleskinned.setColor(eWindowStyleSkinned.__dict__["col" + colorType], color)
							except:
								pass
						elif x.tag == "borderset":
							bsName = str(x.get("name"))
							borderset =  x
							for x in borderset:
								if x.tag == "pixmap":
									bpName = x.get("pos")
									if "filename" in x.attrib:
										try:
											styleskinned.setPixmap(eWindowStyleSkinned.__dict__[bsName], eWindowStyleSkinned.__dict__[bpName], LoadPixmap(file_path + x.get("filename"), desktop))
										except:
											pass
									elif "color" in x.attrib:
										color = parseColor(x.get("color"))
										size = int(x.get("size"))
										try:
											styleskinned.setColorBorder(eWindowStyleSkinned.__dict__[bsName], eWindowStyleSkinned.__dict__[bpName], color, size)
										except:
											pass
						elif x.tag == "listfont":
							fontType = x.get("type")
							fontSize = int(x.get("size"))
							fontFace = x.get("font")
							try:
								styleskinned.setListFont(eWindowStyleSkinned.__dict__["listFont" + fontType], fontSize, fontFace)
							except:
								pass
					try:
						styleskinned.setTitleFont(font)
						styleskinned.setTitleOffset(offset)
					except:
						pass
				elif x.tag == "listboxcontent":
					listboxcontent = x
					for x in listboxcontent:
						if x.tag == "offset":
							name = x.get("name")
							value = x.get("value")
							if name and value:
								try:
									if name == "left":
											eListboxPythonStringContent.setLeftOffset(parseValue(value))
									elif name == "right":
											eListboxPythonStringContent.setRightOffset(parseValue(value))
								except:
									pass
						elif x.tag == "font":
							name = x.get("name")
							font = x.get("font")
							if name and font:
								try:
									if name == "string":
											eListboxPythonStringContent.setFont(parseFont(font, ((1,1),(1,1))))
									elif name == "config_description":
											eListboxPythonConfigContent.setDescriptionFont(parseFont(font, ((1,1),(1,1))))
									elif name == "config_value":
											eListboxPythonConfigContent.setValueFont(parseFont(font, ((1,1),(1,1))))
								except:
									pass
						elif x.tag == "value":
							name = x.get("name")
							value = x.get("value")
							if name and value:
								try:
									if name == "string_item_height":
											eListboxPythonStringContent.setItemHeight(parseValue(value))
									elif name == "config_item_height":
											eListboxPythonConfigContent.setItemHeight(parseValue(value))
								except:
									pass
				elif x.tag == "mediaportal":
					mediaportal = x
					for x in mediaportal:
						if x.tag == "color":
							colorType = x.get("name")
							exec("mp_globals." + x.get("name") + "=\"" + x.get("color") + "\"")
						elif x.tag == "overridefont":
							exec("mp_globals.font=\"" + x.get("font") + "\"")
						elif x.tag == "overridefontsize":
							mp_globals.fontsize = int(x.get("value"))
						elif x.tag == "overridesizefactor":
							mp_globals.sizefactor = int(x.get("value"))

			stylemgr.setStyle(0, styleskinned)
			try:
				stylemgr.setStyle(4, stylescrollbar)
			except:
				pass
		else:
			printl('Missing MP skin.xml this file is mandatory!','','E')
	except:
		printl('Fatal skin.xml error!','','E')
		pass

def _hosters():
	hosters_file = "/usr/lib/enigma2/python/Plugins/Extensions/MediaPortal/resources/hosters.xml"
	open_hosters = open(hosters_file)
	data = open_hosters.read()
	open_hosters.close()
	hosters = re.findall('<hoster>(.*?)</hoster><regex>(.*?)</regex>', data)
	mp_globals.hosters = ["|".join([hoster for hoster,regex in hosters])]
	mp_globals.hosters += ["|".join([regex for hoster,regex in hosters])]

def _status(data):
	statusdata = re.findall('"(.*?)"\s"(.*?)"\s"(.*?)"', data)
	if statusdata:
		mp_globals.status = []
		for (plugin, version, status) in statusdata:
			mp_globals.status.append((plugin,version,status))

from resources.simple_lru_cache import SimpleLRUCache
mp_globals.lruCache = SimpleLRUCache(50, config.mediaportal.watchlistpath.value + 'mp_lru_cache')
mp_globals.yt_lruCache = SimpleLRUCache(100, config.mediaportal.watchlistpath.value + 'mp_yt_lru_cache')

watcher = None
lc_stats = None

def export_lru_caches():
	if config.mediaportal.sp_save_resumecache.value:
		mp_globals.lruCache.saveCache()
		mp_globals.yt_lruCache.saveCache()

def import_lru_caches():
	if config.mediaportal.sp_save_resumecache.value:
		mp_globals.lruCache.readCache()
		mp_globals.yt_lruCache.readCache()

def clearTmpBuffer():
	if mp_globals.yt_tmp_storage_dirty:
		mp_globals.yt_tmp_storage_dirty = False
		BgFileEraser = eBackgroundFileEraser.getInstance()
		path = config.mediaportal.storagepath.value
		if os.path.exists(path):
			for fn in next(os.walk(path))[2]:
				BgFileEraser.erase(os.path.join(path,fn))

def MPmain(session, **kwargs):
	mp_globals.start = True
	startMP(session)

def startMP(session):
	try:
		if not getDesktop(0).isAnimationsEnabled():
			getDesktop(0).setAnimationsEnabled(True)
			mp_globals.animationfix = True
	except:
		pass

	from resources.debuglog import printlog as printl
	printl('Starting MediaPortal %s' % config.mediaportal.version.value,None,'H')

	global watcher, lc_stats

	reactor.callLater(2, import_lru_caches)

	addFont(resolveFilename(SCOPE_PLUGINS, "Extensions/MediaPortal/resources/") + "mediaportal1.ttf", "mediaportal", 100, False)
	addFont(resolveFilename(SCOPE_PLUGINS, "Extensions/MediaPortal/resources/") + "mediaportal_clean.ttf", "mediaportal_clean", 100, False)
	addFont(resolveFilename(SCOPE_PLUGINS, "Extensions/MediaPortal/resources/") + "unifont.otf", "Replacement", 100, True)
	mp_globals.font = 'mediaportal'
	_stylemanager(1)

	if watcher == None:
		watcher = HangWatcher()
	watcher.start()
	if SHOW_HANG_STAT:
		lc_stats = task.LoopingCall(watcher.print_stats)
		lc_stats.start(60)

	#if config.mediaportal.epg_enabled.value and not config.mediaportal.epg_runboot.value and not mpepg.has_epg:
	#	def importFini(msg):
	#		session.open(MessageBoxExt, msg, type = MessageBoxExt.TYPE_INFO, timeout=5)
	#	mpepg.importEPGData().addCallback(importFini)

	if config.mediaportal.premiumize_use.value:
		if not mp_globals.premium_yt_proxy_host:
			CheckPremiumize(session).premiumizeProxyConfig(False)

	mp_globals.currentskin = config.mediaportal.skin.value
	lastservice = session.nav.getCurrentlyPlayingServiceReference()

	if config.mediaportal.ansicht.value == "liste":
		session.openWithCallback(exit, MPList, lastservice)
	elif config.mediaportal.ansicht.value == "wall":
		session.openWithCallback(exit, MPWall, lastservice, config.mediaportal.filter.value)
	elif config.mediaportal.ansicht.value == "wall2":
		session.openWithCallback(exit, MPWall2, lastservice, config.mediaportal.filter.value)
	elif config.mediaportal.ansicht.value == "wall_vti":
		session.openWithCallback(exit, MPWallVTi, lastservice, config.mediaportal.filter.value)

##################################
# Autostart section
class AutoStartTimer:
	def __init__(self, session):
		import enigma

		self.session = session
		self.timer = enigma.eTimer()
		if mp_globals.isDreamOS:
			self.timer_conn = self.timer.timeout.connect(self.onTimer)
		else:
			self.timer.callback.append(self.onTimer)
		self.update()

	def getWakeTime(self):
		import time
		if config.mediaportal.epg_enabled.value:
			clock = config.mediaportal.epg_wakeup.value
			nowt = time.time()
			now = time.localtime(nowt)
			return int(time.mktime((now.tm_year, now.tm_mon, now.tm_mday,
				clock[0], clock[1], lastMACbyte()/5, 0, now.tm_yday, now.tm_isdst)))
		else:
			return -1

	def update(self, atLeast = 0):
		import time
		self.timer.stop()
		wake = self.getWakeTime()
		now = int(time.time())
		if wake > 0:
			if wake < now + atLeast:
				# Tomorrow.
				wake += 24*3600
			next = wake - now
			self.timer.startLongTimer(next)
		else:
			wake = -1
		print>>log, "[MP EPGImport] WakeUpTime now set to", wake, "(now=%s)" % now
		return wake

	def runImport(self):
		if config.mediaportal.epg_enabled.value:
			mpepg.getEPGData()

	def onTimer(self):
		import time
		self.timer.stop()
		now = int(time.time())
		print>>log, "[MP EPGImport] onTimer occured at", now
		wake = self.getWakeTime()
		# If we're close enough, we're okay...
		atLeast = 0
		if wake - now < 60:
			self.runImport()
			atLeast = 60
		self.update(atLeast)

def onBootStartCheck():
	import time
	global autoStartTimer
	print>>log, "[MP EPGImport] onBootStartCheck"
	now = int(time.time())
	wake = autoStartTimer.update()
	print>>log, "[MP EPGImport] now=%d wake=%d wake-now=%d" % (now, wake, wake-now)
	if (wake < 0) or (wake - now > 600):
		print>>log, "[MP EPGImport] starting import because auto-run on boot is enabled"
		autoStartTimer.runImport()
	else:
		print>>log, "[MP EPGImport] import to start in less than 10 minutes anyway, skipping..."

def autostart(reason, session=None, **kwargs):
	"called with reason=1 to during shutdown, with reason=0 at startup?"
	#global autoStartTimer
	global _session, watcher
	#import time
	#print>>log, "[MP EPGImport] autostart (%s) occured at" % reason, time.time()
	if reason == 0:
		if session is not None:
			_session = session
			CheckPathes(session).checkPathes(cb_checkPathes)
		if watcher == None:
			watcher = HangWatcher()
		#if autoStartTimer is None:
		#	autoStartTimer = AutoStartTimer(session)
		#if config.mediaportal.epg_runboot.value:
		#	# timer isn't reliable here, damn
		#	onBootStartCheck()
		#if config.mediaportal.epg_deepstandby.value == 'wakeup':
		#	if config.mediaportal.epg_wakeupsleep.value:
		#		print>>log, "[MP EPGImport] Returning to standby"
		#		from Tools import Notifications
		#		Notifications.AddNotification(Screens.Standby.Standby)
	#else:
		#print>>log, "[MP EPGImport] Stop"
		#if autoStartTimer:
		#autoStartTimer.stop()

def cb_checkPathes():
	pass

def getNextWakeup():
	"returns timestamp of next time when autostart should be called"
	if autoStartTimer:
		if config.mediaportal.epg_deepstandby.value == 'wakeup':
			print>>log, "[MP EPGImport] Will wake up from deep sleep"
			return autoStartTimer.update()
	return -1

def Plugins(path, **kwargs):
	mp_globals.pluginPath = path

	result = [
		PluginDescriptor(name="MediaPortal", description="MediaPortal - EPG Importer", where = [PluginDescriptor.WHERE_AUTOSTART, PluginDescriptor.WHERE_SESSIONSTART], fnc = autostart, wakeupfnc = getNextWakeup),
		PluginDescriptor(name="MediaPortal", description="MediaPortal", where = [PluginDescriptor.WHERE_PLUGINMENU, PluginDescriptor.WHERE_EXTENSIONSMENU], icon="plugin.png", fnc=MPmain)
	]
	return result
