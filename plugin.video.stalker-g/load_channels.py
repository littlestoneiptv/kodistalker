import sys
import urllib
import json
import os
import urlparse
import re
import uuid
import time as time2
from time import time
from time import gmtime, strftime
from datetime import datetime
import datetime as datetime2
import math
import urllib2
import hashlib
from xml.dom import minidom
import xml.parsers.expat
import sys
from zipfile import ZipFile

import xbmcaddon
import xbmcgui
import xbmc

import socket

key = None
mac = ':'.join(re.findall('..', '%012x' % uuid.getnode()))
sn = None
device_id = None
device_id2 = None
signature = None
login = None
password = None

cache_version = '5'

addon = xbmcaddon.Addon()
addonname = addon.getAddonInfo('name')
userdir = xbmc.translatePath(addon.getAddonInfo('profile')).replace('\\'
        , '/')
homedir = userdir.split('/addon_data')[0]
addondir = userdir.replace('userdata/addon_data', 'addons')
extdir = addondir + 'resources/external'


def alert(msg):
    __addon__ = xbmcaddon.Addon()
    __addonname__ = __addon__.getAddonInfo('name')
    xbmcgui.Dialog().ok(__addonname__, msg)


def local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(('8.8.8.8', 80))
    ip = s.getsockname()[0]
    s.close()
    return ip


host_ip = local_ip()
host_port = addon.getSetting('server_port')
host_addr = 'http://' + host_ip + ':' + host_port


def is_json(myjson):
    try:
        json_object = json.loads(myjson)
    except ValueError, e:
        return False
    return True


def setMac(nmac):
    global mac

    if re.match('[0-9a-f]{2}([-:])[0-9a-f]{2}(\\1[0-9a-f]{2}){4}$',
                nmac.lower()):
        mac = nmac


def setLogin(llogin, ppass):
    global login, password

    login = llogin
    password = ppass


def setSerialNumber(serial):
    global sn, device_id, device_id2, signature, mac, login

    if serial['send_serial'] == False:
        return

    if serial['custom'] == False:

        sn = hashlib.md5(mac).hexdigest().upper()[13:]
        device_id = hashlib.sha256(sn).hexdigest().upper()
        device_id2 = hashlib.sha256(mac).hexdigest().upper()
        signature = hashlib.sha256(sn + mac).hexdigest().upper()
    elif serial['custom'] == True:

        sn = serial['sn']
        device_id = serial['device_id']
        device_id2 = serial['device_id2']
        signature = serial['signature']


def handshake(url):
    global key
    global server_url

    server_url = url

    values = {'type': 'stb', 'action': 'handshake',
              'JsHttpRequest': '1-xml'}

    info = retrieveData(url, values)

    key = info['js']['token']

    return


def getProfile(url):
    global sn, device_id, device_id2, signature
    global key
    global is_synced

    values = {
        'type': 'stb',
        'action': 'get_profile',
        'hd': '1',
        'ver': 'ImageDescription%3a%200.2.16-250%3b%20ImageDate%3a%2018%20Mar%202013%2019%3a56%3a53%20GMT%2b0200%3b%20PORTAL%20version%3a%204.9.9%3b%20API%20Version%3a%20JS%20API%20version%3a%20328%3b%20STB%20API%20version%3a%20134%3b%20Player%20Engine%20version%3a%200x566',
        'num_banks': '1',
        'stb_type': 'MAG250',
        'image_version': '216',
        'auth_second_step': '1',
        'hw_version': '1.7-BD-00',
        'not_valid_token': '1',
        'JsHttpRequest': '1-xml',
        }

    if sn != None:
        values['sn'] = sn
        values['device_id'] = device_id
        values['device_id2'] = device_id2
        values['signature'] = signature

    info = retrieveData(url, values)

    return info


def getAuth(url):
    global sn, device_id, device_id2, signature
    global key, login, password

    values = {
        'type': 'stb',
        'action': 'do_auth',
        'login': login,
        'password': password,
        'JsHttpRequest': '1-xml',
        }

    if sn != None:
        values['sn'] = sn
        values['device_id'] = device_id
        values['device_id2'] = device_id2
        values['signature'] = signature

    info = retrieveData(url, values)

    return info


def zip_extract(fzip, destDir):

    zz = ZipFile(fzip)
    zz.extractall(destDir)
    fnames = zz.namelist()
    zz.close()

    return fnames


def curl(url, fout):

    (name, hdrs) = urllib.urlretrieve(url, fout)


