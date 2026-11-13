"""Conservative adapter for manually exported more! rubin person CSVs.

The vendor does not publish a guaranteed CSV schema. Only explicitly mapped
columns are accepted; import remains in the existing review/approval pipeline.
"""
import csv
import io
from django.core.exceptions import ValidationError

ALIASES = {
    "name": {"name", "vollständiger name", "vollstaendiger name"},
    "first": {"vorname", "first name"},
    "last": {"nachname", "familienname", "last name"},
    "email": {"e-mail", "email", "e-mail-adresse", "emailadresse"},
    "function": {"funktion", "amt", "function"},
    "faction": {"fraktion", "faction"},
}
def convert_people_csv(upload):
    if upload.size > 500_000:
        raise ValidationError("more! rubin CSV maximal 500 kB.")
    try:
        source = upload.read().decode("utf-8-sig")
    except UnicodeError:
        raise ValidationError("more! rubin CSV benötigt UTF-8.")
    try:
        reader = csv.DictReader(io.StringIO(source), delimiter=";" if ";" in source.splitlines()[0] else ",")
        columns = reader.fieldnames or []
        normalized = [c.strip().casefold() for c in columns]
        if len(normalized) != len(set(normalized)):
            raise ValidationError("Doppelte CSV-Spalten sind nicht zulässig.")
        mapped = {}
        for target, names in ALIASES.items():
            matches = [original for original, key in zip(columns, normalized) if key in names]
            if len(matches) > 1:
                raise ValidationError("Mehrdeutige CSV-Spalten für " + target)
            if matches:
                mapped[target] = matches[0]
        if "name" not in mapped and not {"first", "last"} <= mapped.keys():
            raise ValidationError("more! rubin Export benötigt Name oder Vorname und Nachname.")
        if not set(columns) <= set(mapped.values()):
            raise ValidationError("Unbekannte Exportspalten. Bitte vor dem Import bewusst entfernen.")
        rows = list(reader)
    except (csv.Error, IndexError) as exc:
        raise ValidationError("more! rubin CSV ist nicht lesbar.") from exc
    if not 1 <= len(rows) <= 200:
        raise ValidationError("CSV benötigt 1 bis 200 Personen.")
    result = io.StringIO()
    writer = csv.DictWriter(result, fieldnames=["name", "email", "function", "faction"])
    writer.writeheader()
    for number, row in enumerate(rows, 2):
        if None in row or any(value is None for value in row.values()):
            raise ValidationError(f"Zeile {number}: Spaltenzahl stimmt nicht.")
        name = row[mapped["name"]].strip() if "name" in mapped else " ".join(
            part for part in (row[mapped["first"]].strip(), row[mapped["last"]].strip()) if part
        )
        if not name:
            raise ValidationError(f"Zeile {number}: Name fehlt.")
        writer.writerow({
            "name": name,
            "email": row[mapped["email"]].strip() if "email" in mapped else "",
            "function": row[mapped["function"]].strip() if "function" in mapped else "",
            "faction": row[mapped["faction"]].strip() if "faction" in mapped else "",
        })
    return result.getvalue().encode("utf-8")
