"""Typed formsets for additional fields and parallel/conditional review steps."""
import hashlib,json
from django import forms
from django.forms import formset_factory
from .models import TemplateKind
from .templates_service import validate_configuration

def fingerprint(obj):return hashlib.sha256(json.dumps({'name':obj.name,'text':obj.initial_markdown,'fields':obj.fields,'workflow':obj.workflow,'four_eyes':obj.four_eyes},sort_keys=True).encode()).hexdigest()
class KindForm(forms.ModelForm):
    expected=forms.CharField(widget=forms.HiddenInput)
    class Meta:
        model=TemplateKind;fields=['name','initial_markdown','four_eyes'];labels={'name':'Vorlagenart','initial_markdown':'Standardabschnitte (Markdown)','four_eyes':'Vieraugenprinzip'}
class FieldForm(forms.Form):
    key=forms.RegexField(label='Feldschlüssel (klein, ohne Leerzeichen)',regex=r'^[a-z][a-z0-9_]{0,39}$',max_length=40)
    label=forms.CharField(label='Beschriftung',max_length=100)
    type=forms.ChoiceField(label='Inhalt',choices=[('text','Text'),('number','Zahl'),('date','Datum'),('choice','Auswahl'),('boolean','Ja/Nein')])
    required=forms.BooleanField(label='Pflichtfeld',required=False)
    section=forms.CharField(label='Abschnitt',required=False,max_length=100)
    choices_text=forms.CharField(label='Auswahlwerte (eine Zeile pro Wert)',required=False,widget=forms.Textarea(attrs={'rows':3}))
class StepForm(forms.Form):
    name=forms.CharField(label='Prüfschritt',max_length=100)
    role=forms.ChoiceField(label='Rolle',choices=[('reviewer','Fachbereichsleitung'),('release','Freigabe'),('clerk','Sitzungsdienst')])
    group=forms.IntegerField(label='Gruppe (gleiche Nummer = parallel)',min_value=1,max_value=100)
    substitute=forms.ChoiceField(label='Vertretung',required=False,choices=[('','Keine'),('reviewer','Fachbereichsleitung'),('release','Freigabe'),('clerk','Sitzungsdienst')])
    condition_field=forms.CharField(label='Nur wenn Zusatzfeld (Feldschlüssel)',max_length=40,required=False)
    condition_value=forms.CharField(label='Entspricht Wert (Ja/Nein: true/false)',max_length=200,required=False)

def sets(request,obj):
    def count(key,existing,maximum):
        try:return min(max(int(request.GET.get(key,existing+2)),existing,2),maximum)
        except ValueError:return min(existing+2,maximum)
    initial_fields=[{**f,'choices_text':'\n'.join(f.get('choices',[]))} for f in obj.fields]
    initial_steps=[{**s,'condition_field':s.get('condition',{}).get('field',''),'condition_value':json.dumps(s['condition']['equals'],ensure_ascii=False) if 'condition' in s and not isinstance(s['condition']['equals'],str) else s.get('condition',{}).get('equals','')} for s in obj.workflow]
    data=request.POST if request.method=='POST' else None
    fields=formset_factory(FieldForm,extra=max(0,count('felder',len(initial_fields),40)-len(initial_fields)),can_delete=True,max_num=40,validate_max=True,absolute_max=40)(data,initial=initial_fields,prefix='fields')
    steps=formset_factory(StepForm,extra=max(0,count('schritte',len(initial_steps),12)-len(initial_steps)),can_delete=True,max_num=12,validate_max=True,absolute_max=12)(data,initial=initial_steps,prefix='steps')
    return fields,steps

def build(fields,steps):
    result=[];workflow=[]
    for form in fields:
        d=form.cleaned_data
        if not d or d.get('DELETE'):continue
        value={k:d[k] for k in ('key','label','type','required')}
        if d['section']:value['section']=d['section']
        if d['type']=='choice':
            choices=[x.strip() for x in d['choices_text'].splitlines() if x.strip()]
            if not choices or len(choices)>100 or len(set(choices))!=len(choices):raise forms.ValidationError('Auswahlfeld benötigt 1 bis 100 unterschiedliche Werte.')
            value['choices']=choices
        result.append(value)
    types={f['key']:f['type'] for f in result}
    for form in steps:
        d=form.cleaned_data
        if not d or d.get('DELETE'):continue
        value={k:d[k] for k in ('name','role','group')}
        if d['substitute']:value['substitute']=d['substitute']
        if d['condition_field']:
            raw=d['condition_value'];kind=types.get(d['condition_field'])
            try:equals=json.loads(raw) if kind in ('number','boolean') else raw
            except ValueError:raise forms.ValidationError('Bedingungswert muss zum Feldtyp passen.')
            if kind=='boolean' and not isinstance(equals,bool) or kind=='number' and (isinstance(equals,bool) or not isinstance(equals,(int,float))):raise forms.ValidationError('Bedingungswert muss zum Feldtyp passen.')
            value['condition']={'field':d['condition_field'],'equals':equals}
        workflow.append(value)
    validate_configuration(result,workflow);return result,workflow
