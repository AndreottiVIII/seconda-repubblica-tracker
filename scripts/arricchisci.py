# -*- coding: utf-8 -*-
"""Le schede piu' ricche: quello che i registri sanno oltre ai gruppi.

Primo giro, solo fonti ufficiali:

  Camera, dai pacchetti interi di dati.camera.it/ocd/dump/ (non dal servizio
  di interrogazione, che a volte resta fermo per giorni):
    persona.rdf        studi e professione
    membroGoverno.rdf  ogni incarico di governo: ruolo, ministero, date
    governo.rdf        il nome di ogni governo
    atto-12 ... 16     le proposte di legge, legislatura per legislatura

  Senato, dal servizio di interrogazione, agganciato col numero del senatore:
    gli incarichi interni (commissioni e Presidenza), che ad agosto non
    avevo trovato perche' cercavo nel posto sbagliato; la professione; le
    proposte di legge, che il Senato pubblica dalla XIII legislatura.

Una fonte per tipo di dato: le proposte presentate alla Camera vengono dalla
Camera, quelle presentate al Senato dal Senato, e un disegno di legge che
passa da un ramo all'altro si conta solo dove e' nato.

Esce data/arricchimenti.json, indicizzato col codice della scheda.
"""
import collections
import io
import json
import os
import re
import sys
import time
import urllib.request
import zipfile
import xml.etree.ElementTree as ET

QUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, QUI)
import camera
import senato

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

ELENCO = os.path.join(QUI, '..', 'data', 'elenco.json')
USCITA = os.path.join(QUI, '..', 'data', 'arricchimenti.json')
CACHE = os.path.join(QUI, '..', 'data', 'cache', 'camera_dump')
DUMP = 'https://dati.camera.it/ocd/dump/%s.rdf.zip'
UA = 'SecondaRepubblicaTracker/0.1 (progetto personale)'

ROMANI = {12: 'XII', 13: 'XIII', 14: 'XIV', 15: 'XV', 16: 'XVI'}
GOVERNI = {'Berlusconi I', 'Dini', 'Prodi I', "D'Alema I", "D'Alema II", 'Amato II',
           'Berlusconi II', 'Berlusconi III', 'Prodi II', 'Berlusconi IV', 'Monti'}
GIORNI_CACHE = 7


# ------------------------------------------------------------------ Camera

ZIP_CAMERA = os.path.join(QUI, '..', 'data', 'cache', 'zip_camera')


def pacchetto(nome):
    """Il testo di un archivio della Camera. Si legge lo zip gia' scaricato in
    data/cache/zip_camera/ (Davide: "scarica gli zip, meglio sempre"); se non
    c'e', lo si scarica li'. Sono legislature chiuse: non cambiano."""
    os.makedirs(ZIP_CAMERA, exist_ok=True)
    percorso = os.path.join(ZIP_CAMERA, nome + '.rdf.zip')
    if not os.path.exists(percorso):
        r = urllib.request.Request(DUMP % nome, headers={'User-Agent': UA})
        open(percorso, 'wb').write(urllib.request.urlopen(r, timeout=600).read())
    with zipfile.ZipFile(percorso) as z:
        return z.read(z.namelist()[0]).decode('utf-8')


RIGA = re.compile(r'^(\S+)\t<([^>]+)>\t(.*) \.\s*$')


def letterale(o):
    o = o.strip()
    if o.startswith('<'):
        return o[1:-1]
    if o.startswith('"'):
        s = o[1:o.rindex('"')]
        s = re.sub(r'\\u([0-9A-Fa-f]{4})', lambda m: chr(int(m.group(1), 16)), s)
        return s.replace('\\"', '"').replace('\\n', ' ')
    return o


def triple(testo, prefisso):
    for riga in testo.splitlines():
        if not riga.startswith(prefisso):
            continue
        m = RIGA.match(riga)
        if m:
            yield (m.group(1)[1:-1], m.group(2).rsplit('/', 1)[-1].split('#')[-1],
                   letterale(m.group(3)))


