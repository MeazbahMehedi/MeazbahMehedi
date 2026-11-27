const {test}=require('node:test');
const assert=require('node:assert/strict');
const {check}=require('../scripts/check_profile_changes.cjs');
function fixture(){
 const state={date:'2026-11-27T00:00:00Z',stars:0,description:'Project',release:[],count:1};
 const files={'data/profile-config.json':JSON.stringify({timezone:'Asia/Shanghai',private_projects:['KeyFlow']}),'data/private-projects.json':JSON.stringify({projects:[{name:'KeyFlow',description:'Keyboard entry',last_commit_at:'2026-11-27T01:00:00Z'}]})};
 let writes=0;
 const io={readFileSync:p=>{if(!(p in files))throw Object.assign(new Error('Missing'),{code:'ENOENT'});return files[p];},writeFileSync:(p,c)=>{files[p]=c;writes++;}};
 const github={paginate:async()=>[{name:'public',size:0,default_branch:'main',description:state.description,stargazers_count:state.stars}],rest:{repos:{listForUser:()=>{},listCommits:async()=>({data:[{commit:{committer:{date:state.date}}}]}),listReleases:async()=>({data:state.release})}},graphql:async()=>({user:{contributionsCollection:{contributionCalendar:{weeks:[{contributionDays:[{date:'2026-11-27',contributionCount:state.count}]}]}}}})};
 return {state,files,io,github,context:{repo:{owner:'owner'},eventName:'schedule'},core:{info:()=>{},warning:()=>{}},now:Date.parse('2026-11-28T00:00:00Z'),writes:()=>writes};
}
test('unchanged five-minute check creates no extra snapshot or publish request',async()=>{
 const f=fixture();assert.equal(await check(f),true);const first=f.files['data/profile-inputs.json'];
 f.now+=300000;assert.equal(await check(f),false);
 assert.equal(f.files['data/profile-inputs.json'],first);assert.equal(f.writes(),1);
});
test('new commit, stars, description, release and calendar changes trigger refresh',async()=>{
 for(const [field,value] of [['date','2026-11-27T02:00:00Z'],['stars',1],['description','New description'],['release',[{tag_name:'v1',updated_at:'2026-11-28',prerelease:false}]],['count',2]]){
  const f=fixture();await check(f);f.state[field]=value;assert.equal(await check(f),true,field);
 }
});
test('the seven-day boundary triggers a refresh without any new commit',async()=>{
 const f=fixture();f.now=Date.parse('2026-12-04T00:00:00Z')-1;await check(f);f.now+=1;
 assert.equal(await check(f),true);
 assert.match(f.files['data/profile-inputs.json'],/Under future development/);
});
test('new public repository is automatically discovered',async()=>{
 const f=fixture();await check(f);
 f.github.paginate=async()=>[{name:'new-project',size:0,description:'New project'}];
 assert.equal(await check(f),true);
 assert.match(f.files['data/profile-inputs.json'],/new-project/);
});
test('manual run refreshes even if account inputs match',async()=>{
 const f=fixture();await check(f);f.context.eventName='workflow_dispatch';assert.equal(await check(f),true);
});
test('private polling detects latest commit without publishing private code or URLs',async()=>{
 const f=fixture();await check(f);
 f.privateGithub={rest:{repos:{get:async()=>({data:{description:'Fresh description',html_url:'hidden',files:['secret.py']}}),listCommits:async()=>({data:[{commit:{committer:{date:'2026-11-27T03:00:00Z'},message:'secret'}}]})}}};
 assert.equal(await check(f),true);
 assert.match(f.files['data/profile-inputs.json'],/Fresh description/);
 assert.doesNotMatch(f.files['data/profile-inputs.json'],/hidden|secret\.py|message/);
});
