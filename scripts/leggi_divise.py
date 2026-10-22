# -*- coding: utf-8 -*-
"""Le leggi che hanno diviso la Camera: come ha votato ognuno, 1996-2013.

Due elenchi:
  scelte     le votazioni finali scelte con Davide (22 leggi note, tutte a voto
             palese: quelle a scrutinio segreto i nomi non li hanno)
  automatiche le 10 votazioni finali palesi con piu' deputati che hanno votato
             diversamente dal proprio gruppo

Per ogni votazione: i totali ufficiali, gruppo per gruppo quanti si', no,
astenuti e quanti non hanno votato, e i nomi di chi ha votato diversamente
dalla linea del suo gruppo (la scelta della maggioranza dei suoi votanti; il
misto escluso, che una linea non ce l'ha).

Legge gli archivi votoNN.rdf.zip e votazione.rdf.zip (come
riassunto_voti_camera.py). Scrive data/leggi_divise.json.
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
sys.path.insert(0, QUI)
import riassunto_voti_camera as rv

D = os.path.join(QUI, '..', 'data', 'cache', 'zip_camera')
USCITA = os.path.join(QUI, '..', 'data', 'leggi_divise.json')
SCELTE = [
    ('vs13_273_308', 'Turco-Napolitano (immigrazione)'),
    ('vs13_247_064', 'Riforma della maturità (Berlinguer)'),
    ('vs13_542_005', 'Procreazione assistita, prima versione'),
    ('vs13_869_049', 'Riforma del Titolo V (federalismo)'),
    ('vs14_030_001', 'Riforma del diritto societario (falso in bilancio)'),
    ('vs14_039_001', 'Rogatorie Italia-Svizzera'),
    ('vs14_153_001', 'Bossi-Fini (immigrazione)'),
    ('vs14_214_117', 'Legge Biagi (mercato del lavoro)'),
    ('vs14_325_067', 'Lodo Schifani (processi alle alte cariche)'),
    ('vs14_489_029', 'Conflitto di interessi (Frattini)'),
    ('vs14_659_010', "Riforma dell'ordinamento giudiziario (Castelli)"),
    ('vs14_660_001', 'Missione in Iraq'),
    ('vs14_692_001', 'Riforma della Costituzione, "devolution"'),
    ('vs15_033_026', 'Indulto'),
    ('vs16_032_031', 'Lodo Alfano'),
    ('vs16_151_110', 'Federalismo fiscale'),
    ('vs16_177_049', 'Pacchetto sicurezza (reato di clandestinità)'),
    ('vs16_277_062', 'Legittimo impedimento'),
    ('vs16_404_112', "Riforma Gelmini dell'università"),
    ('vs16_463_138', 'Prescrizione breve'),
    ('vs16_598_012', 'Pareggio di bilancio in Costituzione'),
    ('vs16_657_029', 'Riforma Fornero del lavoro'),
]
QUANTE_AUTO = 10

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass


def esamina(voti):
    """voti: [(pid, scelta, sigla, gid)] -> gruppi, linea, diversi."""
    gruppi = collections.defaultdict(collections.Counter)
    sigla = {}
    for pid, s, g, gid in voti:
        gruppi[gid][s] += 1
        sigla[gid] = g
    linea = {}
    for gid, c in gruppi.items():
        espressi = collections.Counter({k: v for k, v in c.items() if k in 'FCA'})
        (s1, n1), *resto = espressi.most_common(2) + [(None, 0)]
        if gid and not (sigla.get(gid) or '').upper().startswith(('MIST', 'M-')) and n1 >= 2 and n1 > resto[0][1]:
            linea[gid] = s1
    diversi = [[pid, sigla.get(gid, ''), s, linea[gid]] for pid, s, g, gid in voti
               if gid in linea and s in 'FCA' and s != linea[gid]]
    return ({gid: [sigla.get(gid, ''), dict(c)] for gid, c in gruppi.items()}, linea, diversi)


def main():
    t0 = time.time()
    meta = rv.votazioni()
    scelte = dict(SCELTE)
    finali = {vs for vs, m in meta.items() if m.get('votazioneFinale') and not m.get('votazioneSegreta')}
    print('finali palesi: %d' % len(finali), flush=True)
    raccolti = {}                 # vs -> esame, solo per le scelte e le finali
    for leg in sorted(rv.ROMANI):
        z = zipfile.ZipFile(os.path.join(D, 'voto%s.rdf.zip' % leg))
        for info in sorted(z.infolist(), key=lambda i: i.filename):
            per_vs, voto = collections.defaultdict(list), {}
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
                    elif '</ocd:voto>' in r and voto.get('pid') and (voto.get('vs') in finali or voto.get('vs') in scelte):
                        s = rv.SCELTE.get(voto.get('tipo'), 'M' if 'mission' in voto.get('desc', '') else 'N')
                        per_vs[voto['vs']].append((voto['pid'], s, voto.get('g', ''), voto.get('gid')))
            for vs, voti in per_vs.items():
                raccolti[vs] = esamina(voti)
            print('  %s: %.0f s' % (info.filename, time.time() - t0), flush=True)

    def scheda(vs, nome):
        m = meta.get(vs, {})
        gruppi, linea, diversi = raccolti.get(vs, ({}, {}, []))
        return {'vs': vs, 'nome': nome, 'data': m.get('data'), 'descrizione': m.get('descrizione', ''),
                'si': m.get('favorevoli'), 'no': m.get('contrari'), 'astenuti': m.get('astenuti'),
                'approvata': bool(m.get('approvato')), 'scheda': m.get('scheda', ''),
                'gruppi': [[g[0], g[1].get('F', 0), g[1].get('C', 0), g[1].get('A', 0),
                            g[1].get('M', 0), g[1].get('N', 0), linea.get(gid, '')]
                           for gid, g in sorted(gruppi.items(), key=lambda x: -sum(x[1][1].values()))],
                'diversi': diversi}

    fuori_scelte = [scheda(vs, nome) for vs, nome in SCELTE]
    mancano = [s['nome'] for s in fuori_scelte if not s['gruppi']]
    auto = sorted((vs for vs in finali if vs in raccolti and vs not in scelte),
                  key=lambda vs: (-len(raccolti[vs][2]), meta[vs].get('data', '')))[:QUANTE_AUTO]
    fuori_auto = [scheda(vs, '') for vs in auto]
    json.dump({'_nota': "Votazioni finali palesi alla Camera, voto per voto: 22 leggi scelte e le 10 con piu' "
                        "voti diversi dal proprio gruppo. Generato da scripts/leggi_divise.py.",
               'scelte': fuori_scelte, 'automatiche': fuori_auto},
              io.open(USCITA, 'w', encoding='utf-8', newline='\n'), ensure_ascii=False)
    print('fatto: %d scelte (senza voti: %s), %d automatiche; %.0f s'
          % (len(fuori_scelte), mancano, len(fuori_auto), time.time() - t0))
    for x in fuori_auto:
        print('  auto', x['data'], len(x['diversi']), x['descrizione'][:90])


if __name__ == '__main__':
    main()
