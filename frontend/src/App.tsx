import '@fontsource/roboto/300.css';
import '@fontsource/roboto/400.css';
import '@fontsource/roboto/500.css';
import '@fontsource/roboto/700.css';
import React, { Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { ThemeProvider, CssBaseline, LinearProgress, Box } from '@mui/material';
import theme from './theme';
import Layout from './components/Layout';

// Lazy-load every page so each becomes its own JS chunk
const Dashboard        = lazy(() => import('./pages/Dashboard'));
const AppointmentsBoard = lazy(() => import('./pages/AppointmentsBoard'));
const PredictDuration  = lazy(() => import('./pages/PredictDuration'));
const PredictNoShow    = lazy(() => import('./pages/PredictNoShow'));
const SimulateDay      = lazy(() => import('./pages/SimulateDay'));
const OptimizeSchedule = lazy(() => import('./pages/OptimizeSchedule'));

const PageLoader: React.FC = () => (
  <Box sx={{ width: '100%', mt: 2 }}>
    <LinearProgress />
  </Box>
);

const App: React.FC = () => (
  <ThemeProvider theme={theme}>
    <CssBaseline />
    <BrowserRouter>
      <Layout>
        <Suspense fallback={<PageLoader />}>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/appointments" element={<AppointmentsBoard />} />
            <Route path="/predict-duration" element={<PredictDuration />} />
            <Route path="/predict-noshow" element={<PredictNoShow />} />
            <Route path="/simulate-day" element={<SimulateDay />} />
            <Route path="/optimize" element={<OptimizeSchedule />} />
          </Routes>
        </Suspense>
      </Layout>
    </BrowserRouter>
  </ThemeProvider>
);

export default App;
