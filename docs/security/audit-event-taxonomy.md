# CRAM Audit Event Taxonomy v0.1

Milestone 7 establishes an append-oriented audit trail. Events identify actor (when known), organisation, action, resource type/id, timestamp, and sanitized metadata.

Initial action namespaces include `auth.*`, `user.*`, `role.*`, `organisation.*`, `dataset.*`, `upload.*`, `validation.*`, `approval.*`, `publication.*`, and `report.*`. The implemented authentication and organisation flows emit events immediately; later milestone services must use the same audit service when their business operations are introduced.

Sensitive values including passwords, password hashes, secrets, bearer/refresh/access tokens, authorization headers, and API keys are redacted before persistence. The database trigger rejects UPDATE and DELETE against `cram.audit_logs`; the API exposes read-only list/filter access guarded by `audit.read`.
