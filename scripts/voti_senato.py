# -*- coding: utf-8 -*-
"""I voti di ogni senatore, dalla XIII alla XVI legislatura.

Dai file scaricati da scarica_senato.py (data/cache/zip_senato/<leg>/):
votazioni-senatore/<id>.csv ha una riga per ogni ruolo del senatore in ogni
votazione: 'presente', 'votante', e la scelta ('favorevole', 'contrario',
'astenuto'); chi presiede e' 'presidente'. Chi e' assente non compare.

Per ogni senatore e legislatura si contano:

  votazioni   quelle tenute mentre era in carica (senatori-legislatura.csv)
  espressi    favorevole, contrario o astenuto
  presente    in aula senza votare (presidente, presente non votante)
  assente     non compare: il Senato non segna le missioni, che qui stanno dentro
  con_linea   voti espressi quando il suo gruppo ha una linea netta (misto escluso)
  dissenso    di quelli, i voti diversi dalla linea

Fuori dal conto le verifiche del numero legale e le controprove (la stessa
votazione ripetuta). Le fiducie qui non si riconoscono: l'oggetto delle
votazioni non lo dice.

Scrive data/voti_senato.json. Gira per qualche minuto per legislatura.
"""
import collections
import csv
import glob
import io
import json
import os
import sys
import time

QUI = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(QUI, '..', 'data', 'cache', 'zip_senato')
USCITA = os.path.join(QUI, '..', 'data', 'voti_senato.json')
ROMANI = {13: 'XIII', 14: 'XIV', 15: 'XV', 16: 'XVI'}
FUORI = ('verifica del numero legale', 'controprova')
SCELTA = {'favorevole': 'F', 'contrario': 'C', 'astenuto': 'A'}

csv.field_size_limit(10 ** 7)
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass


def leggi(f):
    with io.open(f, encoding='utf-8', errors='replace', newline='') as fh:
        yield from csv.DictReader(fh)


