# -*- coding: utf-8 -*-
"""Il riassunto dei voti alla Camera, dalla XIII alla XVI legislatura.

Legge gli stessi archivi di conta_voti_camera.py (votoNN.rdf.zip e
votazione.rdf.zip), ma guarda le votazioni invece dei deputati:

  legislature   quante votazioni, quante segrete, quante approvate; su cento
                voti registrati quanti espressi, quante missioni, quante assenze;
                su cento voti espressi in linea col gruppo quanti diversi
  gruppi        le stesse cose gruppo per gruppo
  mesi          la presenza mese per mese
  strette       le votazioni decise per meno voti (differenza fra si' e no)
  battute       le votazioni palesi perse dalla maggioranza: i gruppi di
                maggioranza sono quelli che hanno votato si' all'ultima fiducia
                prima di quel giorno, sotto lo stesso governo; se la
                maggioranza dei loro deputati vota in un modo e la Camera
                decide l'altro, la maggioranza e' battuta. Solo dalla XIV:
                nella XIII le fiducie negli archivi non sono segnate.

Scrive data/riassunto_voti.json. Una decina di minuti.
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
D = os.path.join(QUI, '..', 'data', 'cache', 'zip_camera')
USCITA = os.path.join(QUI, '..', 'data', 'riassunto_voti.json')
ROMANI = {'13': 'XIII', '14': 'XIV', '15': 'XV', '16': 'XVI'}
SCELTE = {'Favorevole': 'F', 'Contrario': 'C', 'Astensione': 'A'}
# per le "strette" contano solo le votazioni con l'aula piena: con 40 votanti
# uno scarto di due voti non vuol dire niente
PIENA = 300
QUANTE = 25

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass


def votazioni():
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
            v = o[1:o.index('"', 1)] if o.startswith('"') else o.strip('<>')
            x = fuori[m.group(1)]
            if k == 'date':
                x['data'] = v[:8]
            elif k in ('richiestaFiducia', 'votazioneFinale', 'votazioneSegreta', 'approvato'):
                x[k] = v == '1'
            elif k in ('favorevoli', 'contrari', 'astenuti', 'maggioranza', 'votanti'):
                x[k] = int(v) if v.isdigit() else None
            elif k == 'title':
                x['titolo'] = v
            elif k == 'type' and not v.startswith('http'):
                # rdf:type e dc:type hanno lo stesso nome corto: si tiene quello che non e' un indirizzo
                x['tipo'] = v
            elif k == 'description':
                x['descrizione'] = re.sub(r'\s+', ' ', v.replace('\\n', ' ')).strip()
            elif k == 'relation' and 'schedavotazione' in v:
                x['scheda'] = v
    return fuori


def main():
    import genera_sito
    t0 = time.time()
    meta = votazioni()
    print('votazioni: %d' % len(meta), flush=True)

    leg_c = collections.defaultdict(collections.Counter)
    gru_c = collections.defaultdict(collections.Counter)      # (leg, gid) -> conti
    sigle = {}                                                  # (leg, gid) -> ultima sigla
    mesi = collections.defaultdict(collections.Counter)        # aaaamm -> conti
    battute, strette = [], []
    maggioranza = {}            # governo -> insieme dei gruppi dell'ultima fiducia

    def chiudi(vs, voti):
        m = meta.get(vs, {})
        leg = ROMANI[vs[2:4]]
        data = m.get('data', '')
        palese = not m.get('votazioneSegreta')
        lc = leg_c[leg]
        lc['votazioni'] += 1
        lc['segrete'] += not palese
        lc['approvate'] += bool(m.get('approvato'))
        lc['fiducie'] += bool(m.get('richiestaFiducia'))
        conta = collections.defaultdict(collections.Counter)
        for pid, s, g, missione, gid in voti:
            if s in 'FCA':
                conta[gid][s] += 1
        linea = {}
        if palese:
            for gid, c in conta.items():
                (s1, n1), *resto = c.most_common(2) + [(None, 0)]
                g = next((x[2] for x in voti if x[4] == gid), '')
                if gid and not g.upper().startswith('MIST') and n1 >= 2 and n1 > resto[0][1]:
                    linea[gid] = s1
        for pid, s, g, missione, gid in voti:
            k = 'espressi' if s in 'FCA' else 'missione' if missione else 'assente'
            for c in (lc, gru_c[(leg, gid)], mesi[data[:6]]):
                c['voti'] += 1
                c[k] += 1
                if s in 'FCA' and gid in linea:
                    c['con_linea'] += 1
                    c['diversi'] += s != linea[gid]
            if gid and g:
                sigle[(leg, gid)] = g
        gov = genera_sito.governo_al(data) if data else ''
        if m.get('richiestaFiducia'):
            # chi ha votato si' alla fiducia, gruppo per gruppo (il misto no: e' di tutti).
            # Fra le "fiducie" ci sono anche le mozioni di sfiducia: li' la maggioranza
            # e' chi vota no.
            # il titolo e' "Votazione Mozione 1-00..."
            sfiducia = ('MOZIONE' in (m.get('titolo') or '').upper() and
                        'DI FIDUCIA' not in (m.get('descrizione') or '').upper())
            pro, contro = ('C', 'F') if sfiducia else ('F', 'C')
            maggioranza[gov] = {gid for gid, c in conta.items()
                                if gid and c[pro] > c[contro] + c['A']
                                and not next((x[2] for x in voti if x[4] == gid), '').upper().startswith('MIST')}
            return
        f, c_ = m.get('favorevoli'), m.get('contrari')
        voce = lambda: {'vs': vs, 'data': data, 'titolo': m.get('titolo', ''), 'tipo': m.get('tipo', ''),
                        'descrizione': (m.get('descrizione') or '')[:300], 'si': f, 'no': c_,
                        'astenuti': m.get('astenuti'), 'approvata': bool(m.get('approvato')),
                        'segreta': not palese, 'scheda': m.get('scheda', ''), 'governo': gov}
        if f is not None and c_ is not None and f + c_ >= PIENA:
            strette.append((abs(f - c_), data, vs, voce()))
        if palese and gov in maggioranza and m.get('approvato') is not None:
            c = collections.Counter()
            for gid in maggioranza[gov]:
                c.update({s: n for s, n in conta.get(gid, {}).items() if s in 'FCA'})
            # gli astenuti contano: se la maggioranza si astiene non ha perso, ha lasciato passare
            if c['F'] + c['C'] + c['A'] >= 50:
                verso = 'F' if c['F'] > c['C'] else 'C'
                netta = c[verso] >= 0.6 * (c['F'] + c['C'] + c['A'])
                if netta and (verso == 'F') != bool(m['approvato']):
                    v = voce()
                    v['maggioranza'] = [c['F'], c['C']]
                    battute.append(v)

    for leg in sorted(ROMANI):
        z = zipfile.ZipFile(os.path.join(D, 'voto%s.rdf.zip' % leg))
        for info in sorted(z.infolist(), key=lambda i: i.filename):
            # i file sono per anno e in ordine: le fiducie vengono prima dei voti che seguono
            per_vs = collections.OrderedDict()
            voto = {}
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
                    elif '</ocd:voto>' in r and voto.get('vs') and voto.get('pid'):
                        per_vs.setdefault(voto['vs'], []).append(
                            (voto['pid'], SCELTE.get(voto.get('tipo'), 'N'), voto.get('g', ''),
                             'mission' in voto.get('desc', ''), voto.get('gid')))
            # in ordine di data e di numero, perche' "l'ultima fiducia" abbia senso
            ordine = sorted(per_vs, key=lambda vs: (meta.get(vs, {}).get('data', ''),
                                                     [int(x) for x in vs[2:].split('_')]))
            for vs in ordine:
                chiudi(vs, per_vs[vs])
            print('  %s: %.0f s' % (info.filename, time.time() - t0), flush=True)

    nomi = {}
    gc_file = os.path.join(QUI, '..', 'data', 'gruppi_camera.json')
    if os.path.exists(gc_file):
        # {gid: [legislatura in cifre, sigla, nome, nato, sciolto]}
        for gid, v in json.load(io.open(gc_file, encoding='utf-8'))['gruppi'].items():
            if v[0] in ROMANI:
                nomi[(ROMANI[v[0]], gid)] = v[2]
    strette.sort(key=lambda x: (x[0], x[1], x[2]))
    fuori = {
        '_nota': "Riassunto dei voti alla Camera XIII-XVI dagli archivi votoNN.rdf.zip e votazione.rdf.zip. "
                 "Generato da scripts/riassunto_voti_camera.py.",
        'legislature': {leg: dict(c) for leg, c in leg_c.items()},
        'gruppi': [{'leg': leg, 'gid': gid, 'sigla': sigle.get((leg, gid), ''),
                    'nome': nomi.get((leg, gid)) or sigle.get((leg, gid), ''), **dict(c)}
                   for (leg, gid), c in sorted(gru_c.items(), key=lambda x: (x[0][0], x[0][1] or '')) if gid and c['voti'] >= 20000],
        'mesi': {m: dict(c) for m, c in sorted(mesi.items()) if m},
        'strette': [x[3] for x in strette[:QUANTE * 4]],
        'battute': sorted(battute, key=lambda v: (v['data'], v['vs'])),
    }
    json.dump(fuori, io.open(USCITA, 'w', encoding='utf-8', newline='\n'), ensure_ascii=False, indent=0)
    print('fatto: %d gruppi, %d mesi, %d strette, %d battute; %.0f s' % (
        len(fuori['gruppi']), len(fuori['mesi']), len(fuori['strette']), len(battute), time.time() - t0))


if __name__ == '__main__':
    main()
