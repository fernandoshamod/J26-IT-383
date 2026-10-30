# PlanoVision

### Smart Integrated Event Planning and Business Intelligence System

**Research Group:** J26-IT-383  
**Specialization:** Information Technology (IT)  
**Institution:** Sri Lanka Institute of Information Technology (SLIIT)  
**Research Batch:** July 2026  
**Current Milestone:** Progress Presentation 1 (PP1) Completed

---

## 1. Project Overview

**PlanoVision** is an AI-driven event planning and business intelligence research platform designed to assist professional event planners with venue analysis, vendor selection, resource scheduling, operational coordination, and financial decision-making.

The research project consists of four individual components, each addressing a specific challenge in event planning through artificial intelligence, machine learning, optimization, and software engineering.

The system is currently at the PP1 research and prototype development stage. Full integration and real-world validation are not yet complete.

## 2. Research Team

| Component | Researcher | Student ID |
|---|---|---|
| Component 1 | Fernando W. S. V. | IT23284302 |
| Component 2 | Ahinsi K. R. N. | IT23292390 |
| Component 3 | Gamage J. H. A. D. N. | IT23288362 |
| Component 4 | Weerasekara T. P. | IT23282490 |

---

## 3. Research Components

### 3.1 Component 1 — AI-Powered Venue Understanding and Context-Aware Adaptive Event Layout Intelligence

**Research Stage:** Original PP1 research completed; scope revision pending panel approval.

#### Research Problem

Event planners face challenges when interpreting venue layouts, evaluating client requirements, managing spatial constraints, and adapting event arrangements when requirements change.

The original research investigated the application of artificial intelligence and optimization algorithms to venue understanding and event layout design.

#### Research Objectives

- Investigate AI-based venue structure recognition.
- Develop a structured representation of venue information using a Spatial Digital Twin approach.
- Analyze contextual event and venue requirements.
- Explore multi-objective event layout optimization.
- Investigate adaptive changes while preserving approved arrangements.
- Examine explainable decision-making for venue and layout changes.

#### Research Methodology

The original PP1 research explored the following techniques:

- **U-Net:** Structural segmentation of venue images.
- **YOLO:** Venue opening and object detection experiments.
- **Spatial Digital Twin:** Structured venue representation with evidence and planner-review requirements.
- **NSGA-II:** Multi-objective event layout optimization.
- **EAG-APR:** Evidence- and Authority-Governed Adaptive Pareto Repair for controlled layout changes.
- **Context-Aware Constraints:** Representation of client, planner, and venue requirements.

#### PP1 Implementation

During the PP1 stage, the following research and development work was undertaken:

- Venue-understanding dataset preparation.
- AI model training and inference experiments.
- Structural segmentation and object-detection experiments.
- Controlled synthetic layout optimization.
- Adaptive layout repair experiments.
- Development of a React and FastAPI research prototype.
- Event management functionality.
- Experimental testing and technical validation.

#### Technologies

Python, PyTorch, U-Net, YOLO, NSGA-II, React, FastAPI, SQLite.

#### Research Limitations and Current Status

The PP1 evaluation identified significant limitations in the original research approach, particularly insufficient novelty between the two-dimensional venue-plan input and the two-dimensional event-arrangement output.

The prototype also had limitations involving real-world venue validation, practical applicability, and independent evaluation.

The original research direction is not being continued as the active Component 1.

A replacement research scope has been proposed following academic supervisory discussions and is awaiting formal panel approval.

The updated research objectives, methodology, and implementation will be documented after approval.

---

### 3.2 Component 2 — Vendor Intelligence and Smart Package Recommendation Engine

**Research Stage:** PP1 research prototype completed.

#### Research Problem

Event planners often need multiple vendors to satisfy event requirements simultaneously. Independent vendor selection can result in incomplete service coverage, incompatible packages, budget violations, or unsuitable vendor combinations.

#### Research Objectives

- Identify vendor candidates based on event requirements.
- Evaluate vendor profile information and risk indicators.
- Analyze service-category compatibility.
- Generate suitable combinations of vendors.
- Apply budget and feasibility constraints.
- Rank alternative vendor packages.
- Provide transparent recommendation explanations.

#### Research Methodology

The component uses an integrated vendor-package generation workflow.

- **Random Forest:** Vendor risk-signal classification using profile and review-related features.
- **Candidate Filtering:** Selection based on event type, location, services, and capacity.
- **Compatibility Scoring:** Evaluation of service-category relationships.
- **Bounded Depth-First Search:** Generation of vendor-package combinations within computational limits.
- **Feasibility Validation:** Checking service coverage, budget, and supported constraints.
- **Weighted Ranking:** Comparing eligible packages using cost, risk signals, and compatibility factors.

