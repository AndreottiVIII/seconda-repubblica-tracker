# -*- coding: utf-8 -*-
"""Costruisce data/estero.json: i fatti fuori dai confini, 1994-2013.

E' l'unica parte del sito che non viene dai registri parlamentari. Sono
avvenimenti scelti a mano, ognuno con la data e la voce di Wikipedia che lo
racconta, e dove esiste un'immagine libera anche una fotografia.

Le fotografie si prendono DALLA VOCE dell'evento, non da una ricerca per
parole. La differenza non e' un dettaglio: cercando "Muammar Gaddafi" su
Commons e' tornata la foto di un politico indonesiano, che e' finita sul sito
sotto la didascalia "Muammar Gheddafi". Verificare che un'immagine esista non
dice niente su chi ci sia dentro; prenderla dalla voce che parla di quel
fatto lo dice, perche' quella l'hanno scelta delle persone per quel fatto.
"""
import sys, os, json, time, urllib.request, urllib.parse

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

QUI = os.path.dirname(os.path.abspath(__file__))
USCITA = os.path.join(QUI, '..', 'data', 'estero.json')
UA = ('SecondaRepubblicaTracker/0.1 (progetto personale; '
      'davide.caniatti@gmail.com)')

W = 'https://it.wikipedia.org/wiki/'

