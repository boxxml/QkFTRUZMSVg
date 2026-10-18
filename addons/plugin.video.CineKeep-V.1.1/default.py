# -*- coding: utf-8 -*-
import xbmc, xbmcgui, xbmcplugin, xbmcaddon, xbmcvfs
import urllib.request as urllib2
import json
import sys
import os
import urllib.parse as parse
import base64
import hashlib

# --- CONFIGURAÇÃO DA SEGURANÇA ---
HASH_SECRETO = "ed823ec32c5d4e9ca9dd968bb0fe9366b7d904ce0cae615308ddd5b89f0e6a3a"

def verificar_pin_adulto():
    addon_handle = xbmcaddon.Addon()
    if addon_handle.getSetting("acesso_adulto_liberto") == "true":
        return True

    kb = xbmc.Keyboard('', 'Insira o PIN para Aceder ao Conteúdo Adulto:', True)
    kb.doModal()
    
    if kb.isConfirmed():
        senha_digitada = kb.getText().strip()
        hash_digitado = hashlib.sha256(senha_digitada.encode('utf-8')).hexdigest()
        
        if hash_digitado == HASH_SECRETO:
            addon_handle.setSetting("acesso_adulto_liberto", "true")
            return True
        else:
            xbmcgui.Dialog().ok("Acesso Negado", "Palavra-passe incorreta!")
            return False
            
    return False

def _obter_fonte_secreta():
    d = [104, 116, 116, 112, 115, 58, 47, 47, 114, 97, 119, 46, 103, 105, 116, 
         104, 117, 98, 117, 115, 101, 114, 99, 111, 110, 116, 101, 110, 116, 46, 
         99, 111, 109, 47, 70, 101, 110, 105, 120, 83, 121, 115, 116, 101, 109, 
         47, 114, 101, 116, 105, 109, 101, 45, 102, 111, 116, 101, 88, 50, 54, 
         47, 114, 101, 102, 115, 47, 104, 101, 97, 100, 115, 47, 109, 97, 105, 
         110, 47, 77, 101, 110, 117, 88, 46, 106, 115, 111, 110]
    return "".join([chr(x) for x in d])

URL_DA_LISTA = _obter_fonte_secreta()

# --- CONFIGURAÇÕES DO ADDON ---
ADDON = xbmcaddon.Addon()
ADDON_PATH = xbmcvfs.translatePath(ADDON.getAddonInfo('path'))
ART_PATH = os.path.join(ADDON_PATH, 'resources', 'art')
PROFILE = xbmcvfs.translatePath(ADDON.getAddonInfo('profile'))
FAV_FILE = os.path.join(PROFILE, 'favoritos.json')
handle = int(sys.argv[1]) if len(sys.argv) > 1 else -1

if not xbmcvfs.exists(PROFILE): xbmcvfs.mkdir(PROFILE)

def get_image(nome_arquivo):
    if not nome_arquivo: return ""
    if nome_arquivo.startswith('http'): return nome_arquivo
    caminho_local = os.path.join(ART_PATH, nome_arquivo)
    return caminho_local if os.path.exists(caminho_local) else ""

def get_json(url):
    try:
        req = urllib2.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        response = urllib2.urlopen(req, timeout=10)
        return json.loads(response.read().decode('utf-8'))
    except: return None

def descodificar_url(texto):
    if not texto: return ""
    if isinstance(texto, str) and not texto.startswith('http') and not texto.startswith('magnet') and len(texto) > 10:
        try: return base64.b64decode(texto.strip()).decode('utf-8')
        except: return texto
    return texto

# --- MENUS ---
def main_menu():
    fundo_padrao = get_image('fanart.jpg')
    add_dir("● [B][COLOR orange]Cine[/COLOR][COLOR red]Keep[/COLOR] [COLOR white]v1.0[/COLOR][/B] ●", "", mode="none", icon=get_image('logo.png'), fanart=fundo_padrao)
    add_dir("● [B][COLOR cyan]Meus Favoritos[/COLOR][/B] ●", "", mode='ver_favoritos', icon=get_image('favoritos.png'), fanart=fundo_padrao)
    add_dir("● [B][COLOR yellow]Pesquisar[/COLOR][/B] ●", "", mode='pesquisar', icon=get_image('search.png'), fanart=fundo_padrao)
    
    dados = get_json(URL_DA_LISTA)
    if dados and 'categorias' in dados:
        for i, cat in enumerate(dados['categorias']):
            icone = get_image(cat.get('imagem', ''))
            add_dir(cat['nome'], i, mode='abrir_categoria', icon=icone, fanart=get_image(cat.get('fanart', '')), logo=get_image(cat.get('clearlogo', '')))
    xbmcplugin.endOfDirectory(handle)

