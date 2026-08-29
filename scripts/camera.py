# -*- coding: utf-8 -*-
"""Seconda fonte: gli open data della Camera dei deputati.

Wikidata e' rapida sui personaggi noti e cieca sui deputati di seconda fila:
di parecchi non registra la morte, e quelli restavano per sempre fra i viventi.
La Camera invece tiene il registro dei propri ex, decessi compresi.

L'aggancio e' per nome PIU' legislatura in comune, mai per data di nascita.
Il solo nome non basta, perche' la Camera arriva fino al Regno e c'e' un
Giuseppe Vacca del 1810. La data di nascita non serve e anzi danneggia, perche'
a volte e' Wikidata a sbagliarla: Giovanni Battista Melis li' risulta del 1922,
alla Camera del 1904, ed e' la Camera ad avere ragione.

Dentro la Camera invece l'aggancio e' esatto: l'URI del deputato per una data
legislatura (d19930_4) contiene l'identificativo della persona (p19930), che
porta le date. Nessuna euristica.
"""
import urllib.request, urllib.parse, json, os, re, sys, time, unicodedata

ENDPOINT = 'https://dati.camera.it/sparql'
QUI = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(QUI, '..', 'data', 'cache', 'camera_registro.json')

LEGISLATURE = [
    ('XII', 'repubblica_12'), ('XIII', 'repubblica_13'),
    ('XIV', 'repubblica_14'), ('XV',   'repubblica_15'),
    ('XVI', 'repubblica_16'),
]

Q_DEPUTATI = """
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
PREFIX ocd: <http://dati.camera.it/ocd/>
SELECT DISTINCT ?dep ?cognome ?nome WHERE {
  ?dep a ocd:deputato ;
       ocd:rif_leg <http://dati.camera.it/ocd/legislatura.rdf/%s> ;
       foaf:surname ?cognome ; foaf:firstName ?nome .
}
"""

Q_DECESSI = """
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
PREFIX bio: <http://purl.org/vocab/bio/0.1/>
SELECT DISTINCT ?pers ?morte WHERE {
  ?pers a foaf:Person ; bio:Death ?d . ?d bio:date ?morte .
}
"""

# Le nascite vanno chieste per tutti, non solo per i defunti: servono a
# riconoscere i viventi che le due fonti chiamano in modo diverso.
Q_NASCITE = """
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
PREFIX bio: <http://purl.org/vocab/bio/0.1/>
SELECT DISTINCT ?pers ?nascita WHERE {
  ?pers a foaf:Person ; bio:Birth ?b . ?b bio:date ?nascita .
}
"""


# Il gruppo parlamentare e' il partito di allora, non quello di poi.
#
# L'etichetta appiccicata all'adesione NON e' il nome del gruppo: nella XV
# dice "L'ULIVO" mentre il gruppo si chiamava "PARTITO DEMOCRATICO-L'ULIVO
# (PD-U)", e dice "DEMOCRAZIA CRISTIANA-PARTITO SOCIALISTA" per quello che era
# "DCA-DEMOCRAZIA CRISTIANA PER LE AUTONOMIE-NUOVO PSI". Il nome vero sta
# dietro ocd:rif_gruppoParlamentare, e si porta dietro la sigla ufficiale fra
# parentesi: quella non va inventata con un acronimo automatico, c'e' gia'.
#
# Le date stanno nei loro campi (startDate/endDate) e non vanno piu' pescate
# dall'etichetta, e motivoTermine dice perche' l'adesione e' finita: serve a
# distinguere un cambio di casacca dalla fine della legislatura o da un decesso.
Q_GRUPPI = """
PREFIX ocd: <http://dati.camera.it/ocd/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?dep ?gp ?gruppo ?allora ?da ?a ?motivo WHERE {
  ?dep a ocd:deputato ;
       ocd:rif_leg <http://dati.camera.it/ocd/legislatura.rdf/%s> ;
       ocd:aderisce ?ad .
  ?ad ocd:rif_gruppoParlamentare ?gp ; ocd:startDate ?da ;
      rdfs:label ?allora .
  ?gp rdfs:label ?gruppo .
  OPTIONAL { ?ad ocd:endDate ?a }
  OPTIONAL { ?ad ocd:motivoTermine ?motivo }
}
"""