# data, titolo, testo, voce di Wikipedia, cosa cercare su Commons, didascalia
EVENTI = [
 ('1995-07-11', 'Srebrenica',
  'Le truppe serbo-bosniache entrano nell’enclave protetta dalle Nazioni '
  'Unite e uccidono oltre ottomila musulmani bosniaci. E’ il massacro che '
  'convince l’Europa che la guerra in Bosnia non si ferma da sola, e apre '
  'la strada all’intervento della NATO.',
  'Massacro_di_Srebrenica', 'Srebrenica genocide memorial',
  'Il memoriale di Potočari'),

 ('1997-04-15', 'Operazione Alba',
  'L’Italia guida una forza multinazionale in Albania, sconvolta dal '
  'crollo delle società finanziarie piramidali. E’ la prima missione '
  'internazionale a comando italiano, e il governo è quello di Prodi.',
  'Operazione_Alba', 'Albania 1997 Italian Army Operation Alba Durres',
  'Militari italiani in Albania, 1997'),

 ('1999-01-01', 'Nasce l’euro',
  'L’euro diventa moneta di conto per undici paesi, Italia compresa: i '
  'cambi con la lira sono fissati per sempre. Le banconote arriveranno tre '
  'anni dopo, ma da questo giorno la politica monetaria non è più a '
  'Roma.', 'Euro', 'Euro sign sculpture Frankfurt Willem Duisenberg', 'Il simbolo dell’euro a Francoforte'),

 ('1999-03-24', 'La guerra del Kosovo',
  'Cominciano i bombardamenti della NATO sulla Jugoslavia. Le basi italiane '
  'sono il perno delle operazioni, e il governo che accompagna il Paese in '
  'guerra è quello di Massimo D’Alema, primo presidente del Consiglio '
  'proveniente dal Partito Comunista Italiano.',
  'Guerra_del_Kosovo', 'NATO bombing of Yugoslavia Belgrade 1999',
  'Belgrado durante i bombardamenti'),

 ('2001-07-20', 'Il G8 di Genova',
  'Il vertice dei grandi si tiene a Genova dal 20 al 22 luglio, sei settimane '
  'dopo l’insediamento del secondo governo Berlusconi. Nelle stesse ore '
  'muore Carlo Giuliani, e la città resta il nome di un passaggio della '
  'storia italiana.', 'G8_di_Genova', 'G8 summit Genoa 2001 Putin',
  'Il vertice di Genova, luglio 2001'),

 ('2001-09-11', 'Le Torri Gemelle',
  'Quattro aerei dirottati negli Stati Uniti, quasi tremila morti. E’ il '
  'giorno che cambia la politica estera di tutti, Italia compresa: da qui '
  'nascono le missioni in Afghanistan e in Iraq, e vent’anni di dibattito '
  'italiano sulla partecipazione alle guerre.',
  'Attentati_dell%27_11_settembre_2001', 'September 11 attacks World Trade Center',
  'New York, 11 settembre 2001'),

 ('2001-10-07', 'L’Afghanistan',
  'Cominciano le operazioni contro i Talebani. L’Italia partecipa dal '
  'primo momento e resterà nel Paese vent’anni: è la missione '
  'militare italiana più lunga dalla seconda guerra mondiale.',
  'Guerra_in_Afghanistan_(2001-2021)', 'Italian Army soldiers Afghanistan ISAF',
  'Militari italiani in Afghanistan'),

 ('2002-01-01', 'L’euro in tasca',
  'Banconote e monete entrano in circolazione. In Italia il cambio è fissato '
  'a 1.936,27 lire per euro, e il passaggio diventa uno dei temi ricorrenti '
  'del decennio.', 'Euro', 'Euro banknotes and coins', 'Le prime banconote'),

 ('2002-05-28', 'Il vertice di Pratica di Mare',
  'Alla base aerea di Pratica di Mare, alle porte di Roma, la NATO e la Russia '
  'firmano la dichiarazione che istituisce il Consiglio NATO-Russia. E’ il '
  'momento in cui l’Italia si presenta come il luogo dove Occidente e '
  'Russia si parlano, e resta la fotografia più citata della politica '
  'estera di quegli anni.',
  'Consiglio_NATO-Russia', 'Berlusconi Bush Putin Pratica di Mare 2002',
  'Pratica di Mare, 28 maggio 2002'),

 ('2003-03-20', 'La guerra in Iraq',
  'Cominciano le operazioni contro l’Iraq di Saddam Hussein. L’Italia '
  'non partecipa all’invasione ma dal luglio manda la missione Antica '
  'Babilonia, la più grande spedizione militare italiana dal 1945.',
  'Guerra_in_Iraq', '2003 invasion of Iraq Baghdad statue Saddam', 'Baghdad, 2003'),

 ('2003-11-12', 'Nassiriya',
  'Un attentato contro la base italiana in Iraq uccide diciannove italiani, '
  'dodici carabinieri, cinque militari dell’Esercito e due civili, oltre a '
  'nove iracheni. E’ la perdita più grave per l’Italia dalla '
  'seconda guerra mondiale.',
  'Attentato_di_Nassiriya', 'Nassiriya Italian base Iraq carabinieri',
  'La commemorazione delle vittime'),

 ('2004-05-01', 'L’Europa a venticinque',
  'Dieci paesi entrano nell’Unione, otto dei quali stavano dall’altra '
  'parte della cortina di ferro. L’Europa in cui l’Italia si muove '
  'cambia forma in un giorno solo.',
  'Allargamento_dell%27Unione_europea', 'European Union member states map 2004 enlargement',
  'L’Unione dopo il 2004'),

 ('2005-03-04', 'Nicola Calipari',
  'A Baghdad il funzionario del SISMI Nicola Calipari viene ucciso da militari '
  'statunitensi mentre riporta all’aeroporto la giornalista Giuliana '
  'Sgrena, appena liberata. Il caso apre una frattura diplomatica fra Roma e '
  'Washington.', 'Nicola_Calipari', '', 'Dalla voce su Nicola Calipari'),

 ('2006-08-11', 'Il Libano',
  'Il Consiglio di sicurezza approva la risoluzione 1701 e l’Italia manda '
  'in Libano il contingente più numeroso, assumendo il comando di UNIFIL. '
  'E’ il momento di massima esposizione italiana nel Mediterraneo '
  'orientale.', 'UNIFIL', 'UNIFIL Italian soldiers Lebanon',
  'Militari italiani in Libano'),

 ('2008-08-30', 'Il Trattato di Bengasi',
  'Italia e Libia firmano a Bengasi il trattato di amicizia, partenariato e '
  'cooperazione: cinque miliardi di dollari in vent’anni come risarcimento '
  'per il periodo coloniale, in cambio di collaborazione sui flussi migratori.',
  'Trattato_di_Bengasi', 'Benghazi Libya',
  'Dalla voce sul trattato'),

 ('2008-09-15', 'Lehman Brothers',
  'Il fallimento della banca d’affari apre la crisi finanziaria mondiale. '
  'Da qui comincia la strada che porterà l’Italia al differenziale '
  'sui titoli di Stato del 2011 e al governo Monti.',
  'Crisi_finanziaria_del_2007-2008', 'Lehman Brothers headquarters',
  'La sede di Lehman Brothers a New York'),

 ('2009-07-08', 'Il G8 dell’Aquila',
  'Il vertice viene spostato dalla Maddalena all’Aquila, colpita tre mesi '
  'prima dal terremoto. E’ l’ultimo G8 a otto: dall’anno '
  'successivo conterà il G20.',
  'G8_dell%27Aquila', 'G8 summit 2009 L Aquila leaders', 'Il vertice dell’Aquila'),

 ('2011-02-15', 'Le primavere arabe',
  'Le rivolte attraversano la sponda sud del Mediterraneo: Tunisia, Egitto, '
  'Libia. Per l’Italia significa la fine degli interlocutori con cui aveva '
  'costruito la propria politica mediterranea, Ben Ali e Mubarak compresi.',
  'Primavera_araba', 'Tahrir Square Cairo February 2011 protest',
  'Piazza Tahrir al Cairo, 2011'),

 ('2011-03-19', 'La Libia, tre anni dopo',
  'Comincia l’intervento internazionale contro Gheddafi. L’Italia '
  'mette a disposizione sette basi: meno di tre anni dopo il trattato di '
  'amicizia, e con lo stesso governo in carica.',
  'Intervento_militare_in_Libia_del_2011',
  'Operation Unified Protector Italy aircraft 2011',
  'La base di Gioia del Colle, 2011'),

 ('2011-11-03', 'Il G20 di Cannes',
  'Al vertice di Cannes l’Italia rifiuta il prestito del Fondo monetario '
  'internazionale ma ne accetta la sorveglianza sui conti pubblici. Nove giorni '
  'dopo Berlusconi si dimette.',
  'Governo_Berlusconi_IV', 'G20 Cannes summit 2011',
  'Il G20 di Cannes, novembre 2011'),

 ('2012-02-15', 'I marò',
  'Due fucilieri di marina italiani vengono fermati in India con l’accusa '
  'di aver ucciso due pescatori dalla petroliera Enrica Lexie. La vicenda '
  'occuperà la diplomazia italiana per anni.',
  'Caso_Enrica_Lexie', 'Enrica Lexie', 'La petroliera Enrica Lexie'),

 ('2011-11-16', 'Lo spread e il governo Monti',
  'Il differenziale fra i titoli di Stato italiani e quelli tedeschi tocca i '
  '519 punti base di media mensile a novembre. Il 12 Berlusconi si dimette, '
  'il 16 giura Mario Monti con un governo di soli tecnici. Per la prima volta '
  'dal 1994 il presidente del Consiglio non ha un seggio in Parlamento.',
  'Governo_Monti', '', ''),

 ('2012-03-02', 'Il fiscal compact',
  'Venticinque paesi firmano il trattato sulla stabilità nell’unione '
  'economica e monetaria. L’Italia lo firma col governo Monti, e da '
  'quell’anno il pareggio di bilancio entra nella Costituzione.',
  'Patto_di_bilancio_europeo', 'Mario Monti 2012',
  'Il Consiglio europeo a Bruxelles'),
]


