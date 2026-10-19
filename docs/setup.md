# Installazione e uso locale

## Requisiti

- Mac Apple Silicon, avviato nativamente in ARM64.
- Python 3.11 o successivo e strumenti sviluppatore Apple.
- TablePlus 27.0.2 (818) installato separatamente.
- SHA-256 dell'eseguibile supportato:
  `4547216d88fcd2868e48f31a2079da27850ace793ae79cc0fb7963d9c827c05a`.

`./scripts/setup_tablecraft.sh --check` esegue i controlli senza creare la copia.
Se manca Python o uno degli strumenti richiesti, il controllo si interrompe e
indica il requisito mancante.

## Creare la copia

Aprire `Avvia TableCraft.command`: al primo avvio esegue automaticamente il setup
usando `/Applications/TablePlus.app`, poi avvia la copia. Il file ZIP di GitHub
contiene gli script, non l'applicazione preparata. Restano necessari tutti i
requisiti elencati sopra. In caso di errore, risolvere il requisito indicato e
riaprire il launcher.

Per eseguire i due passaggi manualmente, dal Terminale nella cartella scaricata:

```sh
./scripts/setup_tablecraft.sh
./"Avvia TableCraft.command"
```

Un percorso sorgente diverso può essere specificato con:

```sh
./scripts/setup_tablecraft.sh --source /percorso/TablePlus.app
```

Il setup crea `analysis/copies/TablePlus-Research.app`. Il percorso tecnico
mantiene il nome storico; nome visibile, schermata iniziale e menu usano
TableCraft. L'identificatore è `com.tinyapp.TablePlus.Research`.

La cartella `analysis/runtime-profile/` contiene i dati del profilo separato.
Il launcher imposta `CFFIXED_USER_HOME` per questo processo. Non importare profili
reali per le demo pubbliche. Il setup non sovrascrive copie già presenti e non
elimina i profili esistenti.

La copia è firmata ad hoc. L'app originale non viene modificata; la copia non
conserva l'identità Developer ID o la notarizzazione originale. Il setup non
modifica Gatekeeper, SIP o le impostazioni di sicurezza del Mac.

## Controlli locali sperimentali

Il setup predefinito applica nome e grafica. Per includere le modifiche ai
controlli locali del campione di ricerca, durante la prima creazione:

```sh
./scripts/setup_tablecraft.sh --local-controls
```

L'opzione applica 21 sostituzioni di codice alla slice ARM64 del campione
supportato. La slice Intel resta invariata. Il manifest dei byte modificati è
scritto in `analysis/evidence/feature-controls/patch-manifest.json` e rimane locale.
Non vengono generate credenziali o autorizzazioni per servizi remoti.

I risultati multi-workspace, multi-tab, filtri e Metrics Board documentati nel
README provengono dalla copia sperimentale. Non costituiscono una garanzia per
ogni funzione del prodotto o per altri campioni.

## Modalità offline

```sh
./"Avvia TableCraft.command" --offline
```

La modalità usa `sandbox-exec` con rete bloccata e accesso negato ai Keychain e
ai percorsi TablePlus originali elencati nel profilo generato. È una modalità
di prova locale; non consente connessioni a database remoti e non è descritta
come isolamento completo. La disponibilità dipende da `sandbox-exec` sul Mac.

## Database di esempio

Creare un database SQLite nuovo con soli dati sintetici:

```sh
mkdir -p analysis/fixtures
sqlite3 analysis/fixtures/tablecraft-demo.sqlite < docs/demo.sql
```

In TableCraft, creare una connessione SQLite verso quel file. La query di
aggregazione restituisce kitchen 161.2, lighting 87.0 e stationery 102.0.

## Analisi statica opzionale

```sh
python3 scripts/analyze_tableplus.py /Applications/TablePlus.app
```

Il comando legge il bundle senza avviare i suoi eseguibili; usa `otool`, `nm`,
`strings`, `codesign`, `swift-demangle` e LLDB. Gli output restano sotto `analysis/`.
La scansione dei riferimenti con Capstone richiede l'ambiente opzionale:

```sh
python3 -m venv .venv-re
.venv-re/bin/pip install -r requirements-analysis.txt
.venv-re/bin/python scripts/find_feature_controls.py
```

## Ripristino

Chiudere TableCraft e avviare `/Applications/TablePlus.app` per usare l'installazione
originale. Conservare il profilo prima di spostare o rimuovere la cartella della
copia locale. Nessuna procedura del repository elimina automaticamente i dati.
