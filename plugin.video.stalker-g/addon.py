# -*- coding: utf-8 -*-
import sys
import os
import json
import urllib
import urllib2
import urlparse
import xbmcaddon
import xbmcgui
import xbmcplugin
import hashlib
import re
import time
import string
import config
import load_channels
import server
from xml.dom import minidom
from xml.sax.saxutils import escape
import xml.etree.ElementTree as ET

addon = xbmcaddon.Addon()
addonname = addon.getAddonInfo('name')
addondir = xbmc.translatePath(addon.getAddonInfo('profile')).replace('\\', '/')
addondir2 = addondir.replace('userdata/addon_data', 'addons')
homedir = addondir.split('/addon_data')[0]
plugin_name = addondir2.split('Kodi/addons/')[-1]

base_url = sys.argv[0]
addon_handle = int(sys.argv[1])
args = urlparse.parse_qs((sys.argv[2])[1:])
go = True

xbmcplugin.setContent(addon_handle, 'movies')

version = xbmc.getInfoLabel('System.BuildVersion')
version = version.split()


def alert(msg):
    __addon__ = xbmcaddon.Addon()
    __addonname__ = __addon__.getAddonInfo('name')
    xbmcgui.Dialog().ok(__addonname__, msg)


def addPortal(portal):

    if portal['url'] == '':
        return

    url = build_url({'mode': 'genres', 'portal': json.dumps(portal)})

    cmd = 'XBMC.RunPlugin(' + base_url + '?mode=cache&stalker_url=' \
        + portal['url'] + ')'

    li = xbmcgui.ListItem(portal['name'], iconImage='DefaultProgram.png'
                          )
    li.addContextMenuItems([('Clear Cache', cmd)])

    xbmcplugin.addDirectoryItem(handle=addon_handle, url=url,
                                listitem=li, isFolder=True)


def build_url(query):
    return base_url + '?' + urllib.urlencode(query)


def homeLevel():
    global portal_1, portal_2, portal_3, go

    portal = [portal_1, portal_2, portal_3]

    if go:
        for i in range(1, 4):
            if portal[i - 1]['active']:
                addPortal(portal[i - 1])

        xbmcplugin.endOfDirectory(addon_handle)



def genreLevel():

    global genre_list

    url = build_url({
        'mode': 'vod',
        'genre_name': 'VoD',
        'portal': json.dumps(portal),
        })

    li = xbmcgui.ListItem('[ VoD ]', iconImage='DefaultVideo.png')
    xbmcplugin.addDirectoryItem(handle=addon_handle, url=url,
                                listitem=li, isFolder=True)

    try:
        data = load_channels.getGenres(
            portal['mac'],
            portal['url'],
            portal['serial'],
            portal['login'],
            portal['password'],
            addondir,
            )
    except Exception, e:

        xbmcgui.Dialog().notification(addonname, str(e),
                xbmcgui.NOTIFICATION_ERROR)

        return

    data = data['genres']
    genre_list = data

    for (id, i) in data.iteritems():

        title = i['title']

        url = build_url({
            'mode': 'channels',
            'genre_id': id,
            'genre_name': title.title(),
            'portal': json.dumps(portal),
            })

        genre_name = title.title()    
        censored_genre = (i['censored']=="1")
        adult_ok = portal['parental'] == 'true'

        if censored_genre:
            iconImage = 'OverlayLocked.png'
        else:
            iconImage = 'DefaultVideo.png'

        if not censored_genre or (censored_genre and adult_ok):
            li = xbmcgui.ListItem(title, iconImage=iconImage)
            xbmcplugin.addDirectoryItem(handle=addon_handle, url=url,
                                    listitem=li, isFolder=True)

    xbmcplugin.addSortMethod(addon_handle, xbmcplugin.SORT_METHOD_LABEL)
    xbmcplugin.endOfDirectory(addon_handle)

