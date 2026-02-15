# ChronoCare AI
## System Design Document

---

# 1. System Architecture Overview

ChronoCare AI consists of five main layers:

1. Data Layer
2. Feature Engineering Layer
3. Model Layer
4. Optimization Layer
5. Application Interface Layer

---

# 2. High-Level Architecture

```
+----------------------+
|   Application Layer  |
|  (Dashboard/API)     |
+----------+-----------+
           |
+----------v-----------+
|   Optimization Layer |
|  (Schedule Engine)   |
+----------+-----------+
           |
+----------v-----------+
|      Model Layer     |
|  Duration & No-show  |
+----------+-----------+
           |
+----------v-----------+
| Feature Engineering  |
+----------+-----------+
           |
+----------v-----------+
|       Data Layer     |
+----------------------+
```

---

# 3. Data Layer

## 3.1 Database Schema

### Patients Table
```sql
CREATE TABLE patients (
    patient_id VARCHAR(50) PRIMARY KEY,
    age INTEGER CHECK (age >= 0 AND age <= 120),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Physicians Table
```sql
CREATE TABLE physicians (
    physician_id VARCHAR(50) PRIMARY KEY,
    specialty VARCHAR(100) NOT NULL,
    department VARCHAR(100),
    avg_consultation_duration INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_specialty (specialty)
);
```

### Appointments Table
```sql
CREATE TABLE appointments (
    appointment_id VARCHAR(50) PRIMARY KEY,
    patient_id VARCHAR(50) REFERENCES patients(patient_id),
    physician_id VARCHAR(50) REFERENCES physicians(physician_id),
    appointment_time TIMESTAMP NOT NULL,
    visit_type VARCHAR(20) CHECK (visit_type IN ('new', 'follow-up')),
    specialty VARCHAR(100) NOT NULL,
    comorbidity_count INTEGER DEFAULT 0,
    actual_duration INTEGER,
    predicted_duration INTEGER,
    attended BOOLEAN,
    no_show_probability FLOAT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_physician_time (physician_id, appointment_time),
    INDEX idx_appointment_time (appointment_time)
);
```

### Visit History Table
```sql
CREATE TABLE visit_history (
    visit_id VARCHAR(50) PRIMARY KEY,
    patient_id VARCHAR(50) REFERENCES patients(patient_id),
    physician_id VARCHAR(50) REFERENCES physicians(physician_id),
    visit_date TIMESTAMP NOT NULL,
    duration INTEGER NOT NULL,
    visit_type VARCHAR(20),
    attended BOOLEAN NOT NULL,
    INDEX idx_patient (patient_id),
    INDEX idx_physician (physician_id)
);
```

## 3.2 Data Access Patterns

- Read-heavy workload (90% reads, 10% writes)
- Frequent queries: appointments by physician and date range
- Caching strategy: Redis for prediction results (TTL: 5 minutes)
- Connection pooling: Min 10, Max 50 connections

## 3.3 Data Retention

- Active appointments: 6 months
- Historical data: 2 years
- Prediction logs: 1 year
- Archived to cold storage after retention period

---

# 4. Feature Engineering Layer

## 4.1 Feature Pipeline

Transforms raw data into model-ready features using scikit-learn pipelines.

### Temporal Features
- hour_of_day: Extracted from appointment_time (0-23)
- day_of_week: Monday=0, Sunday=6
- is_morning: Boolean (before 12 PM)
- is_afternoon: Boolean (12 PM - 5 PM)

### Patient Features
- age_group: Binned (0-18, 19-35, 36-50, 51-65, 66+)
- comorbidity_count: Integer (0-10+)
- visit_type_encoded: One-hot encoding (new=1, follow-up=0)
- patient_visit_count: Historical visit count
- patient_avg_duration: Mean of past visit durations
- patient_no_show_rate: Historical no-show percentage

### Physician Features
- physician_avg_duration: Mean consultation time
- physician_workload_2h: Number of appointments in prior 2 hours
- physician_specialty_encoded: One-hot encoding
- physician_experience: Total appointments conducted

### Appointment Features
- lead_time_days: Days between booking and appointment
- appointment_sequence: Position in daily schedule (1st, 2nd, etc.)
- time_since_last_appointment: Minutes since previous appointment

## 4.2 Feature Preprocessing

- Numerical features: StandardScaler normalization
- Categorical features: One-hot encoding (max 10 categories)
- Missing values: Median imputation for numerical, mode for categorical
- Outlier handling: Winsorization at 1st and 99th percentiles

## 4.3 Feature Store

- Cached features stored in Redis
- Feature versioning for model reproducibility
- Feature monitoring for drift detection

---

# 5. Model Layer

## 5.1 Appointment Duration Model

### Model Selection
- Primary: LightGBM Regressor
- Rationale: Fast training, handles categorical features, built-in regularization

### Architecture
```python
LGBMRegressor(
    objective='regression',
    num_leaves=31,
    learning_rate=0.05,
    n_estimators=100,
    max_depth=6,
    min_child_samples=20,
    subsample=0.8,
    colsample_bytree=0.8
)
```

### Target
- Consultation duration (minutes)
- Range: 5-60 minutes

### Uncertainty Estimation
- Quantile regression for confidence intervals (10th and 90th percentiles)
- Outputs: [lower_bound, prediction, upper_bound]

### Evaluation Metrics
- Mean Absolute Error (MAE): Target < 5 minutes
- Root Mean Squared Error (RMSE): Target < 7 minutes
- R² Score: Target > 0.7
- Prediction interval coverage: Target 80%

### Training
- Training set: 70% of data
- Validation set: 15% of data
- Test set: 15% of data
- Cross-validation: 5-fold time-series split
- Retraining frequency: Quarterly or when MAE degrades >10%

---

## 5.2 No-Show Model

### Model Selection
- Primary: LightGBM Classifier
- Rationale: Handles class imbalance, provides probability calibration

### Architecture
```python
LGBMClassifier(
    objective='binary',
    num_leaves=31,
    learning_rate=0.05,
    n_estimators=100,
    max_depth=6,
    is_unbalance=True,
    scale_pos_weight=2.0
)
```

### Target
- Binary attendance outcome (0=no-show, 1=attended)

### Output
- Calibrated probability score (0.0-1.0)
- Risk category: Low (<0.2), Medium (0.2-0.4), High (>0.4)

### Evaluation Metrics
- AUC-ROC: Target > 0.75
- Precision-Recall AUC: Target > 0.65
- Calibration: Brier score < 0.15
- F1 Score at optimal threshold

### Class Imbalance Handling
- SMOTE oversampling for minority class
- Class weights adjustment
- Threshold tuning based on business cost

---

## 5.3 Doctor Fatigue Modeling

### Method
- Rolling window analysis (2-hour windows)
- Exponential moving average of consultation duration
- Change-point detection using CUSUM algorithm

### Indicators
- Duration drift: >15% increase from baseline
- Appointment overruns: >3 consecutive delays
- Workload intensity: >8 appointments in 2 hours

### Integration
- Fatigue score (0-1) fed into scheduling optimizer
- Suggests breaks when fatigue score >0.7
- Adjusts predicted durations upward during high fatigue

---

## 5.4 Model Serving

### Infrastructure
- Models serialized using joblib/pickle
- Served via FastAPI endpoints
- Model versioning with semantic versioning (v1.0.0)
- A/B testing framework for model comparison

### Caching
- Prediction cache in Redis (TTL: 5 minutes)
- Cache key: hash of input features
- Cache hit rate target: >60%

### Monitoring
- Prediction latency tracking
- Model drift detection (PSI, KL divergence)
- Feature distribution monitoring
- Automated alerts when metrics degrade

---

# 6. Optimization Layer

## 6.1 Schedule Simulation Engine

### Algorithm
- Discrete event simulation
- Time-step: 1 minute resolution
- Simulates full day (8 AM - 5 PM)

### Process
1. Initialize schedule with appointment start times
2. For each appointment:
   - Use predicted duration + buffer
   - Calculate actual start time (accounting for delays)
   - Propagate delay to next appointment
3. Output: Timeline with predicted delays

### Metrics Tracked
- Total waiting time (sum across all patients)
- Maximum delay
- Physician idle time
- Schedule overrun (minutes past end time)

---

## 6.2 Dynamic Scheduling Optimizer

### Optimization Approach
- Mixed Integer Linear Programming (MILP)
- Solver: Google OR-Tools CP-SAT

### Objective Function
```
Minimize: 
  α * total_waiting_time + 
  β * workload_variance + 
  γ * schedule_overrun
  
