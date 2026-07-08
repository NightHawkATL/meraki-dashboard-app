import React, { useState, useContext } from 'react';
import { AuthContext } from '../context/AuthContext.jsx';
import { Box, Button, TextField, Typography, Paper, Alert } from '@mui/material';

const Login = () => {
  const { login } = useContext(AuthContext);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const handleLogin = async (e) => {
    e.preventDefault();
    setError('');

    // Package the credentials as Form Data instead of JSON
    const formData = new URLSearchParams();
    formData.append('username', username);
    formData.append('password', password);

    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/x-www-form-urlencoded' 
        },
        body: formData, // Send the formData object here
      });

      const data = await response.json();

      if (response.ok) {
        login(data.access_token);
      } else {
        setError(data.detail || 'Failed to log in');
      }
    } catch (err) {
      setError('Cannot connect to the server.');
    }
  };

  return (
    <Box sx={{ height: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <Paper elevation={3} sx={{ p: 4, width: '100%', maxWidth: 400 }}>
        <Typography variant="h4" gutterBottom align="center">
          Meraki Admin
        </Typography>
        
        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
        
        <form onSubmit={handleLogin}>
          <TextField
            fullWidth
            label="Email / Username"
            variant="outlined"
            margin="normal"
            value={username}
            onChange={(e) => setUsername(e.target.value)}
          />
          <TextField
            fullWidth
            label="Password"
            type="password"
            variant="outlined"
            margin="normal"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          <Button 
            fullWidth 
            type="submit" 
            variant="contained" 
            color="primary" 
            size="large" 
            sx={{ mt: 3 }}
          >
            Log In
          </Button>
        </form>
      </Paper>
    </Box>
  );
};

export default Login;