import xbmcplugin,xbmcaddon
import time
import datetime
import xbmc
import os
import base64
import urllib2,urllib,json,re
import zipfile
import resources.lib.utils as utils
from resources.lib.croniter import croniter
from collections import namedtuple
from shutil import copyfile
import xml.etree.ElementTree as ET
import traceback
import json

__addon__ = xbmcaddon.Addon()
__author__ = __addon__.getAddonInfo('author')
__scriptid__ = __addon__.getAddonInfo('id')
__scriptname__ = __addon__.getAddonInfo('name')
__cwd__ = __addon__.getAddonInfo('path')
__version__ = __addon__.getAddonInfo('version')
__language__ = __addon__.getLocalizedString
debug = __addon__.getSetting("debug")
offset1hr = __addon__.getSetting("offset1hr")

class epgUpdater:
    def __init__(self):
        self.monitor = UpdateMonitor(update_method = self.settingsChanged)
        self.enabled = utils.getSetting("enable_scheduler")
        self.next_run = 0
        self.update_m3u = False
        updater_path = os.path.join(xbmc.translatePath('special://userdata'), 'addon_data/service.stalker2simple')
        if not os.path.isdir(updater_path):
          try:
            os.mkdir(updater_path)
          except:
            pass

        try:
          self.Stalker_addon = xbmcaddon.Addon('plugin.video.stalker-g')
          utils.setSetting("pluginmissing", "false")
        except:
          utils.log("Stalker To PVR Simple: Failed to find stalker lite addon")
          self.Stalker_addon = None
          utils.setSetting("pluginmissing", "true")
        try:
          self.pvriptvsimple_addon = xbmcaddon.Addon('pvr.iptvsimple')
        except:
          utils.log("Stalker To PVR Simple: Failed to find pvr.iptvsimple addon")
          self.pvriptvsimple_addon = None

    def run(self):
        utils.log("Stalker To PVR Simple Settings::scheduler enabled, finding next run time")

        # Update when starting
        self.updateGroups()
        self.updateM3u()
        if self.enabled:
          self.updateEpg()

        self.findNextRun(time.time())
        while(not xbmc.abortRequested):
            # Sleep/wait for abort for 10 seconds
            now = time.time()
            if(self.enabled):
              if(self.next_run <= now):
                  self.updateEpg()
                  self.findNextRun(now)
              else:
                  self.findNextRun(now)
              if(self.update_m3u):
                  self.updateM3u()
                  self.update_m3u = False
            xbmc.sleep(500)
        # del self.monitor

    def updateGroups(self):
        group_list=utils.getSetting('group_list')
        self.groups = group_list.split(",")

    def installKeyboardFile(self):
      keyboard_file_path = os.path.join(xbmc.translatePath('special://home'), 'addons/service.stalker2simple/keyboard.xml')
      if os.path.isfile(keyboard_file_path):
        utils.log("Stalker To PVR Simple: Keyboard file found.  Copying...")
        copyfile(keyboard_file_path, os.path.join(xbmc.translatePath('special://userdata'), 'keymaps/keyboard.xml'))

    def settingsChanged(self):
        utils.log("Stalker To PVR Simple: Settings changed - update")
        old_settings = utils.refreshAddon()
        current_enabled = utils.getSetting("enable_scheduler")
        install_keyboard_file = utils.getSetting("install_keyboard_file")
        if install_keyboard_file == 'true':
          self.installKeyboardFile()
          utils.setSetting('install_keyboard_file', 'false')
          # Return since this is going to be run immediately again
          return
        
        # Update m3u file if wanted groups has changed
        old_groups = self.groups
        self.updateGroups()
        if self.groups != old_groups:
          self.update_m3u = True

        if old_settings.getSetting("timezone") != utils.getSetting("timezone"):
          if self.pvriptvsimple_addon:
            utils.log("Stalker To PVR Simple: Changing offset")
            self.checkAndUpdatePVRIPTVSetting("epgTimeShift", utils.getSetting("timezone"))

        if(self.enabled == "true"):
            #always recheck the next run time after an update
            utils.log('Stalker To PVR Simple: Recalculate start time , after settings update')
            self.findNextRun(time.time())

    def parseSchedule(self):
        schedule_type = int(utils.getSetting("schedule_interval"))
        cron_exp = utils.getSetting("cron_schedule")

        hour_of_day = utils.getSetting("schedule_time")
        hour_of_day = int(hour_of_day[0:2])
        if(schedule_type == 0 or schedule_type == 1):
            #every day
            cron_exp = "0 " + str(hour_of_day) + " * * *"
        elif(schedule_type == 2):
            #once a week
            day_of_week = utils.getSetting("day_of_week")
            cron_exp = "0 " + str(hour_of_day) + " * * " + day_of_week
        elif(schedule_type == 3):
            #first day of month
            cron_exp = "0 " + str(hour_of_day) + " 1 * *"

        return cron_exp


    def findNextRun(self,now):
        #find the cron expression and get the next run time
        cron_exp = self.parseSchedule()
        cron_ob = croniter(cron_exp,datetime.datetime.fromtimestamp(now))
        new_run_time = cron_ob.get_next(float)
        if(new_run_time != self.next_run):
            self.next_run = new_run_time
            utils.showNotification('Stalker To PVR Simple EPG Updater', 'Next Update: ' + datetime.datetime.fromtimestamp(self.next_run).strftime('%m-%d-%Y %H:%M'))
            utils.log("Stalker To PVR Simple: scheduler will run again on " + datetime.datetime.fromtimestamp(self.next_run).strftime('%m-%d-%Y %H:%M'))

    def updateM3u(self):
        updater_path = os.path.join(xbmc.translatePath('special://userdata'), 'addon_data/service.stalker2simple')
        if self.Stalker_addon is None:
            utils.log("Stalker To PVR Simple: Stalker addon missing")
            return
        else:
            stalkerpath = os.path.join(xbmc.translatePath('special://userdata'), 'addon_data/plugin.video.stalker-g')
            portalnum = utils.getSetting("portalnum")
            url = self.Stalker_addon.getSetting('portal_url_'+portalnum)
            if not 'http' in url:
                url = 'http://' + url
            portalurl = '_'.join(re.findall('[a-zA-Z0-9]+', url))
            channelurl = stalkerpath + '/' + portalurl
            genresurl = stalkerpath + '/' + portalurl + '-genres'    
            host_ip = 'localhost'
            host_port = str(self.Stalker_addon.getSetting('server_port'))
            host_addr = 'http://' + host_ip + ':' + host_port
        if self.pvriptvsimple_addon is None:
            utils.log("Stalker To PVR Simple: pvriptvsimple addon missing")
            return

        self.checkAndUpdatePVRIPTVSetting("epgCache", "false")
        self.checkAndUpdatePVRIPTVSetting("epgPathType", "0")
        self.checkAndUpdatePVRIPTVSetting("epgPath", updater_path + '/Stalkerepg.xml.gz')
        self.checkAndUpdatePVRIPTVSetting("m3uPathType", "0")
        self.checkAndUpdatePVRIPTVSetting("m3uPath", "{0}/Stalker.m3u".format(updater_path))
        utils.log("Stalker To PVR Simple: Updating m3u file")

        correctepg = {}
        if utils.getSetting('correctepg')=="true":
            try:
                correcturl=utils.getSetting('correcturl')
                correctfile = urllib2.urlopen(correcturl)
                correctepg = json.loads(correctfile.read())
            except Exception as e:
                utils.log("Stalker To PVR Simple: Error retrieving epg correction.\n{0}\n{1}".format(e, traceback.format_exc()))
                return
        
        category_ids = {}
        try:
            genrefile=open(genresurl,"r")
            genresjson=json.loads(genrefile.read())
            for i in genresjson['genres']:
                category_idr = i
                category_title = genresjson['genres'][i]['title']
                category_ids[category_title] = category_idr
        except Exception as e:
            utils.log("Stalker To PVR Simple: Error retrieving categories.\n{0}\n{1}".format(e, traceback.format_exc()))
            return

        Channel = namedtuple('Channel', ['tvg_id', 'tvg_name', 'tvg_logo', 'group_title', 'channel_url'])
        channels = []

        chfilter = (utils.getSetting('excludech')=="true")
        chfilregex = utils.getSetting('excluderegex')

        group_idx = {}
        for idx,group in enumerate(self.groups):
             group_idx[group] = idx

        try:    
            channelfile=open(channelurl,"r")
            channeljson=json.loads(channelfile.read())
            allchannels = channeljson['channels']
            
            for category in category_ids:
              if category in self.groups:
                for ch in allchannels:
                    eachchannel = allchannels[ch]
                    if eachchannel['genre_title'] == category:
                        chname = eachchannel['name']
                        chcmd = eachchannel['cmd']
                        chtmp = eachchannel['tmp']
                        chnum = eachchannel['number']
                        chlogo = eachchannel['logo']
                        
                        if chlogo != '':
                            chlogo = url + '/stalker_portal/misc/logos/320/' + chlogo
                        
                        parameters = urllib.urlencode({'channel': chcmd,'tmp': chtmp, 'portal': portalnum})
                        
                        churl = host_addr + '/live.m3u?'+ parameters
                        
                        tvgid = '{0}'.format(chnum)
                        if ch in correctepg:
                            tvgid = '{0}'.format(correctepg[ch])
                        
                        tvglogo = '{0}'.format(chlogo)
                          
                        name = '{0}'.format(chname.encode('utf8'))
                        name = name.replace("&lt;", "<")
                        name = name.replace("&gt;", ">")
                        name = name.replace("&amp;", "&")
                        
                        if chfilter:
                            searchObj = re.search(chfilregex, name)
                            if searchObj == None:
                                channels.append(Channel(tvgid,name,tvglogo,category,churl))
                        else:
                            channels.append(Channel(tvgid,name,tvglogo,category,churl))
        except Exception as e:
            utils.log("Stalker To PVR Simple: Error retrieving channels.\n{0}\n{1}".format(e, traceback.format_exc()))
            return

        wanted_channels = channels
        wanted_channels.sort(key=lambda c: "{0}-{1}".format(group_idx[c.group_title], c.tvg_id))

        try:
          with open("{0}/Stalker.m3u".format(updater_path), "w") as m3u_f:
            m3u_f.write("#EXTM3U\n")
            for c in wanted_channels:
              m3u_f.write('#EXTINF:-1 tvg-name="{0}" tvg-id="{1}" tvg-logo="{2}" group-title="{3}",{0}\n{4}\n'.format(c.tvg_name, c.tvg_id, c.tvg_logo, c.group_title, c.channel_url))
            if utils.getSetting("mergem3u") == "true":
              mergem3u_fn = utils.getSetting("mergem3u_fn")
              if os.path.isfile(mergem3u_fn):
                with open(mergem3u_fn) as mergem3u_f:
                  for line in mergem3u_f:
                    if line.startswith("#EXTM3U"):
                      continue
                    m3u_f.write(line)
        except Exception as e:
          utils.log("Stalker To PVR Simple: Error creating m3u file\n{0}\n{1}".format(e,traceback.format_exc()))


    def checkAndUpdatePVRIPTVSetting(self, setting, value):
      if self.pvriptvsimple_addon.getSetting(setting) != value:
        self.pvriptvsimple_addon.setSetting(setting, value)

    def updateEpg(self):
        url2xmltv = utils.getSetting("xmltv_url")    
        epgFileName = 'Stalkerepg.xml.gz'
        epgFile = None
        updater_path = os.path.join(xbmc.translatePath('special://userdata'), 'addon_data/service.stalker2simple')
        iptvsimple_path = os.path.join(xbmc.translatePath('special://userdata'), 'addon_data/pvr.iptvsimple')

        try:
            response = urllib2.urlopen(url2xmltv)
            epgFile = response.read()
        except Exception as e:
            utils.log('Stalker To PVR Simple Settings: Guide download failed.')
            utils.log('{0}\n{1}'.format(e, traceback.format_exc()))
            return

        if epgFile:
            epgFH = open(updater_path + '/'+epgFileName, "wb")
            epgFH.write(epgFile)
            epgFH.close()

        genresFile = None
        try:
            response = urllib2.urlopen('https://raw.githubusercontent.com/littlestoneiptv/iptvsubs2pvriptvsimple3/master/genres.xml')
            genresFile = response.read()
        except Exception as e:
            utils.log('Stalker To PVR Simple Settings: Genres download failed.')
            utils.log('{0}\n{1}'.format(e, traceback.format_exc()))
            return

        if genresFile:
            genresFH = open(iptvsimple_path + '/genres.xml', "w")
            genresFH.write(genresFile)
            genresFH.close()
        utils.log("Stalker To PVR Simple: EPG updated")

class UpdateMonitor(xbmc.Monitor):
    update_method = None

    def __init__(self,*args, **kwargs):
        xbmc.Monitor.__init__(self)
        self.update_method = kwargs['update_method']

    def onSettingsChanged(self):
        self.update_method()

if __name__ == "__main__":
  epg_updater = epgUpdater()
  epg_updater.run()
