from django.db import migrations

def assign(apps,schema_editor):
    Profile=apps.get_model('core','PersonProfile');Identity=apps.get_model('core','PersonIdentity')
    for profile in Profile.objects.filter(identity__isnull=True).iterator():
        if profile.user_id:identity,_=Identity.objects.get_or_create(user_id=profile.user_id,defaults={'name':profile.name})
        else:identity=Identity.objects.create(name=profile.name)
        profile.identity=identity;profile.save(update_fields=['identity'])
class Migration(migrations.Migration):
    dependencies=[('core','0028_personidentity_personprofile_identity_samplebundle')]
    operations=[migrations.RunPython(assign,migrations.RunPython.noop)]
