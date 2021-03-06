# -*- coding: utf-8 -*-

import re

from platformcode import config, logger
from core.item import Item
from core import httptools, scrapertools, jsontools, servertools, tmdb

# ~ host = 'https://xdede.co/'
host = 'https://movidy.co/'


def do_downloadpage(url, post=None, headers=None):
    url = url.replace('https://xdede.co/', 'https://movidy.co/') # por si viene de enlaces guardados
    data = httptools.downloadpage(url, post=post, headers=headers).data
    # ~ data = httptools.downloadpage_proxy('movidy', url, post=post, headers=headers).data
    return data


def mainlist(item):
    logger.info()
    itemlist = []

    itemlist.append(item.clone( title = 'Películas', action = 'mainlist_pelis' ))
    itemlist.append(item.clone( title = 'Series', action = 'mainlist_series' ))

    itemlist.append(item.clone( title = 'Listas de películas y series', action = 'list_lists', url = host + 'listas' ))

    itemlist.append(item.clone( title = 'Buscar ...', action = 'search', search_type = 'all' ))

    return itemlist

def mainlist_pelis(item):
    logger.info()
    itemlist = []

    itemlist.append(item.clone( title = 'Últimas películas', action = 'list_all', url = host + 'peliculas' ))
    itemlist.append(item.clone( title = 'Estrenos', action = 'list_all', url = host + 'peliculas/estrenos' ))
    itemlist.append(item.clone( title = 'Más valoradas', action = 'list_all', url = host + 'peliculas/mejor-valoradas' ))
    itemlist.append(item.clone( title = 'Actualizadas', action = 'list_all', url = host + 'actualizado/peliculas' ))

    itemlist.append(item.clone( title = 'Por género', action = 'generos', search_type = 'movie' ))
    itemlist.append(item.clone( title = 'Por año', action = 'anyos', search_type = 'movie' ))

    itemlist.append(item.clone( title = 'Listas de películas y series', action = 'list_lists', url = host + 'listas' ))

    itemlist.append(item.clone( title = 'Buscar película ...', action = 'search', search_type = 'movie' ))

    return itemlist

def mainlist_series(item):
    logger.info()
    itemlist = []

    itemlist.append(item.clone( title = 'Últimas series', action = 'list_all', url = host + 'series' ))
    itemlist.append(item.clone( title = 'Más valoradas', action = 'list_all', url = host + 'series/mejor-valoradas' ))
    itemlist.append(item.clone( title = 'Actualizadas', action = 'list_all', url = host + 'actualizado/series' ))

    itemlist.append(item.clone( title = 'Por género', action = 'generos', search_type = 'tvshow' ))
    itemlist.append(item.clone( title = 'Por año', action = 'anyos', search_type = 'tvshow' ))

    itemlist.append(item.clone( title = 'Listas de películas y series', action = 'list_lists', url = host + 'listas' ))

    itemlist.append(item.clone( title = 'Buscar serie ...', action = 'search', search_type = 'tvshow' ))

    return itemlist


def generos(item):
    logger.info()
    itemlist = []

    url_base = host + ('peliculas' if item.search_type == 'movie' else 'series') + '/filtro/'

    data = do_downloadpage(host+'static/js/java.js')

    bloque = scrapertools.find_single_match(data, '<ul class="Ageneros">(.*?)</ul>')

    matches = scrapertools.find_multiple_matches(bloque, '<b>([^<]+)</b></li>')
    for title in matches:
        url = url_base + title + ',/,'
        itemlist.append(item.clone( action="list_all", title=title, url=url ))

    if item.search_type == 'tvshow':
        itemlist.append(item.clone( action="list_all", title='Anime', url=host + 'animes' ))

    return sorted(itemlist, key=lambda it: it.title)

def anyos(item):
    logger.info()
    itemlist = []

    url_base = host + ('peliculas' if item.search_type == 'movie' else 'series') + '/filtro/'

    from datetime import datetime
    current_year = int(datetime.today().year)

    limit_year = 1938 if item.search_type == 'movie' else 1988

    for x in range(current_year, limit_year, -1):
        url = url_base + ',/' + str(x) + ','
        itemlist.append(item.clone( action='list_all', title=str(x), url=url ))

    return itemlist


