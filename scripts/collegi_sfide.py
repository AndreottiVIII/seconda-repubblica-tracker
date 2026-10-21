# -*- coding: utf-8 -*-
"""Le sfide nei collegi uninominali del 1994, 1996 e 2001, Camera e Senato.

Per ogni collegio: chi e' arrivato primo e chi secondo, con quanti voti, e
dov'e' nato chi ha vinto. Legge gli stessi file di collegi_eligendo.py
(open data del Ministero dell'Interno, Eligendo) e le sue schede agganciate
(data/collegi.json), per collegare i nomi alle schede del sito.

La regione di nascita: il luogo di nascita dei candidati e' un comune, scritto
in maiuscolo. La regione di ogni comune viene dagli stessi archivi del Senato,
che elencano tutti i comuni d'Italia con la loro regione. Un comune che porta
lo stesso nome in due regioni resta senza regione (meglio niente che il
sbagliato); un luogo che negli archivi non c'e' (nati all'estero, comuni
scomparsi o scritti diversamente) pure.

Scrive data/collegi_sfide.json.
"""
import collections
import csv
import glob
import io
import json
import os
import re
import sys

QUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, QUI)
import collegi_eligendo as ce

USCITA = os.path.join(QUI, '..', 'data', 'collegi_sfide.json')
COLLEGI = os.path.join(QUI, '..', 'data', 'collegi.json')

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass


def regione_di_circ(circ):
    """'PIEMONTE 1' -> 'PIEMONTE'; le circoscrizioni della Camera sono regioni numerate."""
    return re.sub(r'\s+\d+$', '', circ.strip()).strip()


def nome_regione(r):
    r = ce.norm(r)
    return {'TRENTINOALTOADIGE': "Trentino-Alto Adige", 'FRIULIVENEZIAGIULIA': 'Friuli-Venezia Giulia',
            'EMILIAROMAGNA': 'Emilia-Romagna', 'VALLEDAOSTA': "Valle d'Aosta", 'ABRUZZI': 'Abruzzo',
            'ABRUZZO': 'Abruzzo'}.get(r, r.capitalize())


def comuni_e_regioni():
    """{COMUNE normalizzato: regione}, solo per i nomi che stanno in una regione sola."""
    regioni = collections.defaultdict(set)
    for f in glob.glob(os.path.join(ce.ESTRATTI, 'senato-*', 'senato-*.txt')):
        with io.open(f, encoding='latin-1', newline='') as fh:
            for r in csv.DictReader(fh, delimiter=';'):
                regioni[ce.norm(r['COMUNE'])].add(nome_regione(r['REGIONE']))
    fuori = {c: next(iter(v)) for c, v in regioni.items() if len(v) == 1}
    # come li scrivono i candidati e come li scrive il Senato
    for detto, vero in (('REGGIOCALABRIA', 'REGGIODICALABRIA'), ('REGGIOEMILIA', 'REGGIONELLEMILIA')):
        if vero in fuori:
            fuori[detto] = fuori[vero]
    return fuori


def persona(c):
    """'FRANCESCO DETTO FRANCO', 'CORLEONE' -> 'Franco Corleone'; via il cognome da sposata."""
    nome, cognome = c[3].upper(), re.sub(r'\s+IN\s+.*$', '', c[2].upper())
    nome = re.sub(r'\s+IN\s+.*$', '', nome)
    m = re.search(r'\bDETT[OA]\s+(.+)$', nome)
    if m:
        detto = m.group(1).strip()
        return detto.title() if cognome.split()[0] in detto.split() else ('%s %s' % (detto, cognome)).title()
    return ('%s %s' % (nome, cognome)).strip().title()


def main():
    comuni = comuni_e_regioni()
    print('comuni con una regione sola: %d' % len(comuni))
    schede = json.load(io.open(COLLEGI, encoding='utf-8'))['collegi']
    # (anno, ramo, collegio, voti) -> qid: come collegi_eligendo le ha agganciate
    chi = {(r[0], r[1], r[2], r[3]): q for q, v in schede.items() for r in v}
    # i collegi dove il primo nei voti non e' chi e' stato eletto (Monterotondo 1996):
    # collegi_eligendo.py li lascia fuori dalle schede, e qui fuori pure
    dubbi = {(r[0], r[1], r[2]) for r in json.load(io.open(COLLEGI, encoding='utf-8'))['non_agganciati']
             if r[3] == 'il primo nei voti non risulta eletto'}

    fuori, senza_regione = [], collections.Counter()
    for anno in sorted(ce.ANNI):
        for ramo, leggi in (('C', ce.camera), ('S', ce.senato)):
            collegi = collections.defaultdict(list)
            for c in leggi(anno):
                collegi[(c[0], c[1])].append(c)
            for (zona, coll), tutti in sorted(collegi.items()):
                tutti.sort(key=lambda c: -c[5])
                totale = sum(c[5] for c in tutti)
                if len(tutti) < 2 or not totale or (anno, ramo, coll) in dubbi:
                    continue
                p, s = tutti[0], tutti[1]
                bel = ce.bel_nome(coll)
                luogo = re.sub(r'\s*\(.*\)\s*$', '', p[8]).strip()
                nato_in = comuni.get(ce.norm(luogo), '')
                if not nato_in:
                    senza_regione[luogo] += 1
                regione = nome_regione(regione_di_circ(zona) if ramo == 'C' else zona)
                fuori.append([anno, ramo, regione, bel,
                              persona(p), chi.get((anno, ramo, bel, p[5]), ''), p[5],
                              round(1000 * p[5] / totale) / 10,
                              persona(s), chi.get((anno, ramo, bel, s[5]), ''), s[5],
                              round(1000 * s[5] / totale) / 10,
                              luogo.title(), nato_in])
    print('collegi: %d; vincitori senza regione di nascita: %d' % (len(fuori), sum(senza_regione.values())))
    print('  i piu\' frequenti:', senza_regione.most_common(12))
    json.dump({'_nota': "Collegi uninominali 1994-2001: [anno, ramo, regione, collegio, primo, qid, voti, %, "
                        "secondo, qid, voti, %, nato a, regione di nascita]. Open data del Ministero "
                        "dell'Interno (Eligendo). Generato da scripts/collegi_sfide.py.",
               'collegi': fuori},
              io.open(USCITA, 'w', encoding='utf-8', newline='\n'), ensure_ascii=False, indent=0)


if __name__ == '__main__':
    main()
