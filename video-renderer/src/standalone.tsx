import React from 'react';
import { createRoot } from 'react-dom/client';
import AppRouter from './ui/AppRouter';

const container = document.getElementById('root');
if (!container) throw new Error('#root not found');

createRoot(container).render(<AppRouter />);
