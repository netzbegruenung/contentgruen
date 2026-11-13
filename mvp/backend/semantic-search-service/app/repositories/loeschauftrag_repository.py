"""
Repository fuer die Tabelle ``loeschauftraege``: Loeschauftraege nach dem Widerruf
der Art.-9-Einwilligung (GLOSSARY.md "Loeschauftrag", DSFA R9b).

Den PostgreSQL-Teil des Loeschablaufs fuer einen Auftrag fuehrt ``ausfuehren`` aus:
dieselben Schritte fuer Einwuerfe und Saetze wie das Loeschkommando
(mvp/scripts/manual/person_loeschen.sql, docs/LOESCHKONZEPT.md Schritt 2), aber ohne
Konto, Anzeigename, Einwilligung und Meldungen: Das Konto bleibt.

Erfasst wird nur, was bis zum Widerruf angelegt war (``Loeschauftrag.stichtag``);
was die Person nach einer neuen Einwilligung beitraegt, bleibt unberuehrt
(Entscheidung Maintainer, 13.11.2026).
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable, List, Optional

from sqlalchemy import delete, func, select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from infrastructure.database.connection import AppDatabase, get_app_database
from infrastructure.database.models import (
    Art9EinwilligungZeile,
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
    # Juengste Einwilligung nach dem Widerruf, falls die Person neu eingewilligt hat
    neu_eingewilligt_am: Optional[datetime] = None
    # Juengster Widerruf seit dem Anlegen (``laden``); widerruft die Person nach einer
    # neuen Einwilligung erneut, bleibt es bei einem offenen Auftrag, der dann auch
    # das Dazwischen erfasst.
    widerrufen_am: Optional[datetime] = None

    @property
    def stichtag(self) -> datetime:
        """Was bis hierhin angelegt war, erfasst der Auftrag; Spaeteres nicht."""
        return self.widerrufen_am or self.angelegt_am


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
        """
        Offene Auftraege, die mit der fruehesten Frist zuerst. Hat die Person nach dem
        Widerruf (``angelegt_am``) neu eingewilligt, steht der juengste Zeitpunkt in
        ``neu_eingewilligt_am``.
        """
        neu_eingewilligt = (
            select(func.max(Art9EinwilligungZeile.eingewilligt_am))
            .where(
                Art9EinwilligungZeile.user_id == LoeschauftragZeile.user_id,
                Art9EinwilligungZeile.eingewilligt_am > LoeschauftragZeile.angelegt_am,
            )
            .scalar_subquery()
        )
        with self.db.get_session() as session:
            zeilen = session.execute(
                select(LoeschauftragZeile, neu_eingewilligt)
                .where(LoeschauftragZeile.erledigt_am.is_(None))
                .order_by(LoeschauftragZeile.frist, LoeschauftragZeile.id)
            ).all()
            return [_auftrag(z, neu) for z, neu in zeilen]

    def ueberfaellige_zaehlen(self, jetzt: datetime) -> int:
        """Offene Auftraege, deren Frist vor ``jetzt`` lag."""
        with self.db.get_session() as session:
            return session.execute(
                select(func.count())
                .select_from(LoeschauftragZeile)
                .where(
                    LoeschauftragZeile.erledigt_am.is_(None),
                    LoeschauftragZeile.frist < jetzt,
                )
            ).scalar_one()

    def laden(self, auftrag_id: uuid.UUID) -> Optional[Loeschauftrag]:
        """
        Der Auftrag samt juengstem Widerruf der Person seit dem Anlegen
        (``widerrufen_am``, daraus ``stichtag``). Der Widerruf und das Anlegen laufen in
        einer Transaktion, ``now()`` ist dort derselbe Zeitpunkt; der Backfill legt
        Auftraege zum Zeitpunkt des Widerrufs an.
        """
        with self.db.get_session() as session:
            zeile = session.get(LoeschauftragZeile, auftrag_id)
            if zeile is None:
                return None
            widerrufen_am = session.execute(
                select(func.max(Art9EinwilligungZeile.widerrufen_am)).where(
                    Art9EinwilligungZeile.user_id == zeile.user_id,
                    Art9EinwilligungZeile.widerrufen_am >= zeile.angelegt_am,
                )
            ).scalar_one_or_none()
            return _auftrag(zeile, widerrufen_am=widerrufen_am)

    def ausfuehren(
        self, auftrag: Loeschauftrag, beitraege_behalten: Iterable[str] = ()
    ) -> PostgresBericht:
        """
        Einwuerfe und Saetze der Person vom Personenbezug loesen und den Auftrag
        erledigen, in einer Transaktion: Scheitert ein Schritt, bleibt alles wie vorher
        und der Auftrag offen. Wiederholbar: Ein zweiter Lauf findet nichts mehr.

        Nur was bis ``auftrag.stichtag`` angelegt war: Einwuerfe und Verknuepfungen nach
        ``created_at``, Saetze nach ``updated_at`` (einen Zeitpunkt des Anlegens hat
        ein Satz nicht; wer ihn nach einer neuen Einwilligung neu speichert, hat ihn
        unter ihr beigetragen). Sperren haengen am Beitrag: Ihr Autor geht, ausser
        an den Beitraegen in ``beitraege_behalten`` (nach einer neuen Einwilligung
        angelegt, in Qdrant nicht anonymisiert).

        - Eigene Einwuerfe loeschen; CASCADE nimmt Saetze und "ausformuliert in" daran mit.
        - Saetze an fremden Einwuerfen bleiben, je Satz mit eigenem Platzhalter und
          einer Zeile in ``users`` ("ehemalige Person"), wie im Loeschkommando.
        - ``destilled_by``: der Platzhalter des eigenen Satzes, sonst ein eigener.
        - ``raw_input_content_links.created_by`` leer; an Sperren ihrer Beitraege
          Autor und Widerspruch leer (sonst verbaende beides die Person mit Beitraegen).
        - Platzhalter ohne Satz aus ``users`` abraeumen.
        """
        uid = auftrag.user_id
        bis = auftrag.stichtag
        behalten = _uuids(beitraege_behalten)
        with self.db.get_session() as session:
            session.execute(
                update(AusformuliertIn)
                .where(
                    AusformuliertIn.created_by == uid,
                    AusformuliertIn.created_at <= bis,
                )
                .values(created_by=None)
            )
            sperren = update(Sperre).where(Sperre.autor == uid)
            if behalten:
                sperren = sperren.where(Sperre.content_id.notin_(behalten))
            session.execute(sperren.values(autor=None, widerspruch=None))
            einwuerfe = session.execute(
                delete(Einwurf).where(
                    Einwurf.submitted_by == uid, Einwurf.created_at <= bis
                )
            ).rowcount
            saetze = session.execute(
                select(Satz.id, Satz.raw_input_id).where(
                    Satz.user_id == uid, Satz.updated_at <= bis
                )
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
            # Nicht an Einwuerfen von nach dem Stichtag und nicht, wo ein Satz der Person
            # bleibt (nach einer neuen Einwilligung gespeichert).
            session.execute(
                text(
                    "UPDATE raw_inputs SET destilled_by = :praefix || gen_random_uuid()"
                    " WHERE destilled_by = :uid AND created_at <= :bis"
                    " AND NOT EXISTS (SELECT 1 FROM raw_input_drafts AS d"
                    " WHERE d.raw_input_id = raw_inputs.id AND d.user_id = :uid)"
                ),
                {"praefix": f"{EHEMALIGE_PERSON_KENNUNG}-", "uid": uid, "bis": bis},
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


def _auftrag(
    zeile: LoeschauftragZeile,
    neu_eingewilligt_am: Optional[datetime] = None,
    widerrufen_am: Optional[datetime] = None,
) -> Loeschauftrag:
    return Loeschauftrag(
        id=zeile.id,
        user_id=zeile.user_id,
        angelegt_am=zeile.angelegt_am,
        frist=zeile.frist,
        erledigt_am=zeile.erledigt_am,
        neu_eingewilligt_am=neu_eingewilligt_am,
        widerrufen_am=widerrufen_am,
    )


def _uuids(kennungen: Iterable[str]) -> List[uuid.UUID]:
    """Qdrant-Punktkennungen als UUID (Sperre.content_id); andere gibt es dort nicht."""
    ergebnis = []
    for kennung in kennungen:
        try:
            ergebnis.append(uuid.UUID(str(kennung)))
        except ValueError:
            continue
    return ergebnis


_repository: Optional[LoeschauftragRepository] = None


def get_loeschauftrag_repository() -> LoeschauftragRepository:
    """Die globale Instanz holen oder anlegen."""
    global _repository
    if _repository is None:
        _repository = LoeschauftragRepository()
    return _repository