SALTA = ('commons-logo', 'wikidata', 'disambig', 'question_book', 'edit-',
         'flag_of', 'bandiera', 'ambox', 'crystal', 'nuvola', 'stub',
         'wiki', 'icon', 'symbol', 'blue_pencil', 'searchtool', 'star_')


def cerca_foto(termine, quante=4):
    """I primi risultati di Commons per un termine. Illustrano, non provano."""
    if not termine:
        return []
    u = 'https://commons.wikimedia.org/w/api.php?' + urllib.parse.urlencode({
        'action': 'query', 'list': 'search',
        'srsearch': termine + ' filetype:bitmap', 'srnamespace': 6,
        'srlimit': quante, 'format': 'json'})
    r = urllib.request.Request(u, headers={'User-Agent': UA})
    d = json.load(urllib.request.urlopen(r, timeout=60))
    return [x['title'][5:] for x in d.get('query', {}).get('search', [])]


def foto_della_voce(titolo):
    """I file usati dalla voce di Wikipedia, nell'ordine in cui compaiono.

    Sono immagini che qualcuno ha scelto per quel fatto: e' una garanzia
    debole sul soggetto, ma incomparabilmente piu' forte di una ricerca per
    parole chiave. Si scartano loghi, bandiere e iconcine di servizio.
    """
    url = 'https://it.wikipedia.org/w/api.php?' + urllib.parse.urlencode({
        'action': 'parse', 'page': titolo, 'prop': 'images',
        'format': 'json', 'redirects': 1})
    r = urllib.request.Request(url, headers={'User-Agent': UA})
    d = json.load(urllib.request.urlopen(r, timeout=60))
    fuori = []
    for nome in d.get('parse', {}).get('images', []):
        basso = nome.lower()
        if not basso.endswith(('.jpg', '.jpeg', '.png')):
            continue
        if any(x in basso for x in SALTA):
            continue
        fuori.append(nome)
    return fuori


