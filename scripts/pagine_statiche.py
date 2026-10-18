# -*- coding: utf-8 -*-
"""Il sito scomposto in una pagina per finestra, perche' Google lo trovi.

Il Windows 95 e' una pagina sola che apre finestre, e per Google era proprio
questo: una pagina. Le schede stavano dopo un cancelletto
(secondarepubblica.it/#persona/Q1394911), e quella parte dell'indirizzo lui la
ignora. Chi cercava "Clemente Mastella" non arrivava qui.

Qui ogni finestra che vale la pena trovare diventa un file vero, con il suo
indirizzo, il suo titolo e la sua descrizione:

    /onorevole/clemente-mastella/index.html
    /partito/udeur/index.html
    /cestino/index.html

A vista non cambia niente. Ogni file contiene la stessa scrivania e chiama lo
stesso programma, che sta in un file a parte (programma.js) e il browser
scarica una volta sola: e' lui a leggere l'indirizzo e ad aprire la finestra
giusta. Lo stesso schema di primarepubblica.net, che l'ha fatto per primo.

Tutto finisce in pubblica/, che e' la cartella che il lavoro notturno
pubblica. sito/index.html resta com'era: il file solo, coi dati dentro, che
si apre col doppio clic dal disco.
"""
import hashlib
import html
import json
import os
import re
import shutil
import unicodedata

INDIRIZZO = 'https://secondarepubblica.it'
SITO = 'Seconda Repubblica Tracker'

# Finestre che esistono ma che a chi cerca non servono: strumenti, non
# contenuti. Hanno la loro pagina, perche' un link deve funzionare, ma Google
# non le mostri.
FUORI_DAI_MOTORI = {'trova', 'aggiorna', 'confronta', 'esegui', 'errore'}

# L'icona come file vero. Quella incorporata nella pagina (data:) al browser
# basta, ma Google nei risultati di ricerca la ignora e mette il mappamondo
# grigio: vuole un indirizzo da scaricare, e una misura multipla di 48 pixel.
# Solo nelle pagine pubblicate: dal disco /favicon.ico non porta da nessuna
# parte, e li' resta l'icona incorporata.
ICONE = '\n'.join([
    '<link rel="icon" href="/favicon.ico" sizes="48x48">',
    '<link rel="icon" type="image/png" sizes="96x96" href="/favicon-96.png">',
    '<link rel="icon" type="image/png" sizes="192x192" href="/favicon-192.png">',
    '<link rel="apple-touch-icon" href="/apple-touch-icon.png">',
])
FILE_ICONE = ('favicon.ico', 'favicon-96.png', 'favicon-192.png', 'apple-touch-icon.png')


def scheggia(testo):
    """'Clemente Mastella' -> 'clemente-mastella'. La stessa riduzione la fa
    la scrivania quando legge l'indirizzo: devono coincidere."""
    t = unicodedata.normalize('NFD', str(testo).lower())
    t = ''.join(c for c in t if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]+', '-', t).strip('-')


def assegna_schegge(persone):
    """Il pezzo d'indirizzo di ogni scheda: il nome, e l'anno di nascita solo
    per gli omonimi. Se anche l'anno coincide, il codice della scheda."""
    gruppi = {}
    for p in persone:
        nome = re.sub(r'\s*\([^)]*\)', '', p['n'])
        gruppi.setdefault(scheggia(nome) or p['q'].lower(), []).append(p)
    for base, gente in gruppi.items():
        if len(gente) == 1:
            gente[0]['u'] = base
            continue
        anni = {}
        for p in gente:
            anni.setdefault((p.get('b') or '')[:4], []).append(p)
        for a, stessi in anni.items():
            for p in stessi:
                if a and len(stessi) == 1:
                    p['u'] = '%s-%s' % (base, a)
                else:
                    p['u'] = '%s-%s' % (base, p['q'].lower())


def migliaia(n):
    return format(n, ',').replace(',', '.')


def elenco_parole(cose):
    cose = list(cose)
    if len(cose) <= 1:
        return ''.join(cose)
    return ', '.join(cose[:-1]) + ' e ' + cose[-1]


