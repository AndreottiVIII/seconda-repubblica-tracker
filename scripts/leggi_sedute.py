# -*- coding: utf-8 -*-
"""Le leggi pubblicate governo per governo, e le sedute della Camera anno per anno.

Dagli archivi della Camera (data/cache/zip_camera/):

  legge.rdf.zip    ogni legge con data e titolo. Dal 10 maggio 1994 (il
                   governo Berlusconi I; prima c'era Ciampi) al 14 marzo
                   2013, ogni legge va al governo in carica quel giorno
                   (genera_sito.governo_al): conta chi governava quando e'
                   stata pubblicata, non chi l'ha proposta. I titoli dicono il
                   tipo: "Conversione in legge del decreto-legge" e' un decreto
                   del governo convertito, "Ratifica ed esecuzione" un trattato.
  seduta.rdf.zip   le sedute dell'Assemblea (sNN_numero), con la data.

Scrive data/leggi_sedute.json.
"""
import collections
import io
import json
import os
import re
import sys
import zipfile

QUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, QUI)
D = os.path.join(QUI, '..', 'data', 'cache', 'zip_camera')
USCITA = os.path.join(QUI, '..', 'data', 'leggi_sedute.json')
# le leggi dal giuramento del primo governo del periodo: prima governava Ciampi
DA_LEGGI, DA, A = '19940510', '19940415', '20130314'
ROMANI = {'12': 'XII', '13': 'XIII', '14': 'XIV', '15': 'XV', '16': 'XVI'}

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass


def triple(nome, prefisso):
    z = zipfile.ZipFile(os.path.join(D, nome))
    with z.open(z.namelist()[0]) as f:
        for r in io.TextIOWrapper(f, encoding='utf-8', errors='replace'):
            p = r.rstrip(' .\n').split('\t')
            if len(p) < 3 or not p[0].startswith(prefisso):
                continue
            k = p[1].strip('<>').rsplit('/', 1)[-1].split('#')[-1]
            o = p[2].strip()
            v = o[1:o.index('"', 1)] if o.startswith('"') else o.strip('<>')
            v = v.encode('utf-8').decode('unicode_escape', 'ignore') if '\\u' in v else v
            yield p[0].strip('<>'), k, v


def tipo(titolo):
    t = titolo.lower()
    if t.startswith('conversione in legge') or 'conversione in legge' in t[:60]:
        return 'decreti'
    if t.startswith(('ratifica', 'adesione')) or 'ratifica ed esecuzione' in t[:40]:
        return 'ratifiche'
    return 'altre'


def main():
    import genera_sito
    leggi = collections.defaultdict(dict)
    for s, k, v in triple('legge.rdf.zip', '<http://dati.camera.it/ocd/legge.rdf/L'):
        if k in ('date', 'title'):
            leggi[s][k] = v
    per_gov = collections.defaultdict(collections.Counter)
    titoli = collections.defaultdict(list)
    for s, x in leggi.items():
        d = (x.get('date') or '')[:8]
        if not (DA_LEGGI <= d <= A) or not x.get('title'):
            continue
        gov = genera_sito.governo_al(d)
        t = re.sub(r'\s+', ' ', x['title']).strip()
        n = s.rsplit('_', 1)[-1]
        per_gov[gov]['totale'] += 1
        per_gov[gov][tipo(t)] += 1
        titoli[gov].append([d, n, t[:300]])
    for v in titoli.values():
        v.sort()
    print({g: dict(c) for g, c in per_gov.items()})

    sedute = collections.defaultdict(dict)
    for s, k, v in triple('seduta.rdf.zip', '<http://dati.camera.it/ocd/seduta.rdf/s'):
        m = re.search(r'/s(\d+)_(\d+)$', s)
        if m and m.group(1) in ROMANI and k == 'date':
            sedute[s] = v[:8]
    per_anno = collections.Counter(d[:4] for d in sedute.values() if DA <= d <= A)
    per_leg = collections.Counter(ROMANI[re.search(r'/s(\d+)_', s).group(1)] for s in sedute)
    print('sedute per anno', dict(sorted(per_anno.items())), dict(per_leg))
    json.dump({'_nota': "Leggi pubblicate dal 10 maggio 1994 al 14 marzo 2013, col governo in carica quel giorno, "
                        "e sedute dell'Assemblea della Camera. Dagli archivi legge.rdf e seduta.rdf della Camera. "
                        "Generato da scripts/leggi_sedute.py.",
               'leggi': {g: dict(c) for g, c in per_gov.items()}, 'titoli': titoli,
               'sedute': {'anni': dict(sorted(per_anno.items())), 'legislature': dict(per_leg)}},
              io.open(USCITA, 'w', encoding='utf-8', newline='\n'), ensure_ascii=False)


if __name__ == '__main__':
    main()
