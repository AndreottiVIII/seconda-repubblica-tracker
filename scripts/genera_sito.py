# -*- coding: utf-8 -*-
"""Compatta i dati e li inietta dentro il modello: esce un file HTML solo.

Un file solo, coi dati dentro: si apre col doppio clic dal disco, si mette su
qualunque hosting statico, non serve ne' un server ne' un database. Le chiavi
sono di una o due lettere perche' il file finito viaggia intero nel browser.
"""
import sys, os, json, datetime, re, hashlib, unicodedata
from html import unescape as html_unescape

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

QUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, QUI)
import casacche, controlla_js, pagine_statiche

INGRESSO = os.path.join(QUI, '..', 'data', 'elenco.json')
MODELLO = os.path.join(QUI, 'modello.html')
DISTINTIVI = os.path.join(QUI, '..', 'data', 'distintivi.json')
SPREAD = os.path.join(QUI, '..', 'data', 'spread.json')
CONDANNE = os.path.join(QUI, '..', 'data', 'condanne.json')
VOTO_RUBY = os.path.join(QUI, '..', 'data', 'voto_ruby.json')
ESTERO = os.path.join(QUI, '..', 'data', 'estero.json')
ELEZIONI = os.path.join(QUI, '..', 'data', 'elezioni.json')
SEGRETARI = os.path.join(QUI, '..', 'data', 'segretari.json')
USCITA = os.path.join(QUI, '..', 'sito')
# Il sito come lo pubblica il lavoro notturno: una pagina per finestra,
# perche' Google lo trovi. Si rifa' da zero a ogni giro e non si versiona.
PUBBLICA = os.path.join(QUI, '..', 'pubblica')

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
    'Il codice del sito è mio, con tutti i diritti riservati: non si copia '
    'né si riusa senza permesso. I contenuti scritti a mano - '
    'le condanne, i distintivi, i fatti fuori dai confini, le elezioni, i '
    'segretari di partito, la mappa dei gruppi - si possono riusare citando '
    'la fonte: Seconda Repubblica Tracker, Davide Caniatti. I dati '
    'parlamentari non sono miei e restano di Camera, Senato e Wikidata, con '
    'le licenze loro. Le fotografie hanno ognuna la sua, su Wikimedia '
    'Commons. Tutto scritto per esteso nel file LICENSE del progetto.',
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


def chiave_nome(nome):
    """Il nome ridotto all'osso, per riconoscere la stessa persona scritta in
    due modi. Via gli accenti, via gli apostrofi, e le parole in ordine
    alfabetico: cosi' 'D'Alema Massimo' e 'Massimo D'Alema' cadono insieme."""
    n = unicodedata.normalize('NFD', (nome or '').lower())
    n = ''.join(c for c in n if not unicodedata.combining(c))
    return ' '.join(sorted(n.replace("'", ' ').split()))


GOVERNI_INIZIO = [('19940510', 'Berlusconi I'), ('19950117', 'Dini'), ('19960517', 'Prodi I'),
                  ('19981021', "D'Alema I"), ('19991222', "D'Alema II"), ('20000425', 'Amato II'),
                  ('20010611', 'Berlusconi II'), ('20050423', 'Berlusconi III'),
                  ('20060517', 'Prodi II'), ('20080508', 'Berlusconi IV'), ('20111116', 'Monti')]


def governo_al(giorno):
    """Il governo in carica quel giorno (o appena nominato: la fiducia arriva
    qualche giorno dopo il giuramento)."""
    nome = GOVERNI_INIZIO[0][1]
    for inizio, chi in GOVERNI_INIZIO:
        if inizio <= giorno:
            nome = chi
    return nome


# I gruppi della Camera con le date di vita (data/gruppi_camera.json, dall'archivio
# gruppoParlamentare): servono a dire nella scheda quando un gruppo si e' sciolto.
_FINE_LEG = {'12': '19960508', '13': '20010529', '14': '20060427', '15': '20080428',
             '16': '20130314'}
