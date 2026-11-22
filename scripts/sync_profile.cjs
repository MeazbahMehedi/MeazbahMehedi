// GitHub Actions entry point. Only public, owned repositories are displayed.
const fs = require('node:fs');
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const short = (s,n) => String(s ?? '').replace(/\s+/g,' ').trim().slice(0,n);
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
  const row=(label, names) => {
    const icons=[...new Set(names.map(n=>languageIcons[n] || ({Flask:'flask',FastAPI:'fastapi',PyTorch:'pytorch',Django:'django',React:'react',Vue:'vue',NextJS:'nextjs',TensorFlow:'tensorflow',SQLite:'sqlite',PostgreSQL:'postgres',Docker:'docker','GitHub Actions':'githubactions',Git:'git',GitHub:'github'})[n]).filter(Boolean))].slice(0,12);
    return '<tr><td><strong>'+label+'</strong></td><td>'+(icons.length ? '<picture><source media="(prefers-color-scheme: light)" srcset="https://skillicons.dev/icons?i='+icons.join(',')+'&amp;theme=light" /><img src="https://skillicons.dev/icons?i='+icons.join(',')+'&amp;theme=dark" height="40" alt="'+esc(names.join(', '))+'" /></picture>' : 'No supported technology detected')+'</td></tr>';
  };
  return '<table>\n'+row('Languages',languages)+'\n'+row('Frameworks and data',frameworks)+'\n'+row('Tools',tools)+'\n</table>\n\n<sub>Detected from public repositories and dependency files. Refreshes hourly.</sub>';
}
async function run({github, context, core}) {
  const owner=context.repo.owner;
  const repos=await github.paginate(github.rest.repos.listForUser,{username:owner,type:'owner',per_page:100});
  const own=repos.filter(r=>!r.fork && !r.private && r.name.toLowerCase()!==owner.toLowerCase());
  const now = Date.now();
  const activity = [];
  const totals={}, frameworks=new Set(), tools=new Set(['Git','GitHub']), details=new Map();
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
    detected.forEach(n=>frameworks.add(n));
    if(root.some(f=>/^Dockerfile|^docker-compose|^compose\.ya?ml$/.test(f.name))) tools.add('Docker');
    const gh=root.find(f=>f.name==='.github' && f.type==='dir');
    if(gh) {
      const {data}=await github.rest.repos.getContent({...args,path:'.github'});
      if(Array.isArray(data) && data.some(f=>f.name==='workflows' && f.type==='dir')) tools.add('GitHub Actions');
    }
    const {data:commits}=await github.rest.repos.listCommits({...args,per_page:1});
    const last=commits[0]?.commit?.committer?.date;
    if (!Number.isFinite(Date.parse(last))) throw new Error('Missing last commit for '+repo.name);
    activity.push({...repo,last_commit_at:new Date(last).toISOString()});
    details.set(repo.name,{langs,detected});
  }
  const selected=select(activity,owner);
  if(selected.length!==4) throw new Error('Need four eligible projects; keeping previous profile.');
  const projects=[], entries=[];
  for(let i=0;i<selected.length;i++) {
    const repo=selected[i], args={owner,repo:repo.name}, detail=details.get(repo.name);
    const state=status(repo.last_commit_at, now);
    const desc=short(repo.description || 'Explore the code, documentation and latest updates.',180);
    const stack=[...new Set([...Object.keys(detail.langs).sort((a,b)=>detail.langs[b]-detail.langs[a]),...detail.detected])].slice(0,4);
    const project={status:state,last_commit_at:repo.last_commit_at,slug:'live-'+(i+1),name:short(repo.name,30),category:short(state,28).toUpperCase(),summary:short(desc,58),description:desc,stack,url:repo.html_url};
    // Keep chips within the existing card's fixed width.
    while(project.stack.reduce((n,s)=>n+s.length*7.2+30,32)>570) project.stack.pop();
    project.description=short(desc,145)+' · '+repo.stargazers_count+(repo.stargazers_count===1?' star':' stars');
    projects.push(project);
    entries.push('- **'+esc(state)+'** — <a href="'+esc(repo.html_url)+'">'+esc(repo.name)+'</a>: '+esc(short(desc,130)));
  }
  const languages=Object.keys(totals).sort((a,b)=>totals[b]-totals[a]);
  const cards=projects.map(p=>'<a href="'+esc(p.url)+'"><picture><source media="(prefers-color-scheme: light)" srcset="./assets/project-'+p.slug+'-light.svg" /><img src="./assets/project-'+p.slug+'-dark.svg" width="49%" alt="'+esc(p.name+': '+p.description)+'" /></picture></a>');
  let readme=fs.readFileSync('README.md','utf8');
  readme=replaceBlock(readme,'CURRENT',entries.join('\n')+'\n\n<sub>Status updates hourly. Finished = no default-branch commits for 20 days; a new commit returns it to Working on.</sub>');
  readme=replaceBlock(readme,'PROJECTS','<p align="center">\n'+cards.slice(0,2).join('\n')+'\n</p>\n<p align="center">\n'+cards.slice(2).join('\n')+'\n</p>');
  readme=replaceBlock(readme,'TOOLS',toolTable(languages,[...frameworks].sort(),[...tools].sort()));
  const config={taglines:projects.map(p=>short((p.status==='Finished'?'Finished: ':'Building: ')+p.name,40)),projects};
  // No output is changed until every API read and section validation succeeds.
  fs.writeFileSync('data/projects.json',JSON.stringify(config,null,2)+'\n');
  fs.writeFileSync('README.md',readme);
  core.info('Synced four projects, current work, languages and detected tools.');
}
module.exports={run,select,status,replaceBlock,toolTable};