PERIODO = re.compile(r'\s*\(\d{2}\.\d{2}\.\d{4}\s*-\s*\d{2}\.\d{2}\.\d{4}\)\s*$')


def _ultima_parentesi(t):
    """Il contenuto dell'ultima parentesi bilanciata in fondo, o None."""
    if not t.endswith(')'):
        return None
    prof = 0
    for i in range(len(t) - 1, -1, -1):
        if t[i] == ')':
            prof += 1
        elif t[i] == '(':
            prof -= 1
            if prof == 0:
                return t[i + 1:-1].strip(), t[:i].strip()
    return None


def spezza_gruppo(etichetta):
    """'PARTITO DEMOCRATICO-L'ULIVO (PD-U) (03.05.2006-28.04.2008)'
    -> ('PARTITO DEMOCRATICO-L'ULIVO', 'PD-U').

    Si sfila da destra: prima il periodo, poi la sigla. Sia il nome sia la
    sigla possono contenere parentesi ("UDC (UNIONE DEI DEMOCRATICI
    CRISTIANI...) (UDC (CCD-CDU))"), quindi si contano le parentesi invece di
    fermarsi alla prima che capita.
    """
    t = PERIODO.sub('', (etichetta or '').strip())
    presa = _ultima_parentesi(t)
    if presa and len(presa[0]) <= 40 and presa[1]:
        return presa[1], presa[0]
    return t, ''


def interroga(query, tentativi=4):
    ultimo = None
    for i in range(tentativi):
        try:
            u = ENDPOINT + '?' + urllib.parse.urlencode(
                {'query': query, 'format': 'application/sparql-results+json'})
            r = urllib.request.Request(u, headers={
                'User-Agent': 'SecondaRepubblicaTracker/0.1 (progetto personale; davide.caniatti@gmail.com)',
                'Accept': 'application/sparql-results+json'})
            return json.load(urllib.request.urlopen(r, timeout=300))['results']['bindings']
        except Exception as e:
            ultimo = e
            sys.stderr.write('  ritento (%d): %s\n' % (i + 1, e))
            time.sleep(5 * (i + 1))
    raise ultimo


def nome_leggibile(nome, cognome):
    """'ANTONIO' + 'CIRINO POMICINO' -> 'Antonio Cirino Pomicino'."""
    return ' '.join(x for x in ((nome or '').strip().title(),
                                (cognome or '').strip().title()) if x)


def chiave(nome, cognome=''):
    """Nome e cognome ridotti all'osso: niente accenti, niente maiuscole,
    ordine indifferente. 'SASSO GIUSEPPE' e 'Giuseppe Sasso' coincidono."""
    s = unicodedata.normalize('NFKD', (nome or '') + ' ' + (cognome or '')).lower()
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return ' '.join(sorted(''.join(c if c.isalnum() else ' ' for c in s).split()))


def data_iso(v):
    """La Camera scrive le date come 20150121, e a volte solo l'anno."""
    v = (v or '').strip()
    if len(v) == 8 and v.isdigit():
        return '%s-%s-%s' % (v[0:4], v[4:6], v[6:8])
    if len(v) == 4 and v.isdigit():
        return v
    return None


def id_persona(uri_deputato):
    """Da .../deputato.rdf/d19930_4 all'identificativo persona 19930."""
    m = re.search(r'/d(\d+)_', uri_deputato or '')
    return m.group(1) if m else None


ISTANTANEA = os.path.join(QUI, '..', 'data', 'registri', 'camera.json')