def url_getContents(src, bytes_max, type):
    url = urllib.urlopen(src)
    data = url.read(bytes_max)
    url.close()
    return (json.loads(data) if type == 'json' else data)


def get_string_all(left, right, source):
    result = re.findall(left + '(.*?)' + right, source)
    return result


def retrieveData(url, values):
    global key, mac, login, password

    url += '/stalker_portal'
    load = '/server/load.php'
    refer = '/c/'
    timezone = 'Etc/UTC'

    user_agent = \
        'Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 4 rev: 1812 Mobile Safari/533.3'

    headers = {  # ........'Connection' : 'Keep-Alive',
        'User-Agent': user_agent,
        'Cookie': 'mac=' + mac + '; stb_lang=en; timezone=' + timezone,
        'Referer': url + refer,
        'Accept-Charset': 'UTF-8,*;q=0.8',
        'X-User-Agent': 'Model: MAG250; Link: WiFi',
        }

    if key:
        headers['Authorization'] = 'Bearer ' + key

    data = urllib.urlencode(values)

    for i in range(0, 3):
        req = urllib2.Request(url + load, data, headers)
        resp = urllib2.urlopen(req).read().decode('utf-8')
        if '"js":[]' not in resp:
            break

# check alternate

    if not is_json(resp):

        req = urllib2.Request(url + load + '?' + data, headers=headers)
        resp = urllib2.urlopen(req).read().decode('utf-8')

    if not is_json(resp):
        raise Exception(resp)

    info = json.loads(resp)

    return info


def getKey(haystack, needle):
    return [k for (k, v) in haystack.iteritems() if v == needle][0]


def getGenres(
    portal_mac,
    url,
    serial,
    portal_login,
    portal_password,
    path,
    ):
    global key, cache_version, login, password

    now = time()
    portalurl = '_'.join(re.findall('[a-zA-Z0-9]+', url))
    portalurl = path + '/' + portalurl + '-genres'

    setMac(portal_mac)
    setLogin(portal_login, portal_password)
    setSerialNumber(serial)

    if not os.path.exists(path):
        os.makedirs(path)

    if os.path.exists(portalurl):

        # check last time

        with open(portalurl) as data_file:
            data = json.load(data_file)

        if 'version' not in data or data['version'] != cache_version:
            clearCache(url, path)
        else:

            time_init = float(data['time'])

            # update 12h

            if (now - time_init) / 3600 < 12:
                return data

    handshake(url)
    getAuth(url)
    getProfile(url)

    values = {'type': 'itv', 'action': 'get_genres',
              'JsHttpRequest': '1-xml'}

    info = retrieveData(url, values)

    results = info['js']

    data = '{ "version" : "' + cache_version + '", "time" : "' \
        + str(now) + '", "genres" : {  \n'

    for i in results:
        alias = i['alias']
        id = i['id']
        title = i['title']
        if 'censored' in i:
            censored = '", "censored":"' + str(i['censored'])
        else:
            censored = ''
        data += '"' + id + '" : {"alias":"' + alias + '", "title":"' \
            + title + censored + '"}, \n'

    data = data[:-3] + '\n}}'

    with open(portalurl, 'w') as f:
        f.write(data.encode('utf-8'))

    return json.loads(data.encode('utf-8'))

def getVoDGenresByAlias(
    portal_mac,
    url,
    serial,
    portal_login,
    portal_password,
    path,
    cat_alias,
    ):
    global key, cache_version

    now = time()
    portalurl = '_'.join(re.findall('[a-zA-Z0-9]+', url))
    vodgenre = '_'.join(re.findall('[a-zA-Z0-9]+', cat_alias))
    if cat_alias == '*':
        vodgenre += 'all'
    portalurl = path + '/' + portalurl + '-vodgenres-' + vodgenre

    setMac(portal_mac)
    setLogin(portal_login, portal_password)
    setSerialNumber(serial)

    if not os.path.exists(path):
        os.makedirs(path)

    if os.path.exists(portalurl):
        # check last time
        with open(portalurl) as data_file:
            data = json.load(data_file)
        if 'version' not in data or data['version'] != cache_version:
            clearCache(url, path)
        else:
                time_init = float(data['time'])
                    # update 12h
                if (now - time_init) / 3600 < 12:
                    return data

    handshake(url)
    getAuth(url)
    getProfile(url) 
    data = {}
    data["version"] = cache_version
    data["time"] = str(now)
    genres = {}
    values = {'type': 'vod', 'action': 'get_genres_by_category_alias','cat_alias':cat_alias,'JsHttpRequest': '1-xml'}
    info = retrieveData(url, values)
    results = info['js']
    for i in results:
        id = i['id']
        title = i['title']
        genres[id] = title
    data[cat_alias] = genres
    datafile = json.dumps(data)
    with open(portalurl, 'w') as f:
        f.write(datafile)
    return data

