# -*- coding: utf-8 -*-
"""Il voto del Senato del 14 settembre 2011, per nome.

Il 5 aprile 2011 la Camera vota per sollevare davanti alla Corte
costituzionale un conflitto di attribuzione sul caso Ruby: la Giunta per le
autorizzazioni sosteneva che Silvio Berlusconi, telefonando in questura,
ritenesse la ragazza nipote di Hosni Mubarak, e che quindi l'affare
riguardasse le sue funzioni di governo. Il 14 settembre 2011 il Senato vota
la stessa cosa.

Del voto della Camera negli open data non c'e' traccia: quel dataset copre le
votazioni legate agli atti legislativi, e comunque la Camera pubblica solo i
totali, mai i nomi. Il Senato invece pubblica l'appello nominale, ed e' questo.

Nessuna interpretazione: si prende cosi' com'e', si aggancia alle nostre
schede per URI del senatore, e chi non si aggancia resta fuori col suo nome.
"""
import sys, os, json, urllib.request, urllib.parse, time

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

QUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, QUI)
import senato

USCITA = os.path.join(QUI, '..', 'data', 'voto_ruby.json')
ELENCO = os.path.join(QUI, '..', 'data', 'elenco.json')
VOTAZIONE = 'http://dati.senato.it/votazione/16-602-1'
UA = ('SecondaRepubblicaTracker/0.1 (progetto personale; '
      'davide.caniatti@gmail.com)')

P = 'PREFIX osr: <http://dati.senato.it/osr/> '


def chiedi(query, tentativi=4):
    for i in range(tentativi):
        try:
            u = 'https://dati.senato.it/sparql?' + urllib.parse.urlencode(
                {'query': query, 'format': 'application/sparql-results+json'})
            r = urllib.request.Request(u, headers={
                'User-Agent': UA, 'Accept': 'application/sparql-results+json'})
            return json.load(urllib.request.urlopen(
                r, timeout=240))['results']['bindings']
        except Exception as e:
            if i == tentativi - 1:
                raise
            sys.stderr.write('  ritento (%d): %s\n' % (i + 1, str(e)[:70]))
            time.sleep(5 * (i + 1))


def main():
    numeri = {}
    for r in chiedi(P + 'SELECT ?p ?o WHERE { <%s> ?p ?o FILTER(!isIRI(?o)) }'
                    % VOTAZIONE):
        numeri[r['p']['value'].rsplit('/', 1)[-1]] = r['o']['value']

    voti = []
    for come in ('favorevole', 'contrario', 'astenuto'):
        for r in chiedi(P + 'SELECT ?s WHERE { <%s> osr:%s ?s }'
                        % (VOTAZIONE, come)):
            voti.append({'uri': r['s']['value'], 'come': come})
        time.sleep(0.4)

    if not voti:
        raise SystemExit('nessun voto: il Senato non ha risposto come previsto.')

    # L'aggancio e' esatto: l'URI del senatore e' lo stesso che usiamo gia'.
    persone = json.load(open(ELENCO, encoding='utf-8'))['persone']
    per_uri = {p['id_senato']: p for p in persone if p.get('id_senato')}
    fuori, orfani = [], 0
    for v in voti:
        p = per_uri.get(v['uri'])
        if p:
            fuori.append({'qid': p['qid'], 'come': v['come']})
        else:
            orfani += 1

    dati = {
        'titolo': numeri.get('label', '').strip(),
        'data': '2011-09-14',
        'ramo': 'Senato della Repubblica',
        'favorevoli': int(numeri.get('favorevoli', 0)),
        'contrari': int(numeri.get('contrari', 0)),
        'astenuti': int(numeri.get('astenuti', 0)),
        'presenti': int(numeri.get('presenti', 0)),
        'votanti': int(numeri.get('votanti', 0)),
        'esito': numeri.get('esito', ''),
        'fonte': 'https://dati.senato.it/',
        'voti': fuori,
    }
    json.dump(dati, open(USCITA, 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    print('%s: %d favorevoli, %d contrari, %d astenuti'
          % (dati['esito'], dati['favorevoli'], dati['contrari'],
             dati['astenuti']))
    print('voti nominali: %d, agganciati alle schede: %d, non agganciati: %d'
          % (len(voti), len(fuori), orfani))


if __name__ == '__main__':
    main()
