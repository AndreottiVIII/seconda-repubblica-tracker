# -*- coding: utf-8 -*-
"""Un controllo minimo sul JavaScript del modello, prima di pubblicarlo.

Non e' un interprete: cerca una cosa sola, ma e' quella che fa piu' danno.
Una stringa aperta con un apice e mai chiusa prima di fine riga manda in
errore tutto lo script, e siccome i dati stanno dentro la stessa pagina il
sito non si apre nemmeno: resta una scrivania vuota, senza icone e senza
finestre, e nessun messaggio.

E' successo davvero, per un apostrofo dentro «cosa se ne puo' fare».

Un file HTML solo e' comodo, ma ha questo prezzo: non c'e' un compilatore fra
te e il pubblico. Questo controllo e' il compilatore.
"""
import sys, re

# Un apice puo' aprire una stringa solo se non e' un apostrofo dentro
# un'espressione regolare: /"/g e /^#/ sono legittimi. Si riconosce l'inizio
# di un'espressione regolare da cosa la precede.
PRIMA_DI_REGEX = set('(,=:[!&|?{};\n+')


def righe_sospette(js):
    """[(numero di riga, testo)] delle righe con una stringa non chiusa."""
    fuori = []
    riga = 1
    i = 0
    n = len(js)
    ultimo_significativo = '\n'
    while i < n:
        c = js[i]

        if c == '\n':
            riga += 1
            i += 1
            continue

        # commenti
        if c == '/' and i + 1 < n and js[i+1] == '/':
            while i < n and js[i] != '\n':
                i += 1
            continue
        if c == '/' and i + 1 < n and js[i+1] == '*':
            i += 2
            while i + 1 < n and not (js[i] == '*' and js[i+1] == '/'):
                if js[i] == '\n':
                    riga += 1
                i += 1
            i += 2
            continue

        # espressione regolare
        if c == '/' and ultimo_significativo in PRIMA_DI_REGEX:
            i += 1
            while i < n and js[i] != '\n':
                if js[i] == '\\':
                    i += 2
                    continue
                if js[i] == '/':
                    i += 1
                    break
                i += 1
            ultimo_significativo = '/'
            continue

        # stringhe con apici: devono chiudersi sulla stessa riga
        if c in '"\'':
            apice = c
            inizio = riga
            i += 1
            chiusa = False
            while i < n:
                if js[i] == '\\':
                    i += 2
                    continue
                if js[i] == apice:
                    chiusa = True
                    i += 1
                    break
                if js[i] == '\n':
                    break
                i += 1
            if not chiusa:
                testo = js.split('\n')[inizio - 1].strip()
                fuori.append((inizio, testo[:110]))
            ultimo_significativo = apice
            continue

        # stringhe con apice inverso: possono stare su piu' righe
        if c == '`':
            i += 1
            while i < n:
                if js[i] == '\\':
                    i += 2
                    continue
                if js[i] == '\n':
                    riga += 1
                if js[i] == '`':
                    i += 1
                    break
                i += 1
            ultimo_significativo = '`'
            continue

        if not c.isspace():
            ultimo_significativo = c
        i += 1
    return fuori


def controlla(html, dove=''):
    """Solleva un errore se lo script della pagina non regge."""
    m = re.search(r'<script>(.*?)</script>', html, re.S)
    if not m:
        raise SystemExit('%s: non c\'e\' nessuno script nella pagina.' % dove)
    guai = righe_sospette(m.group(1))
    if guai:
        sys.stderr.write('%s: stringhe non chiuse, il sito non si aprirebbe.\n' % dove)
        for numero, testo in guai:
            sys.stderr.write('  riga %d dello script: %s\n' % (numero, testo))
        raise SystemExit(1)
    return True


if __name__ == '__main__':
    import io, os
    QUI = os.path.dirname(os.path.abspath(__file__))
    percorso = sys.argv[1] if len(sys.argv) > 1 else os.path.join(
        QUI, '..', 'sito', 'index.html')
    controlla(io.open(percorso, encoding='utf-8').read(), os.path.basename(percorso))
    print('%s: lo script regge.' % os.path.basename(percorso))
