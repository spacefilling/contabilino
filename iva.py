"""
Contabilino - Modulo IVA (facoltativo)
Registri IVA sezionali (vendite, acquisti, corrispettivi), documenti con le
righe per aliquota, scritture contabili generate dai documenti, liquidazione
periodica mensile o trimestrale.

Il modulo si attiva da Strumenti > Moduli: finché è spento queste tabelle restano
vuote e il programma funziona come prima. I periodi IVA seguono l'anno solare
(anche se l'esercizio contabile è a cavallo di due anni).

Limiti (vedi anche il manuale):
- la detrazione dell'IVA sugli acquisti segue la data di registrazione del
  documento (non gestisce la registrazione entro il 15 del mese successivo
  con imputazione al mese precedente, né la data di ricezione SdI);
- niente pro-rata generale, IVA per cassa, ventilazione dei corrispettivi,
  regimi speciali (agricoltura, editoria, margine...), split payment, plafond;
- le scadenze e i versamenti (F24) si registrano a mano.
"""

from datetime import date

# Tipi di registro e di documento
VENDITE, ACQUISTI, CORRISPETTIVI = "VENDITE", "ACQUISTI", "CORRISPETTIVI"
FATTURA, NOTA_CREDITO, DOC_CORRISPETTIVI, AUTOFATTURA = "FATTURA", "NOTA_CREDITO", "CORRISPETTIVI", "AUTOFATTURA"

MINIMO_VERSAMENTO = 25.82  # sotto questa cifra l'IVA a debito si riporta al periodo successivo
INTERESSI_TRIMESTRALI = 1.0  # % sull'IVA dovuta da chi liquida ogni trimestre

MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto",
        "settembre", "ottobre", "novembre", "dicembre"]

REGISTRI_PREDEFINITI = [
    ("V", "Registro IVA vendite", VENDITE),
    ("A", "Registro IVA acquisti", ACQUISTI),
    ("C", "Registro dei corrispettivi", CORRISPETTIVI),
]

# codice, descrizione, percentuale, natura (per le operazioni senza imposta)
ALIQUOTE_PREDEFINITE = [
    ("22", "IVA 22%", 22.0, None),
    ("10", "IVA 10%", 10.0, None),
    ("5", "IVA 5%", 5.0, None),
    ("4", "IVA 4%", 4.0, None),
    ("N1", "Escluse ex art. 15", 0.0, "N1"),
    ("N2.2", "Non soggette - altri casi", 0.0, "N2.2"),
    ("N3.1", "Non imponibili - esportazioni", 0.0, "N3.1"),
    ("N3.2", "Non imponibili - cessioni intracomunitarie", 0.0, "N3.2"),
    ("N4", "Esenti (art. 10)", 0.0, "N4"),
    ("N5", "Regime del margine / IVA non esposta", 0.0, "N5"),
]

