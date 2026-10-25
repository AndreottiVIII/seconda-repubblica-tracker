# -*- coding: utf-8 -*-
"""Il testo vero di ogni pagina pubblicata, per chi non esegue il programma.

La scrivania e le sue finestre le disegna il programma (programma.js). Chi non
lo esegue - spesso Google, sempre i lettori di testo semplice - fino al 25
ottobre 2026 trovava in ogni scheda un titolo e la finta schermata d'errore, e
basta: 2.800 pagine quasi uguali e quasi vuote, e Google le ha tolte dai
risultati. Qui ogni pagina riceve il suo contenuto scritto, con i collegamenti
veri fra schede, partiti, legislature e governi. Quando il programma parte, lo
nasconde e mostra la finestra, che dice le stesse cose.

Usato da pagine_statiche.py.
"""
import html
import re

e = lambda s: html.escape(str(s if s is not None else ''), quote=True)
MESI = ['gennaio', 'febbraio', 'marzo', 'aprile', 'maggio', 'giugno', 'luglio',
        'agosto', 'settembre', 'ottobre', 'novembre', 'dicembre']
RAMO = {'C': 'Camera', 'S': 'Senato'}


def data(s):
    s = (s or '').replace('-', '')
    if len(s) >= 8:
        return '%d %s %s' % (int(s[6:8]), MESI[int(s[4:6]) - 1], s[:4])
    return s[:4]


def num(n):
    return '{:,}'.format(int(n or 0)).replace(',', '.')


def pc(a, b):
    return ('%.1f' % (100.0 * a / b)).replace('.', ',') + '%' if b else ''


def link_persona(p):
    return '<a href="/onorevole/%s/">%s</a>' % (e(p['u']), e(p['n']))


def nome_partito(c, dati):
    return (dati['partiti'].get(c) or {}).get('nome', c)


def scheggia(t):
    import unicodedata
    t = unicodedata.normalize('NFD', str(t).lower())
    t = ''.join(c for c in t if not unicodedata.combining(c))
    return re.sub(r'[^a-z0-9]+', '-', t).strip('-')


def indice():
    """I collegamenti alle sezioni principali, in fondo a ogni pagina."""
    voci = [('/', 'Seconda Repubblica Tracker'), ('/elenco/', 'Tutti i parlamentari'),
            ('/partiti/', 'I partiti'), ('/classifiche/', 'Classifiche'), ('/governi/', 'I governi'),
            ('/la-prima-fiducia/', 'Le fiducie'), ('/i-voti-alla-camera/', 'I voti alla Camera'),
            ('/i-voti-al-senato/', 'I voti al Senato'), ('/le-leggi-che-hanno-diviso/', 'Le leggi che hanno diviso'),
            ('/i-collegi/', 'I collegi'), ('/l-emiciclo/', 'L’emiciclo'), ('/elezioni/', 'Le elezioni'),
            ('/il-cavaliere/', 'Il Cavaliere'), ('/metodo/', 'Il metodo'), ('/colofone/', 'Colofone')]
    return '<nav><p>' + ' · '.join('<a href="%s">%s</a>' % (u, e(t)) for u, t in voci) + '</p></nav>'


