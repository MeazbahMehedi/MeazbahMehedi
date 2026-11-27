// Lightweight account check: run the full generators only for meaningful input changes.
const fs = require('node:fs');
const {status,ageLabel,sanitizePrivate} = require('./sync_profile.cjs');
async function check({github,privateGithub,context,core,io=fs,now=Date.now()}) {
  const settings=JSON.parse(io.readFileSync('data/profile-config.json','utf8'));
  const owner=context.repo.owner;
  const repos=await github.paginate(github.rest.repos.listForUser,{username:owner,type:'owner',per_page:100});
  const publicProjects=[];
  for(const repo of repos.filter(r=>!r.private&&!r.fork&&r.name.toLowerCase()!==owner.toLowerCase()).sort((a,b)=>a.name.localeCompare(b.name))) {
    const record={name:repo.name,description:repo.description||'',archived:!!repo.archived,disabled:!!repo.disabled,branch:repo.default_branch||'',topics:[...(repo.topics||[])].sort(),stars:repo.stargazers_count||0,issues:repo.open_issues_count||0,pushed:repo.pushed_at||'',updated:repo.updated_at||''};
    if(!repo.archived&&!repo.disabled) {
      try {
        const {data:commits}=await github.rest.repos.listCommits({owner,repo:repo.name,per_page:1});
        const date=commits[0]?.commit?.committer?.date;
        if(date) Object.assign(record,{last_commit_at:date,status:status(date,now),age:ageLabel(date,now)});
        const {data:releases}=await github.rest.repos.listReleases({owner,repo:repo.name,per_page:20});
        record.releases=releases.filter(r=>!r.draft).map(r=>({tag:r.tag_name,updated:r.updated_at,prerelease:!!r.prerelease}));
      } catch(error) { if(error.status!==409&&error.status!==404) throw error; record.empty=true; }
    }
    publicProjects.push(record);
  }
  const cached=JSON.parse(io.readFileSync('data/private-projects.json','utf8')).projects||[];
  const privateProjects=[];
  for(const name of [...settings.private_projects].sort()) {
    let summary=cached.find(p=>p.name===name);
    if(privateGithub) {
      try {
        const {data:repo}=await privateGithub.rest.repos.get({owner,repo:name});
        const {data:commits}=await privateGithub.rest.repos.listCommits({owner,repo:name,per_page:1});
        summary={name,description:repo.description,last_commit_at:commits[0]?.commit?.committer?.date};
      } catch(error) { core.warning('Private check unavailable for '+name+'; using last observed summary.'); }
    }
    if(summary) {
      const clean=sanitizePrivate(summary,settings.private_projects,now);
      privateProjects.push({...clean,status:status(clean.last_commit_at,now),age:ageLabel(clean.last_commit_at,now)});
    }
  }
  let contributions=null;
  // Calendar changes (issues, pull requests, reviews) should also refresh the charts.
  if(github.graphql) {
    const start=new Date(now);start.setUTCDate(start.getUTCDate()-30);start.setUTCHours(0,0,0,0);
    const response=await github.graphql('query($login:String!,$from:DateTime!,$to:DateTime!){user(login:$login){contributionsCollection(from:$from,to:$to){contributionCalendar{weeks{contributionDays{date contributionCount}}}}}}',{login:owner,from:start.toISOString(),to:new Date(now).toISOString()});
    contributions=response.user.contributionsCollection.contributionCalendar.weeks.flatMap(w=>w.contributionDays).map(d=>({date:d.date,count:d.contributionCount}));
  }
  const inputs={schema:1,utcDate:new Date(now).toISOString().slice(0,10),timezone:settings.timezone,privateReadConfigured:!!privateGithub,publicProjects,privateProjects,contributions};
  const next=JSON.stringify(inputs,null,2)+'\n';
  let previous='';try{previous=io.readFileSync('data/profile-inputs.json','utf8');}catch(error){if(error.code!=='ENOENT')throw error;}
  const changed=context.eventName!=='schedule'||next!==previous;
  if(changed) io.writeFileSync('data/profile-inputs.json',next);
  core.info(changed?'Account changes detected; refreshing profile.':'No account changes; skipped generators and publishing.');
  return changed;
}
module.exports={check};
