import sys
import os
import json
import urllib
import urlparse
import xbmc
import xbmcaddon
import xbmcgui
import xbmcplugin
import load_channels
import hashlib
import re

addon = xbmcaddon.Addon()
addonname = addon.getAddonInfo('name')
addondir = xbmc.translatePath(addon.getAddonInfo('profile'))

portal_NONE = 'false'


def portalConfig(number):
    global portal_NONE
    global serverid

    serverid = addon.getSetting('portal_server_' + number)
    is_active = serverid != portal_NONE

    portal = {}

    portal['name'] = addon.getSetting('portal_name_' + number)
    portal['active'] = is_active

    if not is_active:
        return portal

    portal['url'] = configUrl(number)
    portal['mac'] = configMac(number)
    portal['serial'] = configSerialNumber(number)
    portal['login'] = configLogin(number)
    portal['password'] = configPassword(number)
    portal['vodpages'] = addon.getSetting('vodpages_' + number)
    portal['grpfilter'] = configGrpFilter(number)

    portal['parental'] = addon.getSetting('parental')
    portal['ppassword'] = addon.getSetting('ppassword')

    return portal

def configUrl(number):
    global serverid

    if serverid == 'true':
        portal_url = addon.getSetting('portal_url_'+number)
        if not 'http' in portal_url:
            portal_url = 'http://' + portal_url
    else:
        portal_url = ''
    return portal_url

def configGrpFilter(number):
    global serverid

    grps = ['{0}'.format(x) for x in range(100)]

    if serverid == 'true':
        grpslist = addon.getSetting('grp_filter_' + number)
        if grpslist != '':
            grps = grpslist.split(',')

    return grps


def configMac(number):
    global serverid
    global go

    portal_mac = {'0': '00:1A:78:',
                  '1': '00:1A:79:'}[addon.getSetting('prefix_'
                                    + number)]
    portal_mac += addon.getSetting('portal_mac_' + number)

    if not (portal_mac == ''
            or re.match('[0-9a-f]{2}([-:])[0-9a-f]{2}(\\1[0-9a-f]{2}){4}$'
            , portal_mac.lower()) != None):
        xbmcgui.Dialog().notification(addonname, 'Custom Mac ' + number
                + ' is Invalid.', xbmcgui.NOTIFICATION_ERROR)
        portal_mac = ''
        go = False

    return portal_mac


def configSerialNumber(number):
    global go

    send_serial = addon.getSetting('send_serial_' + number)
    custom_serial = addon.getSetting('custom_serial_' + number)
    serial_number = addon.getSetting('serial_number_' + number)
    device_id = addon.getSetting('device_id_' + number)
    device_id2 = addon.getSetting('device_id2_' + number)
    signature = addon.getSetting('signature_' + number)

    if send_serial != 'true':
        return {'send_serial': False}

    if send_serial == 'true' and custom_serial == 'false':
        return {'send_serial': True, 'custom': False}
    elif send_serial == 'true' and custom_serial == 'true':

# ........if serial_number == '' or device_id == '' or device_id2 == '' or signature == '':
# ............xbmcgui.Dialog().notification(addonname, 'Serial information is invalid.', xbmcgui.NOTIFICATION_ERROR );
# ............go=False;
# ............return None;

        return {
            'send_serial': True,
            'custom': True,
            'sn': serial_number,
            'device_id': device_id,
            'device_id2': device_id2,
            'signature': signature,
            }

    return None


def configLogin(number):
    global go

    login = addon.getSetting('login_' + number)
    if login == '':
        xbmcgui.Dialog().notification(addonname, 'login' + number
                + ' is invalid.', xbmcgui.NOTIFICATION_ERROR)
        go = False
        return None

    return login


def configPassword(number):
    global go

    password = addon.getSetting('password_' + number)
    if password == '':
        xbmcgui.Dialog().notification(addonname, 'password' + number
                + ' is invalid.', xbmcgui.NOTIFICATION_ERROR)
        go = False
        return None

    return password



			