from abc import ABC, abstractmethod
from datetime import date
from typing import Any, Dict, List, Optional


class IModerationRepository(ABC):
    """
    Zugriff der Moderation auf die Beitraege im Suchindex, ueber alle Beitragstypen.

    Anders als die Beitrags-Repositories blendet es gesperrte Beitraege nicht aus:
    Nur ueber die Moderation finden Admins sie noch. Beitraege kommen als Payload
    (dict mit "id") zurueck, weil die Moderation typunabhaengig arbeitet.
    """

    @abstractmethod
    async def laden(self, beitrag_id: str) -> Optional[Dict[str, Any]]:
        """Payload eines Beitrags, auch wenn er gesperrt ist; None, wenn es ihn nicht gibt."""
        pass

    @abstractmethod
    async def sperren(self, beitrag: Dict[str, Any]) -> None:
        """
        Den mit laden geholten Beitrag sperren und seinen Status von vorher fuer
        das Entsperren merken. Ist er schon gesperrt, passiert nichts.
        """
        pass

    @abstractmethod
    async def entsperren(self, beitrag: Dict[str, Any]) -> None:
        """
        Den mit laden geholten Beitrag entsperren: den beim Sperren gemerkten
        Status zurueckschreiben, ohne Status von vorher (Altbestand) das
        Status-Feld entfernen. Ist er nicht gesperrt, passiert nichts.
        """
        pass

    @abstractmethod
    async def gesperrte_laden(self, limit: int) -> List[Dict[str, Any]]:
        """Alle gesperrten Beitraege, hoechstens limit."""
        pass

    @abstractmethod
    async def geloeschte_laden(self) -> List[Dict[str, Any]]:
        """Alle geloeschten Beitraege (Zustand "geloescht"), ohne Obergrenze."""
        pass

    @abstractmethod
    async def geloescht_am_setzen(self, beitrag_ids: List[str], tag: date) -> None:
        """Den Tag des Loeschens (FELD_GELOESCHT_AM) an diese Beitraege schreiben."""
        pass

    @abstractmethod
    async def entfernen(self, beitrag_id: str) -> bool:
        """Den Beitrag aus dem Suchindex entfernen; False, wenn das nicht gelang."""
        pass

    @abstractmethod
    async def aus_aussagen_entfernen(self, beitrag_id: str) -> int:
        """
        Den Beitrag aus den Antwortvorschlaegen aller Aussagen streichen.

        Returns:
            Anzahl der geaenderten Aussagen
        """
        pass