def data(s):
    s = (s or '').strip()
    return '%s-%s-%s' % (s[:4], s[4:6], s[6:8]) if len(s) == 8 and s.isdigit() else None


def pulisci(testo):
    """'<p>Laurea in lettere; insegnante.</p>' -> 'Laurea in lettere; insegnante'."""
    t = re.sub(r'<[^>]+>', ' ', testo or '')
    t = re.sub(r'\s+', ' ', t).strip().rstrip('.;, ').strip()
    t = re.sub(r'\s*;\s*', '; ', t)
    return t[:1].upper() + t[1:] if t else ''


def nome_governo(titolo, conta):
    """'II Governo Prodi (17.05.2006 - 07.05.2008)' -> 'Prodi II'; 'Governo
    Dini (...)' -> 'Dini'. Il numero solo per chi ne ha avuti piu' d'uno: lo
    stesso modo in cui il sito chiama i governi."""
    t = re.sub(r'\s*\(.*$', '', titolo or '').strip()
    m = re.match(r'^([IVXL]+)\s+Governo\s+(.+)$', t)
    ordine, chi = (m.groups() if m else ('I', re.sub(r'^Governo\s+', '', t)))
    return chi if conta.get(chi, 0) <= 1 else '%s %s' % (chi, ordine)


def anagrafe_camera():
    """{pid: {nome, cognome, leg, studi, governo}} per chi tocca il perimetro."""
    persona = pacchetto('persona')
    membri = pacchetto('membroGoverno')
    governi = pacchetto('governo')

    titoli = {}
    for s, p, o in triple(governi, '<http://dati.camera.it/ocd/governo.rdf/'):
        if p == 'title':
            titoli[s.rsplit('/', 1)[-1]] = o
    conta = {}
    for t in titoli.values():
        chi = re.sub(r'^([IVXL]+\s+)?Governo\s+', '', re.sub(r'\s*\(.*$', '', t)).strip()
        conta[chi] = conta.get(chi, 0) + 1
    nomi_gov = {g: nome_governo(t, conta) for g, t in titoli.items()}

    voci = {}
    for s, p, o in triple(membri, '<http://dati.camera.it/ocd/membroGoverno.rdf/'):
        voci.setdefault(s, {})[p] = o
    incarichi = {}
    for v in voci.values():
        pid = (v.get('rif_persona') or '').rsplit('/p', 1)[-1]
        gov = nomi_gov.get((v.get('rif_governo') or '').rsplit('/', 1)[-1], '')
        if not pid.isdigit() or not v.get('title') or gov not in GOVERNI:
            continue
        carica = re.sub(r'\s*\([^)]*\)\s*$', '', v['title']).strip()
        # 'MInistro del Lavoro': un refuso della fonte
        carica = re.sub(r'^MI(?=[a-z])', 'Mi', carica)
        if v.get('interim') == '1':
            carica += ' (ad interim)'
        incarichi.setdefault(pid, []).append(
            {'carica': carica, 'da': data(v.get('startDate')),
             'a': data(v.get('endDate')), 'governo': gov})

    persone = {}
    for s, p, o in triple(persona, '<http://dati.camera.it/ocd/persona.rdf/p'):
        pid = s.rsplit('/p', 1)[-1]
        if not pid.isdigit():
            continue
        x = persone.setdefault(pid, {'leg': set()})
        if p in ('rif_mandatoCamera', 'rif_mandatoSenato'):
            m = re.search(r'/m[cs](\d+)_', o)
            if m and int(m.group(1)) in ROMANI:
                x['leg'].add(ROMANI[int(m.group(1))])
        elif p in ('firstName', 'surname', 'description'):
            x[p] = o

    fuori = {}
    for pid, x in persone.items():
        gov = sorted(incarichi.get(pid, []), key=lambda i: i['da'] or '')
        if not x['leg'] and not gov:
            continue
        voce = {'nome': x.get('firstName', ''), 'cognome': x.get('surname', ''),
                'leg': sorted(x['leg']), 'governi': sorted({i['governo'] for i in gov})}
        if pulisci(x.get('description')):
            voce['studi'] = pulisci(x['description'])
        if gov:
            voce['governo'] = gov
        fuori[pid] = voce
    return fuori