#### PP1 Implementation

- React and Vite frontend.
- FastAPI backend.
- SQLite event persistence.
- Vendor candidate selection.
- Random Forest inference.
- Vendor compatibility assessment.
- Bounded package generation.
- Budget and feasibility validation.
- Package ranking and recommendation explanations.
- Research and administration interfaces.
- Synthetic scenario evaluation.

#### Technologies

React, Vite, Python, FastAPI, Pydantic, pandas, scikit-learn, Random Forest, joblib, SQLite.

#### Current Limitations

The research prototype uses synthetic or simulation-derived service prices, capacity information, availability, and collaboration scenarios.

The risk model uses rule-derived labels rather than independently observed vendor failure outcomes.

Live vendor availability, verified quotations, real-world recommendation accuracy, and production-level security remain outside the validated implementation.

---

### 3.3 Component 3 — Event Planning and Dynamic Resource Optimization

**Research Stage:** PP1 research implementation and experimental evaluation completed.

#### Research Problem

Traditional event schedules can be disrupted by activity delays, unexpected changes, and shared-resource conflicts. Static scheduling approaches may not adequately support real-time monitoring and recovery.

This component investigates intelligent event scheduling, operational state monitoring, and adaptive resource optimization.

#### Research Objectives

- Generate resource-constrained event schedules.
- Detect scheduling and resource conflicts.
- Estimate activity durations and vendor lateness.
- Monitor event execution through operational check-ins.
- Detect deviations from planned schedules.
- Simulate disruption effects.
- Re-optimize unfinished activities while respecting planner constraints.
- Provide operational cost-impact signals for financial analysis.

#### Research Methodology

The component combines machine learning, constraint programming, operational monitoring, and simulation.

- **OR-Tools CP-SAT:** Constraint-based scheduling and resource allocation.
- **XGBoost:** Activity-duration prediction and vendor-lateness classification.
- **Operational Digital Twin:** Tracking activity execution through check-in information.
- **Divergence Detection:** Identifying late or missing activity confirmations.
- **SimPy:** Discrete-event simulation of disruption propagation.
- **Adaptive Re-optimization:** Adjusting remaining schedules while respecting locked activities.
- **SHAP:** Explaining machine learning predictions.

#### PP1 Implementation

- Python-based scheduling engine.
- Resource allocation and conflict detection.
- PSPLIB benchmark validation.
- Activity and vendor-lateness prediction experiments.
- Check-in-based operational monitoring.
- Disruption detection and simulation.
- CP-SAT re-optimization.
- Planner confirmation workflow.
- Operational API and demonstration dashboard.
- Mobile-oriented staff/vendor check-in interface.
- Scenario-based experimental evaluation.

#### Technologies

Python, OR-Tools CP-SAT, XGBoost, SimPy, SHAP, FastAPI, pytest.

#### Current Limitations

The event-specific prediction models were trained primarily using synthetic event histories.

Public datasets were used to investigate selected assumptions, but they do not establish event-specific real-world prediction accuracy.

The main disruption evaluation focuses on activity overruns. Additional disruption types, stronger statistical comparisons, independent practitioner validation, and full cross-component integration remain future work.

---

### 3.4 Component 4 — Spatial-Financial Intelligence and Budget Optimization

**Research Stage:** PP1 research prototype and experimental evaluation completed.

#### Research Problem

Event planners must balance event expenditure, expected revenue, budget constraints, and profit margins while responding to changing client requirements and supplier costs.

Traditional cost estimation alone may not sufficiently explain the financial implications of event changes.

This component investigates financial decision support through budget analysis, machine learning, and controlled what-if comparisons.

#### Research Objectives

- Develop structured event cost and revenue calculations.
- Evaluate budget-overrun and profit-margin risks.
- Analyze the financial effects of event requirements.
- Compare original and modified event plans.
- Provide financial explanations and reporting.
- Support planner-controlled financial decisions.
- Explore financial information exchange with other research components.

#### Research Methodology

The component uses a combination of financial calculations and machine learning.

- **Financial Calculation Engine:** Itemized cost, revenue, reserve, and profit-margin calculations.
- **XGBoost:** Budget-overrun and profit-margin risk classification.
- **TreeSHAP:** Model prediction explanations.
- **What-If Analysis:** Comparison of proposed financial changes against the original plan.
- **Rule-Based Financial Health Analysis:** Financial planning indicators.
- **Scenario Evaluation:** Testing financial behavior under synthetic LKR scenarios.

