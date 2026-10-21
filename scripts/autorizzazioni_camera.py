# -*- coding: utf-8 -*-
"""Le domande di autorizzazione contro i deputati, dalla XII alla XVI.

Dopo la riforma dell'immunita' del 1993 per processare un parlamentare non
serve piu' il permesso della Camera: restano le domande per gli arresti, le
perquisizioni, le intercettazioni e l'uso delle intercettazioni. Una domanda
e' un atto parlamentare, non una condanna, e la scheda la scrive cosi'.

Due fonti, per non contare niente due volte:

  XII e XIII   le Banche dati professionali della Camera (bdp.camera.it, ex
               3270), archivio dell'attivita' non legislativa: contro chi
               (cognome e gruppo), per quale reato, il numero del documento
               (doc. IV) e com'e' finita. Lo stesso metodo di
               primarepubblica.net, copiato: i due siti restano separati.
  XIV-XVI      gli indici dei Documenti IV della Camera
               (documenti.camera.it): numero, data, tipo di domanda e
               cognome del deputato. L'esito li' non c'e'.

L'aggancio e' per cognome dentro la legislatura; due deputati con lo stesso
cognome nella stessa legislatura e la domanda resta fuori (meglio niente che
il sbagliato), e finisce nell'elenco da guardare a mano.

Si lancia a mano, una pagina al secondo: il server e' della Camera. Scrive
data/autorizzazioni.json.
"""
import html
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
USCITA = os.path.join(QUI, '..', 'data', 'autorizzazioni.json')
GREZZO = os.path.join(QUI, '..', 'data', 'cache', 'autorizzazioni_grezze.json')
ELENCO = os.path.join(QUI, '..', 'data', 'elenco.json')
UA = {'User-Agent': 'SecondaRepubblicaTracker/0.1 (https://secondarepubblica.it)'}
PAUSA = 1.0
BDP = 'https://bdp.camera.it/init/di%s/'
TIPI = {'procedere': 'Domande di autorizzazioni a procedere annunziate',
        'arresto': "Domande di autorizzazione all'arresto annunziate"}
# Doc IV: arresti, perquisizioni, intercettazioni (art. 68, secondo e terzo comma);
# Doc IV-ter: le opinioni espresse (art. 68, primo comma); Doc IV-bis: i reati
# commessi da ministro (art. 96).
INDICI = {(leg, doc): 'leg%s/lavori/documentiparlamentari/indiceetesti/%s/elenco.htm' % (n, cartella)
          for leg, n in (('XIV', 14), ('XV', 15), ('XVI', 16))
          for doc, cartella in (('IV', '004'), ('IV-ter', '004ter'), ('IV-bis', '004bis'))}
TIPO = {'IV': 'misure', 'IV-ter': 'opinioni', 'IV-bis': 'ministro'}
ROMANI = {'12': 'XII', '13': 'XIII'}
MESI = {m: i + 1 for i, m in enumerate(['gennaio', 'febbraio', 'marzo', 'aprile', 'maggio', 'giugno',
                                         'luglio', 'agosto', 'settembre', 'ottobre', 'novembre',
                                         'dicembre'])}

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass


def leggi(url, codifica='utf-8'):
    for tentativo in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
                return r.read().decode(codifica, 'replace')
        except Exception:
            time.sleep(10 * (tentativo + 1))
    raise RuntimeError('non risponde: ' + url)


def testo(s):
    return re.sub(r'\n\s*\n+', '\n', html.unescape(re.sub(r'<[^>]+>', '\n', s)))


# ------------------------------------------------------------- XII e XIII

def schede_di(leg, tipo):
    ids, pagina = [], 0
    while True:
        q = {'attivita': TIPI[tipo]}
        if pagina:
            q['page'] = pagina
        s = leggi(BDP % leg + 'ricercaAttivita?' + urllib.parse.urlencode(q))
        nuovi = [i for i in re.findall(r'/init/di%s/scheda/(\d+)' % leg, s) if i not in ids]
        if not nuovi:
            break
        ids += nuovi
        if 'successivo' not in s:
            break
        pagina += 1
        time.sleep(PAUSA)
    return ids


def campo(t, nome, dopo):
    m = re.search(r'\n%s:\s*\n(.*?)\n%s:' % (nome, dopo), t, re.S)
    return re.sub(r'\s+', ' ', m.group(1)).strip() if m else ''


