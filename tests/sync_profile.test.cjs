const {test}=require('node:test');
const assert=require('node:assert/strict');
const {select,status,replaceBlock,toolTable}=require('../scripts/sync_profile.cjs');
test('four newest original public projects, excluding profile, archived and forks',()=>{
 const repo=(name,extra={})=>({name,size:1,pushed_at:'2026-01-01',...extra});
 const rows=[repo('owner'),repo('fork',{fork:true}),repo('secret',{private:true}),repo('old',{archived:true}),repo('hidden',{topics:['profile-hidden']}),...['a','b','c','d','e'].map((n,i)=>repo(n,{pushed_at:'2026-01-0'+(i+1)}))];
 assert.deepEqual(select(rows,'owner').map(r=>r.name),['e','d','c','b']);
});
test('20-day boundary is exact and completion needs no topic or release',()=>{
 const now=Date.parse('2026-11-23T12:00:00Z');
 assert.equal(status('2026-11-03T12:00:00.001Z',now),'Working on');
 assert.equal(status('2026-11-03T12:00:00Z',now),'Finished');
 assert.equal(status('2026-10-01T12:00:00Z',now),'Finished');
 assert.equal(status('2026-11-23T11:59:00Z',now),'Working on');
 assert.throws(()=>status(undefined,now));
 assert.throws(()=>status('invalid',now));
});
test('actual commits rank projects ahead of metadata and tag pushes',()=>{
 const rows=Array.from({length:5},(_,i)=>({name:'p'+i,size:1,pushed_at:'2026-11-23',last_commit_at:'2026-11-0'+(i+1)}));
 rows[0].pushed_at='2026-12-01';
 assert.deepEqual(select(rows,'owner').map(r=>r.name),['p4','p3','p2','p1']);
});
test('section updates preserve personal content and reject missing markers',()=>{
 assert.equal(replaceBlock('intro<!-- SYNC:X:START -->old<!-- SYNC:X:END -->quote','X','new'),'intro<!-- SYNC:X:START -->\nnew\n<!-- SYNC:X:END -->quote');
 assert.throws(()=>replaceBlock('personal content','X','new'));
});
test('tool rendering does not invent unsupported technologies',()=>{
 const html=toolTable(['Python','Unknown'],['PyTorch'],['GitHub Actions']);
 assert.match(html,/i=python&amp;/); assert.match(html,/i=pytorch&amp;/);
 assert.doesNotMatch(html,/pycharm|docker/);
});
