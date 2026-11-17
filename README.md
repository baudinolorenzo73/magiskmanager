# Magisk Manager (APK)

App Android (Kivy) per telefoni con root Magisk. by Lollo ®2026

- **Stato**: versione di Magisk, Zygisk, DenyList, dispositivo.
- **Moduli**: elenco, abilita/disabilita, rimozione, riavvio.
- **Aggiorna**: controlla gli aggiornamenti dei moduli (updateJson o GitHub).
- **Installa**: catalogo con spiegazioni (13 moduli), ricerca di nuovi moduli su GitHub, importazione di elenchi, installazione da ZIP.
- **Integrita**: indizi locali + app Play Integrity Checker (il verdetto lo da Google).
- **Recupero**: copia dell'immagine di boot (boot/init_boot, con SHA-256) e guida per ripristinare il telefono dopo un bootloop.

## Come ottenere l'APK

1. Pubblica questo progetto su GitHub (repository `magiskmanager`).
2. GitHub Actions compila da solo (circa 20-40 minuti la prima volta).
3. Scarica l'APK da **Releases** (oppure da Actions > ultimo run > Artifacts).

## File

- `main.py` interfaccia Kivy · `motore.py` logica (root, moduli, GitHub)
- `buildozer.spec` configurazione APK · `.github/workflows/apk.yml` compilazione
- La versione dell'APK si cambia in `buildozer.spec` (riga `version`).

Al primo avvio Magisk chiede il permesso root: consentilo.