def scheda(leg, id_):
    t = testo(leggi(BDP % leg + 'scheda/' + id_))
    argomento = campo(t, 'Argomento', 'Interventi')
    doc = re.search(r'doc\.\s*IV(?:-ter)?,\s*n\.\s*(\d+)', argomento)
    return {'leg': ROMANI[leg], 'fonte': 'bdp', 'id': id_,
            'data': campo(t, 'Data', 'Argomento').split(' ')[0],
            'doc': doc.group(1) if doc else '',
            'contro': campo(t, 'Contro', 'Presentatori'),
            'argomento': argomento,
            'esito': argomento[doc.end():].lstrip(').; ') if doc else ''}


# ------------------------------------------------------------- XIV-XVI

def data_estesa(s):
    m = re.search(r'(\d{1,2})[°º]?\s+(\w+)\s+(\d{4})', s or '')
    if not m or m.group(2).lower() not in MESI:
        return ''
    return '%s%02d%02d' % (m.group(3), MESI[m.group(2).lower()], int(m.group(1)))


def indice(leg, doc, percorso):
    t = testo(leggi('https://documenti.camera.it/_dati/' + percorso, 'latin-1'))
    t = re.sub(r'Doc\. IV-\s*\n\s*(bis|ter)\s*\n\s*,', r'Doc. IV-\1,', t)
    righe = [x.strip() for x in t.split('\n') if x.strip()]
    fuori, cur = [], None
    for r in righe:
        m = re.match(r'^Doc\. IV(?:-bis|-ter)?, n\. (\d+)(-.*)?$', r)
        if not m and r.startswith('Doc. IV'):
            # relazioni della Giunta su piu' documenti insieme ('nn. 8-A, 13-A e 17-A')
            if cur:
                fuori.append(cur)
            cur = None
            continue
        if m:
            if cur:
                fuori.append(cur)
            cur = None if m.group(2) else {'leg': leg, 'fonte': 'doc ' + doc, 'doc': m.group(1),
                                           'tipo': TIPO[doc], 'data': '', 'testo': ''}
            continue
        if not cur:
            continue
        if not cur['data'] and re.search(r'\d{4}', r) and ('il' in r or re.search(r'\d+ \w+ \d{4}', r)):
            cur['data'] = data_estesa(r)
        elif r.startswith(('Domanda', 'Richiest')) or (cur['testo'] and not r.startswith('(')):
            cur['testo'] = (cur['testo'] + ' ' + r).strip()
    if cur:
        fuori.append(cur)
    for d in fuori:
        m = re.search(r'(?:del|della|dei|delle)\s+deputat[oaie]\s+(.+?)'
                      r'(?:\s*\(|,\s*nell|\s+[Nn]ella sua|\s+e di\s|$)', d['testo'])
        d['contro'] = m.group(1).strip() if m else ''
        d['domanda'] = re.sub(r'\s+nei confronti.*$|\s+del deputat.*$', '', d['testo']).strip()
    return fuori


# ------------------------------------------------------------- aggancio

def norm(s):
    s = unicodedata.normalize('NFKD', s or '').upper()
    return re.sub(r'[^A-Z]', '', ''.join(c for c in s if not unicodedata.combining(c)))


def tipo_di(testo):
    """Nella XII e XIII le banche dati mettono tutto sotto 'autorizzazioni a
    procedere': il testo dice di che cosa si tratta."""
    t = testo.lower()
    if 'insindacabilit' in t or 'sindacabilit' in t:
        return 'opinioni'
    if re.search(r"qualit[aà]'? di ministro|art(?:icolo|\.)\s*96|ministro .* pro tempore", t):
        return 'ministro'
    return 'misure'


def breve(testo, tipo):
    """Il reato (fra parentesi nei testi della Camera) o la misura richiesta."""
    if tipo == 'misure':
        t = re.sub(r'^.*?Domanda di autorizzazione\s*', '', testo, flags=re.S)
        t = re.sub(r'\s+nei confronti.*$|\s+del deputat.*$|,\s*nell.*$', '', t, flags=re.S).strip()
        return t
    if 'procedimento civile' in testo and 'reato' not in testo:
        return 'procedimento civile'
    reati = []
    for x in re.findall(r'\(([^()]+)\)', testo):
        x = x.strip()
        if re.search(r'\d|^doc|^art|^gi[aà]|^reitera|^etc', x, re.I) or x in reati:
            continue
        reati.append(x)
    return '; '.join(reati)