def _salva_istantanea(dati):
    os.makedirs(os.path.dirname(ISTANTANEA), exist_ok=True)
    json.dump(dati, open(ISTANTANEA, 'w', encoding='utf-8'), ensure_ascii=False)


def _istantanea():
    """L'ultima copia buona del registro, versionata nel repository.

    Serve da rete: se l'endpoint non risponde, il lavoro notturno deve poter
    contare sull'ultimo elenco noto invece di pubblicare un sito peggiore. E'
    gia' successo: la Camera non ha risposto dai server di GitHub e sono stati
    pubblicati centocinquantuno morti tornati vivi.
    """
    if os.path.exists(ISTANTANEA):
        return json.load(open(ISTANTANEA, encoding='utf-8'))
    return None


Q_PRESIDENTI = """
PREFIX ocd: <http://dati.camera.it/ocd/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?dep ?u WHERE {
  ?dep a ocd:deputato ;
       ocd:rif_leg <http://dati.camera.it/ocd/legislatura.rdf/%s> ;
       ocd:rif_ufficioParlamentare ?uf .
  ?uf rdfs:label ?u .
  FILTER(STRSTARTS(STR(?u), "PRESIDENTE di UFFICIO DI PRESIDENZA,"))
}
"""


def presidenti():
    """{identificativo persona: legislatura} di chi ha presieduto la Camera.

    Su Wikidata quella carica e' quasi tutta mancante: alla voce 'presidente
    della Camera dei deputati' ci sono nove nomi in tutto, e per il nostro
    perimetro solo Irene Pivetti. Violante, Casini, Bertinotti e Fini non ci
    sono. La Camera invece i propri presidenti li registra, dentro gli uffici
    parlamentari. Comanda il registro, come sempre.
    """
    fuori = {}
    for mandato, codice in LEGISLATURE:
        for r in interroga(Q_PRESIDENTI % codice):
            pid = id_persona(r['dep']['value'])
            if pid:
                fuori[pid] = mandato
        time.sleep(0.3)
    return fuori


def registro(usa_cache=True):
    """{chiave nome: {mandato: {'morte':…, 'nascita':…, 'id':…}}}

    Se l'endpoint tace si ripiega sulla copia versionata invece di restituire
    il vuoto. Un registro vecchio di un giorno vale incomparabilmente piu' di
    un registro assente, che rimanderebbe fra i vivi tutti i morti che solo
    lui conosce.
    """
    if usa_cache and os.path.exists(CACHE):
        return json.load(open(CACHE, encoding='utf-8'))
    try:
        return _costruisci()
    except Exception as e:
        vecchia = _istantanea()
        if vecchia is None:
            raise
        sys.stderr.write('  la Camera non risponde (%s):\n'
                         '  uso la copia versionata, %d voci.\n'
                         % (e, len(vecchia)))
        return vecchia


def unisci_adesioni(grezze):
    """Adesioni ordinate, con quelle consecutive allo stesso gruppo fuse.

    Un'adesione puo' essere spezzata in due record senza che la persona si sia
    mossa: al Senato Viespoli risulta in Futuro e Liberta' dal 2 agosto al 28
    settembre e poi di nuovo dal 29 settembre, ed e' lo stesso gruppo. Contarle
    come due sarebbe un cambio di casacca inventato.
    """
    fuori = []
    for da, a, uri, nome, sigla, allora, motivo in sorted(grezze):
        if fuori and fuori[-1]['uri'] == uri:
            if a > (fuori[-1]['a'] or ''):
                fuori[-1]['a'] = a
                fuori[-1]['fine'] = motivo
            continue
        voce = {'uri': uri, 'g': nome, 's': sigla, 'da': da, 'a': a,
                'fine': motivo}
        # Il gruppo si porta il nome che aveva alla fine; se allora si
        # chiamava altrimenti (Iniziativa Responsabile prima di diventare
        # Popolo e Territorio) vale la pena ricordarlo.
        if allora:
            voce['allora'] = allora
        fuori.append(voce)
    return fuori


