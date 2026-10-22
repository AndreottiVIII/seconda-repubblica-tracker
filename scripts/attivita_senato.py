# -*- coding: utf-8 -*-
"""Interventi e interrogazioni dei senatori, dalla XIII alla XVI legislatura.

Dai file scaricati da scarica_senato.py (data/cache/zip_senato/<leg>/):

  interventi-senatore-ddl-date   ogni intervento su un disegno di legge, con
                                 la seduta: in Aula (numeroSedutaAssemblea) o
                                 in commissione. Solo sulle leggi: e' la stessa
                                 cosa che contano i siti della Camera per la XIV
                                 e la XV.
  sindisp-senatore-date          interrogazioni, interpellanze, mozioni che il
                                 senatore ha firmato: il file non dice chi e' il
                                 primo firmatario, quindi contano tutte.

Scrive data/attivita_senato.json: {id senatore: {legislatura: {'aula', 'commissione',
'interrogazioni', 'scritte', 'interpellanze', 'mozioni'}}}.
"""
import collections
import csv
import glob
import io
import json
import os
import sys

QUI = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(QUI, '..', 'data', 'cache', 'zip_senato')
USCITA = os.path.join(QUI, '..', 'data', 'attivita_senato.json')
ROMANI = {13: 'XIII', 14: 'XIV', 15: 'XV', 16: 'XVI'}
TIPI = {'Interrogazione': 'interrogazioni', 'Interrogazione con richiesta di risposta scritta': 'scritte',
        'Interpellanza': 'interpellanze', 'Mozione': 'mozioni'}

csv.field_size_limit(10 ** 7)
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass


def leggi(f):
    with io.open(f, encoding='utf-8', errors='replace', newline='') as fh:
        yield from csv.DictReader(fh)


def main():
    fuori = collections.defaultdict(dict)
    for n, leg in sorted(ROMANI.items()):
        tot = collections.Counter()
        for f in glob.glob(os.path.join(D, str(n), 'interventi-senatore-ddl-date', '*.csv')):
            s, c, visti = os.path.basename(f)[:-4], collections.Counter(), set()
            for r in leggi(f):
                k = (r['ddl'], r['dataSeduta'], r['numeroSedutaAssemblea'], r['commissione'])
                if k in visti:
                    continue
                visti.add(k)
                c['aula' if r['numeroSedutaAssemblea'] else 'commissione'] += 1
            if c:
                fuori[s].setdefault(leg, {}).update(c)
                tot.update(c)
        for f in glob.glob(os.path.join(D, str(n), 'sindisp-senatore-date', '*.csv')):
            s, c, visti = os.path.basename(f)[:-4], collections.Counter(), set()
            for r in leggi(f):
                if r['atto'] in visti or r['tipo'] not in TIPI:
                    continue
                visti.add(r['atto'])
                c[TIPI[r['tipo']]] += 1
            if c:
                fuori[s].setdefault(leg, {}).update(c)
                tot.update(c)
        print('%s: %s' % (leg, dict(tot)), flush=True)
    json.dump({'_nota': "Interventi sulle leggi (in Aula e in commissione) e atti di sindacato ispettivo firmati "
                        "dai senatori, XIII-XVI, dai file del Senato. Generato da scripts/attivita_senato.py.",
               'senatori': fuori},
              io.open(USCITA, 'w', encoding='utf-8', newline='\n'), ensure_ascii=False)
    print('senatori: %d' % len(fuori))


if __name__ == '__main__':
    main()
