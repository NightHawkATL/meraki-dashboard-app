import React, { useContext, useEffect, useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Box, CircularProgress, Typography } from '@mui/material';
import { AuthContext, AuthProvider } from './context/AuthContext.jsx';
import { ThemeContextProvider } from './context/ThemeContext.jsx'; // <-- New
import Login from './components/Login.jsx';
import Setup from './components/Setup.jsx';
import Layout from './components/Layout.jsx';
import Home from './components/Home.jsx';

// Placeholder Pages (We will build these out next!)
// const Home = () => <Typography variant="h4">Script Execution (Main Page)</Typography>;
const History = () => <Typography variant="h4">Recent History Page</Typography>;
const Settings = () => <Typography variant="h4">Settings & API Keys</Typography>;

const ProtectedRoute = ({ children }) => {
  const { token } = useContext(AuthContext);
  return token ? children : <Navigate to="/login" />;
};

const AppContent = () => {
  const { token } = useContext(AuthContext);
  const [adminExists, setAdminExists] = useState(null);

  const checkStatus = async () => {
    try {
      const res = await fetch('/api/auth/status');
      const data = await res.json();
      setAdminExists(data.admin_exists);
    } catch (err) {
      console.error("Failed to check system status");
    }
  };

  useEffect(() => { checkStatus(); }, []);

  if (adminExists === null) {
    return <Box sx={{ display: 'flex', justifyContent: 'center', mt: 20 }}><CircularProgress /></Box>;
  }

  // Define our URL Rules!
  return (
    <Routes>
      {/* Public Routes */}
      <Route path="/setup" element={!adminExists ? <Setup onSetupComplete={checkStatus} /> : <Navigate to="/login" />} />
      <Route path="/login" element={!token ? (!adminExists ? <Navigate to="/setup" /> : <Login />) : <Navigate to="/" />} />

      {/* Private Routes (Wrapped in the Layout we just built) */}
      <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
        <Route index element={<Home />} />
        <Route path="history" element={<History />} />
        <Route path="settings" element={<Settings />} />
      </Route>
    </Routes>
  );
};

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <ThemeContextProvider>
          <AppContent />
        </ThemeContextProvider>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;