# Organisation, Datenmodell und Rechte

## Mandantenmodell

Eine Installation betreut einen oder mehrere Verwaltungsverbünde. Jeder Verbund enthält rechtlich/fachlich eigenständige Körperschaften mit Gremien, Zuständigkeiten und Einstellungen. Ein primärer Elternbezug dient der Baumdarstellung. Weitere Beziehungen bilden beispielsweise Zweckverbandsmitgliedschaften über Verwaltungsgrenzen ab. Ihre Semantik, Laufzeit und Verantwortlichkeit sind ausdrücklich hinterlegt.

Gemeinsam administrierte Daten bleiben Rechteobjekte. Eine gemeinsame Verwaltung, ein gemeinsamer Elternknoten oder dieselbe Portalzuordnung gewährt keinen Zugang zu vertraulichen Unterlagen anderer Körperschaften. Der Einrichtungsassistent kann im einfachen Modus Zuständigkeiten für alle betreuten Körperschaften bewusst zuweisen; diese Zuweisungen sind anschließend sichtbar.

## Fachliche Objekte

| Objekt | Wesentliche Beziehungen/Verantwortung |
|---|---|
| Person/Konto | Person zentral; höchstens ein aktives persönliches Konto, externe Kontaktdatensätze können ohne Konto existieren |
| Organisation/Körperschaft | Art, primärer Baum, weitere Beziehungen, Regelprofil, CI, Zuständigkeiten |
| Gremium | Zugehörige Körperschaft, Besetzung, Vorsitz, Schriftführung, Beratungsrechte |
| Legislaturperiode/Mandat | Zeitraum, Funktion, Stellvertretung, Gremium; individuelle Amtszeit kann vom Periodenzeitraum abweichen |
| Rolle/Zuweisung | Person, Rolle, Geltungsbereich, Beginn/Ende, gegebenenfalls Sonderfreigabe |
| Fraktion | Körperschaftsbezogen, historisierte Mitgliedschaft und eigener geschützter Arbeitsbereich |
| Vorgang/Vorlage/Version | Verantwortliche Körperschaft, Texte, Felder, Beratungsfolge, Anlagen, Freigabestand |
| Beratung | Konkretes Gremium, eigener Textstand/Ergänzung, Termin, Ergebnis; gemeinsame Vorlage nicht still überschreiben |
| Sitzung/TOP/Ereignis | Zeitpunkt, Teilnehmer, aktive Sitzungshoheit, Wortlaut und Historie |
| Abstimmung | Fixierter Gegenstand, Regel, zulässige Teilnehmer, Ergebnis; geheim gesondertes Datenmodell |
| Niederschrift/Berichtigung | Sitzungsbezug, Fassungen, Prüfungen und nachträgliche Änderungen |
| Beschluss/Aufgabe | Beschlusswortlaut, Umsetzungsauftrag, Zuständigkeit und Fortschritt getrennt |
| Veröffentlichung/Portal | Ausdrücklich freigegebener Inhaltstand, Domainzuordnung und Rücknahme |
| Datei/Export | Eigentümerobjekt, Version, Schutzbereich, Empfängerkreis und Prüfsumme |

Stabile interne IDs sind nicht von Namen, Nummern oder Baumposition abhängig. Historische Zugehörigkeiten werden nicht durch Überschreiben vernichtet. Exporte enthalten Zusammenhänge und Versionsbezüge. Eine Löschung muss Referenzen, gesetzte Aufbewahrung und gemeinsame Stammdaten berücksichtigen.

## Rollen

| Rolle | Typische Aufgaben; tatsächlich wirksam erst nach konkreter Zuweisung |
|---|---|
| Systemadministration | Betrieb, Konten-/Dienstkonfiguration; kein pauschales Lesen fachlicher Inhalte |
| Mandantenadministration | Organisationsbezogene Einstellungen/Zuweisungen im erlaubten Bereich |
| Sitzungsdienst | Planung, Einladung, Freigabe/Bereitstellung, Veröffentlichung und Protokollorganisation |
| Vorlagenersteller/Sachbearbeitung | Zugewiesene Vorlagen erstellen und bearbeiten |
| Fachbereichsleitung/Prüfer | Fachliche Prüfung, Rückgabe und Freigabe |
| Freigebender | Konfigurierter Prüfschritt mit begrenztem Bereich |
| Schriftführung | Zugewiesene Sitzung führen, Anwesenheit, Ergebnisse und Niederschrift |
| Vorsitz | Sitzung prüfen/übernehmen, Feststellungen und Niederschriftsprüfung |
| Bürgermeister/Ortsbürgermeister | Körperschaftsbezogene Amtsfunktion; Vorsitz-/Freigaberechte gesondert zuweisen |
| Mandatsträger | Unterlagen zugehöriger Gremien und erlaubte politische Arbeit |
| Fraktionsverwaltung | Mitgliedschaft und eigener Arbeitsbereich, keine Verwaltung anderer Fraktionen |
| Beratendes Mitglied | Zugewiesene Inhalte/Beratung; Stimmrecht nicht automatisch |
| Gast/Sachverständiger | Ausdrücklich freigegebene Gegenstände und Zeiträume |
| Öffentlichkeit | Ausschließlich veröffentlichte Daten; keine Kontoanlage |

