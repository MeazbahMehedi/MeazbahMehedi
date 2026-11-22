const {test}=require('node:test');
const assert=require('node:assert/strict');
const {select,status,replaceBlock,toolTable,short,ageLabel,featured,researchLinks}=require('../scripts/sync_profile.cjs');
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

test('shortening preserves words and complete sentences',()=>{
 assert.equal(short('Independent CPU scale evaluation of medical reasoning',25),'Independent CPU scale…');
 assert.equal(short('A complete sentence. Additional information follows here.',30),'A complete sentence.');
 assert.equal(short('Already short',30),'Already short');
 assert.equal(short('longunbrokentoken',8).length,8);
});
test('commit ages include today and exact day boundaries',()=>{
 const now=Date.parse('2026-11-23T12:00:00Z');
 assert.equal(ageLabel('2026-11-23T11:00:00Z',now),'today');
 assert.equal(ageLabel('2026-11-22T12:00:00Z',now),'1 day ago');
 assert.equal(ageLabel('2026-11-03T12:00:00Z',now),'20 days ago');
});
test('featured quality signals are independent of activity order and exclude forks',()=>{
 const now=Date.parse('2026-11-23T12:00:00Z');
 const base={size:1,last_commit_at:'2026-11-23T12:00:00Z'};
 const repos=[{...base,name:'fresh'},{...base,name:'documented',last_commit_at:'2026-11-01',has_readme:true,has_release:true,description:'Documented project',stargazers_count:10},{...base,name:'fork',fork:true,has_readme:true,stargazers_count:1000}];
 assert.equal(select(repos,'owner')[0].name,'fresh');
 assert.equal(featured(repos,'owner',now)[0].name,'documented');
 assert.equal(featured(repos,'owner',now).length,2);
});
test('research links use matching files and encode paths',()=>{
 const repo={name:'evaluation',html_url:'https://github.com/test/evaluation',default_branch:'main'};
 const tree=[{type:'blob',path:'reports/Technical Report.pdf',size:10},{type:'blob',path:'results/summary.md',size:10},{type:'blob',path:'app.py',size:10},{type:'tree',path:'metrics.csv'}];
 const links=researchLinks(repo,tree);
 assert.equal(links.length,2);
 assert.equal(links[0].url,'https://github.com/test/evaluation/blob/main/reports/Technical%20Report.pdf');
 assert.equal(researchLinks({...repo,name:'website'},tree).length,0);
});
test('icon alt text excludes unsupported technologies and respects eight-icon limit',()=>{
 const html=toolTable(['Unknown','Python','JavaScript','TypeScript','HTML','CSS','C','C++','Java','Go'],[],[]);
 assert.doesNotMatch(html,/Unknown/);
 assert.equal(html.includes('alt="Python, JavaScript, TypeScript, HTML, CSS, C, C++, Java"'),true);
});