def legislatura(n):
    cartella = os.path.join(D, str(n))
    mandati = collections.defaultdict(list)
    for r in leggi(os.path.join(cartella, 'senatori-legislatura.csv')):
        s = r['senatore'].rsplit('/', 1)[-1]
        mandati[s].append((r['inizioMandato'].replace('-', ''), (r['fineMandato'] or '99999999').replace('-', '')))
    gruppi = collections.defaultdict(list)
    for f in glob.glob(os.path.join(cartella, 'incarichi-senatore-gruppi', '*.csv')):
        s = os.path.basename(f)[:-4]
        for r in leggi(f):
            gruppi[s].append((r['inizioAdesione'].replace('-', ''), (r['fineAdesione'] or '99999999').replace('-', ''),
                              r['gruppo'].rsplit('/', 1)[-1], r['nomeGruppo']))

    def gruppo_al(s, giorno):
        for a, b, g, nome in gruppi.get(s, []):
            if a <= giorno <= b:
                return g, nome
        return None, ''

    votazioni, oggetti = {}, {}                      # uri -> data, oggetto
    voti = collections.defaultdict(dict)             # uri -> {senatore: scelta}
    for f in glob.glob(os.path.join(cartella, 'votazioni-senatore', '*.csv')):
        s = os.path.basename(f)[:-4]
        for r in leggi(f):
            if (r['oggetto'] or '').strip().strip('"').lower().startswith(FUORI):
                continue
            u = r['votazione']
            votazioni[u] = r['dataSeduta'].replace('-', '')
            oggetti[u] = (r['oggetto'] or '').strip().strip('"')
            ruolo = r['voto'].rsplit('/', 1)[-1]
            v = voti[u]
            if ruolo in SCELTA:
                v[s] = SCELTA[ruolo]
            elif s not in v or v[s] == 'P':
                v[s] = 'P'                            # in aula: presente, votante, presidente
    print('  %s: %d votazioni, %d senatori' % (ROMANI[n], len(votazioni), len(mandati)), flush=True)

    conta = collections.defaultdict(collections.Counter)
    # il riassunto della legislatura: totali, mesi, gruppi, votazioni strette
    tot, mesi = collections.Counter(), collections.defaultdict(collections.Counter)
    per_g, nomi_g, strette = collections.defaultdict(collections.Counter), {}, []
    for u, giorno in votazioni.items():
        v = voti[u]
        sc = collections.Counter(x for x in v.values() if x in 'FCA')
        tot['votazioni'] += 1
        # al Senato, fino al 2017, chi si astiene vota contro: passa se i si' superano no e astenuti
        tot['approvate'] += sc['F'] > sc['C'] + sc['A']
        if sum(sc.values()) >= 200:
            strette.append([abs(sc['F'] - sc['C'] - sc['A']), giorno, u, oggetti.get(u, '')[:250],
                            sc['F'], sc['C'], sc['A'], sc['F'] > sc['C'] + sc['A']])
        linea, per_gruppo = {}, collections.defaultdict(collections.Counter)
        for s, x in v.items():
            if x in 'FCA':
                g, nome = gruppo_al(s, giorno)
                if g and not nome.lower().startswith('misto'):
                    per_gruppo[g][x] += 1
        for g, c in per_gruppo.items():
            (s1, n1), *resto = c.most_common(2) + [(None, 0)]
            if n1 >= 2 and n1 > resto[0][1]:
                linea[g] = s1
        for s, periodi in mandati.items():
            if not any(a <= giorno <= b for a, b in periodi):
                continue
            c = conta[s]
            c['votazioni'] += 1
            x = v.get(s)
            g0, nome0 = gruppo_al(s, giorno)
            k = 'assente' if x is None else 'presente' if x == 'P' else 'espressi'
            for cc in (tot, mesi[giorno[:6]], per_g[g0]):
                cc['voti'] += 1
                cc[k] += 1
            if g0:
                nomi_g[g0] = nome0
            if x in ('F', 'C', 'A') and g0 in linea:
                for cc in (tot, mesi[giorno[:6]], per_g[g0]):
                    cc['con_linea'] += 1
                    cc['diversi'] += x != linea[g0]
            if x is None:
                c['assente'] += 1
            elif x == 'P':
                c['presente'] += 1
            else:
                c['espressi'] += 1
                g, _ = gruppo_al(s, giorno)
                if g in linea:
                    c['con_linea'] += 1
                    c['dissenso'] += x != linea[g]
    strette.sort(key=lambda x: (x[0], x[1]))
    riassunto = {'totali': dict(tot), 'mesi': {m: dict(c) for m, c in sorted(mesi.items())},
                 'gruppi': [dict(c, nome=nomi_g.get(g, ''), leg=ROMANI[n]) for g, c in per_g.items()
                            if g and c['voti'] >= 5000],
                 'strette': [x[1:] for x in strette[:40]]}
    return {s: dict(c) for s, c in conta.items()}, riassunto


def main():
    t0 = time.time()
    fuori, riassunti = {}, {}
    for n, leg in sorted(ROMANI.items()):
        senatori, riassunti[leg] = legislatura(n)
        for s, c in senatori.items():
            fuori.setdefault(s, {})[leg] = c
        print('%s fatta, %.0f s' % (leg, time.time() - t0), flush=True)
    json.dump({'_nota': "Voti dei senatori XIII-XVI dai file votazioni-senatore del Senato: votazioni durante "
                        "il mandato, voti espressi, presenti senza votare, assenti (missioni comprese), voti "
                        "diversi dalla linea del gruppo. Generato da scripts/voti_senato.py.",
               'senatori': fuori, 'riassunto': riassunti},
              io.open(USCITA, 'w', encoding='utf-8', newline='\n'), ensure_ascii=False)
    print('senatori: %d; %.0f s' % (len(fuori), time.time() - t0))


if __name__ == '__main__':
    main()
