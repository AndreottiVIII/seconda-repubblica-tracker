# -*- coding: utf-8 -*-
"""Confronta l'elenco appena scaricato con quello dell'ultimo commit.

Stampa una riga se qualcosa e' davvero cambiato, e non stampa niente se l'unica
differenza e' la data di generazione. Serve al lavoro notturno per decidere se
vale la pena di un commit: cosi' la cronologia del repository resta un elenco
di fatti, e non un timbro quotidiano.
"""
import json, os, subprocess, sys

QUI = os.path.dirname(os.path.abspath(__file__))
ELENCO = os.path.join(QUI, '..', 'data', 'elenco.json')


def stati(persone):
    return {p['qid']: (p['stato'], p.get('morte'), p['nome']) for p in persone}


def main():
    nuovo = stati(json.load(open(ELENCO, encoding='utf-8'))['persone'])
    try:
        vecchio_txt = subprocess.check_output(
            ['git', 'show', 'HEAD:data/elenco.json'],
            cwd=os.path.join(QUI, '..'), stderr=subprocess.DEVNULL)
        vecchio = stati(json.loads(vecchio_txt.decode('utf-8'))['persone'])
    except Exception:
        print('primo caricamento dei dati')   # niente con cui confrontare
        return

    morti, tornati, aggiunti = [], [], []
    for q, (stato, morte, nome) in nuovo.items():
        if q not in vecchio:
            aggiunti.append(nome)
        elif vecchio[q][0] != stato:
            (morti if stato == 'deceduto' else tornati).append(nome)

    # Un morto non torna vivo. Se succede in massa vuol dire che una fonte e'
    # caduta e sta pubblicando un elenco monco: si ferma tutto.
    if len(tornati) > 3:
        sys.stderr.write(
            'FERMO TUTTO: %d persone tornerebbero in vita.\n'
            'Una fonte e\' caduta, e pubblicare adesso peggiorerebbe\n'
            'il sito invece di aggiornarlo.\n' % len(tornati))
        for nome in sorted(tornati)[:10]:
            sys.stderr.write('  %s\n' % nome)
        raise SystemExit(1)

    pezzi = []
    if morti:
        pezzi.append('ci lascia ' + ', '.join(sorted(morti)[:5])
                     + ('' if len(morti) <= 5 else ' e altri %d' % (len(morti) - 5)))
    if tornati:
        pezzi.append('%d cambi di stato all’indietro' % len(tornati))
    if aggiunti:
        pezzi.append('%d schede nuove' % len(aggiunti))
    spariti = [v[2] for q, v in vecchio.items() if q not in nuovo]
    if spariti:
        pezzi.append('%d schede sparite' % len(spariti))

    if pezzi:
        print('; '.join(pezzi))


if __name__ == '__main__':
    main()