# ------------------------------------------------------------ le schede

def titolo_scheda(p):
    """Neutro, e uguale a titoloScheda() nella scrivania."""
    a = (p.get('b') or '')[:4]
    return p['n'] + (' (%s)' % a if a else '')


def descrizione_scheda(p, partiti):
    """Una riga di fatti, senza aggettivi: anni, dove ha seduto, quante volte
    ha cambiato casacca, in quali governi. Niente maschili e femminili: si
    scrive 'alla Camera', non 'deputato'."""
    nascita = (p.get('b') or '')[:4]
    morte = (p.get('d') or '')[:4]
    if p['s'] == 2:
        anagrafe = '%s (%s–%s).' % (p['n'], nascita or '?', morte or '?')
    else:
        anagrafe = '%s%s.' % (p['n'], ' (%s)' % nascita if nascita else '')

    rami = {x[4] for x in p.get('g') or []}
    dove = ('alla Camera e al Senato' if rami >= {'C', 'S'}
            else 'al Senato' if 'S' in rami else 'alla Camera')
    leg = p.get('m') or []
    if p.get('x') or not leg:
        seggio = 'Mai in Parlamento fra il 1994 e il 2013.'
    elif len(leg) == 1:
        seggio = 'Ha seduto %s nella %s legislatura.' % (dove, leg[0])
    else:
        seggio = 'Ha seduto %s in %d legislature, dalla %s alla %s.' % (
            dove, len(leg), leg[0], leg[-1])
    if p.get('v'):
        seggio += ' Seggio a vita in Senato.'

    frasi = [anagrafe + ' ' + seggio]
    if p.get('g'):
        c = p.get('c', 0)
        frasi.append('Nessun cambio di casacca.' if c == 0
                     else 'Un cambio di casacca.' if c == 1
                     else '%d cambi di casacca.' % c)
    gv = p.get('gv') or []
    if gv:
        frasi.append(('Nel governo %s.' if len(gv) == 1 else 'Nei governi %s.')
                     % elenco_parole(gv))
    visti = []
    for x in p.get('g') or []:
        if x[1] not in ('?', 'MISTO') and x[1] not in visti:
            visti.append(x[1])
    if visti:
        nomi = [partiti.get(c, {}).get('nome', c) for c in visti]
        if len(nomi) > 4:
            nomi = nomi[:4] + ['altri']
        frasi.append(('Gruppo: %s.' if len(nomi) == 1 else 'Gruppi: %s.')
                     % elenco_parole(nomi))

    # Google taglia attorno ai 160 caratteri: si aggiungono frasi intere
    # finche' ci stanno, e la prima c'e' sempre.
    testo = frasi[0]
    for f in frasi[1:]:
        if len(testo) + 1 + len(f) > 165:
            break
        testo += ' ' + f
    return testo


# ------------------------------------------------------------ le pagine

