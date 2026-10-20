# Changelog

## Unreleased

- `--filter-limits` sulla build ARM64 830 elimina il limite di due filtri per
  creazione e ripristino, con verifica su tre filtri SQLite simultanei.

- `--hide-trial-ui` sulla build ARM64 830 rimuove gli avvisi trial dalla schermata
  iniziale e dalle notifiche, conservando le modifiche a schede/workspace e lo stato licenza.

- Compatibilità del branding con TablePlus 27.1.0 (830), senza richiedere AboutWindow.nib assente in questa build; supporto 27.0.2 (818) conservato.
- Profilo stabile fuori dal checkout, migrazione conservativa delle connessioni e override `TABLECRAFT_PROFILE`.
- `--update` con backup del profilo, conservazione dell'app precedente e blocco se la copia è aperta.
- Test automatici per migrazione, aggiornamento 818/830, errori e conservazione dei dati; rapporto con prove reali sulla 830.
- Chiarimenti sull'attivazione Premium e sui limiti della verifica su un altro Mac.

- Branding su più build con verifica delle risorse prima della copia; versione e hash esatti richiesti solo per le modifiche ai controlli locali.
- Setup compatibile con Python 3.9+, selezione esplicita dell'interprete e messaggi sui requisiti mancanti.
- Preparazione temporanea con pulizia in caso di errore e controllo della firma prima dell'avvio.
- Firma con conservazione degli entitlement e uso dell'icona ICNS già inclusa.
- Nome TableCraft nella schermata iniziale, nei menu e nella finestra Informazioni.
- Icona dell'elefante in stile incisione e logo interno coordinato.
- Setup locale con preflight di versione/hash, profilo separato e modalità offline.
- Analisi statica riproducibile e modifiche ARM64 sperimentali opzionali.
- README italiano/inglese, compatibilità documentata e demo SQLite sintetica.
- Esclusione dei dati locali da Git e controlli CI sui file pubblicabili.

## Limiti locali 830 — 20 ottobre 2026

- Aggiunta opzione esplicita `--workspace-limits`, compatibile con `--update`,
  vincolata a versione e hash del campione ARM64 830; otto modifiche a schede e workspace.
- Verificati quattro tab SQL con query nella quarta e tre workspace SQLite simultanei.
- Analisi dei riferimenti ora parametrizzabile senza sovrascrivere le evidenze storiche.