#### PP1 Implementation

- React and TypeScript financial dashboard.
- Python backend and financial calculation engine.
- Financial Planner interface.
- What-If analysis interface.
- Financial reports and explanation views.
- Budget-overrun and profit-margin risk models.
- Saved-model inference.
- TreeSHAP-based explanations.
- Controlled preview and confirmation workflow.
- SQLite-based local event persistence.
- Financial model evaluation and testing.

#### Dataset and Evaluation

The supplied Component 4 documentation describes a research dataset containing **3,600 synthetic LKR financial scenarios**.

Recorded model evaluation results include:

- Budget-overrun classification accuracy: **95.56%**
- Profit-margin risk classification accuracy: **93.19%**

These results were obtained from synthetic evaluation data and do not represent independently verified performance on actual event outcomes.

#### Technologies

React, TypeScript, Vite, Python, SQLite, XGBoost, TreeSHAP, financial calculation algorithms, and research testing tools.

#### Current Limitations

- Risk classifiers are trained on synthetic financial scenarios.
- Financial health scoring uses defined rules rather than trained prediction.
- Actual supplier quotations and financial outcomes have not been independently verified.
- Complete model inference requires matching saved model artifacts.
- Full cross-component integration and real-world financial validation remain future research work.
- The prototype is not a production financial or booking platform.

---

## 4. Overall System Architecture

PlanoVision is designed around four complementary research areas.

**Event Requirements and Planning Information**
- Component 1: Venue understanding and event-design research conducted during PP1; replacement scope pending approval.
- Component 2: Vendor selection and package intelligence.
- Component 3: Activity scheduling and operational resource optimization.
- Component 4: Financial analysis and budget optimization.

### Intended Information Flow

1. Event requirements are collected and represented.
2. Vendor Intelligence evaluates candidate service packages.
3. Dynamic Resource Optimization manages activity schedules and resource constraints.
4. Financial Intelligence evaluates budgets, expected costs, and financial risks.
5. Operational changes may produce delay and overtime information for financial evaluation.
6. Component 1 integration will be redefined following academic approval of the replacement research scope.

These connections represent the intended system architecture. Complete end-to-end integration is not yet claimed.

---

## 5. Technology Stack

| Research Component | Technologies and Algorithms |
|---|---|
| Component 1 — Original PP1 | Python, PyTorch, U-Net, YOLO, NSGA-II, EAG-APR, React, FastAPI |
| Component 2 | React, Vite, FastAPI, Random Forest, SQLite, bounded search |
| Component 3 | Python, CP-SAT, XGBoost, SimPy, SHAP, FastAPI |
| Component 4 | React, TypeScript, Vite, Python, XGBoost, TreeSHAP, SQLite |

### Development Tools

- Git and GitHub
- Visual Studio Code
- Python development tools
- Node.js and npm
- API development and testing tools
- Machine learning and optimization libraries

---

## 6. GitHub Repository

**Repository:** https://github.com/fernandoshamod/J26-IT-383

The group repository maintains research development across component-specific Git branches.

Each research component may have its own source structure, dependencies, experiments, tests, and documentation.

The main branch provides the overall project README. Individual component branches contain their respective research implementations.

### Component Source Organization

**Component 2**
- `frontend/`
- `backend/`
- `models/`
- `data/`
- `research_evaluation/`
- `tests/`

**Component 3**
- `scheduling_engine/`
- `api/`
- `examples/`
- `notebooks/`
- `tests/`
- `results/`

**Component 4**
- `frontend/`
- `backend/`
- `component4/`
- `api/contracts/`
- `config/`
- `scripts/`
- `tests/`

**Component 1**

frontend/ — React/Vite frontend for event management, venue interaction, and layout optimization.

backend/ — Python backend APIs and event management services.

models/ — Venue understanding models, including U-Net structural segmentation and YOLO detection.

data/ — Venue datasets, annotations, and training data.

optimization/ — NSGA-II multi-objective event layout optimization.

adaptive_repair/ — EAG-APR adaptive layout repair and constraint handling.

scene_compiler/ — Venue scene processing and structured spatial representation.

tests/ — Research prototype testing and validation.

research/ — Model training, experimentation, and evaluation.

The original PP1 research implementation and experimental work form part of the research history. The future component structure will be established following approval of the revised research scope.

---

## 7. Installation and Development

The four components currently use separate development environments. A verified single-command installation for the complete integrated platform is not yet available.

### Component 2 — Vendor Intelligence

**Frontend:**

```powershell
cd frontend
npm ci
npm run dev
```