Where: α=0.5, β=0.3, γ=0.2 (configurable weights)
```

### Constraints
- Hard constraints:
  - Physician availability windows
  - Mandatory breaks (lunch, admin time)
  - Room availability
  - Minimum 5-minute buffer between appointments
  - No overlapping appointments for same physician

- Soft constraints (penalties):
  - Preferred appointment times
  - Patient travel time considerations
  - Appointment type sequencing (new patients in morning)

### Overbooking Strategy
- If no-show probability >0.5, allow overbooking
- Maximum overbooking: 1 appointment per 4-hour block
- Overbooking only for low-urgency appointments

### Rescheduling Logic
- Triggered when delay >20 minutes predicted
- Identifies low-priority appointments (follow-ups, low urgency)
- Suggests rescheduling with alternative time slots
- Requires human approval for execution

---

## 6.3 Real-Time Adjustment

### Triggers
- Appointment completes (update remaining schedule)
- Appointment exceeds predicted duration by >10 minutes
- No-show occurs
- Emergency appointment inserted

### Response
- Recalculate waiting times for remaining appointments
- Identify at-risk appointments (delay >15 minutes)
- Generate notifications for affected patients
- Suggest buffer adjustments

### Performance
- Recalculation time: <2 seconds
- Updates pushed via WebSocket to dashboard

---

# 7. Application Layer

Provides:
- Admin dashboard
- Physician dashboard
- Real-time schedule simulation view
- Patient waiting time estimate view

API Endpoints:
- /predict-duration
- /predict-no-show
- /simulate-day
- /optimize-schedule

---

# 8. Explainability Module

## 8.1 SHAP Integration

- SHAP (SHapley Additive exPlanations) for feature importance
- TreeExplainer for LightGBM models
- Computed on-demand for individual predictions

### Output Format
```json
{
  "prediction": 25,
  "explanation": {
    "base_value": 20,
    "features": [
      {"name": "comorbidity_count", "value": 3, "contribution": +4},
      {"name": "visit_type", "value": "new", "contribution": +2},
      {"name": "time_of_day", "value": 14, "contribution": -1}
    ]
  }
}
```

## 8.2 Human-Readable Explanations

Template-based natural language generation:

- "Longer duration predicted due to high comorbidity count (3) and first-time visit."
- "No-show risk elevated due to short lead time (2 days) and afternoon appointment."
- "Schedule optimized to reduce waiting time by 18 minutes by adjusting buffer times."

## 8.3 Uncertainty Visualization

- Confidence intervals displayed as error bars
- Color-coded risk levels (green/yellow/red)
- Prediction confidence score (0-100%)

## 8.4 Model Cards

- Document model purpose, limitations, and performance
- Bias audit results published
- Training data characteristics
- Intended use cases and restrictions

---

# 9. Responsible Design Measures

- Model uncertainty displayed
- No clinical recommendations
- Explicit "Scheduling Support Only" disclaimer
- Bias audit across:
  - Age groups
  - Specialties
  - Visit types

---

# 10. Deployment Design

## 10.1 Backend Architecture

### Technology Stack
- Language: Python 3.11+
- Web Framework: FastAPI 0.100+
- ASGI Server: Uvicorn with Gunicorn
- Task Queue: Celery with Redis broker
- ML Libraries: LightGBM, scikit-learn, SHAP, pandas, numpy

### Service Structure
```
backend/
├── api/
│   ├── routes/          # API endpoints
│   ├── models/          # Pydantic schemas
│   └── middleware/      # Auth, logging, CORS
├── ml/
│   ├── models/          # Trained model files
│   ├── predictors/      # Prediction logic
│   └── training/        # Training scripts
├── optimization/
│   ├── simulator.py     # Schedule simulation
│   └── optimizer.py     # MILP optimizer
├── database/
│   ├── models.py        # SQLAlchemy models
│   └── repositories.py  # Data access layer
└── utils/
    ├── cache.py         # Redis caching
    └── monitoring.py    # Metrics collection