Vorsitz ist eine sitzungsbezogene Funktion, nicht automatisch in allen Gremien durch Bürgermeisterrolle gegeben. Stimmberechtigung ergibt sich aus aktuellem Mandat, Funktion, Anwesenheit und Gegenstand/Regelprofil, nicht allein aus Portalzugang.

## Rechtegestaltung

Im einfachen Modus werden verständliche Rollenpakete und Zuständigkeitsauswahlen verwendet. Erweitert sind objektbezogene Rechte, bedingte/befristete Freigaben und präzise Empfängerkreise verfügbar. Rechte zum Lesen, Bearbeiten, Freigeben, Veröffentlichen, Exportieren, Delegieren und zur Sitzungshoheit sind getrennt.

Der aktive Kontext ist verpflichtender Bestandteil der serverseitigen Entscheidung. Rollen mehrerer Körperschaften werden nicht unsichtbar zusammenaddiert. Ein Wechsel prüft die aktuelle Berechtigung und schließt unzulässige Dokumentansichten. Links außerhalb des Kontexts bieten einen verständlichen Kontextwechsel an, gewähren aber noch keinen Zugriff.

Eine „Wer kann das sehen – und warum?“-Ansicht erklärt wirksame Freigaben. Vorschauen simulieren erlaubte Rollenansichten ohne beliebigen administrativen Identitätswechsel. Delegation darf nur innerhalb des eigenen vergebbaren Rechteumfangs erfolgen. Entzug und Ablauf wirken auf API, Downloads, Suche, Exportjobs, Abonnementlinks und Synchronisierung.

## Vertraulichkeit, Workflow und Schutzmerkmale

| Dimension | Ausprägungen |
|---|---|
| Sichtbarkeit | Verwaltungsintern, berechtigter Gremienkreis, eingeschränkter Personenkreis, öffentlich vorgesehen |
| Workflow | Entwurf, Prüfung, freigegeben/bereitgestellt, veröffentlicht, zurückgezogen |
| Schutzmerkmale | Personenbezogen, besonders sensibel und weitere konfigurierbare Behandlungsmerkmale |

Schutzmerkmale sind keine rechtliche Bewertung und erteilen keine Rechte. Öffentlich vorgesehen bleibt bis zur Veröffentlichung intern geschützt. Neue Anlagen erben den Schutz ihres Elternobjekts; Erweiterungen verlangen ausdrückliche Berechtigung. Ein öffentlicher TOP kann geschützte Anlagen enthalten; weder deren Inhalt noch sensible Dateinamen/Titel dürfen unbeabsichtigt öffentlich erscheinen.

Öffentliche und interne Fassungen werden getrennt versioniert und verbunden. Eine Schwärzung muss entfernte Inhalte auch in Textextraktion, Metadaten, Kommentaren und eingebetteten Daten beseitigen. Veröffentlichung nimmt ausschließlich geprüfte Fassungen und Felder in eine Positivliste auf. Vieraugenprinzip ist optional konfigurierbar, einschließlich Vertretungsregeln ohne Selbstbestätigung desselben Schritts.

## Historie, Fraktionen und persönliche Daten

Gremien-/Fraktionswechsel und Ausscheiden beenden standardmäßig den weiteren nichtöffentlichen Zugriff; historische Sonderrechte sind ausdrücklich einzuräumen. Persönliche Notizen werden nicht automatisch an Nachfolger übertragen. Fraktionsdaten sind vom privaten Notizbereich getrennt. Übergabe, Export, Löschung und Aufbewahrung müssen im Administrationsablauf erklärt werden.

Name, Funktion, Fraktion und Amtszeit können veröffentlicht werden. Foto und Kontaktfelder brauchen eigene Freigaben. Private Anschrift und interne Kontaktdaten bleiben geschützt. Legislaturperioden liefern Zeitbezüge, ersetzen aber nicht abweichende individuelle Amtszeiten.

Befangenheit wird als Ausschluss von Beratung/Abstimmung dokumentiert. Sie entzieht nicht automatisch Dokumentrechte. Ein anderweitig eingeschränkter Gegenstand bleibt unabhängig davon geschützt.

## Notfallzugriff

Technische Administration benötigt für fachlichen Zugriff einen gesonderten Vorgang: Zweck/Grund, betroffene Objekte, zeitliche Begrenzung, erneute Anmeldung, revisionsfähige Ereignisse und Benachrichtigung zuständiger Stellen. Vorabgenehmigung oder nachträgliche Prüfung ist konfigurierbar und noch im Detail festzulegen. E-Mail-Code bleibt gemäß bestätigtem Default möglich; eine strengere Faktorenregel ist einstellbar. Betriebspersonal mit Host-/Datenbankzugriff bleibt eine organisatorische Vertrauensgrenze; die Anwendung kann diesen Zugriff nicht vollständig technisch ausschließen.
