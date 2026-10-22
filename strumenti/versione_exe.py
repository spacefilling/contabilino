"""
Contabilino - Informazioni di versione dell'eseguibile Windows.

Scrive versione_exe.txt per PyInstaller (--version-file): sono i dati che
Windows mostra in Proprietà > Dettagli del file Contabilino.exe e in Gestione
attività (descrizione, versione, prodotto, copyright con l'autore).

    python strumenti/versione_exe.py
    pyinstaller ... --version-file versione_exe.txt main.py
"""

import os
import sys

RADICE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RADICE)

from version import REPOSITORY, SITO, VERSIONE  # noqa: E402

AUTORE = "spacefiller"
ANNO = "2026"


def main():
    numeri = [int(n) for n in VERSIONE.split(".")]
    numeri = tuple((numeri + [0, 0, 0, 0])[:4])
    testo = f"""# File generato da strumenti/versione_exe.py: non modificarlo a mano.
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers={numeri},
    prodvers={numeri},
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable('041004B0', [
        StringStruct('CompanyName', '{AUTORE}'),
        StringStruct('FileDescription', 'Contabilino - contabilità in partita doppia'),
        StringStruct('FileVersion', '{VERSIONE}'),
        StringStruct('InternalName', 'Contabilino'),
        StringStruct('LegalCopyright', 'Copyright (C) {ANNO} {AUTORE} - licenza GNU GPL v3'),
        StringStruct('OriginalFilename', 'Contabilino.exe'),
        StringStruct('ProductName', 'Contabilino'),
        StringStruct('ProductVersion', '{VERSIONE}'),
        StringStruct('Comments', '{SITO} - {REPOSITORY}')
      ])
    ]),
    VarFileInfo([VarStruct('Translation', [0x0410, 1200])])
  ]
)
"""
    with open(os.path.join(RADICE, "versione_exe.txt"), "w", encoding="utf-8") as f:
        f.write(testo)
    print(f"versione_exe.txt: Contabilino {VERSIONE}, {AUTORE}")


if __name__ == "__main__":
    main()
