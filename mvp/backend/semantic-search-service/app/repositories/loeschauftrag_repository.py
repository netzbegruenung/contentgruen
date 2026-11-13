"""
Repository fuer die Tabelle ``loeschauftraege``: Loeschauftraege nach dem Widerruf
der Art.-9-Einwilligung (GLOSSARY.md "Loeschauftrag", DSFA R9b).

Den PostgreSQL-Teil des Loeschablaufs fuer einen Auftrag fuehrt ``ausfuehren`` aus:
dieselben Schritte fuer Einwuerfe und Saetze wie das Loeschkommando
(mvp/scripts/manual/person_loeschen.sql, docs/LOESCHKONZEPT.md Schritt 2), aber ohne
Konto, Anzeigename, Einwilligung und Meldungen: Das Konto bleibt.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import delete, func, select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from infrastructure.database.connection import AppDatabase, get_app_database
from infrastructure.database.models import (
    AusformuliertIn,
    Einwurf,
    LoeschauftragZeile,
    Satz,
    Sperre,
    User,
)
from services.anzeigename_service import EHEMALIGE_PERSON_KENNUNG, EHEMALIGE_PERSON_NAME

# Bis wann ein Admin den Loeschablauf ausfuehrt, ab dem Widerruf (DSFA R9b).
FRIST_TAGE = 7


@dataclass(frozen=True)
class Loeschauftrag:
    id: uuid.UUID
    user_id: str
    angelegt_am: datetime
    frist: datetime
    erledigt_am: Optional[datetime]


@dataclass(frozen=True)
class PostgresBericht:
    einwuerfe: int
    saetze: int


def _platzhalter() -> str:
    return f"{EHEMALIGE_PERSON_KENNUNG}-{uuid.uuid4()}"


class LoeschauftragRepository:
    def __init__(self, db: Optional[AppDatabase] = None):
        """``db``: eine AppDatabase; ohne Angabe die globale."""
        self.db = db if db is not None else get_app_database()

    def anlegen(self, user_id: str, session: Optional[Session] = None) -> None:
        """
        Einen offenen Auftrag anlegen, Frist FRIST_TAGE ab jetzt. Gibt es schon einen
        offenen, bleibt es bei ihm (Index idx_loeschauftraege_offen). Mit ``session``
        in deren Transaktion (Widerruf), sonst in einer eigenen.
        """
        anweisung = (
            insert(LoeschauftragZeile)
            .values(
                id=uuid.uuid4(),
                user_id=user_id,
                angelegt_am=func.now(),
                frist=func.now() + timedelta(days=FRIST_TAGE),
            )
            .on_conflict_do_nothing(
                index_elements=["user_id"],
                index_where=LoeschauftragZeile.erledigt_am.is_(None),
            )
        )
        if session is not None:
            session.execute(anweisung)
            return
        with self.db.get_session() as eigene:
            eigene.execute(anweisung)

    def offene(self) -> List[Loeschauftrag]:
        """Offene Auftraege, die mit der fruehesten Frist zuerst."""
        with self.db.get_session() as session:
            zeilen = session.execute(
                select(LoeschauftragZeile)
                .where(LoeschauftragZeile.erledigt_am.is_(None))
                .order_by(LoeschauftragZeile.frist, LoeschauftragZeile.id)
            ).scalars()
            return [_auftrag(z) for z in zeilen]

    def laden(self, auftrag_id: uuid.UUID) -> Optional[Loeschauftrag]:
        with self.db.get_session() as session:
            zeile = session.get(LoeschauftragZeile, auftrag_id)
            return _auftrag(zeile) if zeile is not None else None

    def ausfuehren(self, auftrag: Loeschauftrag) -> PostgresBericht:
        """
        Einwuerfe und Saetze der Person vom Personenbezug loesen und den Auftrag
        erledigen, in einer Transaktion: Scheitert ein Schritt, bleibt alles wie vorher
        und der Auftrag offen. Wiederholbar: Ein zweiter Lauf findet nichts mehr.

        - Eigene Einwuerfe loeschen; CASCADE nimmt Saetze und "ausformuliert in" daran mit.
        - Saetze an fremden Einwuerfen bleiben, je Satz mit eigenem Platzhalter und
          einer Zeile in ``users`` ("ehemalige Person"), wie im Loeschkommando.
        - ``destilled_by``: der Platzhalter des eigenen Satzes, sonst ein eigener.
        - ``raw_input_content_links.created_by`` leer; an Sperren ihrer Beitraege
          Autor und Widerspruch leer (sonst verbaende beides die Person mit Beitraegen).
        - Platzhalter ohne Satz aus ``users`` abraeumen.
        """
        uid = auftrag.user_id
        with self.db.get_session() as session:
            session.execute(
                update(AusformuliertIn)
                .where(AusformuliertIn.created_by == uid)
                .values(created_by=None)
            )
            session.execute(
                update(Sperre)
                .where(Sperre.autor == uid)
                .values(autor=None, widerspruch=None)
            )
            einwuerfe = session.execute(
                delete(Einwurf).where(Einwurf.submitted_by == uid)
            ).rowcount
            saetze = session.execute(
                select(Satz.id, Satz.raw_input_id).where(Satz.user_id == uid)
            ).all()
            for satz in saetze:
                ersatz = _platzhalter()
                session.execute(
                    update(Satz).where(Satz.id == satz.id).values(user_id=ersatz)
                )
                session.add(User(user_id=ersatz, anzeigename=EHEMALIGE_PERSON_NAME))
                session.execute(
                    update(Einwurf)
                    .where(Einwurf.id == satz.raw_input_id, Einwurf.destilled_by == uid)
                    .values(destilled_by=ersatz)
                )
            session.flush()
            # Wer den ersten Satz spaeter geleert hat: ein eigener Platzhalter je Einwurf,
            # ohne Zeile in users (kein Codepfad zeigt einen Namen zu destilled_by).
            session.execute(
                text(
                    "UPDATE raw_inputs SET destilled_by = :praefix || gen_random_uuid()"
                    " WHERE destilled_by = :uid"
                ),
                {"praefix": f"{EHEMALIGE_PERSON_KENNUNG}-", "uid": uid},
            )
            session.execute(
                delete(User).where(
                    User.user_id.like(f"{EHEMALIGE_PERSON_KENNUNG}-%"),
                    ~select(Satz.id).where(Satz.user_id == User.user_id).exists(),
                )
            )
            session.execute(
                update(LoeschauftragZeile)
                .where(
                    LoeschauftragZeile.id == auftrag.id,
                    LoeschauftragZeile.erledigt_am.is_(None),
                )
                .values(erledigt_am=func.now())
            )
            return PostgresBericht(einwuerfe=einwuerfe, saetze=len(saetze))

    def erledigte_loeschen_vor(self, grenze: datetime) -> int:
        """Erledigte Auftraege loeschen, die vor ``grenze`` erledigt wurden."""
        with self.db.get_session() as session:
            return session.execute(
                delete(LoeschauftragZeile).where(
                    LoeschauftragZeile.erledigt_am < grenze
                )
            ).rowcount


def _auftrag(zeile: LoeschauftragZeile) -> Loeschauftrag:
    return Loeschauftrag(
        id=zeile.id,
        user_id=zeile.user_id,
        angelegt_am=zeile.angelegt_am,
        frist=zeile.frist,
        erledigt_am=zeile.erledigt_am,
    )


_repository: Optional[LoeschauftragRepository] = None


def get_loeschauftrag_repository() -> LoeschauftragRepository:
    """Die globale Instanz holen oder anlegen."""
    global _repository
    if _repository is None:
        _repository = LoeschauftragRepository()
    return _repository
