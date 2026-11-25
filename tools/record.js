const {chromium}=require('playwright'); const {execFileSync}=require('child_process'); const fs=require('fs');
const out=process.argv[2]; const data={}; let last=Date.now();
const trim=(u,j)=>{
  if(/\/summary\?/.test(u)) return {boxscore:{players:(j.boxscore?.players||[]).map(tp=>({team:{id:tp.team?.id},statistics:(tp.statistics||[]).slice(0,1).map(st=>({labels:st.labels,names:st.names,
    athletes:(st.athletes||[]).map(a=>({starter:a.starter,didNotPlay:a.didNotPlay,stats:a.stats,athlete:{id:a.athlete?.id,displayName:a.athlete?.displayName,shortName:a.athlete?.shortName,position:{abbreviation:a.athlete?.position?.abbreviation},headshot:a.athlete?.headshot?{href:a.athlete.headshot.href}:undefined}}))}))}))}};
  if(/\/injuries$/.test(u)) return {injuries:(j.injuries||[]).map(t=>({id:t.id,displayName:t.displayName,injuries:(t.injuries||[]).map(i=>({status:i.status,shortComment:i.shortComment,
    athlete:{id:i.athlete?.id,displayName:i.athlete?.displayName,position:{abbreviation:i.athlete?.position?.abbreviation},links:(i.athlete?.links||[]).slice(0,1).map(l=>({href:l.href}))}}))}))};
  if(/\/schedule\?/.test(u)) return {events:(j.events||[]).map(e=>({id:e.id,date:e.date,competitions:(e.competitions||[]).slice(0,1).map(c=>({status:{type:{completed:c.status?.type?.completed}},
    competitors:(c.competitors||[]).map(x=>({homeAway:x.homeAway,winner:x.winner,score:x.score,id:x.id,team:{id:x.team?.id,abbreviation:x.team?.abbreviation}}))}))}))};
  if(/\/gamelog$/.test(u)) return {labels:j.labels,seasonTypes:j.seasonTypes,events:Object.fromEntries(Object.entries(j.events||{}).map(([k,v])=>[k,{gameDate:v.gameDate,opponent:{abbreviation:v.opponent?.abbreviation}}]))};
  if(/\/scoreboard\?/.test(u)) return {events:(j.events||[]).map(e=>({id:e.id,date:e.date,status:e.status,competitions:(e.competitions||[]).slice(0,1).map(c=>({competitors:c.competitors,odds:(c.odds||[]).slice(0,1).map(o=>{const {link,header,footer,...r}=o; for(const k of ['moneyline','pointSpread','total']) if(r[k]) r[k]=JSON.parse(JSON.stringify(r[k],(kk,vv)=>kk==='link'?undefined:vv)); return r;})}))}))};
  return j; };
(async()=>{const b=await chromium.launch(); const p=await b.newPage({viewport:{width:400,height:860}});
await p.route(/https:\/\/(site\.api|site\.web\.api)\.espn\.com\/.*/, async route=>{ const u=route.request().url();
  try{ const body=execFileSync('curl',['-sS','--max-time','20','-f',u],{maxBuffer:64<<20}); const j=JSON.parse(body); data[u]=trim(u,j); last=Date.now();
    await route.fulfill({status:200,contentType:'application/json',headers:{'access-control-allow-origin':'*'},body}); }catch(e){ await route.fulfill({status:502,body:''}); } });
await p.route(/https:\/\/a\.espncdn\.com\/.*/, r=>r.abort());
await p.goto('file:///home/user/courtside-edge/index.html');
while(Date.now()-last<15000) await p.waitForTimeout(2000);
console.log('sub:',await p.evaluate(()=>document.querySelector('#hdr-sub').textContent),'requests',Object.keys(data).length);
fs.writeFileSync(out,JSON.stringify({t:Date.now(),data})); await b.close();})();
