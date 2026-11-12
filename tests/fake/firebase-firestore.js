// Minimal in-browser stand-in for the Firestore SDK, used only by tests/e2e.py.
// Data lives in localStorage 'fakefs' (simulates the cloud). Flags in localStorage:
//   fake-deny      -> listeners fail with permission-denied
//   fake-offline   -> only cache snapshots, never a server snapshot
//   fake-fail-once -> first round of listeners fails with 'unavailable'
const K='fakefs';
const store=()=>window.__fs||(window.__fs=JSON.parse(localStorage.getItem(K)||'{}'));
const persist=()=>localStorage.setItem(K,JSON.stringify(store()));
const listeners=new Set();
window.__ops=0;
const rev=o=>o&&Object.fromEntries(Object.entries(o).reverse());   // scramble key order like the real SDK may
export function initializeFirestore(){return {}}
export const persistentLocalCache=()=>({}),persistentMultipleTabManager=()=>({});
export function doc(db,...s){return{type:'doc',path:s.join('/')}}
export function collection(db,...s){return{type:'col',path:s.join('/')}}
function snapFor(ref,fromCache){const st=fromCache&&localStorage.getItem('fake-offline')&&localStorage.getItem('fake-empty-cache')?{}:store();
  if(ref.type==='doc'){const d=st[ref.path];return{exists:()=>!!d,data:()=>rev(structuredClone(d)),metadata:{fromCache,hasPendingWrites:false}}}
  const pre=ref.path+'/';
  const docs=Object.keys(st).filter(p=>p.startsWith(pre)&&!p.slice(pre.length).includes('/')).sort().map(p=>({id:p.slice(pre.length),data:()=>rev(structuredClone(st[p]))}));
  return{docs,metadata:{fromCache,hasPendingWrites:false}}}
export function onSnapshot(ref,opts,next,err){
  if(localStorage.getItem('fake-deny')){setTimeout(()=>err({code:'permission-denied'}),20);return()=>{}}
  if(localStorage.getItem('fake-fail-once')&&!window.__failedOnce){setTimeout(()=>{window.__failedOnce=true;err({code:'unavailable'})},20);return()=>{}}
  const l={ref,next};listeners.add(l);
  setTimeout(()=>listeners.has(l)&&next(snapFor(ref,true)),5);
  if(!localStorage.getItem('fake-offline'))setTimeout(()=>listeners.has(l)&&next(snapFor(ref,false)),60);
  return()=>listeners.delete(l)}
function notify(){listeners.forEach(l=>l.next(snapFor(l.ref,false)))}
export function writeBatch(){const ops=[];return{set(r,d){ops.push(['s',r.path,d])},delete(r){ops.push(['d',r.path])},
  commit(){const st=store();ops.forEach(([t,p,d])=>{window.__ops++;if(t==='s')st[p]=structuredClone(d);else delete st[p]});persist();setTimeout(notify,0);return Promise.resolve()}}}
export async function terminate(){}
export async function clearIndexedDbPersistence(){}
export async function waitForPendingWrites(){}
window.__fakeRemote=(path,data)=>{const st=store();if(data===null)delete st[path];else st[path]=data;persist();notify()};
