# -*- coding: utf-8 -*-
"""Il conto dei cambi di casacca, che e' la domanda per cui esiste il sito.

Una regola sola, e meccanica: due adesioni consecutive sono un cambio di
casacca a meno che portino allo stesso partito, o che il partito d'arrivo sia
un erede dichiarato di quello di partenza (data/partiti.json).

Le successioni valgono SOLO fra una legislatura e l'altra. Dentro una
legislatura non servono, perche' le rinomine le ha gia' risolte il registro
della Camera, che tiene l'identita' del gruppo separata dal suo nome. E
applicarle li' farebbe sparire le scissioni vere: Gianfranco Fini che nel
luglio 2010 lascia il PdL per Futuro e Liberta' e' un cambio di casacca, non
un partito che cambia nome.

Il passaggio al gruppo misto conta sempre, in tutti e due i sensi: uscire da
un gruppo senza entrare in un altro e' una scelta, non un incidente.
"""
import sys, os, json

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

QUI = os.path.dirname(os.path.abspath(__file__))
ORDINE = ['XII', 'XIII', 'XIV', 'XV', 'XVI']


def leggi_mappa(percorso=None):
    percorso = percorso or os.path.join(QUI, '..', 'data', 'partiti.json')
    return json.load(open(percorso, encoding='utf-8'))


def antenati(partiti):
    """{partito: tutti i partiti di cui e' erede, anche alla lontana}."""
    memoria = {}

    def risali(c, visti):
        if c in memoria:
            return memoria[c]
        fuori = set()
        for a in partiti.get(c, {}).get('eredita_da', []):
            if a in visti:
                continue
            fuori.add(a)
            fuori |= risali(a, visti | {a})
        memoria[c] = fuori
        return fuori

    return {c: risali(c, {c}) for c in partiti}


def percorso(p, gruppi):
    """La successione dei partiti di una persona: (legislatura, partito, da, a)."""
    ramo = p.get('ramo') or {}
    fuori = []
    for m in ORDINE:
        for g in (p.get('gruppi_per_mandato') or {}).get(m, []):
            chiave = '%s|%s|%s' % (m, ramo.get(m, '?'), g['g'])
            fuori.append((m, gruppi.get(chiave), g.get('da'), g.get('a')))
    return fuori


def cambi(p, gruppi, ant):
    """Quante volte ha cambiato casacca davvero."""
    passi = percorso(p, gruppi)
    n = 0
    for (leg_a, a, _, _), (leg_b, b, _, _) in zip(passi, passi[1:]):
        if a == b or a is None or b is None:
            continue
        if leg_a != leg_b and b != 'MISTO' and a in ant.get(b, ()):
            continue
        n += 1
    return n


def sintesi(p, gruppi):
    """Il percorso ridotto ai passaggi visibili, per la scheda."""
    fuori, ultimo = [], None
    for _m, part, _da, _a in percorso(p, gruppi):
        if part != ultimo:
            fuori.append(part)
            ultimo = part
    return fuori


def main():
    M = leggi_mappa()
    gruppi, partiti = M['gruppi'], M['partiti']
    ant = antenati(partiti)
    elenco = os.path.join(QUI, '..', 'data', 'elenco.json')
    P = json.load(open(elenco, encoding='utf-8'))['persone']

    conta = {p['qid']: cambi(p, gruppi, ant) for p in P}
    con_gruppo = [p for p in P if p.get('gruppi_per_mandato')]

    print("I VENTI CHE HANNO CAMBIATO PIU' CASACCA (1994-2013)")
    print()
    for p in sorted(P, key=lambda x: (-conta[x['qid']], x['nome']))[:20]:
        print('  %2d  %-25s %s' % (conta[p['qid']], p['nome'][:25],
                                   ' > '.join(sintesi(p, gruppi))[:86]))
    print()
    print('cambi di casacca nel perimetro: %d' % sum(conta.values()))
    print('non hanno mai cambiato: %d su %d'
          % (sum(1 for p in con_gruppo if conta[p['qid']] == 0), len(con_gruppo)))
    distribuzione = {}
    for p in con_gruppo:
        distribuzione[conta[p['qid']]] = distribuzione.get(conta[p['qid']], 0) + 1
    print('distribuzione:', dict(sorted(distribuzione.items())))

    fedeli = [p for p in con_gruppo
              if conta[p['qid']] == 0
              and len([m for m in ORDINE if (p.get('gruppi_per_mandato') or {}).get(m)]) == 5]
    print()
    print('I FEDELI: cinque legislature senza mai cambiare (%d)' % len(fedeli))
    for p in sorted(fedeli, key=lambda x: x['nome'])[:12]:
        print('     %-27s %s' % (p['nome'][:27], sintesi(p, gruppi)[0]))


if __name__ == '__main__':
    main()
