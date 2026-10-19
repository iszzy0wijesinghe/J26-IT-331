import { useState } from 'react';
import { NavLink, Outlet, useLocation } from 'react-router-dom';
import { Icon, type IconName } from '../components/ui/Icons';
const modules: { to: string; title: string; subtitle: string; icon: IconName; code: string }[] = [
  {to:'/c1',title:'Data Credibility',subtitle:'Sensor intelligence',icon:'shield',code:'01'},
  {to:'/c2',title:'Diagnostics',subtitle:'Device health',icon:'activity',code:'02'},
  {to:'/c3',title:'Temporal Forecasting',subtitle:'AI / ML workbench',icon:'chart',code:'03'},
  {to:'/c4',title:'Trust & Decisions',subtitle:'Explainable research',icon:'layers',code:'04'},
];
export function AppLayout(){
 const [open,setOpen]=useState(false); const location=useLocation();
 const current=modules.find(m=>location.pathname.startsWith(m.to));
 return <div className="shell">
   <aside className={`sidebar ${open?'sidebar-open':''}`}>
     <div className="brand"><div className="brand-mark"><Icon name="pulse" size={25}/></div><div><div className="brand-name">Geo<span>Nex</span><span className="brand-dot">.</span></div><div className="brand-caption">RESEARCH WORKBENCH</div></div></div>
     <div className="sidebar-section-label">WORKSPACE</div>
     <NavLink to="/" end className={({isActive})=>`nav-link ${isActive?'nav-active':''}`} onClick={()=>setOpen(false)}><Icon name="grid"/><span>Overview</span></NavLink>
     <div className="sidebar-section-label modules-label">RESEARCH COMPONENTS</div>
     {modules.map(m=><NavLink key={m.to} to={m.to} className={({isActive})=>`nav-link module-link ${isActive?'nav-active':''}`} onClick={()=>setOpen(false)}><Icon name={m.icon}/><span className="nav-label"><span>{m.title}</span><small>{m.subtitle}</small></span><span className="module-code">{m.code}</span></NavLink>)}
     <div className="sidebar-bottom"><div className="research-badge"><span className="status-dot"/> PP1 · Standalone components</div><p>Research demonstration environment. Not a public safety warning system.</p></div>
   </aside>
   {open&&<button className="mobile-backdrop" aria-label="Close menu" onClick={()=>setOpen(false)}/>}
   <div className="main-shell"><header className="topbar"><div className="topbar-left"><button className="menu-button" aria-label="Open navigation" onClick={()=>setOpen(!open)}><Icon name={open?'x':'menu'}/></button><div className="breadcrumb"><span>Workspace</span><Icon name="chevron" size={14}/><strong>{current?current.title:'Overview'}</strong></div></div><div className="topbar-right"><span className="environment-pill"><span className="status-dot"/> Research environment</span><div className="avatar">GN</div></div></header><main className="content"><Outlet/></main><footer className="footer"><span>GeoNex · Independent component demonstrations</span><span>Synthetic research data · PP1</span></footer></div>
 </div>
}