def getVoDCategories(
    portal_mac,
    url,
    serial,
    portal_login,
    portal_password,
    path,
    ):
    global key, cache_version, login, password

    now = time()
    portalurl = '_'.join(re.findall('[a-zA-Z0-9]+', url))
    portalurlg = path + '/' + portalurl + '-vodgenres-all'
    portalurl = path + '/' + portalurl + '-vodcat'


    if not os.path.exists(path):
        os.makedirs(path)

    if os.path.exists(portalurl):
        # check last time
        with open(portalurl) as data_file:
            data = json.load(data_file)
        if 'version' not in data or data['version'] != cache_version:
            clearCache(url, path)
        else:
                time_init = float(data['time'])
                    # update 12h
                if (now - time_init) / 3600 < 12:
                    return data

    setMac(portal_mac)
    setLogin(portal_login, portal_password)
    setSerialNumber(serial)

    handshake(url)
    getAuth(url)
    getProfile(url)

    values = {'type': 'vod', 'action': 'get_categories','JsHttpRequest': '1-xml'}
    info = retrieveData(url, values)
    results = info['js']
    data = '{ "version" : "' + cache_version + '", "time" : "' + str(now) + '", "categories" : {  \n'
    for i in results:
        alias = i['alias']
        id = i['id']
        title = i['title']
        if 'censored' in i:
            censored = '", "censored":"' + str(i['censored'])
        else:
            censored = ''
        data += '"' + id + '" : {"alias":"' + alias + '", "title":"' + title + censored + '"}, \n'
    data = data[:-3] + '\n}}'
    with open(portalurl, 'w') as f:
        f.write(data.encode('utf-8'))
    # save the genres
    genres = {}
    gvalues = {'type': 'vod', 'action': 'get_genres_by_category_alias','cat_alias':'*','JsHttpRequest': '1-xml'}
    ginfo = retrieveData(url, gvalues)
    gresults = ginfo['js']
    for g in gresults:
        gid = g['id']
        gtitle = g['title']
        genres[gid] = gtitle
    genresfile = json.dumps(genres)
    with open(portalurlg, 'w') as f:
        f.write(genresfile)

    return json.loads(data.encode('utf-8'))

def getVoD(
    portal_mac,
    url,
    serial,
    portal_login,
    portal_password,
    portal_vodpages,
    startpg,
    path,
    ):

    now = time()
    startpage = startpg[0]
    portalurl = '_'.join(re.findall('[a-zA-Z0-9]+', url))
    portalurlg = path + '/' + portalurl + '-vodgenres-all'
    portalurl = path + '/' + portalurl + '-vod-p'+startpage.strip()

    if not os.path.exists(path):
        os.makedirs(path)

    if os.path.exists(portalurl):

        # check last time

        with open(portalurl) as data_file:
            data = json.load(data_file)

        if 'version' not in data or data['version'] != cache_version:
            clearCache(url, path)
        else:
            time_init = float(data['time'])
            # update 168h (7 days)
            if (now - time_init) / 3600 < 168:
                return data


    if os.path.exists(portalurlg):
        with open(portalurlg) as genresfile:
            genretypes = json.load(genresfile)
    else:
        genretypes = {}

    setMac(portal_mac)
    setLogin(portal_login, portal_password)
    setSerialNumber(serial)

    handshake(url)
    getAuth(url)
    getProfile(url)

    data = {'vod': []}

    page = int(startpage)
    numpages = page+int(portal_vodpages)

    keys = [
        'screenshot_uri',
        'category_id',
        'genre_id_1',
        'genre_id_2',
        'genre_id_3',
        'genre_id_4',
        'year',
        'director',
        'rating_mpaa',
        'time',
        'rating_imdb',
        'rating_count_imdb',
        'country',
        'actors',
        'description',
        ]

    vars = {
        'type': 'vod',
        'action': 'get_ordered_list',
        'sortby': 'added',
        'not_ended': '0',
        'fav': '0',
        'JsHttpRequest': '1-xml',
        'p': 0,
        }

    while True:

        vars['p'] = page
        info = retrieveData(url, vars)

        if page == int(startpage):
            total_items = float(info['js']['total_items'])
            max_page_items = float(info['js']['max_page_items'])
            max_pages = math.ceil(total_items / max_page_items)

        results = info['js']['data']

        for i in results:

            val = {}
            for key in keys:
                val[key] = (i[key] if key in i.keys() and i[key] else '')

            cmd = (i['cmd'] if not 'redirect/vodcached' in i['cmd'] else 'ffmpeg /media/' + i['id'] + '.mpg')

            genre = []
            for x in range(1, 5):
                j = val['genre_id_' + str(x)]
                if not j in ['', '0'] and genretypes[j]:
                    genre.append(genretypes[j])
            genres = ', '.join(genre)

            obj = {
                'name': i['name'],
                'cmd': cmd,
                'logo': val['screenshot_uri'],
                'cat_id': val['category_id'],
                'genres': genres,
                'year': val['year'],
                'direct': val['director'],
                'mpaa': val['rating_mpaa'],
                'runtime': val['time'],
                'rating': val['rating_imdb'],
                'voters': val['rating_count_imdb'],
                'country': val['country'],
                'cast': val['actors'],
                'plot': val['description'],
                'added': i['added'],
                }

            data['vod'].append(obj)

        page += 1
        if page > max_pages or page >= numpages:
            break
    nextpg = ''
    if page <= max_pages:
        nextpg = str(page).strip()
    header = '{ "version" : "' + cache_version + '", "start_page" : "'  + startpage.strip() + '", "next_page" : "'  + nextpg + '", "total_items" : "'  + str(total_items) + '", "max_page_items" : "'  + str(max_page_items) + '", "time" : "'  + str(now) + '", "vod" : [\n'
    js_data = json.dumps(data).replace('{"vod": [',header).replace('"}, {"', '"},\n{"')

    with open(portalurl, 'w') as f:
        f.write(js_data)

    return json.loads(js_data)