def vodCategory():
    try:
        data = load_channels.getVoDCategories(
            portal['mac'],
            portal['url'],
            portal['serial'],
            portal['login'],
            portal['password'],
            addondir,
            )
    except Exception, e:
        alert('VOD ERROR:\n' + str(e))
        return


    data = data['categories']

    for (id, i) in data.iteritems():
        title = i['title']
        url = build_url({
            'mode': 'vodlist',
            'cat_id': id,
            'cat_name': title.title(),
            'startpg' : '1',
            'portal': json.dumps(portal),
            })
        iconImage = 'DefaultVideo.png'

        li = xbmcgui.ListItem(title, iconImage=iconImage)
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=url,
                                    listitem=li, isFolder=True)

    xbmcplugin.addSortMethod(addon_handle, xbmcplugin.SORT_METHOD_LABEL)
    xbmcplugin.endOfDirectory(addon_handle)

def vodLevel():

    startpg = args.get('startpg', None)
    try:
        data = load_channels.getVoD(
            portal['mac'],
            portal['url'],
            portal['serial'],
            portal['login'],
            portal['password'],
            portal['vodpages'],
            startpg,
            addondir,
            )
    except Exception, e:

        alert('VOD ERROR:\n' + str(e))
        return

    nextpg = data['next_page']
    data = data['vod']
    cat_id_main = args.get('cat_id', None)
    cat_id_main = cat_id_main[0]
    cat_title = args.get('cat_name',None)
    cat_title = cat_title[0]


    for i in data:
        name = i['name']
        cmd = i['cmd']
        logo = i['logo']
        cat_id = i['cat_id']
        year = i['year']
        genre = i['genres'].split(',')[0]
        if cat_id != cat_id_main and cat_id_main !='*':
            continue
        runtime = i['runtime']
        if runtime and version[0] >= '16':
            runtime = str(int(runtime) * 60)
        logo_url = (portal['url'] + logo if logo else 'DefaultVideo.png')
        try:
            title = name.encode('utf-8')
        except Exception, e:
            title = name
        try:
            cmd2 = cmd.encode('utf-8')
        except Exception, e:
            cmd2 = cmd
        url = build_url({
            'mode': 'play',
            'cmd': cmd2,
            'tmp': '0',
            'title': title,
            'genre_name': 'VoD',
            'logo_url': logo_url,
            'portal': json.dumps(portal),
            })
        li = xbmcgui.ListItem(name, iconImage=logo_url,thumbnailImage=logo_url)
        li.setInfo(type='Video', infoLabels={
            'Genre': i['genres'],
            'Title': name,
            'Year': year,
            'Director': i['direct'],
            'Mpaa': i['mpaa'],
            'Duration': runtime,
            'Rating': i['rating'],
            'votes': i['voters'],
            'Country': i['country'],
            'Cast': i['cast'].split(', '),
            'Plot': i['plot'],
            })
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=url,listitem=li)

    if nextpg != '':
        url = build_url({
            'mode': 'vodlist',
            'cat_id': cat_id_main,
            'cat_name': cat_title,
            'startpg' : nextpg,
            'portal': json.dumps(portal),
            })
        iconImage = 'DefaultVideo.png'

        li = xbmcgui.ListItem('Load More ...', iconImage=iconImage)
        xbmcplugin.addDirectoryItem(handle=addon_handle, url=url,listitem=li, isFolder=True)

    xbmcplugin.addSortMethod(addon_handle, xbmcplugin.SORT_METHOD_UNSORTED)
    xbmcplugin.addSortMethod(addon_handle, xbmcplugin.SORT_METHOD_TITLE)
    xbmcplugin.addSortMethod(addon_handle, xbmcplugin.SORT_METHOD_GENRE)
    xbmcplugin.addSortMethod(addon_handle, xbmcplugin.SORT_METHOD_COUNTRY)
    xbmcplugin.addSortMethod(addon_handle, xbmcplugin.SORT_METHOD_VIDEO_YEAR)
    xbmcplugin.addSortMethod(addon_handle, xbmcplugin.SORT_METHOD_MPAA_RATING)
    xbmcplugin.endOfDirectory(addon_handle)


