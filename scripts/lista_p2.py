"""Chi dell'elenco compare nella lista della P2 sequestrata a Castiglion
Fibocchi il 17 marzo 1981 e pubblicata dalla Commissione parlamentare
d'inchiesta presieduta da Tina Anselmi (relazione del 12 luglio 1984).

La lista la trascrive la voce "Appartenenti alla P2" di Wikipedia, con un
collegamento per chi ha una voce: dal collegamento si arriva al codice
Wikidata, e dal codice alla nostra scheda. Niente nomi a mano.

Dalla lista si tengono solo le note che stanno nel documento ("in sonno",
cioe' dimesso; "passato al Grande Oriente") e il numero di fascicolo; "morto"
e' un'aggiunta di Wikipedia. Publio Fiori resta fuori: il Tribunale di Roma
nel 2001 ha escluso la sua affiliazione.

Si lancia a mano: la lista e' quella da quarant'anni. Scrive
data/lista_p2.json. (Lo stesso metodo di primarepubblica.net, copiato: i
due siti restano separati.)
"""
import json
import os
import re
import urllib.parse
import urllib.request

QUI = os.path.dirname(os.path.abspath(__file__))
USCITA = os.path.join(QUI, '..', 'data', 'lista_p2.json')
ELENCO = os.path.join(QUI, '..', 'data', 'elenco.json')
API = 'https://it.wikipedia.org/w/api.php?'
ESCLUSI = {'Q3925320': 'Publio Fiori: affiliazione esclusa dal Tribunale di Roma nel 2001'}
VOCE = re.compile(r'\*\s*(.*?)\[\[([^\]|]+)(?:\|[^\]]*)?\]\]\s*(?:,\s*detto[^(]*)?\(([^)]*)\)')


def chiedi(parametri):
    url = API + urllib.parse.urlencode(dict(parametri, format='json', formatversion=2))
    req = urllib.request.Request(url, headers={'User-Agent': 'SecondaRepubblicaTracker/0.1 (https://secondarepubblica.it)'})
    return json.load(urllib.request.urlopen(req, timeout=60))


def voci():
    testo = chiedi({'action': 'parse', 'page': 'Appartenenti alla P2',
                    'prop': 'wikitext'})['parse']['wikitext']
    fuori = []
    for riga in testo.split('\n'):
        m = VOCE.match(riga)
        if not m:
            continue
        note = [n.strip() for n in m.group(3).split(',')]
        fuori.append({'wiki': m.group(2).strip(),
                      'citta': note[0],
                      'in_sonno': 'in sonno' in note,
                      'grande_oriente': any('Grande Oriente' in n for n in note),
                      'fascicolo': next((re.sub(r'\D', '', n) for n in reversed(note)
                                         if re.search(r'\d', n) and 'morto' not in n), '')})
    return fuori


def codici(titoli):
    qid = {}
    for i in range(0, len(titoli), 50):
        d = chiedi({'action': 'query', 'prop': 'pageprops', 'ppprop': 'wikibase_item',
                    'redirects': 1, 'titles': '|'.join(titoli[i:i + 50])})['query']
        norm = {r['from']: r['to'] for r in d.get('normalized', [])}
        red = {r['from']: r['to'] for r in d.get('redirects', [])}
        pag = {p['title']: p.get('pageprops', {}).get('wikibase_item') for p in d['pages']}
        for t in titoli[i:i + 50]:
            x = norm.get(t, t)
            qid[t] = pag.get(red.get(x, x))
    return qid


def main():
    elenco = json.load(open(ELENCO, encoding='utf-8'))
    nostri = {p['qid']: p['nome'] for p in elenco['persone']}
    lista = voci()
    qid = codici([v['wiki'] for v in lista])
    fuori = []
    for v in lista:
        q = qid.get(v['wiki'])
        if q in nostri and q not in ESCLUSI:
            fuori.append(dict(v, qid=q, nome=nostri[q]))
    json.dump(fuori, open(USCITA, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('%d nella lista, %d dei nostri' % (len(lista), len(fuori)))


if __name__ == '__main__':
    main()
