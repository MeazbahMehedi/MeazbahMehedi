// GitHub Actions entry point. Only public, owned repositories are displayed.
const fs = require('node:fs');
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
function short(s,n) {
  const value=String(s ?? '').replace(/\s+/g,' ').trim();
  if(value.length<=n) return value;
  const part=value.slice(0,n-1);
  const sentence=part.match(/^.*[.!?](?=\s|$)/);
  if(sentence && sentence[0].length>=n/2) return sentence[0];
  const space=part.lastIndexOf(' ');
  return (space>0?part.slice(0,space):part)+'…';
}
function ageLabel(date,now=Date.now()) {
  const days=Math.max(0,Math.floor((now-Date.parse(date))/86400000));
  return days===0?'today':days===1?'1 day ago':days+' days ago';
}
function featureScore(repo,now) {
  const days=Math.max(0,(now-Date.parse(repo.last_commit_at))/86400000);
  return 30*Math.exp(-days/60)+(repo.has_readme?20:0)+(repo.description?10:0)+(repo.has_release?20:0)+Math.min(20,Math.log2(1+(repo.stargazers_count||0))*5);
}
function featured(repos,username,now=Date.now()) {
  const eligible=repos.filter(r=>!r.fork&&!r.private&&!r.archived&&!r.disabled&&r.size>0&&r.name.toLowerCase()!==username.toLowerCase()&&!(r.topics||[]).includes('profile-hidden'));
  return eligible.sort((a,b)=>featureScore(b,now)-featureScore(a,now)||String(b.last_commit_at).localeCompare(String(a.last_commit_at))||a.name.localeCompare(b.name)).slice(0,4);
}
function researchLinks(repo,tree) {
  if(!/research|evaluat|benchmark|experiment|paper|study|detection|domain.shift/i.test([repo.name,repo.description,...(repo.topics||[])].join(' '))) return [];
  return tree.filter(f=>f.type==='blob'&&f.size!==0).filter(f=>/\.pdf$/i.test(f.path)&&/report|paper|research|technical/i.test(f.path)||/(^|\/)(results?|findings|metrics|summary)[^/]*\.(md|csv|json)$/i.test(f.path)).sort((a,b)=>a.path.localeCompare(b.path)).slice(0,3).map(f=>({label:f.path,url:repo.html_url+'/blob/'+encodeURIComponent(repo.default_branch)+'/'+f.path.split('/').map(encodeURIComponent).join('/')}));
}
const languageIcons = {Python:'python',JavaScript:'js',TypeScript:'ts',HTML:'html',CSS:'css',C:'c','C++':'cpp',Java:'java',Go:'go',Rust:'rust',Shell:'bash',Jupyter:'python',Ruby:'ruby',PHP:'php',Kotlin:'kotlin',Swift:'swift',Dart:'dart',R:'r'};
function select(repos, username) {
  return repos.filter(r => !r.fork && !r.private && !r.archived && !r.disabled && !(r.topics || []).includes('profile-hidden') && r.size > 0 && r.name.toLowerCase() !== username.toLowerCase())
    .sort((a,b) => String(b.last_commit_at || b.pushed_at).localeCompare(String(a.last_commit_at || a.pushed_at)) || a.name.localeCompare(b.name)).slice(0,4);
}
const FINISHED_AFTER_MS = 20 * 24 * 60 * 60 * 1000;
function status(latestCommit, now = Date.now()) {
  const committed = Date.parse(latestCommit);
  if (!Number.isFinite(committed)) throw new Error('Missing or invalid last commit date');
  return now - committed >= FINISHED_AFTER_MS ? 'Finished' : 'Working on';
}
function replaceBlock(readme, name, body) {
  const begin = '<!-- SYNC:' + name + ':START -->', end = '<!-- SYNC:' + name + ':END -->';
  const a=readme.indexOf(begin), b=readme.indexOf(end);
  if(a<0 || b<a) throw new Error('Missing section markers: '+name);
  return readme.slice(0,a)+begin+'\n'+body+'\n'+readme.slice(b);
}
function toolTable(languages, frameworks, tools) {
  const techIcons={...languageIcons,Flask:'flask',FastAPI:'fastapi',PyTorch:'pytorch',Django:'django',React:'react',Vue:'vue',NextJS:'nextjs',TensorFlow:'tensorflow',SQLite:'sqlite',PostgreSQL:'postgres',Docker:'docker','GitHub Actions':'githubactions',Git:'git',GitHub:'github'};
  const row=(label,names)=>{
    const seen=new Set();
    const shown=names.filter(n=>{
      const icon=techIcons[n];
      if(!icon||seen.has(icon)) return false;
      seen.add(icon); return true;
    }).slice(0,8);
    const icons=shown.map(n=>techIcons[n]).join(',');
    return '<tr><td><strong>'+label+'</strong></td><td>'+(shown.length?'<picture><source media="(prefers-color-scheme: light)" srcset="https://skillicons.dev/icons?i='+icons+'&amp;theme=light" /><img src="https://skillicons.dev/icons?i='+icons+'&amp;theme=dark" height="40" alt="'+esc(shown.join(', '))+'" /></picture>':'No supported technology detected')+'</td></tr>';
  };
  return '<table>\n'+row('Languages',languages)+'\n'+row('Frameworks and data',frameworks)+'\n'+row('Tools',tools)+'\n</table>';
}
async function run({github, context, core}) {
  const owner=context.repo.owner;
  const repos=await github.paginate(github.rest.repos.listForUser,{username:owner,type:'owner',per_page:100});
  const own=repos.filter(r=>!r.fork && !r.private && r.name.toLowerCase()!==owner.toLowerCase());
  const now = Date.now();
  const activity = [];
  const totals={}, frameworks=new Set(), tools=new Set(['Git','GitHub']), details=new Map(), frameworkCounts=new Map();
  const rules=[[/\bflask\b/i,'Flask'],[/\bfastapi\b/i,'FastAPI'],[/\btorch\b/i,'PyTorch'],[/\bdjango\b/i,'Django'],[/"react"\s*:/i,'React'],[/"vue"\s*:/i,'Vue'],[/"next"\s*:/i,'NextJS'],[/\btensorflow\b/i,'TensorFlow'],[/\b(?:sqlite3?|sqlalchemy)\b/i,'SQLite'],[/\b(?:psycopg2?|asyncpg|pg)\b/i,'PostgreSQL']];
  for(const repo of own) {
    const args={owner,repo:repo.name};
    const {data:langs}=await github.rest.repos.listLanguages(args);
    for(const [name,size] of Object.entries(langs)) totals[name]=(totals[name]||0)+size;
    if(repo.archived || repo.disabled || !repo.size) continue;
    const {data:root}=await github.rest.repos.getContent({...args,path:''});
    if(!Array.isArray(root)) throw new Error('Invalid repository listing');
    const manifests=root.filter(f=>/^(requirements[^/]*\.txt|pyproject\.toml|Pipfile|package\.json|environment\.ya?ml)$/i.test(f.name));
    const text=[];
    for(const f of manifests) {
      const {data}=await github.rest.repos.getContent({...args,path:f.path});
      if(data.encoding!=='base64') throw new Error('Unsupported manifest encoding');
      text.push(Buffer.from(data.content,'base64').toString('utf8'));
    }
    const deps=text.join('\n'), detected=rules.filter(([pattern])=>pattern.test(deps)).map(([,name])=>name);
    detected.forEach(n=>{frameworks.add(n);frameworkCounts.set(n,(frameworkCounts.get(n)||0)+1);});
    if(root.some(f=>/^Dockerfile|^docker-compose|^compose\.ya?ml$/.test(f.name))) tools.add('Docker');
    const gh=root.find(f=>f.name==='.github' && f.type==='dir');
    if(gh) {
      const {data}=await github.rest.repos.getContent({...args,path:'.github'});
      if(Array.isArray(data) && data.some(f=>f.name==='workflows' && f.type==='dir')) tools.add('GitHub Actions');
    }
    const {data:commits}=await github.rest.repos.listCommits({...args,per_page:1});
    const last=commits[0]?.commit?.committer?.date;
    if (!Number.isFinite(Date.parse(last))) throw new Error('Missing last commit for '+repo.name);
    const {data:releases}=await github.rest.repos.listReleases({...args,per_page:20});
    const release=releases.find(r=>!r.draft&&!r.prerelease);
    activity.push({...repo,last_commit_at:new Date(last).toISOString(),has_readme:root.some(f=>/^readme(?:\.|$)/i.test(f.name)),has_release:!!release,release_url:release?.html_url});
    details.set(repo.name,{langs,detected});
  }
  const current=select(activity,owner), selected=featured(activity,owner,now);
  if(current.length!==4 || selected.length!==4) throw new Error('Need four eligible projects; keeping previous profile.');
  const entries=current.map(repo=>'- **'+status(repo.last_commit_at,now)+'** — <a href="'+esc(repo.html_url)+'">'+esc(repo.name)+'</a>: '+esc(short(repo.description||'Explore the latest code and documentation.',130))+' <sub>· Last commit: '+ageLabel(repo.last_commit_at,now)+'</sub>');
  const projects=selected.map((repo,i)=>{
    const detail=details.get(repo.name), state=status(repo.last_commit_at,now);
    const desc=repo.description||'Explore the code, documentation and latest updates.';
    const stack=[...new Set([...detail.detected,...Object.keys(detail.langs).sort((a,b)=>detail.langs[b]-detail.langs[a])])].slice(0,4);
    while(stack.reduce((n,s)=>n+s.length*7.2+30,32)>570) stack.pop();
    return {status:state,last_commit_at:repo.last_commit_at,slug:'live-'+(i+1),name:short(repo.name,30),category:state.toUpperCase(),summary:short(desc,58),description:short(desc,180),stack,url:repo.html_url,footer:'Last commit: '+ageLabel(repo.last_commit_at,now)+' · '+repo.stargazers_count+(repo.stargazers_count===1?' star':' stars')};
  });
  const research=[];
  for(const repo of activity.filter(r=>/research|evaluat|benchmark|experiment|paper|study|detection|domain.shift/i.test([r.name,r.description,...(r.topics||[])].join(' '))).sort((a,b)=>b.last_commit_at.localeCompare(a.last_commit_at)).slice(0,4)) {
    const {data:tree}=await github.rest.git.getTree({owner,repo:repo.name,tree_sha:repo.default_branch,recursive:'1'});
    if(tree.truncated) { core.warning('Research tree truncated for '+repo.name+'; skipping incomplete listing.'); continue; }
    const links=researchLinks(repo,tree.tree);
    if(repo.release_url) links.push({label:'Latest release',url:repo.release_url});
    if(links.length) research.push('- <a href="'+esc(repo.html_url)+'"><strong>'+esc(repo.name)+'</strong></a> — '+links.map(l=>'<a href="'+esc(l.url)+'">'+esc(l.label)+'</a>').join(' · '));
  }
  const languages=Object.keys(totals).sort((a,b)=>totals[b]-totals[a]);
  const cards=projects.map(p=>'<a href="'+esc(p.url)+'"><picture><source media="(prefers-color-scheme: light)" srcset="./assets/project-'+p.slug+'-light.svg" /><img src="./assets/project-'+p.slug+'-dark.svg" width="49%" alt="'+esc(p.name+': '+p.description)+'" /></picture></a>');
  let readme=fs.readFileSync('README.md','utf8');
  readme=replaceBlock(readme,'CURRENT',entries.join('\n'));
  readme=replaceBlock(readme,'PROJECTS','<p align="center">\n'+cards.slice(0,2).join('\n')+'\n</p>\n<p align="center">\n'+cards.slice(2).join('\n')+'\n</p>');
  readme=replaceBlock(readme,'TOOLS',toolTable(languages,[...frameworks].sort((a,b)=>frameworkCounts.get(b)-frameworkCounts.get(a)||a.localeCompare(b)),[...tools].sort()));
  readme=replaceBlock(readme,'RESEARCH',research.join('\n')||'Reports and findings will appear here when available in public research repositories.');
  const synced=new Date(now).toISOString().slice(0,16).replace('T',' ')+' UTC';
  const base='https://github.com/'+owner+'/'+context.repo.repo;
  readme=replaceBlock(readme,'HEALTH','[![Profile refresh]('+base+'/actions/workflows/profile.yml/badge.svg)]('+base+'/actions/workflows/profile.yml)\n\n<sub>Last synced: '+synced+' · Automatic hourly updates</sub>');
  const config={taglines:current.map(p=>short((status(p.last_commit_at,now)==='Finished'?'Finished: ':'Building: ')+p.name,40)),projects};
  // No output is changed until every API read and section validation succeeds.
  fs.writeFileSync('data/projects.json',JSON.stringify(config,null,2)+'\n');
  fs.writeFileSync('README.md',readme);
  core.info('Synced four projects, current work, languages and detected tools.');
}
module.exports={run,select,status,replaceBlock,toolTable,short,ageLabel,featureScore,featured,researchLinks};
