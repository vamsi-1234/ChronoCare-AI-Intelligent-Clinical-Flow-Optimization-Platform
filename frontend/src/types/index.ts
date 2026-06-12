// API types matching backend Pydantic schemas

export interface SHAPFeature {
  name: string;
  value: number;
  contribution: number;
}

export interface Explanation {
  base_value: number | null;
  top_features: SHAPFeature[];
}

// Duration Prediction
export interface PredictDurationRequest {
  patient_id: string;
  age: number;
  visit_type: 'new' | 'follow-up';
  specialty: string;
  comorbidity_count: number;
  physician_id: string;
  appointment_time?: string;
  patient_visit_count?: number;
  patient_avg_duration?: number;
  physician_avg_duration?: number;
  physician_workload?: number;
  appointment_sequence?: number;
}

export interface PredictDurationResponse {
  predicted_duration_minutes: number;
  lower_bound: number;
  upper_bound: number;
  confidence_pct: number;
  explanation: Explanation;
  nl_explanation: string;
  used_fallback: boolean;
}

// No-Show Prediction
export interface PredictNoShowRequest {
  patient_id: string;
  appointment_time: string;
  lead_time_days: number;
  visit_type: 'new' | 'follow-up';
  age?: number;
  specialty?: string;
  patient_no_show_rate?: number;
  patient_visit_count?: number;
}

export interface PredictNoShowResponse {
  no_show_probability: number;
  risk_category: 'low' | 'medium' | 'high';
  explanation: Explanation;
  nl_explanation: string;
  used_fallback: boolean;
}

// Appointments
export interface AppointmentSlot {
  appointment_id: string;
  patient_id: string;
  scheduled_start: string;
  predicted_duration?: number;
  no_show_probability?: number;
  visit_type?: 'new' | 'follow-up';
  priority?: number;
}

export interface SimulationConstraints {
  work_start_hour?: number;
  work_end_hour?: number;
  lunch_start_hour?: number;
  lunch_duration_minutes?: number;
  buffer_minutes?: number;
}

// Day Simulation
export interface SimulateDayRequest {
  physician_id: string;
  date: string;
  appointments: AppointmentSlot[];
  constraints?: SimulationConstraints;
}

export interface SimulatedAppointment {
  appointment_id: string;
  patient_id: string;
  scheduled_start: string;
  predicted_start: string;
  predicted_end: string;
  delay_minutes: number;
  is_at_risk: boolean;
}

export interface SimulateDayResponse {
  physician_id: string;
  date: string;
  simulated_appointments: SimulatedAppointment[];
  total_waiting_time_minutes: number;
  max_delay_minutes: number;
  schedule_overrun_minutes: number;
  physician_idle_time_minutes: number;
  at_risk_count: number;
  recommendations: string[];
}

// Schedule Optimization
export interface OptimizeScheduleRequest {
  physician_id: string;
  date: string;
  appointments: AppointmentSlot[];
  constraints?: SimulationConstraints;
  alpha?: number;
  beta?: number;
  gamma?: number;
}

export interface OptimizedAppointment {
  appointment_id: string;
  patient_id: string;
  original_start: string;
  optimized_start: string;
  predicted_duration: number;
}

export interface OptimizeScheduleResponse {
  physician_id: string;
  date: string;
  optimized_appointments: OptimizedAppointment[];
  expected_total_waiting_time: number;
  expected_overrun_minutes: number;
  improvement_pct: number;
  is_optimal: boolean;
  nl_summary: string;
}

// Health
export interface HealthResponse {
  status: string;
  version: string;
  models: { duration_model: boolean; noshow_model: boolean };
  database: boolean;
}

// ── Daily Appointments Board ───────────────────────────────────────────────

export interface DayAppointment {
  appointment_id: string;
  patient_id: string;
  patient_name?: string | null;
  physician_id: string;
  date: string;
  scheduled_start: string;
  visit_type: 'new' | 'follow-up';
  specialty: string;
  age: number;
  comorbidity_count: number;
  priority: number;
  status: 'pending' | 'in_progress' | 'completed' | 'no_show';
  // Filled after AI assessment
  predicted_duration?: number | null;
  no_show_probability?: number | null;
  risk_category?: 'low' | 'medium' | 'high' | null;
  nl_duration_explanation?: string | null;
  nl_noshow_explanation?: string | null;
  duration_lower?: number | null;
  duration_upper?: number | null;
  duration_confidence?: number | null;
  assessed_at?: string | null;
  // Filled after simulate-day
  delay_minutes?: number | null;
  is_at_risk?: boolean | null;
  predicted_start?: string | null;
}

export interface DayAppointmentsResponse {
  physician_id: string;
  date: string;
  count: number;
  assessed_count: number;
  high_risk_count: number;
  appointments: DayAppointment[];
}

export interface AssessAllResponse {
  physician_id: string;
  date: string;
  assessed: number;
  errors: number;
  high_risk_count: number;
  total_predicted_minutes: number;
  appointments: DayAppointment[];
}

// ── Patients ──────────────────────────────────────────────────────────────

export interface Patient {
  id: number;
  patient_code: string;
  full_name: string;
  date_of_birth: string | null;
  gender: string | null;
  contact_phone: string | null;
  contact_email: string | null;
  address: string | null;
  created_at: string | null;
  visit_count: number;
  no_show_count: number;
  no_show_streak: number;
  days_since_last_visit: number | null;
}

export interface PatientCreate {
  full_name: string;
  date_of_birth?: string;
  gender?: string;
  contact_phone?: string;
  contact_email?: string;
  address?: string;
}

export interface VisitHistoryEntry {
  id: number;
  visit_date: string;
  visit_type: string;
  specialty: string | null;
  physician_id: string | null;
  attended: boolean;
  actual_duration: number | null;
  notes: string | null;
}

// ── Users ─────────────────────────────────────────────────────────────────

export interface UserOut {
  id: number;
  email: string;
  full_name: string;
  role: 'admin' | 'physician' | 'front_desk';
  physician_id: string | null;
  is_active: boolean;
}

export interface UpdateUserRequest {
  full_name?: string;
  role?: string;
  physician_id?: string;
  is_active?: boolean;
  password?: string;
}

// ── Appointments Create ───────────────────────────────────────────────────

export interface CreateAppointmentRequest {
  patient_id: string;
  patient_name?: string;
  physician_id: string;
  scheduled_start: string;
  visit_type: string;
  specialty: string;
  age: number;
  comorbidity_count: number;
  priority: number;
}
