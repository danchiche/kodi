# -*- coding: utf-8 -*- 

import xbmc, xbmcaddon, xbmcgui, xbmcplugin
import sys, os, urllib
import common
from xml.dom.minidom import parseString
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta

URL_XML_FEED = 'http://www.annatel.tv/api/getchannels?login=%s&password=%s'
URL_EPG_FEED = 'http://racacaxtv.ga/xmltv/xmltv.xml.gz'
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
	
	if (epg_xml is not None):
		epgFile = os.path.join(__AddonDataPath__, 'epg.xml')
		return ParseMakeEPG(epg_xml, epgFile)
	else:
		return None

def ParseMakeEPG(epg_xml, epgFile):
	common.DeleteFile(epgFile)
	pFile = common.OpenFileForAppend(epgFile)
	
	current_tz_diff = common.GetTimezoneDifferenceMinutes()
	xml_list = []
	xml_list.append('<?xml version="1.0" encoding="utf-8" ?>')
	xml_list.append("<tv>")
	common.AppendFile('\n'.join(xml_list), pFile)
	xml_list = []
	epg = None
	if (epg_xml is not None):
		parsed_epg = ET.fromstring(epg_xml)
		epg = common.EPG()
		for channel in parsed_epg.findall('channel'):
			channel_id = channel.get("id").encode("utf-8")
			display_name = channel.find('display-name').text.encode("utf-8")
			channel_id_fixed = FixEPGChannelsID(channel_id)
			channel_id_duplicate_fixed = FixEPGChannelsDuplicateID(channel_id)
			if (channel_id_fixed is not None):
				xml_list.append('<channel id="%s">%s</channel>' % (channel_id_fixed, channel_id_fixed))
			if (channel_id_duplicate_fixed is not None):
				xml_list.append('<channel id="%s">%s</channel>' % (channel_id_duplicate_fixed, channel_id_duplicate_fixed))
			common.AppendFile('\n'.join(xml_list), pFile)
			xml_list = []
		
		current_channel = None
		for program in parsed_epg.findall('programme'):
			start = common.ParseEPGTimeUTC(program.get("start").encode("utf-8"))
			stop = common.ParseEPGTimeUTC(program.get("stop").encode("utf-8"))
			try:		title = program.find('title').text.encode("utf-8")
			except:		title = None
			
			#try:		subtitle = program.find('sub-title').text.encode("utf-8")
			#except:		subtitle = None
			
			try:		description = program.find('desc').text.encode("utf-8")
			except:		description = None
			
			#try:		aspect_ratio = program.find("aspect").text.encode("utf-8")
			#except:		aspect_ratio = None
			
			#try:		star_rating = program.find("star-rating")[0].text.encode("utf-8") # <star-rating><value>2/5</value></star-rating>
			#except:		star_rating = None
			
			#credits = []
			#try:			
			#	for credit in program.find('credits'):
			#		job = credit.tag.encode("utf-8")
			#		name = credit.text.encode("utf-8")
			#		credits.append({job:name})
			#except:
			#	pass
			
			try:
				categoryNode = program.find('category')
				category = categoryNode.text.encode("utf-8")
				category_lang = categoryNode.get("lang").encode("utf-8")
			except:
				category = None
				category_lang = None
			
			#try:
			#	lengthNode = program.find('length')
			#	length = lengthNode.text.encode("utf-8")
			#	length_units = lengthNode.get("units").encode("utf-8")
			#except:
			#	length = None
			#	length_units = None
			
			try:
				icon_node = program.find('icon')
				program_icon = icon_node.get("src").encode("utf-8")
			except:
				program_icon = None
			
			program_epg = common.Program(start, stop, title)
			#program_epg.subtitle = subtitle
			program_epg.description = description
			#program_epg.credits = credits
			program_epg.category = category
			program_epg.category_lang = category_lang
			#program_epg.length = length
			#program_epg.length_units = length_units
			#program_epg.aspect_ratio = aspect_ratio
			#program_epg.star_rating = star_rating
			program_epg.icon = program_icon
			
			channel_id = program.get("channel").encode("utf-8")
			
			#Make			
			channel_id_fixed = FixEPGChannelsID(channel_id)
			if (channel_id_fixed is not None):
				xml_list.append('<programme start="%s" stop="%s" channel="%s">' % (common.FormatEPGTime(program_epg.start, current_tz_diff), common.FormatEPGTime(program_epg.stop, current_tz_diff), channel_id_fixed))
				xml_list.append('<title>%s</title>' % program_epg.title)

				if (program_epg.subtitle is not None):
					xml_list.append('<sub-title>%s</sub-title>' % program_epg.subtitle)
				if (program_epg.description is not None):
					xml_list.append('<desc>%s</desc>' % program_epg.description)
				if (program_epg.category is not None):
					xml_list.append('<category')
					if (program_epg.category_lang is not None):
						xml_list.append(' lang="%s"' % program_epg.category_lang)
					xml_list.append('>%s</category>' % program_epg.category)

				if ((program_epg.credits is not None) and (len(program_epg.credits) > 0)):
					xml_list.append('<credits>')
					for credit in program_epg.credits:
						job = credit.keys()[0]
						name = credit.values()[0]
						xml_list.append('<%s>%s</%s>' % (job, name, job))
					xml_list.append('</credits>')

				if ((program_epg.length is not None) and (program_epg.length_units is not None)):
					xml_list.append('<length units="%s">%s</length>' % (program_epg.length_units, program_epg.length))
				if (program_epg.aspect_ratio is not None):
					xml_list.append('<video><aspect>%s</aspect></video>' % program_epg.aspect_ratio)
				if (program_epg.star_rating is not None):
					xml_list.append('<star-rating><value>%s</value></star-rating>' % program_epg.star_rating)
				if (program_epg.icon is not None):
					xml_list.append('<icon src="%s" />' % program_epg.icon)

				xml_list.append('</programme>')
			
			#Make Duplicate			
			channel_id_duplicate_fixed = FixEPGChannelsDuplicateID(channel_id)
			if (channel_id_duplicate_fixed is not None):
				xml_list.append('<programme start="%s" stop="%s" channel="%s">' % (common.FormatEPGTime(program_epg.start, current_tz_diff), common.FormatEPGTime(program_epg.stop, current_tz_diff), channel_id_duplicate_fixed))
				xml_list.append('<title>%s</title>' % program_epg.title)

				if (program_epg.subtitle is not None):
					xml_list.append('<sub-title>%s</sub-title>' % program_epg.subtitle)
				if (program_epg.description is not None):
					xml_list.append('<desc>%s</desc>' % program_epg.description)
				if (program_epg.category is not None):
					xml_list.append('<category')
					if (program_epg.category_lang is not None):
						xml_list.append(' lang="%s"' % program_epg.category_lang)
					xml_list.append('>%s</category>' % program_epg.category)

				if ((program_epg.credits is not None) and (len(program_epg.credits) > 0)):
					xml_list.append('<credits>')
					for credit in program_epg.credits:
						job = credit.keys()[0]
						name = credit.values()[0]
						xml_list.append('<%s>%s</%s>' % (job, name, job))
					xml_list.append('</credits>')

				if ((program_epg.length is not None) and (program_epg.length_units is not None)):
					xml_list.append('<length units="%s">%s</length>' % (program_epg.length_units, program_epg.length))
				if (program_epg.aspect_ratio is not None):
					xml_list.append('<video><aspect>%s</aspect></video>' % program_epg.aspect_ratio)
				if (program_epg.star_rating is not None):
					xml_list.append('<star-rating><value>%s</value></star-rating>' % program_epg.star_rating)
				if (program_epg.icon is not None):
					xml_list.append('<icon src="%s" />' % program_epg.icon)

				xml_list.append('</programme>')
				
			common.AppendFile('\n'.join(xml_list), pFile)
			xml_list = []
	
	xml_list.append("</tv>")
	common.AppendFile('\n'.join(xml_list), pFile)
	xml_list = []
	common.CloseFile(pFile)
	return True