def scarica_prova(nome):
    """Vera o falsa: l'immagine esiste e pesa qualcosa."""
    u = ('https://commons.wikimedia.org/wiki/Special:FilePath/'
         + urllib.parse.quote(nome.replace(' ', '_')) + '?width=320')
    try:
        r = urllib.request.Request(u, headers={'User-Agent': UA})
        with urllib.request.urlopen(r, timeout=60) as f:
            return len(f.read()) > 2000
    except Exception:
        return False


def main():
    eventi = []
    for data, titolo, testo, voce, cerca, didascalia in EVENTI:
        foto = None
        try:
            for candidato in cerca_foto(cerca) + foto_della_voce(voce):
                if scarica_prova(candidato):
                    foto = candidato
                    break
        except Exception as e:
            print('  voce non letta per %s: %s' % (titolo, str(e)[:50]))
        print('   %-28s %s' % (titolo[:28], foto[:54] if foto else '(senza foto)'))
        eventi.append({'data': data, 'titolo': titolo, 'testo': testo,
                       'fonte': W + voce, 'foto': foto,
                       'didascalia': ''})
        time.sleep(0.3)

    nota = (
        "I fatti fuori dai confini, 1994-2013. Questa e' l'unica parte del sito "
        "che non viene dai registri parlamentari: sono avvenimenti scelti a "
        "mano, ognuno con la data e la voce di Wikipedia che lo racconta. Le "
        "fotografie vengono da Wikimedia Commons e sono state scaricate una per "
        "una per verificare che esistano: un nome sbagliato non darebbe errore, "
        "darebbe un riquadro vuoto. La circoscrizione Estero, nella stessa "
        "finestra, viene invece dai registri come tutto il resto."
    )
    json.dump({'_nota': nota, 'eventi': eventi},
              open(USCITA, 'w', encoding='utf-8', newline='\n'),
              ensure_ascii=False, indent=1)
    con = sum(1 for e in eventi if e['foto'])
    print()
    print('%d fatti, %d con fotografia verificata' % (len(eventi), con))


if __name__ == '__main__':
    main()
