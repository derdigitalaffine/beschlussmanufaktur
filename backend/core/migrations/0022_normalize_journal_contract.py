"""Remove host-local integer IDs from transport, preserving all substantive data."""
import hashlib,json
from django.db import migrations

def normalize(bundle):
    tables=bundle.get('tables',{})
    for key in ('ballots','conflicts'):
        for row in tables.get(key,[]):row.pop('id',None)
    for key in ('minutes','minutes_versions','decision_updates'):tables.setdefault(key,[])

def forwards(apps,schema_editor):
    for item in apps.get_model('core','SessionReturn').objects.all().iterator():
        normalize(item.bundle);item.digest=hashlib.sha256(json.dumps(item.bundle,sort_keys=True).encode()).hexdigest();item.save(update_fields=['bundle','digest'])
    for item in apps.get_model('core','TransferBatch').objects.filter(delivered_at__isnull=True,channel='protected').iterator():
        for journal in item.payload.get('data',{}).get('meeting_data',{}).get('journals',[]):normalize(journal)
        item.save(update_fields=['payload'])

class Migration(migrations.Migration):
    dependencies=[('core','0021_offlinereceipt')]
    operations=[migrations.RunPython(forwards,migrations.RunPython.noop)]