def FixEPGChannelsID(channel_id):
	if (channel_id is not None):
		ids = {
			"TF1"									:	"TF1",
			"France 2"								:	"France_2",
			"France 3"								:	"France_3",
			"Canal+"								:	"Canal_+",
			"France 5"								:	"France_5",
			"M6"									:	"M6",
			"Arte"									:	"Arte",
			"C8"									:	"C8",
			"W9"									:	"W9",
			"TMC"									:	"TMC",
			"NT1"									:	"NT1",
			"NRJ 12"								:	"NRJ_12",
			"France 4"								:	"France_4",
			"BFM TV"								:	"BFM_TV",
			"CNews"									:	"CNews",
			"CStar"									:	"CStar",
			"Gulli"									:	"Gulli",
			"RMC Découverte"						:	"RMC_Decouverte",
			"Canal+Cinéma"							:	"Canal+_Cinema",
			"Canal+Family"							:	"Canal+_Family",
			"Canal+Décalé"							:	"Canal_Decale",
			"Canal+Sport"							:	"Canal+_Sport_HD",
			"Ciné+Famiz"							:	"Cine+_Famiz",
			"Ciné+Frisson"							:	"Cine+_Frisson",
			"SFR Sport 1"							:	"SFR_Sport_1",
			"SFR Sport 2"							:	"SFR_Sport_2",
			"SFR Sport 3"							:	"SFR_Sport_3",
			"Ciné+Premier"							:	"Cine+_Premier",
			"Comédie+"								:	"Comedie+",
			"Disney Channel"						:	"Disney_Channel",
			"Disn Cine HD"							:	"Disney_Cinema",
			"Equidia Live"							:	"Equidia",
			"Euronews F"							:	"EuroNews",
			"Eurosport France"						:	"EuroSport",
			"Eurosport 2 France"					:	"EuroSport2",
			"Infosport+"							:	"InfoSport",
			"Planète+"								:	"Planete+",
			"L'Equipe"								:	"Equipe_21",
			"France_O"								:	"France_O",
			"National Geographic Channel France"	:	"National_Geo",
			"Nickelodéon Junior France"				:	"NickJr_France",
			"Paris Première"						:	"Paris_Première",
			"Disney Junior"							:	"Disney_Junior",
			"RTL9"									:	"RTL9",
			"Téva"									:	"Teva",
			"France 24"								:	"France_24",
			"Canal+ Séries"							:	"Canal+_Series",
			"beIN SPORTS 1"							:	"BeIN_Sport_1_HD",
			"beIN SPORTS 2"							:	"BeIN_Sport_2_HD",
			"beIN SPORTS 3"							:	"BeIN_Sport_3_HD"
		}
		if (channel_id in ids):
			return ids[channel_id]
	
	return None

def FixEPGChannelsDuplicateID(channel_id):
	if (channel_id is not None):
		ids = {
			"Canal+Sport"							:	"Canal+_Sport",
			"beIN SPORTS 1"							:	"BeIN_Sport_1",
			"beIN SPORTS 2"							:	"BeIN_Sport_2",
			"TF1"									:	"TF1_HD",
			"France 2"								:	"France_2_HD",
			"Canal+"								:	"Canal+_HD",
			"M6"									:	"M6_HD"
		}
		if (channel_id in ids):
			return ids[channel_id]
	
	return None

