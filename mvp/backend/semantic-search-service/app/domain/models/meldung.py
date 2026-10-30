"""
Angaben der meldenden Person an einer Meldung (Glossar „Meldung“, #438).

Grenzen fuer Name und E-Mail-Adresse, an einer Stelle fuer Melde-Route und
Tabelle ``content_reports``. Der Meldedialog fuehrt dieselben Werte in
``shared/components/report-dialog``. 254 ist die laengste zulaessige
E-Mail-Adresse (RFC 5321).
"""

MELDER_NAME_MAX = 200
MELDER_EMAIL_MAX = 254