The backend uses FastAPI and a prepared Python environment.

```powershell
.\venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

The backend environment and required dependencies must be configured before execution.

### Component 3 — Dynamic Resource Optimization

From the Component 3 research branch:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m pytest tests/ -v
python -m examples.run_example
```

To run its operations API:

```powershell
python -m uvicorn api.app:app --host 127.0.0.1 --port 8000
```

### Component 4 — Financial Intelligence

From the Component 4 project root, using Python 3.12 x64 and a compatible Node.js installation:

```powershell
npm install
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r backend/requirements.txt
npm run dev
```

Documented development addresses:

- Frontend: `http://127.0.0.1:5173`
- Backend: `http://127.0.0.1:8765`

Complete model inference additionally requires the matching research datasets and saved model artifacts excluded from the source-only distribution.

### Component 1 — Original PP1

The original Component 1 used an independent React/FastAPI prototype and AI research environment.


The Component 1 PP1 research prototype was developed using a React/Vite frontend, Python backend services, SQLite, and AI-based venue understanding models.

**Frontend:**

From the Component 1 project directory containing the frontend application:

```powershell
cd frontend
npm install
npm run dev
```

**Backend:**

The backend uses Python and FastAPI with a configured virtual environment and the component's required dependencies.

**Research modules:**

- **U-Net and YOLO:** Venue structure understanding and detection experiments.
- **Spatial Digital Twin:** Structured venue representation and planner-review workflow.
- **NSGA-II:** Multi-objective event layout optimization.
- **EAG-APR:** Constraint-aware adaptive layout repair.
- **SQLite:** Local event data management.

Trained model checkpoints and relevant research data are required for AI inference. The complete application setup depends on the Component 1 source configuration and installed Python dependencies.

The PP1 implementation includes experimental AI inference, event management, controlled layout optimization, and adaptive repair. Real-world venue validation and complete system integration remain outside the verified PP1 scope.

Since the original research scope is being replaced, the former implementation is documented as PP1 research work rather than the active final component.

---

## 8. PP1 Research Progress

| Component | PP1 Research Progress |
|---|---|
| Component 1 | Venue understanding, AI inference experiments, spatial representation, controlled layout optimization, adaptive repair and prototype development |
| Component 2 | Vendor filtering, risk-signal inference, compatibility analysis, bounded package generation, feasibility checks and ranking |
| Component 3 | Scheduling engine, operational digital twin, disruption simulation, predictive models and adaptive re-optimization |
| Component 4 | Financial planner, budget-risk models, what-if analysis, model explanations, reporting and synthetic evaluation |

All four components conducted research and prototype development during the PP1 stage.

The completion of PP1 does not mean that all components are production-ready or fully integrated.

---

## 9. Research Limitations

The overall project currently has the following research limitations:

- Several research components use synthetic or simulation-derived datasets.
- Independent real-world validation remains incomplete.
- Some functionality is demonstrated through controlled research prototypes.
- Full integration between components has not been established.
- Production-level authentication, security, and deployment require further development.
- The original Component 1 approach requires replacement due to insufficient research novelty and practical research limitations.

These limitations will inform future research development and evaluation.

---

## 10. Future Development

### Component 1
- Obtain formal panel approval for the revised research component.
- Define the approved research problem, objectives, and methodology.
- Begin development and validation of the approved replacement research.

### Component 2
- Improve vendor risk evaluation using independent outcome data.
- Extend vendor availability and quotation verification.
- Improve compatibility and requirement matching.
- Strengthen recommendation validation and integration.

### Component 3
- Improve statistical evaluation.
- Investigate additional disruption types.
- Extend concurrent-event experiments.
- Strengthen cross-component integration and practitioner evaluation.

### Component 4
- Improve financial model robustness.
- Validate financial predictions using real event outcomes where available.
- Extend verified quotation and operational information interfaces.
- Improve financial reporting and real-world evaluation.

### Group-Level Development
- Integrate research components through documented interfaces.
- Conduct further software and research testing.
- Complete PP2 research evaluations.
- Prepare the final integrated research demonstration.

---

## 11. Academic Research Status

**Research Group:** J26-IT-383  
**Research Project:** Smart Integrated Event Planning and Business Intelligence System  
**Research Stage:** PP1 Completed  
**Specialization:** Information Technology  
**Institution:** Sri Lanka Institute of Information Technology

This repository contains academic research prototypes and experimental implementations. Reported results must be interpreted within their stated research datasets, methods, and validation limitations.

The revised scope of Component 1 will be documented following formal academic panel approval.
