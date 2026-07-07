import React, { useState } from 'react';
import { Box, Button, TextField, Typography, Paper, Alert } from '@mui/material';

const Setup = ({ onSetupComplete }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleSetup = async (e) => {
    e.preventDefault();
    setError('');

    try {
      const response = await fetch('/api/auth/setup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });

      if (response.ok) {
        onSetupComplete(); // Tells App.jsx to switch to the Login screen!
      } else {
        const data = await response.json();
        setError(data.detail || 'Failed to create admin.');
      }
    } catch (err) {
      setError('Cannot connect to the server.');
    }
  };

  return (
    <Box sx={{ height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <Paper elevation={3} sx={{ p: 4, width: '100%', maxWidth: 400 }}>
        <Typography variant="h4" gutterBottom align="center" color="primary">
          Welcome to Meraki App
        </Typography>
        <Typography variant="body1" gutterBottom align="center" sx={{ mb: 3 }}>
          Let's create your master Admin account.
        </Typography>
        
        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
        
        <form onSubmit={handleSetup}>
          <TextField
            fullWidth label="Admin Email / Username" variant="outlined" margin="normal"
            value={username} onChange={(e) => setUsername(e.target.value)} required
          />
          <TextField
            fullWidth label="Secure Password" type="password" variant="outlined" margin="normal"
            value={password} onChange={(e) => setPassword(e.target.value)} required
          />
          <Button fullWidth type="submit" variant="contained" color="success" size="large" sx={{ mt: 3 }}>
            Create Admin Account
          </Button>
        </form>
      </Paper>
    </Box>
  );
};

export default Setup;