def orderChannels(channels):
    n_data = {}
    for i in channels:
        number = i['number']
        n_data[int(number)] = i

    ordered = sorted(n_data)
    data = {}
    for i in ordered:
        data[i] = n_data[i]

    return data.values()


def channel_data(i):
    global genres

    obj = {
        'number': i['number'],
        'name': i['name'],
        'cmd': i['cmd'],
        'logo': i['logo'],
        'tmp': str(i['use_http_tmp_link']),
        'genre_id': str(i['tv_genre_id']),
        'genre_title': genres[i['tv_genre_id']]['title'],
        }

    return obj


def getAllChannels(
    portal_mac,
    url,
    serial,
    portal_login,
    portal_password,
    path,
    ):

    global login, password
    global genres
    added = False

    now = time()

    portalurl = '_'.join(re.findall('[a-zA-Z0-9]+', url))
    portalurl = path + '/' + portalurl

    setMac(portal_mac)
    setLogin(portal_login, portal_password)
    setSerialNumber(serial)

    if not os.path.exists(path):
        os.makedirs(path)

    if os.path.exists(portalurl):

        # check last time

        with open(portalurl) as data_file:
            data = json.load(data_file)

        if 'version' not in data or data['version'] != cache_version:
            clearCache(url, path)
        else:

            time_init = float(data['time'])

            # update 12h

            if (now - time_init) / 3600 < 12:
                return data

    handshake(url)
    getAuth(url)
    getProfile(url)

    genres = getGenres(
        portal_mac,
        url,
        serial,
        login,
        password,
        path,
        )
    genres = genres['genres']
    censored_genres = []
    
    for (id, i) in genres.iteritems():
        title=i['title']
        title2 = title.title()
        if 'censored' in i:
            if (i['censored']=="1"):
                censored_genres.append(id)
        else:
            if ("adult" in title2.lower()) or ("sex" in title2.lower()):
                censored_genres.append(id)
 
    values = {'type': 'itv', 'action': 'get_all_channels',
              'JsHttpRequest': '1-xml'}

    info = retrieveData(url, values)

    results = info['js']['data']

    header = '{ "version" : "' + cache_version + '", "time" : "' \
        + str(now) + '", "channels" : { \n'
    data = {'channels': {}}

    for i in results:
        id = i['id']
        data['channels'][id] = channel_data(i)

    values = {
        'type': 'itv',
        'action': 'get_ordered_list',
        'genre': '',
        'p': 0,
        'fav': '0',
        'JsHttpRequest': '1-xml',
        }
    for cgenre in censored_genres:
        page = 1
        values['genre']=cgenre
        if cgenre != None:
            while True:
        
                # retrieve adults
                values['p'] = page
                info = retrieveData(url, values)
        
                if page == 1:
                    total_items = float(info['js']['total_items'])
                    max_page_items = float(info['js']['max_page_items'])
                    pages = math.ceil(total_items / max_page_items)
        
                results = info['js']['data']
        
                for i in results:
                    id = i['id']
                    data['channels'][id] = channel_data(i)
        
                page += 1
                if page > pages:
                    break

    js_data = json.dumps(data).replace('{"channels": {',
            header).replace('"}, "', '"},\n"')

    with open(portalurl, 'w') as f:
        f.write(js_data)

    return data


