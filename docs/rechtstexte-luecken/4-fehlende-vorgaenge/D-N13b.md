# D-N13b

- **Vorgang:** **Bild-Adressen Dritter**
- **Fundstelle im Code:** `fe/app/beitragskarte/beitragskarte.component.html` mit zwei Stellen, seit #447 beide über `<app-fremdes-bild>` (`fe/app/shared/fremdes-bild/`): volle Karte `:194`, Kopfband der Album-Karte in Meine Beiträge `:9` (vorher `<img [src]>`, davor `image-result-item.component.html:41`), `domain/models/image.py:37`
- **Was in den Text muss:** Der einzige Abruf, den der Browser der Nutzenden an einen fremden Server richtet — siehe X4
- **Eintrag / Entscheidung:** ✓ Eigener Abschnitt „Bilder von fremden Servern". **Mit #447:** Der Browser lädt ein fremdes Bild erst, wenn die Person auf den Platzhalter „Bild laden“ klickt (`shared/fremdes-bild/`); der Abschnitt sagt das