SCHEMA = """
    CREATE TABLE IF NOT EXISTS registri_iva (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codice TEXT NOT NULL UNIQUE,
        descrizione TEXT NOT NULL,
        tipo TEXT NOT NULL CHECK(tipo IN ('VENDITE', 'ACQUISTI', 'CORRISPETTIVI')),
        attivo INTEGER NOT NULL DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS aliquote_iva (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        codice TEXT NOT NULL UNIQUE,
        descrizione TEXT NOT NULL,
        percentuale REAL NOT NULL DEFAULT 0,
        natura TEXT,
        attiva INTEGER NOT NULL DEFAULT 1
    );
    CREATE TABLE IF NOT EXISTS documenti_iva (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        registrazione_id INTEGER NOT NULL REFERENCES registrazioni(id) ON DELETE CASCADE,
        registro_id INTEGER NOT NULL REFERENCES registri_iva(id),
        protocollo INTEGER NOT NULL,
        data_registrazione TEXT NOT NULL,
        data_documento TEXT,
        numero_documento TEXT,
        controparte_id INTEGER REFERENCES conti(id),
        tipo_documento TEXT NOT NULL DEFAULT 'FATTURA'
            CHECK(tipo_documento IN ('FATTURA', 'NOTA_CREDITO', 'CORRISPETTIVI', 'AUTOFATTURA')),
        reverse_charge INTEGER NOT NULL DEFAULT 0,
        note TEXT
    );
    CREATE TABLE IF NOT EXISTS righe_iva (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        documento_id INTEGER NOT NULL REFERENCES documenti_iva(id) ON DELETE CASCADE,
        aliquota_id INTEGER NOT NULL REFERENCES aliquote_iva(id),
        conto_id INTEGER REFERENCES conti(id),
        imponibile REAL NOT NULL,
        imposta REAL NOT NULL,
        detraibile REAL NOT NULL DEFAULT 100
    );
    CREATE TABLE IF NOT EXISTS liquidazioni_iva (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        anno INTEGER NOT NULL,
        periodicita TEXT NOT NULL CHECK(periodicita IN ('M', 'T')),
        periodo INTEGER NOT NULL,
        iva_debito REAL NOT NULL,
        iva_credito REAL NOT NULL,
        credito_precedente REAL NOT NULL DEFAULT 0,
        debito_precedente REAL NOT NULL DEFAULT 0,
        interessi REAL NOT NULL DEFAULT 0,
        acconto REAL NOT NULL DEFAULT 0,
        risultato REAL NOT NULL,
        registrazione_id INTEGER REFERENCES registrazioni(id) ON DELETE SET NULL,
        data_calcolo TEXT NOT NULL,
        UNIQUE (anno, periodicita, periodo)
    );
"""


def r2(valore):
    """Arrotondamento al centesimo, senza lo zero negativo."""
    return round(valore + 0.0, 2) + 0.0


def crea_tabelle(conn):
    """Tabelle del modulo IVA: solo aggiunte, non toccano i dati esistenti."""
    conn.executescript(SCHEMA)
    conn.commit()


# --- Impostazioni del modulo ---

CONTI_IVA = {
    # ruolo: (impostazione, codice proposto, nome, tipo)
    "acquisti": ("iva_conto_acquisti", "IVA su acquisti", "ATTIVO"),
    "vendite": ("iva_conto_vendite", "IVA su vendite", "PASSIVO"),
    "erario": ("iva_conto_erario", "Erario c/IVA", "PASSIVO"),
}


