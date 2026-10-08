# Betriebssicherung und Wiederherstellung

Betriebswerkzeuge laufen beim lokalen Betreiber, niemals mit Docker-Socket in einer Fachanwendung. Der Wartungsmodus friert HTTP-Schreibanfragen ein und erhält lesenden Zugriff. Auf PostgreSQL warten exklusiver Wartungswechsel und gemeinsame Schreibsperren auf bereits laufende Transaktionen; danach beginnen keine neuen Änderungen. Antworten enthalten 503/Retry-After, keine scheinbar gespeicherten Änderungen. Offline-Schriftführung bleibt lokal und wird nach Wartung abgeglichen. Lokale administrative Managementbefehle bleiben in der Verantwortung des Betreibers.

`manage.py maintenance on|off|status` ist die kontrollierte lokale Schnittstelle. Fach-/Transfer-/Mailworker müssen während einer konsistenten Sicherung ebenfalls pausieren. `manage.py backup_manifest` liefert die Rolle und Prüfsummen aller Codemigrationen ohne Fachinhalte. Backup enthält Datenbank inklusive offener Journale/Prüfaufträge und Dateien; Laufzeitschlüssel werden getrennt gesichert.

Die folgenden Hostwerkzeuge ergänzen verschlüsselte Sicherung, prüfbaren Restore und tägliche Ausführung. Für zusammenhängende Zwei-Host-Restorepunkte beide Seiten in Wartung nehmen, intern initiierte Übertragung pausieren und erst nach Sicherung beider Seiten in kontrollierter Reihenfolge wieder freigeben. Eine beliebige Mischung unterschiedlicher Sicherungszeiten ist kein konsistenter Gesamtstand.

## Verschlüsselte Hostwerkzeuge

`ops/backup.py` wird lokal durch den Betreiber ausgeführt. Benötigt Python/cryptography und Docker-Compose-Rechte auf dem Host; niemals den Docker-Socket in ein Web-/Worker-Container einbinden. 256-Bit-Sicherungsschlüssel separat als private Datei (0600) sichern, beispielsweise `openssl rand -base64 32`. Der Schlüsselpfad darf nicht im Sicherungsziel liegen. Das Ziel muss außerhalb des Repositorys liegen und auf getrenntem Datenträger beziehungsweise sicherem externem Speicher eingebunden sein.

```
python ops/backup.py backup --stack internal --target /mnt/ris-backups --key-file /etc/beschlussmanufaktur/backup.key
python ops/backup.py backup --stack external --target /mnt/ris-backups --key-file /etc/beschlussmanufaktur/backup.key
```

Der Befehl pausiert nur zuvor laufende Fach-/Mail-/Transfer-/TLS-Dienste, friert Fachschreibanfragen ein und sichert PostgreSQL-Custom-Dumps sowie Datei-, Caddy- und TLS-Agentenvolume. Journale, offene Rückgaben, persönliche Notizen, Rechte, OTP-/Passkey-Daten und ausstehende Mailaufträge sind in der jeweiligen Datenbank enthalten. TLS-Proxies werden während dieser konsistenten Sicherung kurz pausiert. Temporäre Klartextbestandteile liegen ausschließlich in einem privaten lokalen Arbeitsverzeichnis und werden anschließend entfernt; das getrennte Ziel erhält ausschließlich authentifiziert verschlüsselte AES-256-GCM-Archive und neutrale Statusmetadaten. Erfolgreiche Sicherung wird unmittelbar entschlüsselt und gegen sämtliche Manifestprüfsummen zurückgelesen. Keine automatische Löschung alter Sicherungen ohne festgelegte Aufbewahrung.

Laufzeitgeheimnisse aus `.env`, Datenverschlüsselungs-/Sicherungsschlüssel und CA-Vertrauen separat sichern. Eine gültige verschlüsselte Sicherung ohne passenden Schlüssel ist nicht wiederherstellbar. Bei Prozess-/Hostabbruch Wartungsstatus und pausierte Dienste bewusst prüfen; nichts wird durch einen unkontrollierten Neustart scheinbar freigegeben.

## Täglich und vor Updates

Die Vorlagen `ops/beschlussmanufaktur-backup@.service`/`.timer` nach `/etc/systemd/system/` installieren. Arbeitsverzeichnis `/srv/beschlussmanufaktur` und Pythonumgebung anpassen; `/etc/beschlussmanufaktur/backup-internal.env` beziehungsweise `backup-external.env` enthält `BACKUP_TARGET` und `BACKUP_KEY_FILE`. Timer bewusst mit `systemctl enable --now beschlussmanufaktur-backup@internal.timer` beziehungsweise `external.timer` aktivieren. Standard 02:30 mit kleiner Zufallsverschiebung. Für ein Vorupdate-Backup denselben Befehl vor jeder Migration ausführen und erfolgreichen Status kontrollieren; Update bei fehlgeschlagener Sicherung abbrechen.

## Restore und Rückweg

```
python ops/backup.py restore --stack internal --archive /mnt/ris-backups/DATEI.bmbak --destination /srv/private-restore-check --key-file /etc/beschlussmanufaktur/backup.key
```

Standard prüft ausschließlich authentifizierte Entschlüsselung, Rollen-/Manifestkonsistenz und Prüfsummen; er verändert keine Installation. Entschlüsseltes Prüfziel ist vertraulich und muss nach Abschluss kontrolliert entfernt werden. Fremde Pfade, Links, doppelte Einträge und manipulierte Archive werden abgewiesen.

`--apply` ist der bewusste lokale Wiederherstellungsbefehl: nur passende Codemigrationen, ausschließlich laufende Ziel-Datenbanken, leere Datenbanken und leere Dateivolumes. Kein Überschreiben bestehender Installationen. Restorepunkte deshalb auf einem neuen, isolierten Ziel wiederherstellen; bei Teilfehler das neue Ziel vollständig verwerfen und erneut beginnen. Wartungsflags bleiben nach Restore gesetzt. Fachrechte, Veröffentlichungswiderrufe, aktuelle Mandatsenden, ausstehende Rückgaben und Schlüssel prüfen, bevor Dienste freigegeben werden. Veraltete veröffentlichte Daten dürfen durch einen Restore nicht ungeprüft wieder öffentlich erscheinen.

Update-Rückweg: passenden vorigen Code/Image-Stand und dessen vollständige Sicherung auf einem neuen isolierten Ziel herstellen, prüfen und kontrolliert umschalten. Datenbankmigrationen nicht blind rückwärts ausführen. Die praktische Wiederherstellung beider produktiven Hosts, Schlüsselverlustfälle und Betriebszuständigkeiten gehören vor Freigabe zur Abnahme in Etappe 11.
