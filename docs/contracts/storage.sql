-- Proposed logical storage spine. This is a valid SQLite schema, not an
-- upstream Lody database migration. One logical owner admits domain operations.
-- The SQLite baseline uses bounded dedicated execution and one writer.
-- Ordinary rowid tables are the baseline; measure table-layout optimizations.
-- Every non-integer primary-key column states NOT NULL explicitly.
-- Identifiers below describe this proposed store; none is an invented upstream
-- stream-incarnation header or a promise of server-side durability.
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = FULL;
-- The adapter verifies FULL and foreign_keys on every relevant connection.
-- Install and measure a bounded checkpoint owner before disabling automatic
-- checkpoints. Bound read transactions and reserve WAL/checkpoint disk space.

CREATE TABLE installation (
    singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
    replica_id TEXT NOT NULL,
    journal_id TEXT NOT NULL,
    schema_version INTEGER NOT NULL CHECK (schema_version = 1)
);

CREATE TABLE deployment_profile (
    profile_id TEXT NOT NULL PRIMARY KEY,
    adapter_id TEXT NOT NULL,
    deployment_origin TEXT NOT NULL,
    account_subject TEXT NOT NULL,
    UNIQUE (adapter_id, deployment_origin, account_subject)
);

CREATE TABLE room (
    profile_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    room_id TEXT NOT NULL,
    local_reset_epoch TEXT NOT NULL,
    canonical_stream_key TEXT NOT NULL,
    server_incarnation TEXT,
    continuity_proof TEXT NOT NULL CHECK (
        continuity_proof IN ('unknown', 'server_incarnation', 'protocol_reconciliation')
    ),
    is_current INTEGER NOT NULL CHECK (is_current IN (0, 1)),
    backend TEXT NOT NULL CHECK (backend IN ('loro', 'flock', 'roost')),
    generation INTEGER NOT NULL CHECK (generation >= 0),
    durable_cursor TEXT,
    applied_receipt_id INTEGER,
    checkpoint_id INTEGER,
    freshness TEXT NOT NULL CHECK (
        freshness IN ('unknown', 'catching_up', 'current', 'stale', 'unsupported', 'corrupt')
    ),
    PRIMARY KEY (profile_id, workspace_id, room_id, local_reset_epoch),
    FOREIGN KEY (profile_id) REFERENCES deployment_profile(profile_id),
    FOREIGN KEY (profile_id, workspace_id, room_id, local_reset_epoch, checkpoint_id)
        REFERENCES checkpoint(profile_id, workspace_id, room_id, local_reset_epoch, checkpoint_id)
        DEFERRABLE INITIALLY DEFERRED,
    CHECK (continuity_proof != 'server_incarnation' OR server_incarnation IS NOT NULL)
);

CREATE UNIQUE INDEX current_room ON room(profile_id, workspace_id, room_id)
    WHERE is_current = 1;

CREATE TABLE inbox (
    receipt_id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    room_id TEXT NOT NULL,
    local_reset_epoch TEXT NOT NULL,
    transport_epoch TEXT NOT NULL,
    source_dedup_key TEXT NOT NULL,
    cursor_before TEXT,
    cursor_after TEXT NOT NULL,
    payload BLOB NOT NULL,
    payload_sha256 TEXT NOT NULL,
    received_at_ms INTEGER NOT NULL,
    FOREIGN KEY (profile_id, workspace_id, room_id, local_reset_epoch)
        REFERENCES room(profile_id, workspace_id, room_id, local_reset_epoch),
    UNIQUE (profile_id, workspace_id, room_id, local_reset_epoch,
            transport_epoch, source_dedup_key)
);

CREATE TABLE checkpoint (
    checkpoint_id INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    room_id TEXT NOT NULL,
    local_reset_epoch TEXT NOT NULL,
    generation INTEGER NOT NULL,
    through_receipt_id INTEGER,
    cursor TEXT,
    codec_version TEXT NOT NULL,
    snapshot BLOB NOT NULL,
    pending_updates BLOB NOT NULL,
    version_summary BLOB NOT NULL,
    snapshot_sha256 TEXT NOT NULL,
    created_at_ms INTEGER NOT NULL,
    FOREIGN KEY (profile_id, workspace_id, room_id, local_reset_epoch)
        REFERENCES room(profile_id, workspace_id, room_id, local_reset_epoch),
    UNIQUE (profile_id, workspace_id, room_id, local_reset_epoch, checkpoint_id)
);