class ModuloIva:
    """Accesso ai dati del modulo IVA di un archivio (usa la connessione di Database)."""

    def __init__(self, db):
        self.db = db
        self.conn = db.conn

    # Impostazioni

    @property
    def periodicita(self):
        """ "M" = liquidazione mensile, "T" = trimestrale."""
        return self.db.get_impostazione("iva_periodicita", "M")

    def conto_ruolo(self, ruolo):
        """Conto di un ruolo IVA ("acquisti", "vendite", "erario", "incasso_corrispettivi")."""
        valore = self.db.get_impostazione(f"iva_conto_{ruolo}")
        return int(valore) if valore and valore.isdigit() else None

    def imposta_conto_ruolo(self, ruolo, conto_id):
        self.db.set_impostazione(f"iva_conto_{ruolo}", conto_id)

    def registro_reverse_charge(self):
        """Registro vendite in cui si integra l'IVA delle fatture in reverse charge."""
        valore = self.db.get_impostazione("iva_registro_reverse")
        if valore and valore.isdigit() and self.get_registro(int(valore)):
            return int(valore)
        vendite = self.get_registri(VENDITE)
        return vendite[0]["id"] if vendite else None

    def prepara(self, crea_conti=True):
        """
        Al primo uso del modulo: registri e aliquote predefiniti e, se mancano,
        i conti IVA (con codici liberi). Non modifica nulla di ciò che esiste già.
        Restituisce l'elenco di ciò che ha creato, da mostrare all'utente.
        """
        creati = []
        with self.conn:
            for codice, descrizione, tipo in REGISTRI_PREDEFINITI:
                if not self.conn.execute("SELECT 1 FROM registri_iva WHERE codice = ?", (codice,)).fetchone():
                    self.conn.execute("INSERT INTO registri_iva (codice, descrizione, tipo) VALUES (?, ?, ?)",
                                      (codice, descrizione, tipo))
                    creati.append(f"registro {codice} - {descrizione}")
            for codice, descrizione, perc, natura in ALIQUOTE_PREDEFINITE:
                if not self.conn.execute("SELECT 1 FROM aliquote_iva WHERE codice = ?", (codice,)).fetchone():
                    self.conn.execute(
                        "INSERT INTO aliquote_iva (codice, descrizione, percentuale, natura) VALUES (?, ?, ?, ?)",
                        (codice, descrizione, perc, natura))
        if crea_conti:
            for ruolo, (_chiave, nome, tipo) in CONTI_IVA.items():
                if self.conto_ruolo(ruolo) and self.db.get_conto(self.conto_ruolo(ruolo)):
                    continue
                esistente = next((c for c in self.db.get_conti() if c["nome"].lower() == nome.lower()), None)
                if esistente:
                    self.imposta_conto_ruolo(ruolo, esistente["id"])
                    continue
                codice = self._codice_libero(tipo)
                conto_id = self.db.crea_conto(codice, nome, tipo)
                self.imposta_conto_ruolo(ruolo, conto_id)
                creati.append(f"conto {codice} - {nome}")
        return creati

    def _codice_libero(self, tipo):
        """Un codice conto non usato, vicino ai conti dello stesso tipo."""
        usati = {c["codice"] for c in self.db.get_conti()}
        base = {"ATTIVO": 150, "PASSIVO": 250, "COSTO": 450, "RICAVO": 550}[tipo]
        for n in range(base, base + 50):
            if str(n) not in usati:
                return str(n)
        n = 9000
        while str(n) in usati:
            n += 1
        return str(n)

    # Registri e aliquote

    def get_registri(self, tipo=None, solo_attivi=True):
        sql = "SELECT * FROM registri_iva WHERE 1 = 1"
        parametri = []
        if tipo:
            sql += " AND tipo = ?"
            parametri.append(tipo)
        if solo_attivi:
            sql += " AND attivo = 1"
        return self.conn.execute(sql + " ORDER BY tipo DESC, codice", parametri).fetchall()

    def get_registro(self, registro_id):
        return self.conn.execute("SELECT * FROM registri_iva WHERE id = ?", (registro_id,)).fetchone()

    def salva_registro(self, codice, descrizione, tipo, registro_id=None, attivo=True):
        with self.conn:
            if registro_id:
                usato = self.conn.execute("SELECT tipo FROM registri_iva WHERE id = ?", (registro_id,)).fetchone()
                if usato and usato["tipo"] != tipo and self._registro_usato(registro_id):
                    raise ValueError("Il registro contiene già documenti: il tipo non si può cambiare.")
                self.conn.execute("UPDATE registri_iva SET codice = ?, descrizione = ?, tipo = ?, attivo = ? WHERE id = ?",
                                  (codice, descrizione, tipo, 1 if attivo else 0, registro_id))
                return registro_id
            cur = self.conn.execute("INSERT INTO registri_iva (codice, descrizione, tipo, attivo) VALUES (?, ?, ?, ?)",
                                    (codice, descrizione, tipo, 1 if attivo else 0))
            return cur.lastrowid

    def _registro_usato(self, registro_id):
        return self.conn.execute("SELECT 1 FROM documenti_iva WHERE registro_id = ? LIMIT 1", (registro_id,)).fetchone()

    def get_aliquote(self, solo_attive=True):
        sql = "SELECT * FROM aliquote_iva" + (" WHERE attiva = 1" if solo_attive else "")
        return self.conn.execute(sql + " ORDER BY percentuale DESC, codice").fetchall()

    def get_aliquota(self, aliquota_id):
        return self.conn.execute("SELECT * FROM aliquote_iva WHERE id = ?", (aliquota_id,)).fetchone()

    def salva_aliquota(self, codice, descrizione, percentuale, natura=None, aliquota_id=None, attiva=True):
        with self.conn:
            if aliquota_id:
                self.conn.execute(
                    "UPDATE aliquote_iva SET codice = ?, descrizione = ?, percentuale = ?, natura = ?, attiva = ? WHERE id = ?",
                    (codice, descrizione, percentuale, natura or None, 1 if attiva else 0, aliquota_id))
                return aliquota_id
            cur = self.conn.execute(
                "INSERT INTO aliquote_iva (codice, descrizione, percentuale, natura, attiva) VALUES (?, ?, ?, ?, ?)",
                (codice, descrizione, percentuale, natura or None, 1 if attiva else 0))
            return cur.lastrowid

    # Documenti

    def prossimo_protocollo(self, registro_id, anno, escludi_documento=None):
        riga = self.conn.execute(
            "SELECT COALESCE(MAX(protocollo), 0) FROM documenti_iva WHERE registro_id = ? "
            "AND substr(data_registrazione, 1, 4) = ? AND id != ?",
            (registro_id, str(anno), escludi_documento or 0)).fetchone()
        return riga[0] + 1

    def documenti_della_registrazione(self, registrazione_id):
        return self.conn.execute(
            "SELECT d.*, r.codice AS registro_codice, r.tipo AS registro_tipo FROM documenti_iva d "
            "JOIN registri_iva r ON r.id = d.registro_id WHERE d.registrazione_id = ? ORDER BY d.id",
            (registrazione_id,)).fetchall()

    def righe_documento(self, documento_id):
        return self.conn.execute(
            "SELECT ri.*, a.codice AS aliquota_codice, a.percentuale, a.natura, a.descrizione AS aliquota_descrizione "
            "FROM righe_iva ri JOIN aliquote_iva a ON a.id = ri.aliquota_id WHERE ri.documento_id = ? ORDER BY ri.id",
            (documento_id,)).fetchall()

    @staticmethod
    def scorpora(lordo, percentuale):
        """Corrispettivi: dal totale lordo a (imponibile, imposta)."""
        imponibile = r2(lordo / (1 + percentuale / 100))
        return imponibile, r2(lordo - imponibile)

    def movimenti_documento(self, tipo_registro, tipo_documento, controparte_id, righe, reverse_charge=False):
        """
        Scrittura contabile di un documento IVA, come lista di (conto_id, dare, avere).
        righe: dict con conto_id, imponibile, imposta, detraibile (%).
        Righe sullo stesso conto vengono sommate.
        """
        conto_acq, conto_ven = self.conto_ruolo("acquisti"), self.conto_ruolo("vendite")
        if not conto_acq or not conto_ven:
            raise ValueError("Conti IVA non impostati: vai in IVA > Impostazioni IVA.")
        importi = {}  # conto_id -> saldo dare-avere

        def aggiungi(conto_id, valore):
            importi[conto_id] = importi.get(conto_id, 0) + valore

        segno = -1 if tipo_documento == NOTA_CREDITO else 1
        imponibile = sum(r["imponibile"] for r in righe)
        imposta = sum(r["imposta"] for r in righe)
        if tipo_registro == ACQUISTI:
            for r in righe:
                indetraibile = r2(r["imposta"] * (100 - r["detraibile"]) / 100)
                aggiungi(r["conto_id"], segno * (r["imponibile"] + indetraibile))
                aggiungi(conto_acq, segno * (r["imposta"] - indetraibile))
            if reverse_charge:
                aggiungi(controparte_id, -segno * imponibile)   # al fornitore solo l'imponibile
                aggiungi(conto_ven, -segno * imposta)           # integrazione: IVA a debito
            else:
                aggiungi(controparte_id, -segno * (imponibile + imposta))
        elif tipo_registro == VENDITE:
            for r in righe:
                aggiungi(r["conto_id"], -segno * r["imponibile"])
            aggiungi(conto_ven, -segno * imposta)
            aggiungi(controparte_id, segno * (imponibile + imposta))
        else:  # corrispettivi: incasso (cassa/banca) del lordo
            for r in righe:
                aggiungi(r["conto_id"], -r["imponibile"])
            aggiungi(conto_ven, -imposta)
            aggiungi(controparte_id, imponibile + imposta)
        movimenti = []
        for conto_id, saldo in importi.items():
            saldo = r2(saldo)
            if saldo > 0:
                movimenti.append((conto_id, saldo, 0))
            elif saldo < 0:
                movimenti.append((conto_id, 0, -saldo))
        if r2(sum(m[1] for m in movimenti) - sum(m[2] for m in movimenti)):
            raise ValueError("La scrittura del documento non quadra.")
        return movimenti

    def registra_documento(self, esercizio_id, registro_id, data_registrazione, causale, controparte_id,
                           righe, tipo_documento=FATTURA, data_documento=None, numero_documento=None,
                           reverse_charge=False, note=None, registrazione_id=None):
        """
        Registra (o, con registrazione_id, modifica) un documento IVA: la scrittura
        contabile nel giornale e il documento nel registro, tutto insieme.
        Con il reverse charge il documento compare anche nel registro vendite
        (integrazione). Restituisce l'id della registrazione.
        """
        registro = self.get_registro(registro_id)
        if not registro:
            raise ValueError("Registro IVA non trovato.")
        if not righe:
            raise ValueError("Il documento non ha righe.")
        if not controparte_id:
            raise ValueError("Indicare il cliente, il fornitore o il conto di incasso.")
        movimenti = self.movimenti_documento(registro["tipo"], tipo_documento, controparte_id, righe, reverse_charge)
        anno = int(data_registrazione[:4])
        db = self.db
        with self.conn:
            if registrazione_id:
                db._registrazione_modificabile(registrazione_id)
                vecchi = {d["registro_id"]: d for d in self.documenti_della_registrazione(registrazione_id)}
                self.conn.execute("UPDATE registrazioni SET data = ?, descrizione = ? WHERE id = ?",
                                  (data_registrazione, causale, registrazione_id))
                self.conn.execute("DELETE FROM movimenti WHERE registrazione_id = ?", (registrazione_id,))
                for conto_id, dare, avere in movimenti:
                    self.conn.execute("INSERT INTO movimenti (registrazione_id, conto_id, dare, avere) VALUES (?, ?, ?, ?)",
                                      (registrazione_id, conto_id, dare, avere))
                self.conn.execute("DELETE FROM documenti_iva WHERE registrazione_id = ?", (registrazione_id,))
            else:
                db._verifica_esercizio_aperto(esercizio_id)
                vecchi = {}
                registrazione_id = db._inserisci_registrazione(esercizio_id, data_registrazione, causale, movimenti)

            def inserisci(reg_id, tipo_doc):
                # Il protocollo resta quello di prima se il documento resta nello stesso registro e anno
                vecchio = vecchi.get(reg_id)
                if vecchio and vecchio["data_registrazione"][:4] == str(anno):
                    protocollo = vecchio["protocollo"]
                else:
                    protocollo = self.prossimo_protocollo(reg_id, anno)
                cur = self.conn.execute(
                    "INSERT INTO documenti_iva (registrazione_id, registro_id, protocollo, data_registrazione, "
                    "data_documento, numero_documento, controparte_id, tipo_documento, reverse_charge, note) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (registrazione_id, reg_id, protocollo, data_registrazione, data_documento, numero_documento,
                     controparte_id, tipo_doc, 1 if reverse_charge else 0, note))
                for r in righe:
                    self.conn.execute(
                        "INSERT INTO righe_iva (documento_id, aliquota_id, conto_id, imponibile, imposta, detraibile) "
                        "VALUES (?, ?, ?, ?, ?, ?)",
                        (cur.lastrowid, r["aliquota_id"], r.get("conto_id"), r2(r["imponibile"]), r2(r["imposta"]),
                         r.get("detraibile", 100) if registro["tipo"] == ACQUISTI else 100))

            inserisci(registro_id, tipo_documento)
            if reverse_charge and registro["tipo"] == ACQUISTI:
                registro_rc = self.registro_reverse_charge()
                if not registro_rc:
                    raise ValueError("Per il reverse charge serve un registro IVA vendite.")
                inserisci(registro_rc, AUTOFATTURA if tipo_documento == FATTURA else NOTA_CREDITO)
        return registrazione_id

    # Registri: righe per periodo

    def righe_registro(self, registro_id, dal, al):
        """Righe dei documenti del registro registrati nel periodo (date ISO, estremi inclusi)."""
        return self.conn.execute(
            """
            SELECT d.id AS documento_id, d.protocollo, d.data_registrazione, d.data_documento,
                   d.numero_documento, d.tipo_documento, d.reverse_charge,
                   c.codice AS controparte_codice, c.nome AS controparte_nome,
                   a.codice AS aliquota_codice, a.descrizione AS aliquota_descrizione, a.percentuale, a.natura,
                   ri.imponibile, ri.imposta, ri.detraibile
            FROM documenti_iva d
            JOIN righe_iva ri ON ri.documento_id = d.id
            JOIN aliquote_iva a ON a.id = ri.aliquota_id
            LEFT JOIN conti c ON c.id = d.controparte_id
            WHERE d.registro_id = ? AND d.data_registrazione BETWEEN ? AND ?
            ORDER BY d.data_registrazione, d.protocollo, ri.id
            """, (registro_id, dal, al)).fetchall()

    @staticmethod
    def segno_documento(tipo_documento):
        return -1 if tipo_documento == NOTA_CREDITO else 1

    def totali_registro(self, registro_id, dal, al):
        """Totali per aliquota: {codice aliquota: dict(descrizione, imponibile, imposta, detraibile)}."""
        totali = {}
        for r in self.righe_registro(registro_id, dal, al):
            s = self.segno_documento(r["tipo_documento"])
            t = totali.setdefault(r["aliquota_codice"], {
                "descrizione": r["aliquota_descrizione"], "percentuale": r["percentuale"],
                "imponibile": 0.0, "imposta": 0.0, "detraibile": 0.0})
            t["imponibile"] += s * r["imponibile"]
            t["imposta"] += s * r["imposta"]
            t["detraibile"] += s * r2(r["imposta"] * r["detraibile"] / 100)
        for t in totali.values():
            for k in ("imponibile", "imposta", "detraibile"):
                t[k] = r2(t[k])
        return dict(sorted(totali.items(), key=lambda kv: -kv[1]["percentuale"]))

    # Liquidazione

    @staticmethod
    def periodo_date(anno, periodicita, periodo):
        """Primo e ultimo giorno del mese (M) o del trimestre (T), in ISO."""
        if periodicita == "M":
            inizio_mese, fine_mese = periodo, periodo
        else:
            inizio_mese, fine_mese = 3 * periodo - 2, 3 * periodo
        dal = date(anno, inizio_mese, 1)
        al = date(anno + (fine_mese == 12), 1 if fine_mese == 12 else fine_mese + 1, 1)
        return dal.isoformat(), date.fromordinal(al.toordinal() - 1).isoformat()

    @staticmethod
    def nome_periodo(anno, periodicita, periodo):
        if periodicita == "M":
            return f"{MESI[periodo - 1]} {anno}"
        return f"{periodo}° trimestre {anno}"

    def calcola_liquidazione(self, anno, periodo, periodicita=None, credito_precedente=None, acconto=0.0):
        """
        Liquidazione IVA del periodo. Credito e debito precedenti si prendono dalla
        liquidazione salvata del periodo prima (stesso anno); per il primo periodo
        dell'anno il credito dell'anno precedente si indica a mano.
        Restituisce un dict con il dettaglio per registro e il risultato.
        """
        periodicita = periodicita or self.periodicita
        dal, al = self.periodo_date(anno, periodicita, periodo)
        dettaglio = []
        debito = credito = 0.0
        for reg in self.get_registri(solo_attivi=False):
            totali = self.totali_registro(reg["id"], dal, al)
            if not totali:
                continue
            imposta = r2(sum(t["imposta"] for t in totali.values()))
            detraibile = r2(sum(t["detraibile"] for t in totali.values()))
            if reg["tipo"] == ACQUISTI:
                credito += detraibile
                dettaglio.append({"registro": reg, "totali": totali, "debito": 0.0, "credito": detraibile})
            else:
                debito += imposta
                dettaglio.append({"registro": reg, "totali": totali, "debito": imposta, "credito": 0.0})

        precedente = None
        if periodo > 1:
            precedente = self.conn.execute(
                "SELECT * FROM liquidazioni_iva WHERE anno = ? AND periodicita = ? AND periodo = ?",
                (anno, periodicita, periodo - 1)).fetchone()
        debito_prec = 0.0
        if credito_precedente is None:
            credito_precedente = 0.0
            if precedente:
                if precedente["risultato"] < 0:
                    credito_precedente = -precedente["risultato"]
                elif precedente["risultato"] < MINIMO_VERSAMENTO:
                    debito_prec = precedente["risultato"]  # sotto il minimo: si somma a questo periodo
        saldo = r2(debito - credito - credito_precedente + debito_prec)
        interessi = r2(saldo * INTERESSI_TRIMESTRALI / 100) if periodicita == "T" and saldo > 0 else 0.0
        risultato = r2(saldo + interessi - acconto)
        return {
            "anno": anno, "periodicita": periodicita, "periodo": periodo, "dal": dal, "al": al,
            "nome": self.nome_periodo(anno, periodicita, periodo), "dettaglio": dettaglio,
            "iva_debito": r2(debito), "iva_credito": r2(credito),
            "credito_precedente": r2(credito_precedente), "debito_precedente": r2(debito_prec),
            "interessi": interessi, "acconto": r2(acconto), "risultato": risultato,
            "da_versare": risultato >= MINIMO_VERSAMENTO,
        }

    def salva_liquidazione(self, liq):
        with self.conn:
            self.conn.execute(
                """INSERT INTO liquidazioni_iva (anno, periodicita, periodo, iva_debito, iva_credito,
                       credito_precedente, debito_precedente, interessi, acconto, risultato, data_calcolo)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                   ON CONFLICT(anno, periodicita, periodo) DO UPDATE SET
                       iva_debito = excluded.iva_debito, iva_credito = excluded.iva_credito,
                       credito_precedente = excluded.credito_precedente,
                       debito_precedente = excluded.debito_precedente, interessi = excluded.interessi,
                       acconto = excluded.acconto, risultato = excluded.risultato,
                       data_calcolo = excluded.data_calcolo""",
                (liq["anno"], liq["periodicita"], liq["periodo"], liq["iva_debito"], liq["iva_credito"],
                 liq["credito_precedente"], liq["debito_precedente"], liq["interessi"], liq["acconto"],
                 liq["risultato"], date.today().isoformat()))

    def get_liquidazione(self, anno, periodicita, periodo):
        return self.conn.execute(
            "SELECT * FROM liquidazioni_iva WHERE anno = ? AND periodicita = ? AND periodo = ?",
            (anno, periodicita, periodo)).fetchone()

    def registra_giroconto(self, liq, esercizio_id):
        """
        Giroconto di liquidazione nel giornale, all'ultimo giorno del periodo:
        IVA su vendite e IVA su acquisti si chiudono su Erario c/IVA.
        (Il versamento con F24 si registra poi a parte: Erario c/IVA a Banca.)
        """
        conto_acq, conto_ven, erario = (self.conto_ruolo(r) for r in ("acquisti", "vendite", "erario"))
        if not (conto_acq and conto_ven and erario):
            raise ValueError("Conti IVA non impostati: vai in IVA > Impostazioni IVA.")
        movimenti = []
        if liq["iva_debito"]:
            movimenti.append((conto_ven, liq["iva_debito"], 0) if liq["iva_debito"] > 0 else (conto_ven, 0, -liq["iva_debito"]))
        if liq["iva_credito"]:
            movimenti.append((conto_acq, 0, liq["iva_credito"]) if liq["iva_credito"] > 0 else (conto_acq, -liq["iva_credito"], 0))
        differenza = r2(liq["iva_debito"] - liq["iva_credito"])
        if differenza > 0:
            movimenti.append((erario, 0, differenza))
        elif differenza < 0:
            movimenti.append((erario, -differenza, 0))
        if len(movimenti) < 2:
            raise ValueError("Nel periodo non c'è IVA da liquidare.")
        reg_id = self.db.crea_registrazione(esercizio_id, liq["al"], f"Liquidazione IVA {liq['nome']}", movimenti)
        with self.conn:
            self.conn.execute(
                "UPDATE liquidazioni_iva SET registrazione_id = ? WHERE anno = ? AND periodicita = ? AND periodo = ?",
                (reg_id, liq["anno"], liq["periodicita"], liq["periodo"]))
        return reg_id