def _costruisci():
    def identificativo(r):
        pid = (r['pers']['value'].rsplit('/p', 1) + [''])[1]
        return pid if pid.isdigit() else None

    dati_persona = {}
    for r in interroga(Q_NASCITE):
        pid = identificativo(r)
        if pid:
            dati_persona[pid] = {
                'nascita': data_iso(r.get('nascita', {}).get('value')),
                'morte': None}
    for r in interroga(Q_DECESSI):
        pid = identificativo(r)
        if pid:
            dati_persona.setdefault(pid, {'nascita': None})['morte'] = \
                data_iso(r.get('morte', {}).get('value'))

    fuori = {}
    for mandato, codice in LEGISLATURE:
        # Qui, al contrario della prima Repubblica, i gruppi si tengono
        # TUTTI: la successione datata delle adesioni e' il dato per cui
        # esiste questo sito.
        grezzi = {}
        for r in interroga(Q_GRUPPI % codice):
            pid = id_persona(r['dep']['value'])
            nome_g, sigla_g = spezza_gruppo(r['gruppo']['value'])
            allora, _ = spezza_gruppo(r.get('allora', {}).get('value') or '')
            if not pid or not nome_g:
                continue
            grezzi.setdefault(pid, set()).add((
                (r['da']['value'] or '')[:10].replace('-', ''),
                (r.get('a', {}).get('value') or '')[:10].replace('-', ''),
                r['gp']['value'], nome_g, sigla_g,
                allora if allora and allora != nome_g else '',
                (r.get('motivo', {}).get('value') or '')))
        gruppi = {pid: unisci_adesioni(v) for pid, v in grezzi.items()}

        righe = interroga(Q_DEPUTATI % codice)
        con_morte = 0
        for r in righe:
            k = chiave(r.get('nome', {}).get('value'), r.get('cognome', {}).get('value'))
            pid = id_persona(r['dep']['value'])
            if not k or not pid:
                continue
            voce = dict(dati_persona.get(pid) or {'morte': None, 'nascita': None})
            voce['id'] = pid
            # La Camera scrive tutto in maiuscolo. Il nome per esteso serve a
            # chi nei registri c'e' e su Wikidata no: senza, resterebbe la
            # chiave d'aggancio, che e' illeggibile ('agostinacchio antonio').
            voce['nome'] = nome_leggibile(r.get('nome', {}).get('value'),
                                          r.get('cognome', {}).get('value'))
            # Il cognome separato serve a mettere l'elenco in ordine: un
            # elenco di persone si ordina per cognome, e 'Nome Cognome' non
            # dice dove finisce l'uno e comincia l'altro.
            voce['cognome'] = (r.get('cognome', {}).get('value') or '').strip().title()
            if pid in gruppi:
                voce['gruppi'] = gruppi[pid]
                voce['gruppo'] = gruppi[pid][0]['g']
            fuori.setdefault(k, {})[mandato] = voce
            if voce['morte']:
                con_morte += 1
        sys.stderr.write('  %-12s %4d deputati, %4d con data di morte\n'
                         % (mandato, len(righe), con_morte))
        time.sleep(0.5)

    # Una risposta molto piu' magra del solito e' un guasto travestito da
    # successo: meglio l'ultima copia buona che un elenco dimezzato.
    vecchia = _istantanea()
    if vecchia and len(fuori) < len(vecchia) * 0.8:
        sys.stderr.write('  ATTENZIONE: solo %d voci contro le %d note: '
                         'uso la copia versionata.\n'
                         % (len(fuori), len(vecchia)))
        return vecchia

    os.makedirs(os.path.dirname(CACHE), exist_ok=True)
    json.dump(fuori, open(CACHE, 'w', encoding='utf-8'), ensure_ascii=False)
    _salva_istantanea(fuori)
    return fuori


