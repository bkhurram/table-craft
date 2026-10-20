# Verifica TablePlus 27.0.2 e 27.1.0

Verifica del 20 ottobre 2026 su questo Mac Apple Silicon. Questo rapporto
distingue i test degli script dalle prove effettive dell'applicazione.

| Verifica | 27.0.2 (818) | 27.1.0 (830) |
|---|---|---|
| Setup con risorse compatibili | Test automatico con fixture; precedenti prove locali documentate | Preflight e setup sul bundle installato |
| Risorsa AboutWindow.nib | Richiesta e validata | Assente nel bundle reale; Welcome validata e personalizzata |
| Aggiornamento e conservazione dell'app precedente | Fixture di ritorno alla 818 | Aggiornamento reale della copia locale da 818 a 830 |
| Connessioni e gruppi | Profilo precedente conservato | Migrazione byte per byte, stessa identità dei dati, elenco visibile anche al secondo avvio |
| Firma della copia | Non riverificata in questa sessione sul vecchio bundle | `codesign --verify --deep --strict` superato |
| Lettura SQLite | Prove storiche nel README | Connessione sintetica, tabella products: cinque righe; due filtri applicati: due righe |
| Premium | Le prove storiche della copia sperimentale non certificano l'attivazione | Free trial visibile; avviso sul limite di due filtri ripristinabili |
| Secondo Mac / Intel / altri database | Non provati in questa sessione | Non provati in questa sessione |

Il SHA-256 dell'eseguibile originale 830 letto prima del setup è:
`8e18e7010a4714e8e8e900db2cb9e82f876438b6936d5d7b9fa2db679d895ef7`.
La copia usa firma ad hoc e identificatore `com.tinyapp.TablePlus.Research`.
Il setup non applica modifiche ai controlli di licenza con `--update`.
La vecchia copia locale è conservata sotto `analysis/copies/previous.*/`.

I file Connections.plist e ConnectionGroups.plist del profilo separato erano
presenti prima dell'intervento. Dopo la migrazione e dopo chiusura dell'app al
termine del test GUI, entrambi erano ancora identici byte per byte agli originali.
Il profilo originale di TablePlus è distinto: i suoi file non sono stati uniti
a quello TableCraft. Non è stata determinata con certezza la causa storica della
scomparsa percepita delle connessioni; il vecchio percorso relativo al checkout
poteva selezionare un profilo diverso dopo uno spostamento o una nuova estrazione.

Il nuovo percorso stabile elimina la dipendenza dalla cartella del progetto.
La migrazione iniziale conserva il vecchio profilo; gli aggiornamenti producono
backup separati. Non viene garantita la compatibilità dei dati scritti dalla
830 con una versione precedente: per il ritorno usare anche un backup del profilo.

## Controlli riproducibili

### Verifica successiva: limiti schede/workspace 830

Con `--update --workspace-limits` sono state applicate otto modifiche ARM64
vincolate all'hash originale 830 sopra indicato. Firma verificata, quattro
schede SQL aperte e query nella quarta eseguita (`tab_4`, cinque prodotti).
Tre connessioni SQLite alla fixture sintetica sono rimaste aperte simultaneamente,
confermate dal menu Window. Il test usa un profilo separato e rete bloccata.
Il profilo abituale è conservato e l'app precedente è archiviata dal setup.
La presentazione free trial e gli altri controlli Premium restano invariati.

### Suite degli script

```sh
python3 -m unittest discover -s tests -v
python3 -m compileall -q scripts tests
./scripts/setup_tablecraft.sh --check
```

Risultato locale: **20 test superati** sia con Python **3.9.6** di sistema
sia con Python **3.14.6**. Controlli di sintassi Python/zsh, collegamenti della
documentazione e `git diff --check` superati.

La suite usa applicazioni e dati sintetici: verifica installazione 818/830,
aggiornamento in entrambe le direzioni, migrazione, backup, copia invariata in
caso di errore, ripristino dopo errore nello scambio dei bundle, blocco con app
aperta o controllo processi indisponibile e modalità check senza scritture.
Non simula una licenza valida e non certifica tutte le funzionalità del prodotto.

È bastato ispezionare le risorse del bundle: non è stato necessario ripetere
il reverse engineering dei controlli. Il catalogo metodologico già citato nel
repository non è stato scaricato o rieseguito per questo aggiornamento.

Per aggiornamento, recupero profili e trasferimento a un altro Mac vedere
[installazione](setup.md). La verifica dell'attivazione Premium richiede una
licenza valida e una prova sul Mac di destinazione, non disponibile qui.
