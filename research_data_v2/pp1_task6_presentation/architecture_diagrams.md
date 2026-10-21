# Mermaid architecture sources

## Active production request flow

~~~mermaid
flowchart LR
  U[User event brief] --> F[React wizard]
  F --> API[FastAPI dynamic endpoint]
  API --> V[Validation and fresh USER ID]
  V --> O[(Current service-option rows)]
  O --> C[Eligible bounded candidate selection]
  C --> G[Bounded combination search]
  R[(Random Forest and review features)] --> Risk[Rule-risk favorability]
  M[(15 category matrix pairs)] --> Compat[Category compatibility]
  G --> Feas[Feasibility on examined packages]
  Risk --> Rank[Weighted ranking]
  Compat --> Rank
  Feas -->|Exclude FAIL; prioritize simulation pass| Rank
  Rank --> X[Evidence-grounded explanations and top-K]
  X --> UI[Recommendations, comparison, feasibility dashboard]
  UI -->|Current USER event and option IDs| DF[Dynamic feasibility API]
~~~

## Standalone work, outside the production path

~~~mermaid
flowchart LR
  T2[Task 2 pair evidence and conflict engine; synthetic fixtures] --> T3[Task 3 read-only shadow adapter]
  P[Production generator] -. copy output for assessment .-> T3
  P -. controlled comparison .-> T4[Task 4 isolated optimization prototype]
  T3 -. no writeback .-> P
  T4 -. not deployed .-> P
~~~

## Future team boundary

~~~mermaid
flowchart LR
  VI[Vendor intelligence event and package requirements] -. proposed interface .-> VT[External venue-team suitability service]
  VT -. future evidence and status .-> VI
  N[Venue Suitability / Digital Twin is owned by another team member; not active here] --- VT
~~~

Sources: [Task 5 discovery](../pp1_task5_demo_readiness/system_discovery.md), [Task 2 README](../pp1_task2_conflict_engine/README.md), [Task 3 README](../pp1_task3_shadow_integration/README.md), [Task 4 README](../pp1_task4_performance/README.md), [venue contract](../audit_2026-10-17_01/venue_integration_contract.md).