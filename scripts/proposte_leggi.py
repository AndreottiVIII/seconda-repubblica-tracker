# -*- coding: utf-8 -*-
"""Che fine hanno fatto le proposte di legge dei deputati, dalla XIII alla XVI.

Gli archivi della Camera non lo dicono: il collegamento alla legge (ocd:lex)
c'e' solo per 251 disegni del governo nella XIV, e i "lavori preparatori"
delle leggi rimandano a nodi che nell'archivio non ci sono. Lo dice invece
l'elenco dei disegni di legge del Senato (modulo elenco-ddl-date, scaricato
da scarica_senato.py in data/cache/zip_senato/<leg>/), che segue ogni disegno
di legge in tutti e due i rami, fase per fase, con lo stato di ciascuna fase.
Il Senato lo pubblica dalla XIII: per la XII il dato non c'e'.

Per ogni proposta d'iniziativa parlamentare (dagli archivi atto-NN.rdf.zip
della Camera, come in arricchisci.py: numero e primo firmatario) si cerca la
fase della Camera con lo stesso numero, e si guarda il disegno di legge intero:

  legge             l'ultimo voto e' stato alla Camera: "approvato definitivamente"
  approvata         approvata dalla Camera e mandata al Senato (l'esito la' qui non si vede)
  testo unificato   approvata insieme ad altre in un testo solo
  assorbita         assorbita da un'altra proposta

Scrive data/proposte_leggi.json: {pid: [[legislatura, numero, titolo, esito, data]]}.
"""
import collections
import csv
import io
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

QUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, QUI)
import arricchisci as a

USCITA = os.path.join(QUI, '..', 'data', 'proposte_leggi.json')
SENATO = os.path.join(QUI, '..', 'data', 'cache', 'zip_senato')
LEGISLATURE = {13: 'XIII', 14: 'XIV', 15: 'XV', 16: 'XVI'}

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass


def proposte(n):
    """{numero: (titolo, [primi firmatari])}, solo i progetti di legge parlamentari."""
    testo = a.pacchetto('atto-%d' % n)
    fuori = {}
    pid = lambda u: (re.search(r'/[dp](\d+)(?:_|$)', u) or [None, None])[1]
    if testo.lstrip().startswith('<http'):
        atti = collections.defaultdict(lambda: {'primi': []})
        for s, p, o in a.triple(testo, '<http://dati.camera.it/ocd/attocamera.rdf/'):
            if p == 'primo_firmatario':
                atti[s]['primi'].append(pid(o))
            elif p in ('type', 'iniziativa', 'title', 'identifier') and not o.startswith('http'):
                atti[s][p] = o
        voci = atti.values()
    else:
        voci = []
        for el in ET.fromstring(testo.encode('utf-8')).iter():
            if a._locale(el.tag) == 'atto':
                voci.append({'type': a._testo(el, 'type'), 'iniziativa': a._testo(el, 'iniziativa'),
                             'title': a._testo(el, 'title'), 'identifier': a._testo(el, 'identifier'),
                             'primi': [a._pid(x) for x in a._figli(el, 'primo_firmatario')]})
    for x in voci:
        if x.get('type') == 'Progetto di Legge' and x.get('iniziativa') == 'Parlamentare' and x.get('identifier'):
            fuori[x['identifier'].strip()] = (a.titolo_proposta(x.get('title') or ''), list(filter(None, x['primi'])))
    return fuori


def esiti(n):
    """{numero alla Camera: [esito, data]} dall'elenco dei disegni di legge del Senato."""
    f = os.path.join(SENATO, str(n), 'elenco-ddl-date.csv')
    if not os.path.exists(f):
        return None
    righe = list(csv.DictReader(io.open(f, encoding='utf-8')))
    # la stessa proposta cambia numero a ogni passaggio ('168', '168-B', '168-D'),
    # e un testo unificato li elenca tutti ('100-200-A'): contano le parti in cifre
    numeri = lambda r: [x for x in (r['numeroFase'] or '').split('-') if x.strip().isdigit()]
    legge = {}
    for r in righe:
        # la XIV scrive gli stati abbreviati: 'appr. definit. Legge', 'appr. in t.u.'
        if (r['stato'] or '').startswith(('approvato definitivamente', 'appr. definit')):
            legge[r['ddl']] = r['dataStato'].replace('-', '')
    fuori = {}
    for r in righe:
        if r['ramo'] != 'C':
            continue
        stato, quando = (r['stato'] or '').strip(), r['dataStato'].replace('-', '')
        for numero in numeri(r):
            if r['ddl'] in legge:
                fuori[numero] = ['legge', legge[r['ddl']]]
            elif fuori.get(numero, [''])[0] == 'legge':
                continue
            elif stato in ('approvato in testo unificato', 'appr. in t.u.'):
                fuori[numero] = ['testo unificato', quando]
            elif stato in ('approvato', 'approvato con modificazioni', 'appr. con modificaz'):
                # approvata dalla Camera e mandata al Senato: com'e' finita la', da qui non si vede
                if fuori.get(numero, [''])[0] not in ('testo unificato',):
                    fuori[numero] = ['approvata', quando]
            elif stato == 'assorbito':
                fuori.setdefault(numero, ['assorbita', quando])
    return fuori


def main():
    fuori = collections.defaultdict(list)
    fatte = []
    for n, leg in sorted(LEGISLATURE.items()):
        e = esiti(n)
        if e is None:
            print('%s: manca l\'elenco del Senato, salto' % leg)
            continue
        fatte.append(leg)
        conta, trovate = collections.Counter(), 0
        for numero, (titolo, primi) in proposte(n).items():
            if numero not in e:
                continue
            trovate += 1
            esito, quando = e[numero]
            conta[esito] += 1
            for p in primi:
                fuori[p].append([leg, numero, titolo, esito, quando])
        print('%s: %d proposte con un esito; %s' % (leg, trovate, dict(conta)), flush=True)
    for v in fuori.values():
        v.sort(key=lambda x: (x[0] != 'XIII', x[4]))
    json.dump({'_nota': "Esito delle proposte di legge dei deputati (primo firmatario), dall'elenco dei disegni "
                        "di legge del Senato, che segue ogni proposta in tutti e due i rami. Legislature: "
                        + ', '.join(fatte) + ". Generato da scripts/proposte_leggi.py.",
               'legislature': fatte, 'proposte': fuori},
              io.open(USCITA, 'w', encoding='utf-8', newline='\n'), ensure_ascii=False, indent=0)
    print('deputati con almeno una proposta arrivata a un esito: %d' % len(fuori))


if __name__ == '__main__':
    main()
