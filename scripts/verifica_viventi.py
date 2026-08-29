# -*- coding: utf-8 -*-
"""Passa in rassegna chi risulta vivente e chiede conto ai registri ufficiali.

Non basta che Wikidata taccia sulla morte di qualcuno: il silenzio non e' una
prova di vita. Qui ogni vivente viene cercato nel registro della Camera o del
Senato, e finisce in una di tre categorie:

  confermato   il registro lo conosce e non lo da' per morto
  non trovato  nessun registro lo aggancia: il suo essere vivo non e' verificato
  fuori        non e' mai stato eletto (i tecnici dei governi Ciampi e Dini)

Chi non torna per nome viene ricercato una seconda volta per legislatura piu'
data di nascita esatta: per la Camera e' VIRGINIO SCOTTI, per Wikidata Gerry
Scotti, ma il seggio e il giorno di nascita sono gli stessi.
"""
import sys, os, json, unicodedata
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import camera, senato

# La console di Windows parla ancora cp1252 e va in errore su una lettera
# straniera: un nome come Stojan Spetic ha fatto morire lo script prima che
# scrivesse i dati. Meglio un carattere storto a schermo che un giro perso.
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass


QUI = os.path.dirname(os.path.abspath(__file__))
ELENCO = os.path.join(QUI, '..', 'data', 'elenco.json')


def spoglio(s):
    s = unicodedata.normalize('NFKD', (s or '').lower())
    return ''.join(c for c in s if not unicodedata.combining(c))


def main():
    dati = json.load(open(ELENCO, encoding='utf-8'))
    vivi = [p for p in dati['persone'] if p['stato'] == 'vivente']

    registri = []
    for etichetta, modulo in [('Camera', camera), ('Senato', senato)]:
        try:
            reg = modulo.registro()
            registri.append((etichetta, modulo, reg, modulo.indice_per_data(reg),
                             modulo.indice_per_mandato(reg)))
        except Exception as e:
            print('%s non raggiungibile: %s' % (etichetta, e))

    alias = {}
    percorso = os.path.join(QUI, '..', 'data', 'alias_registri.json')
    if os.path.exists(percorso):
        alias = {k: v for k, v in json.load(open(percorso, encoding='utf-8')).items()
                 if not k.startswith('_')}

    per_nome, per_data, fuori, muti = [], [], [], []
    for p in vivi:
        # Un ministro tecnico non ha mai avuto un seggio: nessun registro
        # parlamentare puo' confermarlo, e non e' un buco nei dati.
        eletto = [m for m in p['mandati'] if not m.startswith('Governo')]
        if not eletto:
            fuori.append(p)
            continue
        esito = None
        for etichetta, modulo, reg, indice, per_mandato in registri:
            v, come = modulo.cerca_ampia(reg, indice, p['nome'], p['nascita'],
                                         eletto, per_mandato)
            if not v and alias.get(p['qid']):
                v, come = modulo.cerca_ampia(reg, indice, alias[p['qid']],
                                             p['nascita'], eletto, per_mandato)
            if v:
                esito = (etichetta, come, v)
                break
        if not esito:
            muti.append(p)
        elif esito[1] != 'nome':
            per_data.append((p, esito))
        else:
            per_nome.append((p, esito))

    print('VIVENTI PASSATI IN RASSEGNA: %d' % len(vivi))
    print('  confermati vivi dal registro, per nome        %4d' % len(per_nome))
    print('  confermati vivi, ritrovati per altra via      %4d' % len(per_data))
    print('  mai eletti: nessun registro li contiene        %4d' % len(fuori))
    print('  NON AGGANCIATI: la vita non e verificata  %4d' % len(muti))
    print()
    if per_data:
        print('RITROVATI CON I CRITERI PIU LARGHI (nome diverso fra le fonti):')
        for p, e in per_data[:12]:
            print('  %-30s n.%-11s %s, per %s' % (p['nome'], p['nascita'], e[0], e[1]))
        print()
    # Contraddizioni: noi lo diamo vivo, il registro lo da' morto. Non
    # dovrebbero esistercene, perche' la pipeline applica i decessi trovati:
    # se ne spunta una e' un difetto, non una curiosita'.
    contraddizioni = []
    for p, e in per_nome + per_data:
        if e[2].get('morte'):
            contraddizioni.append((p, e))

    print('CONTRADDIZIONI (noi vivo, registro morto): %d' % len(contraddizioni))
    for p, e in contraddizioni[:20]:
        print('  %-28s %s dice morto il %s' % (p['nome'], e[0], e[2]['morte']))
    print()

    print('NON AGGANCIATI, dal piu anziano:')
    for p in sorted(muti, key=lambda x: x['nascita'] or '9'):
        print('  %-28s n.%-11s %s' % (p['nome'], p['nascita'],
                                      ', '.join(p['mandati'])))
    print()

    print('MAI ELETTI (nessun registro parlamentare puo confermarli):')
    for p in sorted(fuori, key=lambda x: x['nascita'] or '9'):
        print('  %-28s n.%-11s %s' % (p['nome'], p['nascita'],
                                      ', '.join(p['mandati'])))
    print()

    # I piu' anziani sono quelli su cui un errore pesa di piu'.
    print('I VIVENTI PIU ANZIANI, con la loro conferma:')
    stato = {}
    for p, e in per_nome:
        stato[p['qid']] = e[0] + ', per nome'
    for p, e in per_data:
        stato[p['qid']] = e[0] + ', per ' + e[1]
    for p in sorted(vivi, key=lambda x: x['nascita'] or '9')[:20]:
        eta = 2026 - int(p['nascita'][:4]) if p['nascita'] else 0
        print('  %-28s %3d anni  %s' % (p['nome'], eta,
              stato.get(p['qid'], 'NESSUNA CONFERMA')))


if __name__ == '__main__':
    main()
