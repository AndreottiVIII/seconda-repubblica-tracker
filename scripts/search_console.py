# -*- coding: utf-8 -*-
"""Come va il sito su Google, letto da Search Console senza browser.

Usa la chiave dell'utente-programma lettore-search-console (permesso
"Limitato", sola lettura), che sta in segreti/ e non va mai su GitHub.
Stampa le visualizzazioni giorno per giorno, lo stato della mappa del sito e,
per le pagine indicate, quando Google le ha lette e se le ha indicizzate.
Ogni lettura resta anche in data/cache/search_console/<data>.json.

    python scripts/search_console.py [indirizzo ...]
"""
import datetime
import json
import os
import sys
import urllib.parse

from google.oauth2 import service_account
from google.auth.transport.requests import AuthorizedSession

QUI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CHIAVE = os.path.join(QUI, 'segreti', 'chiave-search-console.json')
PROPRIETA = 'sc-domain:secondarepubblica.it'
API = 'https://searchconsole.googleapis.com'
PAGINE = ['https://secondarepubblica.it/',
          'https://secondarepubblica.it/onorevole/silvio-berlusconi/',
          'https://secondarepubblica.it/onorevole/roberto-salerno/',
          'https://secondarepubblica.it/governi/']


def sessione():
    c = service_account.Credentials.from_service_account_file(
        CHIAVE, scopes=['https://www.googleapis.com/auth/webmasters.readonly'])
    return AuthorizedSession(c)


def giorni(s, quanti=28):
    fine = datetime.date.today()
    corpo = {'startDate': str(fine - datetime.timedelta(days=quanti)), 'endDate': str(fine),
             'dimensions': ['date'], 'dataState': 'all'}
    r = s.post(API + '/webmasters/v3/sites/%s/searchAnalytics/query' % urllib.parse.quote(PROPRIETA, safe=''),
               json=corpo)
    r.raise_for_status()
    return [(x['keys'][0], int(x['clicks']), int(x['impressions'])) for x in r.json().get('rows', [])]


def mappe(s):
    r = s.get(API + '/webmasters/v3/sites/%s/sitemaps' % urllib.parse.quote(PROPRIETA, safe=''))
    r.raise_for_status()
    return r.json().get('sitemap', [])


def esamina(s, url):
    r = s.post(API + '/v1/urlInspection/index:inspect', json={'inspectionUrl': url, 'siteUrl': PROPRIETA})
    r.raise_for_status()
    i = r.json()['inspectionResult'].get('indexStatusResult', {})
    return {'url': url, 'esito': i.get('coverageState'), 'ultima_lettura': i.get('lastCrawlTime'),
            'verdetto': i.get('verdict')}


def main():
    s = sessione()
    rapporto = {'giorni': giorni(s), 'mappe': mappe(s),
                'pagine': [esamina(s, u) for u in (sys.argv[1:] or PAGINE)]}
    print('Giorno       clic  visualizzazioni')
    for g, c, v in rapporto['giorni'][-14:]:
        print('%s  %4d  %6d' % (g, c, v))
    for m in rapporto['mappe']:
        print('\nMappa del sito: letta il %s, %s indirizzi, errori %s, avvisi %s' % (
            (m.get('lastDownloaded') or '')[:10], sum(int(c.get('submitted', 0)) for c in m.get('contents', [])),
            m.get('errors'), m.get('warnings')))
    print()
    for p in rapporto['pagine']:
        print('%s\n   %s; ultima lettura: %s' % (p['url'], p['esito'], (p['ultima_lettura'] or 'mai')[:10]))
    cartella = os.path.join(QUI, 'data', 'cache', 'search_console')
    os.makedirs(cartella, exist_ok=True)
    with open(os.path.join(cartella, '%s.json' % datetime.date.today()), 'w', encoding='utf-8') as f:
        json.dump(rapporto, f, ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
