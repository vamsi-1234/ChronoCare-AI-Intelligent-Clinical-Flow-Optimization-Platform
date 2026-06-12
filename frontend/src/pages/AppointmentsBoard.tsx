import React, { useState, useCallback } from 'react';
import {
  Box, Paper, Typography, Button, TextField, Select, MenuItem,
  Table, TableBody, TableCell, TableContainer, TableHead, TableRow,
  Chip, Tooltip, CircularProgress, Alert, Grid, Card, CardContent,
  LinearProgress, Stack,
} from '@mui/material';
import RefreshIcon from '@mui/icons-material/Refresh';
import AssessmentIcon from '@mui/icons-material/Assessment';
import ScheduleSendIcon from '@mui/icons-material/ScheduleSend';
import type {
  DayAppointment,
  DayAppointmentsResponse,
  AssessAllResponse,
} from '../types';
import {
  getDayAppointments,
  assessAllAppointments,
  assessAppointment,
  updateAppointmentStatus,
  simulateDay,
} from '../api/client';

const TODAY = new Date().toISOString().slice(0, 10);

const formatTime = (iso: string) => {
  try {
    return new Date(iso).toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false });
  } catch { return iso.slice(11, 16); }
};

const SPECIALTY_EMOJI: Record<string, string> = {
  cardiology: '❤️', dermatology: '🧴', general_practice: '🏥',
  neurology: '🧠', oncology: '🔬', orthopedics: '🦴',
  pediatrics: '👶', psychiatry: '💭', radiology: '📷', urology: '🫀',
};

const RiskBadge: React.FC<{ risk?: string | null; prob?: number | null }> = ({ risk, prob }) => {
  if (!risk) return <Typography variant="caption" color="text.disabled">—</Typography>;
  const bg: Record<string, string> = { low: '#e8f5e9', medium: '#fff3e0', high: '#fce4ec' };
  const fg: Record<string, string> = { low: '#2e7d32', medium: '#e65100', high: '#b71c1c' };
  return (
    <Tooltip title={prob != null ? `${Math.round((prob ?? 0) * 100)}% probability of no-show` : ''}>
      <Box sx={{ display: 'inline-flex', alignItems: 'center', gap: 0.5, px: 1, py: 0.3, borderRadius: 1, bgcolor: bg[risk] || '#f5f5f5', color: fg[risk] || '#424242', cursor: 'default' }}>
        <Box sx={{ width: 7, height: 7, borderRadius: '50%', bgcolor: fg[risk] || '#9e9e9e' }} />
        <Typography variant="caption" sx={{ fontWeight: 700, textTransform: 'uppercase' }}>{risk}</Typography>
        {prob != null && <Typography variant="caption" sx={{ opacity: 0.8 }}>{Math.round((prob ?? 0) * 100)}%</Typography>}
      </Box>
    </Tooltip>
  );
};

const DelayChip: React.FC<{ delay?: number | null }> = ({ delay }) => {
  if (delay == null) return <Typography variant="caption" color="text.disabled">—</Typography>;
  if (delay <= 2) return <Chip label="On time" size="small" color="success" variant="outlined" />;
  if (delay <= 10) return <Chip label={`+${Math.round(delay)} min`} size="small" color="warning" />;
  return <Chip label={`+${Math.round(delay)} min ⚠`} size="small" color="error" />;
};

const StatusSelect: React.FC<{ value: string; onChange: (v: string) => void }> = ({ value, onChange }) => (
  <Select value={value} onChange={e => onChange(e.target.value)} size="small" sx={{ minWidth: 130, fontSize: '0.8rem' }}>
    <MenuItem value="pending">⏳ Pending</MenuItem>
    <MenuItem value="in_progress">▶️ In Progress</MenuItem>
    <MenuItem value="completed">✅ Completed</MenuItem>
    <MenuItem value="no_show">❌ No Show</MenuItem>
  </Select>
);

interface SummaryCardProps { label: string; value: string | number; icon: string; color: string; }
const SummaryCard: React.FC<SummaryCardProps> = ({ label, value, icon, color }) => (
  <Card variant="outlined" sx={{ height: '100%' }}>
    <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 } }}>
      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
        {icon} {label}
      </Typography>
      <Typography variant="h5" sx={{ fontWeight: 800, color }}>{value}</Typography>
    </CardContent>
  </Card>
);