def channel_sorted(url, path):

    portalurl = '_'.join(re.findall('[a-zA-Z0-9]+', url))
    portalurl = path + '/' + portalurl

    with open(portalurl) as data_file:
        data = json.load(data_file)

    channels = data['channels']
    c_list = {}

    for i in channels.values():
        id = '%4d' % int(i['number'])
        c_list[id] = load_channels.getKey(channels, i)

    c_number = sorted(c_list)

    return [channels, c_list, c_number]


def channel_marked(channel_list, mark):

    channels = channel_list[0]
    c_list = channel_list[1]
    c_number = channel_list[2]

    list = []

    for number in c_number:
        c_id = c_list[number]
        if mark in channels[c_id]['name']:
            break
        if not c_id in list:
            list.append(c_id)

    return list


def in_string(list, txt, op):

    result = (True if op == 'all' else False)

    for i in list:
        result = (result and i in txt if op == 'all' else result or i
                  in txt)
        if op == 'all':
            if not result:
                break
        else:
            if result:
                break

    return result


def channelLevel():

    global genre_list
    global addondir, homedir, plugin_name

    try:
        genre_list = load_channels.getGenres(
            portal['mac'],
            portal['url'],
            portal['serial'],
            portal['login'],
            portal['password'],
            addondir,
            )
    except Exception, e:

        xbmcgui.Dialog().notification(addonname, str(e),
                xbmcgui.NOTIFICATION_ERROR)

        return

    genre_list = genre_list['genres']

    stop = False

    try:
        data = load_channels.getAllChannels(
            portal['mac'],
            portal['url'],
            portal['serial'],
            portal['login'],
            portal['password'],
            addondir,
            )
    except Exception, e:

        alert('CHANNEL ERROR:\n' + str(e))
        return

    data = data['channels']
    genre_name = args.get('genre_name', None)
    genre_id_main = args.get('genre_id', None)
    genre_id_main = genre_id_main[0]
    censored_genre_id_main = False
    if genre_list[genre_id_main]['censored']=="1":
        censored_genre_id_main = True
    
    adult_ok = portal['parental'] == 'true'

    if censored_genre_id_main and adult_ok:
        result = xbmcgui.Dialog().input('Parental',
                hashlib.md5(portal['ppassword'].encode('utf-8'
                )).hexdigest(), type=xbmcgui.INPUT_PASSWORD,
                option=xbmcgui.PASSWORD_VERIFY)
        if not result:
            stop = True

    if stop == False:
        for i in data.values():

            name = i['name']
            cmd = i['cmd']
            tmp = i['tmp']
            number = i['number']
            genre_id = i['genre_id']
            logo = i['logo']
            
            adult_genre = (genre_list[genre_id]['censored']=="1")
            
            if (adult_genre and not adult_ok):
                continue

            if not (genre_id_main == genre_id or genre_id_main == '*'):
                continue

            logo_url = ('DefaultVideo.png' if not logo else portal['url'
                        ] + '/stalker_portal/misc/logos/320/' + logo)

            try:
                enc_name = name.encode('utf-8')
            except Exception, e:
                enc_name = name

            url = build_url({
                'mode': 'play',
                'cmd': cmd,
                'tmp': tmp,
                'title': enc_name,
                'genre_name': genre_name,
                'logo_url': logo_url,
                'portal': json.dumps(portal),
                })

            li = xbmcgui.ListItem(name, iconImage=logo_url,
                                  thumbnailImage=logo_url)

            li.setInfo(type='Video', infoLabels={'title': name,
                       'count': number})
            xbmcplugin.addDirectoryItem(handle=addon_handle, url=url,
                    listitem=li)

        xbmcplugin.addSortMethod(addon_handle,
                                 xbmcplugin.SORT_METHOD_PLAYLIST_ORDER)
        xbmcplugin.addSortMethod(addon_handle,
                                 xbmcplugin.SORT_METHOD_TITLE)
        xbmcplugin.addSortMethod(addon_handle,
                                 xbmcplugin.SORT_METHOD_PROGRAM_COUNT)

        xbmcplugin.endOfDirectory(addon_handle)