def scheda(p, dati):
    """Il contenuto della scheda di una persona, come testo."""
    ordine = [L['n'] for L in dati['legislature']]
    h = []
    nato = 'Nata' if p.get('ge') == 'F' else 'Nato'
    lu = p.get('lu') or {}
    riga = []
    if p.get('b'):
        riga.append('%s il %s%s' % (nato, data(p['b']), ', a ' + e(lu['nascita']) if lu.get('nascita') else ''))
    if p.get('s') == 2:
        riga.append(('morta' if p.get('ge') == 'F' else 'morto') + (' il ' + data(p['d']) if p.get('d') else '') +
                    (', a ' + e(lu['morte']) if lu.get('morte') else ''))
    if riga:
        h.append('<p>%s.</p>' % '; '.join(riga))
    legs = [m for m in (p.get('m') or []) if m in ordine]
    if legs:
        link = ['<a href="/elenco/legislatura/%s/">%s</a>' % (scheggia(m), m) for m in legs]
        quali = ('nella %s legislatura' % link[0]) if len(link) == 1 else (
            'nelle legislature %s e %s' % (', '.join(link[:-1]), link[-1]))
        h.append('<p>In Parlamento %s. Cambi di casacca: %d.</p>' % (quali, p.get('c', 0)))
    if p.get('st'):
        h.append('<p>Studi e professione: %s.</p>' % e(p['st']))
    if p.get('k'):
        h.append('<p>Cariche: %s.</p>' % e(', '.join(p['k'])))
    # i gruppi, in ordine
    passi = p.get('g') or []
    if passi:
        righe = []
        for t in passi:
            leg = ordine[t[0]] if isinstance(t[0], int) and t[0] < len(ordine) else ''
            c = t[1]
            nome = nome_partito(c, dati)
            part = ('<a href="/partito/%s/">%s</a>' % (scheggia(c), e(nome))) if c in dati['partiti'] else e(nome)
            righe.append('<li>%s, %s: %s%s, dal %s%s</li>' % (
                leg, RAMO.get(t[4], ''), part, (' (gruppo ' + e(t[5]) + ')') if len(t) > 5 and t[5] else '',
                data(t[2]), (' al ' + data(t[3])) if t[3] else ''))
        h.append('<h2>Gruppi parlamentari</h2><ul>%s</ul>' % ''.join(righe))
    if p.get('go'):
        h.append('<h2>Al governo</h2><ul>%s</ul>' % ''.join(
            '<li>%s: %s, dal %s%s</li>' % (e(g[0]), e(g[1]), data(g[2]), (' al ' + data(g[3])) if g[3] else '')
            for g in p['go']))
    if p.get('el'):
        h.append('<h2>Elezione alla Camera</h2><ul>%s</ul>' % ''.join(
            '<li>%s legislatura: %s%s</li>' % (m, e(v[1]), (', lista ' + e(v[2])) if v[2] else '')
            for m, v in sorted(p['el'].items(), key=lambda x: ordine.index(x[0]) if x[0] in ordine else 99)))
    if p.get('cu'):
        h.append('<h2>Nei collegi uninominali</h2><ul>%s</ul>' % ''.join(
            '<li>%s, %s, collegio di %s: %s voti (%s), %d° su %d</li>' % (
                c[0], RAMO.get(c[1], ''), e(c[2]), num(c[3]), ('%.1f' % c[4]).replace('.', ',') + '%', c[5], c[6])
            for c in p['cu']))
    voti = []
    for m, v in sorted((p.get('vc') or {}).items(), key=lambda x: ordine.index(x[0]) if x[0] in ordine else 99):
        if v[0] >= 20:
            voti.append('<li>Camera, %s legislatura: ha votato %s volte su %s (%s); diverso dal gruppo %s volte su %s</li>'
                        % (m, num(v[1]), num(v[0]), pc(v[1], v[0]), num(v[5]), num(v[4])))
    for m, v in sorted((p.get('vt') or {}).items(), key=lambda x: ordine.index(x[0]) if x[0] in ordine else 99):
        if v[0] >= 20:
            voti.append('<li>Senato, %s legislatura: ha votato %s volte su %s (%s); diverso dal gruppo %s volte su %s</li>'
                        % (m, num(v[1]), num(v[0]), pc(v[1], v[0]), num(v[5]), num(v[4])))
    if voti:
        h.append('<h2>Votazioni</h2><ul>%s</ul>' % ''.join(voti))
    interventi = []
    for m, v in (p.get('ic') or {}).items():
        interventi.append('<li>Camera, %s legislatura: %s interventi (%s)</li>' % (m, num(v[0]), e(v[1])))
    for m, v in (p.get('at') or {}).items():
        interventi.append('<li>Senato, %s legislatura: %s interventi in Aula e %s in commissione sulle leggi; '
                          '%s interrogazioni, %s interpellanze, %s mozioni firmate</li>'
                          % (m, num(v[0]), num(v[1]), num(v[2] + v[3]), num(v[4]), num(v[5])))
    if interventi:
        h.append('<h2>Interventi e interrogazioni</h2><ul>%s</ul>' % ''.join(interventi))
    pr = p.get('pr') or {}
    if pr:
        frasi = ['%s: %s come primo firmatario, %s cofirmate' % (RAMO[k] if k in RAMO else k, num(v[0]), num(v[1]))
                 for k, v in sorted(pr.items())]
        approvate = [x for x in (p.get('pl') or []) + (p.get('ps') or []) if x[3] != 'assorbita']
        h.append('<h2>Proposte di legge</h2><p>%s.%s</p>' % ('; '.join(frasi), (
            ' Approvate: %d.' % len(approvate)) if approvate else ''))
        if approvate:
            h.append('<ul>%s</ul>' % ''.join('<li>%s, n. %s: %s</li>' % (x[0], e(x[1]), e(x[2])) for x in approvate[:30]))
    if p.get('au'):
        h.append('<p>Richieste dei giudici alla Camera: %d.</p>' % len(p['au']))
    per_q = dati.get('_per_q') or {}
    if p.get('pa'):
        h.append('<p>Parenti in Parlamento: %s.</p>' % ', '.join(
            link_persona(per_q[x[1]]) for x in p['pa'] if x[1] in per_q))
    if p.get('w'):
        h.append('<p><a href="https://it.wikipedia.org/wiki/%s">Voce su Wikipedia</a></p>' % e(p['w']))
    h.append('<p>Fonti: Camera dei deputati, Senato della Repubblica, Wikidata. Dettagli nel '
             '<a href="/metodo/">metodo</a>.</p>')
    return ''.join(h)


