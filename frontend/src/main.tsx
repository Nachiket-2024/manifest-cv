import React from 'react';
import ReactDOM from 'react-dom/client';
import { QueryClientProvider } from '@tanstack/react-query';
import { ChakraProvider } from '@chakra-ui/react';

import App from './App.tsx';

// The app's custom Chakra system (theme tokens/semantic tokens), built on
// top of Chakra's defaultConfig rather than replacing it.
import { system } from './theme/system.ts';

// Auth/permissions state itself lives in Zustand (store/authStore.ts),
// which needs no Provider since it's a module-level singleton reachable
// from any component directly.
import { queryClient } from './store/queryClient.ts';

// Imported here, eagerly, purely for its module-load side effect of
// applying the persisted/OS color mode class to <html> BEFORE the first
// paint. Importing it later (e.g. only from Navbar, where the toggle
// button lives) would apply that class after React's first render,
// causing a visible flash of the wrong theme for a user who previously
// chose dark mode.
import './store/themeStore.ts';

// Must be called once, before the app renders, so every API call made
// during the initial session check is already covered.
import { setupAuthInterceptor } from './api/setupAuthInterceptor.ts';

const rootElement = document.getElementById('root') as HTMLElement;

setupAuthInterceptor();

ReactDOM.createRoot(rootElement).render(
    <React.StrictMode>
        <QueryClientProvider client={queryClient}>
            <ChakraProvider value={system}>
                <App />
            </ChakraProvider>
        </QueryClientProvider>
    </React.StrictMode>
);