MAIUSCOLE = {'di', 'del', 'della', 'dei', 'e', 'nell', 'nella', 'sul', 'in', 'd', 'de'}


def bel_luogo(testo):
    """'CAMPANIA 2' -> 'Campania 2'; "SANT'AGATA DE' GOTI" -> "Sant'Agata de' Goti"."""
    parole = re.split(r"([ '\-/()])", (testo or '').strip().lower())
    return ''.join(w if (w in MAIUSCOLE and i > 0) else w[:1].upper() + w[1:]
                   for i, w in enumerate(parole))


def elezioni_camera():
    """{pid: {legislatura: [tipo, luogo, lista]}}. Nella XII, XIII e XIV il
    collegio uninominale per chi e' entrato col maggioritario; per gli altri e
    dalla XV la circoscrizione, con la lista."""
    voci = collections.defaultdict(dict)
    for s, p, o in triple(pacchetto('elezione'), '<http://dati.camera.it/ocd/elezione.rdf/e'):
        m = re.search(r'/e(\d+)_(\d+)_', s)
        if m and int(m.group(1)) in ROMANI:
            voci[(m.group(2), ROMANI[int(m.group(1))])][p] = o
    fuori = {}
    for (pid, leg), v in voci.items():
        tipo = v.get('tipoElezione', '')
        if tipo.startswith('maggioritario'):
            luogo = 'collegio uninominale di %s' % bel_luogo(v.get('spatial'))
            if v.get('coverage'):
                luogo += ' (%s)' % bel_luogo(v['coverage'])
            if 'suppletiva' in tipo:
                luogo += ', elezione suppletiva'
        else:
            luogo = 'circoscrizione %s' % bel_luogo(v.get('coverage'))
        fuori.setdefault(pid, {})[leg] = [
            'M' if tipo.startswith('maggioritario') else 'P', luogo, v.get('lista') or '']
    return fuori


def ruoli_nei_gruppi():
    """{pid: [[legislatura, ruolo, gruppo, da, a]]}: presidente, vicepresidente,
    tesoriere, delegato d'aula, membro del direttivo, del proprio gruppo."""
    voci = collections.defaultdict(dict)
    for s, p, o in triple(pacchetto('incarico'), '<http://dati.camera.it/ocd/incarico.rdf/'):
        voci[s][p] = o
    fuori = {}
    for v in voci.values():
        m = re.search(r'/d(\d+)_(\d+)', v.get('rif_deputato', ''))
        if not m or int(m.group(2)) not in ROMANI:
            continue
        g = re.match(r'^.*? del gruppo (.+?), [A-ZÀ-Ü\' ]+\(', v.get('title', ''))
        ruolo = (v.get('ruolo') or '').strip()
        ruolo = {'MEMBRO DEL C.D.': 'membro del comitato direttivo',
                 'VICEPRES. VICARIO': 'vicepresidente vicario',
                 'SEGRETARIO AMM.': 'segretario amministrativo'}.get(ruolo, ruolo.lower())
        fuori.setdefault(m.group(1), []).append(
            [ROMANI[int(m.group(2))], ruolo, g.group(1).strip() if g else '',
             data(v.get('startDate')), data(v.get('endDate'))])
    for v in fuori.values():
        v.sort(key=lambda x: x[3] or '')
    return fuori


