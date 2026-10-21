# -*- coding: utf-8 -*-
"""Quello che sa Wikidata e i registri delle Camere no: dove si e' nati,
morti e sepolti, i parenti che sono passati anche loro dal Parlamento, la
voce della Treccani.

Lo stesso metodo di primarepubblica.net (le tre interrogazioni sono le sue),
copiato e non richiamato: i due siti restano separati.

- Luoghi (P19, P20, P119): uno solo per tipo; se Wikidata ne da' due, non
  sa quale, e la scheda non ne dice nessuno.
- Parenti (P22 padre, P25 madre, P26 coniuge, P40 figlio, P3373 fratello o
  sorella, P1038 parente): solo quando anche l'altro sta nell'elenco. E' la
  famiglia in Parlamento, non l'albero genealogico.
- Treccani: il Dizionario Biografico degli Italiani (P1986), che e' la
  biografia vera; se manca, la voce dell'Enciclopedia (P3365).

Si lancia a mano. Scrive data/wikidata_extra.json.
"""
import io
import json
import os
import sys
import time

QUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, QUI)
import wd

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

ELENCO = os.path.join(QUI, '..', 'data', 'elenco.json')
USCITA = os.path.join(QUI, '..', 'data', 'wikidata_extra.json')
BLOCCO = 300

LUOGHI = {'P19': 'nascita', 'P20': 'morte', 'P119': 'sepoltura'}
PARENTELE = {'P22': 'padre', 'P25': 'madre', 'P26': 'coniuge', 'P40': 'figlio',
             'P3373': 'fratello', 'P1038': 'parente'}

Q_LUOGHI = """SELECT ?a ?p ?nome WHERE {
  VALUES ?a { %s }
  VALUES ?p { %s }
  ?a ?p ?l .
  ?l rdfs:label ?nome . FILTER(LANG(?nome) = 'it')
}"""
Q_PARENTI = """SELECT ?a ?p ?b WHERE {
  VALUES ?a { %s }
  VALUES ?p { %s }
  ?a ?p ?b .
}"""
Q_TRECCANI = """SELECT ?p ?dbi ?enc WHERE {
  VALUES ?p { %s }
  OPTIONAL { ?p wdt:P1986 ?dbi }
  OPTIONAL { ?p wdt:P3365 ?enc }
}"""


def a_blocchi(qid, query, *altro):
    righe = []
    for i in range(0, len(qid), BLOCCO):
        valori = ' '.join('wd:' + q for q in qid[i:i + BLOCCO])
        righe += wd.sparql(query % ((valori,) + altro), tries=3)
        time.sleep(1)
    return righe


def main():
    persone = json.load(io.open(ELENCO, encoding='utf-8'))['persone']
    qid = sorted(p['qid'] for p in persone if p['qid'].startswith('Q'))
    nostri = set(qid)
    print('persone su Wikidata: %d' % len(qid))

    luoghi = {}
    for r in a_blocchi(qid, Q_LUOGHI, ' '.join('wdt:' + k for k in LUOGHI)):
        a, chi = wd.qid(r, 'a'), LUOGHI.get((wd.v(r, 'p') or '').rsplit('/', 1)[-1])
        if a in nostri and chi:
            luoghi.setdefault(a, {}).setdefault(chi, set()).add(wd.v(r, 'nome'))
    luoghi = {a: {k: next(iter(v)) for k, v in voci.items() if len(v) == 1}
              for a, voci in luoghi.items()}
    luoghi = {a: v for a, v in luoghi.items() if v}

    parenti = {}
    for r in a_blocchi(qid, Q_PARENTI, ' '.join('wdt:' + k for k in PARENTELE)):
        a, b = wd.qid(r, 'a'), wd.qid(r, 'b')
        rel = PARENTELE.get((wd.v(r, 'p') or '').rsplit('/', 1)[-1])
        if a in nostri and b in nostri and a != b and rel and [rel, b] not in parenti.get(a, []):
            parenti.setdefault(a, []).append([rel, b])

    treccani = {}
    for r in a_blocchi(qid, Q_TRECCANI):
        q, dbi, enc = wd.qid(r, 'p'), wd.v(r, 'dbi'), wd.v(r, 'enc')
        if q in nostri and (dbi or enc):
            voce = (dbi + '_(Dizionario-Biografico)') if dbi else enc
            if dbi or q not in treccani:
                treccani[q] = voce

    conta = lambda k: sum(1 for v in luoghi.values() if k in v)
    print('luoghi: %d di nascita, %d di morte, %d di sepoltura' %
          (conta('nascita'), conta('morte'), conta('sepoltura')))
    print('parenti: %d legami fra %d persone' % (sum(len(v) for v in parenti.values()), len(parenti)))
    print('Treccani: %d voci' % len(treccani))
    json.dump({'_nota': "Da Wikidata: luoghi di nascita, morte e sepoltura, parenti che stanno "
                        "anche loro nell'elenco, voce della Treccani. Generato da "
                        "scripts/wikidata_extra.py.",
               'luoghi': luoghi, 'parenti': parenti, 'treccani': treccani},
              io.open(USCITA, 'w', encoding='utf-8', newline='\n'), ensure_ascii=False, indent=0)


if __name__ == '__main__':
    main()
