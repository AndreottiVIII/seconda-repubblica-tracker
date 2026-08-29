# -*- coding: utf-8 -*-
"""Il differenziale fra i titoli decennali italiani e tedeschi, dalla BCE.

Lo spread non e' un dato parlamentare e non sta in nessuno dei due registri:
viene dalla Banca Centrale Europea, che pubblica i tassi d'interesse a lungo
termine usati per i criteri di convergenza. Serie mensili, liberamente
riusabili citando la fonte.

Lo spread e' la differenza fra i due rendimenti, in punti base. Qui non si
calcola niente di piu': nessuna media, nessuna interpolazione, nessun massimo
giornaliero. La serie mensile e' quella che la BCE pubblica, e resta quella.
"""
import sys, os, json, urllib.request

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

QUI = os.path.dirname(os.path.abspath(__file__))
USCITA = os.path.join(QUI, '..', 'data', 'spread.json')
UA = ('SecondaRepubblicaTracker/0.1 (progetto personale; '
      'davide.caniatti@gmail.com)')

BASE = 'https://data-api.ecb.europa.eu/service/data/IRS/M.%s.L.L40.CI.0000.EUR.N.Z'
DA, A = '2010-01', '2013-06'


def serie(paese):
    url = BASE % paese + '?format=jsondata&startPeriod=%s&endPeriod=%s' % (DA, A)
    r = urllib.request.Request(url, headers={'User-Agent': UA,
                                             'Accept': 'application/json'})
    d = json.load(urllib.request.urlopen(r, timeout=120))
    tempi = [x['id'] for x in
             d['structure']['dimensions']['observation'][0]['values']]
    prima = list(d['dataSets'][0]['series'].values())[0]['observations']
    return {tempi[int(k)]: v[0] for k, v in prima.items() if v and v[0] is not None}


def main():
    it, de = serie('IT'), serie('DE')
    mesi = sorted(set(it) & set(de))
    if len(mesi) < 24:
        raise SystemExit('la BCE ha risposto con %d mesi soli: non pubblico.'
                         % len(mesi))
    dati = {
        'fonte': 'Banca Centrale Europea, tassi d’interesse a lungo termine '
                 'per i criteri di convergenza (serie IRS, mensili)',
        'url': 'https://data.ecb.europa.eu/',
        'mesi': [{'m': m, 'it': round(it[m], 2), 'de': round(de[m], 2),
                  's': int(round((it[m] - de[m]) * 100))} for m in mesi],
    }
    json.dump(dati, open(USCITA, 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1)
    picco = max(dati['mesi'], key=lambda x: x['s'])
    print('mesi scaricati: %d (da %s a %s)' % (len(mesi), mesi[0], mesi[-1]))
    print('massimo: %s, %d punti base (Italia %.2f%%, Germania %.2f%%)'
          % (picco['m'], picco['s'], picco['it'], picco['de']))


if __name__ == '__main__':
    main()
