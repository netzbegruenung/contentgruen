"""
Repository fuer den Fangkorb (Rohinput).

Datenzugriff auf ``raw_inputs``, ``raw_input_drafts`` und
``raw_input_content_links``: anlegen, auflisten, einzeln lesen, Entwurf speichern,
Status setzen. Eine Zuweisung ("ich nehm das") gibt es bewusst nicht - mehrere
Personen duerfen denselben Einwurf gleichzeitig destillieren.
"""

import logging
import uuid
from typing import Any, Dict, List, Optional, Sequence

from sqlalchemy import case, desc, func
from sqlalchemy.dialects.postgresql import insert

from domain.models.raw_input import (
    AktionNichtErlaubt,
    EinwurfNichtGefunden,
    RawInputSource,
    RawInputStatus,
    UebergangNichtErlaubt,
    uebergang_erlaubt,
)
from infrastructure.database.connection import get_app_database
from infrastructure.database.models import RawInput, RawInputContentLink, RawInputDraft

logger = logging.getLogger(__name__)


class RawInputRepository:
    """Repository fuer Einwuerfe im Fangkorb."""

    def __init__(self):
        self.db = get_app_database()

    @staticmethod
    def _to_dict(
        raw_input: RawInput,
        eigener_entwurf: Optional[str] = None,
        verknuepfung: Optional[RawInputContentLink] = None,
    ) -> Dict[str, Any]:
        """In ein Dict uebersetzen, solange die Session noch offen ist."""
        return {
            "id": str(raw_input.id),
            "content": raw_input.content,
            "url": raw_input.url,
            "image_url": raw_input.image_url,
            "submitted_by": raw_input.submitted_by,
            "source_channel": raw_input.source_channel,
            "status": raw_input.status,
            "created_at": raw_input.created_at,
            "own_draft": eigener_entwurf,
            # In der Tabelle created_by/created_at, nach aussen der Bearbeitungsstand.
            "processed_content_id": (
                str(verknuepfung.content_id) if verknuepfung else None
            ),
            "processed_by": verknuepfung.created_by if verknuepfung else None,
            "processed_at": verknuepfung.created_at if verknuepfung else None,
        }

    def create(
        self,
        content: Optional[str] = None,
        url: Optional[str] = None,
        image_url: Optional[str] = None,
        submitted_by: Optional[str] = None,
        source_channel: str = RawInputSource.WEB.value,
    ) -> Dict[str, Any]:
        """
        Einen Einwurf anlegen.

        Args:
            content: Freitext - der eine Satz oder die Notiz zum Link
            url: Link auf den Beitrag draussen
            image_url: Bild-URL (kein Upload, siehe docs/ROHINPUT.md)
            submitted_by: Wer eingeworfen hat; None fuer Kanaele ohne Sitzung
            source_channel: Herkunftskanal ("web" oder "share")

        Returns:
            Dict[str, Any]: der angelegte Einwurf
        """
        try:
            with self.db.get_session() as session:
                raw_input = RawInput(
                    content=content,
                    url=url,
                    image_url=image_url,
                    submitted_by=submitted_by,
                    source_channel=source_channel,
                    status=RawInputStatus.OPEN.value,
                )
                session.add(raw_input)
                session.commit()
                session.refresh(raw_input)
                logger.info(
                    f"Rohinput {raw_input.id} angelegt (Kanal: {source_channel})"
                )
                return self._to_dict(raw_input)
        except Exception as e:
            logger.error(f"Fehler beim Anlegen eines Rohinputs: {e}", exc_info=True)
            raise

    def get_all(
        self,
        limit: int = 20,
        offset: int = 0,
        status: Optional[str] = None,
        current_user: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Einwuerfe auflisten: eigene zuerst, dann neueste zuerst.

        Absichtlich ohne Filter auf die einwerfende Person: der Fangkorb ist ein
        gemeinsamer Vorrat. ``current_user`` bestimmt nur die Reihenfolge und
        welcher Entwurfssatz mitkommt. Sortiert wird in der Datenbank, weil die
        Liste paginiert ist.

        Args:
            limit: maximale Anzahl
            offset: zu ueberspringende Eintraege
            status: optionaler Filter auf einen Bearbeitungsstand
            current_user: die anfragende Person, oder None

        Returns:
            List[Dict[str, Any]]: die Einwuerfe mit Bearbeitungsstand
        """
        try:
            with self.db.get_session() as session:
                query = session.query(RawInput)
                if status is not None:
                    query = query.filter(RawInput.status == status)

                reihenfolge = [desc(RawInput.created_at)]
                if current_user is not None:
                    reihenfolge.insert(
                        0, case((RawInput.submitted_by == current_user, 0), else_=1)
                    )

                rows = query.order_by(*reihenfolge).limit(limit).offset(offset).all()
                return self._mit_bearbeitungsstand(session, rows, current_user)
        except Exception as e:
            logger.error(f"Fehler beim Lesen der Rohinputs: {e}", exc_info=True)
            raise

    def get_by_id(
        self, raw_input_id: uuid.UUID, current_user: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Einen Einwurf mit eigenem Entwurf und erster Verknuepfung, oder None."""
        try:
            with self.db.get_session() as session:
                row = (
                    session.query(RawInput)
                    .filter(RawInput.id == raw_input_id)
                    .one_or_none()
                )
                if row is None:
                    return None
                return self._mit_bearbeitungsstand(session, [row], current_user)[0]
        except Exception as e:
            logger.error(f"Fehler beim Lesen eines Rohinputs: {e}", exc_info=True)
            raise

    def count(self, status: Optional[str] = None) -> int:
        """Anzahl der Einwuerfe, optional auf einen Bearbeitungsstand gefiltert."""
        try:
            with self.db.get_session() as session:
                query = session.query(RawInput)
                if status is not None:
                    query = query.filter(RawInput.status == status)
                return query.count()
        except Exception as e:
            logger.error(f"Fehler beim Zaehlen der Rohinputs: {e}", exc_info=True)
            raise

    def save_draft(
        self, raw_input_id: uuid.UUID, user_id: str, sentence: Optional[str]
    ) -> Dict[str, Any]:
        """
        Den eigenen Entwurfssatz speichern (Upsert) oder, wenn leer, loeschen.

        Raises:
            EinwurfNichtGefunden: den Einwurf gibt es nicht
        """
        try:
            with self.db.get_session() as session:
                vorhanden = (
                    session.query(RawInput.id)
                    .filter(RawInput.id == raw_input_id)
                    .one_or_none()
                )
                if vorhanden is None:
                    raise EinwurfNichtGefunden(raw_input_id)

                if not sentence:
                    session.query(RawInputDraft).filter(
                        RawInputDraft.raw_input_id == raw_input_id,
                        RawInputDraft.user_id == user_id,
                    ).delete(synchronize_session=False)
                    session.commit()
                    return {
                        "raw_input_id": str(raw_input_id),
                        "sentence": None,
                        "updated_at": None,
                    }

                updated_at = session.execute(
                    self._entwurf_upsert(raw_input_id, user_id, sentence)
                ).scalar_one()
                session.commit()
                return {
                    "raw_input_id": str(raw_input_id),
                    "sentence": sentence,
                    "updated_at": updated_at,
                }
        except EinwurfNichtGefunden:
            raise
        except Exception as e:
            logger.error(f"Fehler beim Speichern eines Entwurfs: {e}", exc_info=True)
            raise

    def set_status(
        self,
        raw_input_id: uuid.UUID,
        neuer_status: RawInputStatus,
        user_id: str,
        content_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        """
        Status setzen; bei processed zugleich die Verknuepfung schreiben.

        Beides in einer Transaktion, die Zeile ist dabei gesperrt (FOR UPDATE),
        damit zwei gleichzeitige Wechsel sich nicht ueberschreiben. Die
        Verknuepfung ist idempotent (ON CONFLICT DO NOTHING): ein wiederholter
        Aufruf nach verlorener Antwort schadet nicht.

        Raises:
            EinwurfNichtGefunden: den Einwurf gibt es nicht
            AktionNichtErlaubt: verwerfen will jemand anderes als die einwerfende Person
            UebergangNichtErlaubt: der Wechsel ist aus dem aktuellen Status nicht erlaubt
        """
        if neuer_status == RawInputStatus.PROCESSED and content_id is None:
            raise ValueError("processed braucht eine content_id")

        try:
            with self.db.get_session() as session:
                row = (
                    session.query(RawInput)
                    .filter(RawInput.id == raw_input_id)
                    .with_for_update()
                    .one_or_none()
                )
                if row is None:
                    raise EinwurfNichtGefunden(raw_input_id)

                if (
                    neuer_status == RawInputStatus.DISCARDED
                    and row.submitted_by != user_id
                ):
                    raise AktionNichtErlaubt(
                        "Verwerfen darf nur, wer den Einwurf eingeworfen hat"
                    )

                aktuell = RawInputStatus(row.status)
                if not uebergang_erlaubt(aktuell, neuer_status):
                    raise UebergangNichtErlaubt(aktuell, neuer_status)

                row.status = neuer_status.value
                if neuer_status == RawInputStatus.PROCESSED:
                    session.execute(
                        self._verknuepfung_einfuegen(raw_input_id, content_id, user_id)
                    )
                session.commit()
                logger.info(
                    f"Rohinput {raw_input_id}: {aktuell.value} -> {neuer_status.value}"
                )
                return self._mit_bearbeitungsstand(session, [row], user_id)[0]
        except (EinwurfNichtGefunden, AktionNichtErlaubt, UebergangNichtErlaubt):
            raise
        except Exception as e:
            logger.error(f"Fehler beim Statuswechsel: {e}", exc_info=True)
            raise

    # Hilfsfunktionen

    @staticmethod
    def _entwurf_upsert(raw_input_id: uuid.UUID, user_id: str, sentence: str):
        """INSERT ... ON CONFLICT (raw_input_id, user_id) DO UPDATE."""
        stmt = insert(RawInputDraft).values(
            raw_input_id=raw_input_id, user_id=user_id, sentence=sentence
        )
        return stmt.on_conflict_do_update(
            index_elements=[RawInputDraft.raw_input_id, RawInputDraft.user_id],
            set_={"sentence": stmt.excluded.sentence, "updated_at": func.now()},
        ).returning(RawInputDraft.updated_at)

    @staticmethod
    def _verknuepfung_einfuegen(
        raw_input_id: uuid.UUID, content_id: uuid.UUID, user_id: str
    ):
        """INSERT ... ON CONFLICT (raw_input_id, content_id) DO NOTHING."""
        return (
            insert(RawInputContentLink)
            .values(
                raw_input_id=raw_input_id, content_id=content_id, created_by=user_id
            )
            .on_conflict_do_nothing(
                index_elements=[
                    RawInputContentLink.raw_input_id,
                    RawInputContentLink.content_id,
                ]
            )
        )

    def _mit_bearbeitungsstand(
        self, session, rows: Sequence[RawInput], current_user: Optional[str]
    ) -> List[Dict[str, Any]]:
        """Eigenen Entwurf und erste Verknuepfung an die Zeilen haengen."""
        if not rows:
            return []
        ids = [row.id for row in rows]
        entwuerfe = self._eigene_entwuerfe(session, ids, current_user)
        verknuepfungen = self._erste_verknuepfungen(session, ids)
        return [
            self._to_dict(row, entwuerfe.get(row.id), verknuepfungen.get(row.id))
            for row in rows
        ]

    @staticmethod
    def _eigene_entwuerfe(
        session, ids: List[uuid.UUID], current_user: Optional[str]
    ) -> Dict[uuid.UUID, str]:
        """Entwurfssaetze der anfragenden Person - nie die anderer."""
        if current_user is None:
            return {}
        entwuerfe = (
            session.query(RawInputDraft)
            .filter(
                RawInputDraft.raw_input_id.in_(ids),
                RawInputDraft.user_id == current_user,
            )
            .all()
        )
        return {entwurf.raw_input_id: entwurf.sentence for entwurf in entwuerfe}

    @staticmethod
    def _erste_verknuepfungen(
        session, ids: List[uuid.UUID]
    ) -> Dict[uuid.UUID, RawInputContentLink]:
        """Je Einwurf die aelteste Verknuepfung - wer ihn zuerst verarbeitet hat."""
        verknuepfungen = (
            session.query(RawInputContentLink)
            .filter(RawInputContentLink.raw_input_id.in_(ids))
            .order_by(RawInputContentLink.created_at)
            .all()
        )
        erste: Dict[uuid.UUID, RawInputContentLink] = {}
        for verknuepfung in verknuepfungen:
            erste.setdefault(verknuepfung.raw_input_id, verknuepfung)
        return erste


# Globale Repository-Instanz
_raw_input_repository: Optional[RawInputRepository] = None


def get_raw_input_repository() -> RawInputRepository:
    """Die globale RawInputRepository-Instanz holen oder anlegen."""
    global _raw_input_repository
    if _raw_input_repository is None:
        _raw_input_repository = RawInputRepository()
    return _raw_input_repository
