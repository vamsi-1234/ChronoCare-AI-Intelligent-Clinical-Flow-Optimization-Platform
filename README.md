# ChronoCare AI

> Intelligent Clinical Flow Optimization Platform

ChronoCare AI is a predictive clinical workflow optimization system that uses machine learning to improve hospital scheduling efficiency, reduce patient waiting times, and balance physician workload.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)

## 🎯 Key Features

- **Appointment Duration Prediction**: ML-powered predictions with uncertainty estimation
- **No-Show Risk Assessment**: Identify high-risk appointments to optimize overbooking
- **Dynamic Delay Simulation**: Real-time cascade delay forecasting throughout the day
- **Adaptive Scheduling**: AI-driven schedule optimization balancing multiple objectives
- **Explainable AI**: SHAP-based explanations for all predictions
- **Real-Time Updates**: Live schedule adjustments as appointments complete

## 🏥 Problem Statement

Hospitals face significant scheduling challenges:
- Fixed-duration appointments causing cascading delays
- Physician overload and uneven workload distribution
- High no-show rates (15-30% industry average)
- Poor waiting time transparency for patients

ChronoCare AI addresses these inefficiencies through data-driven scheduling intelligence.

## 📊 Performance Targets

| Metric | Target |
|--------|--------|
| Duration Prediction MAE | < 5 minutes |
| No-Show Prediction AUC | > 0.75 |
| API Response Time (p95) | < 500ms |
| Schedule Optimization | < 5 seconds |
| System Uptime | 99.5% |

## 🏗️ Architecture

```
┌─────────────────────────────────────┐
│      Application Layer (React)      │
│         Dashboard & API UI          │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│     Optimization Layer (OR-Tools)   │
│      Schedule Simulation Engine     │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│      Model Layer (LightGBM)         │
│   Duration & No-Show Prediction     │
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│   Feature Engineering (scikit-learn)│
└──────────────┬──────────────────────┘
               │
┌──────────────▼──────────────────────┐
│    Data Layer (PostgreSQL + Redis)  │
└─────────────────────────────────────┘
```

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker & Docker Compose (optional)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/your-org/chronocare-ai.git
cd chronocare-ai
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Initialize database:
```bash
python scripts/init_db.py
```

6. Generate synthetic data:
```bash
python scripts/generate_synthetic_data.py --appointments 1000
```

7. Train models:
```bash
python scripts/train_models.py
```

8. Start the API server:
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

9. Access the API documentation:
```
http://localhost:8000/docs
```

### Docker Quick Start

```bash
docker-compose up -d
```

This will start:
- API server on `http://localhost:8000`
- Frontend on `http://localhost:3000`
- PostgreSQL on `localhost:5432`
- Redis on `localhost:6379`

## 📚 API Endpoints

### Prediction Endpoints

**Predict Appointment Duration**
```bash
POST /api/v1/predict-duration
Content-Type: application/json

{
  "patient_id": "P12345",
  "age": 45,
  "visit_type": "follow-up",
  "specialty": "cardiology",
  "comorbidity_count": 2,
  "physician_id": "D001"
}
```

**Predict No-Show Risk**
```bash
POST /api/v1/predict-no-show
Content-Type: application/json

{
  "patient_id": "P12345",
  "appointment_time": "2026-02-20T14:00:00Z",
  "lead_time_days": 7,
  "visit_type": "new"
}
```

### Optimization Endpoints

**Simulate Daily Schedule**
```bash
POST /api/v1/simulate-day
Content-Type: application/json

{
  "physician_id": "D001",
  "date": "2026-02-20",
  "appointments": [...]
}
```

**Optimize Schedule**
```bash
POST /api/v1/optimize-schedule
Content-Type: application/json

{
  "physician_id": "D001",
  "date": "2026-02-20",
  "appointments": [...],
  "constraints": {...}
}
```

See full API documentation at `/docs` when running the server.

## 🧪 Testing

