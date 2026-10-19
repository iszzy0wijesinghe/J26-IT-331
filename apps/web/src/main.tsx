import React from 'react';
import ReactDOM from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { App } from './app/App';
import './styles/global.css';
import './styles/c4.css';
import './styles/c4-metrics.css';
import './styles/c4-filters.css';
import './styles/c4/c4-MLExplorer.css';
import './styles/c4/c4-TelemetryExplorer.css';
import './styles/c4/c4-ThreatInvestigation.css';
import './styles/c4/c4-Authentication.css';
import './styles/c4/c4-Registry.css';
import './styles/c4/c4-Storage.css';
import './styles/c4/c4-Policy.css';
import './styles/c4/c4-HowC4Works.css';

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode><BrowserRouter><App /></BrowserRouter></React.StrictMode>
);
