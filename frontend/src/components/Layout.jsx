import React, { useContext } from 'react';
import { Outlet, useNavigate, useLocation } from 'react-router-dom';
import { 
  AppBar, Toolbar, Typography, Box, Drawer, List, ListItem, 
  ListItemButton, ListItemIcon, ListItemText, IconButton, Tooltip 
} from '@mui/material';
import { 
  PlayArrow, History, Settings, Logout, 
  LightMode, DarkMode, SettingsBrightness 
} from '@mui/icons-material';
import { AuthContext } from '../context/AuthContext.jsx';
import { ThemeContext } from '../context/ThemeContext.jsx';

const drawerWidth = 240;

const Layout = () => {
  const { logout } = useContext(AuthContext);
  const { themeMode, changeTheme } = useContext(ThemeContext);
  const navigate = useNavigate();
  const location = useLocation();

  const menuItems = [
    { text: 'Run Script', icon: <PlayArrow />, path: '/' },
    { text: 'Recent History', icon: <History />, path: '/history' },
    { text: 'Settings', icon: <Settings />, path: '/settings' },
  ];

  return (
    <Box sx={{ display: 'flex' }}>
      {/* TOP APP BAR */}
      <AppBar position="fixed" sx={{ zIndex: (theme) => theme.zIndex.drawer + 1 }}>
        <Toolbar>
          <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1 }}>
            Meraki Dashboard App
          </Typography>
          
          {/* THEME TOGGLE BUTTONS */}
          <Tooltip title="Light Mode">
            <IconButton color={themeMode === 'light' ? 'secondary' : 'inherit'} onClick={() => changeTheme('light')}>
              <LightMode />
            </IconButton>
          </Tooltip>
          <Tooltip title="Dark Mode">
            <IconButton color={themeMode === 'dark' ? 'secondary' : 'inherit'} onClick={() => changeTheme('dark')}>
              <DarkMode />
            </IconButton>
          </Tooltip>
          <Tooltip title="System Default">
            <IconButton color={themeMode === 'system' ? 'secondary' : 'inherit'} onClick={() => changeTheme('system')}>
              <SettingsBrightness />
            </IconButton>
          </Tooltip>

        </Toolbar>
      </AppBar>

      {/* SIDEBAR DRAWER */}
      <Drawer
        variant="permanent"
        sx={{
          width: drawerWidth,
          flexShrink: 0,
          [`& .MuiDrawer-paper`]: { width: drawerWidth, boxSizing: 'border-box' },
        }}
      >
        <Toolbar /> {/* Empty Toolbar to push list down below AppBar */}
        <Box sx={{ overflow: 'auto', display: 'flex', flexDirection: 'column', height: '100%' }}>
          <List>
            {menuItems.map((item) => (
              <ListItem key={item.text} disablePadding>
                <ListItemButton 
                  selected={location.pathname === item.path}
                  onClick={() => navigate(item.path)}
                >
                  <ListItemIcon>{item.icon}</ListItemIcon>
                  <ListItemText primary={item.text} />
                </ListItemButton>
              </ListItem>
            ))}
          </List>
          
          {/* LOGOUT AT THE BOTTOM */}
          <Box sx={{ flexGrow: 1 }} />
          <List>
            <ListItem disablePadding>
              <ListItemButton onClick={logout} sx={{ color: 'error.main' }}>
                <ListItemIcon sx={{ color: 'error.main' }}><Logout /></ListItemIcon>
                <ListItemText primary="Log Out" />
              </ListItemButton>
            </ListItem>
          </List>
        </Box>
      </Drawer>

      {/* MAIN CONTENT AREA */}
      <Box component="main" sx={{ flexGrow: 1, p: 3, mt: 8 }}>
        {/* React Router will render the specific page right here! */}
        <Outlet /> 
      </Box>
    </Box>
  );
};

export default Layout;