def indice_per_data(reg):
    """(legislatura, data di nascita) -> voci. Serve a ritrovare chi le due
    fonti chiamano in modo diverso: per la Camera e' VIRGINIO SCOTTI, per
    Wikidata Gerry Scotti, ma la data di nascita e il seggio sono gli stessi."""
    fuori = {}
    for k, voci in reg.items():
        for mandato, v in voci.items():
            if v.get('nascita') and len(v['nascita']) == 10:
                fuori.setdefault((mandato, v['nascita']), []).append((k, v))
    return fuori


def indice_per_mandato(reg):
    """legislatura -> voci, per l'ultimo tentativo a strascico."""
    fuori = {}
    for k, voci in reg.items():
        for mandato, v in voci.items():
            fuori.setdefault(mandato, []).append((k, v))
    return fuori


def cerca_chiave(reg, indice, nome, nascita, mandati, per_mandato=None):
    """Come cerca_ampia, ma restituisce la CHIAVE della persona nel registro.

    Serve perche' di una persona non interessa piu' una legislatura sola: la
    successione dei gruppi va letta su tutte quelle che ha fatto.
    """
    k = chiave(nome)
    voci = reg.get(k)
    if voci and any(m in voci for m in mandati):
        return k, 'nome'

    pezzi = {x for x in k.split() if len(x) >= 3}
    if nascita and len(nascita) == 10:
        for mandato in mandati:
            for kk, _voce in indice.get((mandato, nascita), []):
                if pezzi & {x for x in kk.split() if len(x) >= 3}:
                    return kk, 'data'

    if per_mandato and len(pezzi) >= 2:
        for mandato in mandati:
            for kk, _voce in per_mandato.get(mandato, []):
                altri = {x for x in kk.split() if len(x) >= 3}
                if len(altri) >= 2 and (altri <= pezzi or pezzi <= altri):
                    return kk, 'nome contenuto'
    return None, None


def cerca_ampia(reg, indice, nome, nascita, mandati, per_mandato=None):
    """Tre tentativi, dal piu' stretto al piu' largo.

    1. nome esatto e legislatura in comune;
    2. legislatura piu' data di nascita esatta, purche' resti almeno un pezzo
       di cognome in comune: senza quel vincolo si accoppierebbe Rosa Russo
       Iervolino col primo Raffaele Russo che passa;
    3. un nome contenuto nell'altro, nella stessa legislatura. Serve ai cognomi
       da sposata, che i registri accorciano: LODI ADRIANA sta dentro Adriana
       Lodi Faustini Fustini. Si pretendono almeno due parole in comune.
    """
    v = cerca(reg, nome, mandati)
    if v:
        return v, 'nome'

    pezzi = {x for x in chiave(nome).split() if len(x) >= 3}
    if nascita and len(nascita) == 10:
        for mandato in mandati:
            for k, voce in indice.get((mandato, nascita), []):
                if pezzi & {x for x in k.split() if len(x) >= 3}:
                    return voce, 'data'

    if per_mandato and len(pezzi) >= 2:
        for mandato in mandati:
            for k, voce in per_mandato.get(mandato, []):
                altri = {x for x in k.split() if len(x) >= 3}
                if len(altri) >= 2 and (altri <= pezzi or pezzi <= altri):
                    return voce, 'nome contenuto'
    return None, None


def cerca(reg, nome, mandati):
    """La voce di quella persona, cercata solo fra le legislature che ha in
    comune col registro. Nessuna legislatura condivisa, nessun aggancio."""
    voci = reg.get(chiave(nome))
    if not voci:
        return None
    comuni = [m for m in mandati if m in voci]
    if not comuni:
        return None
    for m in comuni:
        if voci[m].get('morte'):
            return voci[m]
    return voci[comuni[0]]


if __name__ == '__main__':
    reg = registro(usa_cache=False)
    con_morte = sum(1 for v in reg.values() if any(x.get('morte') for x in v.values()))
    print('deputati distinti nel perimetro: %d' % len(reg))
    print('di cui con data di morte: %d' % con_morte)
