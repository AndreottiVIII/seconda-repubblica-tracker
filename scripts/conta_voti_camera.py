# -*- coding: utf-8 -*-
"""I voti di ogni deputato, dalla XIII alla XVI legislatura.

La Camera li pubblica negli archivi votoNN.rdf.zip (dati.camera.it/ocd/dump),
uno per legislatura, divisi per anno: 33 GB di testo in tutto. Nel servizio di
interrogazione online ci sono solo dalla XVII; per la XII non ci sono affatto.
Gli archivi si leggono direttamente dallo zip, senza scompattarli.

Per ogni deputato e legislatura si contano:

  votazioni     in quante votazioni c'era un suo voto registrato
  espressi      favorevole, contrario o astenuto
  missione      "non ha votato" perche' in missione: non e' un'assenza
  assente       "non ha votato" e basta
  dissenso      voti espressi diversi da quello della maggioranza del suo
                gruppo, sulle votazioni palesi; il gruppo misto non conta,
                perche' una linea non ce l'ha
  fiducie       come ha votato su ogni votazione che la Camera segna come
                fiducia (dalla XIV: nella XIII il segno non c'e')
  gruppi        i gruppi con cui ha votato, col primo e l'ultimo giorno: un
                controllo dei cambi di casacca che non viene dai registri dei gruppi

Scrive data/voti_camera.json. Gira per ore? No: una decina di minuti.
"""
import collections
import io
import json
import os
import re
import sys
import time
import zipfile

QUI = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(QUI, '..', 'data', 'cache', 'zip_camera')
USCITA = os.path.join(QUI, '..', 'data', 'voti_camera.json')
ROMANI = {'13': 'XIII', '14': 'XIV', '15': 'XV', '16': 'XVI'}

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass


def votazioni():
    """{vs14_014_029: {data, fiducia, finale, segreta, titolo}}"""
    z = zipfile.ZipFile(os.path.join(D, 'votazione.rdf.zip'))
    fuori = collections.defaultdict(dict)
    with z.open(z.namelist()[0]) as f:
        for r in io.TextIOWrapper(f, encoding='utf-8', errors='replace'):
            p = r.rstrip(' .\n').split('\t')
            if len(p) < 3:
                continue
            m = re.search(r'/(vs(\d+)_\d+_\d+)>?$', p[0])
            if not m or m.group(2) not in ROMANI:
                continue
            k = p[1].strip('<>').rsplit('/', 1)[-1].split('#')[-1]
            o = p[2].strip()
            v = o[1:o.index('"', 1)] if o.startswith('"') else o
            if k == 'date':
                fuori[m.group(1)]['data'] = v[:8]
            elif k in ('richiestaFiducia', 'votazioneFinale', 'votazioneSegreta'):
                fuori[m.group(1)][k] = v == '1'
            elif k in ('favorevoli', 'contrari', 'astenuti'):
                # i totali ufficiali: l'elenco nominale a volte ha qualche nome in meno
                fuori[m.group(1)][k] = int(v) if v.isdigit() else None
            elif k == 'title':
                fuori[m.group(1)]['titolo'] = v
            elif k == 'description':
                fuori[m.group(1)]['descrizione'] = re.sub(r'\s+', ' ', v).strip()
    return fuori


SCELTE = {'Favorevole': 'F', 'Contrario': 'C', 'Astensione': 'A'}


