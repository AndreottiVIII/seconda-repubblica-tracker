# -*- coding: utf-8 -*-
"""I cambi di gruppo dei registri contro i gruppi con cui si e' votato.

Ogni voto alla Camera registra il gruppo del deputato quel giorno. Dai voti
(data/voti_camera.json, che li riassume per deputato: ogni gruppo col primo e
l'ultimo giorno in cui ci ha votato) si ricostruisce la successione dei gruppi
dalla XIII alla XVI, in modo indipendente dal registro delle adesioni da cui
nascono le schede.

Le due fonti numerano i gruppi in modo diverso: i DS della XIII sono gr440
nei voti e gr439 nel registro, e ogni componente del gruppo misto ha nei
voti un codice suo. La corrispondenza si ricava dai dati: un codice dei voti
corrisponde al gruppo del registro in cui stava la gran parte di chi ci ha
votato, nei giorni in cui ci ha votato.

Poi, per ogni deputato e legislatura, si confrontano le due successioni:

  nei voti, non nel registro   ha votato con un gruppo che la scheda non ha
  nel registro, mai nei voti   un gruppo della scheda, durato piu' di trenta
                               giorni, in cui non ha mai votato
  ordine diverso               gli stessi gruppi in un ordine diverso

Non corregge niente: scrive data/controllo_casacche_voti.json, da guardare.
"""
import collections
import datetime
import io
import json
import os
import sys

QUI = os.path.dirname(os.path.abspath(__file__))
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass


def giorno(s):
    return datetime.date(int(s[:4]), int(s[4:6]), int(s[6:8])) if s and len(s) >= 8 else None


def compatta(seq):
    fuori = []
    for x in seq:
        if not fuori or fuori[-1] != x:
            fuori.append(x)
    return fuori


def main():
    persone = json.load(io.open(os.path.join(QUI, '..', 'data', 'elenco.json'),
                                encoding='utf-8'))['persone']
    V = json.load(io.open(os.path.join(QUI, '..', 'data', 'voti_camera.json'),
                          encoding='utf-8'))['deputati']

    casi = []
    for p in persone:
        voti = V.get(p.get('id_camera') or '')
        for leg, v in (voti or {}).items():
            reg = sorted(((g['uri'].rsplit('/', 1)[-1], g.get('s') or g.get('g'),
                           g.get('da') or '', g.get('a') or '99999999')
                          for g in (p.get('gruppi_per_mandato') or {}).get(leg, [])
                          if 'camera.it' in (g.get('uri') or '')), key=lambda x: x[2])
            if reg and v.get('gruppi'):
                casi.append((p, leg, reg, v['gruppi']))

    # la corrispondenza fra i codici dei voti e quelli del registro
    # Per ogni periodo di voto, il gruppo del registro con cui si sovrappone di
    # piu': il primo voto col gruppo nuovo arriva spesso prima che il registro
    # segni l'adesione, e guardare solo quello sbaglia proprio nei cambi.
    def sovrapposto(reg, primo, ultimo):
        migliore, giorni = None, -1
        for gid, _, da, a in reg:
            g = (min(ultimo, a) > max(primo, da)) and                 (giorno(min(ultimo, a)) - giorno(max(primo, da))).days or 0
            if g > giorni:
                migliore, giorni = gid, g
        return migliore if giorni > 0 else None
    coppie = collections.defaultdict(collections.Counter)
    for p, leg, reg, gruppi in casi:
        for vgid, primo, ultimo, sigla in gruppi:
            m = sovrapposto(reg, primo, ultimo)
            if m:
                coppie[vgid][m] += 1
    mappa = {}
    for vgid, c in coppie.items():
        (rgid, n), tot = c.most_common(1)[0], sum(c.values())
        if n >= 3 and n / tot >= 0.6:
            mappa[vgid] = rgid
    print('codici dei voti: %d, tradotti nel registro: %d' % (len(coppie), len(mappa)))

    rapporto = {'solo_voti': [], 'solo_registro': [], 'ordine': []}
    for p, leg, reg, gruppi in casi:
        base = {'qid': p['qid'], 'nome': p['nome'], 'leg': leg}
        sigle = {r[0]: r[1] for r in reg}
        dai_voti = compatta([mappa.get(g[0], '?' + g[0]) for g in gruppi])
        dal_reg = compatta([r[0] for r in reg])
        for g in gruppi:
            m = mappa.get(g[0])
            # un giorno solo in un gruppo e' quasi sempre un passaggio tecnico
            if m and m not in dal_reg and g[1] != g[2]:
                rapporto['solo_voti'].append(dict(base, gruppo=m, sigla_voti=g[3],
                                                  primo_voto=g[1], ultimo_voto=g[2],
                                                  registro=[sigle[x] for x in dal_reg]))
        for gid, sigla, da, a in reg:
            durata = (giorno(a) or giorno('20130314')) - giorno(da) if giorno(da) else None
            # conta solo se in quel periodo ha votato, e con un altro gruppo
            altro = any(mappa.get(g[0]) not in (None, gid) and g[1] <= da and g[2] >= a
                        for g in gruppi)
            if gid not in dai_voti and durata and durata.days > 30 and altro:
                rapporto['solo_registro'].append(dict(base, gruppo=gid, sigla=sigla, da=da, a=a))
        comuni_v = compatta([g for g in dai_voti if g in dal_reg])
        comuni_r = compatta([g for g in dal_reg if g in dai_voti])
        if set(comuni_v) != set(comuni_r):
            rapporto['ordine'].append(dict(base, voti=[sigle.get(g, g) for g in comuni_v],
                                           registro=[sigle.get(g, g) for g in comuni_r]))
    print('deputati-legislature confrontati: %d' % len(casi))
    for k, v in rapporto.items():
        print('  %-14s %d' % (k, len(v)))
        for x in v[:15]:
            print('      ', json.dumps(x, ensure_ascii=False))
    json.dump({'mappa': mappa, **rapporto},
              io.open(os.path.join(QUI, '..', 'data', 'controllo_casacche_voti.json'),
                      'w', encoding='utf-8', newline='\n'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
