export type ModelAvailability = {model:string;horizon_minutes:number;available:boolean};
export type C3Health = {status:string;component:string;scope:string};
export type ModelsResponse = {models:ModelAvailability[];note:string};
const BASE='/api/c3';
async function getJson<T>(path:string, signal?:AbortSignal):Promise<T>{
 const response=await fetch(`${BASE}${path}`,{signal});
 if(!response.ok) throw new Error(`C3 API returned HTTP ${response.status}`);
 return response.json() as Promise<T>;
}
export const c3Api={health:(signal?:AbortSignal)=>getJson<C3Health>('/health',signal),models:(signal?:AbortSignal)=>getJson<ModelsResponse>('/models',signal)};
