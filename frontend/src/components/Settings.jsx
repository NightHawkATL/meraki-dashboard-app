import React, { useState, useContext, useEffect } from 'react';
import { 
  Box, Tabs, Tab, Typography, Paper, TextField, Button, Grid, 
  List, ListItem, ListItemButton, ListItemText, Badge, Divider, InputAdornment, Alert, CircularProgress
} from '@mui/material';
import { Search, Sync, Save, VpnKey, Security } from '@mui/icons-material';
import { AuthContext } from '../context/AuthContext.jsx'; // <--- We need the token!

function TabPanel(props) {
  const { children, value, index, ...other } = props;
  return (
    <div role="tabpanel" hidden={value !== index} {...other}>
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

const Settings = () => {
  const { token } = useContext(AuthContext);
  const [activeTab, setActiveTab] = useState(0);
  const [apiKey, setApiKey] = useState('');
  
  // Real Data State
  const [cachedOrgs, setCachedOrgs] = useState([]);
  const [cachedNetworks, setCachedNetworks] = useState({});
  const [selectedOrg, setSelectedOrg] = useState(null);
  const [networkSearch, setNetworkSearch] = useState('');
  
  // Status State
  const [statusMessage, setStatusMessage] = useState(null);
  const [statusType, setStatusType] = useState('info'); // 'success', 'error', 'info'
  const [isSyncing, setIsSyncing] = useState(false);

  // 1. Fetch the cached data from PostgreSQL when the page loads
  const fetchCache = async () => {
    try {
      const response = await fetch('/api/meraki/cache', {
        headers: { 'Authorization': `Bearer ${token}` }
      });
      if (response.ok) {
        const data = await response.json();
        setCachedOrgs(data.orgs);
        setCachedNetworks(data.networks);
      }
    } catch (err) {
      console.error("Failed to fetch cache:", err);
    }
  };

  useEffect(() => {
    fetchCache();
  }, []); // Run once on mount

  // 2. Save the API Key
  const handleSaveApiKey = async () => {
    setStatusMessage(null);
    try {
      const response = await fetch('/api/meraki/key', {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}` 
        },
        body: JSON.stringify({ api_key: apiKey }),
      });
      
      const data = await response.json();
      if (response.ok) {
        setStatusType('success');
        setStatusMessage('API Key securely encrypted and saved!');
        setApiKey(''); // Clear the box for security
      } else {
        setStatusType('error');
        setStatusMessage(data.detail || 'Failed to save key.');
      }
    } catch (err) {
      setStatusType('error');
      setStatusMessage('Cannot connect to the server.');
    }
  };

  // 3. Sync with Meraki Cloud
  const handleSyncMeraki = async () => {
    setStatusMessage(null);
    setIsSyncing(true);
    setStatusType('info');
    setStatusMessage('Syncing with Meraki... This may take up to 30 seconds.');
    
    try {
      const response = await fetch('/api/meraki/sync', {
        method: 'POST',
        headers: { 'Authorization': `Bearer ${token}` }
      });
      
      const data = await response.json();
      if (response.ok) {
        setStatusType('success');
        setStatusMessage(data.message);
        fetchCache(); // Refresh the lists!
      } else {
        setStatusType('error');
        setStatusMessage(data.detail || 'Sync failed.');
      }
    } catch (err) {
      setStatusType('error');
      setStatusMessage('Cannot connect to the server.');
    } finally {
      setIsSyncing(false);
    }
  };

  return (
    <Box sx={{ maxWidth: 1200, mx: 'auto' }}>
      <Typography variant="h4" gutterBottom>Settings</Typography>
      
      <Paper elevation={3} sx={{ mt: 3 }}>
        <Tabs value={activeTab} onChange={(e, val) => setActiveTab(val)} borderBottom={1} borderColor="divider">
          <Tab label="Profile & Security" />
          <Tab label="Meraki Integration" />
          <Tab label="System (Admin)" />
          <Tab label="Policies (Admin)" />
        </Tabs>

        {/* TAB 1: Profile & Security (Placeholder for now) */}
        <TabPanel value={activeTab} index={0}>
          <Typography variant="h6">Change Password</Typography>
          <Typography variant="body2" color="text.secondary">Password management coming soon.</Typography>
        </TabPanel>

        {/* TAB 2: Meraki Integration */}
        <TabPanel value={activeTab} index={1}>
          <Typography variant="h6" gutterBottom>Meraki API Key</Typography>
          <Typography variant="body2" color="text.secondary" paragraph>
            Your API key is AES-encrypted at rest. It is only decrypted in server memory during script execution.
          </Typography>
          
          {statusMessage && (
            <Alert severity={statusType} sx={{ mb: 3 }}>{statusMessage}</Alert>
          )}

          <Box sx={{ display: 'flex', gap: 2, mb: 4 }}>
            <TextField 
              fullWidth type="password" label="Cisco Meraki API Key" 
              value={apiKey} onChange={(e) => setApiKey(e.target.value)}
              InputProps={{ startAdornment: <InputAdornment position="start"><VpnKey /></InputAdornment> }}
            />
            <Button variant="contained" color="primary" onClick={handleSaveApiKey} startIcon={<Save />} sx={{ px: 4 }}>
              Save Key
            </Button>
            <Button 
              variant="outlined" color="secondary" 
              onClick={handleSyncMeraki} 
              disabled={isSyncing}
              startIcon={isSyncing ? <CircularProgress size={20} /> : <Sync />} 
              sx={{ px: 4 }}
            >
              Verify & Sync
            </Button>
          </Box>

          <Divider sx={{ my: 4 }} />

          <Typography variant="h6" gutterBottom>Cached Meraki Data</Typography>
          <TextField 
            fullWidth placeholder="Search networks..." 
            value={networkSearch} onChange={(e) => setNetworkSearch(e.target.value)} sx={{ mb: 2 }}
            InputProps={{ startAdornment: <InputAdornment position="start"><Search /></InputAdornment> }}
          />

          <Grid container spacing={3}>
            {/* LEFT BOX: Organizations */}
            <Grid item xs={12} md={6}>
              <Paper variant="outlined" sx={{ height: 400, overflow: 'auto' }}>
                <List dense>
                  {cachedOrgs.length > 0 ? cachedOrgs.map((org) => (
                    <ListItem key={org.id} disablePadding>
                      <ListItemButton selected={selectedOrg === org.id} onClick={() => setSelectedOrg(org.id)}>
                        <ListItemText primary={org.name} secondary={`ID: ${org.id}`} />
                        <Badge badgeContent={org.netCount} color="primary" sx={{ mr: 2 }} />
                      </ListItemButton>
                    </ListItem>
                  )) : (
                    <Box sx={{ p: 3, textAlign: 'center', color: 'text.secondary' }}>
                      <Typography>No Orgs Found. Save an API key and click Sync.</Typography>
                    </Box>
                  )}
                </List>
              </Paper>
            </Grid>

            {/* RIGHT BOX: Networks */}
            <Grid item xs={12} md={6}>
              <Paper variant="outlined" sx={{ height: 400, overflow: 'auto' }}>
                <List dense>
                  {selectedOrg && cachedNetworks[selectedOrg] ? (
                    cachedNetworks[selectedOrg]
                      .filter(net => net.name.toLowerCase().includes(networkSearch.toLowerCase()))
                      .map((net) => (
                      <ListItem key={net.id}>
                        <ListItemText primary={net.name} secondary={`ID: ${net.id}`} />
                      </ListItem>
                    ))
                  ) : (
                    <Box sx={{ p: 3, textAlign: 'center', color: 'text.secondary' }}>
                      <Typography>Select an Organization to view its Networks.</Typography>
                    </Box>
                  )}
                </List>
              </Paper>
            </Grid>
          </Grid>
        </TabPanel>

        {/* TAB 3 & 4 */}
        <TabPanel value={activeTab} index={2}><Typography>System Settings coming soon.</Typography></TabPanel>
        <TabPanel value={activeTab} index={3}><Typography>Policies coming soon.</Typography></TabPanel>
      </Paper>
    </Box>
  );
};

export default Settings;