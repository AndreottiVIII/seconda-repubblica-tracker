# -*- coding: utf-8 -*-
"""Costruisce data/partiti.json: dal gruppo parlamentare al partito.

I nomi dei gruppi sono quelli che scrivono i registri, presi uno per uno dalle
cinque legislature e dai due rami: 135 righe in tutto. Sono elencati per esteso
apposta, invece di essere indovinati da una regola: una regola che sbaglia
sbaglia in silenzio, un elenco sbagliato si vede e si corregge.

Le successioni ('eredita_da') dicono di chi un partito e' erede legittimo. Un
passaggio verso un erede non e' un cambio di casacca: e' il partito che si e'
mosso, non la persona. Sono state ricavate dai passaggi di massa fra una
legislatura e l'altra, non dalla memoria: quando l'88% di chi usciva dai DS
entra nel gruppo successivo, non e' una scelta individuale.
"""
import sys, json, os

sys.stdout.reconfigure(encoding='utf-8', errors='replace')

QUI = os.path.dirname(os.path.abspath(__file__))
USCITA = os.path.join(QUI, '..', 'data', 'partiti.json')

# codice: (nome per esteso, colore, di chi e' erede)
PARTITI = {
    'PDS':        ("Partito Democratico della Sinistra", "#E2001A", []),
    'DS':         ("Democratici di Sinistra", "#D8001C", ["PDS"]),
    'PD':         ("Partito Democratico", "#EF3340", ["DS", "MARGHERITA"]),
    'SD':         ("Sinistra Democratica per il Socialismo Europeo", "#C8102E", ["DS"]),
    'SIN-IND':    ("Sinistra Democratica (indipendenti)", "#B03060", []),
    'PRC':        ("Partito della Rifondazione Comunista", "#B80000", []),
    'PDCI':       ("Partito dei Comunisti Italiani", "#A00000", ["PRC"]),
    'VERDI':      ("Federazione dei Verdi", "#7AC943", []),
    'ROSA':       ("La Rosa nel Pugno / Socialisti e Radicali", "#E6007E", []),
    'PSI-PROG':   ("Progressisti PSI", "#F4436C", []),
    'IU':         ("Insieme con l'Unione (Verdi e Comunisti)", "#8FBC5A",
                   ["VERDI", "PDCI"]),
    'PPI':        ("Partito Popolare Italiano", "#0F8C8C", []),
    'MARGHERITA': ("La Margherita - Democrazia e Libertà", "#F0A30A",
                   ["PPI", "DEM"]),
    'DEM':        ("I Democratici", "#F4A300", []),
    'RINN':       ("Rinnovamento Italiano", "#FFD24C", []),
    'CCD':        ("Centro Cristiano Democratico", "#1C90D4", []),
    'CDU':        ("Cristiani Democratici Uniti", "#5BB6E8", []),
    'UDR':        ("Unione Democratica per la Repubblica", "#9BC53D",
                   ["CCD", "CDU"]),
    'UDEUR':      ("Unione Democratici per l'Europa", "#8DB600", ["UDR"]),
    'UDC':        ("Unione di Centro", "#0E7AC4", ["CCD", "CDU"]),
    'DE':         ("Democrazia Europea", "#66A3D2", []),
    'DCA':        ("Democrazia Cristiana per le Autonomie - Nuovo PSI",
                   "#B0B0B0", []),
    'FI':         ("Forza Italia", "#005BAA", []),
    'AN':         ("Alleanza Nazionale", "#1560BD", []),
    'PDL':        ("Il Popolo della Libertà", "#0F52BA", ["FI", "AN"]),
    'FLI':        ("Futuro e Libertà per l'Italia", "#00A0B0", ["PDL"]),
    'RESP':       ("I Responsabili / Popolo e Territorio", "#7B68A6", []),
    'CN':         ("Coesione Nazionale", "#8A7CA8", []),
    'CDN':        ("Centro Destra Nazionale", "#6A5ACD", []),
    'LEGA':       ("Lega Nord", "#009933", []),
    'LEGA-FED':   ("Lega Italiana Federalista / Federalisti e Liberaldemocratici",
                   "#66CC66", ["LEGA"]),
    'IDV':        ("Italia dei Valori", "#FF7900", []),
    'AUT':        ("Autonomie (SVP, Valle d'Aosta, minoranze linguistiche)",
                   "#A0522D", []),
    'MISTO':      ("Gruppo misto", "#808080", []),
}