def list_all(item):
    logger.info()
    itemlist = []

    es_busqueda = 'search?' in item.url
    es_lista = '/listas/' in item.url
    tipo_url = 'tvshow' if '/series' in item.url or '/animes' in item.url else 'movie'

    data = do_downloadpage(item.url)
    # ~ logger.debug(data)

    matches = re.compile('<article(.*?)</article>', re.DOTALL).findall(data)
    for article in matches:
        url = scrapertools.find_single_match(article, ' href="([^"]+)"')
        thumb = scrapertools.find_single_match(article, ' data-echo="([^"]+)"')
        title = scrapertools.find_single_match(article, ' title="([^"]+)"').strip()
        if not url or not title: continue

        tid = scrapertools.find_single_match(url, '(\d+)-')
        if tid:
            infoLabels = {'tmdb_id':tid, 'year': '-'}
        else:
            infoLabels = {'year': '-'}

        if es_busqueda or es_lista:
            tipo = 'tvshow' if '/series' in url or '/animes' in url else 'movie'
            if item.search_type not in ['all', tipo]: continue
        else:
            tipo = tipo_url

        sufijo = '' if item.search_type != 'all' else tipo

        if tipo == 'movie':
            qlty = 'Low' if 'CALIDAD BAJA' in article else ''
            itemlist.append(item.clone( action='findvideos', url=url, title=title, thumbnail=thumb, qualities=qlty, fmt_sufijo=sufijo,
                                        contentType='movie', contentTitle=title, infoLabels=infoLabels ))
        else:
            itemlist.append(item.clone( action='temporadas', url=url, title=title, thumbnail=thumb, fmt_sufijo=sufijo,
                                        contentType='tvshow', contentSerieName=title, infoLabels=infoLabels ))


    tmdb.set_infoLabels(itemlist)

    next_page_link = scrapertools.find_single_match(data, '<a href="([^"]+)"[^>]*>Pagina siguiente')
    if next_page_link:
        itemlist.append(item.clone( title='>> Página siguiente', url=next_page_link, action='list_all' ))

    return itemlist


def temporadas(item):
    logger.info()
    itemlist = []

    data = do_downloadpage(item.url)

    patron = ' onclick="activeSeason\(this,\'temporada-(\d+)'
    matches = re.compile(patron, re.DOTALL).findall(data)
    for numtempo in matches:
        itemlist.append(item.clone( action='episodios', title='Temporada %s' % numtempo,
                                    contentType='season', contentSeason=numtempo ))

    tmdb.set_infoLabels(itemlist)

    return itemlist

# Si una misma url devuelve los episodios de todas las temporadas, definir rutina tracking_all_episodes para acelerar el scrap en trackingtools.
def tracking_all_episodes(item):
    return episodios(item)

def episodios(item):
    logger.info()
    itemlist=[]

    data = do_downloadpage(item.url)

    patron = '<li\s*><a href="([^"]+)"\s*up-modal=".Flex"><div class="wallEp"(.*?)</li>'
    matches = re.compile(patron, re.DOTALL).findall(data)

    for url, datos in matches:
        try:
            season, episode = scrapertools.find_single_match(url, '/(\d+)x(\d+)$')
        except:
            continue

        if item.contentSeason and item.contentSeason != int(season):
            continue

        title = scrapertools.find_single_match(datos, '<h2>(.*?)</h2>')
        thumb = scrapertools.find_single_match(datos, ' data-echo="([^"]+)"')
        titulo = '%sx%s %s' % (season, episode, title)

        itemlist.append(item.clone( action='findvideos', title = titulo, thumbnail=thumb, url = url,
                                    contentType = 'episode', contentSeason = season, contentEpisodeNumber = episode ))

    tmdb.set_infoLabels(itemlist)

    return itemlist


# Asignar un numérico según las calidades del canal, para poder ordenar por este valor
def puntuar_calidad(txt):
    orden = ['360p', '480p', '720p', '1080p']
    if txt not in orden: return 0
    else: return orden.index(txt) + 1

# Si hay excepciones concretas de este canal, añadir aquí, si son genéricas añadir en servertools.corregir_servidor
def corregir_servidor(servidor):
    servidor = servertools.corregir_servidor(servidor)
    if servidor == 'pro': return 'fembed'
    if servidor in ['beta', 'bot', 'soap']: return 'directo'
    return servidor

