# -*- coding: utf-8 -*-
"""Compatta i dati e li inietta dentro il modello: esce un file HTML solo.

Un file solo, coi dati dentro: si apre col doppio clic dal disco, si mette su
qualunque hosting statico, non serve ne' un server ne' un database. Le chiavi
sono di una o due lettere perche' il file finito viaggia intero nel browser.
"""
import sys, os, json, datetime, re, hashlib

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

QUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, QUI)
import casacche, controlla_js

INGRESSO = os.path.join(QUI, '..', 'data', 'elenco.json')
MODELLO = os.path.join(QUI, 'modello.html')
DISTINTIVI = os.path.join(QUI, '..', 'data', 'distintivi.json')
USCITA = os.path.join(QUI, '..', 'sito')

TITOLO = 'Seconda Repubblica Tracker'
ORDINE = casacche.ORDINE

ANNI = {'XII': '1994-1996', 'XIII': '1996-2001', 'XIV': '2001-2006',
        'XV': '2006-2008', 'XVI': '2008-2013'}

# Le legislature cominciano e finiscono in questi giorni: servono a disegnare
# la striscia del tempo in scala, non a legislature di larghezza uguale.
DURATA = {
    'XII':  ('19940415', '19960508'), 'XIII': ('19960509', '20010529'),
    'XIV':  ('20010530', '20060427'), 'XV':   ('20060428', '20080428'),
    'XVI':  ('20080429', '20130314'),
}

COLOFONE = [
    'SECONDA REPUBBLICA TRACKER',
    '',
    'Chi ha cambiato casacca in Parlamento fra il 1994 e il 2013, e quante '
    'volte. Cinque legislature, dalla XII alla XVI.',
    '',
    'I dati vengono da tre fonti pubbliche, interrogate ogni notte e messe a '
    'confronto fra loro: gli open data della Camera dei deputati '
    '(dati.camera.it), quelli del Senato della Repubblica (dati.senato.it) e '
    'Wikidata. L’elenco di chi ha seduto in Parlamento lo danno le Camere: '
    'dove le fonti si contraddicono, comandano i registri ufficiali.',
    '',
    'Il sito registra fatti, non giudizi. Un cambio di gruppo parlamentare '
    'è un atto pubblico, depositato e datato. Qui trovate quello, con la '
    'data e la fonte. Le conclusioni sono affare vostro.',
    '',
    'Se trovate un errore scrivetemi e lo correggo: davide.caniatti@gmail.com',
    '',
    'Fatto da Davide Caniatti insieme a Claude (Anthropic), che ha scritto il '
    'codice, scovato i difetti dei dati e discusso ogni scelta di metodo.',
    '',
    'Per copiare questo sito, ripubblicarlo altrove, riusarne delle parti o '
    'adattarlo serve la mia autorizzazione scritta, e va citata la fonte: '
    'Seconda Repubblica Tracker, Davide Caniatti. Vale anche per gli estratti, '
    'per le tabelle e per i dati così come li trovate qui, già '
    'incrociati e verificati.',
]

# Le cariche che fanno di una persona un nome che si ricorda. Wikidata le
# scrive lunghe e uguali per tutti: 'ministro della giustizia della Repubblica
# Italiana'. La coda si taglia, il resto vale.
CODA = ' della Repubblica Italiana'
PESANTI = ('presidente del consiglio', 'presidente della camera',
           'presidente del senato', 'presidente della repubblica',
           'vicepresidente del consiglio', 'ministro', 'ministri')


def ripulisci_carica(c):
    c = (c or '').strip()
    if c.endswith(CODA):
        c = c[:-len(CODA)]
    c = re.sub(r'\s+', ' ', c).strip()
    return c[:1].upper() + c[1:] if c else ''


def e_pesante(c):
    b = (c or '').lower()
    if 'deputato' in b or 'senatore' in b:
        return False
    return any(b.startswith(x) for x in PESANTI)


def foto_breve(u):
    """Della foto si tiene il solo nome del file: il resto e' sempre uguale."""
    if not u:
        return None
    return u.rsplit('/', 1)[-1]


def wiki_breve(u):
    if not u:
        return None
    return u.rsplit('/', 1)[-1]