def main():
    t0 = time.time()
    meta = votazioni()
    print('votazioni XIII-XVI: %d, fiducie: %d' % (
        len(meta), sum(1 for v in meta.values() if v.get('richiestaFiducia'))))

    stat = collections.defaultdict(lambda: collections.Counter())
    fiducie = collections.defaultdict(list)          # (pid, leg) -> [[vs, scelta]]
    # (pid, leg) -> {codice del gruppo: [primo giorno, ultimo giorno, sigla]}: il
    # codice e' quello del registro dei gruppi (gr474), la sigla cambia anche
    # quando il gruppo resta lo stesso (IR, IRNP, PT) e nel misto dice la componente
    gruppi = collections.defaultdict(dict)
    riaperte = 0
    chiuse = set()

    def chiudi(vs, voti):
        """voti: [(pid, scelta, sigla, missione)] di una votazione."""
        nonlocal riaperte
        if vs in chiuse:
            riaperte += 1
        chiuse.add(vs)
        m = meta.get(vs, {})
        leg = vs[2:4]
        palese = not m.get('votazioneSegreta')
        linea = {}
        if palese:
            conta = collections.defaultdict(collections.Counter)
            for pid, s, g, _, _ in voti:
                if s in 'FCA':
                    conta[g][s] += 1
            for g, c in conta.items():
                (s1, n1), *resto = c.most_common(2) + [(None, 0)]
                # una linea c'e' solo se e' netta: con un pareggio no
                if g and not g.upper().startswith('MIST') and n1 >= 2 and n1 > resto[0][1]:
                    linea[g] = s1
        data = m.get('data', '')
        for pid, s, g, missione, gid in voti:
            c = stat[(pid, leg)]
            c['votazioni'] += 1
            if s in 'FCA':
                c['espressi'] += 1
                if g in linea:
                    c['con_linea'] += 1
                    if s != linea[g]:
                        c['dissenso'] += 1
            elif missione:
                c['missione'] += 1
            else:
                c['assente'] += 1
            if m.get('richiestaFiducia'):
                fiducie[(pid, leg)].append([vs, s if s in 'FCA' else ('M' if missione else 'N')])
            if gid and data:
                gg = gruppi[(pid, leg)].setdefault(gid, [data, data, g])
                if data < gg[0]:
                    gg[0] = data
                if data > gg[1]:
                    gg[1] = data

    for leg in sorted(ROMANI):
        z = zipfile.ZipFile(os.path.join(D, 'voto%s.rdf.zip' % leg))
        for info in sorted(z.infolist(), key=lambda i: i.filename):
            corrente, voti, voto = None, [], {}
            with z.open(info) as f:
                for r in io.TextIOWrapper(f, encoding='utf-8', errors='replace'):
                    if '<ocd:voto ' in r:
                        voto = {}
                    elif 'rif_votazione' in r:
                        m = re.search(r'(vs\d+_\d+_\d+)', r)
                        voto['vs'] = m.group(1) if m else None
                    elif 'rif_deputato' in r:
                        m = re.search(r'/d(\d+)_\d+', r)
                        voto['pid'] = m.group(1) if m else None
                    elif '<dc:type>' in r:
                        voto['tipo'] = r.split('<dc:type>')[1].split('<')[0]
                    elif 'rif_gruppoParlamentare' in r:
                        m = re.search(r'/(gr\d+)', r)
                        voto['gid'] = m.group(1) if m else None
                    elif 'siglaGruppo' in r:
                        voto['g'] = re.sub(r'<[^>]+>', '', r).strip()
                    elif '<dc:description>' in r:
                        voto['desc'] = r.lower()
                    elif '</ocd:voto>' in r:
                        if not voto.get('vs') or not voto.get('pid'):
                            continue
                        if voto['vs'] != corrente:
                            if corrente:
                                chiudi(corrente, voti)
                            corrente, voti = voto['vs'], []
                        s = SCELTE.get(voto.get('tipo'), 'N')
                        voti.append((voto['pid'], s, voto.get('g', ''),
                                     'mission' in voto.get('desc', ''), voto.get('gid')))
                if corrente:
                    chiudi(corrente, voti)
            print('  %s: %d votazioni lette, %.0f s' % (info.filename, len(chiuse), time.time() - t0))
            sys.stdout.flush()

    fuori = {}
    for (pid, leg), c in stat.items():
        v = dict(c)
        if fiducie.get((pid, leg)):
            v['fiducie'] = fiducie[(pid, leg)]
        if gruppi[(pid, leg)]:
            v['gruppi'] = sorted(([g] + x for g, x in gruppi[(pid, leg)].items()),
                                 key=lambda x: x[1])
        fuori.setdefault(pid, {})[ROMANI[leg]] = v
    fid = {vs: {'data': m.get('data'), 'titolo': m.get('titolo'), 'descrizione': m.get('descrizione'),
                'ufficiale': [m.get('favorevoli'), m.get('contrari'), m.get('astenuti')]}
           for vs, m in meta.items() if m.get('richiestaFiducia')}
    json.dump({'_nota': 'Voti dei deputati XIII-XVI dagli archivi votoNN.rdf.zip della Camera. '
                        'Generato da scripts/conta_voti_camera.py.',
               'fiducie': fid, 'deputati': fuori},
              open(USCITA, 'w', encoding='utf-8', newline='\n'), ensure_ascii=False)
    print('deputati: %d; votazioni non contigue nei file: %d; %.0f s'
          % (len(fuori), riaperte, time.time() - t0))


if __name__ == '__main__':
    main()