def sortchildrenby(parent, attr, reversed):
    is_reversed = bool(reversed)
    parent[:] = sorted(parent, key=lambda child: child.get(attr),
                       reverse=is_reversed)


def playLevel():

    dp = xbmcgui.DialogProgressBG()
    dp.create('IPTV', 'Loading ...')

    title = args['title'][0]
    cmd = args['cmd'][0]
    tmp = args['tmp'][0]
    genre_name = args['genre_name'][0]
    logo_url = args['logo_url'][0]

    if genre_name == 'VoD':
        tmp = '0'

    try:
        url = load_channels.retriveUrl(
            portal['mac'],
            portal['url'],
            portal['serial'],
            portal['login'],
            portal['password'],
            cmd,
            tmp,
            )
    except Exception, e:

        dp.close()
        alert('PLAY ERROR:\n' + str(e))
        return

    dp.update(80)

    title = title.decode('utf-8')

    title += ' (' + portal['name'] + ')'

    li = xbmcgui.ListItem(title, iconImage='DefaultVideo.png',
                          thumbnailImage=logo_url)
    li.setInfo('video', {'Title': title, 'Genre': genre_name})
    xbmc.Player().play(item=url, listitem=li)

    dp.update(100)

    dp.close()


mode = args.get('mode', None)
portal = args.get('portal', None)

if portal is None:
    portal_1 = config.portalConfig('1')
    portal_2 = config.portalConfig('2')
    portal_3 = config.portalConfig('3')
else:

#  Force outside call to portal_1

    portal = json.loads(portal[0])
    portal_2 = config.portalConfig('2')
    portal_3 = config.portalConfig('3')

    if not (portal['name'] == portal_2['name'] or portal['name']
            == portal_3['name']):
        portal = config.portalConfig('1')

if mode is None:
    homeLevel()
elif mode[0] == 'cache':

    stalker_url = args.get('stalker_url', None)
    stalker_url = stalker_url[0]
    load_channels.clearCache(stalker_url, addondir)
elif mode[0] == 'genres':

    genreLevel()
elif mode[0] == 'vod':
    vodCategory()
elif mode[0] == 'vodlist':
    vodLevel()
#elif mode[0] == 'vod':
#    vodLevel()
elif mode[0] == 'channels':

    channelLevel()
elif mode[0] == 'play':

    playLevel()

elif mode[0] == 'server':

    port = addon.getSetting('server_port')

    action = args.get('action', None)
    action = action[0]

    dp = xbmcgui.DialogProgressBG()
    dp.create('M3U Server', 'Working ...')

    if action == 'start':

        if server.serverOnline():
            xbmcgui.Dialog().notification(addonname,
                    'Server already started.\nPort: ' + str(port),
                    xbmcgui.NOTIFICATION_INFO)
        else:
            server.startServer()
            time.sleep(5)
            if server.serverOnline():
                xbmcgui.Dialog().notification(addonname,
                        'Server started.\nPort: ' + str(port),
                        xbmcgui.NOTIFICATION_INFO)
            else:
                xbmcgui.Dialog().notification(addonname,
                        'Server not started. Wait a minute and try again. '
                        , xbmcgui.NOTIFICATION_ERROR)
    else:

        if server.serverOnline():
            server.stopServer()
            time.sleep(5)
            xbmcgui.Dialog().notification(addonname, 'Server stopped.',
                    xbmcgui.NOTIFICATION_INFO)
        else:
            xbmcgui.Dialog().notification(addonname,
                    'Server is already stopped.',
                    xbmcgui.NOTIFICATION_INFO)

    dp.close()

			