def retriveUrl(
    portal_mac,
    url,
    serial,
    portal_login,
    portal_password,
    channel,
    tmp,
    ):

    setMac(portal_mac)
    setLogin(portal_login, portal_password)
    setSerialNumber(serial)

    if 'matrix' in channel:
        return retrieve_matrixUrl(url, channel)
    else:

        return retrive_defaultUrl(url, channel, tmp)


def retrive_defaultUrl(url, channel, tmp):

    global login, password

    if tmp == '0':
        s = channel.split(' ')
        url = (s[1] if len(s) > 1 else s[0])
        return url

    handshake(url)
    getAuth(url)
    getProfile(url)

    values = {
        'type': ('itv' if tmp != '' else 'vod'),
        'action': 'create_link',
        'cmd': channel,
        'JsHttpRequest': '1-xml',
        }

    info = retrieveData(url, values)

    # alert(str(info))

    cmd = info['js']['cmd']

    s = cmd.split(' ')

    url = (s[1] if len(s) > 1 else s[0])

    return_url = url
#
#    # TRY RETRIEVE THE 1 EXTM3U
#
#    request = urllib2.Request(url)
#    request.get_method = lambda : 'HEAD'
#    response = urllib2.urlopen(request)
#    data = response.read().decode('utf-8')
#
#    data = data.splitlines()
#    if data[0]==u'#EXTM3U':
#        data = data[len(data) - 1]
#        # RETRIEVE THE 2 EXTM3U
#        url = response.geturl().split('?')[0]
#        url_base = url[:-(len(url) - url.rfind('/'))]
#        return_url = url_base + '/' + data
    return return_url


def retrieve_matrixUrl(url, channel):

    global login, password

    channel = channel.split('/')
    channel = channel[len(channel) - 1]

    url += '/stalker_portal/server/api/matrix.php?channel=' + channel \
        + '&mac=' + mac

    # RETRIEVE THE 1 EXTM3U

    request = urllib2.Request(url)
    response = urllib2.urlopen(request)
    data = response.read().decode('utf-8')

    _s1 = data.split(' ')
    data = _s1[0]
    if len(_s1) > 1:
        data = _s1[len(_s1) - 1]

    return data

def retrieveEPGData(url, ch_id):
    global key, mac, login, password

    url += '/stalker_portal'
    load = '/server/load.php'
    refer = '/c/'
    timezone = 'Etc/UTC'

    user_agent = \
        'Mozilla/5.0 (QtEmbedded; U; Linux; C) AppleWebKit/533.3 (KHTML, like Gecko) MAG200 stbapp ver: 4 rev: 1812 Mobile Safari/533.3'

    headers = {  # ........'Connection' : 'Keep-Alive',
        'User-Agent': user_agent,
        'Cookie': 'mac=' + mac + '; stb_lang=en; timezone=' + timezone,
        'Referer': url + refer,
        'Accept-Charset': 'UTF-8,*;q=0.8',
        'X-User-Agent': 'Model: MAG250; Link: WiFi',
        }

    if key:
        headers['Authorization'] = 'Bearer ' + key
    values = { 'type' : 'itv', 'action' : 'get_short_epg', 'ch_id' : ch_id, 'JsHttpRequest' : '1-xml'}
    data = urllib.urlencode(values)

    for i in range(0, 9):
        req = urllib2.Request(url + load, data, headers)
        try:
            resp = urllib2.urlopen(req).read().decode('utf-8')
        except:
            resp = ''
        if resp:
            break
    if is_json(resp):
        info = json.loads(resp)
    else:
        info = {'js':[]}
    return info