_G = os.path.join(QUI, '..', 'data', 'gruppi_camera.json')
SCIOLTI = {}
if os.path.exists(_G):
    SCIOLTI = {gid: v for gid, v in json.load(open(_G, encoding='utf-8'))['gruppi'].items()
               if v[4] and v[4] < _FINE_LEG.get(v[0], '0')}


def nome_gruppo(nome, sigla):
    """'RINNOVAMENTO ITALIANO' -> 'Rinnovamento Italiano'; la sigla resta com'e'."""
    piccole = {'di', 'del', 'della', 'per', 'la', 'e', "l'", 'il'}
    parole = nome.lower().split()
    return ' '.join(w.upper() if w.upper() == (sigla or '').upper() else
                    (w if i and w in piccole else w[:1].upper() + w[1:])
                    for i, w in enumerate(parole))


def note_gruppi(p):
    """[[legislatura, testo]]: quando il gruppo di qualcuno si e' sciolto, e le
    note delle correzioni fatte a mano."""
    fuori = []
    for leg, gl in (p.get('gruppi_per_mandato') or {}).items():
        for g in gl:
            if g.get('nota'):
                fuori.append([leg, g['nota']])
            v = SCIOLTI.get((g.get('uri') or '').rsplit('/', 1)[-1])
            if v and g.get('a') == v[4]:
                d = v[4]
                articolo = "l'" if int(d[6:8]) in (8, 11) else 'il '
                fuori.append([leg, 'Il gruppo %s si scioglie %s%s.' % (
                    nome_gruppo(v[2], v[1]), articolo, data_estesa(d))])
    return fuori


MESI_IT = ['gennaio', 'febbraio', 'marzo', 'aprile', 'maggio', 'giugno', 'luglio',
           'agosto', 'settembre', 'ottobre', 'novembre', 'dicembre']


def data_estesa(d):
    return '%d %s %s' % (int(d[6:8]), MESI_IT[int(d[4:6]) - 1], d[:4])


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
    if p.get('foto_senato'):
        # Il Senato ha la foto ufficiale di tutti i suoi senatori, nessuno
        # escluso: chiude i buchi che Wikidata e la Camera lasciano aperti.
        d['fs'] = p['foto_senato']
    if p.get('wikipedia'):
        d['w'] = wiki_breve(p['wikipedia'])
    if p.get('non_eletto'):
        d['x'] = 1
    if p.get('senatore_a_vita'):
        d['v'] = 1
    if p.get('genere'):
        d['ge'] = p['genere']
    # Solo le quattro circoscrizioni fuori dai confini: le altre sono venti
    # regioni che nel sito non servono a niente, e peserebbero.
    estere = {m: c for m, c in (p.get('circoscrizioni') or {}).items()
              if any(x in c.upper() for x in
                     ('EUROPA', 'AMERICA', 'AFRICA', 'ASIA', 'OCEANIA'))}
    if estere:
        d['es'] = estere
    if p.get('incarichi'):
        d['in'] = {m: [[x['r'], x['o']] for x in v]
                   for m, v in p['incarichi'].items()}
    if p.get('mandato'):
        # 'md' e' gia' della morte dubbia: qui ci vuole un nome suo.
        d['mn'] = p['mandato']
    if p.get('solo_registro'):
        d['r'] = 1
    if p.get('morte_dubbia'):
        d['md'] = p['morte_dubbia']
    if p.get('id_camera'):
        d['ci'] = p['id_camera']
    if note_gruppi(p):
        d['gs'] = note_gruppi(p)
    return d