def pagine(dati):
    """Tutte le pagine da scrivere: (indirizzo, chiave della finestra, titolo
    senza il nome del sito, descrizione, persona o None)."""
    P = dati['persone']
    partiti = dati['partiti']
    N = migliaia(len(P))
    con_gruppo = [p for p in P if p.get('g')]
    cambiati = sum(1 for p in con_gruppo if p['c'] > 0)
    almeno5 = sum(1 for p in con_gruppo if p['c'] >= 5)
    nel_misto = sum(1 for p in P if any(x[1] == 'MISTO' for x in p.get('g') or []))
    cond = (dati.get('condanne') or {}).get('voci', [])
    el = dati.get('elezioni') or {}
    mesi = (dati.get('spread') or {}).get('mesi') or []
    out = []

    def fissa(chiave, indirizzo, titolo, descrizione):
        out.append((indirizzo, chiave, titolo, descrizione, None))

    fissa('elenco', '/elenco/',
          'Tutti i parlamentari e i ministri della Seconda Repubblica',
          'L’elenco completo dei %s deputati, senatori e ministri dal 1994 al '
          '2013, per cognome, con legislature, partiti e cambi di casacca.' % N)
    fissa('classifiche', '/classifiche/',
          'Chi ha cambiato più volte casacca in Parlamento, 1994-2013',
          'La classifica dei cambi di casacca nella Seconda Repubblica: %d persone '
          'hanno cambiato partito almeno cinque volte, %s almeno una.'
          % (almeno5, migliaia(cambiati)))
    fissa('partiti', '/partiti/', 'I partiti della Seconda Repubblica in Parlamento',
          'I %d partiti passati per Camera e Senato dal 1994 al 2013, con quante '
          'persone ci sono passate e chi li ha guidati.' % len(partiti))
    fissa('albero', '/albero-dei-partiti/',
          'Albero dei partiti della Seconda Repubblica: chi discende da chi',
          'Scissioni, fusioni e confluenze dal 1994 al 2013, e perché passare a un '
          'partito erede non conta come cambio di casacca.')
    fissa('tempo', '/linea-del-tempo/', 'Linea del tempo dei partiti, 1994-2013',
          'Ogni partito dal primo all’ultimo giorno in cui qualcuno vi risulta '
          'iscritto in Parlamento, e quante persone ci sono passate.')
    fissa('misto', '/gruppo-misto/', 'Il gruppo misto nella Seconda Repubblica',
          'Ci sono passate %d persone fra il 1994 e il 2013: dopo i grandi partiti, '
          'la casacca più diffusa del periodo.' % nel_misto)
    fissa('famosi', '/hall-of-fame/',
          'Hall of fame: presidenti del Consiglio, delle Camere e ministri 1994-2013',
          'Chi fra il 1994 e il 2013 ha guidato un governo, presieduto una Camera o '
          'avuto un ministero, e quanti sono ancora vivi.')
    fissa('poltrone', '/le-poltrone/',
          'Le poltrone: chi ha avuto più incarichi fra Parlamento e governo',
          'Seggi in Parlamento e posti al governo, sommati: la classifica dei '
          'deputati, senatori e ministri della Seconda Repubblica.')
    fissa('responsabili', '/i-responsabili/',
          'I Responsabili: i gruppi nati dopo la sfiducia del dicembre 2010',
          'Iniziativa Responsabile e Popolo e Territorio: chi c’era, da quale gruppo '
          'arrivava e quando, nei mesi dopo il voto di sfiducia al governo Berlusconi IV.')
    fissa('governi', '/governi/', 'Gli undici governi della Seconda Repubblica',
          'Da Berlusconi I a Monti, dal maggio 1994 all’aprile 2013: i ministri di '
          'ogni governo, compresi quelli mai entrati in Parlamento.')
    fissa('cadute', '/le-cadute/', 'Le cadute dei governi della Seconda Repubblica',
          'I governi finiti prima del tempo per un voto perso o un appoggio '
          'ritirato: come, quando, con quali numeri, e chi ha cambiato gruppo attorno.')
    fissa('cavaliere', '/il-cavaliere/',
          'Il Cavaliere: Silvio Berlusconi in Parlamento e al governo, 1994-2013',
          'Silvio Berlusconi nei dati di Camera e Senato: i suoi governi, i suoi '
          'partiti e chi ci è passato.')
    fissa('mubarak', '/la-nipote-di-mubarak/',
          'La nipote di Mubarak: il voto sul caso Ruby, nome per nome',
          'Il 5 aprile 2011 la Camera e il 14 settembre 2011 il Senato votano il '
          'conflitto di attribuzione sul caso Ruby. Al Senato, chi ha votato che cosa.')
    fissa('donne', '/le-donne/', 'Le donne in Parlamento, 1994-2013',
          'Quante sono le donne fra deputati, senatori e ministri della Seconda '
          'Repubblica, secondo i registri di Camera e Senato.')
    fissa('estero', '/fuori-dall-italia/',
          'Fuori dall’Italia: la circoscrizione Estero e i fatti internazionali',
          'I parlamentari eletti all’estero dal 2006, e i fatti fuori dai confini '
          'che hanno coinvolto i governi dal 1994 al 2013.')
    fissa('elezioni', '/elezioni/', 'Elezioni politiche e referendum dal 1994 al 2013',
          'Le %d elezioni politiche e i %d referendum della Seconda Repubblica: date, '
          'affluenza, legge elettorale, governo nato dopo.'
          % (len(el.get('politiche', [])), len(el.get('referendum', []))))
    fissa('statistiche', '/statistiche/',
          'Statistiche sui parlamentari della Seconda Repubblica',
          'Età, longevità, cambi di casacca, chi è subentrato e chi è uscito prima: '
          'i numeri dei %s deputati, senatori e ministri dal 1994 al 2013.' % N)
    if cond:
        fissa('cestino', '/cestino/',
              'Condanne definitive fra i parlamentari della Seconda Repubblica',
              '%d persone su %s hanno una condanna penale passata in giudicato, per '
              'un totale di %d sentenze.' % (len({v['qid'] for v in cond}), N, len(cond)))
    if mesi:
        da, a = mesi[0]['m'][:4], mesi[-1]['m'][:4]
        fissa('spread', '/spread/', 'Lo spread fra BTP e Bund dal %s al %s' % (da, a),
              'Il differenziale fra titoli di Stato italiani e tedeschi a dieci anni, '
              'mese per mese dal %s al %s, sui dati della Banca centrale europea.' % (da, a))
    fissa('metodo', '/metodo/', 'Il metodo: come si contano i cambi di casacca',
          'Da quali fonti vengono i dati, come si incrociano e quale regola decide '
          'quando un cambio di gruppo è un cambio di casacca.')
    fissa('leggimi', '/colofone/', 'Colofone: chi fa Seconda Repubblica Tracker',
          'Chi ha fatto il sito, da quali fonti vengono i dati, come segnalare un errore.')
    fissa('trova', '/trova/', 'Trova un parlamentare della Seconda Repubblica',
          'Cerca per nome fra i %s deputati, senatori e ministri.' % N)
    fissa('aggiorna', '/aggiorna/', 'Aggiorna', 'Ricontrolla adesso le fonti.')
    fissa('confronta', '/confronta/', 'Confronta due percorsi',
          'Due percorsi parlamentari affiancati.')
    fissa('esegui', '/esegui/', 'Esegui', 'Apre una scheda o un partito per nome.')
    fissa('errore', '/segnala-un-errore/', 'Segnala un errore',
          'Come segnalare un errore nei dati.')

    # i partiti
    for c, info in sorted(partiti.items()):
        gente = sum(1 for p in P if any(x[1] == c for x in p.get('g') or []))
        if not gente:
            continue
        nome = info.get('nome', c)
        fissa('partito/' + c, '/partito/%s/' % scheggia(c),
              '%s in Parlamento, 1994-2013' % nome,
              '%s: le %d persone passate per i suoi gruppi fra il 1994 e il 2013, da '
              'dove arrivavano, dove sono andate e chi lo ha guidato.' % (nome, gente))

    # gli elenchi che vale la pena trovare: i vivi, i morti, le legislature,
    # i governi. Gli altri filtri restano col cancelletto.
    vivi = sum(1 for p in P if p['s'] == 1)
    morti = sum(1 for p in P if p['s'] == 2)
    fissa('lista/stato:vivi', '/elenco/vivi/',
          'I parlamentari della Seconda Repubblica ancora vivi',
          'I %s deputati, senatori e ministri della Seconda Repubblica ancora in '
          'vita, su %s.' % (migliaia(vivi), N))
    fissa('lista/stato:morti', '/elenco/morti/',
          'I parlamentari della Seconda Repubblica che non ci sono più',
          'I %s deputati, senatori e ministri della Seconda Repubblica scomparsi, '
          'su %s.' % (migliaia(morti), N))
    for L in dati['legislature']:
        gente = sum(1 for p in P if L['n'] in p['m'])
        fissa('lista/mandato:' + L['n'], '/elenco/legislatura/%s/' % scheggia(L['n']),
              '%s legislatura (%s): deputati e senatori' % (L['n'], L['anni']),
              'Le %d persone che hanno seduto in Parlamento nella %s legislatura, '
              'dal %s al %s, con i gruppi e i cambi di casacca.'
              % (gente, L['n'], data_breve(L['da']), data_breve(L['a'])))
    governi = sorted({g for p in P for g in p.get('gv') or []})
    for g in governi:
        gente = sum(1 for p in P if g in (p.get('gv') or []))
        fissa('lista/governo:' + g, '/elenco/governo/%s/' % scheggia(g),
              'Governo %s: i ministri' % g,
              'Le %d persone che hanno fatto parte del governo %s, con il loro '
              'percorso in Parlamento.' % (gente, g))

    for p in P:
        out.append(('/onorevole/%s/' % p['u'], 'persona/' + p['q'],
                    titolo_scheda(p), descrizione_scheda(p, partiti), p))
    return out