def findvideos(item):
    logger.info()
    itemlist = []

    IDIOMAS = {'1': 'Esp', '2': 'Lat', '3': 'VOSE', '4': 'VO'}

    data = do_downloadpage(item.url, headers = {'Referer': item.url})
    # ~ logger.debug(data)

    # Enlaces de usuarios
    if '<div class="linksUsers">' in data:
        enlaces = scrapertools.find_multiple_matches(data.split('<div class="linksUsers">')[1], '<li(.*?)</li>')
        for enlace in enlaces:
            url = scrapertools.find_single_match(enlace, ' href="([^"]+)"')
            numlang = scrapertools.find_single_match(enlace, '/img/(\d+)\.png')

            servidor = scrapertools.find_single_match(enlace, '\?domain=([^."]+)')
            if not servidor: servidor = scrapertools.find_single_match(enlace, '<span><img[^>]+>([^.<]+)')
            servidor = corregir_servidor(servidor)

            qlty = scrapertools.find_single_match(enlace, '<b>(.*?)</b>')
            user = scrapertools.find_single_match(enlace, 'user/([^"]+)')

            itemlist.append(Item( channel = item.channel, action = 'play', server = servidor,
                                  title = '', url = url, referer = item.url,
                                  language = IDIOMAS.get(numlang, 'VO'), 
                                  quality = qlty, quality_num = puntuar_calidad(qlty), other = user
                           ))

    # Enlaces oficiales
    ifr = scrapertools.find_single_match(data, '<iframe src="https://wmovies.co/ifr/([^"]+)')
    if not ifr: return itemlist
    referer = 'https://wmovies.co/ifr/'+ifr

    try:
        data = do_downloadpage('https://wmovies.co/cpt', post = {'type': '1', 'id': ifr}, headers = {'Referer': referer})
        # ~ logger.debug(data)
        data = jsontools.load(data)
        if data['status'] != 200: return itemlist

        matches = scrapertools.find_multiple_matches(data['data'], '<div class="OD_(\d)(.*?)</div>')
        for numlang, datos in matches:

            enlaces = scrapertools.find_multiple_matches(datos, " onclick=\"\w+\('([^']+)'.*?<span>([^<]+)")
            for url, servidor in enlaces:
                if not url.startswith('http'): url = 'https://wmovies.co/' + url

                servidor = corregir_servidor(servidor)
                if servidor == 'gvideo': continue # descartar pq no son enlaces directos de gvideo

                itemlist.append(Item( channel = item.channel, action = 'play', server = servidor,
                                      title = '', url = url, referer = referer,
                                      language = IDIOMAS.get(numlang, 'VO')
                               ))
    except:
        pass

    return itemlist

def play(item):
    logger.info()
    itemlist = []
    
    headers = {'Referer': item.referer}

    if not 'get-player' in item.url:
        data = do_downloadpage(item.url, headers = headers)
        # ~ logger.debug(data)

    if item.url.startswith('https://wmovies.co/u/'):
        url = scrapertools.find_single_match(data,'<a class="Go_V2" href="([^"]+)')

    else:
        if not 'get-player' in item.url:
            if not '"status":200' in data or not '"data":"' in data: return 'El vídeo no está disponible'
            item.url = 'https://wmovies.co/get-player/' + scrapertools.find_single_match(data,'"data":"([^"]+)')
        
        resp = httptools.downloadpage(item.url, headers = headers, follow_redirects = False)
        
        if 'refresh' in resp.headers:
            url = scrapertools.find_single_match(resp.headers['refresh'], ';\s*(.*)')
        elif 'location' in resp.headers:
            url = resp.headers['location']
        else: # directos
            # ~ logger.debug(resp.data)
            url = None
            bloque = scrapertools.find_single_match(resp.data, '"sources":\s*\[(.*?)\]')
            if not bloque: return 'No se encuentran fuentes para este vídeo'
            for enlace in scrapertools.find_multiple_matches(bloque, "\{(.*?)\}"):
                v_url = scrapertools.find_single_match(enlace, '"file":\s*"([^"]+)')
                if not v_url: continue
                v_lbl = scrapertools.find_single_match(enlace, '"label":\s*"([^"]+)')
                if not v_lbl: v_lbl = scrapertools.find_single_match(enlace, '"type":\s*"([^"]+)')
                if not v_lbl: v_lbl = 'mp4'
                itemlist.append([v_lbl, v_url])

            if len(itemlist) > 1:
                return sorted(itemlist, key=lambda x: int(x[0]) if x[0].isdigit() else 0)

    if url:
       url = url.replace('www.privatecrypt.me', 'www.fembed.com') #.replace('isthebest.rest', '.com')
       servidor = servertools.get_server_from_url(url)
       if servidor != 'directo':
           url = servertools.normalize_url(servidor, url)
           itemlist.append(item.clone( url = url, server = servidor ))

    return itemlist



def search(item, texto):
    logger.info("texto: %s" % texto)
    try:
        item.url = host + 'search?go=' + texto.replace(" ", "+")
        return list_all(item)
    except:
        import sys
        for line in sys.exc_info():
            logger.error("%s" % line)
        return []


def list_lists(item):
    logger.info()
    itemlist = []

    data = do_downloadpage(item.url)
    # ~ logger.debug(data)

    matches = re.compile('<article(.*?)</article>', re.DOTALL).findall(data)
    for article in matches:
        url = scrapertools.find_single_match(article, ' href="([^"]+)"')
        title = scrapertools.find_single_match(article, '<h2>(.*?)</h2>').strip()
        plot = scrapertools.find_single_match(article, '<p>(.*?)</p>').strip()
        if not url or not title: continue

        itemlist.append(item.clone( action="list_all", title=title, url=url, plot=plot, search_type='all' ))

    next_page_link = scrapertools.find_single_match(data, '<a href="([^"]+)"[^>]*>Pagina siguiente')
    if next_page_link:
        itemlist.append(item.clone( title='>> Página siguiente', url=next_page_link, action='list_lists' ))

    return itemlist
