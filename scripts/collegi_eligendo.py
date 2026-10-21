# -*- coding: utf-8 -*-
"""I collegi uninominali del 1994, 1996 e 2001, candidato per candidato.

Dal 1994 al 2001 tre quarti dei deputati e dei senatori si eleggono in un
collegio: vince chi prende piu' voti. Gli archivi del Ministero dell'Interno
(Eligendo, open data) hanno i voti di ogni candidato in ogni collegio:

  Camera   Camera_<data>_Uninom_Cand&Contr.txt, comune per comune; chi corre
           con piu' simboli ha una riga per simbolo con gli stessi voti.
  Senato   Senato_<anno>_candlista.txt, gia' sommati per collegio.

Gli zip si scaricano a mano da elezionistorico.interno.gov.it/eligendo/
opendata.php (rimandano a dait.interno.gov.it/documenti/opendata/...) in
data/cache/eligendo/, estratti in data/cache/eligendo/estratti/<nome zip>/.

L'aggancio ai nostri parlamentari: cognome e data di nascita; se la data
manca (succede nel 1996), cognome e nome per intero, ma solo se nell'elenco
c'e' una persona sola con quel nome. Chi resta fuori finisce nell'elenco da
guardare a mano. Scrive data/collegi.json.
"""
import collections
import csv
import glob
import io
import json
import os
import re
import sys
import unicodedata

QUI = os.path.dirname(os.path.abspath(__file__))
ESTRATTI = os.path.join(QUI, '..', 'data', 'cache', 'eligendo', 'estratti')
ELENCO = os.path.join(QUI, '..', 'data', 'elenco.json')
USCITA = os.path.join(QUI, '..', 'data', 'collegi.json')
ARRICCHIMENTI = os.path.join(QUI, '..', 'data', 'arricchimenti.json')
ANNI = {'1994': 'XII', '1996': 'XIII', '2001': 'XIV'}
LEG = ['XI', 'XII', 'XIII', 'XIV', 'XV']

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass


def norm(s):
    s = unicodedata.normalize('NFKD', s or '').upper()
    return re.sub(r'[^A-Z]', '', ''.join(c for c in s if not unicodedata.combining(c)))


def data_iso(s):
    m = re.match(r'(\d{1,2})/(\d{1,2})/(\d{4})', (s or '').strip())
    return '%s-%02d-%02d' % (m.group(3), int(m.group(2)), int(m.group(1))) if m else ''


def numero(s):
    s = (s or '').strip().replace('.', '').replace(',', '.') if ',' in (s or '') else (s or '').strip()
    return int(float(s)) if s else 0


def righe(percorso):
    with io.open(percorso, encoding='latin-1', newline='') as f:
        return list(csv.DictReader(f, delimiter=';'))


def bel_nome(s):
    """'TORINO 1' -> 'Torino 1'; i nomi dei collegi arrivano a volte maiuscoli."""
    s = (s or '').strip()
    return s if not s.isupper() else ' '.join(
        x if re.match(r'^[IVX]+$', x) else x.capitalize() for x in s.lower().split()).title()


def camera(anno):
    f = glob.glob(os.path.join(ESTRATTI, 'camera-%s*' % anno, 'Camera_*_Uninom_Cand&Contr.txt'))[0]
    per_comune, simboli = {}, collections.defaultdict(list)
    for r in righe(f):
        cand = (r['circ'].strip(), r['coll'].strip(), r['cognome'].strip(), r['nome'].strip(),
                data_iso(r['datanascita']))
        per_comune[cand + (r['comune'].strip(),)] = numero(r['TOTVOTI'])
        s = (r['descrcontrass'] or '').strip()
        if s and s not in simboli[cand]:
            simboli[cand].append(s)
    voti = collections.Counter()
    for k, v in per_comune.items():
        voti[k[:5]] += v
    return [(k[0], k[1], k[2], k[3], k[4], v, simboli[k], '') for k, v in voti.items()]


def senato(anno):
    f = glob.glob(os.path.join(ESTRATTI, 'senato-%s*' % anno, 'Senato_*_candlista.txt'))[0]
    voti, simboli, eletti = collections.Counter(), collections.defaultdict(list), set()
    for r in righe(f):
        cand = (r['REGIONE'].strip(), r['COLLEGIO'].strip(), r['cognome'].strip(), r['nome'].strip(),
                data_iso(r['datanascita']))
        voti[cand] += numero(r['votiLista'])
        s = (r['descrlista'] or '').strip()
        if s and s not in simboli[cand]:
            simboli[cand].append(s)
        if (r.get('CODTIPOELETTO') or '').strip() == 'E':
            eletti.add(cand)
    return [k + (v, simboli[k], 'E' if k in eletti else '') for k, v in voti.items()]


