# -*- coding: utf-8 -*-
"""Le nostre schede contro l'anagrafe della Camera, archivio per archivio.

Non corregge niente: elenca le differenze, perche' ognuna va guardata. Cinque
controlli:

  1. chi ha seduto alla Camera fra la XII e la XVI e da noi non c'e';
  2. il sesso;
  3. le legislature alla Camera;
  4. le date di inizio e fine dei mandati;
  5. chi la Camera dice uscito per decesso e da noi risulta vivo.

Legge gli archivi in data/cache/zip_camera/ (scarica_elenco non li usa: e'
un controllo esterno, fatto con una fonte diversa da quella che ha costruito
le schede). Scrive data/controllo_camera.json.
"""
import collections
import io
import json
import os
import re
import sys
import zipfile

QUI = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(QUI, '..', 'data', 'cache', 'zip_camera')
ELENCO = os.path.join(QUI, '..', 'data', 'elenco.json')
USCITA = os.path.join(QUI, '..', 'data', 'controllo_camera.json')
ROMANI = {'12': 'XII', '13': 'XIII', '14': 'XIV', '15': 'XV', '16': 'XVI'}

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass


def triple(nome):
    z = zipfile.ZipFile(os.path.join(D, nome + '.rdf.zip'))
    with z.open(z.namelist()[0]) as f:
        for r in io.TextIOWrapper(f, encoding='utf-8', errors='replace'):
            p = r.rstrip(' .\n').split('\t')
            if len(p) >= 3:
                yield (p[0].strip('<>'), p[1].strip('<>').rsplit('/', 1)[-1].split('#')[-1],
                       p[2].strip())


def val(o):
    return o[1:o.rindex('"')] if o.startswith('"') else o.strip('<>')


def main():
    persone = json.load(open(ELENCO, encoding='utf-8'))['persone']
    per_id = {p['id_camera']: p for p in persone if p.get('id_camera')}

    # i mandati alla Camera, XII-XVI
    mandati = collections.defaultdict(dict)
    for s, p, o in triple('mandatoCamera'):
        m = re.search(r'/mc(\d+)_(\d+)_(\d+)', s)
        if m and m.group(1) in ROMANI:
            mandati[(m.group(2), m.group(1), m.group(3))][p] = val(o)
    per_dep = collections.defaultdict(list)
    for (pid, leg, _), v in mandati.items():
        per_dep[pid].append((ROMANI[leg], v.get('startDate', ''), v.get('endDate', ''),
                             v.get('motivoTermine', '')))

    anagrafe = collections.defaultdict(dict)
    for s, p, o in triple('persona'):
        m = re.search(r'/p(\d+)$', s)
        if m and m.group(1) in per_dep and p in ('gender', 'firstName', 'surname'):
            anagrafe[m.group(1)][p] = val(o)

    rapporto = {'mancanti': [], 'sesso': [], 'legislature': [], 'date': [], 'decessi': []}
    for pid, mm in sorted(per_dep.items()):
        a = anagrafe.get(pid, {})
        nome = ('%s %s' % (a.get('firstName', ''), a.get('surname', ''))).strip()
        p = per_id.get(pid)
        if not p:
            rapporto['mancanti'].append({'id': pid, 'nome': nome,
                                         'legislature': sorted({x[0] for x in mm})})
            continue
        g = {'male': 'M', 'female': 'F'}.get(a.get('gender'))
        if g and p.get('genere') and g != p['genere'].upper():
            rapporto['sesso'].append({'qid': p['qid'], 'nome': p['nome'],
                                      'noi': p['genere'], 'camera': g})
        loro = {x[0] for x in mm}
        nostre = {m for m, r in (p.get('ramo') or {}).items() if r == 'C'}
        if loro != nostre:
            rapporto['legislature'].append({'qid': p['qid'], 'nome': p['nome'],
                                            'solo_camera': sorted(loro - nostre),
                                            'solo_noi': sorted(nostre - loro)})
        for leg in sorted(loro & nostre):
            inizio = min(x[1] for x in mm if x[0] == leg)
            fine = max(x[2] for x in mm if x[0] == leg)
            noi = (p.get('mandato') or {}).get(leg)
            if noi and (noi[0] != inizio or (noi[1] or '') != fine):
                rapporto['date'].append({'qid': p['qid'], 'nome': p['nome'], 'leg': leg,
                                         'noi': noi, 'camera': [inizio, fine]})
        if any(x[3] == 'Decesso' for x in mm) and not p.get('morte'):
            rapporto['decessi'].append({'qid': p['qid'], 'nome': p['nome'],
                                        'quando': [x[2] for x in mm if x[3] == 'Decesso']})

    print('deputati XII-XVI nell\'anagrafe della Camera: %d' % len(per_dep))
    for k, v in rapporto.items():
        print('  %-12s %d' % (k, len(v)))
        for x in v[:8]:
            print('      ', json.dumps(x, ensure_ascii=False))
    json.dump(rapporto, open(USCITA, 'w', encoding='utf-8', newline='\n'),
              ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