MESI = ['gennaio', 'febbraio', 'marzo', 'aprile', 'maggio', 'giugno', 'luglio',
        'agosto', 'settembre', 'ottobre', 'novembre', 'dicembre']


def data_breve(s):
    s = s.replace('-', '')
    return '%d %s %s' % (int(s[6:8]), MESI[int(s[4:6]) - 1], s[:4])


# ------------------------------------------------------------ la testa

def testa_casa(dati, descrizione):
    """La testa della pagina principale: indirizzo ufficiale, anteprima e dati
    strutturati. Questi ultimi dicono a Google che e' un archivio, chi lo cura
    e da quali fonti viene, e lo rendono trovabile nella ricerca di dataset."""
    autore = {'@type': 'Person', '@id': INDIRIZZO + '/#autore',
              'name': 'Davide Caniatti'}
    grafo = {
        '@context': 'https://schema.org',
        '@graph': [
            {'@type': 'WebSite', '@id': INDIRIZZO + '/#sito', 'url': INDIRIZZO + '/',
             'name': SITO, 'inLanguage': 'it-IT', 'author': {'@id': autore['@id']}},
            autore,
            {'@type': 'Dataset',
             'name': 'Parlamentari e ministri della Seconda Repubblica: i cambi di '
                     'gruppo parlamentare',
             'description': ('I %s deputati, senatori e ministri della Seconda '
                             'Repubblica italiana, dalla XII alla XVI legislatura '
                             '(1994-2013), con la storia datata dei gruppi '
                             'parlamentari, i governi, le date di nascita e di morte. '
                             'Si aggiorna ogni notte incrociando gli open data della '
                             'Camera dei deputati e del Senato con Wikidata.'
                             % migliaia(len(dati['persone']))),
             'url': INDIRIZZO + '/',
             'creator': {'@id': autore['@id']},
             'inLanguage': 'it-IT',
             'temporalCoverage': '1994-04-15/2013-03-14',
             'spatialCoverage': {'@type': 'Place', 'name': 'Italia'},
             'dateModified': dati['generato'],
             'isBasedOn': ['https://dati.camera.it/', 'https://dati.senato.it/',
                           'https://www.wikidata.org/', 'https://it.wikipedia.org/'],
             'keywords': ['Seconda Repubblica', 'cambi di casacca', 'trasformismo',
                          'parlamentari', 'gruppi parlamentari', 'Camera dei deputati',
                          'Senato della Repubblica', 'storia politica italiana']},
        ],
    }
    return testa('/', SITO + ': chi ha cambiato casacca dal 1994 al 2013',
                 descrizione, grafo)


