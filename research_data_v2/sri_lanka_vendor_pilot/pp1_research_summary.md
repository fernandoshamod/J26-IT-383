# PP1 Sri Lankan vendor pilot: research summary

**State on 19 October 2026:** A schema and read-only validator exist, but **no Sri Lankan vendors were collected**. Counts: Photography 0/20, Decoration 0/20, Catering 0/20, Entertainment 0/20, Audio Visual 0/20; **0/100 total**. Targets are planning goals, not observed coverage.

The three wedding/event directories expose useful category and locality information, but this audit did not establish permission for bulk reuse. OpenStreetMap data is reusable under ODbL with attribution and share-alike obligations; bounded Overpass access attempts failed with TLS/HTTP errors. No ratings, prices, capacities, review statistics, service areas or availability were invented to fill the gap.

The current FastAPI service reads only the existing US-derived profiles and synthetic service options. It does not read this pilot CSV. The saved Random Forest requires five complete review features and was not retrained or altered. Therefore this pilot cannot yet generate evidence-based Sri Lankan packages or risk predictions.

For PP1, show the working existing recommendation demo and describe this folder as **future-market research and a data governance prototype**. Do not demonstrate the header-only CSV as a populated Sri Lankan dataset or claim live Sri Lankan vendor availability.

**Next step:** obtain a small written, reusable vendor export or vendor submissions with explicit service, location, scoped LKR quote and permission terms; separately establish real review-feature provenance before any model scoring. Then validate the first records and design an isolated adapter for review, leaving the working demo unchanged.

