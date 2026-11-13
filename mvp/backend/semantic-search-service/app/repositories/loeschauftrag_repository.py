"""
Repository fuer die Tabelle ``loeschauftraege``: Loeschauftraege nach dem Widerruf
der Art.-9-Einwilligung (GLOSSARY.md "Loeschauftrag", DSFA R9b).

Den PostgreSQL-Teil des Loeschablaufs fuer einen Auftrag fuehrt ``ausfuehren`` aus:
dieselben Schritte fuer Einwuerfe und Saetze wie das Loeschkommando
(mvp/scripts/manual/person_loeschen.sql, docs/LOESCHKONZEPT.md Schritt 2), aber ohne
Konto, Anzeigename, Einwilligung und Meldungen: Das Konto bleibt.

Was die Person nach einer neuen Einwilligung beitraegt, bleibt unberuehrt
(Entscheidung Maintainer, 13.11.2026): Obergrenze ist die frueheste Einwilligung nach
dem juengsten Widerruf, zu irgendeinem Wortlaut (``Loeschauftrag.obergrenze``).
Ohne eine solche erfasst der Auftrag alles, auch Nachzuegler, die kurz vor dem
Widerruf geprueft und erst danach gespeichert wurden.
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


class StandGeaendert(RuntimeError):
    """Seit dem Laden hat die Person widerrufen oder neu eingewilligt."""


@dataclass(frozen=True)
class Loeschauftrag:
    id: uuid.UUID
    user_id: str
    angelegt_am: datetime
    frist: datetime
    erledigt_am: Optional[datetime]
    # Juengster Widerruf der Person (``offene``, ``laden``); widerruft sie nach einer
    # neuen Einwilligung erneut, bleibt es bei einem offenen Auftrag.
    widerrufen_am: Optional[datetime] = None
    # Frueheste Einwilligung nach dem juengsten Widerruf, zu irgendeinem Wortlaut:
    # Was ab da angelegt ist, erfasst der Auftrag nicht. Ohne: alles.
    obergrenze: Optional[datetime] = None

    @property
    def neu_eingewilligt_am(self) -> Optional[datetime]:
        """Fuer die Liste der Admins: die neue Einwilligung, ab der nichts mehr geht."""
        return self.obergrenze


@dataclass(frozen=True)
class _Stand:
    widerrufen_am: Optional[datetime]
    obergrenze: Optional[datetime]


def _stand(session: Session, user_id: str, angelegt_am: datetime) -> _Stand:
    """
    Juengster Widerruf und die Obergrenze danach, frisch aus der Datenbank.

    Obergrenze ist die frueheste Einwilligung nach dem juengsten Widerruf und nicht vor
    dem Anlegen des Auftrags, zu irgendeinem Wortlaut: Jede gespeicherte Einwilligung
    galt, als sie gegeben wurde (POST nimmt nur geltende an), und die Zusage "Was ich
    nach einer neuen Einwilligung beitrage, bleibt" haengt nicht daran, ob spaeter ein
    neuer Wortlaut kommt. Fehlt eine Zeile mit Widerruf, gibt es keine Obergrenze: Der
    Auftrag erfasst alles.
    """
    widerrufen_am = session.execute(
        select(func.max(Art9EinwilligungZeile.widerrufen_am)).where(
            Art9EinwilligungZeile.user_id == user_id
        )
    ).scalar_one_or_none()
    if widerrufen_am is None:
        return _Stand(widerrufen_am=None, obergrenze=None)
    obergrenze = session.execute(
        select(func.min(Art9EinwilligungZeile.eingewilligt_am)).where(
            Art9EinwilligungZeile.user_id == user_id,
            Art9EinwilligungZeile.eingewilligt_am > max(widerrufen_am, angelegt_am),
        )
    ).scalar_one_or_none()
    return _Stand(widerrufen_am=widerrufen_am, obergrenze=obergrenze)


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

        Den offenen Auftrag sperrt es vorher (FOR UPDATE): Fuehrt ihn ein Admin gerade
        aus (``ausfuehren`` sperrt ihn ebenso), wartet der Widerruf. Danach ist der
        Auftrag erledigt, die Sperre findet ihn nicht mehr, und es entsteht ein neuer;
        so geht ein Widerruf waehrend der Ausfuehrung nicht verloren.
        """
        sperren = (
            select(LoeschauftragZeile.id)
            .where(
                LoeschauftragZeile.user_id == user_id,
                LoeschauftragZeile.erledigt_am.is_(None),
            )
            .with_for_update()
        )
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
            session.execute(sperren).all()
            session.execute(anweisung)
            return
        with self.db.get_session() as eigene:
            eigene.execute(sperren).all()
            eigene.execute(anweisung)

    def offene(self) -> List[Loeschauftrag]:
        """
        Offene Auftraege, die mit der fruehesten Frist zuerst, je mit juengstem
        Widerruf und Obergrenze (eine neue Einwilligung nach diesem Widerruf). Offene
        Auftraege sind wenige; je Auftrag zwei Abfragen ueber den Index.
        """
        with self.db.get_session() as session:
            zeilen = (
                session.execute(
                    select(LoeschauftragZeile)
                    .where(LoeschauftragZeile.erledigt_am.is_(None))
                    .order_by(LoeschauftragZeile.frist, LoeschauftragZeile.id)
                )
                .scalars()
                .all()
            )
            return [
                _auftrag(z, _stand(session, z.user_id, z.angelegt_am)) for z in zeilen
            ]

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
        """Der Auftrag samt juengstem Widerruf und Obergrenze der Person."""
        with self.db.get_session() as session:
            zeile = session.get(LoeschauftragZeile, auftrag_id)
            if zeile is None:
                return None
            return _auftrag(zeile, _stand(session, zeile.user_id, zeile.angelegt_am))

    def ausfuehren(
        self, auftrag: Loeschauftrag, beitraege_behalten: Iterable[str] = ()
    ) -> PostgresBericht:
        """
        Einwuerfe und Saetze der Person vom Personenbezug loesen und den Auftrag
        erledigen, in einer Transaktion: Scheitert ein Schritt, bleibt alles wie vorher
        und der Auftrag offen. Wiederholbar: Ein zweiter Lauf findet nichts mehr.

        Zuerst sperrt es die Zeile des Auftrags (FOR UPDATE) und liest den Stand neu:
        Hat die Person seit ``laden`` widerrufen oder neu eingewilligt, passt der
        Qdrant-Teil nicht mehr zum Stand, und es bricht mit ``StandGeaendert`` ab;
        der Auftrag bleibt offen, ein zweiter Lauf nimmt den neuen Stand. Ist er
        schon erledigt (zweiter Klick), aendert es nichts.

        Gibt es eine ``obergrenze``, nur was davor angelegt war: Einwuerfe und
        Verknuepfungen nach ``created_at``, Saetze nach ``updated_at`` (einen Zeitpunkt
        des Anlegens hat ein Satz nicht; wer ihn nach einer neuen Einwilligung neu
        speichert, hat ihn unter ihr beigetragen). Sperren haengen am Beitrag: Ihr
        Autor geht, ausser an den Beitraegen in ``beitraege_behalten`` (nach der neuen
        Einwilligung angelegt, in Qdrant nicht anonymisiert).

        - Eigene Einwuerfe loeschen; CASCADE nimmt Saetze und "ausformuliert in" daran mit.
        - Saetze an fremden Einwuerfen bleiben, je Satz mit eigenem Platzhalter und
          einer Zeile in ``users`` ("ehemalige Person"), wie im Loeschkommando.
        - ``destilled_by``: der Platzhalter des eigenen Satzes, sonst ein eigener.
        - ``raw_input_content_links.created_by`` leer; an Sperren ihrer Beitraege
          Autor und Widerspruch leer (sonst verbaende beides die Person mit Beitraegen).
        - Platzhalter ohne Satz aus ``users`` abraeumen.
        """
        uid = auftrag.user_id
        vor = auftrag.obergrenze
        behalten = _uuids(beitraege_behalten)

        def davor(spalte):
            return [] if vor is None else [spalte < vor]

        with self.db.get_session() as session:
            gesperrt = session.execute(
                select(LoeschauftragZeile.erledigt_am)
                .where(LoeschauftragZeile.id == auftrag.id)
                .with_for_update()
            ).first()
            if gesperrt is None or gesperrt.erledigt_am is not None:
                return PostgresBericht(einwuerfe=0, saetze=0)
            if _stand(session, uid, auftrag.angelegt_am) != _Stand(
                auftrag.widerrufen_am, vor
            ):
                raise StandGeaendert(str(auftrag.id))
            session.execute(
                update(AusformuliertIn)
                .where(
                    AusformuliertIn.created_by == uid,
                    *davor(AusformuliertIn.created_at),
                )
                .values(created_by=None)
            )
            sperren = update(Sperre).where(Sperre.autor == uid)
            if behalten:
                sperren = sperren.where(Sperre.content_id.notin_(behalten))
            session.execute(sperren.values(autor=None, widerspruch=None))
            einwuerfe = session.execute(
                delete(Einwurf).where(
                    Einwurf.submitted_by == uid, *davor(Einwurf.created_at)
                )
            ).rowcount
            saetze = session.execute(
                select(Satz.id, Satz.raw_input_id).where(
                    Satz.user_id == uid, *davor(Satz.updated_at)
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
            # Nicht an Einwuerfen von nach der Obergrenze und nicht, wo ein Satz der
            # Person bleibt (nach einer neuen Einwilligung gespeichert).
            session.execute(
                text(
                    "UPDATE raw_inputs SET destilled_by = :praefix || gen_random_uuid()"
                    " WHERE destilled_by = :uid"
                    " AND (CAST(:vor AS timestamptz) IS NULL OR created_at < :vor)"
                    " AND NOT EXISTS (SELECT 1 FROM raw_input_drafts AS d"
                    " WHERE d.raw_input_id = raw_inputs.id AND d.user_id = :uid)"
                ),
                {"praefix": f"{EHEMALIGE_PERSON_KENNUNG}-", "uid": uid, "vor": vor},
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


def _auftrag(zeile: LoeschauftragZeile, stand: _Stand) -> Loeschauftrag:
    return Loeschauftrag(
        id=zeile.id,
        user_id=zeile.user_id,
        angelegt_am=zeile.angelegt_am,
        frist=zeile.frist,
        erledigt_am=zeile.erledigt_am,
        widerrufen_am=stand.widerrufen_am,
        obergrenze=stand.obergrenze,
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