Run the test suite:
```bash
# Unit tests
pytest tests/unit -v

# Integration tests
pytest tests/integration -v

# All tests with coverage
pytest --cov=. --cov-report=html
```

## 📈 Model Training

### Training Duration Model

```bash
python scripts/train_duration_model.py \
  --data data/appointments.csv \
  --output models/duration_model_v1.pkl \
  --validate
```

### Training No-Show Model

```bash
python scripts/train_noshow_model.py \
  --data data/appointments.csv \
  --output models/noshow_model_v1.pkl \
  --validate
```

### Model Evaluation

```bash
python scripts/evaluate_models.py \
  --duration-model models/duration_model_v1.pkl \
  --noshow-model models/noshow_model_v1.pkl \
  --test-data data/test_set.csv
```

## 🔧 Configuration

Key configuration options in `.env`:

```bash
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/chronocare

# Redis
REDIS_URL=redis://localhost:6379

# API
API_KEY_HEADER=X-API-Key
RATE_LIMIT_PER_MINUTE=100

# Models
DURATION_MODEL_PATH=models/duration_model_v1.pkl
NOSHOW_MODEL_PATH=models/noshow_model_v1.pkl

# Optimization
OPTIMIZATION_TIMEOUT_SECONDS=10
ALPHA_WAITING_TIME=0.5
BETA_WORKLOAD_VARIANCE=0.3
GAMMA_SCHEDULE_OVERRUN=0.2
```

## 📊 Monitoring

### Metrics Dashboard

Access Grafana dashboard at `http://localhost:3001` (when using Docker Compose)

Key metrics monitored:
- API request rate and latency
- Model prediction accuracy
- Cache hit rate
- Database connection pool usage
- Error rates

### Model Monitoring

```bash
# Check model drift
python scripts/check_model_drift.py --days 7

# Generate performance report
python scripts/generate_model_report.py --output reports/weekly_report.html
```

## 🔒 Security

- **No Real Patient Data**: System uses only synthetic or anonymized data
- **API Authentication**: API key-based authentication required
- **Rate Limiting**: 100 requests/minute per API key
- **Encryption**: TLS 1.3 for data in transit, AES-256 for data at rest
- **Audit Logging**: All API access logged for security review

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 Documentation

- [Requirements Document](.kiro/specs/chronocare-ai/requirements.md)
- [Design Document](.kiro/specs/chronocare-ai/design.md)
- [API Documentation](http://localhost:8000/docs) (when server is running)
- [Model Cards](docs/model_cards/)

## 🗺️ Roadmap

- [x] Core prediction models (duration, no-show)
- [x] Schedule optimization engine
- [x] REST API with FastAPI
- [ ] Real-time WebSocket updates
- [ ] Advanced bias monitoring dashboard
- [ ] Reinforcement learning scheduler
- [ ] Multi-hospital optimization
- [ ] Mobile app for physicians
- [ ] Patient notification system

## ⚠️ Limitations

- Based on synthetic data (not validated on real clinical data)
- Performance depends on data quality and representativeness
- Does not replace human judgment in scheduling decisions
- Cannot predict rare emergency disruptions
- Not intended for diagnostic or clinical decision-making

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Synthetic data generation inspired by healthcare scheduling research
- ML models built with LightGBM and scikit-learn
- Optimization powered by Google OR-Tools
- Explainability via SHAP (SHapley Additive exPlanations)

## 📧 Contact

- Project Lead: [your-email@example.com](mailto:your-email@example.com)
- Issues: [GitHub Issues](https://github.com/your-org/chronocare-ai/issues)
- Discussions: [GitHub Discussions](https://github.com/your-org/chronocare-ai/discussions)

---

**Disclaimer**: ChronoCare AI is a decision-support tool for scheduling optimization only. It does not provide medical diagnosis, treatment recommendations, or clinical decision-making. All scheduling decisions should be reviewed by qualified healthcare administrators.