CREATE TABLE command_intent (
    command_id TEXT NOT NULL PRIMARY KEY,
    profile_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    turn_id TEXT NOT NULL,
    owner_generation INTEGER NOT NULL,
    idempotency_key TEXT NOT NULL,
    frozen_input BLOB NOT NULL,
    frozen_input_sha256 TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN (
        'accepted', 'dispatching', 'running', 'waiting_permission',
        'completed', 'failed', 'cancelled', 'delivery_uncertain'
    )),
    created_at_ms INTEGER NOT NULL,
    updated_at_ms INTEGER NOT NULL,
    FOREIGN KEY (profile_id) REFERENCES deployment_profile(profile_id),
    UNIQUE (profile_id, workspace_id, session_id, idempotency_key)
);

CREATE TABLE producer_state (
    profile_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    room_id TEXT NOT NULL,
    local_reset_epoch TEXT NOT NULL,
    producer_id TEXT NOT NULL,
    producer_epoch TEXT NOT NULL,
    next_sequence INTEGER NOT NULL CHECK (next_sequence >= 0),
    is_current INTEGER NOT NULL CHECK (is_current IN (0, 1)),
    PRIMARY KEY (profile_id, workspace_id, room_id, local_reset_epoch,
                 producer_id, producer_epoch),
    FOREIGN KEY (profile_id, workspace_id, room_id, local_reset_epoch)
        REFERENCES room(profile_id, workspace_id, room_id, local_reset_epoch)
);

CREATE UNIQUE INDEX current_producer ON producer_state(
    profile_id, workspace_id, room_id, local_reset_epoch, producer_id
) WHERE is_current = 1;

CREATE TABLE outbox (
    operation_id TEXT NOT NULL PRIMARY KEY,
    profile_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    room_id TEXT NOT NULL,
    local_reset_epoch TEXT NOT NULL,
    producer_id TEXT NOT NULL,
    producer_epoch TEXT NOT NULL,
    producer_sequence INTEGER NOT NULL CHECK (producer_sequence >= 0),
    owner_generation INTEGER NOT NULL,
    payload BLOB NOT NULL,
    payload_sha256 TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN (
        'pending', 'sending', 'transport_accepted', 'reconciled', 'blocked'
    )),
    created_at_ms INTEGER NOT NULL,
    transport_receipt BLOB,
    transport_accepted_at_ms INTEGER,
    reconciliation_evidence BLOB,
    UNIQUE (profile_id, workspace_id, room_id, local_reset_epoch,
            producer_id, producer_epoch, producer_sequence),
    FOREIGN KEY (profile_id, workspace_id, room_id, local_reset_epoch,
                 producer_id, producer_epoch)
        REFERENCES producer_state(profile_id, workspace_id, room_id, local_reset_epoch,
                                 producer_id, producer_epoch),
    CHECK (state != 'transport_accepted' OR
           (transport_receipt IS NOT NULL AND transport_accepted_at_ms IS NOT NULL)),
    CHECK (state != 'reconciled' OR reconciliation_evidence IS NOT NULL)
);

CREATE TRIGGER outbox_immutable_payload BEFORE UPDATE ON outbox
WHEN NEW.operation_id IS NOT OLD.operation_id
  OR NEW.profile_id IS NOT OLD.profile_id
  OR NEW.workspace_id IS NOT OLD.workspace_id
  OR NEW.room_id IS NOT OLD.room_id
  OR NEW.local_reset_epoch IS NOT OLD.local_reset_epoch
  OR NEW.producer_id IS NOT OLD.producer_id
  OR NEW.producer_epoch IS NOT OLD.producer_epoch
  OR NEW.producer_sequence IS NOT OLD.producer_sequence
  OR NEW.payload IS NOT OLD.payload
  OR NEW.payload_sha256 IS NOT OLD.payload_sha256
BEGIN
    SELECT RAISE(ABORT, 'outbox identity and payload are immutable');
END;

CREATE TRIGGER command_immutable_input BEFORE UPDATE ON command_intent
WHEN NEW.command_id IS NOT OLD.command_id
  OR NEW.profile_id IS NOT OLD.profile_id
  OR NEW.workspace_id IS NOT OLD.workspace_id
  OR NEW.session_id IS NOT OLD.session_id
  OR NEW.turn_id IS NOT OLD.turn_id
  OR NEW.idempotency_key IS NOT OLD.idempotency_key
  OR NEW.frozen_input IS NOT OLD.frozen_input
  OR NEW.frozen_input_sha256 IS NOT OLD.frozen_input_sha256
BEGIN
    SELECT RAISE(ABORT, 'command identity and frozen input are immutable');
END;

CREATE TABLE observation_event (
    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
    profile_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    session_id TEXT,
    event_type TEXT NOT NULL,
    body_json TEXT NOT NULL CHECK (json_valid(body_json)),
    observed_at_ms INTEGER NOT NULL,
    FOREIGN KEY (profile_id) REFERENCES deployment_profile(profile_id)
);

