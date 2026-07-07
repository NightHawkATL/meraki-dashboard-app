import React, { createContext, useState, useMemo, useEffect } from 'react';
import { ThemeProvider, createTheme, CssBaseline, useMediaQuery } from '@mui/material';

export const ThemeContext = createContext();

export const ThemeContextProvider = ({ children }) => {
  // Load saved preference or default to 'system'
  const [themeMode, setThemeMode] = useState(localStorage.getItem('themeMode') || 'system');
  
  // Detect if the user's Windows/Mac is in Dark Mode
  const prefersDarkMode = useMediaQuery('(prefers-color-scheme: dark)');

  const changeTheme = (mode) => {
    setThemeMode(mode);
    localStorage.setItem('themeMode', mode);
  };

  // Figure out the actual color to display based on the selection
  const activeMode = themeMode === 'system' ? (prefersDarkMode ? 'dark' : 'light') : themeMode;

  const theme = useMemo(
    () =>
      createTheme({
        palette: {
          mode: activeMode,
          primary: { main: '#1976d2' }, // Standard blue, easy to change to IHG colors later!
          background: {
            default: activeMode === 'dark' ? '#121212' : '#f5f5f5',
            paper: activeMode === 'dark' ? '#1e1e1e' : '#ffffff',
          },
        },
      }),
    [activeMode]
  );

  return (
    <ThemeContext.Provider value={{ themeMode, changeTheme }}>
      <ThemeProvider theme={theme}>
        <CssBaseline />
        {children}
      </ThemeProvider>
    </ThemeContext.Provider>
  );
};