# -*- coding: utf-8 -*-
"""Quanto e' noto ciascuno, misurato dalle letture della sua voce su Wikipedia.

Per ogni persona con una voce in italiano somma le visite degli ultimi dodici
mesi (API pubblica di Wikimedia, solo utenti veri, niente robot). Serve a
scegliere quali schede mostrare a Google per prime. Scrive data/notorieta.json,
{qid: visite}; chi non ha voce non compare.

    python scripts/notorieta.py
"""
import datetime
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request

QUI = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ELENCO = os.path.join(QUI, 'data', 'elenco.json')
USCITA = os.path.join(QUI, 'data', 'notorieta.json')
API = ('https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/'
       'it.wikipedia/all-access/user/%s/monthly/%s/%s')
AGENTE = 'SecondaRepubblicaTracker/1.0 (https://secondarepubblica.it)'


def visite(titolo, da, a):
    url = API % (urllib.parse.quote(titolo, safe=''), da, a)
    for tentativo in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': AGENTE}), timeout=30) as r:
                return sum(x['views'] for x in json.load(r)['items'])
        except urllib.error.HTTPError as e:
            if e.code == 404:
                return 0
            time.sleep(2 ** tentativo)
        except OSError:
            time.sleep(2 ** tentativo)
    return None


def main():
    persone = json.load(open(ELENCO, encoding='utf-8'))['persone']
    fatti = json.load(open(USCITA, encoding='utf-8')) if os.path.exists(USCITA) else {}
    oggi = datetime.date.today().replace(day=1)
    da = (oggi - datetime.timedelta(days=365)).strftime('%Y%m01')
    a = (oggi - datetime.timedelta(days=1)).strftime('%Y%m%d')
    for i, p in enumerate(persone):
        if not p.get('wikipedia') or p['qid'] in fatti:
            continue
        titolo = urllib.parse.unquote(p['wikipedia'].rsplit('/wiki/', 1)[1])
        v = visite(titolo, da, a)
        if v is not None:
            fatti[p['qid']] = v
        if i % 200 == 0:
            print('%d/%d' % (i, len(persone)), flush=True)
            json.dump(fatti, open(USCITA, 'w', encoding='utf-8'), sort_keys=True, indent=0)
        time.sleep(0.05)
    json.dump(fatti, open(USCITA, 'w', encoding='utf-8'), sort_keys=True, indent=0)
    print('Fatto: %d persone' % len(fatti))


if __name__ == '__main__':
    main()
