# -*- coding: utf-8 -*-
"""Terza fonte: gli open data del Senato della Repubblica.

La Camera copre i propri deputati e ignora i senatori: questo chiude il buco
dall'altra parte del Parlamento. Stessa regola d'aggancio, nome piu' legislatura
in comune, e la data di nascita tenuta fuori dalla decisione.

Il Senato numera le legislature con le cifre: qui la XII e' la 12.
"""
import urllib.request, urllib.parse, json, os, sys, time, re

ENDPOINT = 'https://dati.senato.it/sparql'
QUI = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(QUI, '..', 'data', 'cache', 'senato_registro.json')

LEGISLATURE = {12: 'XII', 13: 'XIII', 14: 'XIV', 15: 'XV', 16: 'XVI'}

Q_SENATORI = """
PREFIX osr: <http://dati.senato.it/osr/>
PREFIX ocd: <http://dati.camera.it/ocd/>
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
SELECT DISTINCT ?s ?nome ?cognome ?leg ?nascita ?morte ?tipo ?foto ?genere WHERE {
  ?s a osr:Senatore ; foaf:firstName ?nome ; foaf:lastName ?cognome ;
     osr:mandato ?m .
  ?m a ocd:mandatoSenato ; osr:legislatura ?leg .
  FILTER(?leg >= 12 && ?leg <= 16)
  OPTIONAL { ?m osr:tipoMandato ?tipo }
  OPTIONAL { ?s osr:dataNascita ?nascita }
  OPTIONAL { ?s osr:dataMorte ?morte }
  OPTIONAL { ?s foaf:depiction ?foto }
  OPTIONAL { ?s foaf:gender ?genere }
}
"""

# Il vincolo su ocd:mandatoSenato non e' un dettaglio. Il dataset del Senato
# contiene anche i mandati alla CAMERA di chi e' poi diventato senatore,
# marcati ocd:mandatoCamera: senza il filtro, Calderoli risultava senatore
# nella XII e nella XIII, quando era deputato, e un terzo delle voci restava
# senza gruppo perche' il Senato non registra i gruppi della Camera.

# Il Senato dichiara da solo l'identificativo della Camera delle persone che
# hanno seduto in entrambi i rami: e' un aggancio esatto, e arriva proprio
# dove l'euristica sui nomi e' piu' fragile. Il Senato scrive a volte 'dd'
# dove la Camera scrive 'd', e mette gli zeri davanti.
Q_PONTE = """
PREFIX osr: <http://dati.senato.it/osr/>
PREFIX owl: <http://www.w3.org/2002/07/owl#>
SELECT DISTINCT ?s ?dep WHERE {
  ?s a osr:Senatore ; osr:mandato ?m .
  ?m osr:legislatura ?leg ; owl:sameAs ?dep .
  FILTER(?leg >= 12 && ?leg <= 16)
}
"""


# Tutte le adesioni datate, non solo la prima: la successione dei gruppi e'
# il dato per cui esiste questo sito. Un gruppo cambia
# nome negli anni, quindi fra le sue denominazioni si sceglie quella in vigore
# il giorno dell'adesione: nell'ottava legislatura il MSI e' "MSI - DN", non
# quello che si chiamera' poi.
Q_ADESIONI = """
PREFIX osr: <http://dati.senato.it/osr/>
PREFIX ocd: <http://dati.camera.it/ocd/>
PREFIX foaf: <http://xmlns.com/foaf/0.1/>
SELECT DISTINCT ?nome ?cognome ?gr ?inizio ?fine WHERE {
  ?s a osr:Senatore ; foaf:firstName ?nome ; foaf:lastName ?cognome ;
     ocd:aderisce ?a .
  ?a osr:legislatura %d ; osr:gruppo ?gr ; osr:inizio ?inizio .
  OPTIONAL { ?a osr:fine ?fine }
}
"""

# Le denominazioni si chiedono a parte. Chiedendole insieme alle adesioni si
# moltiplicano fra loro, e la risposta sbatte contro il tetto di diecimila
# righe dell'endpoint: la prima legislatura da sola lo sfondava.
Q_DENOMINAZIONI = """
PREFIX osr: <http://dati.senato.it/osr/>
SELECT ?gr ?titolo ?breve ?dInizio ?dFine WHERE {
  ?gr osr:denominazione ?d . ?d osr:titolo ?titolo .
  OPTIONAL { ?d osr:titoloBreve ?breve }
  OPTIONAL { ?d osr:inizio ?dInizio }
  OPTIONAL { ?d osr:fine ?dFine }
}
"""


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


def data_iso(v):
    v = (v or '').strip()[:10]
    if len(v) == 10 and v[4] == '-' and v[7] == '-':
        return v
    if len(v) >= 4 and v[:4].isdigit():
        return v[:4]
    return None


ISTANTANEA = os.path.join(QUI, '..', 'data', 'registri', 'senato.json')


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


def registro(usa_cache=True):
    """{chiave nome: {mandato: {'morte':…, 'nascita':…}}}

    Come per la Camera: se l'endpoint tace si usa la copia versionata.
    """
    if usa_cache and os.path.exists(CACHE):
        return json.load(open(CACHE, encoding='utf-8'))
    try:
        return _costruisci()
    except Exception as e:
        vecchia = _istantanea()
        if vecchia is None:
            raise
        sys.stderr.write('  il Senato non risponde (%s):\n'
                         '  uso la copia versionata, %d voci.\n'
                         % (e, len(vecchia)))
        return vecchia


