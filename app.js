let M=null,META=null,IDX=new Map(),DOC=new Map();

const q=document.getElementById("q");
const court=document.getElementById("court");
const year=document.getElementById("year");
const sort=document.getElementById("sort");
const st=document.getElementById("st");
const res=document.getElementById("res");
const searchBtn=document.getElementById("searchBtn");

const low=s=>String(s||"").replaceAll("İ","i").replaceAll("I","ı").toLocaleLowerCase("tr-TR");

function toks(s){
  const a=low(s).match(/[0-9a-zçğıöşü]+/g)||[];
  return [...new Set(a.filter(x=>x.length>=3))];
}

function shard(tok){
  let h=5381;
  for(const ch of tok){
    h=(((h<<5)+h)+ch.codePointAt(0))>>>0;
  }
  return h%64;
}

function decode(a){
  let x=0;
  return a.map(d=>(x+=d));
}

async function getIdx(s){
  if(IDX.has(s)) return IDX.get(s);
  const r=await fetch(`index/i-${String(s).padStart(2,"0")}.json`);
  if(!r.ok) throw new Error("İndeks parçası açılamadı: "+r.status);
  const d=await r.json();
  IDX.set(s,d);
  return d;
}

async function postings(t){
  const d=await getIdx(shard(t));
  return d[t]?decode(d[t]):[];
}

function intersect(a,b){
  let i=0,j=0,r=[];
  while(i<a.length&&j<b.length){
    if(a[i]===b[j]){r.push(a[i]);i++;j++;}
    else if(a[i]<b[j]) i++;
    else j++;
  }
  return r;
}

function metaById(id){
  return META[id-1];
}

async function getDoc(id){
  const ci=Math.floor((id-1)/M.doc_chunk);
  if(!DOC.has(ci)){
    const r=await fetch(`docs/d-${String(ci).padStart(3,"0")}.json`);
    if(!r.ok) throw new Error("Karar metni açılamadı: "+r.status);
    const d=await r.json();
    DOC.set(ci,new Map(d.map(x=>[x.id,x.text])));
  }
  return DOC.get(ci).get(id)||"";
}

function snippet(text,ts){
  const l=low(text);
  let p=-1;
  for(const t of ts){
    const x=l.indexOf(t);
    if(x>=0&&(p<0||x<p)) p=x;
  }
  if(p<0) return text.slice(0,850);
  const a=Math.max(0,p-220),b=Math.min(text.length,p+760);
  return (a?"…":"")+text.slice(a,b)+(b<text.length?"…":"");
}

async function init(){
  const mr=await fetch("manifest.json");
  if(!mr.ok) throw new Error("manifest.json açılamadı: "+mr.status);
  M=await mr.json();

  const rr=await fetch("meta.json");
  if(!rr.ok) throw new Error("meta.json açılamadı: "+rr.status);
  META=await rr.json();

  st.textContent=M.count.toLocaleString("tr-TR")+" karar hazır.";
}

async function go(){
  const raw=q.value.trim();
  const ts=toks(raw);
  const cf=low(court.value.trim());
  const yf=year.value.trim();

  if(!raw&&!cf&&!yf){
    st.textContent="Arama veya filtre girin.";
    return;
  }

  st.textContent="İndekste aranıyor...";
  res.innerHTML="";
  searchBtn.disabled=true;

  try{
    let ids=null;

    if(ts.length){
      const lists=[];
      for(const t of ts){
        const p=await postings(t);
        if(!p.length){
          st.textContent="0 sonuç bulundu.";
          return;
        }
        lists.push(p);
      }

      lists.sort((a,b)=>a.length-b.length);
      ids=lists[0];

      for(let i=1;i<lists.length;i++){
        ids=intersect(ids,lists[i]);
        if(!ids.length) break;
      }
    }else{
      ids=META.map(x=>x.row_id);
    }

    let cand=ids
      .map(metaById)
      .filter(x=>x &&
        (!cf||low(x.court).includes(cf)) &&
        (!yf||String(x.year)===yf)
      );

    if(sort.value==="date"){
      cand.sort((a,b)=>String(b.karar_tarihi||"").localeCompare(String(a.karar_tarihi||"")));
    }

    const pool=cand.slice(0,200);
    const scored=[];

    for(const m of pool){
      const text=await getDoc(m.row_id);
      const l=low(text);
      let score=0;

      if(raw&&l.includes(low(raw))) score+=100;

      for(const t of ts){
        let p=0,c=0;
        while((p=l.indexOf(t,p))>=0&&c<12){
          score+=4;
          c++;
          p+=t.length;
        }
      }

      scored.push({m,text,score});
    }

    if(sort.value==="rel"){
      scored.sort((a,b)=>
        b.score-a.score ||
        String(b.m.karar_tarihi||"").localeCompare(String(a.m.karar_tarihi||""))
      );
    }

    const shown=scored.slice(0,60);
    st.textContent=cand.length+" sonuç bulundu; ilk "+shown.length+" gösteriliyor.";
    res.innerHTML="";

    for(const x of shown){
      const c=document.createElement("div");
      c.className="c";

      const title=document.createElement("b");
      title.textContent=x.m.court||"Yargıtay";

      const mm=document.createElement("div");
      mm.className="m";
      mm.textContent=`E: ${x.m.esas_no||""}   K: ${x.m.karar_no||""}   Tarih: ${x.m.karar_tarihi||""}`;

      const t=document.createElement("div");
      t.className="t";
      t.textContent=snippet(x.text,ts);

      const bt=document.createElement("button");
      bt.className="more";
      bt.textContent="Tam Kararı Aç";
      bt.onclick=()=>{
        t.textContent=x.text;
        bt.remove();
      };

      c.append(title,mm,t,bt);
      res.append(c);
    }
  }catch(e){
    st.textContent="Hata: "+e.message;
  }finally{
    searchBtn.disabled=false;
  }
}

searchBtn.addEventListener("click",go);
document.addEventListener("keydown",e=>{
  if(e.key==="Enter") go();
});

init().catch(e=>{
  st.textContent="Yükleme hatası: "+e.message;
});
