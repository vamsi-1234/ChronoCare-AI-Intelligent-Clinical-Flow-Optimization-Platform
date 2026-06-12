import React, { useEffect, useState } from 'react';
import {
  Box, Grid, Card, CardContent, Typography, CircularProgress, Alert,
  LinearProgress, Divider,
} from '@mui/material';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import PersonOffIcon from '@mui/icons-material/PersonOff';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import { getHealth } from '../api/client';
import type { HealthResponse } from '../types';

const StatCard: React.FC<{
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ReactNode;
  color: string;
  progress?: number;
}> = ({ title, value, subtitle, icon, color, progress }) => (
  <Card>
    <CardContent>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <Box>
          <Typography variant="body2" color="text.secondary" gutterBottom>
            {title}
          </Typography>
          <Typography variant="h4" sx={{ fontWeight: 700, color }}>
            {value}
          </Typography>
          {subtitle && (
            <Typography variant="caption" color="text.secondary">
              {subtitle}
            </Typography>
          )}
        </Box>
        <Box
          sx={{
            bgcolor: color + '1a',
            borderRadius: 2,
            p: 1.2,
            display: 'flex',
            alignItems: 'center',
            color,
          }}
        >
          {icon}
        </Box>
      </Box>
      {progress !== undefined && (
        <Box sx={{ mt: 2 }}>
          <LinearProgress
            variant="determinate"
            value={progress}
            sx={{
              height: 6,
              borderRadius: 3,
              bgcolor: color + '22',
              '& .MuiLinearProgress-bar': { bgcolor: color },
            }}
          />
        </Box>
      )}
    </CardContent>
  </Card>
);

const Dashboard: React.FC = () => {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    getHealth()
      .then(setHealth)
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading)
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', mt: 8 }}>
        <CircularProgress />
      </Box>
    );

  return (
    <Box>
      <Box sx={{ mb: 3 }}>
        <Typography variant="h4" gutterBottom>
          Dashboard
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Welcome to ChronoCare AI — Intelligent Clinical Flow Optimization Platform
        </Typography>
      </Box>

      {error && <Alert severity="warning" sx={{ mb: 2 }}>{error}</Alert>}

      {/* Stats */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <StatCard
            title="Duration Model"
            value={health?.models.duration_model ? 'Ready' : 'Offline'}
            subtitle="MAE ≈ 5 min"
            icon={<AccessTimeIcon />}
            color={health?.models.duration_model ? '#2e7d32' : '#d32f2f'}
            progress={health?.models.duration_model ? 100 : 0}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <StatCard
            title="No-Show Model"
            value={health?.models.noshow_model ? 'Ready' : 'Offline'}
            subtitle="AUC ≈ 0.61"
            icon={<PersonOffIcon />}
            color={health?.models.noshow_model ? '#2e7d32' : '#d32f2f'}
            progress={health?.models.noshow_model ? 61 : 0}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <StatCard
            title="Database"
            value={health?.database ? 'Connected' : 'Error'}
            subtitle="SQLite / PostgreSQL"
            icon={<CheckCircleIcon />}
            color={health?.database ? '#1976d2' : '#d32f2f'}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 3 }}>
          <StatCard
            title="API Version"
            value={health?.version ?? '—'}
            subtitle="FastAPI / Uvicorn"
            icon={<WarningAmberIcon />}
            color="#ed6c02"
          />
        </Grid>
      </Grid>

      {/* Feature cards */}
      <Typography variant="h5" sx={{ mb: 2 }}>
        Platform Features
      </Typography>
      <Grid container spacing={3}>
        {[
          {
            title: '⏱ Appointment Duration Prediction',
            desc: 'LightGBM regressor predicts consultation duration with 90% confidence intervals. SHAP explainability included.',
            target: 'MAE < 5 min',
          },
          {
            title: '🚫 No-Show Risk Assessment',
            desc: 'Identify high-risk appointments based on lead time, visit type, and patient history. Risk category: Low / Medium / High.',
            target: 'AUC > 0.75',
          },
          {
            title: '📅 Dynamic Delay Simulation',
            desc: 'Discrete-event simulation propagates delays across the full day, identifies at-risk slots, and generates recommendations.',
            target: '< 5s for 50+ appts',
          },
          {
            title: '✨ Adaptive Schedule Optimization',
            desc: 'Priority-aware greedy optimizer reorders appointments to minimize total waiting time, workload variance, and overrun.',
            target: '20%+ wait reduction',
          },
        ].map((f) => (
          <Grid key={f.title} size={{ xs: 12, sm: 6 }}>
            <Card sx={{ height: '100%' }}>
              <CardContent>
                <Typography variant="h6" gutterBottom>
                  {f.title}
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
                  {f.desc}
                </Typography>
                <Divider sx={{ mb: 1 }} />
                <Typography variant="caption" color="primary.main" sx={{ fontWeight: 600 }}>
                  Target: {f.target}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Disclaimer */}
      <Alert severity="info" sx={{ mt: 4 }}>
        <strong>Disclaimer:</strong> ChronoCare AI is a decision-support tool for scheduling
        optimization only. It does not provide medical diagnosis, treatment recommendations, or
        clinical decision-making. All scheduling decisions should be reviewed by qualified
        healthcare administrators.
      </Alert>
    </Box>
  );
};

export default Dashboard;
