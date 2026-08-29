# -*- coding: utf-8 -*-
"""Fonde il cursus honorum scritto a mano con le cariche prese da Wikidata.

Le due liste dicevano in gran parte le stesse cose con parole diverse, e la
scheda le stampava tutte e due: Sergio Mattarella si ritrovava la presidenza
della Repubblica scritta due volte a quattro righe di distanza.

Qui si tiene del cursus curato solo quello che le cariche non dicono gia'.
Ed e' parecchio, perche' Wikidata registra le cariche di governo e ignora
quasi tutto il resto: segretari di partito, sindacati, Banca d'Italia, CONI,
IRI. Quella e' la ragione per cui il foglio scritto a mano esiste.

Tre modi per dire che una voce del cursus e' gia' coperta:

  1. le parole. 'Rapporti con il Parlamento' sta dentro 'Ministro per i
     rapporti con il Parlamento';
  2. gli anni esatti. 'Vice PdC (1983-1987)' e 'Vicepresidente del Consiglio
     1983-1987' sono la stessa cosa, per quanto scritte in modo diverso;
  3. il ministero in forma breve. 'Agricoltura (1993-1994)' e 'Ministro delle
     politiche agricole alimentari e forestali' non hanno una parola in comune
     e sono la stessa poltrona: se il periodo si sovrappone a una carica di
     ministro e la voce non comincia con un ruolo diverso, e' quella.
"""
import re
import unicodedata

# Parole che non distinguono una carica dall'altra.
VUOTE = {
    'ministro', 'ministero', 'della', 'dello', 'dell', 'dei', 'degli', 'delle',
    'del', 'di', 'per', 'il', 'la', 'lo', 'i', 'gli', 'le', 'e', 'a', 'al',
    'alla', 'con', 'ai', 'alle', 'repubblica', 'italiana', 'italiano',
}

# Se una voce comincia cosi' non e' un ministero, e la terza regola non vale.
RUOLI = ('segretario', 'presidente', 'direttore', 'governatore', 'vicedirettore',
         'capogruppo', 'vigilanza', 'sottosegretario', 'vicepresidente', 'vice ',
         'commissario', 'sindaco', 'senatore', 'deputato')

APERTO = 2100  # un incarico ancora in corso


def parole(testo):
    """Le parole che contano, senza accenti, senza anni fra parentesi."""
    t = re.sub(r'\([^)]*\)', ' ', testo or '')
    t = unicodedata.normalize('NFKD', t.lower())
    t = ''.join(c for c in t if not unicodedata.combining(c))
    return {w for w in re.split(r'[^a-z0-9]+', t) if w and w not in VUOTE}


def periodi(testo):
    """Gli intervalli di anni dichiarati fra parentesi.

    Regge sia '(1987-1991)' che '(1969-1973/1989-1992)' che '(1991-)' che
    l'anno secco '(1993)'.
    """
    fuori = set()
    for blocco in re.findall(r'\(([^)]*)\)', testo or ''):
        for m in re.finditer(r'(\d{4})\s*-\s*(\d{4})?', blocco):
            fuori.add((int(m.group(1)),
                       int(m.group(2)) if m.group(2) else APERTO))
        for m in re.finditer(r'(?<![\d-])(\d{4})(?![\d-])', blocco):
            fuori.add((int(m.group(1)), int(m.group(1))))
    return fuori


def _si_sovrappongono(a, b):
    return a[0] <= b[1] and b[0] <= a[1]


def gia_detta(voce, cariche):
    """La voce del cursus e' gia' contenuta nelle cariche datate?"""
    mie_parole = parole(voce)
    miei_periodi = periodi(voce)

    for c in cariche:
        loro = parole(c['carica'])
        if mie_parole and mie_parole <= loro:
            return True

    anni_carica = {(c['da'] or '', c['a'] or '') for c in cariche}
    for da, a in miei_periodi:
        if (str(da), '' if a == APERTO else str(a)) in anni_carica:
            return True

    if not voce.lower().startswith(RUOLI):
        for c in cariche:
            if not c['da'] or not c['carica'].lower().startswith('ministro'):
                continue
            suo = (int(c['da']), int(c['a']) if c['a'] else APERTO)
            if any(_si_sovrappongono(mio, suo) for mio in miei_periodi):
                return True
    return False


def residuo(cursus, cariche):
    """Le voci del cursus curato che le cariche non dicono gia'."""
    if not cursus:
        return []
    cariche = cariche or []
    fuori = []
    for voce in re.split(r',\s*', cursus):
        voce = voce.strip().rstrip(',')
        if voce and not gia_detta(voce, cariche):
            fuori.append(voce)
    return fuori
