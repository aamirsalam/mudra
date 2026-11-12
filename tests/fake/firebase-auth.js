const K='fake-user';const cbs=[];
const get=()=>{try{return JSON.parse(localStorage.getItem(K))}catch(e){return null}};
const auth={};
export function getAuth(){return auth}
function emit(){cbs.forEach(cb=>cb(get()))}
export function onAuthStateChanged(a,cb){cbs.push(cb);setTimeout(()=>cb(get()),10);return()=>{}}
export class GoogleAuthProvider{setCustomParameters(){}}
export async function signInWithPopup(){localStorage.setItem(K,JSON.stringify({email:localStorage.getItem('fake-email')||'aamir.salam5@gmail.com',uid:'u1'}));emit();return{}}
export const signInWithRedirect=signInWithPopup;
export async function getRedirectResult(){return null}
export async function signOut(){localStorage.removeItem(K);emit()}