const AppointmentsBoard: React.FC = () => {
  const [physicianId, setPhysicianId] = useState('D001');
  const [date, setDate] = useState(TODAY);
  const [appointments, setAppointments] = useState<DayAppointment[]>([]);
  const [hasLoaded, setHasLoaded] = useState(false);
  const [loading, setLoading] = useState(false);
  const [assessing, setAssessing] = useState(false);
  const [simulating, setSimulating] = useState(false);
  const [simulationDone, setSimulationDone] = useState(false);
  const [error, setError] = useState('');
  const [simSummary, setSimSummary] = useState<{ totalWait: number; overrun: number; atRisk: number } | null>(null);

  const assessed = appointments.filter(a => a.assessed_at).length;
  const highRisk = appointments.filter(a => a.risk_category === 'high').length;
  const totalPredMin = appointments.reduce((s, a) => s + (a.predicted_duration ?? 0), 0);

  const loadDay = useCallback(async () => {
    setLoading(true); setError(''); setSimulationDone(false); setSimSummary(null);
    try {
      const resp: DayAppointmentsResponse = await getDayAppointments(physicianId, date);
      setAppointments(resp.appointments);
      setHasLoaded(true);
    } catch (e: unknown) { setError((e as Error).message || 'Failed to load appointments'); }
    finally { setLoading(false); }
  }, [physicianId, date]);

  const handleAssessAll = async () => {
    setAssessing(true); setError('');
    try {
      const resp: AssessAllResponse = await assessAllAppointments(physicianId, date);
      setAppointments(resp.appointments);
    } catch (e: unknown) { setError((e as Error).message || 'Assessment failed'); }
    finally { setAssessing(false); }
  };

  const handleAssessSingle = async (id: string) => {
    try {
      const updated = await assessAppointment(id);
      setAppointments(prev => prev.map(a => a.appointment_id === id ? updated : a));
    } catch (e: unknown) { setError((e as Error).message || 'Assessment failed'); }
  };

  const handleSimulate = async () => {
    setSimulating(true); setError('');
    try {
      const slots = appointments
        .filter(a => a.status !== 'no_show')
        .map(a => ({ appointment_id: a.appointment_id, patient_id: a.patient_id, scheduled_start: a.scheduled_start, predicted_duration: a.predicted_duration ?? 20, no_show_probability: a.no_show_probability ?? 0.15, visit_type: a.visit_type, priority: a.priority }));
      const sim = await simulateDay({ physician_id: physicianId, date, appointments: slots });
      setAppointments(prev => prev.map(a => {
        const slot = sim.simulated_appointments.find(s => s.appointment_id === a.appointment_id);
        if (!slot) return a;
        return { ...a, delay_minutes: slot.delay_minutes, is_at_risk: slot.is_at_risk, predicted_start: slot.predicted_start };
      }));
      setSimSummary({ totalWait: sim.total_waiting_time_minutes, overrun: sim.schedule_overrun_minutes, atRisk: sim.at_risk_count });
      setSimulationDone(true);
    } catch (e: unknown) { setError((e as Error).message || 'Simulation failed'); }
    finally { setSimulating(false); }
  };

  const handleStatusChange = async (id: string, newStatus: string) => {
    try {
      await updateAppointmentStatus(id, newStatus);
      setAppointments(prev => prev.map(a => a.appointment_id === id ? { ...a, status: newStatus as DayAppointment['status'] } : a));
    } catch (e: unknown) { setError((e as Error).message || 'Status update failed'); }
  };

  const busy = loading || assessing || simulating;

  return (
    <Box>
      <Typography variant="h4" gutterBottom>📋 Daily Appointments Board</Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        Load your schedule, run AI risk assessment, simulate delay propagation, and manage appointment status — all in one view.
      </Typography>

      <Paper sx={{ p: 2, mb: 3 }} variant="outlined">
        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ flexWrap: 'wrap', alignItems: 'center' }}>
          <TextField label="Physician ID" value={physicianId} onChange={e => setPhysicianId(e.target.value)} size="small" sx={{ width: 140 }} />
          <TextField label="Date" type="date" value={date} onChange={e => { setDate(e.target.value); setHasLoaded(false); }} size="small" slotProps={{ htmlInput: { max: '2030-12-31' } }} sx={{ width: 180 }} />
          <Button variant="contained" onClick={loadDay} disabled={busy} startIcon={loading ? <CircularProgress size={16} color="inherit" /> : <RefreshIcon />} sx={{ minWidth: 120 }}>
            Load Day
          </Button>
          {hasLoaded && <>
            <Button variant="outlined" color="secondary" onClick={handleAssessAll} disabled={busy || appointments.length === 0} startIcon={assessing ? <CircularProgress size={16} /> : <AssessmentIcon />} sx={{ minWidth: 130 }}>
              Assess All
            </Button>
            <Button variant="outlined" onClick={handleSimulate} disabled={busy || appointments.length === 0} startIcon={simulating ? <CircularProgress size={16} /> : <ScheduleSendIcon />} sx={{ minWidth: 130 }}>
              Simulate Day
            </Button>
          </>}
        </Stack>
      </Paper>

      {busy && <LinearProgress sx={{ mb: 2, borderRadius: 1 }} />}
      {error && <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError('')}>{error}</Alert>}

      {hasLoaded && appointments.length > 0 && (
        <Grid container spacing={2} sx={{ mb: 3 }}>
          <Grid size={{ xs: 6, sm: 4, md: 2.4 }}>
            <SummaryCard label="Appointments" value={appointments.length} icon="📅" color="primary.main" />
          </Grid>
          <Grid size={{ xs: 6, sm: 4, md: 2.4 }}>
            <SummaryCard label="Assessed" value={`${assessed} / ${appointments.length}`} icon="✅" color="success.main" />
          </Grid>
          <Grid size={{ xs: 6, sm: 4, md: 2.4 }}>
            <SummaryCard label="High Risk" value={highRisk} icon="⚠️" color="error.main" />
          </Grid>
          <Grid size={{ xs: 6, sm: 4, md: 2.4 }}>
            <SummaryCard label="Total Pred. Time" value={assessed > 0 ? `${Math.round(totalPredMin)} min` : '—'} icon="⏱️" color="text.primary" />
          </Grid>
          <Grid size={{ xs: 6, sm: 4, md: 2.4 }}>
            <SummaryCard label="Sim. Overrun" value={simSummary ? `${Math.round(simSummary.overrun)} min` : '—'} icon="📈" color={simSummary && simSummary.overrun > 10 ? 'error.main' : 'text.secondary'} />
          </Grid>
        </Grid>
      )}

      {simulationDone && simSummary && (
        <Alert severity={simSummary.atRisk > 0 ? 'warning' : 'success'} sx={{ mb: 2 }}>
          <strong>Simulation complete.</strong> Total waiting time: <strong>{Math.round(simSummary.totalWait)} min</strong> | Overrun: <strong>{Math.round(simSummary.overrun)} min</strong> | At-risk: <strong>{simSummary.atRisk}</strong>.
          {simSummary.atRisk > 0 && ' Highlighted rows have delays > 15 min.'}
        </Alert>
      )}

      {hasLoaded ? (
        <TableContainer component={Paper} variant="outlined">
          <Table size="small" sx={{ minWidth: 900 }}>
            <TableHead>
              <TableRow sx={{ bgcolor: 'grey.100' }}>
                {['Time', 'Patient', 'Type', 'Specialty', 'Age / Comorbid', 'Pred. Duration', 'No-Show Risk', ...(simulationDone ? ['Delay'] : []), 'Status', 'Actions'].map(h => (
                  <TableCell key={h} sx={{ fontWeight: 700, whiteSpace: 'nowrap' }}>{h}</TableCell>
                ))}
              </TableRow>
            </TableHead>
            <TableBody>
              {appointments.length === 0 ? (
                <TableRow><TableCell colSpan={10} align="center" sx={{ py: 5, color: 'text.secondary' }}>No appointments found for this day.</TableCell></TableRow>
              ) : appointments.map(appt => (
                <TableRow
                  key={appt.appointment_id}
                  sx={{
                    bgcolor: appt.is_at_risk ? '#fff8e1' : appt.risk_category === 'high' ? '#fff3f3' : 'inherit',
                    '&:hover': { bgcolor: appt.is_at_risk ? '#fff3cd' : 'action.hover' },
                    opacity: appt.status === 'no_show' ? 0.55 : 1,
                    transition: 'background-color 0.15s',
                  }}
                >
                  <TableCell>
                    <Typography variant="body2" sx={{ fontWeight: 700 }}>{formatTime(appt.scheduled_start)}</Typography>
                    <Typography variant="caption" color="text.secondary">{appt.appointment_id}</Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2" sx={{ fontWeight: 600 }}>{appt.patient_id}</Typography>
                    <Typography variant="caption" color="text.secondary">Priority {appt.priority}/5</Typography>
                  </TableCell>
                  <TableCell>
                    <Chip label={appt.visit_type === 'new' ? '🆕 New' : 'Follow-up'} size="small" color={appt.visit_type === 'new' ? 'secondary' : 'default'} variant={appt.visit_type === 'new' ? 'filled' : 'outlined'} sx={{ fontSize: '0.72rem' }} />
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">{SPECIALTY_EMOJI[appt.specialty] || ''} {appt.specialty.replace(/_/g, ' ')}</Typography>
                  </TableCell>
                  <TableCell>
                    <Typography variant="body2">{appt.age} yrs</Typography>
                    <Box sx={{ display: 'flex', gap: 0.3, mt: 0.2, flexWrap: 'wrap' }}>
                      {appt.comorbidity_count === 0
                        ? <Typography variant="caption" color="text.secondary">none</Typography>
                        : Array.from({ length: Math.min(appt.comorbidity_count, 5) }).map((_, i) => (
                          <Box key={i} sx={{ width: 7, height: 7, borderRadius: '50%', bgcolor: 'error.light' }} />
                        ))}
                      {appt.comorbidity_count > 5 && <Typography variant="caption" color="text.secondary">+{appt.comorbidity_count - 5}</Typography>}
                    </Box>
                  </TableCell>
                  <TableCell>
                    {appt.predicted_duration != null ? (
                      <Tooltip title={appt.nl_duration_explanation || 'AI prediction'} placement="top">
                        <Box>
                          <Typography variant="body2" sx={{ fontWeight: 700 }}>{Math.round(appt.predicted_duration)} min</Typography>
                          {appt.duration_lower != null && appt.duration_upper != null && (
                            <Typography variant="caption" color="text.secondary">{Math.round(appt.duration_lower)}–{Math.round(appt.duration_upper)} min</Typography>
                          )}
                        </Box>
                      </Tooltip>
                    ) : <Typography variant="caption" color="text.disabled">—</Typography>}
                  </TableCell>
                  <TableCell>
                    <Tooltip title={appt.nl_noshow_explanation || 'AI no-show prediction'} placement="top">
                      <Box><RiskBadge risk={appt.risk_category} prob={appt.no_show_probability} /></Box>
                    </Tooltip>
                  </TableCell>
                  {simulationDone && <TableCell><DelayChip delay={appt.delay_minutes} /></TableCell>}
                  <TableCell>
                    <StatusSelect value={appt.status} onChange={v => handleStatusChange(appt.appointment_id, v)} />
                  </TableCell>
                  <TableCell>
                    {appt.assessed_at
                      ? <Chip label="Assessed ✓" size="small" color="success" variant="outlined" />
                      : <Button size="small" variant="outlined" onClick={() => handleAssessSingle(appt.appointment_id)} disabled={busy}>Assess</Button>}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      ) : !loading && (
        <Box sx={{ textAlign: 'center', py: 10, border: '2px dashed', borderColor: 'divider', borderRadius: 2 }}>
          <Typography variant="h6" color="text.secondary" gutterBottom>📅 No data loaded yet</Typography>
          <Typography variant="body2" color="text.disabled">Enter a Physician ID and date above, then click <strong>Load Day</strong>.</Typography>
          <Typography variant="body2" color="text.disabled" sx={{ mt: 0.5 }}>Sample appointments are automatically generated for demonstration.</Typography>
        </Box>
      )}

      <Typography variant="caption" color="text.disabled" sx={{ display: 'block', mt: 2 }}>
        ⚠ AI predictions are for demonstration only and not for clinical use. Status changes are stored in-memory and reset on server restart.
      </Typography>
    </Box>
  );
};

export default AppointmentsBoard;