def grafo_scheda(p, url, titolo, dati):
    individuo = {'@type': 'Person', 'name': p['n']}
    if p['q'].startswith('Q'):
        individuo['sameAs'] = ['https://www.wikidata.org/wiki/' + p['q']]
    if p.get('b'):
        individuo['birthDate'] = p['b']
    if p.get('d'):
        individuo['deathDate'] = p['d']
    return {'@context': 'https://schema.org', '@type': 'ProfilePage',
            'url': url, 'name': titolo, 'inLanguage': 'it-IT',
            'dateModified': dati['generato'],
            'isPartOf': {'@id': INDIRIZZO + '/#sito'},
            'mainEntity': individuo}


def testa(indirizzo, titolo, descrizione, grafo=None, fuori=False, canonico=True):
    e = lambda s: html.escape(s, quote=True)
    url = INDIRIZZO + indirizzo
    righe = ['<meta name="description" content="%s">' % e(descrizione)]
    if fuori:
        righe.append('<meta name="robots" content="noindex">')
    if canonico:
        righe.append('<link rel="canonical" href="%s">' % e(url))
    righe += [
        '<meta property="og:type" content="website">',
        '<meta property="og:locale" content="it_IT">',
        '<meta property="og:site_name" content="%s">' % SITO,
        '<meta property="og:title" content="%s">' % e(titolo),
        '<meta property="og:description" content="%s">' % e(descrizione),
        '<meta property="og:url" content="%s">' % e(url),
        # Come voynichizer.com, dove WhatsApp l'anteprima la mostra: JPEG e non
        # PNG, tipo e indirizzo sicuro dichiarati, e un nome di file nuovo,
        # perche' WhatsApp si ricorda a lungo di un'immagine che non e' riuscito
        # a leggere, e sotto il nome vecchio non ci riproverebbe.
        '<meta property="og:image" content="%s/preview.jpg">' % INDIRIZZO,
        '<meta property="og:image:secure_url" content="%s/preview.jpg">' % INDIRIZZO,
        '<meta property="og:image:type" content="image/jpeg">',
        '<meta property="og:image:width" content="1200">',
        '<meta property="og:image:height" content="630">',
        '<meta property="og:image:alt" content="Una finestra di Windows 95: Seconda '
        'Repubblica Tracker, chi ha cambiato casacca in Parlamento dal 1994 al 2013">',
        '<meta name="twitter:card" content="summary_large_image">',
        '<meta name="twitter:image" content="%s/preview.jpg">' % INDIRIZZO,
    ]
    if grafo:
        righe.append('<script type="application/ld+json">%s</script>'
                     % json.dumps(grafo, ensure_ascii=False, separators=(',', ':'))
                     .replace('</', '<\\/'))
    return '\n'.join(righe)