def _gruppi():
    """{(chiave nome, mandato): sigla} col gruppo d'ingresso in quella legislatura."""
    import camera

    # nome del gruppo valido in un certo giorno
    denominazioni = {}
    for r in interroga(Q_DENOMINAZIONI):
        gr = r['gr']['value']
        titolo = (r.get('breve', {}).get('value')
                  or r.get('titolo', {}).get('value') or '').strip()
        if titolo:
            denominazioni.setdefault(gr, []).append((
                (r.get('dInizio', {}).get('value') or '')[:10],
                (r.get('dFine', {}).get('value') or '')[:10], titolo))

    def come_si_chiamava(gr, giorno):
        candidate = denominazioni.get(gr) or []
        for da, a, titolo in candidate:
            if da and giorno and da > giorno:
                continue
            if a and giorno and a < giorno:
                continue
            return titolo
        return candidate[0][2] if candidate else None

    scelte = {}
    for numero, mandato in sorted(LEGISLATURE.items()):
        righe = interroga(Q_ADESIONI % numero)
        if len(righe) >= 10000:
            raise RuntimeError('legislatura %d troncata' % numero)
        for r in righe:
            k = camera.chiave(r.get('nome', {}).get('value'),
                              r.get('cognome', {}).get('value'))
            adesione = (r.get('inizio', {}).get('value') or '')[:10]
            fine = (r.get('fine', {}).get('value') or '')[:10]
            if not k:
                continue
            titolo = come_si_chiamava(r['gr']['value'], adesione)
            if not titolo:
                continue
            scelte.setdefault((k, mandato), set()).add(
                (adesione.replace('-', ''), fine.replace('-', ''),
                 r['gr']['value'], titolo))
        time.sleep(0.3)
    return {k: unisci_adesioni(v) for k, v in scelte.items()}


def unisci_adesioni(grezze):
    """Adesioni ordinate, con quelle consecutive allo stesso gruppo fuse.

    Il Senato spezza in due un'adesione senza che la persona si sia mossa:
    Viespoli risulta in Futuro e Liberta' dal 2 agosto al 28 settembre 2010 e
    poi di nuovo dal 29 settembre, ed e' lo stesso gruppo. Contarle come due
    sarebbe un cambio di casacca inventato. L'identita' e' l'URI del gruppo,
    non il nome, che cambia negli anni.
    """
    fuori = []
    for da, a, uri, nome in sorted(grezze):
        if fuori and fuori[-1]['uri'] == uri:
            if a > (fuori[-1]['a'] or ''):
                fuori[-1]['a'] = a
            continue
        fuori.append({'uri': uri, 'g': nome, 'da': da, 'a': a})
    return fuori


def _ponte():
    """{URI del senatore: identificativo persona della Camera}."""
    fuori = {}
    for r in interroga(Q_PONTE):
        m = re.search(r'/dd?0*(\d+)_', r['dep']['value'])
        if m:
            fuori[r['s']['value']] = m.group(1)
    return fuori


def _costruisci():
    import camera
    gruppi = _gruppi()
    ponte = _ponte()
    fuori = {}
    for r in interroga(Q_SENATORI):
        mandato = LEGISLATURE.get(int(float(r['leg']['value'])))
        if not mandato:
            continue
        k = camera.chiave(r.get('nome', {}).get('value'),
                          r.get('cognome', {}).get('value'))
        if not k:
            continue
        voce = {'morte': data_iso(r.get('morte', {}).get('value')),
                'nascita': data_iso(r.get('nascita', {}).get('value')),
                'nome': camera.nome_leggibile(r.get('nome', {}).get('value'),
                                              r.get('cognome', {}).get('value')),
                'uri': r['s']['value'],
                'cognome': (r.get('cognome', {}).get('value') or '').strip()}
        # Il Senato pubblica la foto ufficiale di tutti i suoi senatori,
        # legislatura per legislatura. Dell'indirizzo bastano il numero della
        # legislatura e l'identificativo: il resto e' sempre uguale.
        m = re.search(r'/leg/(\d+)/Immagini/Senatori/0*(\d+)\.jpg',
                      r.get('foto', {}).get('value') or '')
        if m:
            voce['foto_senato'] = [m.group(1), m.group(2)]
        g = (r.get('genere', {}).get('value') or '').strip().upper()
        if g:
            voce['genere'] = 'F' if g.startswith('F') else 'M'
        # I senatori a vita e di diritto attraversano ogni legislatura per
        # definizione: contati come gli altri falserebbero ogni classifica
        # di longevita', quindi restano marcati.
        tipo = (r.get('tipo', {}).get('value') or '').lower()
        if 'vita' in tipo or 'diritto' in tipo:
            voce['a_vita'] = True
        if r['s']['value'] in ponte:
            voce['id_camera'] = ponte[r['s']['value']]
        if (k, mandato) in gruppi:
            voce['gruppi'] = gruppi[(k, mandato)]
            voce['gruppo'] = gruppi[(k, mandato)][0]['g']
        fuori.setdefault(k, {})[mandato] = voce
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


def cerca(reg, nome, mandati):
    import camera
    return camera.cerca(reg, nome, mandati)


def indice_per_data(reg):
    import camera
    return camera.indice_per_data(reg)


def indice_per_mandato(reg):
    import camera
    return camera.indice_per_mandato(reg)


def cerca_ampia(reg, indice, nome, nascita, mandati, per_mandato=None):
    import camera
    return camera.cerca_ampia(reg, indice, nome, nascita, mandati, per_mandato)


def cerca_chiave(reg, indice, nome, nascita, mandati, per_mandato=None):
    import camera
    return camera.cerca_chiave(reg, indice, nome, nascita, mandati, per_mandato)


if __name__ == '__main__':
    sys.path.insert(0, QUI)
    reg = registro(usa_cache=False)
    con_morte = sum(1 for v in reg.values() if any(x.get('morte') for x in v.values()))
    print('senatori distinti nel perimetro: %d' % len(reg))
    print('di cui con data di morte: %d' % con_morte)