CREATE TABLE session_projection (
    profile_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    body_json TEXT NOT NULL CHECK (json_valid(body_json)),
    event_sequence INTEGER NOT NULL,
    PRIMARY KEY (profile_id, workspace_id, session_id),
    FOREIGN KEY (profile_id) REFERENCES deployment_profile(profile_id)
);

CREATE TABLE work_item_link (
    profile_id TEXT NOT NULL,
    workspace_id TEXT NOT NULL,
    session_id TEXT NOT NULL,
    work_item_id TEXT NOT NULL,
    evidence_uri TEXT NOT NULL,
    mapping_revision INTEGER NOT NULL,
    PRIMARY KEY (profile_id, workspace_id, session_id, work_item_id),
    FOREIGN KEY (profile_id) REFERENCES deployment_profile(profile_id)
);

CREATE INDEX inbox_room_order ON inbox(
    profile_id, workspace_id, room_id, local_reset_epoch, receipt_id
);
CREATE INDEX outbox_pending ON outbox(state, created_at_ms);
CREATE INDEX event_workspace_order ON observation_event(profile_id, workspace_id, sequence);

-- Namespace rules: profile_id isolates deployment and authenticated account.
-- A transport_epoch fences a connection; it does NOT identify stream content.
-- local_reset_epoch is OUR namespace, never a fabricated server incarnation.
-- Persist server_incarnation only when the adapter obtains an authoritative
-- value from a supported protocol. If continuity cannot be proved, bootstrap
-- into a fresh local_reset_epoch. Retain the old epoch and unsent outbox while
-- reconciling; never blindly send old updates into a recreated foreign stream.
-- generation fences in-flight worker/transport owners within a room epoch.
--
-- Transaction A: insert an entire contiguous transport batch and update its
-- room's durable_cursor together. Do not checkpoint a partial SSE/control batch.
-- Transaction B: advance applied_receipt_id, update the materialized projection,
-- and insert its replay events together. The watermark means imported through
-- that receipt, INCLUDING retained causal-pending operations; it does not mean
-- every received operation is visible. Duplicate replay must not emit new events.
-- On restart, rebuild the document from checkpoint plus ALL later inbox rows;
-- the projection watermark suppresses duplicate publication, not document replay.
-- Transaction C: install snapshot + pending bytes + represented receipt/cursor
-- together, then prune ONLY journal data proven covered by that checkpoint.
-- codec_version fixes how snapshot/pending/version bytes decode. An empty pending
-- BLOB explicitly means no sidecar; export failure must not become an empty BLOB.
-- applied_receipt_id and through_receipt_id deliberately have no foreign keys:
-- covered inbox rows may be pruned. The storage API verifies, before pruning,
-- that each watermark names a receipt in the SAME profile/workspace/room/reset
-- epoch, is contiguous in that room, and never exceeds its durable receive head.
-- It also verifies that the selected checkpoint belongs to the current generation
-- or a proved ancestor, and that projection event_sequence names the event written
-- in Transaction B. Event retention may later delete that event independently.
--
-- Allocate producer sequence and insert immutable outbox bytes in ONE transaction.
-- A retry reuses its recorded tuple and bytes; it never consumes next_sequence.
-- New epochs/producer fencing follow the VERIFIED adapter protocol, not a socket
-- reconnect counter. Resolve old ambiguous sends before fencing their epoch;
-- a fenced old epoch requires CRDT reconciliation, not blind prompt replay.
-- Transport receipts prove only the acknowledgement defined by that protocol;
-- neither receipt nor reconciliation_evidence implies another peer observed it.
-- Reconciliation may succeed after a lost acknowledgement, without a receipt.
--
-- Command acceptance and the relevant outgoing CRDT records must commit
-- together before acknowledging acceptance or dispatching an ACP prompt.
-- A repeated idempotency key must compare the frozen-input hash AND canonical
-- bytes: equal input returns the original receipt; different input is a conflict.
-- INSERT OR REPLACE is forbidden for intents/outbox/producer state. It could
-- bypass update triggers or destroy a receipt whose effects are already in flight.
-- The storage API validates monotonic state transitions and generation fencing.
-- No SQL schema alone enforces these application transaction boundaries.

-- Required implementation amendments: persist retry eligibility for operations
-- whose server-directed or policy floor must survive owner replacement. Define
-- the concrete records with the owning adapter; a notification only rechecks
-- eligibility. This core schema is not a complete migration for those adapters.
-- Reserve capacity at admission for mandatory completion, cancellation, recovery,
-- and observation transitions. Completion must not acquire ordinary admission
-- capacity that only its own completion can release. Physical ENOSPC is a
-- separate storage fault and never permits false acceptance.
-- A statement success is not a commit acknowledgement. The operation owner
-- completes the transaction even when the requesting CLI or observer disconnects.
