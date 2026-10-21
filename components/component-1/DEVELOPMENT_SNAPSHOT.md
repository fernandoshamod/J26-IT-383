# Component 1 development snapshot

This branch imports existing research and maintained application source for ongoing group development. Unfinished capabilities remain documented in docs/COMPONENT_1_GITHUB_AUDIT.md. No new model training, research mechanism, real-venue qualification or group integration is claimed.

Nine files differ from the prepared source solely by removal of extra blank lines at EOF. DEVELOPMENT_SOURCE_MANIFEST.json records original versus publication-copy hashes and the precise exception set. Historical baseline/provenance manifests remain unchanged and describe the source before formatting cleanup; they are not claimed to match changed bytes. Use the development manifest to verify this snapshot.

The existing app/setup.ps1 creates a local environment, installs dependencies/builds and generates an installation-local runtime manifest as its normal setup step. Before setup, app/PORTABLE_SOURCE_MANIFEST.json retains the historical baseline; direct verify_portable.py will report the documented formatting hash differences. This is an expected baseline difference, not a source-integrity PASS. Tests must first verify the development manifest, then clearly distinguish any generated installation manifest from the historical baseline.

Two downloaded third-party reference files (CADTransformer_ONTOLOGY.py and CubiCasa_NATIVE_LOADER.py under research/.../acquired/) are intentionally excluded pending review of redistribution terms/notices. They are not maintained app runtime dependencies. Do not add them with force. The historical research reference directory is not a complete private-data reproduction bundle. Eighteen previously reviewed Python source snapshots under outputs are retained with their exact original hashes; other generated outputs/private assets remain excluded.

Private floorplans, raw datasets, weights, databases, environments, logs and notebook outputs are not distributed. Read docs/THIRD_PARTY_AND_DATA_RIGHTS.md for unresolved publication/dependency obligations. This is not a production release or assurance of legal clearance. Target laptop and live image-to-layout integration remain unverified.
