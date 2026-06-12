import React, { useState } from 'react';
import {
  Box, Card, CardContent, Typography, TextField, Button,
  Alert, CircularProgress, Grid, Chip, Table, TableBody,
  TableCell, TableContainer, TableHead, TableRow, Paper, Divider,
} from '@mui/material';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from 'recharts';
import { simulateDay } from '../api/client';
import type { SimulateDayRequest, SimulateDayResponse, AppointmentSlot } from '../types';

const SAMPLE_APPOINTMENTS: AppointmentSlot[] = [
  { appointment_id: 'A001', patient_id: 'P001', scheduled_start: '2026-06-12T09:00:00', predicted_duration: 25, no_show_probability: 0.1, visit_type: 'new', priority: 3 },
  { appointment_id: 'A002', patient_id: 'P002', scheduled_start: '2026-06-12T09:30:00', predicted_duration: 35, no_show_probability: 0.2, visit_type: 'follow-up', priority: 1 },
  { appointment_id: 'A003', patient_id: 'P003', scheduled_start: '2026-06-12T10:15:00', predicted_duration: 20, no_show_probability: 0.05, visit_type: 'follow-up', priority: 2 },
  { appointment_id: 'A004', patient_id: 'P004', scheduled_start: '2026-06-12T11:00:00', predicted_duration: 40, no_show_probability: 0.35, visit_type: 'new', priority: 2 },
  { appointment_id: 'A005', patient_id: 'P005', scheduled_start: '2026-06-12T13:00:00', predicted_duration: 30, no_show_probability: 0.15, visit_type: 'follow-up', priority: 1 },
];