def elenco(gente):
    """Un elenco di persone con il collegamento alla scheda."""
    gente = sorted(gente, key=lambda p: (p['n'].split()[-1].lower(), p['n'].lower()))
    return '<ul>%s</ul>' % ''.join('<li>%s</li>' % link_persona(p) for p in gente)


def corpo(chiave, descrizione, persona, dati):
    """Il testo di una pagina, dato quello che la pagina mostra."""
    P = dati['persone']
    h = ['<p>%s</p>' % e(descrizione)] if descrizione else []
    if persona:
        h.append(scheda(persona, dati))
    elif chiave.startswith('partito/'):
        c = chiave.split('/', 1)[1]
        h.append(elenco([p for p in P if any(x[1] == c for x in p.get('g') or [])]))
    elif chiave.startswith('lista/mandato:'):
        m = chiave.split(':', 1)[1]
        h.append(elenco([p for p in P if m in (p.get('m') or [])]))
    elif chiave.startswith('lista/governo:'):
        g = chiave.split(':', 1)[1]
        h.append(elenco([p for p in P if g in (p.get('gv') or [])]))
    elif chiave.startswith('lista/cerca:'):
        nome = chiave.split(':', 1)[1]
        h.append(elenco([p for p in P if re.sub(r'\s*\([^)]*\)', '', p['n']) == nome]))
    elif chiave == 'partiti':
        h.append('<ul>%s</ul>' % ''.join('<li><a href="/partito/%s/">%s</a></li>' % (scheggia(c), e(v.get('nome', c)))
                                         for c, v in sorted(dati['partiti'].items(), key=lambda x: x[1].get('nome', x[0]))))
    elif chiave in ('elenco', 'indice'):
        h.append('<ul>%s</ul>' % ''.join('<li><a href="/elenco/legislatura/%s/">%s legislatura (%s)</a></li>' % (
            scheggia(L['n']), L['n'], L['anni']) for L in dati['legislature']))
    h.append(indice())
    return ''.join(h)
