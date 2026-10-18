import type { ReactNode } from 'react';
export type IconName = 'grid'|'shield'|'activity'|'chart'|'layers'|'settings'|'chevron'|'arrow'|'check'|'clock'|'terminal'|'database'|'brain'|'play'|'pulse'|'menu'|'x';
const paths: Record<IconName, ReactNode> = {
 grid:<><rect x="3" y="3" width="7" height="7" rx="1"/><rect x="14" y="3" width="7" height="7" rx="1"/><rect x="3" y="14" width="7" height="7" rx="1"/><rect x="14" y="14" width="7" height="7" rx="1"/></>,
 shield:<><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"/><path d="m9 12 2 2 4-4"/></>,
 activity:<path d="M2 12h4l3-8 5 16 3-8h5"/>,
 chart:<><path d="M3 3v18h18"/><path d="m7 15 4-5 4 3 5-7"/></>,
 layers:<><path d="m12 2 9 5-9 5-9-5 9-5Z"/><path d="m3 12 9 5 9-5M3 17l9 5 9-5"/></>,
 settings:<><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.6 1.6 0 0 0 .32 1.77l.06.06-2 2-.06-.06A1.6 1.6 0 0 0 16 18.4a1.6 1.6 0 0 0-1 1.47V20h-3v-.13a1.6 1.6 0 0 0-1-1.47 1.6 1.6 0 0 0-1.77.32l-.06.06-2-2 .06-.06A1.6 1.6 0 0 0 7.6 15a1.6 1.6 0 0 0-1.47-1H6v-3h.13a1.6 1.6 0 0 0 1.47-1A1.6 1.6 0 0 0 7.28 8.2l-.06-.06 2-2 .06.06A1.6 1.6 0 0 0 11 6.6a1.6 1.6 0 0 0 1-1.47V5h3v.13a1.6 1.6 0 0 0 1 1.47 1.6 1.6 0 0 0 1.77-.32l.06-.06 2 2-.06.06A1.6 1.6 0 0 0 19.4 10a1.6 1.6 0 0 0 1.47 1H21v3h-.13A1.6 1.6 0 0 0 19.4 15Z"/></>,
 chevron:<path d="m9 18 6-6-6-6"/>, arrow:<path d="M5 12h14m-6-6 6 6-6 6"/>,
 check:<path d="m4 12 5 5L20 6"/>, clock:<><circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/></>,
 terminal:<><rect x="2" y="3" width="20" height="18" rx="2"/><path d="m6 8 4 4-4 4m6 0h5"/></>,
 database:<><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M3 5v14c0 1.7 4 3 9 3s9-1.3 9-3V5M3 12c0 1.7 4 3 9 3s9-1.3 9-3"/></>,
 brain:<><path d="M12 18V5a3 3 0 0 0-5-2 4 4 0 0 0-4 5 4 4 0 0 0 0 7 4 4 0 0 0 5 5 3 3 0 0 0 4-2ZM12 18V5a3 3 0 0 1 5-2 4 4 0 0 1 4 5 4 4 0 0 1 0 7 4 4 0 0 1-5 5 3 3 0 0 1-4-2Z"/><path d="M8 8v4m8-4v4"/></>,
 play:<path d="m8 5 12 7-12 7V5Z"/>, pulse:<><path d="M2 12h5l3-6 4 12 3-6h5"/></>,
 menu:<path d="M4 6h16M4 12h16M4 18h16"/>,x:<path d="M5 5l14 14M19 5 5 19"/>
};
export function Icon({ name, size=19, className='' }:{name:IconName,size?:number,className?:string}){return <svg className={className} width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{paths[name]}</svg>}
