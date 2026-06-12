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
  Patient,
  PatientCreate,
  VisitHistoryEntry,
  UserOut,
  UpdateUserRequest,
  CreateAppointmentRequest,
} from '../types';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api/v1',
  headers: { 'Content-Type': 'application/json' },
  timeout: 30000,
});

// Attach JWT token from localStorage on every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('chronocare_token');
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// Response interceptor — clean error messages + auto-logout on 401
api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('chronocare_token');
      localStorage.removeItem('chronocare_user');
      window.location.href = '/login';
    }
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

// ── Daily Appointments Board ──────────────────────────────────────────────

export const getDayAppointments = (physicianId: string, date: string) =>
  api.get<DayAppointmentsResponse>(`/appointments/day/${physicianId}/${date}`).then((r) => r.data);

export const assessAllAppointments = (physicianId: string, date: string) =>
  api.post<AssessAllResponse>(`/appointments/assess-all/${physicianId}/${date}`).then((r) => r.data);

export const assessAppointment = (id: string) =>
  api.post<DayAppointment>(`/appointments/${id}/assess`).then((r) => r.data);

export const updateAppointmentStatus = (id: string, newStatus: string) =>
  api.put<DayAppointment>(`/appointments/${id}/status`, { status: newStatus }).then((r) => r.data);

export const createAppointment = (body: CreateAppointmentRequest) =>
  api.post<DayAppointment>('/appointments', body).then((r) => r.data);

// ── Patients ──────────────────────────────────────────────────────────────

export const searchPatients = (q?: string) =>
  api.get<Patient[]>('/patients', { params: q ? { q } : {} }).then((r) => r.data);

export const createPatient = (body: PatientCreate) =>
  api.post<Patient>('/patients', body).then((r) => r.data);

export const getPatient = (id: number) =>
  api.get<Patient>(`/patients/${id}`).then((r) => r.data);

export const getPatientHistory = (id: number) =>
  api.get<VisitHistoryEntry[]>(`/patients/${id}/history`).then((r) => r.data);

// ── Users (admin) ─────────────────────────────────────────────────────────

export const listUsers = () =>
  api.get<UserOut[]>('/users').then((r) => r.data);

export const updateUser = (id: number, body: UpdateUserRequest) =>
  api.patch<UserOut>(`/users/${id}`, body).then((r) => r.data);

export const deactivateUser = (id: number) =>
  api.delete(`/users/${id}`);

// ── Auth ──────────────────────────────────────────────────────────────────

export const registerUser = (body: {
  email: string;
  password: string;
  full_name: string;
  role: string;
  physician_id?: string;
}) => api.post<UserOut>('/auth/register', body).then((r) => r.data);