PARTICELLE = {'DE', 'DI', 'DEL', 'DELLA', 'DELLE', 'DEI', 'DEGLI', 'DA', 'DAL', 'DALLA', 'LA', 'LO', 'LE'}


def pezzi(cog):
    return {norm(x) for x in re.split(r"[\s'-]+", cog) if len(norm(x)) > 2 and norm(x) not in PARTICELLE}


def cognomi_di(cog):
    """'BENETTO IN RAVETTO' -> BENETTO, RAVETTO; 'CORSI ZEFFIRELLI' -> anche CORSI."""
    cog = re.sub(r'\s+', ' ', cog.upper().replace('0', 'O'))
    fuori = {norm(cog)}
    for pezzo in re.split(r'\s+IN\s+', cog):
        fuori.add(norm(pezzo))
        fuori.update(pezzi(pezzo))
    return fuori


def nomi_di(nome):
    """I nomi di battesimo, piu' quello con cui si e' noti ('DETTO FURIO')."""
    nome = re.sub(r'\s+IN\s+.*$', '', nome.upper())
    return {norm(x) for x in re.split(r'\s+|DETT[OA]|NOTO', nome) if len(norm(x)) > 1}


def main():
    persone = json.load(io.open(ELENCO, encoding='utf-8'))['persone']
    per_cognome = collections.defaultdict(list)
    for p in persone:
        cog = p.get('cognome') or p['nome'].split()[-1]
        for k in {norm(cog)} | pezzi(cog):
            per_cognome[k].append(p)
    esatta = lambda p: p.get('nascita') and p.get('prec_nascita') == 'giorno'
    seduto = lambda p, leg, ramo: (p.get('ramo') or {}).get(leg) == ramo
    battesimo = lambda p: {norm(x) for x in p['nome'].split()} - {norm(p.get('cognome') or '')} - \
        pezzi(p.get('cognome') or '')

    def cerca(c, leg, ramo, vincitore):
        cog, nome, nato = c[2], c[3], c[4]
        tutti = list({p['qid']: p for k in cognomi_di(cog) for p in per_cognome.get(k, [])}.values())
        # chi ha il cognome identico per intero viene prima ('RUSSO SPENA' non e' un Russo)
        interi = [p for p in tutti if norm(p.get('cognome') or '') == norm(cog)]
        if interi and len(cog.split()) > 1:
            tutti = interi
        if nato:
            stessa = [p for p in tutti if esatta(p) and p['nascita'] == nato]
            if stessa:
                return stessa
            if vincitore:
                # eletto, nato quel giorno e seduto li': il cognome puo' essere scritto
                # in un altro modo (Giovannelli, Mininni Iannuzzi); le prime cinque lettere
                # pero' devono tornare: Togni e Tarolli sono nati lo stesso giorno
                gemelli = [p for p in persone if esatta(p) and p['nascita'] == nato and seduto(p, leg, ramo)
                           and norm(p.get('cognome') or '')[:5] == norm(cog)[:5]]
                if len(gemelli) == 1:
                    return gemelli
            # una data diversa esclude, salvo che sia chi ha vinto e sieda li'
            tutti = [p for p in tutti if not esatta(p) or (vincitore and seduto(p, leg, ramo))]
        nomi = nomi_di(nome)
        col_nome = [p for p in tutti if nomi & {norm(x) for x in p['nome'].split()}]
        if len(col_nome) > 1:
            col_nome = [p for p in col_nome if leg in (p.get('ramo') or {})] or col_nome
        if len(col_nome) > 1:
            # due omonimi: vale chi ha proprio quei nomi di battesimo
            uguali = [p for p in col_nome if battesimo(p) == nomi]
            col_nome = uguali if len(uguali) == 1 else col_nome
        if not vincitore and not nato:
            # senza data, chi ha perso si prende solo se in Parlamento c'era li' vicino
            vicine = {LEG[i] for i in range(max(0, LEG.index(leg) - 1), LEG.index(leg) + 2)}
            col_nome = [p for p in col_nome if vicine & set(p.get('ramo') or {})]
        if len(col_nome) == 1 or not vincitore:
            return col_nome
        # chi ha vinto il collegio siede in quel ramo: basta il cognome
        return [p for p in tutti if (p.get('ramo') or {}).get(leg) == ramo]

    # chi la Camera registra eletto in ciascun collegio (scripts/arricchisci.py)
    ufficiali = collections.defaultdict(set)
    for q, s in json.load(io.open(ARRICCHIMENTI, encoding='utf-8'))['schede'].items():
        for leg, e in (s.get('elezioni') or {}).items():
            m = re.match(r'collegio uninominale di (.+?)(?: \(|,|$)', e[1]) if e[0] == 'M' else None
            if m:
                ufficiali[(leg, norm(m.group(1)))].add(q)

    fuori, mancate, contati = {}, [], collections.Counter()
    for anno, leg in sorted(ANNI.items()):
        for ramo, leggi in (('C', camera), ('S', senato)):
            cand = leggi(anno)
            collegi = collections.defaultdict(list)
            for c in cand:
                collegi[(c[0], c[1])].append(c)
            for (zona, coll), tutti in collegi.items():
                tutti.sort(key=lambda c: -c[5])
                totale = sum(c[5] for c in tutti)
                trovati = [cerca(c, leg, ramo, pos == 1 or c[7] == 'E') for pos, c in enumerate(tutti, 1)]
                # se i voti danno primo chi non e' stato eletto li', l'archivio non torna:
                # il collegio resta fuori (Camera: chi registra la Camera; Senato: la E)
                eletto = ufficiali.get((leg, norm(coll)))
                if ((ramo == 'C' and eletto and len(trovati[0]) == 1 and trovati[0][0]['qid'] not in eletto)
                        or (ramo == 'S' and tutti[0][7] != 'E')):
                    mancate.append([anno, ramo, coll, 'il primo nei voti non risulta eletto', '', '', 0])
                    continue
                for pos, (c, tr) in enumerate(zip(tutti, trovati), 1):
                    if len(tr) != 1:
                        # chi ha vinto il collegio e' di sicuro nostro: se non si trova, va guardato
                        if pos == 1 or c[7] == 'E' or len(tr) > 1:
                            mancate.append([anno, ramo, coll, c[2], c[3], c[4], len(tr)])
                        continue
                    altro = tutti[1] if pos == 1 and len(tutti) > 1 else tutti[0]
                    fuori.setdefault(tr[0]['qid'], []).append(
                        [anno, ramo, bel_nome(coll), c[5], round(1000 * c[5] / totale) / 10 if totale else 0,
                         pos, len(tutti), c[5] - altro[5], ' / '.join(c[6]), 1 if c[7] == 'E' and pos > 1 else 0, c[0]])
    # la stessa persona in due collegi dello stesso anno e ramo: vale quello nella
    # sua circoscrizione; se non si sa, nessuno dei due
    per_q = {p['qid']: p for p in persone}
    for q, v in list(fuori.items()):
        doppi = collections.Counter((r[0], r[1]) for r in v)
        for k, n in doppi.items():
            if n < 2:
                continue
            circ = norm((per_q[q].get('circoscrizioni') or {}).get(ANNI[k[0]], ''))[:6]
            dentro = [r for r in v if (r[0], r[1]) == k and circ and norm(r[-1]).startswith(circ)]
            for r in [r for r in v if (r[0], r[1]) == k and (len(dentro) != 1 or r is not dentro[0])]:
                v.remove(r)
                mancate.append([r[0], r[1], r[2], per_q[q]['nome'], 'omonimo in due collegi', '', 2])
        if not v:
            del fuori[q]
    for v in fuori.values():
        for r in v:
            r.pop()
            contati[(r[0], r[1], 'vinto' if r[5] == 1 else 'perso')] += 1
        v.sort()
    for k in sorted(contati):
        print(k, contati[k])
    print('persone con almeno un collegio: %d; da guardare: %d' % (len(fuori), len(mancate)))
    json.dump({'_nota': "Collegi uninominali di Camera e Senato 1994, 1996, 2001 dagli open data del "
                        "Ministero dell'Interno (Eligendo). Per persona: [anno, ramo, collegio, voti, "
                        "percentuale, posizione, candidati, distacco dal secondo o dal primo, simboli, eletto col recupero al Senato]. "
                        "Generato da scripts/collegi_eligendo.py.",
               'collegi': fuori, 'non_agganciati': mancate},
              io.open(USCITA, 'w', encoding='utf-8', newline='\n'), ensure_ascii=False, indent=0)


if __name__ == '__main__':
    main()