# (legislatura, ramo): {nome del gruppo come lo scrive il registro: partito}
GRUPPI = {
    ('XII', 'C'): {
        'PROGRESSISTI - FEDERATIVO': 'PDS',
        'FORZA ITALIA': 'FI',
        'LEGA NORD': 'LEGA',
        'ALLEANZA NAZIONALE': 'AN',
        'MISTO': 'MISTO',
        'FEDERALISTI E LIBERALDEMOCRATICI': 'LEGA-FED',
        'CENTRO CRISTIANO DEMOCRATICO': 'CCD',
        'RIFONDAZIONE COMUNISTA - PROGRESSISTI': 'PRC',
        'PARTITO POPOLARE ITALIANO': 'PPI',
        'I DEMOCRATICI': 'DEM',
        'LEGA ITALIANA FEDERALISTA': 'LEGA-FED',
    },
    ('XII', 'S'): {
        'Progr. Feder.': 'PDS',
        'Lega Nord': 'LEGA',
        'AN-MSI': 'AN',
        'FI': 'FI',
        'Misto': 'MISTO',
        'PPI': 'PPI',
        'Rif.Com.-Progr.': 'PRC',
        'CCD': 'CCD',
        'Pr. Verdi-Rete': 'VERDI',
        'Scudo Crociato': 'CDU',
        'Sinistra Dem.': 'SIN-IND',
        'Lega Federal.': 'LEGA-FED',
        'Progr. PSI': 'PSI-PROG',
        'LIF': 'LEGA-FED',
        'AN': 'AN',
        'CDU': 'CDU',
    },
    ('XIII', 'C'): {
        "DEMOCRATICI DI SINISTRA - L'ULIVO": 'DS',
        'MISTO': 'MISTO',
        'FORZA ITALIA': 'FI',
        'ALLEANZA NAZIONALE': 'AN',
        "POPOLARI DEMOCRATICI - L'ULIVO": 'PPI',
        'LEGA NORD PADANIA': 'LEGA',
        'CENTRO CRISTIANO DEMOCRATICO': 'CCD',
        'RINNOVAMENTO ITALIANO': 'RINN',
        'UDR - UNIONE DEMOCRATICA PER LA REPUBBLICA': 'UDR',
        "UNIONE DEMOCRATICA PER L'EUROPA": 'UDEUR',
        "DEMOCRATICI - L'ULIVO": 'DEM',
        'COMUNISTA': 'PDCI',
    },
    ('XIII', 'S'): {
        'Sin.Dem.-Ulivo': 'DS',
        'Misto': 'MISTO',
        'FI': 'FI',
        'AN': 'AN',
        'PPI': 'PPI',
        'Lega': 'LEGA',
        'CCD': 'CCD',
        'Verdi-U': 'VERDI',
        'Rin.Ld.Ind-Pop.': 'RINN',
        'Rinn. Ital. e Ind.': 'RINN',
        'Rinnovam. Ital.': 'RINN',
        'Rif.Com.-Progr.': 'PRC',
        'CDU': 'CDU',
        'Democrazia Europea': 'DE',
        'DS-U': 'DS',
        'UDR(CDU-CDR-NI)': 'UDR',
        'CDU-CDR': 'CDU',
        'UDR': 'UDR',
        'CCD-CDL': 'CCD',
        'UDeuR': 'UDEUR',
        'UDEUR': 'UDEUR',
        'Lega Forza Padania': 'LEGA',
        'Lega Nord': 'LEGA',
    },
    ('XIV', 'C'): {
        'FORZA ITALIA': 'FI',
        "DEMOCRATICI DI SINISTRA-L'ULIVO": 'DS',
        'ALLEANZA NAZIONALE': 'AN',
        "MARGHERITA, DL-L'ULIVO": 'MARGHERITA',
        'MISTO': 'MISTO',
        'UDC UNIONE DEI DEMOCRATICI CRISTIANI E DEI DEMOCRATICI DI CENTRO '
        '(CCD-CDU)': 'UDC',
        'LEGA NORD FEDERAZIONE PADANA': 'LEGA',
        'RIFONDAZIONE COMUNISTA': 'PRC',
    },
    ('XIV', 'S'): {
        'FI': 'FI',
        'DS-U': 'DS',
        'AN': 'AN',
        'Misto': 'MISTO',
        'Mar': 'MARGHERITA',
        'CCD-CDU:BF': 'UDC',
        'LNP': 'LEGA',
        'Aut': 'AUT',
        'Verdi-U': 'VERDI',
        'Mar-DL-U': 'MARGHERITA',
        'UDC': 'UDC',
        'Verdi-Un': 'VERDI',
    },
    ('XV', 'C'): {
        "PARTITO DEMOCRATICO-L'ULIVO": 'PD',
        'FORZA ITALIA': 'FI',
        'MISTO': 'MISTO',
        'ALLEANZA NAZIONALE': 'AN',
        'RIFONDAZIONE COMUNISTA - SINISTRA EUROPEA': 'PRC',
        'UDC (UNIONE DEI DEMOCRATICI CRISTIANI E DEI DEMOCRATICI DI CENTRO)':
            'UDC',
        'SINISTRA DEMOCRATICA. PER IL SOCIALISMO EUROPEO': 'SD',
        'LEGA NORD PADANIA': 'LEGA',
        'SOCIALISTI E RADICALI-RNP': 'ROSA',
        'ITALIA DEI VALORI': 'IDV',
        'VERDI': 'VERDI',
        'COMUNISTI ITALIANI': 'PDCI',
        'POPOLARI-UDEUR': 'UDEUR',
        'DCA-DEMOCRAZIA CRISTIANA PER LE AUTONOMIE-NUOVO PSI': 'DCA',
    },
    ('XV', 'S'): {
        'Ulivo': 'PD',
        'FI': 'FI',
        'Misto': 'MISTO',
        'AN': 'AN',
        'RC-SE': 'PRC',
        'UDC': 'UDC',
        'LNP': 'LEGA',
        'SDSE': 'SD',
        'Aut': 'AUT',
        'IU-Verdi-Com': 'IU',
        'DC-Ind-MA': 'DCA',
        'DC-PRI-IND-MPA': 'DCA',
        'PD-Ulivo': 'PD',
    },
    ('XVI', 'C'): {
        "POPOLO DELLA LIBERTA'": 'PDL',
        'PARTITO DEMOCRATICO': 'PD',
        'MISTO': 'MISTO',
        'LEGA NORD PADANIA': 'LEGA',
        'UNIONE DI CENTRO PER IL TERZO POLO': 'UDC',
        "FUTURO E LIBERTA' PER IL TERZO POLO": 'FLI',
        'ITALIA DEI VALORI': 'IDV',
        "POPOLO E TERRITORIO (NOI SUD-LIBERTA' ED AUTONOMIA, POPOLARI D'ITALIA "
        "DOMANI-PID, MOVIMENTO DI RESPONSABILITA' NAZIONALE-MRN, AZIONE "
        "POPOLARE, ALLEANZA DI CENTRO-ADC, INTESA POPOLARE)": 'RESP',
    },
    ('XVI', 'S'): {
        'PdL': 'PDL',
        'PD': 'PD',
        'Misto': 'MISTO',
        'LNP': 'LEGA',
        'Per il Terzo Polo:ApI-FLI': 'FLI',
        'UDC-SVP-Aut': 'UDC',
        'IdV': 'IDV',
        'CDN': 'CDN',
        'CN': 'CN',
        'FLI': 'FLI',
        'UDC-SVP-Aut:UV-MAIE-Io Sud-MRE': 'UDC',
        'FDI-CDN': 'CDN',
        'CN-Io Sud': 'CN',
        'CN-Io Sud-FS': 'CN',
        'UDC-SVP-AUT:UV-MAIE-VN-MRE-PLI': 'UDC',
        'CN:GS-SI-PID-IB': 'CN',
        'UDC-SVP-IS-Aut': 'UDC',
        'UDC-SVP-AUT:UV-MAIE-VN-MRE-PLI-PSI': 'UDC',
    },
}

