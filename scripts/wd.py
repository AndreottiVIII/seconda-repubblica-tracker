"""Utility minime per parlare con Wikidata (API + SPARQL)."""
import urllib.request, urllib.parse, json, time, sys

UA = 'DuriAMorire/0.1 (progetto personale; davide.caniatti@gmail.com) python-urllib'


def _get(url, tries=5):
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': UA})
            return json.load(urllib.request.urlopen(req, timeout=60))
        except Exception as e:
            last = e
            time.sleep(3 * (i + 1))
    raise last


def cerca(nome, limit=10):
    """wbsearchentities: restituisce gli id candidati per un nome."""
    url = 'https://www.wikidata.org/w/api.php?' + urllib.parse.urlencode({
        'action': 'wbsearchentities', 'search': nome, 'language': 'it',
        'uselang': 'it', 'format': 'json', 'limit': limit, 'type': 'item'})
    return [r['id'] for r in _get(url).get('search', [])]


def entita(ids):
    """wbgetentities a blocchi di 50: claims + label italiana."""
    out = {}
    for i in range(0, len(ids), 50):
        blocco = ids[i:i + 50]
        url = 'https://www.wikidata.org/w/api.php?' + urllib.parse.urlencode({
            'action': 'wbgetentities', 'ids': '|'.join(blocco),
            'props': 'claims|labels|sitelinks', 'languages': 'it|en',
            'sitefilter': 'itwiki', 'format': 'json'})
        out.update(_get(url).get('entities', {}))
        time.sleep(0.3)
    return out


def valori(ent, prop):
    return [c['mainsnak']['datavalue']['value']
            for c in ent.get('claims', {}).get(prop, [])
            if c['mainsnak'].get('snaktype') == 'value']


def data_di(ent, prop):
    """Estrae 'YYYY-MM-DD' (o 'YYYY' se il giorno non e' noto) da P569/P570."""
    for v in valori(ent, prop):
        t, prec = v['time'], v.get('precision', 11)
        anno, mese, giorno = t[1:5], t[6:8], t[9:11]
        if prec >= 11 and mese != '00' and giorno != '00':
            return '%s-%s-%s' % (anno, mese, giorno)
        if prec == 10 and mese != '00':
            return '%s-%s' % (anno, mese)
        return anno
    return None


def etichetta(ent):
    lab = ent.get('labels', {})
    return (lab.get('it') or lab.get('en') or {}).get('value')


SPARQL = 'https://query.wikidata.org/sparql'


def sparql(query, tries=6):
    """POST su WDQS con backoff: l'endpoint pubblico rifiuta a raffica."""
    data = urllib.parse.urlencode({'query': query}).encode()
    last = None
    for i in range(tries):
        try:
            req = urllib.request.Request(SPARQL, data=data, headers={
                'User-Agent': UA, 'Accept': 'application/sparql-results+json',
                'Content-Type': 'application/x-www-form-urlencoded'})
            return json.load(urllib.request.urlopen(req, timeout=300))['results']['bindings']
        except Exception as e:
            last = e
            sys.stderr.write('  ritento (%d): %s\n' % (i + 1, e))
            time.sleep(5 * (i + 1))
    raise last


def v(riga, campo):
    """Valore di una colonna SPARQL, None se assente."""
    x = riga.get(campo)
    return x['value'] if x else None


def qid(riga, campo):
    x = v(riga, campo)
    return x.rsplit('/', 1)[-1] if x else None