def fine_mandato():
    """{pid: [[legislatura, data, motivo]]}, solo per i mandati finiti prima
    del tempo: dimissioni, dimissioni per incompatibilita', decesso."""
    voci = collections.defaultdict(dict)
    for s, p, o in triple(pacchetto('mandatoCamera'), '<http://dati.camera.it/ocd/mandatoCamera.rdf/'):
        voci[s][p] = o
    fuori = {}
    for s, v in voci.items():
        m = re.search(r'/mc(\d+)_(\d+)_', s)
        motivo = v.get('motivoTermine', '')
        if not m or int(m.group(1)) not in ROMANI or not motivo:
            continue
        if motivo in ('Fine Legislatura', 'Scioglimento della Camera'):
            continue
        fuori.setdefault(m.group(2), []).append(
            [ROMANI[int(m.group(1))], data(v.get('endDate')),
             motivo.replace("incompatibilita'", 'incompatibilità')])
    return fuori


def _locale(tag):
    return tag.rsplit('}', 1)[-1]


def _figli(el, nome):
    return [x for x in el if _locale(x.tag) == nome]


def _testo(el, nome):
    f = _figli(el, nome)
    return (f[0].text or '').strip() if f else ''


def _pid(el):
    v = next((v for k, v in el.attrib.items() if k.endswith('resource')), '')
    m = re.search(r'/[dp](\d+)(?:_|$)', v)
    return m.group(1) if m else None


def titolo_proposta(t):
    """'ROSSI ed altri: Norme sul lavoro' -> 'Norme sul lavoro': chi la firma
    lo dice gia' la scheda."""
    t = re.sub(r'\s+', ' ', t or '').strip()
    m = re.match(r"^[A-ZÀ-Ü' .,-]+?(?: ed altri| e [A-ZÀ-Ü' .-]+)?: (.+)$", t)
    return (m.group(1) if m else t)[:240]


def proposte_camera():
    """{pid: {primo, cofirmate, governo, titoli}} dalla XII alla XVI.

    Solo i progetti di legge, e del progetto conta chi lo firma: le relazioni
    di commissione sono atti annidati con un loro primo firmatario, il
    relatore, e contarle gli darebbe la legge di un altro."""
    fuori = {}

    def conta(tipo, iniziativa, primi, altri, quando, titolo):
        if tipo != 'Progetto di Legge':
            return
        if iniziativa == 'Parlamentare':
            for p in filter(None, primi):
                v = fuori.setdefault(p, {})
                v['primo'] = v.get('primo', 0) + 1
                v.setdefault('titoli', []).append([quando, titolo_proposta(titolo)])
            for p in filter(None, altri):
                v = fuori.setdefault(p, {})
                v['cofirmate'] = v.get('cofirmate', 0) + 1
        else:
            for p in filter(None, primi):
                v = fuori.setdefault(p, {})
                v['governo'] = v.get('governo', 0) + 1

    numero = lambda u: (re.search(r'/[dp](\d+)(?:_|$)', u) or [None, None])[1]
    for n in ROMANI:
        testo = pacchetto('atto-%d' % n)
        # La Camera non usa lo stesso formato per tutte le legislature: la XV
        # arriva a righe di triple, le altre in XML.
        if testo.lstrip().startswith('<http'):
            atti = {}
            for s, p, o in triple(testo, '<http://dati.camera.it/ocd/attocamera.rdf/'):
                a = atti.setdefault(s, {'primi': [], 'altri': []})
                if p == 'primo_firmatario':
                    a['primi'].append(numero(o))
                elif p == 'altro_firmatario':
                    a['altri'].append(numero(o))
                elif p in ('type', 'iniziativa', 'date', 'title') and not o.startswith('http'):
                    # rdf:type e dc:type finiscono tutti e due in 'type': conta
                    # il secondo, che e' un testo ('Progetto di Legge')
                    a[p] = o
            for a in atti.values():
                conta(a.get('type'), a.get('iniziativa'), a['primi'], a['altri'],
                      data(a.get('date')) or '', a.get('title'))
            continue
        radice = ET.fromstring(testo.encode('utf-8'))
        for el in radice.iter():
            if _locale(el.tag) != 'atto':
                continue
            conta(_testo(el, 'type'), _testo(el, 'iniziativa'),
                  [_pid(x) for x in _figli(el, 'primo_firmatario')],
                  [_pid(x) for x in _figli(el, 'altro_firmatario')],
                  data(_testo(el, 'date')) or '', _testo(el, 'title'))
    for v in fuori.values():
        if v.get('titoli'):
            v['titoli'].sort()
    return fuori