const SimulateDay: React.FC = () => {
  const [physicianId, setPhysicianId] = useState('D001');
  const [date, setDate] = useState('2026-06-12');
  const [result, setResult] = useState<SimulateDayResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async () => {
    setLoading(true);
    setError('');
    setResult(null);
    const body: SimulateDayRequest = {
      physician_id: physicianId,
      date,
      appointments: SAMPLE_APPOINTMENTS.map((a) => ({
        ...a,
        scheduled_start: a.scheduled_start.replace('2026-06-12', date),
      })),
      constraints: { buffer_minutes: 5, work_end_hour: 17, lunch_start_hour: 12, lunch_duration_minutes: 60 },
    };
    try {
      setResult(await simulateDay(body));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  const chartData = result?.simulated_appointments.map((a) => ({
    id: a.appointment_id,
    delay: a.delay_minutes,
    risk: a.is_at_risk,
  })) ?? [];

  return (
    <Box>
      <Typography variant="h4" gutterBottom>Daily Schedule Simulation</Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        Simulate delay propagation across a physician's full day. Identifies at-risk
        appointments (&gt;15 min delay) and generates recommendations.
      </Typography>

      {/* Controls */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Grid container spacing={2} sx={{ alignItems: 'center' }}>
            <Grid size={{ xs: 12, sm: 4 }}>
              <TextField label="Physician ID" value={physicianId} onChange={(e) => setPhysicianId(e.target.value)} fullWidth size="small" />
            </Grid>
            <Grid size={{ xs: 12, sm: 4 }}>
              <TextField label="Date" type="date" value={date} onChange={(e) => setDate(e.target.value)} fullWidth size="small" slotProps={{ inputLabel: { shrink: true } }} />
            </Grid>
            <Grid size={{ xs: 12, sm: 4 }}>
              <Button variant="contained" fullWidth onClick={handleSubmit} disabled={loading} size="large" color="secondary">
                {loading ? <CircularProgress size={20} color="inherit" /> : 'Run Simulation'}
              </Button>
            </Grid>
          </Grid>
          <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
            Using {SAMPLE_APPOINTMENTS.length} sample appointments. Integration with live schedule data coming soon.
          </Typography>
        </CardContent>
      </Card>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {result && (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
          {/* KPI row */}
          <Grid container spacing={2}>
            {[
              { label: 'Total Waiting Time', value: `${result.total_waiting_time_minutes} min`, color: '#1976d2' },
              { label: 'Max Delay', value: `${result.max_delay_minutes} min`, color: result.max_delay_minutes > 15 ? '#d32f2f' : '#2e7d32' },
              { label: 'Schedule Overrun', value: `${result.schedule_overrun_minutes} min`, color: result.schedule_overrun_minutes > 0 ? '#ed6c02' : '#2e7d32' },
              { label: 'Physician Idle', value: `${result.physician_idle_time_minutes} min`, color: '#7b1fa2' },
              { label: 'At-Risk Appointments', value: result.at_risk_count, color: result.at_risk_count > 0 ? '#d32f2f' : '#2e7d32' },
            ].map((kpi) => (
              <Grid key={kpi.label} size={{ xs: 6, sm: 4, md: 2.4 }}>
                <Card>
                  <CardContent sx={{ textAlign: 'center', py: 1.5 }}>
                    <Typography variant="h5" sx={{ fontWeight: 700, color: kpi.color }}>
                      {kpi.value}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">{kpi.label}</Typography>
                  </CardContent>
                </Card>
              </Grid>
            ))}
          </Grid>

          {/* Delay chart */}
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Delay by Appointment</Typography>
              <Box sx={{ height: 220 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={chartData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="id" tick={{ fontSize: 12 }} />
                    <YAxis unit=" min" tick={{ fontSize: 12 }} />
                    <Tooltip formatter={(v) => v !== undefined ? [`${v} min`, 'Delay'] : ['', '']} />
                    <Bar dataKey="delay" radius={[4, 4, 0, 0]}>
                      {chartData.map((entry, i) => (
                        <Cell key={i} fill={entry.risk ? '#d32f2f' : '#1976d2'} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </Box>
              <Box sx={{ display: 'flex', gap: 1, mt: 1 }}>
                <Chip size="small" label="Normal" sx={{ bgcolor: '#1976d2', color: 'white' }} />
                <Chip size="small" label="At Risk (>15 min)" sx={{ bgcolor: '#d32f2f', color: 'white' }} />
              </Box>
            </CardContent>
          </Card>

          {/* Appointments table */}
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Simulated Timeline</Typography>
              <TableContainer component={Paper} elevation={0} sx={{ border: '1px solid', borderColor: 'divider' }}>
                <Table size="small">
                  <TableHead>
                    <TableRow sx={{ bgcolor: 'primary.main' }}>
                      {['ID', 'Patient', 'Scheduled', 'Predicted Start', 'End', 'Delay', 'Status'].map((h) => (
                        <TableCell key={h} sx={{ color: 'white', fontWeight: 700 }}>{h}</TableCell>
                      ))}
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {result.simulated_appointments.map((a) => (
                      <TableRow key={a.appointment_id} sx={{ bgcolor: a.is_at_risk ? '#fff3e0' : 'inherit' }}>
                        <TableCell>{a.appointment_id}</TableCell>
                        <TableCell>{a.patient_id}</TableCell>
                        <TableCell>{new Date(a.scheduled_start).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</TableCell>
                        <TableCell>{new Date(a.predicted_start).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</TableCell>
                        <TableCell>{new Date(a.predicted_end).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</TableCell>
                        <TableCell>
                          <Chip
                            label={`${a.delay_minutes} min`}
                            size="small"
                            color={a.delay_minutes === 0 ? 'success' : a.is_at_risk ? 'error' : 'warning'}
                          />
                        </TableCell>
                        <TableCell>
                          {a.is_at_risk
                            ? <Chip label="⚠ At Risk" color="error" size="small" />
                            : <Chip label="✓ On Track" color="success" size="small" />}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>

          {/* Recommendations */}
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Recommendations</Typography>
              <Divider sx={{ mb: 1.5 }} />
              {result.recommendations.map((rec, i) => (
                <Alert key={i} severity={rec.includes('risk') || rec.includes('overrun') ? 'warning' : 'info'} sx={{ mb: 1 }}>
                  {rec}
                </Alert>
              ))}
            </CardContent>
          </Card>
        </Box>
      )}

      {!result && !loading && !error && (
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 200, border: '2px dashed', borderColor: 'divider', borderRadius: 3 }}>
          <Typography color="text.secondary">Configure and click Run Simulation</Typography>
        </Box>
      )}
    </Box>
  );
};

export default SimulateDay;
