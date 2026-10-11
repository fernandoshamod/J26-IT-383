# PSPLIB j30 instances

480 standard single-mode RCPSP benchmark instances (`.sm` format), 30 real
activities each plus a dummy source and sink job, 4 renewable resource
types. This is the instance set the proposal names in Sections 3.4/3.6 and
Objective 6 for validating the scheduling engine's correctness and solve
time independently of the event domain.

Original source: Kolisch, R. and Sprecher, A., PSPLIB — A project
scheduling problem library, European Journal of Operational Research
(1997), hosted at the official PSPLIB site
(https://www.om-db.wi.tum.de/psplib/). That server was unreachable
(404) when this project needed the files, so this copy was obtained from
the `data/instances/sm/j30/` directory of
https://github.com/AlkisPlas/MPRJ_RCPSP, a public academic mirror
bundling the same standard files. The official optimal-solution file
(`j30opt.sm`) was not retrievable at the same time; see
`scheduling_engine/psplib.py` for how validation instead uses each
instance's own embedded critical-path lower bound ("MPM-Time") as a sanity
check, pending access to the official optimal values.

Format reference: each `.sm` file's own header documents its fields
inline. Parsed by `scheduling_engine/psplib.py::parse_sm`.
