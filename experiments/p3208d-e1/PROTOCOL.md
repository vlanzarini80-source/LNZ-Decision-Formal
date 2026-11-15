
# LNZ P320.8d / E1 - Preregistrazione

Stato: PROTOCOLLO NON ESEGUITO.
Data: 2026-11-15.

## Obiettivo

Confrontare LNZ con una baseline Lean standard nel rilevamento di alterazioni rispetto a una specifica matematica fissata prima dell'esperimento.

E1 NON dimostra la fedelta semantica fra un articolo e un enunciato Lean.

## Confine di fiducia

- Specifica, definizioni e toolchain devono essere fissate.
- Il generatore puo modificare soltanto la soluzione.
- Il verificatore non deve accettare hash forniti dal candidato.
- Il riferimento deve essere approvato separatamente.
- Usare soltanto casi controllati in questa fase.

## Baseline B0

Build Lean, ispezione degli assiomi e controlli standard disponibili.

Comparator sara incluso soltanto dopo aver verificato versione, funzionamento e compatibilita.

## Trattamento LNZ

Stessa baseline B0, piu i controlli aggiuntivi di specifica e provenienza effettivamente implementati.

## Possibili esiti

- ACCEPT: candidato conforme alla specifica formale.
- REJECT: violazione della politica preregistrata.
- REVIEW: evidenza insufficiente per decidere.

## Regole sperimentali

- Gli esiti attesi non sono input del verificatore.
- Registrare exit code, log, versioni, hash e motivazioni.
- Calcolare metriche solo dopo l'esecuzione.
- Non attribuire a LNZ funzionalita gia presenti nella baseline.
- Non eseguire repository ostili su runner con credenziali.
- Nessun PASS matematico prima della verifica reale.