# ------------------------------------------------------------------ Senato

P = '''PREFIX osr: <http://dati.senato.it/osr/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
'''


def intera(query):
    """Il Senato taglia a diecimila righe senza dirlo: una risposta che ci
    arriva e' una risposta tagliata, e non si usa."""
    righe = senato.interroga(query)
    if len(righe) >= 10000:
        raise RuntimeError('risposta del Senato tagliata a %d righe' % len(righe))
    return righe


def _v(r, k):
    return (r.get(k, {}).get('value') or '').strip()


def nomi_commissioni():
    """Come si chiamava ogni commissione, periodo per periodo."""
    nomi = {}
    for r in intera(P + '''SELECT ?co ?t ?b ?di ?df WHERE {
      ?co a osr:Commissione .
      { ?co osr:denominazione ?d . ?d osr:titolo ?t .
        OPTIONAL { ?d osr:titoloBreve ?b } OPTIONAL { ?d osr:inizio ?di } OPTIONAL { ?d osr:fine ?df } }
      UNION { ?co osr:titolo ?t . OPTIONAL { ?co osr:titoloBreve ?b } } }'''):
        nomi.setdefault(_v(r, 'co'), []).append(
            (_v(r, 'di')[:10], _v(r, 'df')[:10], _v(r, 't'), _v(r, 'b')))
    return nomi


def nome_commissione(nomi, co, giorno):
    validi = [n for n in nomi.get(co, []) if not (n[0] and giorno and n[0] > giorno)
              and not (n[1] and giorno and n[1] < giorno)] or nomi.get(co, [])
    if not validi:
        return ''
    _, _, titolo, breve = validi[0]
    if 'permanente' in titolo.lower() and breve:
        return '%s (%s)' % (titolo, breve)
    return titolo


def incarichi_senato():
    """{uri senatore: {legislatura: [[RUOLO, ORGANO]]}}, nello stesso formato
    degli incarichi della Camera: presidenze, vicepresidenze e segreterie di
    commissione, e la Presidenza del Senato con vicepresidenti, questori e
    segretari."""
    nomi = nomi_commissioni()
    fuori = {}

    def metti(s, leg, ruolo, organo):
        if leg not in ROMANI or not organo:
            return
        voce = [ruolo.upper(), organo.upper()]
        lista = fuori.setdefault(s, {}).setdefault(ROMANI[leg], [])
        if voce not in lista:
            lista.append(voce)

    for n in ROMANI:
        time.sleep(0.5)
        for r in intera(P + '''SELECT ?s ?c ?co ?i WHERE {
          ?s a osr:Senatore ; osr:afferisce ?a .
          ?a osr:carica ?c ; osr:legislatura %d ; osr:commissione ?co ; osr:inizio ?i .
          FILTER(STR(?c) != "Membro") }''' % n):
            metti(_v(r, 's'), n, _v(r, 'c'),
                  nome_commissione(nomi, _v(r, 'co'), _v(r, 'i')[:10]))
    time.sleep(0.5)
    # La Presidenza: l'organo porta la legislatura nell'indirizzo, .../presidenza/14
    for r in intera(P + '''SELECT ?s ?o ?c WHERE {
      ?s a osr:Senatore ; osr:afferisce ?a . ?a osr:organo ?o ; osr:carica ?c .
      FILTER(CONTAINS(STR(?c), "Senato")) }'''):
        try:
            leg = int(_v(r, 'o').rstrip('/').rsplit('/', 1)[-1])
        except ValueError:
            continue
        c = _v(r, 'c')
        ruolo = {'Presidente del Senato': 'PRESIDENTE', 'Vice Presidente del Senato': 'VICEPRESIDENTE',
                 'Questore del Senato': 'QUESTORE', 'Segretario del Senato': 'SEGRETARIO'}.get(c)
        if ruolo:
            metti(_v(r, 's'), leg, ruolo,
                  'PRESIDENZA DEL SENATO' if ruolo == 'PRESIDENTE' else 'UFFICIO DI PRESIDENZA')
    return fuori


