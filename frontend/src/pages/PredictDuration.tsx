import React, { useState } from 'react';
import {
  Box, Card, CardContent, Typography, TextField, MenuItem,
  Button, Alert, CircularProgress, Grid, Chip, Divider, LinearProgress,
} from '@mui/material';
import { predictDuration } from '../api/client';
import type { PredictDurationRequest, PredictDurationResponse } from '../types';
import ExplanationBar from '../components/ExplanationBar';

const SPECIALTIES = [
  'cardiology', 'dermatology', 'general_practice', 'neurology',
  'oncology', 'orthopedics', 'pediatrics', 'psychiatry', 'radiology', 'urology',
];

const defaultForm: PredictDurationRequest = {
  patient_id: 'P12345',
  age: 45,
  visit_type: 'follow-up',
  specialty: 'cardiology',
  comorbidity_count: 2,
  physician_id: 'D001',
  appointment_time: new Date().toISOString().slice(0, 16),
  physician_workload: 3,
  appointment_sequence: 4,
};

const PredictDuration: React.FC = () => {
  const [form, setForm] = useState<PredictDurationRequest>(defaultForm);
  const [result, setResult] = useState<PredictDurationResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleChange = (field: keyof PredictDurationRequest) => (
    e: React.ChangeEvent<HTMLInputElement>
  ) => {
    const val = e.target.type === 'number' ? Number(e.target.value) : e.target.value;
    setForm((f) => ({ ...f, [field]: val }));
  };

  const handleSubmit = async () => {
    setLoading(true);
    setError('');
    setResult(null);
    try {
      const res = await predictDuration(form);
      setResult(res);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box>
      <Typography variant="h4" gutterBottom>Predict Appointment Duration</Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        Enter patient and appointment details to get an ML-powered duration estimate with
        confidence interval and explainability breakdown.
      </Typography>

      <Grid container spacing={3}>
        {/* Form */}
        <Grid size={{ xs: 12, md: 5 }}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Input Features</Typography>
              <Grid container spacing={2}>
                <Grid size={6}>
                  <TextField label="Patient ID" value={form.patient_id} onChange={handleChange('patient_id')} fullWidth size="small" />
                </Grid>
                <Grid size={6}>
                  <TextField label="Physician ID" value={form.physician_id} onChange={handleChange('physician_id')} fullWidth size="small" />
                </Grid>
                <Grid size={6}>
                  <TextField label="Age" type="number" value={form.age} onChange={handleChange('age')} fullWidth size="small" slotProps={{ htmlInput: { min: 0, max: 120 } }} />
                </Grid>
                <Grid size={6}>
                  <TextField label="Comorbidities" type="number" value={form.comorbidity_count} onChange={handleChange('comorbidity_count')} fullWidth size="small" slotProps={{ htmlInput: { min: 0, max: 20 } }} />
                </Grid>
                <Grid size={6}>
                  <TextField select label="Visit Type" value={form.visit_type} onChange={handleChange('visit_type')} fullWidth size="small">
                    <MenuItem value="new">New</MenuItem>
                    <MenuItem value="follow-up">Follow-up</MenuItem>
                  </TextField>
                </Grid>
                <Grid size={6}>
                  <TextField select label="Specialty" value={form.specialty} onChange={handleChange('specialty')} fullWidth size="small">
                    {SPECIALTIES.map((s) => <MenuItem key={s} value={s}>{s.replace(/_/g, ' ')}</MenuItem>)}
                  </TextField>
                </Grid>
                <Grid size={6}>
                  <TextField label="Physician Workload" type="number" value={form.physician_workload ?? 0} onChange={handleChange('physician_workload')} fullWidth size="small" slotProps={{ htmlInput: { min: 0, max: 20 } }} helperText="Appts in last 2h" />
                </Grid>
                <Grid size={6}>
                  <TextField label="Appt Sequence" type="number" value={form.appointment_sequence ?? 1} onChange={handleChange('appointment_sequence')} fullWidth size="small" helperText="Position in day" />
                </Grid>
                <Grid size={12}>
                  <TextField label="Appointment Time" type="datetime-local" value={form.appointment_time ?? ''} onChange={handleChange('appointment_time')} fullWidth size="small" slotProps={{ inputLabel: { shrink: true } }} />
                </Grid>
                <Grid size={12}>
                  <Button variant="contained" fullWidth onClick={handleSubmit} disabled={loading} size="large">
                    {loading ? <CircularProgress size={20} color="inherit" /> : 'Predict Duration'}
                  </Button>
                </Grid>
              </Grid>
            </CardContent>
          </Card>
        </Grid>

        {/* Results */}
        <Grid size={{ xs: 12, md: 7 }}>
          {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
          {result && (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
              {/* Main prediction */}
              <Card>
                <CardContent>
                  <Typography variant="h6" gutterBottom>Prediction Result</Typography>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
                    <Typography variant="h3" color="primary.main" sx={{ fontWeight: 700 }}>
                      {result.predicted_duration_minutes}
                    </Typography>
                    <Typography variant="h6" color="text.secondary">minutes</Typography>
                    {result.used_fallback && (
                      <Chip label="Fallback" color="warning" size="small" />
                    )}
                  </Box>

                  {/* Confidence interval bar */}
                  <Box sx={{ mb: 2 }}>
                    <Typography variant="body2" color="text.secondary" gutterBottom>
                      90% Confidence Interval: <strong>{result.lower_bound} – {result.upper_bound} min</strong>
                    </Typography>
                    <Box sx={{ position: 'relative', height: 20, bgcolor: 'primary.light', borderRadius: 2, opacity: 0.3, width: '100%' }} />
                    <Box sx={{
                      position: 'relative', mt: -2.5,
                      mx: `${Math.max(0, (result.lower_bound / result.upper_bound) * 50)}%`,
                      width: `${Math.min(100, ((result.upper_bound - result.lower_bound) / result.upper_bound) * 100)}%`,
                      height: 20, bgcolor: 'primary.main', borderRadius: 2, opacity: 0.7,
                    }} />
                  </Box>

                  <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                    <Chip label={`Confidence: ${result.confidence_pct}%`} color="success" size="small" />
                    <Chip label={`Lower: ${result.lower_bound} min`} size="small" />
                    <Chip label={`Upper: ${result.upper_bound} min`} size="small" />
                  </Box>

                  <Divider sx={{ my: 2 }} />
                  <Typography variant="body2" color="text.secondary" sx={{ fontStyle: 'italic' }}>
                    💬 {result.nl_explanation}
                  </Typography>
                </CardContent>
              </Card>

              {/* SHAP Explanation */}
              {result.explanation.top_features.length > 0 && (
                <Card>
                  <CardContent>
                    <Typography variant="h6" gutterBottom>Feature Contributions (SHAP)</Typography>
                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 2 }}>
                      Red = increases duration · Green = decreases duration
                    </Typography>
                    <ExplanationBar
                      baseValue={result.explanation.base_value}
                      features={result.explanation.top_features}
                    />
                    <Divider sx={{ my: 1.5 }} />
                    <Box sx={{ display: 'flex', gap: 1 }}>
                      <Chip label={`Base: ${result.explanation.base_value?.toFixed(1)} min`} size="small" variant="outlined" />
                      <Chip label={`Final: ${result.predicted_duration_minutes} min`} color="primary" size="small" />
                    </Box>
                  </CardContent>
                </Card>
              )}

              {/* Confidence meter */}
              <Card>
                <CardContent>
                  <Typography variant="body2" gutterBottom>Prediction Confidence</Typography>
                  <LinearProgress
                    variant="determinate"
                    value={result.confidence_pct}
                    sx={{ height: 10, borderRadius: 5, mb: 0.5 }}
                    color={result.confidence_pct > 70 ? 'success' : result.confidence_pct > 40 ? 'warning' : 'error'}
                  />
                  <Typography variant="caption" color="text.secondary">{result.confidence_pct}%</Typography>
                </CardContent>
              </Card>
            </Box>
          )}
          {!result && !loading && !error && (
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 200, border: '2px dashed', borderColor: 'divider', borderRadius: 3 }}>
              <Typography color="text.secondary">Fill the form and click Predict Duration</Typography>
            </Box>
          )}
        </Grid>
      </Grid>
    </Box>
  );
};

export default PredictDuration;