def intestazione(testo):
    """Il titolo vero della pagina, per chi legge con lo schermo e per i
    motori. Graficamente c'e' gia': e' la barra della finestra."""
    return '<h1 class="solo-lettori">%s</h1>' % html.escape(testo)


# ------------------------------------------------------------ il montaggio

def scomponi(scheletro):
    """Separa dalla pagina gia' riempita il foglio di stile e il programma, che
    diventano due file comuni a tutte le pagine."""
    i = scheletro.index('<style>')
    j = scheletro.index('</style>', i) + len('</style>')
    stile = scheletro[i + len('<style>'):j - len('</style>')]
    a = scheletro.index('<script>\n/* L\'indirizzo del sito')
    b = scheletro.rindex('</script>')
    programma = scheletro[a + len('<script>'):b]
    involucro = (scheletro[:i] + '<!--%%STILE%%-->' + scheletro[j:a]
                 + '<!--%%PROGRAMMA%%-->' + scheletro[b + len('</script>'):])
    return involucro, stile.strip('\n') + '\n', programma.strip('\n') + '\n'


def costruisci(scheletro, dati, descrizione_casa, versione, cartella_sito, uscita):
    """scheletro: la pagina con dati, colofone e versione gia' al loro posto, e
    ancora da riempire titolo, testa e intestazione.
    Scrive la cartella da pubblicare e restituisce (file, pagine in mappa)."""
    involucro, stile, programma = scomponi(scheletro)
    elenco_pagine = pagine(dati)

    # Al programma la tabella degli indirizzi arriva coi dati. I titoli delle
    # schede la scrivania li compone da sola (titoloScheda): portarseli dietro
    # tutti peserebbe quanto mezzo elenco.
    titolo_casa = SITO + ': chi ha cambiato casacca dal 1994 al 2013'
    percorsi = {'/': 'indice'}
    titoli = {'/': titolo_casa}
    for indirizzo, chiave, titolo, descrizione, persona in elenco_pagine:
        if not persona:
            percorsi[indirizzo] = chiave
            titoli[indirizzo] = '%s | %s' % (titolo, SITO)
    segnaposto = '"__INDIRIZZI__":null'
    if segnaposto not in programma:
        raise SystemExit('Nel programma manca il posto per la tabella degli indirizzi.')
    programma = programma.replace(
        segnaposto, '"indirizzi":' + json.dumps(
            {'percorsi': percorsi, 'titoli': titoli},
            ensure_ascii=False, separators=(',', ':')), 1)

    # Il richiamo ai due file comuni cambia quando cambia il loro contenuto:
    # anche una correzione fatta in giornata arriva subito a chi ha gia' in
    # memoria la copia vecchia.
    impronta = lambda s: hashlib.sha1(s.encode('utf-8')).hexdigest()[:10]
    involucro = (involucro
                 .replace('<!--%%STILE%%-->',
                          '<link rel="stylesheet" href="/stile.css?v=%s">' % impronta(stile))
                 .replace('<!--%%PROGRAMMA%%-->',
                          '<script>var RADICE = "/";</script>\n'
                          '<script src="/programma.js?v=%s"></script>' % impronta(programma)))
    e = lambda s: html.escape(s, quote=True)

    def monta(titolo_pieno, testa_html, h1):
        return (involucro
                .replace('%%TITOLO%%', e(titolo_pieno))
                .replace('<!--%%TESTA%%-->', testa_html + '\n' + ICONE)
                .replace('<!--%%INTESTAZIONE%%-->', intestazione(h1)))

    if os.path.isdir(uscita):
        shutil.rmtree(uscita)
    os.makedirs(uscita)

    def scrivi(nome, testo):
        percorso = os.path.join(uscita, *nome.split('/'))
        os.makedirs(os.path.dirname(percorso), exist_ok=True)
        with open(percorso, 'w', encoding='utf-8', newline='\n') as f:
            f.write(testo)

    scrivi('index.html', monta(titolo_casa, testa_casa(dati, descrizione_casa),
                               titolo_casa))
    mappa = ['/']
    for indirizzo, chiave, titolo, descrizione, persona in elenco_pagine:
        pieno = '%s | %s' % (titolo, SITO)
        fuori = chiave in FUORI_DAI_MOTORI
        grafo = grafo_scheda(persona, INDIRIZZO + indirizzo, pieno, dati) if persona else None
        scrivi(indirizzo.strip('/') + '/index.html',
               monta(pieno, testa(indirizzo, pieno, descrizione, grafo, fuori), titolo))
        if not fuori:
            mappa.append(indirizzo)

    # Per un indirizzo che non esiste GitHub Pages serve 404.html: e' la
    # scrivania stessa, che legge l'indirizzo e, se non lo riconosce, apre la
    # finestra principale.
    scrivi('404.html', monta(SITO, testa('/', SITO, descrizione_casa, fuori=True,
                                         canonico=False), SITO))

    scrivi('stile.css', stile)
    scrivi('programma.js', programma)
    scrivi('versione.txt', versione)

    # La mappa del sito. La data c'e' solo sull'indice, l'unica pagina che
    # cambia davvero ogni giorno: una data uguale su tremila pagine Google
    # impara presto a non crederci.
    voci = ['  <url><loc>%s%s</loc>%s</url>' % (
        INDIRIZZO, html.escape(x),
        '<lastmod>%s</lastmod>' % dati['generato'] if x == '/' else '') for x in mappa]
    scrivi('sitemap.xml', '<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           + '\n'.join(voci) + '\n</urlset>\n')
    scrivi('robots.txt', 'User-agent: *\nAllow: /\n\nSitemap: %s/sitemap.xml\n' % INDIRIZZO)

    # Quello che sta solo nella cartella del sito: l'icona e l'immagine per le
    # anteprime quando il link gira.
    for nome in ('favicon.png', 'anteprima.png', 'preview.jpg') + FILE_ICONE:
        sorgente = os.path.join(cartella_sito, nome)
        if os.path.exists(sorgente):
            shutil.copyfile(sorgente, os.path.join(uscita, nome))

    file = sum(len(f) for _, _, f in os.walk(uscita))
    return file, len(mappa)