def getEPG(
    portal_mac,
    url,
    serial,
    portal_login,
    portal_password,
    path,
    ):
    global login, password
    global key, cache_version;
    
    now = time();
    portalurl = "_".join(re.findall("[a-zA-Z0-9]+", url));
    portalurl = path + '/' + portalurl + '-epg';
    
    setMac(portal_mac)
    setLogin(portal_login, portal_password)
    setSerialNumber(serial)
    
    if not os.path.exists(path): 
        os.makedirs(path);
    
    if os.path.exists(portalurl):
        #check last time
        xmldoc = minidom.parse(portalurl);
        itemlist = xmldoc.getElementsByTagName('tv');
        version = itemlist[0].attributes['cache-version'].value;
        if version != cache_version:
            clearCache(url, path);
        else:
            time_init = float(itemlist[0].attributes['cache-time'].value);
            # update 2h
            if ((now - time_init) / 3600) < 2:
                return xmldoc.toxml(encoding='utf-8');
    

    handshake(url);
    getAuth(url);
    getProfile(url);

    allchannels = getAllChannels(portal_mac, url, serial, portal_login, portal_password, path);
    channels = allchannels['channels'];    
    
    doc = minidom.Document();
    base = doc.createElement('tv');
    base.setAttribute("cache-version", cache_version);
    base.setAttribute("cache-time", str(now));
    base.setAttribute("generator-info-name", "IPTV Plugin");
    base.setAttribute("generator-info-url", "http://www.xmltv.org/");
    doc.appendChild(base)

    for c in channels:
        channel = channels[c];
        info = retrieveEPGData(url, c)

        results = info['js'];
        if results:
            name = channel['name'];
            tvgid = channel['number'];
            
            c_entry = doc.createElement('channel');
            c_entry.setAttribute("id", tvgid);
            base.appendChild(c_entry)
            
            dn_entry = doc.createElement('display-name');
            dn_entry_content = doc.createTextNode(name);
            dn_entry.appendChild(dn_entry_content);
            c_entry.appendChild(dn_entry);
        
            for epg in results:
                start_time     = datetime.fromtimestamp(float(epg['start_timestamp']));
                stop_time    = datetime.fromtimestamp(float(epg['stop_timestamp']));
                
                pg_entry = doc.createElement('programme');
                pg_entry.setAttribute("start", start_time.strftime('%Y%m%d%H%M%S -0000'));
                pg_entry.setAttribute("stop", stop_time.strftime('%Y%m%d%H%M%S -0000'));
                pg_entry.setAttribute("channel", tvgid);
                base.appendChild(pg_entry);
                
                t_entry = doc.createElement('title');
                t_entry.setAttribute("lang", "en");
                t_entry_content = doc.createTextNode(epg['name']);
                t_entry.appendChild(t_entry_content);
                pg_entry.appendChild(t_entry);
                
                d_entry = doc.createElement('desc');
                d_entry.setAttribute("lang", "en");
                d_entry_content = doc.createTextNode(epg['descr']);
                d_entry.appendChild(d_entry_content);
                pg_entry.appendChild(d_entry);
                        
                c_entry = doc.createElement('category');
                c_entry_content = doc.createTextNode(epg['category']);
                c_entry.appendChild(c_entry_content);
                pg_entry.appendChild(c_entry);
            
    with open(portalurl, 'w') as f: 
        f.write(doc.toxml(encoding='utf-8'));
    
    return doc.toxml(encoding='utf-8');
    

def clearCache(url, path):

    portalurl = '_'.join(re.findall('[a-zA-Z0-9]+', url))

    for (root, dirs, files) in os.walk(path):
        for file in files:
            if file.startswith(portalurl):
                os.remove(root + '/' + file)


def main(argv):
    if argv[0] == 'load':
        data = getAllChannels(
            argv[1],
            argv[2],
            argv[3],
            argv[4],
            argv[5],
            argv[6],
            )
    elif argv[0] == 'genres':
        getGenres(
            argv[1],
            argv[2],
            argv[3],
            argv[4],
            argv[5],
            argv[6],
            )
    elif argv[0] == 'channel':

        url = retriveUrl(
            argv[1],
            argv[2],
            argv[3],
            argv[4],
            argv[5],
            argv[6],
            argv[7],
            )
    elif argv[0] == 'vod_url':
        url = retriveUrl(
            argv[1],
            argv[2],
            argv[3],
            argv[4],
            argv[5],
            argv[6],
            '0',
            )
    elif argv[0] == 'cache':

        clearCache(argv[1], argv[2])
    elif argv[0] == 'profile':

        handshake(argv[1])
    elif argv[0] == 'epg':
        getEPG(
            argv[1],
            argv[2],
            argv[3],
            argv[4],
            argv[5],
            argv[6],
            )


if __name__ == '__main__':
    main(sys.argv[1:])