def aggancia(domande, persone):
    per_cognome = {}
    for p in persone:
        for leg, r in (p.get('ramo') or {}).items():
            if r == 'C':
                per_cognome.setdefault((leg, norm(p.get('cognome') or p['nome'].split()[-1])), []).append(p)
    fuori, mancate = {}, []
    for d in domande:
        if d['fonte'] == 'bdp':
            contro = re.sub(r'\.\s*domanda annunziata.*$', '', d['contro'])
            chi_lista = [c[0].strip() for c in re.findall(r'([^,(]+?)\s*\(([^)]*)\)', contro)]
            esito = d.get('esito', '').upper()
            esito = ('concessa' if 'CONCESSA' in esito else 'negata' if 'NEGATA' in esito
                     else 'restituita' if 'RESTITUZIONE' in esito or 'RINVIO' in esito else '')
            tipo = tipo_di(d['argomento'])
            m = re.match(r'(\d\d)-(\d\d)-(\d\d)', d['data'] or '')
            data = ('19' + m.group(3) + m.group(2) + m.group(1)) if m else ''
            riga = lambda: [d['leg'], data, tipo, ('IV-ter ' if tipo == 'opinioni' else 'IV ') + d['doc']
                            if d['doc'] else '', esito, breve(d['argomento'], tipo)]
        else:
            chi_lista = [x.strip() for x in re.split(r',| e ', d['contro']) if x.strip()]
            riga = lambda: [d['leg'], d['data'], d['tipo'], d['fonte'][4:] + ' ' + d['doc'], '',
                            breve(d['testo'], d['tipo'])]
        for chi in chi_lista:
            parti = chi.split()
            cognome = ' '.join(x for x in parti if x.isupper() and len(x) > 1) or chi
            nome = norm(' '.join(x for x in parti if not x.isupper()))
            tutti = per_cognome.get((d['leg'], norm(cognome)), [])
            if not tutti and len(parti) > 1 and all(x.isupper() for x in parti):
                # tutto maiuscolo ('GIOVANNI ALEMANNO'): il cognome e' in fondo
                for k in (1, 2):
                    tutti = per_cognome.get((d['leg'], norm(' '.join(parti[-k:]))), [])
                    if tutti:
                        nome = norm(' '.join(parti[:-k]))
                        break
            if len(tutti) > 1 and nome:
                tutti = [p for p in tutti if norm(p['nome']).startswith(nome)]
            if len(tutti) == 1:
                r = riga()
                if r not in fuori.setdefault(tutti[0]['qid'], []):
                    fuori[tutti[0]['qid']].append(r)
            else:
                mancate.append([d['leg'], chi, d['doc'], len(tutti)])
    return fuori, mancate


def main():
    grezze = json.load(io.open(GREZZO, encoding='utf-8')) if os.path.exists(GREZZO) else []
    visti = {(r['leg'], r.get('id')) for r in grezze if r['fonte'] == 'bdp'}
    for leg in ROMANI:
        for tipo in TIPI:
            ids = schede_di(leg, tipo)
            print('%s %s: %d domande' % (ROMANI[leg], tipo, len(ids)), flush=True)
            for id_ in ids:
                if (ROMANI[leg], id_) in visti:
                    continue
                r = scheda(leg, id_)
                r['tipo'] = tipo
                grezze.append(r)
                visti.add((r['leg'], id_))
                time.sleep(PAUSA)
    grezze = [r for r in grezze if r['fonte'] == 'bdp']
    for (leg, doc), percorso in sorted(INDICI.items()):
        voci = indice(leg, doc, percorso)
        print('%s: %d documenti %s' % (leg, len(voci), doc), flush=True)
        grezze += voci
        time.sleep(PAUSA)
    os.makedirs(os.path.dirname(GREZZO), exist_ok=True)
    json.dump(grezze, io.open(GREZZO, 'w', encoding='utf-8'), ensure_ascii=False, indent=0)

    persone = json.load(io.open(ELENCO, encoding='utf-8'))['persone']
    agganciate, mancate = aggancia(grezze, persone)
    print('domande: %d; agganciate a %d deputati; non agganciate: %d'
          % (len(grezze), len(agganciate), len(mancate)))
    json.dump({'_nota': "Domande di autorizzazione contro i deputati, XII-XVI: banche dati "
                        "della Camera (XII, XIII) e indici dei Documenti IV (XIV-XVI). Una "
                        "domanda e' un atto parlamentare, non una condanna. Generato da "
                        "scripts/autorizzazioni_camera.py.",
               'domande': agganciate, 'non_agganciate': mancate},
              io.open(USCITA, 'w', encoding='utf-8', newline='\n'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