```

### API Server Configuration
- Workers: 4 per CPU core
- Timeout: 30 seconds
- Max request size: 10 MB
- CORS: Configured for frontend domain

---

## 10.2 Database

### Primary Database
- PostgreSQL 15+
- Connection pooling: PgBouncer
- Replication: 1 primary, 2 read replicas
- Backup: Daily full backup, continuous WAL archiving

### Caching Layer
- Redis 7+
- Persistence: RDB snapshots every 5 minutes
- Eviction policy: LRU
- Memory: 4 GB allocated

---

## 10.3 Frontend

### Technology Stack
- Framework: React 18+ with TypeScript
- State Management: Redux Toolkit
- UI Library: Material-UI (MUI)
- Charts: Recharts for visualizations
- API Client: Axios with interceptors

### Pages
- Dashboard: Overview of daily schedules
- Physician View: Individual physician schedule
- Analytics: Performance metrics and trends
- Admin Panel: Configuration and user management

### Real-Time Updates
- WebSocket connection for live schedule updates
- Notification system for delay alerts
- Auto-refresh every 60 seconds

---

## 10.4 Containerization

### Docker Setup
```dockerfile
# Backend Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Docker Compose
```yaml
services:
  api:
    build: ./backend
    ports: ["8000:8000"]
    environment:
      - DATABASE_URL=postgresql://user:pass@db:5432/chronocare
      - REDIS_URL=redis://redis:6379
    depends_on: [db, redis]
  
  db:
    image: postgres:15
    volumes: ["postgres_data:/var/lib/postgresql/data"]
  
  redis:
    image: redis:7
    volumes: ["redis_data:/data"]
  
  frontend:
    build: ./frontend
    ports: ["3000:3000"]
```

