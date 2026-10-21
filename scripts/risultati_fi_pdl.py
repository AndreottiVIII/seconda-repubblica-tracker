# -*- coding: utf-8 -*-
"""Forza Italia e il Popolo della Liberta' alle elezioni della Camera, 1994-2008.

La quota proporzionale (1994-2001) e il voto di lista (2006, 2008), sommati
comune per comune dagli open data del Ministero dell'Interno (Eligendo), in
Italia: senza la Valle d'Aosta, che vota a parte, e senza l'estero. Gli zip
stanno in data/cache/eligendo/ (vedi collegi_eligendo.py). Per la scheda di
Berlusconi. Scrive data/risultati_fi_pdl.json.
"""
import collections
import csv
import io
import json
import os

QUI = os.path.dirname(os.path.abspath(__file__))
ESTRATTI = os.path.join(QUI, '..', 'data', 'cache', 'eligendo', 'estratti')
USCITA = os.path.join(QUI, '..', 'data', 'risultati_fi_pdl.json')
FILE = [('1994', 'camera-19940327/camera-19940327_Proporzionale.txt', 'VOTI_LISTA', 'FORZA ITALIA'),
        ('1996', 'camera-19960421/camera-19960421_Proporzionale.txt', 'VOTI_LISTA', 'FORZA ITALIA'),
        ('2001', 'camera-20010513/camera-20010513_Proporzionale.txt', 'VOTI_LISTA', 'FORZA ITALIA'),
        ('2006', 'camera-20060409/camera_italia-20060409.txt', 'VOTILISTA', 'FORZA ITALIA'),
        ('2008', 'camera-20080413/camera_italia-20080413.txt', 'VOTI_LISTA', "IL POPOLO DELLA LIBERTA'")]


def main():
    fuori = []
    for anno, nome, colonna, lista in FILE:
        voti = collections.Counter()
        with io.open(os.path.join(ESTRATTI, nome), encoding='latin-1', newline='') as f:
            for r in csv.DictReader(f, delimiter=';'):
                v = (r[colonna] or '0').replace(',00', '').replace('.', '')
                voti[r['LISTA'].strip()] += int(float(v or 0))
        totale = sum(voti.values())
        classifica = [k for k, _ in voti.most_common()]
        fuori.append({'anno': anno, 'lista': lista, 'voti': voti[lista],
                      'percentuale': round(100 * voti[lista] / totale, 1),
                      'posto': classifica.index(lista) + 1, 'primo': classifica[0],
                      'primo_voti': voti[classifica[0]], 'validi': totale})
        print(fuori[-1])
    json.dump({'_nota': "Forza Italia (1994-2006) e PdL (2008) alla Camera, voti di lista in Italia "
                        "senza Valle d'Aosta ed estero, dagli open data del Ministero dell'Interno. "
                        "Generato da scripts/risultati_fi_pdl.py.", 'elezioni': fuori},
              io.open(USCITA, 'w', encoding='utf-8', newline='\n'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