NOTA = (
    "Dal gruppo parlamentare al partito. La chiave e' "
    "'legislatura|ramo|nome del gruppo come lo scrive il registro'. "
    "'eredita_da' dice di chi un partito e' erede legittimo: un passaggio "
    "verso un erede non conta come cambio di casacca, perche' e' il partito "
    "che si e' mosso, non la persona. Quando un partito si spacca, sono eredi "
    "tutti e due i tronconi. File generato da scripts/costruisci_mappa_partiti.py."
)


def main():
    gruppi = {}
    for (leg, ramo), d in GRUPPI.items():
        for nome, partito in d.items():
            if partito not in PARTITI:
                raise SystemExit('partito ignoto: %s' % partito)
            gruppi['%s|%s|%s' % (leg, ramo, nome)] = partito
    for codice, (_n, _c, eredi) in PARTITI.items():
        for e in eredi:
            if e not in PARTITI:
                raise SystemExit('%s eredita da un partito ignoto: %s' % (codice, e))
    fuori = {
        '_nota': NOTA,
        'partiti': {k: {'nome': v[0], 'colore': v[1], 'eredita_da': v[2]}
                    for k, v in PARTITI.items()},
        'gruppi': gruppi,
    }
    json.dump(fuori, open(USCITA, 'w', encoding='utf-8'),
              ensure_ascii=False, indent=1, sort_keys=True)
    print('partiti: %d   gruppi mappati: %d' % (len(PARTITI), len(gruppi)))


if __name__ == '__main__':
    main()
