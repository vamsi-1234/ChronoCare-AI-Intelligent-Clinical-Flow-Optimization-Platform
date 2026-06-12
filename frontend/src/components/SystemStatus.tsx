import React, { useEffect, useState } from 'react';
import {
  Box, Chip, Tooltip, Typography,
} from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import { getHealth } from '../api/client';
import type { HealthResponse } from '../types';

const StatusDot: React.FC<{ ok: boolean; label: string }> = ({ ok, label }) => (
  <Tooltip title={label}>
    <Chip
      icon={ok ? <CheckCircleIcon sx={{ fontSize: 14 }} /> : <ErrorIcon sx={{ fontSize: 14 }} />}
      label={label}
      color={ok ? 'success' : 'error'}
      size="small"
      variant="outlined"
      sx={{ fontSize: 11 }}
    />
  </Tooltip>
);

const SystemStatus: React.FC = () => {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    getHealth()
      .then(setHealth)
      .catch(() => setError(true));
    const id = setInterval(() => {
      getHealth()
        .then((h) => { setHealth(h); setError(false); })
        .catch(() => setError(true));
    }, 30000);
    return () => clearInterval(id);
  }, []);

  return (
    <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', flexWrap: 'wrap' }}>
      {error ? (
        <Chip label="API Unreachable" color="error" size="small" />
      ) : health ? (
        <>
          <StatusDot ok={health.status === 'ok'} label="API" />
          <StatusDot ok={health.database} label="Database" />
          <StatusDot ok={health.models?.duration_model} label="Duration Model" />
          <StatusDot ok={health.models?.noshow_model} label="No-Show Model" />
          <Typography variant="caption" sx={{ color: 'text.secondary' }}>
            v{health.version}
          </Typography>
        </>
      ) : (
        <Chip label="Checking…" size="small" />
      )}
    </Box>
  );
};

export default SystemStatus;
