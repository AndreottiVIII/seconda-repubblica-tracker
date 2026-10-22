# -*- coding: utf-8 -*-
"""Nome e data di nascita di ogni senatore della XIII-XVI, col suo numero del Senato.

Serve a genera_sito.py per agganciare i dati del Senato (voti_senato.json,
attivita_senato.json) alle schede di chi nell'elenco non ha il numero del
Senato: soprattutto i senatori a vita (Andreotti, Agnelli, Bobbio...). Il
lavoro notturno su GitHub i file grandi non li ha: questo e' piccolo e si
versiona. Legge data/cache/zip_senato/<leg>/senatori-legislatura.csv, scrive
data/senatori_anagrafe.json: {numero: [nome, cognome, nascita]}.
"""
import csv
import glob
import io
import json
import os

QUI = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(QUI, '..', 'data', 'cache', 'zip_senato')
USCITA = os.path.join(QUI, '..', 'data', 'senatori_anagrafe.json')


def main():
    fuori = {}
    for f in sorted(glob.glob(os.path.join(D, '*', 'senatori-legislatura.csv'))):
        for r in csv.DictReader(io.open(f, encoding='utf-8')):
            fuori[r['senatore'].rsplit('/', 1)[-1]] = [r['nome'], r['cognome'], r['dataNascita']]
    json.dump(fuori, io.open(USCITA, 'w', encoding='utf-8', newline='\n'), ensure_ascii=False, indent=0)
    print('senatori: %d' % len(fuori))


if __name__ == '__main__':
    main()
