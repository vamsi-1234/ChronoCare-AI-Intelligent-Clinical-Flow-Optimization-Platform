import React, { useState } from 'react';
import {
  Box, Card, CardContent, Typography, TextField, MenuItem,
  Button, Alert, CircularProgress, Grid, Chip, Divider,
} from '@mui/material';
import {
  RadialBarChart, RadialBar, PolarAngleAxis, ResponsiveContainer,
} from 'recharts';
import { predictNoShow } from '../api/client';
import type { PredictNoShowRequest, PredictNoShowResponse } from '../types';
import RiskBadge from '../components/RiskBadge';
import ExplanationBar from '../components/ExplanationBar';

const SPECIALTIES = [
  'cardiology', 'dermatology', 'general_practice', 'neurology',
  'oncology', 'orthopedics', 'pediatrics', 'psychiatry', 'radiology', 'urology',
];

const tomorrow = () => {
  const d = new Date();
  d.setDate(d.getDate() + 7);
  return d.toISOString().slice(0, 16);
};

const defaultForm: PredictNoShowRequest = {
  patient_id: 'P12345',
  appointment_time: tomorrow(),
  lead_time_days: 7,
  visit_type: 'new',
  age: 38,
  specialty: 'general_practice',
};

const riskColor = { low: '#2e7d32', medium: '#ed6c02', high: '#d32f2f' };

const PredictNoShow: React.FC = () => {
  const [form, setForm] = useState<PredictNoShowRequest>(defaultForm);
  const [result, setResult] = useState<PredictNoShowResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleChange = (field: keyof PredictNoShowRequest) => (
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
      const res = await predictNoShow(form);
      setResult(res);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setLoading(false);
    }
  };

  const gaugeData = result
    ? [{ name: 'risk', value: Math.round(result.no_show_probability * 100), fill: riskColor[result.risk_category] }]
    : [];

  return (
    <Box>
      <Typography variant="h4" gutterBottom>No-Show Risk Assessment</Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        Estimate the probability that a patient will not attend their appointment.
        Calibrated LightGBM classifier with SHAP explanations.
      </Typography>

      <Grid container spacing={3}>
        {/* Form */}
        <Grid size={{ xs: 12, md: 5 }}>
          <Card>
            <CardContent>
              <Typography variant="h6" gutterBottom>Patient & Appointment Details</Typography>
              <Grid container spacing={2}>
                <Grid size={6}>
                  <TextField label="Patient ID" value={form.patient_id} onChange={handleChange('patient_id')} fullWidth size="small" />
                </Grid>
                <Grid size={6}>
                  <TextField label="Age" type="number" value={form.age ?? ''} onChange={handleChange('age')} fullWidth size="small" slotProps={{ htmlInput: { min: 0, max: 120 } }} />
                </Grid>
                <Grid size={6}>
                  <TextField select label="Visit Type" value={form.visit_type} onChange={handleChange('visit_type')} fullWidth size="small">
                    <MenuItem value="new">New</MenuItem>
                    <MenuItem value="follow-up">Follow-up</MenuItem>
                  </TextField>
                </Grid>
                <Grid size={6}>
                  <TextField select label="Specialty" value={form.specialty ?? ''} onChange={handleChange('specialty')} fullWidth size="small">
                    {SPECIALTIES.map((s) => <MenuItem key={s} value={s}>{s.replace(/_/g, ' ')}</MenuItem>)}
                  </TextField>
                </Grid>
                <Grid size={6}>
                  <TextField label="Lead Time (days)" type="number" value={form.lead_time_days} onChange={handleChange('lead_time_days')} fullWidth size="small" slotProps={{ htmlInput: { min: 0, max: 180 } }} helperText="Days until appt" />
                </Grid>
                <Grid size={6}>
                  <TextField label="Past No-Show Rate" type="number" value={form.patient_no_show_rate ?? ''} onChange={handleChange('patient_no_show_rate')} fullWidth size="small" slotProps={{ htmlInput: { min: 0, max: 1, step: 0.01 } }} helperText="0.0 – 1.0" />
                </Grid>
                <Grid size={12}>
                  <TextField label="Appointment Time" type="datetime-local" value={form.appointment_time} onChange={handleChange('appointment_time')} fullWidth size="small" slotProps={{ inputLabel: { shrink: true } }} />
                </Grid>
                <Grid size={12}>
                  <Button variant="contained" fullWidth onClick={handleSubmit} disabled={loading} size="large" color="warning">
                    {loading ? <CircularProgress size={20} color="inherit" /> : 'Assess No-Show Risk'}
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
              {/* Gauge + risk category */}
              <Card>
                <CardContent sx={{ textAlign: 'center' }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
                    <Typography variant="h6">No-Show Risk</Typography>
                    <RiskBadge risk={result.risk_category} />
                  </Box>

                  <Box sx={{ height: 180 }}>
                    <ResponsiveContainer width="100%" height="100%">
                      <RadialBarChart
                        cx="50%" cy="100%"
                        innerRadius="60%" outerRadius="100%"
                        startAngle={180} endAngle={0}
                        data={gaugeData}
                      >
                        <PolarAngleAxis type="number" domain={[0, 100]} angleAxisId={0} tick={false} />
                        <RadialBar dataKey="value" cornerRadius={8} background={{ fill: '#eee' }} />
                      </RadialBarChart>
                    </ResponsiveContainer>
                  </Box>

                  <Typography
                    variant="h3"
                    sx={{ fontWeight: 700, color: riskColor[result.risk_category], mt: -3 }}
                  >
                    {(result.no_show_probability * 100).toFixed(1)}%
                  </Typography>
                  <Typography variant="body2" color="text.secondary">probability of no-show</Typography>

                  <Box sx={{ display: 'flex', gap: 1, justifyContent: 'center', mt: 2, flexWrap: 'wrap' }}>
                    <Chip label={`Risk: ${result.risk_category}`} color={result.risk_category === 'low' ? 'success' : result.risk_category === 'medium' ? 'warning' : 'error'} />
                    {result.used_fallback && <Chip label="Fallback estimate" color="warning" size="small" />}
                  </Box>

                  <Divider sx={{ my: 2 }} />
                  <Typography variant="body2" color="text.secondary" sx={{ fontStyle: 'italic' }}>
                    💬 {result.nl_explanation}
                  </Typography>
                </CardContent>
              </Card>

              {/* Risk thresholds guide */}
              <Card>
                <CardContent>
                  <Typography variant="subtitle2" gutterBottom>Risk Thresholds</Typography>
                  <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
                    <Chip label="Low < 20%" color="success" size="small" />
                    <Chip label="Medium 20–40%" color="warning" size="small" />
                    <Chip label="High > 40%" color="error" size="small" />
                  </Box>
                  <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                    High-risk appointments may be candidates for overbooking or confirmation calls.
                  </Typography>
                </CardContent>
              </Card>

              {/* SHAP */}
              {result.explanation.top_features.length > 0 && (
                <Card>
                  <CardContent>
                    <Typography variant="h6" gutterBottom>Feature Contributions (SHAP)</Typography>
                    <ExplanationBar
                      baseValue={result.explanation.base_value}
                      features={result.explanation.top_features}
                    />
                  </CardContent>
                </Card>
              )}
            </Box>
          )}

          {!result && !loading && !error && (
            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 200, border: '2px dashed', borderColor: 'divider', borderRadius: 3 }}>
              <Typography color="text.secondary">Fill the form and click Assess No-Show Risk</Typography>
            </Box>
          )}
        </Grid>
      </Grid>
    </Box>
  );
};

export default PredictNoShow;
