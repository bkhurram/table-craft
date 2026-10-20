# Verifica della separazione del Portachiavi

Verifica statica del 20 ottobre 2026 sul runtime incorporato TableCraft
27.1.0 (830), slice ARM64. SHA-256 dell'eseguibile:
`4f26418e0178fd2448de1fd87ec2d36145107430ccb39df34cf176d89187e12c`.
Non sono stati letti, esportati o modificati elementi del Portachiavi.
Il runtime e il suo manifest non sono stati modificati.

## Risultato prima della correzione

La separazione del profilo su disco non comprende il Portachiavi. Il codice
nativo mantiene il servizio predefinito `com.tableplus.TablePlus` e assegna
l'etichetta visibile `TablePlus` alle password create dal componente
`KeychainSwift`. Il branding e `CFFIXED_USER_HOME` non riscrivono questi valori.

Reimportare una connessione non crea automaticamente un servizio TableCraft.
Quando il codice salva una password importata, continua a usare il componente
nativo e la sua etichetta. La finestra con il nome «TablePlus» non basta quindi
a distinguere una voce preesistente da una appena creata mediante TableCraft.
Non è stato verificato il contenuto dei file importati dall'utente.

La copia ha una firma ad hoc diversa dall'originale. Se richiede una password
protetta da un'autorizzazione che non comprende questa identità, macOS può
chiedere il consenso. Dalla sola schermata non è possibile identificare la
singola voce o la sua lista delle applicazioni autorizzate.

## Evidenze statiche

| Indirizzo ARM64 | Evidenza |
|---|---|
| `0x100d95e50` | Stringa costante `com.tableplus.TablePlus` |
| `0x100807768` | Inizializzazione dell'istanza condivisa con quel servizio nel campo `+0x30` |
| `0x100a0d0cc`, `0x100a0d288`, `0x100a0d33c`, `0x100a0d3a4` | Altri percorsi di inizializzazione con lo stesso servizio predefinito |
| `0x100a0d518` | Costruzione della voce: `kSecAttrLabel` impostato al valore Swift `TablePlus` alle istruzioni `0x100a0d634`–`0x100a0d648`; `kSecAttrService` ricavato dall'istanza |
| `0x100a0d9ac` | Query di lettura: `kSecAttrService` ricavato dallo stesso campo `+0x30`, poi chiamata a `SecItemCopyMatching` a `0x100a0dbe4` |

Rilevazione con `otool -Iv`, lettura Mach-O e disassemblaggio ARM64; nessun
accesso ai segreti richiesto. Le evidenze dettagliate locali sono nella cartella
`analysis/keychain-audit/`. La verifica completa di inventario e firma del
runtime è passata dopo l'analisi.

## Requisiti della correzione

TableCraft deve usare un servizio proprio e un'etichetta TableCraft, sia in
lettura sia in scrittura e cancellazione. Cambiare soltanto il testo mostrato
non separa le credenziali. Occorre inoltre verificare gli eventuali servizi
specifici, come quelli MCP/TLS, che hanno identificatori distinti.

Le password già presenti nel servizio precedente non diventano automaticamente
parte del nuovo servizio. Dopo la separazione servono un'importazione che
contenga effettivamente le password, il loro reinserimento oppure una migrazione
esplicita. La migrazione deve lasciare intatte le voci originali e non deve
prevedere un ripiego silenzioso sul servizio TablePlus.

## Correzione applicata

Il runtime incorporato ora utilizza esattamente:

- Servizio: `com.tablecraft.TableCraft`.
- Etichetta per le nuove password: `TableCraft`.

La modifica comprende entrambe le slice ARM64 e Intel: stringa del servizio,
sei lunghezze Swift per architettura e l'etichetta nel percorso di salvataggio.
Le query di lettura, scrittura e cancellazione usano il campo del servizio
inizializzato con la nuova identità. Non è stato aggiunto un ripiego sul
servizio precedente. I servizi distinti MCP/TLS non sono oggetto di questa
modifica alle password generiche.

`patch_keychain_identity.py` verifica build, hash e byte prima della scrittura;
non legge o modifica il Portachiavi. L'aggiornamento è stato eseguito su una
copia temporanea, poi firmata e verificata. Il vecchio runtime è conservato
localmente sotto `analysis/runtime-backups/`. Schede, finestre, filtri, logo e
visibilità trial sono stati nuovamente verificati dal manifest del runtime.

Per applicare la stessa modifica a un runtime incorporato precedente supportato:

```sh
python3 scripts/portable_runtime.py isolate-keychain
```

Anche una nuova incorporazione con `embed` applica questa identità prima della
firma, se la copia di partenza usa ancora il servizio precedente. Le password
esistenti non sono migrate: riavviare TableCraft, poi reimportarle da un file che
le contenga oppure reinserirle e salvarle. Le voci TablePlus rimangono intatte.
Le etichette delle vecchie voci non vengono rinominate.

La verifica del codice comprende entrambe le architetture; l'avvio nativo resta
verificato soltanto su Apple Silicon.

## Riferimenti Apple

- [Attributo del servizio](https://developer.apple.com/documentation/security/ksecattrservice)
- [Identità delle password generiche](https://developer.apple.com/documentation/security/ksecclassgenericpassword)
- [Autorizzazioni di accesso](https://developer.apple.com/documentation/security/access-control-lists)

## Verifiche della correzione

- 38 test automatici superati, inclusi rifiuto di hash sconosciuti e modifiche
  parziali, conservazione dei byte estranei alla patch, idempotenza e ripristino
  del runtime precedente in caso di errore di firma o pubblicazione.
- Il codice ARM64 reale degli inizializzatori è stato eseguito su dati sintetici:
  servizio di 25 byte e stringa Swift `TableCraft` di 10 byte confermati. Il test
  non chiama il Portachiavi e non usa credenziali.
- Disassemblaggio di entrambe le slice e verifica integrale della firma dopo la
  modifica; tutti gli override precedenti presenti nel nuovo manifest.

Non è stata eseguita una prova con password reali. Il test delle stringhe native
non equivale a una prova end-to-end di autenticazione a un database.

Il nuovo eseguibile ha SHA-256
`dad81c0c4c6223efe28dca37452ef9a425629630343346ce51d25cfb21d89048`.
L'avvio dello ZIP aggiornato, estratto in una cartella separata con profilo
temporaneo, è riuscito; il processo è stato terminato dopo 10 secondi dal test.
Il confronto di tutte le sezioni Mach-O in entrambe le architetture conferma
che contengono esclusivamente le modifiche previste. Framework e risorse sono
identici al backup; è cambiato soltanto l'eseguibile con la relativa firma.
