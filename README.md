# Seconda Repubblica Tracker

Chi ha cambiato casacca in Parlamento fra il 1994 e il 2013, e quante volte.
Cinque legislature, dalla XII alla XVI, 2.763 persone, 1.403 cambi di gruppo.

Un file HTML solo, coi dati dentro. Si apre col doppio clic dal disco.

## Le fonti

| | endpoint | note |
|---|---|---|
| Camera | `dati.camera.it/sparql` | i gruppi, con la sigla ufficiale e le date |
| Senato | `dati.senato.it/sparql` | non interrogabile dal browser (niente CORS) |
| Wikidata | `query.wikidata.org/sparql` | foto, voci di Wikipedia, cariche di governo |

**L'elenco di chi ha seduto in Parlamento lo danno le Camere.** Wikidata serve
per il contorno: da sola non lega i senatori a vita a nessuna legislatura, e
attribuisce meno mandati di quanti ne risultino ai registri.

## Che cosa conta come cambio di casacca

Due iscrizioni consecutive a gruppi diversi, con due eccezioni:

1. **Il gruppo ha solo cambiato nome.** Non serve nemmeno accorgersene: il
   registro della Camera tiene l'identità del gruppo separata dal suo nome, e
   *Iniziativa Responsabile* e *Popolo e Territorio* risultano lo stesso gruppo.
2. **Fra una legislatura e l'altra, il partito d'arrivo è erede di quello di
   partenza** (`data/partiti.json`). Chi passa dai DS al PD non ha cambiato
   casacca: si è mosso il partito. Quando un partito si spacca, sono eredi
   entrambi i tronconi.

Le successioni valgono **solo** fra una legislatura e l'altra: dentro una
legislatura ogni spostamento è una scelta. Il passaggio al gruppo misto conta
sempre.

## Come si usa

```bash
python scripts/scarica_elenco.py --fresco
python scripts/costruisci_mappa_partiti.py
python scripts/genera_sito.py
```

Esce `sito/index.html`. Senza `--fresco` le risposte restano in cache dodici ore.

| script | cosa fa |
|---|---|
| `wd.py` `camera.py` `senato.py` | parlano con le tre fonti |
| `scarica_elenco.py` | costruisce `data/elenco.json` |
| `costruisci_mappa_partiti.py` | dai 135 nomi di gruppo ai 34 partiti |
| `casacche.py` | il conto dei cambi, con le successioni |
| `genera_sito.py` | compatta i dati e li inietta in `modello.html` |
| `novita.py` | dice al lavoro notturno se è cambiato qualcosa di vero |
| `verifica_viventi.py` | chiede conto ai registri di chi risulta vivo |

## Le reti di sicurezza

- Istantanee dei registri versionate in `data/registri/`: se un endpoint tace,
  si usa l'ultima copia buona invece del vuoto.
- Soglia dell'80%: una fonte che torna con meno dell'80% delle voci note è un
  guasto travestito da successo.
- `novita.py` fallisce se più di tre persone tornerebbero in vita, e blocca la
  pubblicazione.
- Il file `data/esclusi.json` porta la ragione scritta di ogni esclusione.

## Correzioni

davide.caniatti@gmail.com

Per copiare questo sito, ripubblicarlo altrove, riusarne delle parti o adattarlo
serve la mia autorizzazione scritta, e va citata la fonte: Seconda Repubblica
Tracker, Davide Caniatti.
