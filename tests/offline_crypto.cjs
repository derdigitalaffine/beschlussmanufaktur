const {test}=require('node:test');
const assert=require('node:assert/strict');
const {seal,open}=require('../backend/static/offline_store.js');
const password='Eine lange lokale Passphrase 2026';
test('private contents are encrypted, authenticated and bound to their local identity',async()=>{
 const data={expires_at:'2027-01-01',markdown:'GEHEIME NOTIZ',queue:[{kind:'presence'}]};
 const a=await seal(data,password,'account.context.meeting'),b=await seal(data,password,'account.context.meeting');
 assert(!JSON.stringify(a).includes('GEHEIME'));assert.notEqual(a.cipher,b.cipher);assert.deepEqual(await open(a,password),data);
 await assert.rejects(open(a,'Eine andere falsche Passphrase'));
 await assert.rejects(open({...a,id:'another-account'},password));
 await assert.rejects(open({...a,cipher:a.cipher.substring(0,10)+'AA'+a.cipher.substring(12)},password));
});
test('large packet buffer works without JavaScript argument overflow',async()=>{
 const data={expires_at:'2027-01-01',packet:'a'.repeat(2*1024*1024)};assert.deepEqual(await open(await seal(data,password,'large'),password),data);
});
test('short passwords are refused',async()=>{await assert.rejects(seal({expires_at:'2027-01-01'},'short','id'));});
