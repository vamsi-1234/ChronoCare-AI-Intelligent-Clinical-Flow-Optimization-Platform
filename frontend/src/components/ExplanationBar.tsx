import React from 'react';
import { Box, Chip } from '@mui/material';
import type { SHAPFeature } from '../types';

interface Props {
  baseValue?: number | null;
  features: SHAPFeature[];
  maxWidth?: number;
}

const BAR_MAX = 200;

const ExplanationBar: React.FC<Props> = ({ baseValue, features, maxWidth = BAR_MAX }) => {
  if (!features.length) return null;
  const maxAbs = Math.max(...features.map((f) => Math.abs(f.contribution)), 0.001);

  return (
    <Box>
      {baseValue != null && (
        <Box sx={{ mb: 1, color: 'text.secondary', fontSize: 13 }}>
          Base value: <strong>{baseValue.toFixed(2)}</strong>
        </Box>
      )}
      {features.map((f) => {
        const pct = (Math.abs(f.contribution) / maxAbs) * maxWidth;
        const positive = f.contribution >= 0;
        return (
          <Box key={f.name} sx={{ display: 'flex', alignItems: 'center', mb: 0.8, gap: 1 }}>
            <Box sx={{ width: 160, fontSize: 12, color: 'text.secondary', flexShrink: 0 }}>
              {f.name}
              <Chip
                label={f.value}
                size="small"
                sx={{ ml: 0.5, height: 16, fontSize: 10 }}
              />
            </Box>
            <Box sx={{ flex: 1, display: 'flex', alignItems: 'center' }}>
              <Box
                sx={{
                  width: pct,
                  height: 14,
                  borderRadius: 2,
                  bgcolor: positive ? 'error.light' : 'success.light',
                  transition: 'width 0.4s ease',
                  minWidth: 4,
                }}
              />
              <Box
                sx={{
                  ml: 0.5,
                  fontSize: 11,
                  fontWeight: 600,
                  color: positive ? 'error.main' : 'success.main',
                }}
              >
                {positive ? '+' : ''}
                {f.contribution.toFixed(3)}
              </Box>
            </Box>
          </Box>
        );
      })}
    </Box>
  );
};

export default ExplanationBar;
