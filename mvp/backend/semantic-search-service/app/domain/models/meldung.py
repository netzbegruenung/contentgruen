"""
Angaben der meldenden Person an einer Meldung (Glossar „Meldung“, #438).

Grenzen fuer Name und E-Mail-Adresse, an einer Stelle fuer Melde-Route und
Tabelle ``content_reports``. Der Meldedialog fuehrt dieselben Werte in
``shared/components/report-dialog``. 254 ist die laengste zulaessige
E-Mail-Adresse (RFC 5321).
"""

from dataclasses import dataclass
from typing import Optional

MELDER_NAME_MAX = 200
MELDER_EMAIL_MAX = 254


@dataclass(frozen=True)
class MelderAngaben:
    """Was die meldende Person nach Art. 16 Abs. 2 DSA zur Meldung angibt.

    Name und E-Mail-Adresse sind freiwillig (lit. c), die Erklaerung guten
    Glaubens ist Pflicht (lit. d). Die drei reisen gemeinsam von der Melde-Route
    ueber den ModerationService bis in die Tabelle.
    """

    guter_glaube: bool
    name: Optional[str] = None
    email: Optional[str] = None
