import '@fontsource/roboto/300.css';
import '@fontsource/roboto/400.css';
import '@fontsource/roboto/500.css';
import '@fontsource/roboto/700.css';
import React, { Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider, CssBaseline, LinearProgress, Box } from '@mui/material';
import theme from './theme';
import Layout from './components/Layout';
import { AuthProvider } from './contexts/AuthContext';
import ProtectedRoute from './components/ProtectedRoute';

// Lazy-load every page so each becomes its own JS chunk
const Dashboard        = lazy(() => import('./pages/Dashboard'));
const AppointmentsBoard = lazy(() => import('./pages/AppointmentsBoard'));
const PredictDuration  = lazy(() => import('./pages/PredictDuration'));
const PredictNoShow    = lazy(() => import('./pages/PredictNoShow'));
const SimulateDay      = lazy(() => import('./pages/SimulateDay'));
const OptimizeSchedule = lazy(() => import('./pages/OptimizeSchedule'));
const Login            = lazy(() => import('./pages/Login'));
const AdminDashboard   = lazy(() => import('./pages/AdminDashboard'));

const PageLoader: React.FC = () => (
  <Box sx={{ width: '100%', mt: 2 }}>
    <LinearProgress />
  </Box>
);

const App: React.FC = () => (
  <ThemeProvider theme={theme}>
    <CssBaseline />
    <AuthProvider>
      <BrowserRouter>
        <Suspense fallback={<PageLoader />}>
          <Routes>
            {/* Public */}
            <Route path="/login" element={<Login />} />

            {/* Protected — all authenticated users */}
            <Route path="/" element={
              <ProtectedRoute>
                <Layout><Dashboard /></Layout>
              </ProtectedRoute>
            } />
            <Route path="/appointments" element={
              <ProtectedRoute>
                <Layout><AppointmentsBoard /></Layout>
              </ProtectedRoute>
            } />
            <Route path="/predict-duration" element={
              <ProtectedRoute>
                <Layout><PredictDuration /></Layout>
              </ProtectedRoute>
            } />
            <Route path="/predict-noshow" element={
              <ProtectedRoute>
                <Layout><PredictNoShow /></Layout>
              </ProtectedRoute>
            } />
            <Route path="/simulate-day" element={
              <ProtectedRoute>
                <Layout><SimulateDay /></Layout>
              </ProtectedRoute>
            } />
            <Route path="/optimize" element={
              <ProtectedRoute>
                <Layout><OptimizeSchedule /></Layout>
              </ProtectedRoute>
            } />

            {/* Admin only */}
            <Route path="/admin" element={
              <ProtectedRoute allowedRoles={['admin']}>
                <Layout><AdminDashboard /></Layout>
              </ProtectedRoute>
            } />

            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </Suspense>
      </BrowserRouter>
    </AuthProvider>
  </ThemeProvider>
);

export default App;