def compatta(p, gruppi, ant):
    d = {
        'q': p['qid'],
        'n': p['nome'] or '?',
        's': {'vivente': 1, 'deceduto': 2, 'ignoto': 3}[p['stato']],
        'm': [x for x in ORDINE if x in p['mandati']],
        'c': casacche.cambi(p, gruppi, ant),
        # Il cognome serve a mettere l'elenco in ordine. Per i ministri mai
        # eletti nessun registro lo separa dal nome: si ripiega sull'ultima
        # parola, che nella stragrande maggioranza dei casi e' quella giusta.
        'co': p.get('cognome') or (p['nome'] or '?').split()[-1],
    }
    if p.get('nascita'):
        d['b'] = p['nascita']
    if p.get('morte'):
        d['d'] = p['morte']
    ramo = p.get('ramo') or {}
    passi = []
    for m in ORDINE:
        for g in (p.get('gruppi_per_mandato') or {}).get(m, []):
            chiave = '%s|%s|%s' % (m, ramo.get(m, '?'), g['g'])
            passi.append([ORDINE.index(m), gruppi.get(chiave) or '?',
                          g.get('da') or '', g.get('a') or '',
                          ramo.get(m, '?'), g.get('allora') or ''])
    if passi:
        d['g'] = passi
    governi = [x.replace('Governo ', '') for x in p['mandati']
               if x.startswith('Governo ')]
    if governi:
        d['gv'] = governi
    cariche = sorted({ripulisci_carica(c) for c in (p.get('cariche') or [])
                      if e_pesante(c)})
    if cariche:
        d['k'] = cariche
        d['h'] = 1
    if p.get('foto'):
        d['f'] = foto_breve(p['foto'])
    elif p.get('id_camera'):
        # Ripiego: la foto ufficiale della Camera, che ce l'ha per il 99% dei
        # suoi deputati. L'indirizzo si ricava dall'identificativo e dalla
        # legislatura, e vale la pena tenerla anche quando Wikidata tace.
        camerali = [m for m in ORDINE if ramo.get(m) == 'C']
        if camerali:
            d['fc'] = [p['id_camera'], camerali[-1]]
    if p.get('wikipedia'):
        d['w'] = wiki_breve(p['wikipedia'])
    if p.get('non_eletto'):
        d['x'] = 1
    if p.get('senatore_a_vita'):
        d['v'] = 1
    if p.get('solo_registro'):
        d['r'] = 1
    if p.get('morte_dubbia'):
        d['md'] = p['morte_dubbia']
    if p.get('id_camera'):
        d['ci'] = p['id_camera']
    return d


def main():
    grezzo = json.load(open(INGRESSO, encoding='utf-8'))
    M = casacche.leggi_mappa()
    gruppi, partiti = M['gruppi'], M['partiti']
    ant = casacche.antenati(partiti)

    persone = [compatta(p, gruppi, ant) for p in grezzo['persone']]
    persone.sort(key=lambda x: x['n'])

    # I distintivi: fatti datati e con una fonte, scritti a mano perche'
    # nessun registro li tiene. Il file e' piccolo apposta: se un distintivo
    # non si puo' scrivere senza un aggettivo, non e' un fatto.
    distintivi = {}
    if os.path.exists(DISTINTIVI):
        distintivi = {k: v for k, v in
                      json.load(open(DISTINTIVI, encoding='utf-8')).items()
                      if not k.startswith('_')}
        noti = {p['q'] for p in persone}
        for q in list(distintivi):
            if q not in noti:
                print('  distintivo per uno sconosciuto, ignorato: %s' % q)
                del distintivi[q]
        for p in persone:
            if p['q'] in distintivi:
                p['ds'] = distintivi[p['q']]
        print('distintivi assegnati: %d' % len(distintivi))

    dati = {
        'generato': datetime.date.today().isoformat(),
        'persone': persone,
        'partiti': partiti,
        'legislature': [{'n': m, 'anni': ANNI[m],
                         'da': DURATA[m][0], 'a': DURATA[m][1]} for m in ORDINE],
    }

    modello = open(MODELLO, encoding='utf-8').read()
    corpo = json.dumps(dati, ensure_ascii=False, separators=(',', ':'))

    # La versione e' un'impronta del contenuto, non un orario: cosi' cambia
    # quando cambia qualcosa davvero, e chi ha la pagina aperta non se la
    # vede ricaricare ogni notte per niente. La data di generazione resta
    # fuori dal conto proprio per questo.
    senza_data = dict(dati)
    senza_data.pop('generato', None)
    impronta = hashlib.md5(
        (modello + json.dumps(senza_data, ensure_ascii=False, sort_keys=True)
         ).encode('utf-8')).hexdigest()[:12]

    html = (modello
            .replace('/*__DATI__*/', corpo)
            .replace('/*__COLOFONE__*/', json.dumps(COLOFONE, ensure_ascii=False))
            .replace('%%TITOLO%%', TITOLO)
            .replace('%%VERSIONE%%', impronta))

    # Prima di scrivere su disco. Con i dati dentro la pagina, una stringa
    # non chiusa non rompe una funzione: spegne tutto lo script, e il sito
    # diventa una scrivania vuota senza nemmeno un messaggio d'errore.
    controlla_js.controlla(html, 'index.html')

    os.makedirs(USCITA, exist_ok=True)
    percorso = os.path.join(USCITA, 'index.html')
    open(percorso, 'w', encoding='utf-8').write(html)
    # Il file che la pagina interroga per sapere se e' rimasta indietro.
    open(os.path.join(USCITA, 'versione.txt'), 'w', encoding='utf-8').write(impronta)

    vivi = sum(1 for p in persone if p['s'] == 1)
    print('%s: %d persone, %d viventi, %d cambi di casacca'
          % (os.path.basename(percorso), len(persone), vivi,
             sum(p['c'] for p in persone)))
    print('versione: %s' % impronta)
    print('peso: %.2f MB' % (os.path.getsize(percorso) / 1024.0 / 1024.0))


if __name__ == '__main__':
    main()