def professioni_senato():
    fuori = {}
    for n in ROMANI:
        time.sleep(0.5)
        for r in intera(P + '''SELECT DISTINCT ?s ?prof WHERE {
          ?s a osr:Senatore ; osr:mandato ?m ; osr:professione ?x .
          ?m osr:legislatura %d . ?x rdfs:label ?prof }''' % n):
            fuori.setdefault(_v(r, 's'), set()).add(_v(r, 'prof'))
    return {s: '; '.join(sorted(v)) for s, v in fuori.items()}


def proposte_senato():
    """{uri senatore: {primo, cofirmate, titoli}} dalla XIII alla XVI: della
    XII negli open data del Senato non c'e' traccia. Solo i disegni di legge
    presentati al Senato: quelli trasmessi dalla Camera li conta la Camera."""
    fuori = {}
    visti = set()

    def fetta(n, da, a):
        """Una fetta di date. Il Senato non ha archivi interi da scaricare: la
        sua pagina "Scarica i dati" lancia le stesse interrogazioni, divise
        per date. Una legislatura intera, ordinata e sfogliata, gli manda il
        server in errore; un anno alla volta no. Se una fetta arriva al tetto
        di diecimila righe, la si divide a meta'."""
        try:
            return intera(P + '''SELECT ?id ?sen ?primo ?t ?d WHERE {
              ?ddl a osr:Ddl ; osr:legislatura %d ; osr:ramo ?ramo ;
                   osr:presentatoTrasmesso ?pt ; osr:idDdl ?id ; osr:titolo ?t ;
                   osr:dataPresentazione ?d ; osr:iniziativa ?i .
              ?i osr:senatore ?sen . OPTIONAL { ?i osr:primoFirmatario ?primo }
              FILTER(STR(?ramo) = "S" && STR(?pt) = "presentato"
                     && STR(?d) >= "%s" && STR(?d) < "%s") }''' % (n, da, a))
        except RuntimeError:
            import datetime
            g = lambda s: datetime.date(int(s[:4]), int(s[5:7]), int(s[8:10]))
            meta = (g(da) + (g(a) - g(da)) / 2).isoformat()
            return fetta(n, da, meta) + fetta(n, meta, a)

    for n in (13, 14, 15, 16):
        for anno in range(1996, 2014):
            time.sleep(0.4)
            righe = fetta(n, '%d-01-01' % anno, '%d-01-01' % (anno + 1))
            for r in righe:
                chiave = (_v(r, 'id'), _v(r, 'sen'))
                if chiave in visti:
                    continue
                visti.add(chiave)
                v = fuori.setdefault(_v(r, 'sen'), {})
                if _v(r, 'primo') == '1':
                    v['primo'] = v.get('primo', 0) + 1
                    v.setdefault('titoli', []).append([_v(r, 'd')[:10], _v(r, 't')[:240]])
                else:
                    v['cofirmate'] = v.get('cofirmate', 0) + 1
    for v in fuori.values():
        if v.get('titoli'):
            v['titoli'].sort()
    return fuori


# ------------------------------------------------------------------ aggancio

