# -*- coding: utf-8 -*-
"""Quante volte ha preso la parola ogni deputato, legislatura per legislatura.

Non esiste una fonte sola per tutto il periodo, e le fonti non contano la
stessa cosa: la scheda lo dice riga per riga.

  XII    il portale storico (storia.camera.it): tutti gli interventi, in Aula
         e in commissione, fra il 15 aprile 1994 e l'8 maggio 1996. Il
         portale ha un buco dall'estate 1996 al 2008 circa: per la XIII non
         serve, e per la XIII una fonte non c'e'.
  XIV    il sito della legislatura (leg14.camera.it), "Interventi su progetti
  XV     di legge in Assemblea": gli interventi sulle leggi, in Aula, con la
         data; si contano le date.
  XVI    gli open data della Camera (SPARQL, ocd:intervento): in Aula
         (resoconti dell'Assemblea) e in commissione (bollettini), separati.

Una pagina al secondo: i server sono della Camera. Si lancia a mano e
riprende da dove era (data/cache/interventi_camera_grezzi.json). Scrive
data/interventi_camera.json: {qid: {legislatura: [numero, che cosa conta]}}.
"""
import io
import json
import os
import re
import sys
import time
import unicodedata
import urllib.parse
import urllib.request

QUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, QUI)
ELENCO = os.path.join(QUI, '..', 'data', 'elenco.json')
GREZZO = os.path.join(QUI, '..', 'data', 'cache', 'interventi_camera_grezzi.json')
USCITA = os.path.join(QUI, '..', 'data', 'interventi_camera.json')
UA = {'User-Agent': 'SecondaRepubblicaTracker/0.1 (https://secondarepubblica.it)'}
PAUSA = 1.0

PAGINA_LEG = {
    'XIV': 'https://leg14.camera.it/cartellecomuni/leg14/organiparlamentari/assemblea/contenitore_dati.asp'
           '?deputato=d{id}&tipopagina=&Pagina=Deputati/Composizione/01.camera/nuovacomposizione/'
           'attivita.asp?deputato=d{id}&Tipo=NSALG',
    'XV': 'https://leg15.camera.it/cartellecomuni/leg15/include/contenitore_dati.asp?deputato=d{id}'
          '&tipopagina=&Pagina=/CartelleComuni/Leg15/Deputati/Composizione/SchedeDeputati/'
          'intLAssemblea.asp?deputato=d{id}&Tipo=IAL',
}
# il portale storico: la XII va dal 15 aprile 1994 all'8 maggio 1996
XII_DA, XII_A = '19940415', '19960508'
PER_PAGINA = 15

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass


def leggi(url, codifica='utf-8', dati=None, intestazioni=None):
    for tentativo in range(4):
        try:
            r = urllib.request.Request(url, data=dati, headers=dict(UA, **(intestazioni or {})))
            with urllib.request.urlopen(r, timeout=120) as f:
                return f.read().decode(codifica, 'replace')
        except Exception:
            if tentativo == 3:
                raise
            time.sleep(10 * (tentativo + 1))


