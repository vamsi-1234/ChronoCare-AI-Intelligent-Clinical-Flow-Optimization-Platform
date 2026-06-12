import React, { useState } from 'react';
import {
  Box, Drawer, AppBar, Toolbar, Typography, List, ListItem,
  ListItemButton, ListItemIcon, ListItemText, Divider, useTheme,
  useMediaQuery, IconButton, Avatar, Chip, Tooltip,
} from '@mui/material';
import { useLocation, useNavigate } from 'react-router-dom';
import DashboardIcon from '@mui/icons-material/Dashboard';
import TimerIcon from '@mui/icons-material/Timer';
import PersonOffIcon from '@mui/icons-material/PersonOff';
import CalendarMonthIcon from '@mui/icons-material/CalendarMonth';
import AutoFixHighIcon from '@mui/icons-material/AutoFixHigh';
import EventNoteIcon from '@mui/icons-material/EventNote';
import MenuIcon from '@mui/icons-material/Menu';
import LocalHospitalIcon from '@mui/icons-material/LocalHospital';
import AdminPanelSettingsIcon from '@mui/icons-material/AdminPanelSettings';
import LogoutIcon from '@mui/icons-material/Logout';
import SystemStatus from './SystemStatus';
import { useAuth } from '../contexts/AuthContext';

const DRAWER_WIDTH = 240;

const ALL_NAV_ITEMS = [
  { label: 'Dashboard',         path: '/',                 icon: <DashboardIcon />,            roles: ['admin','physician','front_desk'] },
  { label: 'Daily Board',       path: '/appointments',     icon: <EventNoteIcon />,            roles: ['admin','physician','front_desk'] },
  { label: 'Predict Duration',  path: '/predict-duration', icon: <TimerIcon />,                roles: ['admin','physician','front_desk'] },
  { label: 'No-Show Risk',      path: '/predict-noshow',   icon: <PersonOffIcon />,            roles: ['admin','physician','front_desk'] },
  { label: 'Simulate Day',      path: '/simulate-day',     icon: <CalendarMonthIcon />,        roles: ['admin','physician','front_desk'] },
  { label: 'Optimize Schedule', path: '/optimize',         icon: <AutoFixHighIcon />,          roles: ['admin','physician','front_desk'] },
  { label: 'Admin',             path: '/admin',            icon: <AdminPanelSettingsIcon />,   roles: ['admin'] },
];

const roleColor: Record<string, 'error' | 'primary' | 'success'> = {
  admin: 'error', physician: 'primary', front_desk: 'success',
};

const Layout: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));
  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  const navItems = ALL_NAV_ITEMS.filter(
    (item) => !user || item.roles.includes(user.role)
  );

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const drawer = (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Box sx={{ p: 2, display: 'flex', alignItems: 'center', gap: 1 }}>
        <LocalHospitalIcon color="primary" sx={{ fontSize: 28 }} />
        <Box>
          <Typography variant="h6" sx={{ lineHeight: 1.2, fontWeight: 700, color: 'primary.main' }}>
            ChronoCare
          </Typography>
          <Typography variant="caption" color="text.secondary">
            AI Scheduling Platform
          </Typography>
        </Box>
      </Box>
      <Divider />
      <List sx={{ flex: 1, pt: 1 }}>
        {navItems.map((item) => {
          const active = location.pathname === item.path;
          return (
            <ListItem key={item.path} disablePadding>
              <ListItemButton
                selected={active}
                onClick={() => { navigate(item.path); setMobileOpen(false); }}
                sx={{
                  mx: 1, borderRadius: 2, mb: 0.5,
                  '&.Mui-selected': {
                    bgcolor: 'primary.main',
                    color: 'white',
                    '& .MuiListItemIcon-root': { color: 'white' },
                    '&:hover': { bgcolor: 'primary.dark' },
                  },
                }}
              >
                <ListItemIcon sx={{ minWidth: 36 }}>{item.icon}</ListItemIcon>
                <ListItemText primary={item.label} slotProps={{ primary: { style: { fontSize: 14 } } }} />
              </ListItemButton>
            </ListItem>
          );
        })}
      </List>
      <Divider />
      {/* User info + logout */}
      {user && (
        <Box sx={{ p: 1.5 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
            <Avatar sx={{ width: 32, height: 32, bgcolor: 'primary.main', fontSize: 14 }}>
              {user.full_name.charAt(0).toUpperCase()}
            </Avatar>
            <Box sx={{ flex: 1, minWidth: 0 }}>
              <Typography variant="body2" noWrap sx={{ fontWeight: 600 }}>{user.full_name}</Typography>
              <Chip label={user.role.replace('_', ' ')} color={roleColor[user.role]} size="small" sx={{ height: 18, fontSize: 10 }} />
            </Box>
            <Tooltip title="Sign out">
              <IconButton size="small" onClick={handleLogout}><LogoutIcon fontSize="small" /></IconButton>
            </Tooltip>
          </Box>
        </Box>
      )}
      <Divider />
      <Box sx={{ p: 1.5 }}>
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
          System Status
        </Typography>
        <SystemStatus />
      </Box>
    </Box>
  );

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh', bgcolor: 'background.default' }}>
      {isMobile && (
        <AppBar position="fixed" elevation={1} sx={{ zIndex: theme.zIndex.drawer + 1 }}>
          <Toolbar>
            <IconButton color="inherit" onClick={() => setMobileOpen(!mobileOpen)} edge="start" sx={{ mr: 1 }}>
              <MenuIcon />
            </IconButton>
            <LocalHospitalIcon sx={{ mr: 1 }} />
            <Typography variant="h6" sx={{ fontWeight: 700 }}>ChronoCare AI</Typography>
          </Toolbar>
        </AppBar>
      )}

      {isMobile ? (
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={() => setMobileOpen(false)}
          sx={{ '& .MuiDrawer-paper': { width: DRAWER_WIDTH } }}
        >
          {drawer}
        </Drawer>
      ) : (
        <Drawer
          variant="permanent"
          sx={{
            width: DRAWER_WIDTH,
            flexShrink: 0,
            '& .MuiDrawer-paper': { width: DRAWER_WIDTH, boxSizing: 'border-box', border: 'none', boxShadow: '2px 0 8px rgba(0,0,0,0.06)' },
          }}
        >
          {drawer}
        </Drawer>
      )}

      <Box
        component="main"
        sx={{ flex: 1, p: { xs: 2, md: 3 }, pt: isMobile ? '80px' : 3, maxWidth: '100%', overflow: 'auto' }}
      >
        {children}
      </Box>
    </Box>
  );
};

export default Layout;
