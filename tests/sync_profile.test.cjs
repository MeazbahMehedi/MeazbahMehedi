const {test}=require('node:test');
const assert=require('node:assert/strict');
const {select,status,replaceBlock,toolTable,short,ageLabel,featured,researchLinks,formatChinaTime,sanitizePrivate,run}=require('../scripts/sync_profile.cjs');
test('four newest original public projects, excluding profile, archived and forks',()=>{
 const repo=(name,extra={})=>({name,size:1,pushed_at:'2026-01-01',...extra});
 const rows=[repo('owner'),repo('fork',{fork:true}),repo('secret',{private:true}),repo('old',{archived:true}),repo('hidden',{topics:['profile-hidden']}),...['a','b','c','d','e'].map((n,i)=>repo(n,{pushed_at:'2026-01-0'+(i+1)}))];
 assert.deepEqual(select(rows,'owner').map(r=>r.name),['e','d','c','b']);
});
test('seven-day boundary is exact and new work restores active status',()=>{
 const now=Date.parse('2026-11-23T12:00:00Z');
 assert.equal(status('2026-11-16T12:00:00.001Z',now),'Working on');
 assert.equal(status('2026-11-16T12:00:00Z',now),'Under future development');
 assert.equal(status('2026-10-01T12:00:00Z',now),'Under future development');
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
 assert.equal(ageLabel('2026-11-16T12:00:00Z',now),'7 days ago');
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


test('China Standard Time handles the next calendar day',()=>{
 assert.equal(formatChinaTime(Date.parse('2026-11-27T16:09:00Z')),'2026-11-28 00:09 China Standard Time (UTC+08:00)');
});

test('approved private summaries publish only the allowed metadata',()=>{
 const project={name:'KeyFlow',description:'Keyboard entry',last_commit_at:'2026-11-27T16:00:00Z',secret:'do-not-publish',html_url:'private-link',files:['private.py']};
 const summary=sanitizePrivate(project,['KeyFlow'],Date.parse('2026-11-28T00:00:00Z'));
 assert.deepEqual(Object.keys(summary).sort(),['description','last_commit_at','name']);
 assert.throws(()=>sanitizePrivate({...project,name:'unapproved'},['KeyFlow']));
 assert.throws(()=>sanitizePrivate({...project,last_commit_at:'2099-01-01'},['KeyFlow']));
});

function fixture(){
 const now=Date.parse('2026-11-28T00:00:00Z');
 const sections=['CURRENT','PROJECTS','TOOLS','RESEARCH','HEALTH'];
 const files={
  'README.md':sections.map(n=>'<!-- SYNC:'+n+':START -->\nold\n<!-- SYNC:'+n+':END -->').join('\n'),
  'data/profile-config.json':JSON.stringify({timezone:'Asia/Shanghai',inactive_after_days:7,private_projects:['KeyFlow','scholarsend']}),
  'data/private-projects.json':JSON.stringify({projects:[{name:'KeyFlow',description:'Keyboard entry',last_commit_at:'2026-11-27T16:00:00Z'},{name:'scholarsend',description:'Academic scheduling',last_commit_at:'2026-11-26T12:00:00Z'}]})
 };
 const repos=Array.from({length:4},(_,i)=>({name:'public'+i,size:0,html_url:'https://github.com/owner/public'+i,default_branch:'main',description:'Public project',stargazers_count:0}));
 repos.push({name:'empty',size:0,html_url:'https://github.com/owner/empty'});
 let writes=0;
 const io={readFileSync:p=>files[p],writeFileSync:(p,c)=>{files[p]=c;writes++;}};
 const dates=Object.fromEntries(repos.map((r,i)=>[r.name,'2026-11-'+(20-i)+'T00:00:00Z']));
 const github={paginate:async()=>repos,rest:{repos:{
  listForUser:()=>{},listLanguages:async()=>({data:{Python:100}}),
  listCommits:async({repo})=>{if(repo==='empty'){const e=new Error('Empty repo');e.status=409;throw e;}return {data:[{commit:{committer:{date:dates[repo]}}}]};},
  getContent:async()=>({data:[{name:'README.md',type:'file'}]}),listReleases:async()=>({data:[]})
 }}};
 const core={info:()=>{},warning:()=>{}};
 const context={repo:{owner:'owner',repo:'owner'},eventName:'schedule'};
 return {now,files,io,github,core,context,writes:()=>writes};
}

test('full sync includes zero-size committed repos and approved private activity without private links',async()=>{
 const f=fixture(); await run(f);
 assert.match(f.files['README.md'],/Working on.*KeyFlow/);
 assert.match(f.files['README.md'],/scholarsend/);
 assert.doesNotMatch(f.files['README.md'],/href="[^"]*(KeyFlow|scholarsend)/);
 assert.match(f.files['README.md'],/China Standard Time/);
 const projects=JSON.parse(f.files['data/projects.json']).projects;
 assert.equal(projects.length,4);
 assert.equal(projects.some(p=>p.name==='empty'),false);
 assert.equal(projects.some(p=>p.name==='public0'),true);
 assert.match(f.files['README.md'],/Under future development/);
 assert.doesNotMatch(f.files['README.md'],/Finished =|Status updates hourly|Detected from/);
});

test('authenticated private polling updates only the allowlisted summaries',async()=>{
 const f=fixture(); const names=[];
 f.privateGithub={rest:{repos:{get:async({repo})=>{names.push(repo);return {data:{description:'Latest approved description',private:true}};},listCommits:async()=>({data:[{commit:{committer:{date:'2026-11-27T23:00:00Z'}}}]})}}};
 await run(f);
 assert.deepEqual(names,['KeyFlow','scholarsend']);
 const snapshot=JSON.parse(f.files['data/private-projects.json']);
 assert.equal(snapshot.projects.every(p=>p.last_commit_at==='2026-11-27T23:00:00.000Z'),true);
});

test('private polling failure preserves last observed summaries and still updates public projects',async()=>{
 const f=fixture();
 f.privateGithub={rest:{repos:{get:async()=>{throw Object.assign(new Error('Unavailable'),{status:403});}}}};
 await run(f);
 const snapshot=JSON.parse(f.files['data/private-projects.json']).projects.find(p=>p.name==='KeyFlow');
 assert.equal(snapshot.last_commit_at,'2026-11-27T16:00:00.000Z');
 assert.match(f.files['README.md'],/public0/);
});
