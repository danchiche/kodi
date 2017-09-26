# -*- coding: utf-8 -*- 

import xbmc, xbmcaddon, xbmcgui, xbmcplugin
import sys, os, urllib
import common
from xml.dom.minidom import parseString
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

URL_XML_FEED = 'http://www.annatel.tv/api/getchannels?login=%s&password=%s'
URL_EPG_FEED = 'http://anna.tl/xmltv/XmltvAnnatel.xml.gz'
__AddonID__ = 'plugin.video.annatel.tv'
__Addon__ = xbmcaddon.Addon(__AddonID__)
__AddonDataPath__ = os.path.join(xbmc.translatePath( "special://userdata/addon_data").decode("utf-8"), __AddonID__)
__XML__ = os.path.join(__AddonDataPath__, "Annatel", "XML")
__EPG__ = os.path.join(__AddonDataPath__, "Annatel", "EPG")

def GetCredentials():
	username = __Addon__.getSetting('username')
	password = __Addon__.getSetting('password')
	return (username, password)

def IsLoggedIn():
	username, password = GetCredentials()
	return ((username is not None) and (username != "") and (password is not None) and (password != ""))
		
def LoadLogin():
	resp = common.YesNoDialog("Authentification!",
							  "Il faut configurer votre login et mot de passe Annatel TV!",
							  "Cliquez sur Yes pour configurer votre login et mot de passe",
							  nolabel="Non",
							  yeslabel="Oui")
	if (resp):
		common.OpenSettings()
	else:
		common.ShowNotification("Authentification!\nMerci d\'entrer votre login et mot de passe Annatel TV", 10, addon=__Addon__)

def GetTVChannels():
	if (IsLoggedIn()):
		username, password = GetCredentials()
		xml_link = URL_XML_FEED % (urllib.quote(username), urllib.quote(password))
		local_xml = os.path.join(__XML__, "annatel.xml")
		doc = common.DownloadBinary(xml_link)
		if (doc is None):
			doc = common.ReadFile(local_xml)
		else:
			common.WriteFile(doc, local_xml)
			common.SetLastModifiedLocal(__XML__)
		
		if (doc is not None):
			response = []
			parsed_doc = parseString(doc)
			for channel in parsed_doc.getElementsByTagName('channel'):
				name = channel.getElementsByTagName('name')[0].childNodes[0].data
				url = channel.getElementsByTagName('url')[0].childNodes[0].data
				logo = channel.getElementsByTagName('logo')[0].childNodes[0].data
				tv_channel = common.TV(url, name, name, tvg_logo=logo)
				response.append(tv_channel)
			
			return response
		else:
			return None
	else:
		return None


def IsOldEPG():
	modified = common.GetLastModifiedLocal(__EPG__)
	if (modified is not None):
		today = datetime.now()
		return ((today - modified).days > 1)
	else:
		return True
		
def GetEPG():
	epg_xml = common.ReadGzUrl(URL_EPG_FEED)
	local_epg = os.path.join(__EPG__, "tvguide.xml")
	if (epg_xml is not None):
		common.WriteFile(epg_xml, local_epg)
		common.SetLastModifiedLocal(__EPG__)
	else:
		epg_xml = common.ReadFile(local_epg)
	
	epg_file = os.path.join(__AddonDataPath__, 'epg.xml')
	if (epg_xml is not None):
		common.DeleteFile(epg_file)
		common.WriteFile(epg_xml, epg_file)
		return True
	else:
		return None