def salva(grezzi):
    os.makedirs(os.path.dirname(GREZZO), exist_ok=True)
    json.dump(grezzi, io.open(GREZZO, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)


# ------------------------------------------------------------- XVI

def xvi():
    q = '''SELECT ?d ?sez (COUNT(?i) AS ?n) WHERE {
      ?i a <http://dati.camera.it/ocd/intervento> ;
         <http://dati.camera.it/ocd/rif_deputato> ?d ;
         <http://purl.org/dc/elements/1.1/relation> ?r .
      FILTER(STRENDS(STR(?d), "_16"))
      BIND(REPLACE(STR(?r), "^.*[?&]sezione=([a-zA-Z]+).*$", "$1") AS ?sez)
    } GROUP BY ?d ?sez'''
    t = leggi('https://dati.camera.it/sparql', dati=urllib.parse.urlencode({'query': q}).encode(),
              intestazioni={'Accept': 'text/csv'})
    fuori = {}
    for riga in t.splitlines()[1:]:
        m = re.match(r'"?http://dati.camera.it/ocd/deputato.rdf/d(\d+)_16"?,"?(\w+)"?,"?(\d+)"?', riga)
        if m:
            fuori.setdefault(m.group(1), {})[m.group(2)] = int(m.group(3))
    return fuori


# ------------------------------------------------------------- XIV e XV

DATA = re.compile(r'(?<![\d/-])\d{1,2}-\d{1,2}-(?:19|20)\d\d(?![\d-])')


def sito_leg(leg, id_):
    t = leggi(PAGINA_LEG[leg].format(id=id_), 'latin-1')
    if "ATTIVITA' DI DEPUTATO" not in t:
        return None
    # solo la parte con l'attivita': il resto della pagina e' il menu
    corpo = t.split("ATTIVITA' DI DEPUTATO")[-1]
    return len(DATA.findall(corpo))


# ------------------------------------------------------------- XII

def scheggia(nome, cognome, nascita):
    """'MASSIMO', "D'ALEMA", 1949-04-20 -> massimo-d-alema-19490420."""
    s = ('%s %s' % (nome, cognome)).lower()
    s = re.sub(r"'(?=[a-z])", '-', s).replace("'", '')
    s = ''.join(c for c in unicodedata.normalize('NFKD', s) if not unicodedata.combining(c))
    return '%s-%s' % (re.sub(r'\s+', '-', s.strip()), nascita.replace('-', ''))


def date_pagina(slug, da):
    t = leggi('https://storia.camera.it/deputato/%s/dibattiti%s' % (slug, '?da=%d' % da if da else ''))
    time.sleep(PAUSA)
    return [(re.search(r'/lavori/dibattiti/(\d{8})', v) or [None, ''])[1] for v in t.split('class="navin"')[1:]]


def fino_a(slug, totale, giorno, cache):
    """Quanti interventi fino a quel giorno compreso: l'elenco e' in ordine di
    data, si cerca a dimezzamento la pagina dove si passa il giorno."""
    def pagina(k):
        if k not in cache:
            cache[k] = date_pagina(slug, k * PER_PAGINA)
        return cache[k]
    pagine = max(1, -(-totale // PER_PAGINA))
    if (pagina(0) or ['9'])[0] > giorno:
        return 0
    basso, alto = 0, pagine - 1
    while basso < alto:
        mezzo = (basso + alto + 1) // 2
        d = pagina(mezzo)
        if d and d[0] and d[0] <= giorno:
            basso = mezzo
        else:
            alto = mezzo - 1
    return basso * PER_PAGINA + sum(1 for d in pagina(basso) if d and d <= giorno)


def xii(slug):
    t = leggi('https://storia.camera.it/deputato/' + slug)
    time.sleep(PAUSA)
    if '/deputato/' + slug not in t:
        return None
    m = re.search(r'visualizza tutti i (\d+) interventi di', t)
    totale = int(m.group(1)) if m else 0
    if not totale:
        return 0
    cache = {}
    prima = fino_a(slug, totale, '19940414', cache)
    return fino_a(slug, totale, XII_A, cache) - prima


# ------------------------------------------------------------- tutto

def main():
    import arricchisci
    persone = json.load(io.open(ELENCO, encoding='utf-8'))['persone']
    grezzi = json.load(io.open(GREZZO, encoding='utf-8')) if os.path.exists(GREZZO) else {}
    deputati = {leg: [p for p in persone if (p.get('ramo') or {}).get(leg) == 'C' and p.get('id_camera')]
                for leg in ('XII', 'XIV', 'XV', 'XVI')}

    if 'XVI' not in grezzi:
        grezzi['XVI'] = xvi()
        salva(grezzi)
    print('XVI: %d deputati negli open data' % len(grezzi['XVI']), flush=True)

    for leg in ('XIV', 'XV'):
        fatti = grezzi.setdefault(leg, {})
        da_fare = [p['id_camera'] for p in deputati[leg] if p['id_camera'] not in fatti]
        print('%s: %d deputati, %d da leggere' % (leg, len(deputati[leg]), len(da_fare)), flush=True)
        for i, id_ in enumerate(da_fare, 1):
            try:
                fatti[id_] = sito_leg(leg, id_)
            except Exception as e:
                print('  %s d%s: %s' % (leg, id_, str(e)[:80]), flush=True)
            time.sleep(PAUSA)
            if i % 50 == 0 or i == len(da_fare):
                salva(grezzi)
                print('  %s %d/%d' % (leg, i, len(da_fare)), flush=True)

    anagrafe = arricchisci.anagrafe_camera()
    fatti = grezzi.setdefault('XII', {})
    da_fare = [p for p in deputati['XII'] if p['id_camera'] not in fatti]
    print('XII: %d deputati, %d da leggere' % (len(deputati['XII']), len(da_fare)), flush=True)
    for i, p in enumerate(da_fare, 1):
        a = anagrafe.get(p['id_camera']) or {}
        if a.get('nome') and len(p.get('nascita') or '') == 10:
            slug = scheggia(a['nome'], a['cognome'], p['nascita'])
            try:
                fatti[p['id_camera']] = [slug, xii(slug)]
            except Exception as e:
                print('  XII %s: %s' % (slug, str(e)[:80]), flush=True)
        if i % 25 == 0 or i == len(da_fare):
            salva(grezzi)
            print('  XII %d/%d' % (i, len(da_fare)), flush=True)

    fuori = {}
    for leg, voci in (('XII', grezzi['XII']), ('XIV', grezzi['XIV']), ('XV', grezzi['XV'])):
        cosa = 'aula e commissione' if leg == 'XII' else 'leggi in aula'
        for p in deputati[leg]:
            v = voci.get(p['id_camera'])
            n = v[1] if leg == 'XII' and v else v
            if n is not None and not (leg == 'XII' and not v):
                fuori.setdefault(p['qid'], {})[leg] = [n, cosa]
    for p in deputati['XVI']:
        v = grezzi['XVI'].get(p['id_camera'], {})
        fuori.setdefault(p['qid'], {})['XVI'] = [v.get('assemblea', 0), 'aula', v.get('bollettini', 0)]
    mancano = {leg: sum(1 for p in deputati[leg] if leg not in fuori.get(p['qid'], {}))
               for leg in deputati}
    print('schede con interventi: %d; senza dato per legislatura: %s' % (len(fuori), mancano))
    json.dump({'_nota': "Interventi dei deputati: XII dal portale storico (aula e commissione), XIV e "
                        "XV dai siti delle legislature (interventi sulle leggi in aula), XVI dagli open "
                        "data (aula; il terzo numero e' la commissione). La XIII non ha una fonte. "
                        "Generato da scripts/interventi_camera.py.",
               'interventi': fuori},
              io.open(USCITA, 'w', encoding='utf-8', newline='\n'), ensure_ascii=False, indent=0)


if __name__ == '__main__':
    main()
