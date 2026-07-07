import React, { useState } from 'react';
import { 
  Box, Tabs, Tab, Typography, Paper, TextField, Button, Grid, 
  List, ListItem, ListItemButton, ListItemText, Badge, Divider, InputAdornment
} from '@mui/material';
import { Search, Sync, Save, VpnKey, Security } from '@mui/icons-material';

// --- MOCK DATA (To show the layout before we attach the backend) ---
const mockOrgs = [
  { id: '123', name: 'IHG Corporate', netCount: 45 },
  { id: '456', name: 'Test Lab Org', netCount: 3 }
];

const mockNetworks = {
  '123': [{ id: 'n1', name: 'ATLAA - Main Network' }, { id: 'n2', name: 'NYCBB - Guest Network' }],
  '456': [{ id: 'n3', name: 'Lab Router 1' }]
};
// ------------------------------------------------------------------

// A standard helper component for MUI Tabs
function TabPanel(props) {
  const { children, value, index, ...other } = props;
  return (
    <div role="tabpanel" hidden={value !== index} {...other}>
      {value === index && <Box sx={{ p: 3 }}>{children}</Box>}
    </div>
  );
}

const Settings = () => {
  const [activeTab, setActiveTab] = useState(0);
  const [apiKey, setApiKey] = useState('');
  const [selectedOrg, setSelectedOrg] = useState(null);
  const [networkSearch, setNetworkSearch] = useState('');

  const handleTabChange = (event, newValue) => {
    setActiveTab(newValue);
  };

  const handleSaveApiKey = () => {
    // We will wire this to FastAPI next!
    console.log("Saving encrypted key to DB...");
  };

  const handleSyncMeraki = () => {
    // We will wire this to the Meraki Python SDK next!
    console.log("Syncing Orgs and Networks...");
  };

  return (
    <Box sx={{ maxWidth: 1200, mx: 'auto' }}>
      <Typography variant="h4" gutterBottom>Settings</Typography>
      
      <Paper elevation={3} sx={{ mt: 3 }}>
        <Tabs value={activeTab} onChange={handleTabChange} borderBottom={1} borderColor="divider">
          <Tab label="Profile & Security" />
          <Tab label="Meraki Integration" />
          <Tab label="System (Admin)" />
          <Tab label="Policies (Admin)" />
        </Tabs>

        {/* TAB 1: Profile & Security */}
        <TabPanel value={activeTab} index={0}>
          <Typography variant="h6" gutterBottom>Change Password</Typography>
          <Grid container spacing={3}>
            <Grid item xs={12} md={6}>
              <TextField fullWidth type="password" label="New Password" variant="outlined" margin="normal" />
              <TextField fullWidth type="password" label="Confirm Password" variant="outlined" margin="normal" />
              {/* Placeholder for the Password Strength Bar */}
              <Box sx={{ height: 8, bgcolor: 'grey.300', borderRadius: 4, mt: 1, mb: 2 }}>
                 <Box sx={{ height: '100%', width: '0%', bgcolor: 'success.main', borderRadius: 4 }} />
              </Box>
              <Button variant="contained" color="primary">Update Password</Button>
              <Button variant="outlined" color="inherit" sx={{ ml: 2 }}>Generate Secure Password</Button>
            </Grid>
          </Grid>
          
          <Divider sx={{ my: 4 }} />
          
          <Typography variant="h6" gutterBottom>Two-Factor Authentication</Typography>
          <Button variant="contained" color="secondary" startIcon={<Security />}>
            Setup 2FA (Google Authenticator)
          </Button>
        </TabPanel>

        {/* TAB 2: Meraki Integration */}
        <TabPanel value={activeTab} index={1}>
          <Typography variant="h6" gutterBottom>Meraki API Key</Typography>
          <Typography variant="body2" color="text.secondary" paragraph>
            Your API key is AES-encrypted at rest. It is only decrypted in server memory during script execution.
          </Typography>
          
          <Box sx={{ display: 'flex', gap: 2, mb: 4 }}>
            <TextField 
              fullWidth 
              type="password" 
              label="Cisco Meraki API Key" 
              value={apiKey} 
              onChange={(e) => setApiKey(e.target.value)}
              InputProps={{ startAdornment: <InputAdornment position="start"><VpnKey /></InputAdornment> }}
            />
            <Button variant="contained" color="primary" onClick={handleSaveApiKey} startIcon={<Save />} sx={{ px: 4 }}>
              Save Key
            </Button>
            <Button variant="outlined" color="secondary" onClick={handleSyncMeraki} startIcon={<Sync />} sx={{ px: 4 }}>
              Verify & Sync
            </Button>
          </Box>

          <Divider sx={{ my: 4 }} />

          <Typography variant="h6" gutterBottom>Cached Meraki Data</Typography>
          <TextField 
            fullWidth 
            placeholder="Search networks..." 
            value={networkSearch}
            onChange={(e) => setNetworkSearch(e.target.value)}
            sx={{ mb: 2 }}
            InputProps={{ startAdornment: <InputAdornment position="start"><Search /></InputAdornment> }}
          />

          <Grid container spacing={3}>
            {/* LEFT BOX: Organizations */}
            <Grid item xs={12} md={6}>
              <Paper variant="outlined" sx={{ height: 400, overflow: 'auto' }}>
                <List dense>
                  {mockOrgs.map((org) => (
                    <ListItem key={org.id} disablePadding>
                      <ListItemButton 
                        selected={selectedOrg === org.id} 
                        onClick={() => setSelectedOrg(org.id)}
                      >
                        <ListItemText primary={org.name} secondary={`ID: ${org.id}`} />
                        <Badge badgeContent={org.netCount} color="primary" sx={{ mr: 2 }} />
                      </ListItemButton>
                    </ListItem>
                  ))}
                </List>
              </Paper>
            </Grid>

            {/* RIGHT BOX: Networks */}
            <Grid item xs={12} md={6}>
              <Paper variant="outlined" sx={{ height: 400, overflow: 'auto' }}>
                <List dense>
                  {selectedOrg ? (
                    mockNetworks[selectedOrg]
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

        {/* TAB 3 & 4: Placeholders for now */}
        <TabPanel value={activeTab} index={2}><Typography>Mapbox and Google Places API keys will go here.</Typography></TabPanel>
        <TabPanel value={activeTab} index={3}><Typography>Password complexity rules and User Management table will go here.</Typography></TabPanel>

      </Paper>
    </Box>
  );
};

export default Settings;