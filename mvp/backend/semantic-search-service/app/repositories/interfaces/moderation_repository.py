from abc import ABC, abstractmethod
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
    async def sperren(self, beitrag_id: str, status_vorher: Optional[str]) -> None:
        """Status auf gesperrt setzen und den Status von vorher fuer das Entsperren merken."""
        pass

    @abstractmethod
    async def entsperren(self, beitrag_id: str) -> None:
        """
        Den beim Sperren gemerkten Status zurueckschreiben. Ohne Status von vorher
        (Altbestand) das Status-Feld entfernen.
        """
        pass

    @abstractmethod
    async def gesperrte(self, limit: int) -> List[Dict[str, Any]]:
        """Alle gesperrten Beitraege, hoechstens limit."""
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
