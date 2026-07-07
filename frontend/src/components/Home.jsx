import React, { useState } from 'react';
import { 
  Box, Grid, Card, CardContent, Typography, TextField, 
  MenuItem, Button, Autocomplete, Divider, Paper 
} from '@mui/material';
import { Map as MapIcon, LocationOn, Phone } from '@mui/icons-material';

// --- MOCK DATA (We will replace this with live DB data later) ---
const availableScripts = [
  { id: 'port_bounce', name: 'Bounce Switch Ports' },
  { id: 'vlan_update', name: 'Update Guest VLANs' },
  { id: 'device_status', name: 'Get Device Status Report' }
];

const cachedOrgs = [
  { id: 'org_1', name: 'IHG Corporate' },
  { id: 'org_2', name: 'Test Lab Org' }
];

const cachedNetworks = {
  'org_1': [
    { id: 'net_1', name: 'ATLAA - Main Network' },
    { id: 'net_2', name: 'NYCBB - Guest Network' }
  ],
  'org_2': [
    { id: 'net_3', name: 'Lab Router 1' }
  ]
};
// ----------------------------------------------------------------

const Home = () => {
  const [selectedScript, setSelectedScript] = useState('');
  const [selectedOrg, setSelectedOrg] = useState('');
  const [selectedNetwork, setSelectedNetwork] = useState('');
  const [searchQuery, setSearchQuery] = useState(null);

  // When a user uses the Smart Search, Auto-Fill the Org and Network!
  const handleSmartSearch = (event, newValue) => {
    setSearchQuery(newValue);
    if (newValue) {
      // Find which org this network belongs to
      const orgId = Object.keys(cachedNetworks).find(org => 
        cachedNetworks[org].some(net => net.id === newValue.id)
      );
      if (orgId) {
        setSelectedOrg(orgId);
        setSelectedNetwork(newValue.id);
      }
    }
  };

  // Flatten networks for the search bar
  const allNetworks = Object.values(cachedNetworks).flat();

  // Determine if we are ready to execute
  const isReadyToExecute = selectedScript && selectedOrg && selectedNetwork;

  return (
    <Box sx={{ maxWidth: 1200, mx: 'auto' }}>
      
      {/* 1. SMART SEARCH BAR */}
      <Paper elevation={2} sx={{ p: 2, mb: 4 }}>
        <Typography variant="h6" gutterBottom color="primary">Smart Search</Typography>
        <Autocomplete
          options={allNetworks}
          getOptionLabel={(option) => option.name}
          onChange={handleSmartSearch}
          value={searchQuery}
          renderInput={(params) => (
            <TextField {...params} label="Search for Inncode, Hotel Name, or Network..." variant="outlined" />
          )}
        />
      </Paper>

      {/* 2. CASCADING SELECTION BOXES (Horizontal Row) */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        {/* Box 1: Script */}
        <Grid item xs={12} md={4}>
          <Card elevation={selectedScript ? 1 : 3} sx={{ borderTop: selectedScript ? '4px solid #4caf50' : '4px solid #1976d2' }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>1. Select Script</Typography>
              <TextField select fullWidth label="Available Scripts" value={selectedScript} onChange={(e) => setSelectedScript(e.target.value)}>
                {availableScripts.map((script) => (
                  <MenuItem key={script.id} value={script.id}>{script.name}</MenuItem>
                ))}
              </TextField>
            </CardContent>
          </Card>
        </Grid>

        {/* Box 2: Organization */}
        <Grid item xs={12} md={4}>
          <Card elevation={selectedOrg ? 1 : 3} sx={{ opacity: selectedScript ? 1 : 0.5, transition: 'opacity 0.3s' }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>2. Select Organization</Typography>
              <TextField select fullWidth label="Organization" value={selectedOrg} 
                onChange={(e) => { setSelectedOrg(e.target.value); setSelectedNetwork(''); }}
                disabled={!selectedScript}
              >
                {cachedOrgs.map((org) => (
                  <MenuItem key={org.id} value={org.id}>{org.name}</MenuItem>
                ))}
              </TextField>
            </CardContent>
          </Card>
        </Grid>

        {/* Box 3: Network */}
        <Grid item xs={12} md={4}>
          <Card elevation={selectedNetwork ? 1 : 3} sx={{ opacity: selectedOrg ? 1 : 0.5, transition: 'opacity 0.3s' }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>3. Select Network</Typography>
              <TextField select fullWidth label="Target Network" value={selectedNetwork} 
                onChange={(e) => setSelectedNetwork(e.target.value)}
                disabled={!selectedOrg}
              >
                {selectedOrg && cachedNetworks[selectedOrg] ? cachedNetworks[selectedOrg].map((net) => (
                  <MenuItem key={net.id} value={net.id}>{net.name}</MenuItem>
                )) : <MenuItem disabled>Select an Org first</MenuItem>}
              </TextField>
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* 3. EXECUTION VERIFICATION */}
      {isReadyToExecute && (
        <Paper elevation={4} sx={{ p: 3, mb: 4, bgcolor: 'background.paper', border: '1px solid #1976d2' }}>
          <Typography variant="h6" color="primary" gutterBottom>Verification</Typography>
          <Typography variant="body1">
            You are about to run <strong>{availableScripts.find(s => s.id === selectedScript)?.name}</strong> on <strong>{allNetworks.find(n => n.id === selectedNetwork)?.name}</strong>.
          </Typography>
          <Box sx={{ mt: 2, display: 'flex', gap: 2 }}>
            <Button variant="contained" color="success" size="large">
              Execute Script
            </Button>
            <Button variant="outlined" color="error" onClick={() => {
              setSelectedScript(''); setSelectedOrg(''); setSelectedNetwork(''); setSearchQuery(null);
            }}>
              Cancel / Reset
            </Button>
          </Box>
        </Paper>
      )}

      <Divider sx={{ my: 4 }} />

      {/* 4. HOTEL INFO & MAPBOX */}
      <Grid container spacing={3}>
        <Grid item xs={12} md={4}>
          <Card sx={{ height: '100%' }}>
            <CardContent>
              <Typography variant="h6" gutterBottom>Site Information</Typography>
              {selectedNetwork ? (
                <Box sx={{ mt: 2 }}>
                  <Typography variant="subtitle1" fontWeight="bold">Holiday Inn Express - {allNetworks.find(n => n.id === selectedNetwork)?.name.split(' - ')[0]}</Typography>
                  <Box sx={{ display: 'flex', alignItems: 'center', mt: 1, color: 'text.secondary' }}>
                    <LocationOn sx={{ mr: 1, fontSize: 20 }} />
                    <Typography variant="body2">1234 Placeholder Way, Atlanta GA</Typography>
                  </Box>
                  <Box sx={{ display: 'flex', alignItems: 'center', mt: 1, color: 'text.secondary' }}>
                    <Phone sx={{ mr: 1, fontSize: 20 }} />
                    <Typography variant="body2">(555) 123-4567</Typography>
                  </Box>
                </Box>
              ) : (
                <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
                  Select a network to view site details.
                </Typography>
              )}
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} md={8}>
          <Card sx={{ height: '300px', display: 'flex', alignItems: 'center', justifyContent: 'center', bgcolor: 'background.default' }}>
            <Box sx={{ textAlign: 'center', color: 'text.secondary' }}>
              <MapIcon sx={{ fontSize: 60, mb: 1, opacity: 0.5 }} />
              <Typography variant="h6">Mapbox Integration</Typography>
              <Typography variant="body2">Map will appear here when a network is selected.</Typography>
            </Box>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
};

export default Home;