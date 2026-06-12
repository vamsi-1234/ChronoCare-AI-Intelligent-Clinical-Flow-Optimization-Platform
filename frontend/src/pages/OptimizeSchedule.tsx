import React, { useState } from 'react';
import {
  Box, Card, CardContent, Typography, TextField, Button,
  Alert, CircularProgress, Grid, Chip, Table, TableBody,
  TableCell, TableContainer, TableHead, TableRow, Paper,
  LinearProgress,
} from '@mui/material';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  Legend,
} from 'recharts';
import { optimizeSchedule } from '../api/client';
import type { OptimizeScheduleRequest, OptimizeScheduleResponse, AppointmentSlot } from '../types';

const SAMPLE_APPOINTMENTS: AppointmentSlot[] = [
  { appointment_id: 'A001', patient_id: 'P001', scheduled_start: '2026-06-12T08:00:00', predicted_duration: 30, no_show_probability: 0.4, visit_type: 'follow-up', priority: 1 },
  { appointment_id: 'A002', patient_id: 'P002', scheduled_start: '2026-06-12T08:30:00', predicted_duration: 20, no_show_probability: 0.1, visit_type: 'new', priority: 3 },
  { appointment_id: 'A003', patient_id: 'P003', scheduled_start: '2026-06-12T09:00:00', predicted_duration: 40, no_show_probability: 0.6, visit_type: 'follow-up', priority: 1 },
  { appointment_id: 'A004', patient_id: 'P004', scheduled_start: '2026-06-12T10:00:00', predicted_duration: 25, no_show_probability: 0.05, visit_type: 'new', priority: 4 },
  { appointment_id: 'A005', patient_id: 'P005', scheduled_start: '2026-06-12T11:00:00', predicted_duration: 35, no_show_probability: 0.2, visit_type: 'follow-up', priority: 2 },
];

