# -*- coding: utf-8 -*-
"""La prima fiducia al Senato di ogni governo, dalla XIII alla XVI, nome per nome.

Il Senato vota la fiducia per appello nominale, e negli open data gli appelli
nominali ci sono solo dalla XVIII. Per il 1996-2013 i nomi stanno nei resoconti
stenografici: "Rispondono si' i senatori: Adamo, Adragna, ...". Il sito del
Senato respinge i programmi (risponde una pagina vuota): gli elenchi li ha letti
il browser, in pagina, e li ha salvati in data/cache/senato_resoconti/
fiducie_senato.json. Per la XII (1994-96) i resoconti sono solo in PDF, e
mancano.

Qui si agganciano i cognomi ai senatori in carica quel giorno
(data/cache/zip_senato/<leg>/senatori-legislatura.csv). Il resoconto scrive il
cognome, e per gli omonimi anche il nome ("Monti Mario"). Dove fra una lettera
e l'altra dell'alfabeto la virgola si perde, due cognomi restano attaccati
("Vitali Zanda"): si separano quando i due pezzi sono due senatori.

Scrive data/fiducie_senato.json.
"""
import collections
import csv
import io
import json
import os
import re
import sys
import unicodedata

QUI = os.path.dirname(os.path.abspath(__file__))
D = os.path.join(QUI, '..', 'data', 'cache', 'zip_senato')
FONTE = os.path.join(QUI, '..', 'data', 'cache', 'senato_resoconti', 'fiducie_senato.json')
USCITA = os.path.join(QUI, '..', 'data', 'fiducie_senato.json')

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass


def norm(s):
    s = unicodedata.normalize('NFKD', s or '').upper().replace('-', ' ').replace("'", ' ').replace('’', ' ')
    s = re.sub(r'[^A-Z ]', '', ''.join(c for c in s if not unicodedata.combining(c)))
    return re.sub(r'\s+', ' ', s).strip()


def in_carica(leg, giorno):
    fuori = []
    for r in csv.DictReader(io.open(os.path.join(D, str(leg), 'senatori-legislatura.csv'), encoding='utf-8')):
        a, b = r['inizioMandato'], r['fineMandato'] or '9999-99-99'
        if a <= giorno <= b:
            fuori.append((r['senatore'].rsplit('/', 1)[-1], norm(r['cognome']), norm(r['nome'])))
    return fuori


def esatto(n, senatori):
    pari = [s for s in senatori if s[1] == n]
    if len(pari) == 1:
        return [pari[0][0]]
    # omonimi: "MONTI MARIO" = cognome + nome
    # il resto dopo il cognome deve essere il nome per intero, o il suo inizio
    con_nome = [s for s in senatori if n.startswith(s[1] + ' ') and
                (s[2] + ' ').startswith(n[len(s[1]) + 1:] + ' ')]
    return [con_nome[0][0]] if len(con_nome) == 1 else None


def simile(n, senatori):
    """I cognomi doppi scritti per intero da una parte e corti dall'altra ("PASSIGLI" e
    "PASSIGLI VANNI", "CORSI ZEFFIRELLI" e "ZEFFIRELLI"): vale se ce n'e' uno solo, e se le
    parole in piu' non sono il cognome di un altro senatore ("AYALA BAIO" sono due persone)."""
    p = n.split()
    primi = {s[1].split()[0] for s in senatori}
    trovati = []
    for s in senatori:
        c = s[1].split()
        if p[:len(c)] == c and len(p) > len(c):
            avanzo = p[len(c):]
        elif p[-len(c):] == c and len(p) > len(c):
            avanzo = p[:-len(c)]
        elif c[:len(p)] == p:
            avanzo = []
        else:
            continue
        if avanzo and avanzo[0] in primi - {c[0]}:
            continue
        trovati.append(s)
    return [trovati[0][0]] if len(trovati) == 1 else None


def dividi(parole, senatori, regola):
    """Piu' cognomi attaccati ("MURA PITTONI RIZZI"): uno alla volta, da sinistra."""
    if not parole:
        return []
    for k in range(len(parole), 0, -1):
        testa = regola(' '.join(parole[:k]), senatori)
        if testa:
            resto = dividi(parole[k:], senatori, regola)
            if resto is not None:
                return testa + resto
    return None


def aggancia(nome, senatori):
    """Un nome del resoconto -> [id] (uno, o piu' se erano attaccati), o None. Prima
    l'esatto, poi cognomi attaccati esatti ("VITALI ZANDA"), poi i cognomi doppi."""
    n = norm(nome)
    # la separazione prima dei cognomi doppi: "AYALA BAIO DOSSI" sono Ayala e Baio, non solo Ayala
    return (esatto(n, senatori) or dividi(n.split(), senatori, esatto) or
            dividi(n.split(), senatori, lambda x, ss: esatto(x, ss) or simile(x, ss)) or simile(n, senatori))


def main():
    fuori, problemi = [], []
    for f in json.load(io.open(FONTE, encoding='utf-8')):
        senatori = in_carica(f['leg'], f['data'])
        voto = {}
        for scelta, chiave in (('F', 'si'), ('C', 'no'), ('A', 'astenuti')):
            for nome in f[chiave]:
                ids = aggancia(nome, senatori)
                if not ids:
                    problemi.append([f['governo'], scelta, nome])
                    continue
                for s in ids:
                    voto[s] = scelta
        conta = collections.Counter(voto.values())
        uff = f.get('ufficiale') or [None, None, None]
        print('%-15s %s  si %3d  no %3d  astenuti %d   ufficiale %s' % (
            f['governo'], f['data'], conta['F'], conta['C'], conta['A'], '/'.join(map(str, uff))))
        fuori.append({'governo': f['governo'], 'leg': f['leg'], 'data': f['data'].replace('-', ''),
                      'fonte': f['url'], 'voti': voto, 'si': conta['F'], 'no': conta['C'], 'astenuti': conta['A'],
                      'ufficiale': f.get('ufficiale')})
    print('nomi non agganciati: %d' % len(problemi))
    for p in problemi:
        print('  ', p)
    json.dump({'_nota': "Prima fiducia al Senato di ogni governo, XIII-XVI, nome per nome, dai resoconti "
                        "stenografici del Senato. Generato da scripts/fiducie_senato.py.",
               'fiducie': fuori, 'non_agganciati': problemi},
              io.open(USCITA, 'w', encoding='utf-8', newline='\n'), ensure_ascii=False)


if __name__ == '__main__':
    main()