def listar_itens(lista_ou_url, is_fav=False, is_serie=False):
    itens = []
    if is_fav: 
        itens = lista_ou_url
    elif is_serie:
        dados = get_json(lista_ou_url)
        itens = dados.get('episodios', []) or dados.get('itens', []) if dados else []
    else:
        dados = get_json(URL_DA_LISTA)
        try: 
            cat_selecionada = dados['categorias'][int(lista_ou_url)]
            
            nome_cat = cat_selecionada.get('nome', '').lower()
            if 'adulto' in nome_cat or '18+' in nome_cat or 'proibido' in nome_cat:
                if not verificar_pin_adulto():
                    return
            
            itens = cat_selecionada['itens']
        except: itens = []

    for item in itens:
        nome = item.get('nome', 'Sem nome')
        url_item = item.get('url', '')
        tipo = item.get('tipo', 'filme')
        img = get_image(item.get('imagem', ''))
        
        li = xbmcgui.ListItem(label=nome)
        li.setArt({'thumb': img, 'icon': img, 'fanart': get_image(item.get('fanart', '')), 'clearlogo': get_image(item.get('clearlogo', ''))})
        li.setInfo('video', {'plot': item.get('sinopse', ''), 'title': nome})
        
        url_real = descodificar_url(url_item)
        if tipo == 'serie' or (isinstance(url_real, str) and url_real.endswith('.json')):
            u = sys.argv[0] + "?" + parse.urlencode({'mode': 'abrir_serie', 'url': url_item})
            xbmcplugin.addDirectoryItem(handle, u, li, True)
        else:
            li.setProperty('IsPlayable', 'true')
            u = sys.argv[0] + "?" + parse.urlencode({'mode': 'play', 'url': url_item, 'legenda': item.get('legenda', ''), 'nome': nome})
            
            label_fav = "[B][COLOR red]Remover Favorito[/COLOR][/B]" if is_fav else "[B][COLOR yellow]Adicionar Favorito[/COLOR][/B]"
            cmd = "RunPlugin(%s?mode=%s&nome=%s&url=%s&img=%s&fan=%s&sin=%s&leg=%s&logo=%s)" % (
                sys.argv[0], "rem_fav" if is_fav else "add_fav", parse.quote_plus(nome), parse.quote_plus(str(url_item)),
                parse.quote_plus(img), parse.quote_plus(item.get('fanart','')), parse.quote_plus(item.get('sinopse','')), 
                parse.quote_plus(item.get('legenda','')), parse.quote_plus(item.get('clearlogo',''))
            )
            li.addContextMenuItems([(label_fav, cmd)])
            xbmcplugin.addDirectoryItem(handle, u, li, False)
    xbmcplugin.endOfDirectory(handle)

def add_dir(label, index, mode, icon="", fanart="", logo=""):
    u = sys.argv[0] + "?" + parse.urlencode({'mode': mode, 'index': index})
    li = xbmcgui.ListItem(label=label); li.setArt({'icon': icon, 'thumb': icon, 'fanart': fanart, 'clearlogo': logo})
    xbmcplugin.addDirectoryItem(handle, u, li, True)

# --- ROTAS ---
params = dict(parse.parse_qsl(sys.argv[2][1:])) if len(sys.argv) > 2 else {}
mode = params.get('mode')

if not mode: main_menu()
elif mode == 'abrir_categoria': listar_itens(params.get('index'))
elif mode == 'abrir_serie': listar_itens(params.get('url'), is_serie=True)
elif mode == 'pesquisar':
    kb = xbmc.Keyboard('', 'Pesquisar...')
    kb.doModal()
    if kb.isConfirmed() and kb.getText():
        texto = kb.getText().lower(); d = get_json(URL_DA_LISTA)
        if d:
            pDialog = xbmcgui.DialogProgress()
            pDialog.create('CineKeep', 'A varrer listas do servidor...')
            res = []; cats_para_ler = []
            for c in d.get('categorias', []):
                nome_c = c.get('nome', '').lower()
                if 'adulto' in nome_c or '18+' in nome_c:
                    continue
                for it in c.get('itens', []):
                    if it.get('url') and it['url'].endswith('.json'): cats_para_ler.append(it)
            
            total = len(cats_para_ler)
            for i, cat in enumerate(cats_para_ler):
                if pDialog.iscanceled(): break
                pDialog.update(int((i/float(total))*100), 'Procurando em: %s' % cat['nome'])
                dados_sub = get_json(cat['url'])
                if dados_sub:
                    for f in (dados_sub.get('episodios', []) or dados_sub.get('itens', [])):
                        if texto in f.get('nome', '').lower(): res.append(f)
            pDialog.close()
            if res: listar_itens(res, is_fav=True)
            else: xbmcgui.Dialog().notification("Busca", "Nada encontrado.")

elif mode == 'play':
    url = descodificar_url(params.get('url', ''))
    leg = descodificar_url(params.get('legenda', ''))
    
    li = xbmcgui.ListItem(path=url)
    li.setInfo('video', {'title': params.get('nome', 'Video')})
    if leg: li.setSubtitles([leg])
    xbmcplugin.setResolvedUrl(handle, True, li)

elif mode == 'add_fav':
    nome = params.get('nome', ''); favs = []
    if os.path.exists(FAV_FILE):
        try: 
            with open(FAV_FILE, 'r') as f: favs = json.load(f)
        except: pass
    if not any(i['nome'] == nome for i in favs):
        favs.append({'nome': nome, 'url': params.get('url',''), 'imagem': params.get('img',''), 'fanart': params.get('fan',''), 'sinopse': params.get('sin',''), 'legenda': params.get('leg',''), 'clearlogo': params.get('logo','')})
        with open(FAV_FILE, 'w') as f: json.dump(favs, f)
        xbmcgui.Dialog().notification("Favoritos", "Adicionado!")

elif mode == 'rem_fav':
    if os.path.exists(FAV_FILE):
        with open(FAV_FILE, 'r') as f: favs = json.load(f)
        favs = [i for i in favs if i['nome'] != params.get('nome', '')]
        with open(FAV_FILE, 'w') as f: json.dump(favs, f)
        xbmc.executebuiltin("Container.Refresh")

elif mode == 'ver_favoritos':
    if os.path.exists(FAV_FILE):
        with open(FAV_FILE, 'r') as f: l = json.load(f)
        if l: listar_itens(l, is_fav=True)