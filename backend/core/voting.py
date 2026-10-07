"""Online named ballots and separately recorded hand/secret paper counts."""
import uuid
from collections import Counter
from django.conf import settings
from django.core.exceptions import ValidationError,PermissionDenied
from django.db import transaction
from .models import Meeting,MeetingEvent,Vote,Ballot,Decision,Mandate
from .live_service import assert_writer,effective_voters,event
from .meetings_service import lock_meeting,meeting_access

RULES=('majority_cast','majority_present','two_thirds_statutory','unanimous','election')

def eligible(context,vote):
    if not meeting_access(context,'private',vote.meeting):return None
    p=next((p for p in effective_voters(vote.meeting,vote.item) if p.user_id==context.user_id and str(p.pk) in vote.electorate),None)
    if not p:return None
    from django.utils import timezone
    day=timezone.localdate()
    if not Mandate.objects.filter(pk=p.mandate_id,user=context.user,committee=vote.meeting.committee,archived=False,starts_on__lte=day,ends_on__gte=day,voting=True).exists():return None
    return p

@transaction.atomic
def open_vote(context,meeting_id,version,device,epoch,wording,mode,rule,options):
    obj=lock_meeting(context,meeting_id,'live',version);assert_writer(obj,context,device,epoch)
    if obj.state!='live' or obj.paused or not obj.active_item_id:raise ValidationError('Laufende Sitzung und aufgerufener TOP erforderlich.')
    if obj.votes.filter(state='open').exists():raise ValidationError('Zuerst den laufenden Versuch abschließen oder abbrechen.')
    determination=obj.events.filter(kind='quorum',item=obj.active_item).order_by('-version').first()
    changes=obj.events.filter(kind__in=['presence','conflict','top','roster']).order_by('-version').first()
    if not determination or not determination.payload.get('confirmed') or changes and changes.version>determination.version:raise ValidationError('Aktuelle Beschlussfähigkeit durch Vorsitz feststellen lassen und dokumentieren.')
    if mode not in ('manual','named','secret') or rule not in RULES:raise ValidationError('Ungültiges Abstimmungsverfahren.')
    if not wording.strip() or len(wording)>100000:raise ValidationError('Abstimmungswortlaut erforderlich.')
    options=[s.strip() for s in options if s.strip()]
    if not 2<=len(options)<=30 or len(set(options))!=len(options) or any(len(s)>200 for s in options):raise ValidationError('Zwei bis dreißig unterschiedliche Optionen erforderlich.')
    if rule!='election' and options!=['Ja','Nein','Enthaltung']:raise ValidationError('Sachbeschlüsse verwenden Ja, Nein, Enthaltung.')
    voters=effective_voters(obj,obj.active_item)
    if not voters:raise ValidationError('Keine Stimmberechtigten anwesend.')
    if mode=='named' and any(not p.user_id for p in voters):raise ValidationError('Digital benötigt jede berechtigte Person ein Konto; sonst Papierverfahren wählen.')
    obj.version+=1;obj.save(update_fields=['version'])
    vote=Vote.objects.create(meeting=obj,item=obj.active_item,wording=wording,mode=mode,rule=rule,options=options,electorate=[str(p.pk) for p in voters],opened_version=obj.version)
    event(obj,context,device,'vote_open',{'vote_id':str(vote.pk),'wording':wording,'mode':mode,'rule':rule,'options':options,'electorate':vote.electorate})
    return vote