def aggancia(persone, anagrafe):
    """La voce d'anagrafe della Camera di ogni scheda. Chi e' passato dalla
    Camera ha gia' il suo identificativo, ed e' lo stesso. Per gli altri,
    senatori e ministri senza seggio alla Camera, nome piu' una legislatura o
    un governo in comune; due omonimi possibili, nessun aggancio."""
    per_nome = {}
    for pid, v in anagrafe.items():
        per_nome.setdefault(camera.chiave(v['nome'], v['cognome']), []).append(pid)
    fuori = {}
    for p in persone:
        if p.get('id_camera') in anagrafe:
            fuori[p['qid']] = p['id_camera']
            continue
        miei = {m.replace('Governo ', '') for m in p['mandati']}
        nome = re.sub(r'\s*\([^)]*\)', '', p['nome'] or '')
        candidati = [c for c in per_nome.get(camera.chiave(nome), [])
                     if miei & (set(anagrafe[c]['leg']) | set(anagrafe[c]['governi']))]
        if len(candidati) == 1:
            fuori[p['qid']] = candidati[0]
    return fuori


def main():
    persone = json.load(open(ELENCO, encoding='utf-8'))['persone']

    print('Camera: anagrafe e governi...')
    anagrafe = anagrafe_camera()
    pid_di = aggancia(persone, anagrafe)
    print('  %d schede legate all\'anagrafe della Camera' % len(pid_di))
    print('Camera: proposte di legge...')
    prop_c = proposte_camera()
    print('Camera: elezioni, ruoli nei gruppi, fine dei mandati...')
    elez = elezioni_camera()
    ruoli = ruoli_nei_gruppi()
    fine = fine_mandato()
    print('Senato: incarichi...')
    inc_s = incarichi_senato()
    print('Senato: professioni...')
    prof_s = professioni_senato()
    print('Senato: proposte di legge...')
    prop_s = proposte_senato()

    fuori = {}
    for p in persone:
        x = {}
        pid = pid_di.get(p['qid'])
        a = anagrafe.get(pid) if pid else None
        s = p.get('id_senato')
        # studi e professione: la Camera, e per chi alla Camera non c'e' la
        # professione che dichiara il Senato
        if a and a.get('studi'):
            x['studi'] = a['studi']
        elif s and prof_s.get(s):
            x['studi'] = prof_s[s]
        if a and a.get('governo'):
            x['governo'] = a['governo']
        c = p.get('id_camera')
        if c and elez.get(c):
            x['elezioni'] = elez[c]
        if c and ruoli.get(c):
            x['ruoli_gruppo'] = ruoli[c]
        if c and fine.get(c):
            x['fine_mandato'] = fine[c]
        if s and inc_s.get(s):
            x['incarichi_senato'] = inc_s[s]
        prop = {}
        if p.get('id_camera') and prop_c.get(p['id_camera']):
            prop['C'] = prop_c[p['id_camera']]
        if s and prop_s.get(s):
            prop['S'] = prop_s[s]
        if prop:
            x['proposte'] = prop
        if x:
            fuori[p['qid']] = x

    conta = lambda campo: sum(1 for v in fuori.values() if campo in v)
    print()
    print('schede arricchite: %d su %d' % (len(fuori), len(persone)))
    for campo in ('studi', 'governo', 'elezioni', 'ruoli_gruppo', 'fine_mandato',
                  'incarichi_senato', 'proposte'):
        print('  %-18s %d' % (campo, conta(campo)))
    json.dump({'_nota': 'Primo giro di arricchimento: studi e professione, incarichi di '
                        'governo (Camera, membroGoverno), incarichi interni al Senato, '
                        'proposte di legge (Camera dai pacchetti atto-12..16, Senato dalla '
                        'XIII). Generato da scripts/arricchisci.py.',
               'schede': fuori},
              open(USCITA, 'w', encoding='utf-8', newline='\n'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
