# Phase 2D: Data Quality & Provenance Hardening

## Overview
Phase 2D introduces robust data quality and provenance tracking into the Xaiote backend. This phase focuses on extending the import processing to track the lifecycle and origin of data at a granular level. 

## Key Features Implemented
1. **Source Provenance on Master Data:**
   - Added `source_import_job_id` (ForeignKey to `ImportJob`) to all Master models (`Customer`, `Vendor`, `Product`, `Machine`) and `WorkOrder`.
   - Ensures any record updated or created via an import can trace its exact origin back to the job that modified it.

2. **Advanced Job Telemetry:**
   - Expanded `ImportJob` metrics to include `needs_review_rows`, `created_rows`, `updated_rows`, and `unchanged_rows`.
   - Provides clear visibility into the impact of an import on the dataset.

3. **Granular Import Auditing:**
   - Introduced `ImportAuditAction` ENUM (`CREATED`, `UPDATED`, `UNCHANGED`, `REJECTED`).
   - Extended `ImportAudit` model to capture `action`, `previous_source_import_job_id`, and `target_record_id`.
   - Provides an immutable ledger of how a record evolved through multiple file imports, keeping references to prior state origins.

4. **Deterministic Data Quality Checks:**
   - Implemented logic where `WorkOrder` quantities of `0` result in `ValidationStatus.NEEDS_REVIEW` instead of outright rejection or being blindly marked as valid.

5. **Tenant Storage Isolation:**
   - Modified S3 object paths to use `{current_company.id}/{file_hash}` ensuring files are strictly isolated at the storage layer per tenant.

## Architecture & Schema Changes
- Migration `110c40d6285f` (Phase 2D) deployed to both `xaiote` and `xaiote_test`.
- Upgraded `ImportJobResponse`, `ImportAuditResponse`, and all Master `*Response` schemas in `schemas/` to propagate the new data fields to API consumers.

## Next Steps
- Integrate these telemetry fields into the frontend dashboard.
- Provide user interfaces for resolving records flagged as `NEEDS_REVIEW`.
