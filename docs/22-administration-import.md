# Administration und geprüfte Importe

Import ist ausschließlich im internen Dienst unter der ausdrücklich gewählten Organisationsverwaltungsrolle verfügbar. UTF-8-CSV (Komma/Semikolon), maximal 500 kB/200 Zeilen. Unterstützt sind Gremien/Stammdaten, interne Personenprofile und Konten/Rollen als Einladungen. Erlaubte Spalten werden angezeigt. Fremde Körperschafts-IDs, Passwörter und beliebige Felder sind ausgeschlossen; keine Rubin-Migration.

Jeder Import erzeugt zuerst eine Vorschau, gebunden an Person, Kontext und Körperschaft. Nach ausdrücklicher Bestätigung werden Daten und Dubletten erneut geprüft. Die Übernahme ist atomar und idempotent, Vorschauen verfallen nach 24 Stunden. Bereits vorhandene Datensätze werden nicht still überschrieben. Namen-/E-Mail-Dubletten brauchen bewusste fachliche Identitätsentscheidung.

Kontenimporte erzeugen ausschließlich Einladung und verschlüsselte Versandwarteschlange, keinen aktiven Zugang und kein Standardpasswort. Der bestehende `invitation-worker` sendet nach erfolgreicher Übernahme, prüft die Berechtigung des Einladenden erneut und wiederholt höchstens zehnmal. Nach Zustellung wird der gespeicherte Einladungscode gelöscht. SMTP kann bei einem Prozessabbruch nach Annahme vor Verbuchung dieselbe Einladung erneut zustellen; der Code ist unverändert und nur einmal annehmbar.

`DATA_ENCRYPTION_KEY` ist ein separat gesicherter Fernet-Schlüssel. Ohne Schlüssel ist die Übernahme von Konteneinladungen gesperrt. Generieren: `python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'`. Schlüssel ausschließlich als Laufzeitgeheimnis setzen und getrennt von Datenbank/Sicherung schützen. Grundlage: https://cryptography.io/en/stable/fernet/ . Wechsel benötigt bewusste Neuverschlüsselung, kein stiller Austausch.

## Zentrale Personen und Dubletten

Profile können dieselbe zentrale Personenidentität verwenden. Ein bereits zugeordnetes Konto identifiziert eine Person eindeutig; Funktionen, Fraktionen, Amtszeiten, Kontakte und öffentliche Freigaben bleiben pro Körperschaft. Ohne Konto wird keine Namensähnlichkeit automatisch als Identitätsbeweis verwendet. Die Dublettenaktion benötigt ausdrückliche aktuelle Organisationsverwaltung für sämtliche betroffenen Körperschaften, eine Begründung und zwei sichtbare Identitäten. Unterschiedliche Konten und zwei Profile in derselben Körperschaft werden nicht automatisch zusammengeführt. Fremde Personenidentitäten werden nicht zur Auswahl angeboten.

## Minimale Auslieferungstestdaten

Bootstrap erzeugt zusätzlich eine klar markierte Testkörperschaft mit Rat, Raum und Legislaturperiode und einer ausdrücklichen Verwaltungsrolle für die einrichtende Person. Keine künstlichen Benutzerkonten, Standardpasswörter, Fachvorlagen oder öffentlichen Veröffentlichungen. Bereits bestehende Installationen können diese kleinen Beispieldaten bewusst anlegen.

Die Administration sieht den Umfang vor dem Löschknopf. Entfernt werden ausschließlich unveränderte markierte Beispieldaten. Neue Fachreferenzen, zusätzliche Rollen oder Änderungen an Beispielstammdaten sperren das Löschen. Produktive Daten werden nicht mit entfernt. Nach Löschen erzeugen Neustart und Update nichts erneut. Wer die Beispiele produktiv verwendet hat, muss diese Beziehungen zuerst bewusst bereinigen.
