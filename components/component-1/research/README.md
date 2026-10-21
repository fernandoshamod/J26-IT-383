# Full research source beyond the portable application

`workspace/` preserves original relative source paths for model training/evaluation, baseline comparisons, review selection, function usability, feasibility recovery and diagnosis benchmark experiments. These originals are separate from portable runtime patches under `../app/`. They may depend on excluded historical output trees, original modules or private datasets. They are not installed or executed by the four-service launcher and have not been independently reproduced from this staged directory.

No model retraining was performed. No historical generated output or private venue pixels are included. Colab notebooks have all stored outputs, execution counts, attachments and non-kernel metadata removed; transformations are recorded in provenance. Notebook helper code retains its package-relative layout; actual remote Colab execution and private Drive completeness remain unverified.
