import axios from 'axios';
import type {
  HealthResponse,
  PredictDurationRequest,
  PredictDurationResponse,
  PredictNoShowRequest,
  PredictNoShowResponse,
  SimulateDayRequest,
  SimulateDayResponse,
  OptimizeScheduleRequest,
  OptimizeScheduleResponse,
  DayAppointment,
  DayAppointmentsResponse,
  AssessAllResponse,
} from '../types';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api/v1',
  headers: { 'Content-Type': 'application/json' },
  timeout: 30000,
});

// Response interceptor for clean error messages
api.interceptors.response.use(
  (res) => res,
  (err) => {
    const msg =
      err.response?.data?.detail ||
      err.response?.data?.message ||
      err.message ||
      'Unknown error';
    return Promise.reject(new Error(typeof msg === 'string' ? msg : JSON.stringify(msg)));
  }
);

export const getHealth = () =>
  api.get<HealthResponse>('/health').then((r) => r.data);

export const predictDuration = (body: PredictDurationRequest) =>
  api.post<PredictDurationResponse>('/predict-duration', body).then((r) => r.data);

export const predictNoShow = (body: PredictNoShowRequest) =>
  api.post<PredictNoShowResponse>('/predict-no-show', body).then((r) => r.data);

export const simulateDay = (body: SimulateDayRequest) =>
  api.post<SimulateDayResponse>('/simulate-day', body).then((r) => r.data);

export const optimizeSchedule = (body: OptimizeScheduleRequest) =>
  api.post<OptimizeScheduleResponse>('/optimize-schedule', body).then((r) => r.data);

// ── Daily Appointments Board ───────────────────────────────────────────────

export const getDayAppointments = (physicianId: string, date: string) =>
  api
    .get<DayAppointmentsResponse>(`/appointments/day/${physicianId}/${date}`)
    .then((r) => r.data);

export const assessAllAppointments = (physicianId: string, date: string) =>
  api
    .post<AssessAllResponse>(`/appointments/assess-all/${physicianId}/${date}`)
    .then((r) => r.data);

export const assessAppointment = (id: string) =>
  api.post<DayAppointment>(`/appointments/${id}/assess`).then((r) => r.data);

export const updateAppointmentStatus = (id: string, newStatus: string) =>
  api
    .put<DayAppointment>(`/appointments/${id}/status`, { status: newStatus })
    .then((r) => r.data);

