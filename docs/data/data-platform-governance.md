# CRAM Data Platform Governance - Milestones 9-12

## Scope

This document defines the implemented data-platform controls for the Data Catalogue, Generic Data Ingestion, Data Validation Framework, and Dataset Approval/Publishing milestones. It does not define partner-specific schemas, scientific thresholds, or the final FCC/partner approval chain.

## Catalogue and institutional ownership

A `Dataset` is the logical data product. Each dataset has an owning organisation, descriptive metadata, sensitivity, expected format, update frequency, and lifecycle status. `DatasetSource` records the institutional/API/file origin and may identify a provider organisation. Credentials are never stored in source metadata; only a `connection_secret_ref` may identify a secret-managed configuration entry.

`DatasetVersion` is the immutable version boundary for each accepted upload. `DatasetField` stores schema metadata and dataset-configurable validation rules.

## Generic ingestion

Milestone 10 accepts CSV first. The original byte stream is stored unchanged in the configured S3-compatible object store. CRAM records the original safe filename, MIME type, size, SHA-256 checksum, uploader, object key, and upload timestamp. Unsupported formats, unsafe filenames, empty files, and files larger than the configured development limit are rejected before a version is accepted.

The controlled weather-like CSV fixture is synthetic acceptance data only and is not the official SL-Met schema or contract.

## Validation

Validation rules are configuration attached to `DatasetField`; climate assumptions are not hard-coded. The framework supports required columns/values, unexpected-column warnings, type parsing, numeric minimum/maximum rules, future timestamp checks, latitude/longitude range checks, and duplicate-record warnings. Results are persisted as `DataValidationRun` and `ValidationError` records with severity and row/field context.

Validation can execute synchronously or through a FastAPI background task. Invalid versions enter `VALIDATION_FAILED` and cannot be submitted for approval.

## Approval and publishing

Implemented lifecycle states are:

`DRAFT -> UPLOADED -> VALIDATING -> VALIDATION_FAILED | VALIDATED -> PENDING_APPROVAL -> APPROVED -> PUBLISHED`

`REJECTED`, `SUPERSEDED`, and `ARCHIVED` are represented for later use without inventing additional workflows.

Upload/validate, approve, and publish permissions are separated. The framework does not invent the final institutional approval chain; that remains subject to stakeholder approval. `DatasetVersionStatusHistory` records every lifecycle transition.

## Audit and publication boundary

Dataset creation/configuration, upload, validation, approval/rejection, and publication create audit events. Dashboards and analytics in later milestones must consume `PUBLISHED` versions by default. No later climate module is implemented by Milestones 9-12.
