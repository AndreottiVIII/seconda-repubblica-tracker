# -*- coding: utf-8 -*-
"""Che fine hanno fatto le proposte di legge dei senatori, dalla XIII alla XVI.

Dai file ddl-senatore-date scaricati da scarica_senato.py: ogni proposta che il
senatore ha firmato, con lo stato della fase al Senato; flagPrimoFirmatario=1
quando e' il primo firmatario. Contano solo quelle, come per i deputati
(proposte_leggi.py):

  legge             approvata definitivamente al Senato (l'ultimo voto e' li')
  approvata         approvata dal Senato e mandata alla Camera
  testo unificato   approvata insieme ad altre in un testo solo
  assorbita         assorbita da un'altra proposta

Scrive data/proposte_senato.json: {numero del senatore: [[legislatura, numero,
titolo, esito, data]]}.
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
USCITA = os.path.join(QUI, '..', 'data', 'proposte_senato.json')
ROMANI = {13: 'XIII', 14: 'XIV', 15: 'XV', 16: 'XVI'}

csv.field_size_limit(10 ** 7)
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass


def esito(stato):
    s = (stato or '').strip().lower()
    if s.startswith(('approvato definitivamente', 'appr. definit', 'appr. def.')):
        return 'legge'
    if s in ('approvato in testo unificato', 'appr. in t.u.'):
        return 'testo unificato'
    if s in ('approvato', 'approvato con modificazioni', 'appr. con modificaz'):
        return 'approvata'
    if s == 'assorbito':
        return 'assorbita'
    return None


def main():
    fuori = collections.defaultdict(list)
    for n, leg in sorted(ROMANI.items()):
        conta = collections.Counter()
        for f in glob.glob(os.path.join(D, str(n), 'ddl-senatore-date', '*.csv')):
            s, visti = os.path.basename(f)[:-4], set()
            for r in csv.DictReader(io.open(f, encoding='utf-8', errors='replace', newline='')):
                if r['flagPrimoFirmatario'] != '1' or r['ramo'] != 'S' or r['ddl'] in visti:
                    continue
                visti.add(r['ddl'])
                conta['proposte'] += 1
                e = esito(r['stato'])
                if e:
                    conta[e] += 1
                    fuori[s].append([leg, r['numeroFase'], (r['titolo'] or '').strip(), e,
                                     (r['dataStato'] or '').replace('-', '')])
        print('%s: %s' % (leg, dict(conta)), flush=True)
    for v in fuori.values():
        v.sort(key=lambda x: (x[4], x[1]))
    json.dump({'_nota': "Esito delle proposte di legge dei senatori (primo firmatario), XIII-XVI, dai file "
                        "ddl-senatore del Senato. Generato da scripts/proposte_senato.py.",
               'proposte': fuori},
              io.open(USCITA, 'w', encoding='utf-8', newline='\n'), ensure_ascii=False, indent=0)
    print('senatori con almeno una proposta arrivata a un esito: %d' % len(fuori))


if __name__ == '__main__':
    main()
