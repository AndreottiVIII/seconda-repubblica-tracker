# -*- coding: utf-8 -*-
"""Tutti i file che il Senato offre da scaricare, dalla XIII alla XVI.

Il Senato non pubblica archivi interi come la Camera: la sua pagina "Scarica
i dati" (dati.senato.it/DatiSenato/browse/) e' fatta di moduli, uno per tipo
di dato, che restituiscono un CSV. Qui si compilano quei moduli come farebbe
una persona, uno per volta e con calma:

  per legislatura   l'elenco dei senatori, l'elenco dei disegni di legge
  per senatore      gruppi, commissioni, disegni di legge, interventi sui
                    disegni di legge, documenti non legislativi, sindacato
                    ispettivo, voti in tutte le votazioni elettroniche

La XII legislatura (1994-96) il Senato non la offre.

I file finiscono in data/cache/zip_senato/<legislatura>/, che non si versiona.
Chi c'e' gia' non si riscarica: il giro si puo' interrompere e riprendere.
"""
import csv
import http.cookiejar
import io
import os
import re
import sys
import time
import urllib.parse
import urllib.request

QUI = os.path.dirname(os.path.abspath(__file__))
USCITA = os.path.join(QUI, '..', 'data', 'cache', 'zip_senato')
BASE = 'https://dati.senato.it/DatiSenato'
UA = 'SecondaRepubblicaTracker/0.1 (progetto personale)'
PAUSA = 0.5

LEGISLATURE = {13: ('1996-05-09', '2001-05-29'), 14: ('2001-05-30', '2006-04-27'),
               15: ('2006-04-28', '2008-04-28'), 16: ('2008-04-29', '2013-03-14')}

# alias e numero del modulo, come stanno nelle pagine del Senato
PER_LEGISLATURA = [('senatori-legislatura', 2, False), ('elenco-ddl-date', 33, True)]
PER_SENATORE = [
    ('incarichi-senatore-gruppi', 8, False),
    ('incarichi-senatore-commissioni', 9, False),
    ('votazioni-senatore', 11, False),
    ('ddl-senatore-date', 37, True),
    ('interventi-senatore-ddl-date', 5, True),
    ('documenti-senatore-date', 38, True),
    ('sindisp-senatore-date', 39, True),
]

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

barattolo = http.cookiejar.CookieJar()
apri = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(barattolo))
apri.addheaders = [('User-Agent', UA)]
gettone = {}


def pagina(n, leg):
    t = apri.open('%s/browse/%d?legislatura=%d' % (BASE, n, leg), timeout=120).read().decode('utf-8', 'replace')
    m = re.search(r'name="authenticity_token" type="hidden" value="([^"]+)"', t)
    gettone['v'] = m.group(1)


def scarica(alias, numero, leg, campi, destinazione, tentativi=3):
    if os.path.exists(destinazione) and os.path.getsize(destinazione) > 0:
        return 'gia'
    dati = {'authenticity_token': gettone['v'], 'alias': alias, 'id': str(numero),
            'legislatura': str(leg), 'query_format': 'csv', 'commit': 'Download'}
    dati.update(campi)
    ultimo = None
    for i in range(tentativi):
        try:
            r = apri.open(BASE + '/virtuoso_bridge/query/execute',
                          urllib.parse.urlencode(dati).encode(), timeout=300)
            tipo = r.headers.get('Content-Type', '')
            corpo = r.read()
            if 'csv' not in tipo:
                raise RuntimeError('risposta non CSV (%s)' % tipo)
            os.makedirs(os.path.dirname(destinazione), exist_ok=True)
            open(destinazione, 'wb').write(corpo)
            return 'ok'
        except Exception as e:
            ultimo = e
            time.sleep(5 * (i + 1))
            pagina(6, leg)
    print('    NON riuscito %s: %s' % (os.path.basename(destinazione), str(ultimo)[:80]))
    return 'errore'


def main():
    conti = {'ok': 0, 'gia': 0, 'errore': 0}
    for leg, (da, a) in LEGISLATURE.items():
        cartella = os.path.join(USCITA, str(leg))
        pagina(6, leg)
        for alias, numero, con_date in PER_LEGISLATURA:
            campi = {'search[legislatura]': str(leg)}
            if con_date:
                campi.update({'search[dataInizio]': da, 'search[dataFine]': a})
            conti[scarica(alias, numero, leg, campi, os.path.join(cartella, alias + '.csv'))] += 1
            time.sleep(PAUSA)
        elenco = os.path.join(cartella, 'senatori-legislatura.csv')
        senatori = sorted({r['senatore'].rsplit('/', 1)[-1]
                           for r in csv.DictReader(io.open(elenco, encoding='utf-8'))})
        print('legislatura %d: %d senatori' % (leg, len(senatori)))
        for k, s in enumerate(senatori, 1):
            for alias, numero, con_date in PER_SENATORE:
                campi = {'search[senatore]': s, 'search[legislatura]': str(leg)}
                if alias == 'interventi-senatore-ddl-date':
                    # questo modulo non ha il campo legislatura: se c'e', risponde una pagina d'errore
                    del campi['search[legislatura]']
                if con_date:
                    campi.update({'search[dataInizio]': da, 'search[dataFine]': a})
                esito = scarica(alias, numero, leg, campi,
                                os.path.join(cartella, alias, s + '.csv'))
                conti[esito] += 1
                if esito != 'gia':
                    time.sleep(PAUSA)
            if k % 25 == 0:
                print('  %d/%d senatori  (%s)' % (k, len(senatori), conti))
    print('fatto:', conti)


if __name__ == '__main__':
    main()