### Kubernetes Deployment (Production)
- API: 3 replicas with horizontal pod autoscaling
- Database: StatefulSet with persistent volumes
- Redis: StatefulSet with persistence
- Ingress: NGINX with TLS termination
- Monitoring: Prometheus + Grafana

---

# 11. Error Handling & Resilience

## 11.1 Error Handling Strategy

### API Errors
- 400 Bad Request: Invalid input data with field-level validation errors
- 401 Unauthorized: Missing or invalid API key
- 404 Not Found: Resource doesn't exist
- 429 Too Many Requests: Rate limit exceeded
- 500 Internal Server Error: Unexpected server error
- 503 Service Unavailable: Dependency failure (DB, Redis, ML model)

### Error Response Format
```json
{
  "error": {
    "code": "INVALID_INPUT",
    "message": "Patient age must be between 0 and 120",
    "details": {"field": "age", "value": 150},
    "request_id": "req_abc123",
    "timestamp": "2026-02-15T10:30:00Z"
  }
}
```

## 11.2 Fallback Mechanisms

### Model Unavailable
- Fallback to rule-based predictions:
  - Duration: Use specialty average
  - No-show: Use historical baseline (15%)
- Log fallback usage for monitoring

### Database Connection Failure
- Retry with exponential backoff (3 attempts)
- Circuit breaker pattern (open after 5 failures)
- Return cached data if available
- Graceful degradation message to user

### Optimization Timeout
- If optimizer doesn't converge in 10 seconds:
  - Return greedy heuristic schedule
  - Flag as "suboptimal" in response

## 11.3 Logging

### Log Levels
- DEBUG: Detailed diagnostic information
- INFO: General operational events
- WARNING: Unexpected but handled situations
- ERROR: Error events that need attention
- CRITICAL: System-level failures

### Structured Logging
```json
{
  "timestamp": "2026-02-15T10:30:00Z",
  "level": "INFO",
  "service": "prediction-api",
  "request_id": "req_abc123",
  "user_id": "user_456",
  "endpoint": "/predict-duration",
  "duration_ms": 245,
  "status_code": 200
}
```

