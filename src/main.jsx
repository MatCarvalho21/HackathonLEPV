import React from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css'; // base primeiro: os estilos da jornada (pp.css, importado pelo App) sobrepõem
import App from './App.jsx';

createRoot(document.getElementById('root')).render(
  <React.StrictMode><App /></React.StrictMode>,
);
