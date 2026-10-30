# PlanoVision â€“ Vendor Intelligence & Smart Package Recommendation Engine

### Smart Integrated Event Planning and Business Intelligence System

**Academic Research Prototype | IT4010 Research Project**

## Project Overview

PlanoVision is an intelligent event-planning research prototype designed to support event planners in selecting suitable combinations of vendors.

The system combines machine learning-based vendor intelligence, constraint-aware package generation, and multi-criteria recommendation techniques to support transparent vendor selection decisions.

The prototype is intended for academic research and demonstration, not for live vendor booking.

## Research Problem

Selecting multiple vendors for an event can be a complex and time-consuming process. Event planners must consider several factors, including:

- Budget limitations
- Vendor service categories
- Customer review information
- Event-specific requirements
- Compatibility between selected service categories

Traditional manual selection makes it difficult to compare complete vendor packages consistently.

## Proposed Solution

PlanoVision provides a structured decision-support workflow:

1. Collect event requirements from the user.
2. Identify candidate vendors and services.
3. Analyze review-derived vendor risk using a Random Forest classifier.
4. Generate multi-vendor packages using bounded Depth-First Search (DFS).
5. Rank candidate packages using weighted multi-criteria scoring.
6. Display recommendations and supporting explanations.

## Core Research Components

### 1. Vendor Risk Classification

**Algorithm:** Random Forest Classifier

**Features:**
- Stars
- Review count
- Collected review count
- Mean review rating
- Rating standard deviation

**Risk categories:** Low, Medium and High.

The classifier was evaluated using an 80/20 train-test split. It achieved 100% accuracy on the test labels used in the research.

**Important limitation:** These labels were derived from deterministic review-based rules rather than observed vendor failures. Therefore, this result does not establish 100% real-world vendor reliability prediction.

### 2. Smart Vendor Package Generation

The recommendation engine uses bounded Depth-First Search to construct combinations of candidate vendor services while considering event requirements.

The search is bounded to control computational complexity.

### 3. Multi-Criteria Package Ranking

Candidate packages are evaluated using three weighted criteria:

| Criterion | Weight |
|---|---:|
| Cost efficiency | 40% |
| Review-derived risk favorability | 40% |
| Category-based compatibility | 20% |

The final ranking is a weighted decision-support method, not a separately trained machine learning ranking model.

### 4. Application Workspaces

- **Event Planner:** Event requirement entry, feasibility checking and package recommendations.
- **Administrator:** Research-oriented administration, monitoring and reporting features.
- **Vendor Demo Portal:** Demonstration of vendor profile, service and availability management.

The vendor demo portal is separate from the research recommendation dataset and does not provide verified live vendor availability.

## Research Dataset

The prototype uses:

- **18,430** historical vendor profiles from a US Yelp-derived research dataset.
- **57,549** synthetic service options for simulation and package generation.

The research data is not a verified directory of currently available Sri Lankan vendors.

Some datasets and trained model files are excluded from the repository and may require separate preparation for reproducibility.

## Technology Stack

| Layer | Technologies |
|---|---|
| Frontend | React, Vite, JavaScript |
| Backend | Python, FastAPI |
| Database | SQLite |
| Machine Learning | Scikit-learn, Random Forest |
| Package Generation | Bounded Depth-First Search |
| Ranking | Weighted Multi-Criteria Scoring |
| Version Control | Git and GitHub |

## Repository Structure

```text
PlanoVision-Vendor-Intelligence/
â”œâ”€â”€ backend/
â”œâ”€â”€ frontend/
â”œâ”€â”€ hybrid_simulation_v1/
â”œâ”€â”€ notebooks/
â”œâ”€â”€ research_data_v2/
â”œâ”€â”€ research_evaluation/
â”œâ”€â”€ tests/
â”œâ”€â”€ docs/
â””â”€â”€ README.md
```

## Research Evaluation

The prototype has been evaluated using classification metrics, synthetic event scenarios, package generation tests and ranking comparisons.

The evaluation is primarily based on historical and simulated data. Results should not be interpreted as confirmed real-world vendor reliability, booking success or commercial performance.

## Current Limitations

- Review-derived risk labels are not actual vendor failure records.
- Service prices and availability are not verified live quotations.
- Compatibility scoring is based on service-category rules.
- Package recommendations require verification before real-world use.
- The vendor demonstration portal is not a production-ready authenticated marketplace.

## Future Improvements

- Train reliability prediction models using observed vendor performance outcomes.
- Integrate verified Sri Lankan vendor profiles and service quotations.
- Improve event scheduling and vendor conflict detection.
- Investigate learning-to-rank approaches using real user feedback.
- Conduct real-world usability and recommendation quality evaluations.

## Project Status

**Research and Development â€“ PP1 Prototype**

Developed as an individual research component within the Smart Integrated Event Planning and Business Intelligence System.

## Disclaimer

PlanoVision is an academic research prototype. Vendor recommendations are intended for experimental decision support and do not constitute verified bookings or guarantees of vendor performance.