### Log Aggregation
- Centralized logging with ELK stack (Elasticsearch, Logstash, Kibana)
- Retention: 30 days for application logs, 90 days for audit logs

---

# 12. Testing Strategy

## 12.1 Unit Testing
- Framework: pytest
- Coverage target: >80%
- Test isolation: Mock external dependencies
- Focus areas:
  - Feature engineering functions
  - Prediction logic
  - API input validation
  - Database queries

## 12.2 Integration Testing
- Test API endpoints end-to-end
- Test database transactions
- Test model loading and prediction
- Test caching behavior

## 12.3 Model Testing
- Backtesting on historical data
- A/B testing framework for model comparison
- Prediction quality monitoring
- Bias testing across demographic groups

## 12.4 Performance Testing
- Load testing: 1000 concurrent requests
- Stress testing: Identify breaking point
- Latency testing: p95, p99 response times
- Tools: Locust, Apache JMeter

## 12.5 Security Testing
- Penetration testing quarterly
- Dependency vulnerability scanning (Snyk, Dependabot)
- SQL injection prevention testing
- API authentication testing

---

# 13. Monitoring & Maintenance

## 13.1 Application Monitoring

### Metrics Tracked
- Request rate (requests/second)
- Response time (p50, p95, p99)
- Error rate (errors/total requests)
- Cache hit rate
- Database connection pool usage

### Tools
- Prometheus for metrics collection
- Grafana for dashboards
- AlertManager for alerting

### Alerts
- API response time >1 second (p95)
- Error rate >5%
- Database connection pool >80% utilized
- Model prediction latency >500ms

## 13.2 Model Monitoring

### Drift Detection
- Feature distribution monitoring (PSI score)
- Prediction distribution monitoring
- Target drift detection (actual vs predicted)
- Alert when PSI >0.2 or MAE increases >15%

### Performance Tracking
- Daily MAE calculation on completed appointments
- Weekly model performance report
- Quarterly model retraining evaluation

### Bias Monitoring
- Prediction accuracy by age group
- Prediction accuracy by specialty
- Fairness metrics (demographic parity, equal opportunity)
- Monthly bias audit report

## 13.3 Maintenance Schedule

### Daily
- Health check monitoring
- Error log review
- Performance metrics review

### Weekly
- Model performance evaluation
- Database query optimization review
- Security log audit

### Monthly
- Bias audit report
- Capacity planning review
- Dependency updates

### Quarterly
- Model retraining evaluation
- Security penetration testing
- Disaster recovery drill
- Performance optimization review

---

# 14. Security Considerations

## 14.1 Data Security
- All data anonymized (no real patient data)
- Encryption at rest (AES-256)
- Encryption in transit (TLS 1.3)
- Database access restricted by IP whitelist

## 14.2 API Security
- API key authentication
- Rate limiting per API key
- CORS configuration for allowed origins
- Input validation and sanitization
- SQL injection prevention (parameterized queries)

## 14.3 Infrastructure Security
- Network segmentation (VPC)
- Firewall rules (allow only necessary ports)
- Regular security patches
- Secrets management (AWS Secrets Manager, HashiCorp Vault)
- Audit logging for all access

## 14.4 Compliance
- GDPR compliance (data anonymization, right to deletion)
- HIPAA considerations (though using synthetic data)
- SOC 2 Type II audit preparation
- Regular security assessments

---

# 15. Disaster Recovery

## 15.1 Backup Strategy
- Database: Daily full backup, continuous WAL archiving
- Models: Versioned in S3 with lifecycle policies
- Configuration: Version controlled in Git
- Recovery Time Objective (RTO): 4 hours
- Recovery Point Objective (RPO): 1 hour

## 15.2 High Availability
- Multi-AZ deployment
- Load balancer with health checks
- Auto-scaling groups
- Database replication (primary + 2 replicas)

## 15.3 Incident Response
- On-call rotation for critical issues
- Incident severity levels (P0-P4)
- Runbooks for common issues
- Post-mortem process for major incidents

---

# 16. Future Enhancements

- Reinforcement learning scheduling
- Cross-department optimization
- Real-time EMR integration
- Multi-hospital benchmarking
