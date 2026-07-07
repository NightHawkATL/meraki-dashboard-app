import React, { useContext, useEffect, useState } from 'react';
import { Container, Typography, Box, Button, CircularProgress } from '@mui/material';
import { AuthContext, AuthProvider } from './context/AuthContext.jsx';
import Login from './components/Login.jsx';
import Setup from './components/Setup.jsx'; // Import the new setup screen

const Dashboard = () => {
  const { logout } = useContext(AuthContext);
  return (
    <Container maxWidth="md">
      <Box sx={{ mt: 10, textAlign: 'center' }}>
        <Typography variant="h3" gutterBottom color="primary">Welcome to the Dashboard!</Typography>
        <Button variant="outlined" color="error" onClick={logout}>Log Out</Button>
      </Box>
    </Container>
  );
};

const AppContent = () => {
  const { token } = useContext(AuthContext);
  const [adminExists, setAdminExists] = useState(null);

  // Check if the database has an admin user yet
  const checkStatus = async () => {
    try {
      const res = await fetch('/api/auth/status');
      const data = await res.json();
      setAdminExists(data.admin_exists);
    } catch (err) {
      console.error("Failed to check system status");
    }
  };

  useEffect(() => {
    checkStatus();
  }, []);

  // Show a loading spinner while we check the database
  if (adminExists === null) {
    return <Box sx={{ display: 'flex', justifyContent: 'center', mt: 20 }}><CircularProgress /></Box>;
  }

  // If no admin exists, show the Setup screen
  if (!adminExists) {
    return <Setup onSetupComplete={checkStatus} />;
  }

  // Otherwise, run the normal Login/Dashboard flow
  return token ? <Dashboard /> : <Login />;
};

function App() {
  return (
    <AuthProvider>
      <AppContent />
    </AuthProvider>
  );
}

export default App;