# -*- coding: utf-8 -*-
"""Chi ha guidato i partiti: segretari, presidenti, coordinatori.

Non e' un dato parlamentare. La segreteria di un partito non e' un atto delle
Camere, e infatti nei registri non c'e': viene da Wikidata, che la modella dal
lato della persona. "Segretario del Partito Democratico" e' una carica a se',
non una proprieta' del partito; la proprieta' del partito (P488) da' il
presidente, che e' un'altra cosa ancora.

Due lezioni imparate a caro prezzo, e per questo scritte qui:

1. Il filtro sulle etichette va fatto in Python, non dentro la query. Chiedere
   a Wikidata di applicare una REGEX su migliaia di etichette per 2.763
   persone alla volta manda l'endpoint in timeout: dieci minuti e niente. Si
   chiedono tutte le cariche di cinquanta persone per volta, che e' un lavoro
   banale per il server, e si filtra qui.

2. Il risultato si salva a ogni blocco. Un giro di cinquantacinque blocchi che
   fallisce all'ultimo non deve ricominciare da capo: chi ha gia' risposto
   resta su disco, e il giro dopo riprende da dove era arrivato.
"""
import sys, os, json, time, re

QUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, QUI)
import wd

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

ELENCO = os.path.join(QUI, '..', 'data', 'elenco.json')
PARZIALE = os.path.join(QUI, '..', 'data', 'cache', 'leader_parziale.json')
USCITA = os.path.join(QUI, '..', 'data', 'leader.json')

BLOCCO = 50

# Le cariche che ci interessano: guidare un partito. L'etichetta italiana di
# Wikidata ha sempre la forma "segretario del Partito X", "presidente della
# Lega Nord", "coordinatore di Forza Italia".
GUIDA = re.compile(
    r'^(segretari[oa]|presidente|presidentessa|coordinat[oa]re|leader|'
    r'portavoce)\s+(nazionale\s+|federale\s+|politic[oa]\s+)?'
    r'(del|della|dei|delle|di|d\')\s*(.+)$', re.I | re.U)

# Le cariche pubbliche che cominciano allo stesso modo ma non c'entrano nulla.
NON_PARTITI = (
    'consiglio', 'repubblica', 'senato', 'camera', 'regione', 'provincia',
    'comune', 'commissione', 'assemblea', 'parlamento europeo', 'stato',
    'giunta', 'ministri', 'corte', 'banca', 'istituto', 'universita',
    'nazioni unite', 'unione europea', 'consorzio', 'ordine', 'federazione '
    'italiana', 'club', 'associazione', 'fondazione', 'societa', 'gruppo '
    'parlamentare', 'gruppo misto',
)

Q = """SELECT ?p ?pos ?posLabel ?da ?a WHERE {
  VALUES ?p { %s }
  ?p p:P39 ?st . ?st ps:P39 ?pos .
  OPTIONAL { ?st pq:P580 ?da }
  OPTIONAL { ?st pq:P582 ?a }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "it,en". }
}"""


def e_partito(oggetto):
    basso = oggetto.lower()
    return not any(x in basso for x in NON_PARTITI)


def leggi_parziale():
    if os.path.exists(PARZIALE):
        try:
            return json.load(open(PARZIALE, encoding='utf-8'))
        except Exception:
            pass
    return {'fatti': [], 'voci': []}


def main():
    persone = json.load(open(ELENCO, encoding='utf-8'))['persone']
    nomi = {p['qid']: p['nome'] for p in persone}
    qid = sorted(q for q in nomi if q.startswith('Q'))

    stato = leggi_parziale()
    fatti = set(stato['fatti'])
    voci = stato['voci']
    da_fare = [q for q in qid if q not in fatti]
    print('persone su Wikidata: %d, gia\' interrogate: %d, da fare: %d'
          % (len(qid), len(fatti), len(da_fare)))

    blocchi = [da_fare[i:i + BLOCCO] for i in range(0, len(da_fare), BLOCCO)]
    for n, blocco in enumerate(blocchi, 1):
        valori = ' '.join('wd:' + q for q in blocco)
        try:
            righe = wd.sparql(Q % valori, tries=3)
        except Exception as e:
            print('  blocco %d/%d non riuscito, lo riprovera\' il prossimo giro: %s'
                  % (n, len(blocchi), str(e)[:60]))
            continue

        presi = 0
        for r in righe:
            etichetta = wd.v(r, 'posLabel') or ''
            m = GUIDA.match(etichetta.strip())
            if not m or not e_partito(m.group(4)):
                continue
            voci.append({
                'qid': wd.qid(r, 'p'),
                'ruolo': m.group(1).lower(),
                'partito': m.group(4).strip(),
                'carica': etichetta,
                'da': (wd.v(r, 'da') or '')[:10],
                'a': (wd.v(r, 'a') or '')[:10],
            })
            presi += 1

        fatti |= set(blocco)
        json.dump({'fatti': sorted(fatti), 'voci': voci},
                  open(PARZIALE, 'w', encoding='utf-8'), ensure_ascii=False)
        if n % 5 == 0 or presi:
            print('  blocco %d/%d: %d cariche di partito (totale %d)'
                  % (n, len(blocchi), presi, len(voci)))
        time.sleep(0.6)

    # I doppioni esistono: la stessa carica puo' arrivare due volte.
    unici = {}
    for v in voci:
        unici[(v['qid'], v['carica'], v['da'])] = v
    voci = sorted(unici.values(), key=lambda v: (v['partito'], v['da'] or '9'))

    os.makedirs(os.path.dirname(USCITA), exist_ok=True)
    json.dump({'_nota': 'Chi ha guidato i partiti: segretari, presidenti, '
                        'coordinatori. Da Wikidata, che modella queste cariche '
                        'dal lato della persona. Non sono atti parlamentari e '
                        'nei registri di Camera e Senato non compaiono.',
               'voci': voci},
              open(USCITA, 'w', encoding='utf-8', newline='\n'),
              ensure_ascii=False, indent=1)

    print()
    print('cariche di partito trovate: %d, su %d persone'
          % (len(voci), len({v['qid'] for v in voci})))
    import collections
    c = collections.Counter(v['partito'] for v in voci)
    print()
    print('i partiti piu\' ricorrenti:')
    for k, n in c.most_common(25):
        print('   %-46s %d' % (k[:46], n))


if __name__ == '__main__':
    main()
