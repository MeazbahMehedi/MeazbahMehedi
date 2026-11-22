const {test}=require('node:test');
const assert=require('node:assert/strict');
const {select,status,replaceBlock,toolTable}=require('../scripts/sync_profile.cjs');
test('four newest original public projects, excluding profile, archived and forks',()=>{
 const repo=(name,extra={})=>({name,size:1,pushed_at:'2026-01-01',...extra});
 const rows=[repo('owner'),repo('fork',{fork:true}),repo('secret',{private:true}),repo('old',{archived:true}),repo('hidden',{topics:['profile-hidden']}),...['a','b','c','d','e'].map((n,i)=>repo(n,{pushed_at:'2026-01-0'+(i+1)}))];
 assert.deepEqual(select(rows,'owner').map(r=>r.name),['e','d','c','b']);
});
test('completion is explicit and new work after a release is active',()=>{
 assert.equal(status({topics:['profile-completed']},null),'Completed');
 assert.equal(status({}, {tag_name:'v1',published_at:'2026-01-01'},'2026-01-02'),'Working on');
 assert.equal(status({}, {tag_name:'v1',published_at:'2026-01-02'},'2026-01-01'),'Released v1');
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