@transaction.atomic
def cast(context,vote_id,choice,request_id):
    vote=Vote.objects.select_related('meeting','item').get(pk=vote_id)
    obj=Meeting.objects.select_for_update().get(pk=vote.meeting_id);vote.meeting=obj
    if obj.leading_server!=settings.SERVER_ROLE or obj.state!='live' or obj.paused or vote.state!='open' or vote.mode!='named':raise ValidationError('Abstimmung nicht geöffnet.')
    person=eligible(context,vote)
    if not person:raise PermissionDenied('Kein Stimmrecht im aktiven Kontext.')
    if choice not in vote.options:raise ValidationError('Unbekannte Option.')
    previous=Ballot.objects.filter(vote=vote,participant=person).first()
    if previous:
        if previous.choice==choice and previous.request_id==request_id:return previous
        raise ValidationError('Stimme bereits verbindlich abgegeben.')
    if Ballot.objects.filter(request_id=request_id).exists():raise ValidationError('Stimm-ID bereits verwendet.')
    return Ballot.objects.create(vote=vote,participant=person,choice=choice,request_id=request_id)

def calculate(vote,counts,invalid):
    cast_count=sum(counts.values());total=len(vote.electorate)
    result={'counts':counts,'invalid':invalid,'missing':total-cast_count-invalid,'eligible':total,'outcome':'unresolved'}
    if vote.rule=='election':
        maximum=max(counts.values(),default=0);leaders=[k for k,v in counts.items() if v==maximum]
        result['leaders']=leaders;result['outcome']='chair_determination_required';return result
    yes=counts.get('Ja',0);no=counts.get('Nein',0)
    required={'majority_cast':(yes+no)//2+1,'majority_present':total//2+1,'two_thirds_statutory':(2*vote.meeting.statutory_count+2)//3,'unanimous':total}[vote.rule]
    result.update(required=required,outcome='accepted' if yes>=required else 'rejected')
    return result

@transaction.atomic
def finish(context,vote_id,version,device,epoch,counts=None,invalid=0,abort=False):
    vote=Vote.objects.select_related('meeting').get(pk=vote_id)
    obj=lock_meeting(context,vote.meeting_id,'live',version);assert_writer(obj,context,device,epoch)
    if vote.state!='open':raise ValidationError('Versuch bereits geschlossen.')
    if abort:vote.state='aborted';vote.result={}
    else:
        if obj.paused:raise ValidationError('Sitzung pausiert.')
        if set(vote.electorate)!={str(p.pk) for p in effective_voters(obj,vote.item)}:raise ValidationError('Stimmberechtigtenkreis geändert; Versuch abbrechen.')
        if vote.mode=='named':counts=dict(Counter(vote.ballots.values_list('choice',flat=True)));invalid=0
        elif not isinstance(counts,dict) or set(counts)!=set(vote.options):raise ValidationError('Alle Optionen einzeln auszählen.')
        if any(type(v)!=int or v<0 for v in counts.values()) or type(invalid)!=int or invalid<0 or sum(counts.values())+invalid>len(vote.electorate):raise ValidationError('Unplausible Auszählung.')
        vote.state='closed';vote.result=calculate(vote,counts,invalid)
    vote.save(update_fields=['state','result']);obj.version+=1;obj.save(update_fields=['version'])
    event(obj,context,device,'vote_close',{'vote_id':str(vote.pk),'state':vote.state,'result':vote.result})
    return vote

@transaction.atomic
def confirm(context,vote_id,version,device,epoch,wording,reason):
    vote=Vote.objects.select_related('meeting').get(pk=vote_id)
    obj=lock_meeting(context,vote.meeting_id,'live',version);assert_writer(obj,context,device,epoch)
    if vote.state!='closed' or not reason.strip() or not wording.strip() or len(wording)>100000:raise ValidationError('Geschlossene Auszählung, endgültiger Wortlaut und Feststellung des Vorsitzes erforderlich.')
    decision=Decision.objects.create(vote=vote,wording=wording,result=vote.result,chair_confirmation=reason[:1000],confirmed_by=context.user)
    vote.state='confirmed';vote.save(update_fields=['state']);obj.version+=1;obj.save(update_fields=['version'])
    event(obj,context,device,'decision',{'decision_id':str(decision.pk),'vote_id':str(vote.pk),'wording':wording,'result':vote.result,'chair_confirmation':reason})
    return decision
