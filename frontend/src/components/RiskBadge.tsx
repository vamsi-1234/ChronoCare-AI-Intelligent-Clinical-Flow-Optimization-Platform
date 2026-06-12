import React from 'react';
import { Chip } from '@mui/material';

interface Props {
  risk: 'low' | 'medium' | 'high';
}

const color: Record<string, 'success' | 'warning' | 'error'> = {
  low: 'success',
  medium: 'warning',
  high: 'error',
};

const RiskBadge: React.FC<Props> = ({ risk }) => (
  <Chip
    label={risk.toUpperCase()}
    color={color[risk] ?? 'default'}
    size="small"
    sx={{ fontWeight: 700, letterSpacing: 0.5 }}
  />
);

export default RiskBadge;
