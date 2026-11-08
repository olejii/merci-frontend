import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { initializeApi } from 'src/api/client.ts';

import './index.css';

import App from './App.tsx';

import './styles/global.css';

initializeApi().then(() =>
  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <App />
    </StrictMode>,
  ),
);
