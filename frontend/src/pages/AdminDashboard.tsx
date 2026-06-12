import React, { useEffect, useState } from 'react';
import {
  Box, Typography, Card, CardContent, Grid, Button, Chip,
  Table, TableBody, TableCell, TableHead, TableRow, TableContainer,
  Dialog, DialogTitle, DialogContent, DialogActions,
  TextField, Select, MenuItem, FormControl, InputLabel,
  Alert, CircularProgress, Tooltip, Switch,
} from '@mui/material';
import {
  PersonAdd, Refresh, AdminPanelSettings,
  People, LocalHospital, Person,
} from '@mui/icons-material';
import { useAuth } from '../contexts/AuthContext';
import { listUsers, registerUser, updateUser, deactivateUser } from '../api/client';
import type { UserOut } from '../types';

const roleColor: Record<string, 'error' | 'primary' | 'success'> = {
  admin: 'error',
  physician: 'primary',
  front_desk: 'success',
};

const AdminDashboard: React.FC = () => {
  const { user } = useAuth();
  const [users, setUsers] = useState<UserOut[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [addOpen, setAddOpen] = useState(false);
  const [saving, setSaving] = useState(false);

  const [form, setForm] = useState({
    email: '', password: '', full_name: '',
    role: 'front_desk', physician_id: '',
  });

  const load = async () => {
    setLoading(true);
    try {
      setUsers(await listUsers());
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const handleAdd = async () => {
    setSaving(true);
    try {
      await registerUser({
        ...form,
        physician_id: form.physician_id || undefined,
      });
      setAddOpen(false);
      setForm({ email: '', password: '', full_name: '', role: 'front_desk', physician_id: '' });
      await load();
    } catch (e: any) {
      setError(e.message);
    } finally {
      setSaving(false);
    }
  };

  const handleToggleActive = async (u: UserOut) => {
    try {
      if (u.is_active) {
        await deactivateUser(u.id);
      } else {
        await updateUser(u.id, { is_active: true });
      }
      await load();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const counts = {
    total: users.length,
    active: users.filter((u) => u.is_active).length,
    physicians: users.filter((u) => u.role === 'physician').length,
    front_desk: users.filter((u) => u.role === 'front_desk').length,
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Box>
          <Typography variant="h4" sx={{ fontWeight: 700 }}>Admin Dashboard</Typography>
          <Typography color="text.secondary">Manage users and system settings</Typography>
        </Box>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button startIcon={<Refresh />} onClick={load} variant="outlined">Refresh</Button>
          <Button startIcon={<PersonAdd />} onClick={() => setAddOpen(true)} variant="contained">
            Add User
          </Button>
        </Box>
      </Box>

      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>{error}</Alert>}

      {/* KPI Cards */}
      <Grid container spacing={2} sx={{ mb: 3 }}>
        {[
          { label: 'Total Users', value: counts.total, icon: <People />, color: '#1565c0' },
          { label: 'Active Users', value: counts.active, icon: <Person />, color: '#2e7d32' },
          { label: 'Physicians', value: counts.physicians, icon: <LocalHospital />, color: '#6a1b9a' },
          { label: 'Front Desk', value: counts.front_desk, icon: <AdminPanelSettings />, color: '#e65100' },
        ].map((card) => (
          <Grid size={{ xs: 6, sm: 3 }} key={card.label}>
            <Card sx={{ borderTop: `4px solid ${card.color}` }}>
              <CardContent sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <Box sx={{ color: card.color }}>{card.icon}</Box>
                <Box>
                  <Typography variant="h5" sx={{ fontWeight: 700 }}>{card.value}</Typography>
                  <Typography variant="body2" color="text.secondary">{card.label}</Typography>
                </Box>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Users Table */}
      <Card>
        <CardContent sx={{ p: 0 }}>
          {loading ? (
            <Box sx={{ display: 'flex', justifyContent: 'center', py: 6 }}>
              <CircularProgress />
            </Box>
          ) : (
            <TableContainer>
              <Table>
                <TableHead sx={{ bgcolor: 'grey.50' }}>
                  <TableRow>
                    <TableCell><strong>Name</strong></TableCell>
                    <TableCell><strong>Email</strong></TableCell>
                    <TableCell><strong>Role</strong></TableCell>
                    <TableCell><strong>Physician ID</strong></TableCell>
                    <TableCell><strong>Active</strong></TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {users.map((u) => (
                    <TableRow key={u.id} sx={{ opacity: u.is_active ? 1 : 0.5 }}>
                      <TableCell>{u.full_name}</TableCell>
                      <TableCell>{u.email}</TableCell>
                      <TableCell>
                        <Chip
                          label={u.role.replace('_', ' ')}
                          color={roleColor[u.role]}
                          size="small"
                        />
                      </TableCell>
                      <TableCell>{u.physician_id || '—'}</TableCell>
                      <TableCell>
                        <Tooltip title={u.id === user?.id ? 'Cannot deactivate yourself' : ''}>
                          <span>
                            <Switch
                              checked={u.is_active}
                              onChange={() => handleToggleActive(u)}
                              disabled={u.id === user?.id}
                              size="small"
                            />
                          </span>
                        </Tooltip>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          )}
        </CardContent>
      </Card>

      {/* Add User Dialog */}
      <Dialog open={addOpen} onClose={() => setAddOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Add New User</DialogTitle>
        <DialogContent sx={{ pt: 2, display: 'flex', flexDirection: 'column', gap: 2 }}>
          <TextField
            label="Full Name" fullWidth required
            value={form.full_name} onChange={(e) => setForm({ ...form, full_name: e.target.value })}
          />
          <TextField
            label="Email" type="email" fullWidth required
            value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })}
          />
          <TextField
            label="Password" type="password" fullWidth required
            value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })}
          />
          <FormControl fullWidth>
            <InputLabel>Role</InputLabel>
            <Select
              label="Role" value={form.role}
              onChange={(e) => setForm({ ...form, role: e.target.value })}
            >
              <MenuItem value="front_desk">Front Desk</MenuItem>
              <MenuItem value="physician">Physician</MenuItem>
              <MenuItem value="admin">Admin</MenuItem>
            </Select>
          </FormControl>
          {form.role === 'physician' && (
            <TextField
              label="Physician ID (e.g. D001)" fullWidth
              value={form.physician_id}
              onChange={(e) => setForm({ ...form, physician_id: e.target.value })}
              helperText="This ID links the physician to their appointments board"
            />
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAddOpen(false)}>Cancel</Button>
          <Button
            onClick={handleAdd} variant="contained" disabled={saving}
            startIcon={saving ? <CircularProgress size={16} /> : undefined}
          >
            Create User
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default AdminDashboard;
