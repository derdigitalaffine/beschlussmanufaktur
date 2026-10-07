# Quellen und offene Entscheidungen

Recherchestand: 2026-10-07. Entscheidungen stammen aus dem Interview; externe Quellen dienen der fachlichen Einordnung. Produktwerbung ist kein Nachweis zugesicherter Schnittstellen oder Rechtskonformität. Technische Empfehlungen sind nicht bereits implementiert.

## Quellen

| Quelle | Verwendung und Grenze |
|---|---|
| [more! Sitzungsdienst](https://more-rubin.de/sitzungsdienst) | Referenzumfang vom Sitzungsdienst bis Beschlusskontrolle/Entschädigungen; keine Übernahme eines proprietären Datenmodells |
| [more! Zusatzmodule](https://more-rubin.de/module) | Einordnung von Druck, Anträgen, DMS und Abstimmungen; konkrete Schnittstellen später prüfen |
| [Kommunale Vorlage VG Pellenz](https://gremien.pellenz.de/smcbi/getfile.asp?id=194384&type=do) | Beispiel für Zuständigkeit, Beratungsfolge, Sachlage, Finanzangaben, Anlagen und Beschluss; keine allgemeine Feldpflicht |
| [§ 34 GemO RLP, OpenLex](https://openlex.de/rheinland-pfalz/gemo/34) | Vorläufiger Abgleich von Einladung/TO; sekundäre Gesetzeswiedergabe |
| [§ 34 GemO RLP, anwalt24](https://www.anwalt24.de/gesetze/gemo-1/34) | Übereinstimmende sekundäre Wiedergabe; ersetzt nicht amtlichen Abgleich |
| [Landesrecht RLP](https://landesrecht.rlp.de/) | Offizielle Rechercheanlaufstelle; direkter Abruf des relevanten Paragraphen war in dieser Recherche nicht möglich |
| [Verkündungsplattform RLP](https://verkuendung.rlp.de/) | Amtliche Veröffentlichungen für abschließenden Normenabgleich |
| [Gestaltungsreferenz](https://www.otterbach-otterberg.de/) | Vom Auftraggeber benannte Orientierung; keine Übernahme realer Kundendaten/Assets |
| [OWASP Authorization Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Authorization_Cheat_Sheet.html) | Standardmäßig verweigern, jeden Zugriff serverseitig prüfen |
| [NIST Authentikatoren](https://pages.nist.gov/800-63-4/sp800-63b/authenticators/) | E-Mail nicht als Out-of-band-Authentifizierung gemäß NIST; dokumentierte Abweichung beim gewählten Default |
| [Caddy Automatic HTTPS](https://caddyserver.com/docs/automatic-https) | Lokale CA, Vertrauensinstallation, ACME und Erneuerung |
| [Caddy TLS](https://caddyserver.com/docs/caddyfile/directives/tls) | Zertifikate, DNS-Provideradapter, Challengekonfiguration und Grenzen |
| [Let's Encrypt Challenge Types](https://letsencrypt.org/docs/challenge-types/) | DNS-01 von bloßer DNS-Auflösungsprüfung unterscheiden |
| [Django](https://docs.djangoproject.com/en/5.2/) | Offizielle Dokumentation zur vorgeschlagenen Python-Basis; Version noch nicht festgelegt |
| [Django REST framework](https://www.django-rest-framework.org/) | Vorgeschlagene API-Basis |
| [PostgreSQL Volltext](https://www.postgresql.org/docs/current/textsearch.html) | Vorgeschlagene Suchbasis, Rechtefilter zusätzlich erforderlich |
| [WhisperX](https://github.com/m-bain/whisperX) | Spätere Transkription mit Zeitmarken/Sprechertrennung und bekannten Grenzen |
| [SpeechMind API](https://www.speechmind.com/docs/introduction/) | Mögliche spätere Anbieterintegration; konkrete API-/Vertragsbedingungen offen |
| [MDN Aufnahmeereignisse](https://developer.mozilla.org/en-US/docs/Web/API/MediaRecorder/dataavailable_event) | Spätere Browseraufnahme, abschnittsweise Bereitstellung und Gerätezustandsgrenzen |

## Pflichtklärungen vor Implementierung oder Livegang

| ID | Frage | Zeitpunkt/Verantwortung |
|---|---|---|
| O-01 | RLP-Normenstand, Geschäftsordnungen und eigene Regelprofile für VG/OG, Landkreis, Ausschüsse und Zweckverbände | Fachliche Prüfung vor Regeln und Abnahme |
| O-02 | Zulässigkeit/Ausgestaltung digitaler und geheimer Abstimmungen/Wahlen; Trennung Identität/Stimmwert und qualifizierte Prüfung | Vor Implementierung des Wahlverfahrens |
| O-03 | Rechtefrischegrenze, Sitzungsaktivierung/-rückgabe, Offlineübernahme und Führerschaft bei Netzteilung | Architekturdetail vor Live-Modul |
| O-04 | Konten-/Faktorenspeicher je Bereich, initiale Registrierung, synchronisierte Sperren und sichere Wiederherstellung | Vor IAM-Implementierung |
| O-05 | DNS-Anbieter, Provideradapter und primärer ACME-Weg; DNS-01 oder alternative Challenges | Vor TLS-Implementierung |
| O-06 | IMAP: nur Rückläufer oder auch fachliche Eingänge? Zuordnung und Bearbeitungsrechte | Vor Mailmodul |
| O-07 | Konkrete Aufbewahrung, Archive, Fraktions-/Notizübergabe und Auditfristen | Vor produktivem Datenbetrieb |
| O-08 | Für den tatsächlichen öffentlichen Einsatz geltende Barrierefreiheitsanforderungen trotz bewusst verschobener Umsetzung | Vor Livegangentscheidung |
| O-09 | Konkrete Bibliotheken/Versionen für Frontend, Zusammenarbeit, Markdown, PDF/DOCX, Jobs und Live-Kanal | Technischer Prototyp |
| O-10 | Lastgrößen, Hardware, Such-/Ladezeiten, Restorezeit, Sync-Intervall und Gerätematrix | Vor Dimensionierung/Abnahme |
| O-11 | Notfallzugriff: vorherige zweite Genehmigung versus nachträgliche Prüfung; Meldungsempfänger | Vor Administration |
| O-12 | Vertrauliche E-Mail-Anlagen und formale Einladungs-/Zugangsnachweise | Vor Einladungsmodul; Default nur geschützter Link |
| O-13 | Zugriff auf besonders geschützte Objekte: genaue Kategorien, Logumfang und zulässige Aufbewahrung | Vor Auditkonfiguration |

Diese offenen Punkte ändern die bestätigten Grundentscheidungen nicht. Architekturvorschläge dürfen im Zuge ihrer Klärung angepasst werden, ohne still neue Funktionen aus dem Kern zu entfernen.

## Spätere Klärungen

Aufnahmevoraussetzungen und Löschfristen, SpeechMind-Vertrag/API, Modelllizenzen/GPU-Bedarf, Anbieteraktivierung, Sitzungsgeldsatzungen/Finanzverfahren, DMS-Produkt und OParl-Spezifikationsversion werden vor dem jeweiligen späteren Modul bestimmt. MIT-Lizenz des Projekts überschreibt keine fremden Modell-/Bibliotheksbedingungen.
