"""
Contabilino - Layer database SQLite
Gestione connessione, tabelle, CRUD per esercizi/conti/registrazioni/movimenti.
"""

import sqlite3
import os

from dateutils import format_display, parse_iso, to_iso, periodo_label


class Database:
    def __init__(self, db_path):
        self.db_path = db_path
        self.conn = None
        self.backup_path = None  # valorizzato se una migrazione crea una copia di sicurezza

    def connect(self):
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("PRAGMA foreign_keys = ON")
        self.conn.row_factory = sqlite3.Row

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None

    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS esercizi (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                descrizione TEXT NOT NULL,
                data_inizio TEXT NOT NULL,
                data_fine TEXT NOT NULL,
                data_chiusura TEXT
            );

            CREATE TABLE IF NOT EXISTS conti (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codice TEXT NOT NULL UNIQUE,
                nome TEXT NOT NULL,
                tipo TEXT NOT NULL CHECK(tipo IN ('ATTIVO', 'PASSIVO', 'COSTO', 'RICAVO')),
                padre_id INTEGER REFERENCES conti(id)
            );

            CREATE TABLE IF NOT EXISTS registrazioni (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                esercizio_id INTEGER NOT NULL,
                data TEXT NOT NULL,
                numero INTEGER NOT NULL,
                descrizione TEXT NOT NULL,
                FOREIGN KEY (esercizio_id) REFERENCES esercizi(id)
            );

            CREATE TABLE IF NOT EXISTS movimenti (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                registrazione_id INTEGER NOT NULL,
                conto_id INTEGER NOT NULL,
                dare REAL NOT NULL DEFAULT 0,
                avere REAL NOT NULL DEFAULT 0,
                FOREIGN KEY (registrazione_id) REFERENCES registrazioni(id) ON DELETE CASCADE,
                FOREIGN KEY (conto_id) REFERENCES conti(id)
            );
        """)
        self.conn.commit()
        self._migrate()

    def _migrate(self):
        """
        Aggiorna la struttura dei DB creati con le versioni precedenti.
        Le aggiunte per i moduli IVA e bilancio sono solo tabelle e colonne nuove:
        i dati esistenti non vengono toccati e chi non usa i moduli non vede differenze.
        """
        cursor = self.conn.cursor()
        cursor.execute("PRAGMA table_info(conti)")
        columns = [row[1] for row in cursor.fetchall()]
        if "padre_id" not in columns:
            cursor.execute("ALTER TABLE conti ADD COLUMN padre_id INTEGER REFERENCES conti(id)")
            self.conn.commit()
        if "voce_bilancio" not in columns:
            # Voce dello schema di bilancio (art. 2424/2425 c.c.) a cui il conto è collegato: facoltativa
            cursor.execute("ALTER TABLE conti ADD COLUMN voce_bilancio TEXT")
            self.conn.commit()
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS impostazioni (chiave TEXT PRIMARY KEY, valore TEXT)"
        )
        self.conn.commit()
        self._migrate_esercizi()

    # --- Impostazioni dell'archivio (moduli attivi, dati dell'azienda...) ---

    def get_impostazione(self, chiave, predefinito=None):
        cursor = self.conn.cursor()
        cursor.execute("SELECT valore FROM impostazioni WHERE chiave = ?", (chiave,))
        riga = cursor.fetchone()
        return riga[0] if riga else predefinito

    def set_impostazione(self, chiave, valore):
        with self.conn:
            if valore is None:
                self.conn.execute("DELETE FROM impostazioni WHERE chiave = ?", (chiave,))
            else:
                self.conn.execute(
                    "INSERT INTO impostazioni (chiave, valore) VALUES (?, ?) "
                    "ON CONFLICT(chiave) DO UPDATE SET valore = excluded.valore",
                    (chiave, str(valore)),
                )

    def modulo_attivo(self, nome):
        """Moduli facoltativi: "iva", "bilancio". Spenti finché l'utente non li attiva."""
        return self.get_impostazione(f"modulo_{nome}") == "1"

    def imposta_modulo(self, nome, attivo):
        self.set_impostazione(f"modulo_{nome}", "1" if attivo else "0")

    def _migrate_esercizi(self):
        """
        Converte la vecchia tabella esercizi (anno + data_apertura) nella nuova
        struttura con periodo esplicito (data_inizio + data_fine).
        Gli esercizi esistenti erano anni solari: diventano 01/01 - 31/12.
        Prima di modificare la struttura viene creata una copia di sicurezza del DB.
        """
        cursor = self.conn.cursor()
        cursor.execute("PRAGMA table_info(esercizi)")
        columns = [row[1] for row in cursor.fetchall()]
        if not columns or "data_inizio" in columns:
            return  # tabella assente (appena creata) o già aggiornata

        # Leggi i dati esistenti e convertili
        cursor.execute("SELECT * FROM esercizi")
        vecchi = cursor.fetchall()
        convertiti = []
        for row in vecchi:
            chiavi = row.keys()
            anno = row["anno"] if "anno" in chiavi else None
            apertura = row["data_apertura"] if "data_apertura" in chiavi else None

            # Gli esercizi erano anni solari: l'inizio è il 1° gennaio dell'anno
            # (la data di apertura era una data qualsiasi, non l'inizio del periodo)
            inizio = f"{int(anno)}-01-01" if anno else to_iso(apertura)
            if not inizio:
                continue  # riga irrecuperabile: senza anno né data di apertura

            anno_fine = int(anno) if anno else parse_iso(inizio).year
            fine = f"{anno_fine}-12-31"

            descrizione = (row["descrizione"] or "").strip() if "descrizione" in chiavi else ""
            if not descrizione:
                descrizione = f"Esercizio {anno_fine}"

            convertiti.append((
                row["id"], descrizione, inizio, fine,
                row["data_chiusura"] if "data_chiusura" in chiavi else None,
            ))

        self.backup_path = self._crea_backup()

        # Ricostruzione della tabella (SQLite non permette di togliere il vincolo
        # UNIQUE su anno con una ALTER TABLE): gli id vengono preservati perché
        # le registrazioni vi fanno riferimento.
        self.conn.commit()
        self.conn.execute("PRAGMA foreign_keys = OFF")
        cursor.execute("""
            CREATE TABLE esercizi_nuovi (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                descrizione TEXT NOT NULL,
                data_inizio TEXT NOT NULL,
                data_fine TEXT NOT NULL,
                data_chiusura TEXT
            )
        """)
        cursor.executemany(
            "INSERT INTO esercizi_nuovi (id, descrizione, data_inizio, data_fine, data_chiusura) "
            "VALUES (?, ?, ?, ?, ?)",
            convertiti,
        )
        cursor.execute("DROP TABLE esercizi")
        cursor.execute("ALTER TABLE esercizi_nuovi RENAME TO esercizi")
        self.conn.commit()
        self.conn.execute("PRAGMA foreign_keys = ON")

    def _crea_backup(self):
        """Copia di sicurezza del file di database prima di una migrazione."""
        import shutil
        from datetime import datetime

        if not os.path.exists(self.db_path):
            return None
        base, ext = os.path.splitext(self.db_path)
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        backup_path = f"{base}_backup_{timestamp}{ext or '.db'}"
        try:
            shutil.copy2(self.db_path, backup_path)
            return backup_path
        except OSError:
            return None

    def insert_default_conti(self):
        """Inserisce il piano dei conti predefinito se la tabella è vuota."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM conti")
        if cursor.fetchone()[0] == 0:
            conti_default = [
                ("100", "Cassa", "ATTIVO", None),
                ("110", "Banca", "ATTIVO", None),
                ("200", "Debiti fornitori", "PASSIVO", None),
                ("300", "Crediti clienti", "ATTIVO", None),
                ("400", "Costi generali", "COSTO", None),
                ("500", "Ricavi generali", "RICAVO", None),
            ]
            cursor.executemany(
                "INSERT INTO conti (codice, nome, tipo, padre_id) VALUES (?, ?, ?, ?)",
                conti_default,
            )
            self.conn.commit()

    def init_db(self):
        """Inizializza un nuovo database con tabelle e conti predefiniti."""
        self.create_tables()
        self.insert_default_conti()

    # --- Esercizi ---

    def get_esercizi(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM esercizi ORDER BY data_inizio DESC")
        return cursor.fetchall()

    def get_esercizio(self, esercizio_id):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM esercizi WHERE id = ?", (esercizio_id,))
        return cursor.fetchone()

    def get_esercizio_per_data(self, data_iso):
        """Esercizio il cui periodo contiene la data indicata (None se nessuno)."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM esercizi WHERE ? BETWEEN data_inizio AND data_fine "
            "ORDER BY data_inizio DESC LIMIT 1",
            (data_iso,),
        )
        return cursor.fetchone()

    def crea_esercizio(self, descrizione, data_inizio, data_fine):
        self._valida_periodo(data_inizio, data_fine)
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO esercizi (descrizione, data_inizio, data_fine) VALUES (?, ?, ?)",
            (descrizione, data_inizio, data_fine),
        )
        self.conn.commit()
        return cursor.lastrowid

    def modifica_esercizio(self, esercizio_id, descrizione, data_inizio, data_fine):
        esercizio = self.get_esercizio(esercizio_id)
        if esercizio and esercizio["data_chiusura"] and (
            data_inizio != esercizio["data_inizio"] or data_fine != esercizio["data_fine"]
        ):
            raise ValueError(
                "L'esercizio è chiuso: il periodo non si può cambiare (la descrizione sì). "
                "Per cambiarlo va prima riaperto."
            )
        self._valida_periodo(data_inizio, data_fine, escludi_id=esercizio_id)
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE esercizi SET descrizione = ?, data_inizio = ?, data_fine = ? WHERE id = ?",
            (descrizione, data_inizio, data_fine, esercizio_id),
        )
        self.conn.commit()

    def _valida_periodo(self, data_inizio, data_fine, escludi_id=None):
        """
        Controlla che il periodo sia coerente e non si sovrapponga ad altri esercizi.
        Solleva ValueError con un messaggio leggibile.
        """
        inizio = parse_iso(data_inizio)
        fine = parse_iso(data_fine)
        if not inizio:
            raise ValueError("Data di inizio non valida.")
        if not fine:
            raise ValueError("Data di fine non valida.")
        if fine <= inizio:
            raise ValueError("La data di fine deve essere successiva alla data di inizio.")

        cursor = self.conn.cursor()
        if escludi_id:
            cursor.execute(
                "SELECT * FROM esercizi WHERE id != ? AND ? <= data_fine AND ? >= data_inizio",
                (escludi_id, data_inizio, data_fine),
            )
        else:
            cursor.execute(
                "SELECT * FROM esercizi WHERE ? <= data_fine AND ? >= data_inizio",
                (data_inizio, data_fine),
            )
        altro = cursor.fetchone()
        if altro:
            raise ValueError(
                "Il periodo si sovrappone all'esercizio "
                f"\"{altro['descrizione']}\" ({periodo_label(altro['data_inizio'], altro['data_fine'])})."
            )

    def registrazioni_fuori_periodo(self, esercizio_id, data_inizio, data_fine):
        """Quante registrazioni dell'esercizio resterebbero fuori dal periodo indicato."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM registrazioni WHERE esercizio_id = ? "
            "AND (data < ? OR data > ?)",
            (esercizio_id, data_inizio, data_fine),
        )
        return cursor.fetchone()[0]

    def elimina_esercizio(self, esercizio_id):
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM registrazioni WHERE esercizio_id = ?", (esercizio_id,)
        )
        if cursor.fetchone()[0] > 0:
            raise ValueError("Impossibile eliminare: l'esercizio contiene registrazioni.")
        cursor.execute("DELETE FROM esercizi WHERE id = ?", (esercizio_id,))
        self.conn.commit()

    def chiudi_esercizio(self, esercizio_id, data_chiusura):
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE esercizi SET data_chiusura = ? WHERE id = ?",
            (data_chiusura, esercizio_id),
        )
        self.conn.commit()

    def riapri_esercizio(self, esercizio_id):
        cursor = self.conn.cursor()
        cursor.execute(
            "UPDATE esercizi SET data_chiusura = NULL WHERE id = ?",
            (esercizio_id,),
        )
        self.conn.commit()

    # --- Conti ---

    def get_conti(self):
        """Tutti i conti ordinati gerarchicamente: padre, poi figli, poi prossimo padre."""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT c.*, p.codice as padre_codice, p.nome as padre_nome
            FROM conti c
            LEFT JOIN conti p ON p.id = c.padre_id
            ORDER BY COALESCE(p.codice, c.codice), c.padre_id IS NOT NULL, c.codice
        """)
        return cursor.fetchall()

    def get_conti_padri(self):
        """Solo i conti che non hanno padre (conti principali)."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM conti WHERE padre_id IS NULL ORDER BY codice")
        return cursor.fetchall()

    def get_sottoconti(self, padre_id):
        """Sottoconti di un conto padre."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM conti WHERE padre_id = ? ORDER BY codice", (padre_id,))
        return cursor.fetchall()

    def get_conto(self, conto_id):
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT c.*, p.codice as padre_codice, p.nome as padre_nome
            FROM conti c
            LEFT JOIN conti p ON p.id = c.padre_id
            WHERE c.id = ?
        """, (conto_id,))
        return cursor.fetchone()

    def _verifica_padre(self, padre_id, conto_id=None):
        """
        I livelli sono due, conto e sottoconto: il padre deve essere un conto
        principale e un conto con sottoconti non può diventare a sua volta un sottoconto.
        """
        if not padre_id:
            return
        padre = self.get_conto(padre_id)
        if not padre:
            raise ValueError("Conto padre non trovato.")
        if padre["padre_id"]:
            raise ValueError("Il conto padre deve essere un conto principale, non un sottoconto.")
        if conto_id and self.conto_ha_sottoconti(conto_id):
            raise ValueError(
                "Questo conto ha dei sottoconti: non può diventare a sua volta un sottoconto "
                "(i livelli sono due, conto e sottoconto)."
            )

    def crea_conto(self, codice, nome, tipo, padre_id=None):
        self._verifica_padre(padre_id)
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO conti (codice, nome, tipo, padre_id) VALUES (?, ?, ?, ?)",
            (codice, nome, tipo, padre_id),
        )
        self.conn.commit()
        return cursor.lastrowid

    def modifica_conto(self, conto_id, codice, nome, tipo, padre_id=None):
        cursor = self.conn.cursor()
        # Impedisci che un conto sia padre di se stesso
        if padre_id == conto_id:
            raise ValueError("Un conto non può essere padre di se stesso.")
        # Impedisci loop: un padre non può diventare figlio di un suo figlio
        if padre_id:
            figli = self.get_sottoconti(conto_id)
            figli_ids = [f["id"] for f in figli]
            if padre_id in figli_ids:
                raise ValueError("Riferimento circolare: il padre selezionato è un figlio di questo conto.")
        self._verifica_padre(padre_id, conto_id)
        cursor.execute(
            "UPDATE conti SET codice = ?, nome = ?, tipo = ?, padre_id = ? WHERE id = ?",
            (codice, nome, tipo, padre_id, conto_id),
        )
        self.conn.commit()

    def elimina_conto(self, conto_id):
        cursor = self.conn.cursor()
        # Controlla movimenti
        cursor.execute(
            "SELECT COUNT(*) FROM movimenti WHERE conto_id = ?", (conto_id,)
        )
        if cursor.fetchone()[0] > 0:
            raise ValueError("Impossibile eliminare: il conto ha movimenti associati.")
        # Controlla sottoconti
        cursor.execute(
            "SELECT COUNT(*) FROM conti WHERE padre_id = ?", (conto_id,)
        )
        if cursor.fetchone()[0] > 0:
            raise ValueError("Impossibile eliminare: il conto ha sottoconti.")
        cursor.execute("DELETE FROM conti WHERE id = ?", (conto_id,))
        self.conn.commit()

    def conto_ha_movimenti(self, conto_id):
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM movimenti WHERE conto_id = ?", (conto_id,)
        )
        return cursor.fetchone()[0] > 0

    def conto_ha_sottoconti(self, conto_id):
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM conti WHERE padre_id = ?", (conto_id,)
        )
        return cursor.fetchone()[0] > 0

    # --- Registrazioni ---

    def get_prossimo_numero(self, esercizio_id):
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT COALESCE(MAX(numero), 0) + 1 FROM registrazioni WHERE esercizio_id = ?",
            (esercizio_id,),
        )
        return cursor.fetchone()[0]

    def _verifica_esercizio_aperto(self, esercizio_id):
        """
        Le registrazioni di un esercizio chiuso non si aggiungono, modificano
        né eliminano: solleva ValueError con un messaggio leggibile.
        """
        esercizio = self.get_esercizio(esercizio_id)
        if not esercizio:
            raise ValueError("Esercizio non trovato.")
        if esercizio["data_chiusura"]:
            raise ValueError(
                f"L'esercizio \"{esercizio['descrizione']}\" è chiuso: per cambiarne "
                "le registrazioni va prima riaperto (Esercizio > Gestione Esercizi)."
            )

    def _registrazione_modificabile(self, registrazione_id):
        """Riga della registrazione, dopo aver verificato che il suo esercizio sia aperto."""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM registrazioni WHERE id = ?", (registrazione_id,))
        registrazione = cursor.fetchone()
        if not registrazione:
            raise ValueError("Registrazione non trovata.")
        self._verifica_esercizio_aperto(registrazione["esercizio_id"])
        return registrazione

    def crea_registrazione(self, esercizio_id, data, descrizione, movimenti):
        """
        Crea una registrazione con i relativi movimenti.
        movimenti: lista di tuple (conto_id, dare, avere)
        """
        self._verifica_esercizio_aperto(esercizio_id)
        with self.conn:  # tutto o niente: mai una registrazione con un movimento solo
            return self._inserisci_registrazione(esercizio_id, data, descrizione, movimenti)

    def _inserisci_registrazione(self, esercizio_id, data, descrizione, movimenti):
        """Inserisce testata e movimenti; la transazione la gestisce chi chiama."""
        cursor = self.conn.cursor()
        numero = self.get_prossimo_numero(esercizio_id)
        cursor.execute(
            "INSERT INTO registrazioni (esercizio_id, data, numero, descrizione) VALUES (?, ?, ?, ?)",
            (esercizio_id, data, numero, descrizione),
        )
        registrazione_id = cursor.lastrowid
        for conto_id, dare, avere in movimenti:
            cursor.execute(
                "INSERT INTO movimenti (registrazione_id, conto_id, dare, avere) VALUES (?, ?, ?, ?)",
                (registrazione_id, conto_id, dare, avere),
            )
        return registrazione_id

    def get_registrazioni(self, esercizio_id):
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT r.id, r.data, r.numero, r.descrizione,
                   m.conto_id, c.codice, c.nome, m.dare, m.avere
            FROM registrazioni r
            JOIN movimenti m ON m.registrazione_id = r.id
            JOIN conti c ON c.id = m.conto_id
            WHERE r.esercizio_id = ?
            ORDER BY r.data, r.numero, m.id
            """,
            (esercizio_id,),
        )
        return cursor.fetchall()

    def modifica_registrazione(self, registrazione_id, data, descrizione, movimenti):
        """
        Aggiorna data, causale e movimenti di una registrazione; il numero resta lo stesso.
        movimenti: lista di tuple (conto_id, dare, avere)
        """
        self._registrazione_modificabile(registrazione_id)
        cursor = self.conn.cursor()
        with self.conn:  # tutto o niente
            cursor.execute(
                "UPDATE registrazioni SET data = ?, descrizione = ? WHERE id = ?",
                (data, descrizione, registrazione_id),
            )
            cursor.execute(
                "DELETE FROM movimenti WHERE registrazione_id = ?", (registrazione_id,)
            )
            for conto_id, dare, avere in movimenti:
                cursor.execute(
                    "INSERT INTO movimenti (registrazione_id, conto_id, dare, avere) VALUES (?, ?, ?, ?)",
                    (registrazione_id, conto_id, dare, avere),
                )

    # --- Numerazione in ordine di data ---

    def data_ultima_registrazione(self, esercizio_id, escludi_id=None):
        """Data più recente tra le registrazioni dell'esercizio (None se non ce ne sono)."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT MAX(data) FROM registrazioni WHERE esercizio_id = ? AND id != ?",
            (esercizio_id, escludi_id or 0),
        )
        return cursor.fetchone()[0]

    def _numerazione_cronologica(self, esercizio_id):
        """Coppie (id, numero attuale, numero in ordine di data) delle registrazioni dell'esercizio."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT id, numero FROM registrazioni WHERE esercizio_id = ? ORDER BY data, numero, id",
            (esercizio_id,),
        )
        return [(r["id"], r["numero"], i) for i, r in enumerate(cursor.fetchall(), 1)]

    def conta_numeri_fuori_ordine(self, esercizio_id):
        """Quante registrazioni cambierebbero numero rinumerando in ordine di data."""
        return sum(1 for _id, attuale, nuovo in self._numerazione_cronologica(esercizio_id) if attuale != nuovo)

    def rinumera_in_ordine_di_data(self, esercizio_id):
        """
        Rinumera le registrazioni dell'esercizio 1, 2, 3... in ordine di data
        (a parità di data resta l'ordine dei numeri attuali). Solo esercizi aperti.
        Restituisce quante registrazioni hanno cambiato numero.
        """
        self._verifica_esercizio_aperto(esercizio_id)
        cambi = [(nuovo, rid) for rid, attuale, nuovo in self._numerazione_cronologica(esercizio_id)
                 if attuale != nuovo]
        with self.conn:
            self.conn.executemany("UPDATE registrazioni SET numero = ? WHERE id = ?", cambi)
        return len(cambi)

    def conta_registrazioni_successive(self, esercizio_id, numero):
        """Quante registrazioni dell'esercizio hanno un numero più alto (quelle da rinumerare)."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM registrazioni WHERE esercizio_id = ? AND numero > ?",
            (esercizio_id, numero),
        )
        return cursor.fetchone()[0]

    def elimina_registrazione(self, registrazione_id, rinumera=False):
        """
        Elimina una registrazione con i suoi movimenti.
        Con rinumera=True le registrazioni successive dello stesso esercizio
        scalano di un numero, così al posto di quella eliminata non resta un buco.
        """
        registrazione = self._registrazione_modificabile(registrazione_id)
        cursor = self.conn.cursor()
        with self.conn:  # tutto o niente
            cursor.execute(
                "DELETE FROM movimenti WHERE registrazione_id = ?", (registrazione_id,)
            )
            cursor.execute(
                "DELETE FROM registrazioni WHERE id = ?", (registrazione_id,)
            )
            if rinumera:
                cursor.execute(
                    "UPDATE registrazioni SET numero = numero - 1 "
                    "WHERE esercizio_id = ? AND numero > ?",
                    (registrazione["esercizio_id"], registrazione["numero"]),
                )

    def storna_registrazione(self, registrazione_id, data, descrizione):
        """
        Storno: nuova registrazione con gli stessi conti e importi ma Dare e Avere
        invertiti, che annulla l'effetto dell'originale (l'originale resta com'è).
        Va nell'esercizio che contiene la data indicata, che deve essere aperto:
        così si può stornare anche una registrazione di un esercizio già chiuso.
        Restituisce l'id della registrazione di storno.
        """
        esercizio = self.get_esercizio_per_data(data)
        if not esercizio:
            raise ValueError(f"Nessun esercizio comprende la data {format_display(data)}.")
        if esercizio["data_chiusura"]:
            raise ValueError(
                f"La data {format_display(data)} cade nell'esercizio "
                f"\"{esercizio['descrizione']}\", che è chiuso."
            )
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT conto_id, dare, avere FROM movimenti WHERE registrazione_id = ? ORDER BY id",
            (registrazione_id,),
        )
        movimenti = [(m["conto_id"], m["avere"], m["dare"]) for m in cursor.fetchall()]
        if not movimenti:
            raise ValueError("Registrazione non trovata.")
        return self.crea_registrazione(esercizio["id"], data, descrizione, movimenti)

    # --- Riporto dei saldi tra esercizi ---

    CAUSALE_APERTURA = "Saldo di apertura"

    def get_esercizio_precedente(self, esercizio_id):
        """L'esercizio che finisce più di recente prima dell'inizio di questo (None se nessuno)."""
        esercizio = self.get_esercizio(esercizio_id)
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT * FROM esercizi WHERE data_fine < ? ORDER BY data_fine DESC LIMIT 1",
            (esercizio["data_inizio"],),
        )
        return cursor.fetchone()

    def saldi_da_riportare(self, esercizio_id, contropartita_id=None):
        """
        Saldi dei conti di ATTIVO e PASSIVO alla fine dell'esercizio, da riportare
        nel successivo: lista di (conto, importo_dare, importo_avere), uno dei due a zero.
        La contropartita dell'apertura (patrimonio netto) è esclusa: riceve la differenza.
        """
        righe = []
        for r in self.get_saldi(esercizio_id):
            if r["tipo"] not in ("ATTIVO", "PASSIVO") or r["id"] == contropartita_id:
                continue
            saldo = round(r["totale_dare"] - r["totale_avere"], 2)
            if saldo > 0:
                righe.append((r, saldo, 0))
            elif saldo < 0:
                righe.append((r, 0, -saldo))
        return righe

    def conta_aperture(self, esercizio_id):
        """Registrazioni di apertura già presenti nell'esercizio (riconosciute dalla causale)."""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT COUNT(*) FROM registrazioni WHERE esercizio_id = ? AND descrizione LIKE ?",
            (esercizio_id, self.CAUSALE_APERTURA + "%"),
        )
        return cursor.fetchone()[0]

    def registra_apertura(self, esercizio_id, da_esercizio_id, contropartita_id):
        """
        Riporta i saldi di attivo e passivo dell'esercizio da_esercizio_id all'inizio
        di esercizio_id: una registrazione per conto, con contropartita il conto di
        patrimonio netto indicato (che alla fine ha saldo = attività - passività).
        Tutto o niente. Restituisce il numero di registrazioni create.
        """
        self._verifica_esercizio_aperto(esercizio_id)
        esercizio = self.get_esercizio(esercizio_id)
        precedente = self.get_esercizio(da_esercizio_id)
        causale = f"{self.CAUSALE_APERTURA} (da {precedente['descrizione']})"
        righe = self.saldi_da_riportare(da_esercizio_id, contropartita_id)
        with self.conn:
            for conto, dare, avere in righe:
                if dare:
                    movimenti = [(conto["id"], dare, 0), (contropartita_id, 0, dare)]
                else:
                    movimenti = [(contropartita_id, avere, 0), (conto["id"], 0, avere)]
                self._inserisci_registrazione(esercizio_id, esercizio["data_inizio"], causale, movimenti)
        return len(righe)

    # --- Saldi ---

    def get_saldi(self, esercizio_id):
        """
        Saldi dell'esercizio ordinati gerarchicamente: padre, figli, prossimo padre.
        Contano solo i movimenti delle registrazioni di quell'esercizio.
        """
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT c.id, c.codice, c.nome, c.tipo, c.padre_id,
                   p.codice as padre_codice,
                   COALESCE(SUM(m.dare), 0) as totale_dare,
                   COALESCE(SUM(m.avere), 0) as totale_avere
            FROM conti c
            LEFT JOIN conti p ON p.id = c.padre_id
            LEFT JOIN movimenti m ON m.conto_id = c.id
                AND m.registrazione_id IN (SELECT id FROM registrazioni WHERE esercizio_id = ?)
            GROUP BY c.id, c.codice, c.nome, c.tipo, c.padre_id, p.codice
            ORDER BY COALESCE(p.codice, c.codice), c.padre_id IS NOT NULL, c.codice
            """,
            (esercizio_id,),
        )
        return cursor.fetchall()

    def _righe_registrazioni(self, condizione, parametri):
        """Righe (movimenti) delle registrazioni scelte, con i dati del conto, in ordine."""
        cursor = self.conn.cursor()
        cursor.execute(
            f"""
            SELECT r.id, r.esercizio_id, r.numero, r.data, r.descrizione,
                   m.id AS movimento_id, m.conto_id, c.codice, c.nome, m.dare, m.avere
            FROM registrazioni r
            JOIN movimenti m ON m.registrazione_id = r.id
            JOIN conti c ON c.id = m.conto_id
            WHERE {condizione}
            ORDER BY r.data, r.numero, r.id, m.id
            """,
            parametri,
        )
        return cursor.fetchall()

    @staticmethod
    def _compatta(righe):
        """
        Una voce per registrazione. Per le registrazioni semplici (un conto in Dare e
        uno in Avere) è il formato di sempre: dare_*, avere_*, importo. Per quelle con
        più righe (es. fattura con IVA) dare_conto_id/avere_conto_id sono None se il
        lato ha più conti, dare_nome/avere_nome li elencano, e "righe" contiene tutto.
        """
        registrazioni = {}
        for r in righe:
            reg = registrazioni.get(r["id"])
            if reg is None:
                reg = registrazioni[r["id"]] = {
                    "id": r["id"], "esercizio_id": r["esercizio_id"], "numero": r["numero"],
                    "data": r["data"], "descrizione": r["descrizione"], "righe": [],
                }
            reg["righe"].append({
                "movimento_id": r["movimento_id"], "conto_id": r["conto_id"], "codice": r["codice"],
                "nome": r["nome"], "dare": r["dare"], "avere": r["avere"],
            })
        risultato = []
        for reg in registrazioni.values():
            in_dare = [x for x in reg["righe"] if x["dare"]]
            in_avere = [x for x in reg["righe"] if x["avere"]]
            for lato, righe_lato in (("dare", in_dare), ("avere", in_avere)):
                if len(righe_lato) == 1:
                    reg[f"{lato}_conto_id"] = righe_lato[0]["conto_id"]
                    reg[f"{lato}_codice"] = righe_lato[0]["codice"]
                    reg[f"{lato}_nome"] = righe_lato[0]["nome"]
                else:
                    reg[f"{lato}_conto_id"] = None
                    reg[f"{lato}_codice"] = "diversi"
                    reg[f"{lato}_nome"] = ", ".join(x["codice"] for x in righe_lato)
            reg["importo"] = round(sum(x["dare"] for x in reg["righe"]), 2)
            reg["semplice"] = len(in_dare) == 1 and len(in_avere) == 1 and len(reg["righe"]) == 2
            risultato.append(reg)
        return risultato

    def get_registrazioni_compatte(self, esercizio_id):
        """Una voce per registrazione dell'esercizio (vedi _compatta), in ordine di data e numero."""
        return self._compatta(self._righe_registrazioni("r.esercizio_id = ?", (esercizio_id,)))

    def get_registrazione_compatta(self, registrazione_id):
        """Una sola registrazione, nello stesso formato (None se non esiste)."""
        regs = self._compatta(self._righe_registrazioni("r.id = ?", (registrazione_id,)))
        return regs[0] if regs else None

    def get_causali_usate(self, esercizio_id=None):
        """Restituisce le causali già utilizzate (per autocompletamento)."""
        cursor = self.conn.cursor()
        if esercizio_id:
            cursor.execute(
                "SELECT DISTINCT descrizione FROM registrazioni WHERE esercizio_id = ? ORDER BY descrizione",
                (esercizio_id,),
            )
        else:
            cursor.execute(
                "SELECT DISTINCT descrizione FROM registrazioni ORDER BY descrizione"
            )
        return [row[0] for row in cursor.fetchall()]

    def get_giornale_export(self, esercizio_id):
        """Dati per export del libro giornale: una voce per registrazione, con tutte le righe."""
        return self.get_registrazioni_compatte(esercizio_id)

    def ha_registrazioni_composte(self, esercizio_id):
        """True se nell'esercizio c'è almeno una registrazione con più di due righe."""
        cursor = self.conn.cursor()
        cursor.execute(
            """SELECT 1 FROM movimenti m JOIN registrazioni r ON r.id = m.registrazione_id
               WHERE r.esercizio_id = ? GROUP BY m.registrazione_id HAVING COUNT(*) > 2 LIMIT 1""",
            (esercizio_id,),
        )
        return cursor.fetchone() is not None