def main():
    grezzo = json.load(open(INGRESSO, encoding='utf-8'))
    M = casacche.leggi_mappa()
    gruppi, partiti = M['gruppi'], M['partiti']
    ant = casacche.antenati(partiti)

    persone = [compatta(p, gruppi, ant) for p in grezzo['persone']]
    persone.sort(key=lambda x: x['n'])
    # Il pezzo d'indirizzo di ogni scheda, /onorevole/clemente-mastella/.
    pagine_statiche.assegna_schegge(persone)
    # I mandati di pochi giorni, senza adesione a un gruppo: eletti che si
    # dimettono all'inizio della legislatura, o che muoiono subito. Contano come
    # gli altri; la scheda aggiunge una nota. Vengono
    # dall'anagrafe della Camera, tramite scripts/controlla_camera.py.
    brevi_file = os.path.join(QUI, '..', 'data', 'mandati_brevi.json')
    if os.path.exists(brevi_file):
        brevi = json.load(open(brevi_file, encoding='utf-8')).get('mandati', {})
        for p in persone:
            if p['q'] in brevi:
                p['mb'] = brevi[p['q']]
        print('mandati brevi: %d persone' % sum(1 for p in persone if p.get('mb')))

    # Le schede piu' ricche: studi, governo, elezioni, ruoli nel gruppo, fine
    # del mandato, incarichi al Senato, proposte di legge. Le ricava
    # scripts/arricchisci.py dagli archivi scaricati sul PC; qui arriva il file
    # gia' fatto, perche' il lavoro notturno quegli archivi non li ha. I titoli
    # delle proposte restano fuori: peserebbero quanto mezzo sito, e la scheda
    # li carica a parte (pagine_statiche li scrive in pubblica/proposte/).
    arr_file = os.path.join(QUI, '..', 'data', 'arricchimenti.json')
    if os.path.exists(arr_file):
        arr = json.load(open(arr_file, encoding='utf-8')).get('schede', {})
        for p in persone:
            x = arr.get(p['q'])
            if not x:
                continue
            if x.get('studi'):
                p['st'] = x['studi']
            if x.get('governo'):
                p['go'] = [[g['governo'], g['carica'], g['da'], g['a']] for g in x['governo']]
            if x.get('elezioni'):
                p['el'] = x['elezioni']
            if x.get('ruoli_gruppo'):
                p['rg'] = x['ruoli_gruppo']
            if x.get('fine_mandato'):
                p['fm'] = x['fine_mandato']
            if x.get('ispettivi'):
                p['ai'] = x['ispettivi']
            for leg, voci in (x.get('incarichi_senato') or {}).items():
                lista = p.setdefault('in', {}).setdefault(leg, [])
                for r, o in voci:
                    lista.append([r, o, 'S'])
            if x.get('proposte'):
                p['pr'] = {ramo: [v.get('primo', 0), v.get('cofirmate', 0), v.get('governo', 0)]
                           for ramo, v in x['proposte'].items()}
        print('schede arricchite: %d' % sum(1 for p in persone if p['q'] in arr))

    # Da Wikidata (scripts/wikidata_extra.py): luoghi di nascita, morte e
    # sepoltura, parenti che stanno anche loro nell'elenco, voce della Treccani.
    # Le parentele si scrivono dal punto di vista di ciascuno, e si completano
    # al contrario: Wikidata a volte ne registra un lato solo.
    wx_file = os.path.join(QUI, '..', 'data', 'wikidata_extra.json')
    if os.path.exists(wx_file):
        wx = json.load(open(wx_file, encoding='utf-8'))
        dal_lato = {'padre': 'figlio_di', 'madre': 'figlio_di', 'figlio': 'genitore_di',
                    'coniuge': 'coniuge', 'fratello': 'fratello', 'parente': 'parente'}
        inverso = {'figlio_di': 'genitore_di', 'genitore_di': 'figlio_di', 'coniuge': 'coniuge',
                   'fratello': 'fratello', 'parente': 'parente'}
        legami = {}
        for a, voci in wx.get('parenti', {}).items():
            for rel, b in voci:
                r = dal_lato[rel]
                for x, y, z in ((a, b, r), (b, a, inverso[r])):
                    if [z, y] not in legami.setdefault(x, []):
                        legami[x].append([z, y])
        per_q = {p['q']: p for p in persone}
        for q, luoghi in wx.get('luoghi', {}).items():
            if q in per_q:
                per_q[q]['lu'] = luoghi
        for q, v in legami.items():
            if q in per_q:
                per_q[q]['pa'] = v
        for q, voce in wx.get('treccani', {}).items():
            if q in per_q:
                per_q[q]['tr'] = voce
    # La lista P2 (scripts/lista_p2.py): il numero del fascicolo.
    p2_file = os.path.join(QUI, '..', 'data', 'lista_p2.json')
    if os.path.exists(p2_file):
        per_q = {p['q']: p for p in persone}
        for x in json.load(open(p2_file, encoding='utf-8')):
            if x['qid'] in per_q:
                per_q[x['qid']]['p2'] = x.get('fascicolo') or ''
    # I collegi uninominali del 1994, 1996 e 2001 (scripts/collegi_eligendo.py):
    # [anno, ramo, collegio, voti, %, posto, candidati, distacco, simboli, recupero]
    cu_file = os.path.join(QUI, '..', 'data', 'collegi.json')
    if os.path.exists(cu_file):
        per_q = {p['q']: p for p in persone}
        for q, v in json.load(open(cu_file, encoding='utf-8'))['collegi'].items():
            if q in per_q:
                per_q[q]['cu'] = v
    # Il Senato dai file scaricati sul PC: i voti (scripts/voti_senato.py) e
    # interventi e interrogazioni (scripts/attivita_senato.py), per numero del senatore.
    elenco_x = json.load(open(os.path.join(QUI, '..', 'data', 'elenco.json'), encoding='utf-8'))['persone']
    senato_q = {x['id_senato'].rsplit('/', 1)[-1]: x['qid'] for x in elenco_x if x.get('id_senato')}
    # chi nell'elenco non ha il numero del Senato (i senatori a vita, soprattutto):
    # nome, cognome e data di nascita del Senato (scripts/senatori_anagrafe.py),
    # solo se tornano con una persona sola
    an_file = os.path.join(QUI, '..', 'data', 'senatori_anagrafe.json')
    if os.path.exists(an_file):
        semplice = lambda s: re.sub(r'[^a-z]', '', unicodedata.normalize('NFKD', s or '').encode(
            'ascii', 'ignore').decode().lower())
        per_nome = {}
        for x in elenco_x:
            if x.get('nascita'):
                per_nome.setdefault((semplice(x['nome']), x['nascita']), []).append(x['qid'])
        for s, (nome, cognome, nato) in json.load(open(an_file, encoding='utf-8')).items():
            q = per_nome.get((semplice(nome + cognome), nato), [])
            if s not in senato_q and len(q) == 1:
                senato_q[s] = q[0]
    per_q = {p['q']: p for p in persone}
    vt_file = os.path.join(QUI, '..', 'data', 'voti_senato.json')
    if os.path.exists(vt_file):
        for s, legs in json.load(open(vt_file, encoding='utf-8'))['senatori'].items():
            if senato_q.get(s) in per_q:
                # [votazioni, espressi, presente senza votare, assente, con una linea, diversi]
                per_q[senato_q[s]]['vt'] = {leg: [v.get(k, 0) for k in ('votazioni', 'espressi', 'presente',
                                                                        'assente', 'con_linea', 'dissenso')]
                                            for leg, v in legs.items()}
    at_file = os.path.join(QUI, '..', 'data', 'attivita_senato.json')
    if os.path.exists(at_file):
        for s, legs in json.load(open(at_file, encoding='utf-8'))['senatori'].items():
            if senato_q.get(s) in per_q:
                # [in Aula, in commissione, interrogazioni, a risposta scritta, interpellanze, mozioni]
                per_q[senato_q[s]]['at'] = {leg: [v.get(k, 0) for k in ('aula', 'commissione', 'interrogazioni',
                                                                        'scritte', 'interpellanze', 'mozioni')]
                                            for leg, v in legs.items()}
    # Com'e' andata alla Camera per le proposte (scripts/proposte_leggi.py), per
    # numero della Camera: [legislatura, numero, titolo, esito, data]
    pl_file = os.path.join(QUI, '..', 'data', 'proposte_leggi.json')
    if os.path.exists(pl_file):
        per_q = {p['q']: p for p in persone}
        camera_q = {x['id_camera']: x['qid'] for x in json.load(open(
            os.path.join(QUI, '..', 'data', 'elenco.json'), encoding='utf-8'))['persone'] if x.get('id_camera')}
        for pid, v in json.load(open(pl_file, encoding='utf-8'))['proposte'].items():
            if camera_q.get(pid) in per_q:
                per_q[camera_q[pid]]['pl'] = v
    # Gli interventi alla Camera (scripts/interventi_camera.py):
    # {legislatura: [numero, che cosa conta, (in commissione, solo XVI)]}
    ic_file = os.path.join(QUI, '..', 'data', 'interventi_camera.json')
    if os.path.exists(ic_file):
        per_q = {p['q']: p for p in persone}
        for q, v in json.load(open(ic_file, encoding='utf-8'))['interventi'].items():
            if q in per_q:
                per_q[q]['ic'] = v
    # Le richieste dei giudici alla Camera (scripts/autorizzazioni_camera.py):
    # [legislatura, data, tipo, documento, esito, reato o misura]
    au_file = os.path.join(QUI, '..', 'data', 'autorizzazioni.json')
    if os.path.exists(au_file):
        per_q = {p['q']: p for p in persone}
        for q, v in json.load(open(au_file, encoding='utf-8'))['domande'].items():
            if q in per_q:
                per_q[q]['au'] = sorted(v, key=lambda r: (r[1] or '', r[3]))

    # I voti alla Camera, dalla XIII alla XVI: li conta scripts/conta_voti_camera.py
    # dagli archivi votoNN.rdf.zip (33 GB, solo sul PC). Per ogni legislatura:
    # votazioni, voti espressi, in missione, assente, votazioni con una linea del
    # gruppo, voti diversi da quella linea, e le fiducie (si', no, astenuto, in
    # missione, non ha votato).
    voti_file = os.path.join(QUI, '..', 'data', 'voti_camera.json')
    prime_fiducie = []
    tutte_fiducie = []
    if os.path.exists(voti_file):
        V = json.load(open(voti_file, encoding='utf-8'))
        per_ci = {p['ci']: p for p in persone if p.get('ci')}
        for pid, legs in V['deputati'].items():
            p = per_ci.get(pid)
            if not p:
                continue
            vc = {}
            for leg, v in legs.items():
                f_ = {}
                for _, scelta in v.get('fiducie', []):
                    f_[scelta] = f_.get(scelta, 0) + 1
                vc[leg] = [v.get('votazioni', 0), v.get('espressi', 0), v.get('missione', 0),
                           v.get('assente', 0), v.get('con_linea', 0), v.get('dissenso', 0)] +                           [f_.get(k, 0) for k in 'FCAMN']
            p['vc'] = vc
        # Il primo voto di fiducia di ogni governo, con i nomi: la mozione di
        # fiducia con cui la Camera accoglie un governo nuovo.
        for vs, m in sorted(V['fiducie'].items(), key=lambda kv: kv[1].get('data') or ''):
            if not re.search(r'MOZION[EI] DI FIDUCIA', m.get('descrizione') or '', re.I):
                continue
            voti = {}
            for pid, legs in V['deputati'].items():
                for v in legs.values():
                    for x, scelta in v.get('fiducie', []):
                        if x == vs and pid in per_ci:
                            voti.setdefault(scelta, []).append(per_ci[pid]['q'])
            prime_fiducie.append({'g': governo_al(m['data']), 'data': m['data'], 'vs': vs,
                                  'ufficiale': m.get('ufficiale'), 'voti': voti})
        # Tutte le fiducie, per il grafico: data, governo, si', no, astenuti (i totali
        # ufficiali dove ci sono), e il titolo dell'atto. I nomi stanno in un file per
        # votazione (pubblica/fiducie/), scritto da pagine_statiche.
        conta_nom = {}
        for pid, legs in V['deputati'].items():
            for v in legs.values():
                for x, scelta in v.get('fiducie', []):
                    conta_nom.setdefault(x, {}).setdefault(scelta, 0)
                    conta_nom[x][scelta] += 1
        for vs, m in sorted(V['fiducie'].items(), key=lambda kv: kv[1].get('data') or ''):
            u = m.get('ufficiale') or [None, None, None]
            c = conta_nom.get(vs, {})
            # Due totali ufficiali dell'archivio sono impossibili (510 e 470 contrari
            # su 630 deputati, Prodi II, 2006): li' vale l'elenco nominale.
            if None in u or sum(u) > 630:
                u = [c.get('F', 0), c.get('C', 0), c.get('A', 0)]
            titolo = re.sub(r'^Votazione\s+', '', m.get('titolo') or '')
            desc = (m.get('descrizione') or '').upper()
            # Le mozioni contro il governo o un ministro la Camera le segna come
            # fiducie, ma li' votare si' vuol dire votare contro il governo.
            sfiducia = titolo.startswith('Mozione') and 'DI FIDUCIA' not in desc
            tutte_fiducie.append([vs, m.get('data'), governo_al(m.get('data') or ''),
                                  u[0], u[1], u[2], titolo, 'S' if sfiducia else 'F'])
        print('voti alla Camera: %d schede; prime fiducie: %s'
              % (sum(1 for p in persone if p.get('vc')),
                 ', '.join('%s %s' % (x['g'], x['data']) for x in prime_fiducie)))

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
    # Lo spread non e' un dato parlamentare: viene dalla BCE, e se manca il
    # sito esce lo stesso, con una schermata in meno.
    if os.path.exists(SPREAD):
        dati['spread'] = json.load(open(SPREAD, encoding='utf-8'))
    # Le condanne: scritte a mano perche' verificate a mano, e attaccate solo a
    # persone che nell'elenco esistono davvero.
    # Chi ha guidato i partiti. Wikidata queste cariche le tiene male: su
    # 2.763 persone ne restituisce undici vere, nove delle quali di un solo
    # partito. Quindi il file e' scritto a mano, e qui i nomi vengono
    # riagganciati alle schede: chi una scheda non ce l'ha - perche' in
    # Parlamento nel perimetro non c'e' mai stato - resta scritto senza
    # collegamento, che e' il modo onesto di dire che di lui non sappiamo
    # niente d'altro.
    if prime_fiducie:
        dati['fiducie'] = prime_fiducie
    if tutte_fiducie:
        dati['fiducie_tutte'] = tutte_fiducie
    # Per la scheda di Berlusconi: Forza Italia e PdL alle elezioni
    # (scripts/risultati_fi_pdl.py)
    fi_file = os.path.join(QUI, '..', 'data', 'risultati_fi_pdl.json')
    if os.path.exists(fi_file):
        dati['risultati_fi_pdl'] = {'elezioni': json.load(open(fi_file, encoding='utf-8'))['elezioni']}
    # Le sfide nei collegi uninominali 1994-2001 (scripts/collegi_sfide.py)
    cs_file = os.path.join(QUI, '..', 'data', 'collegi_sfide.json')
    if os.path.exists(cs_file):
        dati['collegi_sfide'] = json.load(open(cs_file, encoding='utf-8'))['collegi']
    # Il riassunto dei voti alla Camera (scripts/riassunto_voti_camera.py)
    rv_file = os.path.join(QUI, '..', 'data', 'riassunto_voti.json')
    if os.path.exists(rv_file):
        rv = json.load(open(rv_file, encoding='utf-8'))
        dati['riassunto_voti'] = {k: v for k, v in rv.items() if not k.startswith('_')}
        # I gruppi: quando un gruppo cambia nome l'archivio dei voti gli da' un codice
        # nuovo (UDC -> UDCPTP, IR -> PT, FLI -> FLPTP). Si riuniscono per sigla col
        # registro dei gruppi; FLI e FLPTP nel registro non ci sono, e si uniscono a
        # mano. Le componenti del misto vanno tutte nel misto.
        gc = json.load(open(os.path.join(QUI, '..', 'data', 'gruppi_camera.json'),
                            encoding='utf-8'))['gruppi']
        romani = {'13': 'XIII', '14': 'XIV', '15': 'XV', '16': 'XVI'}
        per_sigla = {(romani.get(v[0]), v[1]): gid for gid, v in gc.items()}
        # le sigle dell'archivio dei voti che il registro non conosce, scritte a mano:
        # (legislatura, sigla nei voti) -> (sigla comune, nome)
        a_mano = {
            ('XIII', 'DS-U'): ('DS-U', "DEMOCRATICI DI SINISTRA - L'ULIVO"),
            ('XIII', 'COMUN'): ('COMUN', 'COMUNISTI ITALIANI'),
            ('XIII', 'RC-PRO'): ('RC-PRO', 'RIFONDAZIONE COMUNISTA - PROGRESSISTI'),
            ('XIII', 'LEGA-P'): ('LEGA', 'LEGA NORD PADANIA'),
            ('XIII', 'LFNIP'): ('LEGA', 'LEGA NORD PADANIA'),
            ('XIII', 'LEGANP'): ('LEGA', 'LEGA NORD PADANIA'),
            ('XIV', 'UDC'): ('UDC', 'UDC (CCD-CDU)'),
            ('XIV', 'U.D.C.'): ('UDC', 'UDC (CCD-CDU)'),
            ('XIV', 'CCDCDU'): ('UDC', 'UDC (CCD-CDU)'),
            ('XVI', 'FLI'): ('FLI', "FUTURO E LIBERTA' PER IL TERZO POLO"),
            ('XVI', 'FLPTP'): ('FLI', "FUTURO E LIBERTA' PER IL TERZO POLO"),
        }
        uniti = {}
        for g in rv.get('gruppi', []):
            if (g['leg'], g['sigla']) in a_mano:
                sigla, nome = a_mano[(g['leg'], g['sigla'])]
                u = uniti.setdefault((g['leg'], 'a mano', sigla), {'leg': g['leg'], 'sigla': sigla, 'nome': nome})
                for k, v in g.items():
                    if isinstance(v, int):
                        u[k] = u.get(k, 0) + v
                continue
            sigla = g['sigla']
            misto = sigla.upper().startswith(('MIST', 'M-')) or g['nome'].upper().startswith('MISTO')
            chiave = (g['leg'], 'MISTO' if misto else g['gid'] if g['gid'] in gc
                      else per_sigla.get((g['leg'], sigla), sigla))
            nome = 'GRUPPO MISTO' if misto else (gc[chiave[1]][2] if chiave[1] in gc else g['nome'])
            u = uniti.setdefault(chiave, {'leg': g['leg'], 'sigla': 'MISTO' if misto else sigla, 'nome': nome})
            for k, v in g.items():
                if isinstance(v, int):
                    u[k] = u.get(k, 0) + v
        dati['riassunto_voti']['gruppi'] = list(uniti.values())
        # le descrizioni della Camera portano entita' HTML ('&#39;'): la pagina le riscrive da se'
        for elenco in ('battute', 'strette'):
            for x in dati['riassunto_voti'].get(elenco, []):
                x['descrizione'] = html_unescape(x.get('descrizione') or '')
                x['titolo'] = html_unescape(x.get('titolo') or '')

    if os.path.exists(SEGRETARI):
        sg = json.load(open(SEGRETARI, encoding='utf-8'))
        per_nome = {}
        for p in persone:
            per_nome.setdefault(chiave_nome(p['n']), []).append(p['q'])
        guide, agganciati, orfani = {}, 0, 0
        for sigla, righe in sg.get('guide', {}).items():
            fuori = []
            for nome, ruolo, da, a in righe:
                cand = per_nome.get(chiave_nome(nome), [])
                q = cand[0] if len(cand) == 1 else ''
                if q:
                    agganciati += 1
                else:
                    orfani += 1
                    fuori.append(nome)
                guide.setdefault(sigla, []).append([nome, ruolo, da, a, q])
            for nome in fuori:
                print('  guida senza scheda (resta senza collegamento): %s, %s'
                      % (nome, sigla))
        if guide:
            dati['segretari'] = {'guide': guide, 'fonti': sg.get('fonti', {})}
            print('chi ha guidato i partiti: %d voci su %d partiti, '
                  '%d con scheda, %d senza'
                  % (agganciati + orfani, len(guide), agganciati, orfani))

    if os.path.exists(ELEZIONI):
        el = json.load(open(ELEZIONI, encoding='utf-8'))
        if el.get('politiche'):
            dati['elezioni'] = {'politiche': el['politiche'],
                                'referendum': el.get('referendum', [])}
            print('elezioni: %d politiche, %d referendum'
                  % (len(el['politiche']), len(el.get('referendum', []))))

    if os.path.exists(ESTERO):
        e = json.load(open(ESTERO, encoding='utf-8'))
        if e.get('eventi'):
            dati['estero'] = {'eventi': e['eventi']}
            print('fatti fuori dai confini: %d' % len(e['eventi']))

    if os.path.exists(VOTO_RUBY):
        v = json.load(open(VOTO_RUBY, encoding='utf-8'))
        noti = {p['q'] for p in persone}
        v['voti'] = [x for x in v.get('voti', []) if x.get('qid') in noti]
        if v['voti']:
            dati['voto_ruby'] = v
            print('voto del 14 settembre 2011: %d nomi' % len(v['voti']))

    if os.path.exists(CONDANNE):
        c = json.load(open(CONDANNE, encoding='utf-8'))
        noti = {p['q'] for p in persone}
        buone = [v for v in c.get('voci', []) if v.get('qid') in noti]
        for v in c.get('voci', []):
            if v.get('qid') not in noti:
                print('  condanna per uno sconosciuto, ignorata: %s' % v.get('qid'))
        if buone:
            dati['condanne'] = {'voci': buone}
            print('condanne verificate: %d su %d persone'
                  % (len(buone), len({v['qid'] for v in buone})))
    else:
        print('  (data/spread.json assente: niente schermata dello spread)')

    dati['__INDIRIZZI__'] = None
    modello = open(MODELLO, encoding='utf-8').read()
    corpo = json.dumps(dati, ensure_ascii=False, separators=(',', ':'))

    # La versione e' un'impronta del contenuto, non un orario: cosi' cambia
    # quando cambia qualcosa davvero, e chi ha la pagina aperta non se la
    # vede ricaricare ogni notte per niente. La data di generazione resta
    # fuori dal conto proprio per questo.
    # Il colofone va contato anche lui. Sta fuori dai dati e fuori dal modello
    # - e' una costante di questo script, iniettata a parte - e per un po' e'
    # rimasto fuori pure dall'impronta: cambiarlo pubblicava una pagina nuova
    # che nessun browser aperto avrebbe mai scaricato, perche' la versione
    # restava quella di prima. Un testo che cambia senza cambiare la versione
    # e' un aggiornamento che non arriva a nessuno.
    senza_data = dict(dati)
    senza_data.pop('generato', None)
    impronta = hashlib.md5(
        (modello + json.dumps(COLOFONE, ensure_ascii=False)
         + json.dumps(senza_data, ensure_ascii=False, sort_keys=True)
         ).encode('utf-8')).hexdigest()[:12]

    scheletro = (modello
                 .replace('/*__DATI__*/', corpo)
                 .replace('/*__COLOFONE__*/', json.dumps(COLOFONE, ensure_ascii=False))
                 .replace('%%VERSIONE%%', impronta))

    # La descrizione che Google mostra sotto il titolo: sotto i 160
    # caratteri, oltre i quali la taglia, e con il numero vero delle schede.
    descrizione = ('I %s deputati, senatori e ministri della Seconda Repubblica, '
                   'dal 1994 al 2013: chi ha cambiato gruppo in Parlamento e '
                   'quante volte.' % pagine_statiche.migliaia(len(persone)))
    titolo_casa = TITOLO + ': chi ha cambiato casacca dal 1994 al 2013'
    html = (scheletro
            .replace('%%TITOLO%%', titolo_casa)
            .replace('<!--%%TESTA%%-->', pagine_statiche.testa_casa(dati, descrizione))
            .replace('<!--%%INTESTAZIONE%%-->', pagine_statiche.intestazione(titolo_casa)))

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

    file, in_mappa = pagine_statiche.costruisci(scheletro, dati, descrizione, impronta,
                                                USCITA, PUBBLICA)
    controlla_js.controlla(
        open(os.path.join(PUBBLICA, 'programma.js'), encoding='utf-8').read(),
        'programma.js')
    print('sito da pubblicare: %d file in pubblica/, %d indirizzi nella mappa'
          % (file, in_mappa))


if __name__ == '__main__':
    main()