const OptimizeSchedule: React.FC = () => {
  const [physicianId, setPhysicianId] = useState('D001');
  const [date, setDate] = useState('2026-06-12');
  const [alpha, setAlpha] = useState(0.5);
  const [beta, setBeta] = useState(0.3);
  const [gamma, setGamma] = useState(0.2);
  const [result, setResult] = useState<OptimizeScheduleResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async () => {
    setLoading(true);
    setError('');
    setResult(null);
    const body: OptimizeScheduleRequest = {
      physician_id: physicianId,
      date,
      appointments: SAMPLE_APPOINTMENTS.map((a) => ({
        ...a,
        scheduled_start: a.scheduled_start.replace('2026-06-12', date),
      })),
      alpha,
      beta,
      gamma,
    };
    try {
      setResult(await optimizeSchedule(body));
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  // Comparison chart: original vs optimized start times (as minutes since midnight)
  const comparisonData = result?.optimized_appointments.map((a) => {
    const toMin = (s: string) => {
      const d = new Date(s);
      return d.getHours() * 60 + d.getMinutes();
    };
    return {
      id: a.appointment_id,
      original: toMin(a.original_start),
      optimized: toMin(a.optimized_start),
      duration: a.predicted_duration,
    };
  }) ?? [];

  return (
    <Box>
      <Typography variant="h4" gutterBottom>Schedule Optimization</Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        Reorder appointments to minimize total patient waiting time, workload variance,
        and schedule overrun. Configurable objective weights below.
      </Typography>

      {/* Controls */}
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Typography variant="h6" gutterBottom>Optimization Parameters</Typography>
          <Grid container spacing={2} sx={{ alignItems: 'center' }}>
            <Grid size={{ xs: 12, sm: 3 }}>
              <TextField label="Physician ID" value={physicianId} onChange={(e) => setPhysicianId(e.target.value)} fullWidth size="small" />
            </Grid>
            <Grid size={{ xs: 12, sm: 3 }}>
              <TextField label="Date" type="date" value={date} onChange={(e) => setDate(e.target.value)} fullWidth size="small" slotProps={{ inputLabel: { shrink: true } }} />
            </Grid>
            <Grid size={{ xs: 12, sm: 2 }}>
              <TextField
                label="α Waiting Time"
                type="number"
                value={alpha}
                onChange={(e) => setAlpha(Number(e.target.value))}
                fullWidth size="small"
                slotProps={{ htmlInput: { min: 0, max: 1, step: 0.1 } }}
                helperText="Weight 0-1"
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 2 }}>
              <TextField
                label="β Workload Var"
                type="number"
                value={beta}
                onChange={(e) => setBeta(Number(e.target.value))}
                fullWidth size="small"
                slotProps={{ htmlInput: { min: 0, max: 1, step: 0.1 } }}
                helperText="Weight 0-1"
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 2 }}>
              <TextField
                label="γ Overrun"
                type="number"
                value={gamma}
                onChange={(e) => setGamma(Number(e.target.value))}
                fullWidth size="small"
                slotProps={{ htmlInput: { min: 0, max: 1, step: 0.1 } }}
                helperText="Weight 0-1"
              />
            </Grid>
            <Grid size={12}>
              <Button variant="contained" onClick={handleSubmit} disabled={loading} size="large" color="success" fullWidth>
                {loading ? <CircularProgress size={20} color="inherit" /> : '✨ Optimize Schedule'}
              </Button>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

      {result && (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
          {/* KPIs */}
          <Grid container spacing={2}>
            {[
              { label: 'Expected Waiting Time', value: `${result.expected_total_waiting_time} min`, color: '#1976d2' },
              { label: 'Expected Overrun', value: `${result.expected_overrun_minutes} min`, color: result.expected_overrun_minutes > 0 ? '#ed6c02' : '#2e7d32' },
              { label: 'Improvement vs Naive', value: `${result.improvement_pct}%`, color: result.improvement_pct > 0 ? '#2e7d32' : '#d32f2f' },
              { label: 'Schedule Status', value: result.is_optimal ? 'Optimal' : 'Suboptimal', color: result.is_optimal ? '#2e7d32' : '#ed6c02' },
            ].map((kpi) => (
              <Grid key={kpi.label} size={{ xs: 6, md: 3 }}>
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

          {/* Improvement meter */}
          {result.improvement_pct > 0 && (
            <Card>
              <CardContent>
                <Typography variant="body2" gutterBottom>
                  Waiting time improvement over naive scheduling
                </Typography>
                <LinearProgress
                  variant="determinate"
                  value={Math.min(100, result.improvement_pct)}
                  sx={{ height: 12, borderRadius: 6, mb: 0.5 }}
                  color="success"
                />
                <Typography variant="caption" color="success.main" sx={{ fontWeight: 600 }}>
                  {result.improvement_pct}% reduction
                </Typography>
              </CardContent>
            </Card>
          )}

          {/* NL summary */}
          <Alert severity="success" icon={false}>
            <Typography variant="body2">{result.nl_summary}</Typography>
          </Alert>

          {/* Before/After chart */}
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Start Time Comparison (minutes since midnight)</Typography>
              <Box sx={{ height: 220 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={comparisonData} margin={{ top: 5, right: 20, left: 0, bottom: 5 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} />
                    <XAxis dataKey="id" tick={{ fontSize: 12 }} />
                    <YAxis tick={{ fontSize: 12 }} domain={[440, 'auto']} unit="m" />
                    <Tooltip formatter={(v) => {
                      if (v === undefined || v === null) return ['', ''];
                      const num = Number(v);
                      const h = Math.floor(num / 60);
                      const m = num % 60;
                      return [`${h}:${String(m).padStart(2, '0')}`, ''];
                    }} />
                    <Legend />
                    <Bar dataKey="original" name="Original Start" fill="#90caf9" radius={[4, 4, 0, 0]} />
                    <Bar dataKey="optimized" name="Optimized Start" fill="#1976d2" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </Box>
            </CardContent>
          </Card>

          {/* Optimized schedule table */}
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Optimized Schedule</Typography>
              <TableContainer component={Paper} elevation={0} sx={{ border: '1px solid', borderColor: 'divider' }}>
                <Table size="small">
                  <TableHead>
                    <TableRow sx={{ bgcolor: 'success.main' }}>
                      {['#', 'Appt ID', 'Patient', 'Original Start', 'Optimized Start', 'Duration', 'Change'].map((h) => (
                        <TableCell key={h} sx={{ color: 'white', fontWeight: 700 }}>{h}</TableCell>
                      ))}
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {result.optimized_appointments.map((a, i) => {
                      const origD = new Date(a.original_start);
                      const optD = new Date(a.optimized_start);
                      const diffMin = Math.round((optD.getTime() - origD.getTime()) / 60000);
                      return (
                        <TableRow key={a.appointment_id}>
                          <TableCell>{i + 1}</TableCell>
                          <TableCell>{a.appointment_id}</TableCell>
                          <TableCell>{a.patient_id}</TableCell>
                          <TableCell>{origD.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</TableCell>
                          <TableCell><strong>{optD.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</strong></TableCell>
                          <TableCell>{a.predicted_duration} min</TableCell>
                          <TableCell>
                            <Chip
                              label={diffMin === 0 ? 'No change' : `${diffMin > 0 ? '+' : ''}${diffMin} min`}
                              size="small"
                              color={diffMin === 0 ? 'default' : diffMin < 0 ? 'success' : 'warning'}
                            />
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </TableBody>
                </Table>
              </TableContainer>
            </CardContent>
          </Card>
        </Box>
      )}

      {!result && !loading && !error && (
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 200, border: '2px dashed', borderColor: 'divider', borderRadius: 3 }}>
          <Typography color="text.secondary">Configure weights and click Optimize Schedule</Typography>
        </Box>
      )}
    </Box>
  );
};

export default OptimizeSchedule;
