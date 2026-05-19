CREATE SCHEMA IF NOT EXISTS council;

CREATE TABLE IF NOT EXISTS council.import_batch (
  import_batch_id bigserial PRIMARY KEY,
  document_family text NOT NULL,
  source_root text NOT NULL,
  source_manifest_path text,
  source_manifest_hash text,
  importer_name text NOT NULL,
  importer_version text NOT NULL,
  started_at timestamptz NOT NULL DEFAULT now(),
  completed_at timestamptz,
  status text NOT NULL DEFAULT 'running',
  diagnostics jsonb NOT NULL DEFAULT '{}'::jsonb,
  CONSTRAINT ck_council_import_batch_status
    CHECK (status IN ('running', 'completed', 'failed'))
);

CREATE TABLE IF NOT EXISTS council.import_record_event (
  import_record_event_id bigserial PRIMARY KEY,
  import_batch_id bigint NOT NULL REFERENCES council.import_batch(import_batch_id) ON DELETE CASCADE,
  record_family text NOT NULL,
  natural_key text NOT NULL,
  prior_content_hash text,
  content_hash text,
  change_status text NOT NULL,
  active_record_table text,
  active_record_id bigint,
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_council_import_record_event_status
    CHECK (change_status IN ('added', 'removed', 'changed', 'unchanged'))
);

CREATE INDEX IF NOT EXISTS idx_council_import_record_event_batch
  ON council.import_record_event(import_batch_id, record_family, change_status);

CREATE TABLE IF NOT EXISTS council.jurisdiction (
  jurisdiction_id bigserial PRIMARY KEY,
  jurisdiction_key text NOT NULL,
  name_raw text NOT NULL,
  jurisdiction_type text,
  province text,
  country text NOT NULL DEFAULT 'Canada',
  website_url text,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  natural_key text NOT NULL,
  content_hash text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  superseded_by_id bigint REFERENCES council.jurisdiction(jurisdiction_id),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_council_jurisdiction_active_key
  ON council.jurisdiction(natural_key)
  WHERE is_active;

CREATE UNIQUE INDEX IF NOT EXISTS uq_council_jurisdiction_key_active
  ON council.jurisdiction(jurisdiction_key)
  WHERE is_active;

CREATE TABLE IF NOT EXISTS council.source_document (
  source_document_id bigserial PRIMARY KEY,
  jurisdiction_id bigint REFERENCES council.jurisdiction(jurisdiction_id) ON DELETE SET NULL,
  import_batch_id bigint REFERENCES council.import_batch(import_batch_id) ON DELETE SET NULL,
  source_document_key text NOT NULL,
  document_type text NOT NULL,
  title_raw text,
  repo_relpath text NOT NULL,
  source_url text,
  mime_type text,
  page_count integer,
  source_file_hash text NOT NULL,
  published_date date,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  natural_key text NOT NULL,
  content_hash text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  superseded_by_id bigint REFERENCES council.source_document(source_document_id),
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_council_source_document_page_count
    CHECK (page_count IS NULL OR page_count >= 0)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_council_source_document_active_key
  ON council.source_document(natural_key)
  WHERE is_active;

CREATE INDEX IF NOT EXISTS idx_council_source_document_jurisdiction
  ON council.source_document(jurisdiction_id, document_type);

CREATE TABLE IF NOT EXISTS council.source_page (
  source_page_id bigserial PRIMARY KEY,
  source_document_id bigint NOT NULL REFERENCES council.source_document(source_document_id) ON DELETE CASCADE,
  page_number integer NOT NULL,
  page_label_raw text,
  text_raw text,
  width numeric,
  height numeric,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  natural_key text NOT NULL,
  content_hash text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  superseded_by_id bigint REFERENCES council.source_page(source_page_id),
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_council_source_page_number
    CHECK (page_number >= 1)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_council_source_page_active_key
  ON council.source_page(natural_key)
  WHERE is_active;

CREATE UNIQUE INDEX IF NOT EXISTS uq_council_source_page_document_number_active
  ON council.source_page(source_document_id, page_number)
  WHERE is_active;

CREATE TABLE IF NOT EXISTS council.source_asset (
  source_asset_id bigserial PRIMARY KEY,
  source_document_id bigint REFERENCES council.source_document(source_document_id) ON DELETE CASCADE,
  source_page_id bigint REFERENCES council.source_page(source_page_id) ON DELETE CASCADE,
  asset_type text NOT NULL,
  repo_relpath text NOT NULL,
  mime_type text,
  file_hash text,
  width integer,
  height integer,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  natural_key text NOT NULL,
  content_hash text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  superseded_by_id bigint REFERENCES council.source_asset(source_asset_id),
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_council_source_asset_owner
    CHECK (source_document_id IS NOT NULL OR source_page_id IS NOT NULL)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_council_source_asset_active_key
  ON council.source_asset(natural_key)
  WHERE is_active;

CREATE INDEX IF NOT EXISTS idx_council_source_asset_document
  ON council.source_asset(source_document_id, asset_type);

CREATE TABLE IF NOT EXISTS council.body (
  body_id bigserial PRIMARY KEY,
  jurisdiction_id bigint NOT NULL REFERENCES council.jurisdiction(jurisdiction_id) ON DELETE CASCADE,
  parent_body_id bigint REFERENCES council.body(body_id) ON DELETE SET NULL,
  body_key text NOT NULL,
  body_type text NOT NULL,
  name_raw text NOT NULL,
  slug text NOT NULL,
  description text,
  website_url text,
  start_date date,
  end_date date,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  natural_key text NOT NULL,
  content_hash text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  superseded_by_id bigint REFERENCES council.body(body_id),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_council_body_active_key
  ON council.body(natural_key)
  WHERE is_active;

CREATE UNIQUE INDEX IF NOT EXISTS uq_council_body_slug_active
  ON council.body(jurisdiction_id, slug)
  WHERE is_active;

CREATE INDEX IF NOT EXISTS idx_council_body_type
  ON council.body(jurisdiction_id, body_type);

CREATE TABLE IF NOT EXISTS council.person (
  person_id bigserial PRIMARY KEY,
  jurisdiction_id bigint REFERENCES council.jurisdiction(jurisdiction_id) ON DELETE SET NULL,
  person_key text NOT NULL,
  display_name_raw text NOT NULL,
  sort_name text NOT NULL,
  slug text NOT NULL,
  given_name text,
  family_name text,
  honorific_raw text,
  email text,
  phone text,
  website_url text,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  natural_key text NOT NULL,
  content_hash text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  superseded_by_id bigint REFERENCES council.person(person_id),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_council_person_active_key
  ON council.person(natural_key)
  WHERE is_active;

CREATE UNIQUE INDEX IF NOT EXISTS uq_council_person_slug_active
  ON council.person(jurisdiction_id, slug)
  WHERE is_active;

CREATE INDEX IF NOT EXISTS idx_council_person_sort
  ON council.person(sort_name);

CREATE TABLE IF NOT EXISTS council.office_term (
  office_term_id bigserial PRIMARY KEY,
  jurisdiction_id bigint NOT NULL REFERENCES council.jurisdiction(jurisdiction_id) ON DELETE CASCADE,
  person_id bigint NOT NULL REFERENCES council.person(person_id) ON DELETE CASCADE,
  office_title_raw text NOT NULL,
  ward_raw text,
  district_raw text,
  term_start_date date,
  term_end_date date,
  election_date date,
  status text NOT NULL DEFAULT 'active',
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  natural_key text NOT NULL,
  content_hash text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  superseded_by_id bigint REFERENCES council.office_term(office_term_id),
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_council_office_term_status
    CHECK (status IN ('active', 'former', 'appointed', 'acting', 'unknown'))
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_council_office_term_active_key
  ON council.office_term(natural_key)
  WHERE is_active;

CREATE INDEX IF NOT EXISTS idx_council_office_term_person
  ON council.office_term(person_id, status);

CREATE TABLE IF NOT EXISTS council.body_membership (
  body_membership_id bigserial PRIMARY KEY,
  body_id bigint NOT NULL REFERENCES council.body(body_id) ON DELETE CASCADE,
  person_id bigint NOT NULL REFERENCES council.person(person_id) ON DELETE CASCADE,
  office_term_id bigint REFERENCES council.office_term(office_term_id) ON DELETE SET NULL,
  role_raw text,
  role_key text,
  membership_type text NOT NULL DEFAULT 'member',
  start_date date,
  end_date date,
  voting_member boolean,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  natural_key text NOT NULL,
  content_hash text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  superseded_by_id bigint REFERENCES council.body_membership(body_membership_id),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_council_body_membership_active_key
  ON council.body_membership(natural_key)
  WHERE is_active;

CREATE INDEX IF NOT EXISTS idx_council_body_membership_body
  ON council.body_membership(body_id, is_active);

CREATE INDEX IF NOT EXISTS idx_council_body_membership_person
  ON council.body_membership(person_id, is_active);

CREATE TABLE IF NOT EXISTS council.meeting (
  meeting_id bigserial PRIMARY KEY,
  jurisdiction_id bigint NOT NULL REFERENCES council.jurisdiction(jurisdiction_id) ON DELETE CASCADE,
  body_id bigint NOT NULL REFERENCES council.body(body_id) ON DELETE CASCADE,
  meeting_key text NOT NULL,
  meeting_type text,
  title_raw text NOT NULL,
  meeting_date date NOT NULL,
  meeting_time_raw text,
  starts_at timestamptz,
  ends_at timestamptz,
  location_raw text,
  livestream_url text,
  meeting_status text NOT NULL DEFAULT 'scheduled',
  focus text,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  natural_key text NOT NULL,
  content_hash text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  superseded_by_id bigint REFERENCES council.meeting(meeting_id),
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_council_meeting_status
    CHECK (meeting_status IN ('scheduled', 'completed', 'cancelled', 'postponed', 'unknown'))
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_council_meeting_active_key
  ON council.meeting(natural_key)
  WHERE is_active;

CREATE UNIQUE INDEX IF NOT EXISTS uq_council_meeting_key_active
  ON council.meeting(meeting_key)
  WHERE is_active;

CREATE INDEX IF NOT EXISTS idx_council_meeting_calendar
  ON council.meeting(body_id, meeting_date, starts_at);

CREATE TABLE IF NOT EXISTS council.meeting_document (
  meeting_document_id bigserial PRIMARY KEY,
  meeting_id bigint NOT NULL REFERENCES council.meeting(meeting_id) ON DELETE CASCADE,
  source_document_id bigint NOT NULL REFERENCES council.source_document(source_document_id) ON DELETE CASCADE,
  document_role text NOT NULL,
  source_order integer,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  natural_key text NOT NULL,
  content_hash text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  superseded_by_id bigint REFERENCES council.meeting_document(meeting_document_id),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_council_meeting_document_active_key
  ON council.meeting_document(natural_key)
  WHERE is_active;

CREATE INDEX IF NOT EXISTS idx_council_meeting_document_meeting
  ON council.meeting_document(meeting_id, document_role);

CREATE TABLE IF NOT EXISTS council.agenda_section (
  agenda_section_id bigserial PRIMARY KEY,
  meeting_id bigint NOT NULL REFERENCES council.meeting(meeting_id) ON DELETE CASCADE,
  agenda_section_key text NOT NULL,
  parent_agenda_section_id bigint REFERENCES council.agenda_section(agenda_section_id) ON DELETE SET NULL,
  label_raw text,
  title_raw text NOT NULL,
  summary text,
  source_order integer,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  natural_key text NOT NULL,
  content_hash text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  superseded_by_id bigint REFERENCES council.agenda_section(agenda_section_id),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_council_agenda_section_active_key
  ON council.agenda_section(natural_key)
  WHERE is_active;

CREATE INDEX IF NOT EXISTS idx_council_agenda_section_meeting
  ON council.agenda_section(meeting_id, source_order);

CREATE TABLE IF NOT EXISTS council.business_item (
  business_item_id bigserial PRIMARY KEY,
  jurisdiction_id bigint NOT NULL REFERENCES council.jurisdiction(jurisdiction_id) ON DELETE CASCADE,
  lead_body_id bigint REFERENCES council.body(body_id) ON DELETE SET NULL,
  business_item_key text NOT NULL,
  business_item_type text NOT NULL,
  title_raw text NOT NULL,
  slug text NOT NULL,
  summary text,
  current_stage text,
  status text NOT NULL DEFAULT 'active',
  opened_date date,
  closed_date date,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  natural_key text NOT NULL,
  content_hash text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  superseded_by_id bigint REFERENCES council.business_item(business_item_id),
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_council_business_item_status
    CHECK (status IN ('active', 'scheduled', 'deferred', 'adopted', 'defeated', 'withdrawn', 'closed', 'superseded', 'unknown'))
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_council_business_item_active_key
  ON council.business_item(natural_key)
  WHERE is_active;

CREATE UNIQUE INDEX IF NOT EXISTS uq_council_business_item_slug_active
  ON council.business_item(jurisdiction_id, slug)
  WHERE is_active;

CREATE INDEX IF NOT EXISTS idx_council_business_item_status
  ON council.business_item(jurisdiction_id, status);

CREATE TABLE IF NOT EXISTS council.business_item_evidence (
  business_item_evidence_id bigserial PRIMARY KEY,
  business_item_id bigint NOT NULL REFERENCES council.business_item(business_item_id) ON DELETE CASCADE,
  source_document_id bigint REFERENCES council.source_document(source_document_id) ON DELETE SET NULL,
  evidence_key text NOT NULL,
  evidence_type text NOT NULL,
  evidence_value_raw text NOT NULL,
  evidence_value_normalized text,
  signal_weight numeric(6,3) NOT NULL DEFAULT 0,
  confidence numeric(6,3) NOT NULL DEFAULT 0,
  observed_date date,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  natural_key text NOT NULL,
  content_hash text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  superseded_by_id bigint REFERENCES council.business_item_evidence(business_item_evidence_id),
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_council_business_item_evidence_confidence
    CHECK (confidence >= 0 AND confidence <= 1)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_council_business_item_evidence_active_key
  ON council.business_item_evidence(natural_key)
  WHERE is_active;

CREATE INDEX IF NOT EXISTS idx_council_business_item_evidence_item
  ON council.business_item_evidence(business_item_id, evidence_type);

CREATE INDEX IF NOT EXISTS idx_council_business_item_evidence_value
  ON council.business_item_evidence(evidence_type, evidence_value_normalized)
  WHERE is_active;

CREATE TABLE IF NOT EXISTS council.business_item_relationship (
  business_item_relationship_id bigserial PRIMARY KEY,
  from_business_item_id bigint NOT NULL REFERENCES council.business_item(business_item_id) ON DELETE CASCADE,
  to_business_item_id bigint NOT NULL REFERENCES council.business_item(business_item_id) ON DELETE CASCADE,
  relationship_key text NOT NULL,
  relationship_type text NOT NULL,
  confidence numeric(6,3) NOT NULL DEFAULT 1,
  rationale text,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  natural_key text NOT NULL,
  content_hash text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  superseded_by_id bigint REFERENCES council.business_item_relationship(business_item_relationship_id),
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_council_business_item_relationship_type
    CHECK (relationship_type IN ('same_as', 'continuation_of', 'derived_from', 'supersedes', 'split_from', 'related_to')),
  CONSTRAINT ck_council_business_item_relationship_confidence
    CHECK (confidence >= 0 AND confidence <= 1),
  CONSTRAINT ck_council_business_item_relationship_distinct
    CHECK (from_business_item_id <> to_business_item_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_council_business_item_relationship_active_key
  ON council.business_item_relationship(natural_key)
  WHERE is_active;

CREATE INDEX IF NOT EXISTS idx_council_business_item_relationship_from
  ON council.business_item_relationship(from_business_item_id, relationship_type);

CREATE INDEX IF NOT EXISTS idx_council_business_item_relationship_to
  ON council.business_item_relationship(to_business_item_id, relationship_type);

CREATE TABLE IF NOT EXISTS council.business_item_candidate_link (
  business_item_candidate_link_id bigserial PRIMARY KEY,
  from_business_item_id bigint NOT NULL REFERENCES council.business_item(business_item_id) ON DELETE CASCADE,
  to_business_item_id bigint NOT NULL REFERENCES council.business_item(business_item_id) ON DELETE CASCADE,
  candidate_key text NOT NULL,
  proposed_relationship_type text NOT NULL,
  score numeric(6,3) NOT NULL,
  review_status text NOT NULL DEFAULT 'pending',
  reason_codes jsonb NOT NULL DEFAULT '[]'::jsonb,
  explanation text,
  reviewed_at timestamptz,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  natural_key text NOT NULL,
  content_hash text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  superseded_by_id bigint REFERENCES council.business_item_candidate_link(business_item_candidate_link_id),
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_council_business_item_candidate_link_relationship_type
    CHECK (proposed_relationship_type IN ('same_as', 'continuation_of', 'derived_from', 'supersedes', 'split_from', 'related_to')),
  CONSTRAINT ck_council_business_item_candidate_link_score
    CHECK (score >= 0 AND score <= 1),
  CONSTRAINT ck_council_business_item_candidate_link_review_status
    CHECK (review_status IN ('pending', 'accepted', 'rejected', 'superseded')),
  CONSTRAINT ck_council_business_item_candidate_link_distinct
    CHECK (from_business_item_id <> to_business_item_id)
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_council_business_item_candidate_link_active_key
  ON council.business_item_candidate_link(natural_key)
  WHERE is_active;

CREATE INDEX IF NOT EXISTS idx_council_business_item_candidate_link_review
  ON council.business_item_candidate_link(review_status, score DESC);

ALTER TABLE council.business_item_candidate_link
  ALTER COLUMN reason_codes TYPE jsonb USING to_jsonb(reason_codes),
  ALTER COLUMN reason_codes SET DEFAULT '[]'::jsonb;

CREATE TABLE IF NOT EXISTS council.agenda_item (
  agenda_item_id bigserial PRIMARY KEY,
  meeting_id bigint NOT NULL REFERENCES council.meeting(meeting_id) ON DELETE CASCADE,
  agenda_section_id bigint REFERENCES council.agenda_section(agenda_section_id) ON DELETE SET NULL,
  business_item_id bigint REFERENCES council.business_item(business_item_id) ON DELETE SET NULL,
  agenda_item_key text NOT NULL,
  item_number_raw text,
  item_type text,
  title_raw text NOT NULL,
  description text,
  decision_requested text,
  source_order integer,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  natural_key text NOT NULL,
  content_hash text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  superseded_by_id bigint REFERENCES council.agenda_item(agenda_item_id),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_council_agenda_item_active_key
  ON council.agenda_item(natural_key)
  WHERE is_active;

CREATE INDEX IF NOT EXISTS idx_council_agenda_item_meeting
  ON council.agenda_item(meeting_id, source_order);

CREATE INDEX IF NOT EXISTS idx_council_agenda_item_business
  ON council.agenda_item(business_item_id);

CREATE TABLE IF NOT EXISTS council.package_document (
  package_document_id bigserial PRIMARY KEY,
  meeting_id bigint NOT NULL REFERENCES council.meeting(meeting_id) ON DELETE CASCADE,
  source_document_id bigint NOT NULL REFERENCES council.source_document(source_document_id) ON DELETE CASCADE,
  agenda_item_id bigint REFERENCES council.agenda_item(agenda_item_id) ON DELETE SET NULL,
  business_item_id bigint REFERENCES council.business_item(business_item_id) ON DELETE SET NULL,
  package_document_key text NOT NULL,
  title_raw text NOT NULL,
  document_type text,
  document_category text,
  template_type text,
  page_start integer,
  page_end integer,
  page_numbers integer[],
  page_count integer,
  summary text,
  boundary_basis text,
  source_order integer,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  natural_key text NOT NULL,
  content_hash text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  superseded_by_id bigint REFERENCES council.package_document(package_document_id),
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_council_package_document_pages
    CHECK (
      (page_start IS NULL OR page_start >= 1)
      AND (page_end IS NULL OR page_end >= 1)
      AND (page_start IS NULL OR page_end IS NULL OR page_end >= page_start)
      AND (page_count IS NULL OR page_count >= 0)
    )
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_council_package_document_active_key
  ON council.package_document(natural_key)
  WHERE is_active;

CREATE INDEX IF NOT EXISTS idx_council_package_document_meeting
  ON council.package_document(meeting_id, source_order);

CREATE INDEX IF NOT EXISTS idx_council_package_document_agenda_item
  ON council.package_document(agenda_item_id);

CREATE INDEX IF NOT EXISTS idx_council_package_document_business_item
  ON council.package_document(business_item_id);

CREATE TABLE IF NOT EXISTS council.attendance (
  attendance_id bigserial PRIMARY KEY,
  meeting_id bigint NOT NULL REFERENCES council.meeting(meeting_id) ON DELETE CASCADE,
  person_id bigint NOT NULL REFERENCES council.person(person_id) ON DELETE CASCADE,
  body_membership_id bigint REFERENCES council.body_membership(body_membership_id) ON DELETE SET NULL,
  attendance_status text NOT NULL,
  role_raw text,
  note text,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  natural_key text NOT NULL,
  content_hash text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  superseded_by_id bigint REFERENCES council.attendance(attendance_id),
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_council_attendance_status
    CHECK (attendance_status IN ('present', 'absent', 'regrets', 'remote', 'partial', 'unknown'))
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_council_attendance_active_key
  ON council.attendance(natural_key)
  WHERE is_active;

CREATE INDEX IF NOT EXISTS idx_council_attendance_meeting
  ON council.attendance(meeting_id, attendance_status);

CREATE INDEX IF NOT EXISTS idx_council_attendance_person
  ON council.attendance(person_id, attendance_status);

CREATE TABLE IF NOT EXISTS council.business_item_event (
  business_item_event_id bigserial PRIMARY KEY,
  business_item_id bigint NOT NULL REFERENCES council.business_item(business_item_id) ON DELETE CASCADE,
  meeting_id bigint REFERENCES council.meeting(meeting_id) ON DELETE SET NULL,
  agenda_item_id bigint REFERENCES council.agenda_item(agenda_item_id) ON DELETE SET NULL,
  body_id bigint REFERENCES council.body(body_id) ON DELETE SET NULL,
  event_key text NOT NULL,
  event_type text NOT NULL,
  event_stage text,
  event_date date,
  title_raw text,
  outcome text,
  summary text,
  source_order integer,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  natural_key text NOT NULL,
  content_hash text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  superseded_by_id bigint REFERENCES council.business_item_event(business_item_event_id),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_council_business_item_event_active_key
  ON council.business_item_event(natural_key)
  WHERE is_active;

CREATE INDEX IF NOT EXISTS idx_council_business_item_event_item
  ON council.business_item_event(business_item_id, event_date, source_order);

CREATE INDEX IF NOT EXISTS idx_council_business_item_event_meeting
  ON council.business_item_event(meeting_id);

CREATE TABLE IF NOT EXISTS council.motion (
  motion_id bigserial PRIMARY KEY,
  meeting_id bigint NOT NULL REFERENCES council.meeting(meeting_id) ON DELETE CASCADE,
  agenda_item_id bigint REFERENCES council.agenda_item(agenda_item_id) ON DELETE SET NULL,
  business_item_id bigint REFERENCES council.business_item(business_item_id) ON DELETE SET NULL,
  moved_by_person_id bigint REFERENCES council.person(person_id) ON DELETE SET NULL,
  seconded_by_person_id bigint REFERENCES council.person(person_id) ON DELETE SET NULL,
  motion_key text NOT NULL,
  motion_type text,
  motion_text_raw text NOT NULL,
  outcome text,
  source_order integer,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  natural_key text NOT NULL,
  content_hash text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  superseded_by_id bigint REFERENCES council.motion(motion_id),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_council_motion_active_key
  ON council.motion(natural_key)
  WHERE is_active;

CREATE INDEX IF NOT EXISTS idx_council_motion_meeting
  ON council.motion(meeting_id, source_order);

CREATE INDEX IF NOT EXISTS idx_council_motion_business
  ON council.motion(business_item_id);

CREATE INDEX IF NOT EXISTS idx_council_motion_people
  ON council.motion(moved_by_person_id, seconded_by_person_id);

CREATE TABLE IF NOT EXISTS council.vote (
  vote_id bigserial PRIMARY KEY,
  meeting_id bigint NOT NULL REFERENCES council.meeting(meeting_id) ON DELETE CASCADE,
  motion_id bigint REFERENCES council.motion(motion_id) ON DELETE SET NULL,
  agenda_item_id bigint REFERENCES council.agenda_item(agenda_item_id) ON DELETE SET NULL,
  business_item_id bigint REFERENCES council.business_item(business_item_id) ON DELETE SET NULL,
  vote_key text NOT NULL,
  vote_type text,
  outcome text,
  vote_text_raw text,
  votes_for integer,
  votes_against integer,
  abstentions integer,
  source_order integer,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  natural_key text NOT NULL,
  content_hash text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  superseded_by_id bigint REFERENCES council.vote(vote_id),
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_council_vote_counts
    CHECK (
      (votes_for IS NULL OR votes_for >= 0)
      AND (votes_against IS NULL OR votes_against >= 0)
      AND (abstentions IS NULL OR abstentions >= 0)
    )
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_council_vote_active_key
  ON council.vote(natural_key)
  WHERE is_active;

CREATE INDEX IF NOT EXISTS idx_council_vote_meeting
  ON council.vote(meeting_id, source_order);

CREATE INDEX IF NOT EXISTS idx_council_vote_business
  ON council.vote(business_item_id);

CREATE TABLE IF NOT EXISTS council.vote_member (
  vote_member_id bigserial PRIMARY KEY,
  vote_id bigint NOT NULL REFERENCES council.vote(vote_id) ON DELETE CASCADE,
  person_id bigint NOT NULL REFERENCES council.person(person_id) ON DELETE CASCADE,
  vote_position text NOT NULL,
  note text,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  natural_key text NOT NULL,
  content_hash text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  superseded_by_id bigint REFERENCES council.vote_member(vote_member_id),
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_council_vote_member_position
    CHECK (vote_position IN ('for', 'against', 'abstain', 'absent', 'conflict', 'unknown'))
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_council_vote_member_active_key
  ON council.vote_member(natural_key)
  WHERE is_active;

CREATE INDEX IF NOT EXISTS idx_council_vote_member_vote
  ON council.vote_member(vote_id, vote_position);

CREATE INDEX IF NOT EXISTS idx_council_vote_member_person
  ON council.vote_member(person_id, vote_position);

CREATE TABLE IF NOT EXISTS council.business_item_property (
  business_item_property_id bigserial PRIMARY KEY,
  business_item_id bigint NOT NULL REFERENCES council.business_item(business_item_id) ON DELETE CASCADE,
  property_label_raw text NOT NULL,
  address_raw text,
  pid text,
  relationship_type text NOT NULL DEFAULT 'subject_property',
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  natural_key text NOT NULL,
  content_hash text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  superseded_by_id bigint REFERENCES council.business_item_property(business_item_property_id),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_council_business_item_property_active_key
  ON council.business_item_property(natural_key)
  WHERE is_active;

CREATE INDEX IF NOT EXISTS idx_council_business_item_property_item
  ON council.business_item_property(business_item_id);

CREATE INDEX IF NOT EXISTS idx_council_business_item_property_pid
  ON council.business_item_property(pid);

CREATE TABLE IF NOT EXISTS council.business_item_zoning_amendment (
  business_item_zoning_amendment_id bigserial PRIMARY KEY,
  business_item_id bigint NOT NULL REFERENCES council.business_item(business_item_id) ON DELETE CASCADE,
  bylaw_name_raw text,
  bylaw_amendment_key text,
  from_zone_raw text,
  to_zone_raw text,
  official_plan_amendment boolean,
  future_land_use_change_raw text,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  natural_key text NOT NULL,
  content_hash text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  superseded_by_id bigint REFERENCES council.business_item_zoning_amendment(business_item_zoning_amendment_id),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_council_business_item_zoning_amendment_active_key
  ON council.business_item_zoning_amendment(natural_key)
  WHERE is_active;

CREATE INDEX IF NOT EXISTS idx_council_business_item_zoning_amendment_item
  ON council.business_item_zoning_amendment(business_item_id);

CREATE INDEX IF NOT EXISTS idx_council_business_item_zoning_amendment_zones
  ON council.business_item_zoning_amendment(from_zone_raw, to_zone_raw);

CREATE TABLE IF NOT EXISTS council.route_target (
  route_target_id bigserial PRIMARY KEY,
  route_name text NOT NULL,
  path_template text NOT NULL,
  entity_table text NOT NULL,
  entity_id bigint NOT NULL,
  slug text,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  natural_key text NOT NULL,
  content_hash text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  superseded_by_id bigint REFERENCES council.route_target(route_target_id),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_council_route_target_active_key
  ON council.route_target(natural_key)
  WHERE is_active;

CREATE INDEX IF NOT EXISTS idx_council_route_target_route
  ON council.route_target(route_name, slug);

CREATE INDEX IF NOT EXISTS idx_council_route_target_entity
  ON council.route_target(entity_table, entity_id);

CREATE TABLE IF NOT EXISTS council.entity_alias (
  entity_alias_id bigserial PRIMARY KEY,
  entity_table text NOT NULL,
  entity_id bigint NOT NULL,
  alias_type text NOT NULL,
  alias_raw text NOT NULL,
  alias_normalized text NOT NULL,
  source_document_id bigint REFERENCES council.source_document(source_document_id) ON DELETE SET NULL,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  natural_key text NOT NULL,
  content_hash text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  superseded_by_id bigint REFERENCES council.entity_alias(entity_alias_id),
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_council_entity_alias_active_key
  ON council.entity_alias(natural_key)
  WHERE is_active;

CREATE INDEX IF NOT EXISTS idx_council_entity_alias_lookup
  ON council.entity_alias(entity_table, alias_normalized);

CREATE INDEX IF NOT EXISTS idx_council_entity_alias_entity
  ON council.entity_alias(entity_table, entity_id);

CREATE TABLE IF NOT EXISTS council.source_citation (
  source_citation_id bigserial PRIMARY KEY,
  source_document_id bigint NOT NULL REFERENCES council.source_document(source_document_id) ON DELETE CASCADE,
  source_page_id bigint REFERENCES council.source_page(source_page_id) ON DELETE SET NULL,
  cited_table text NOT NULL,
  cited_id bigint NOT NULL,
  citation_label text,
  page_start integer,
  page_end integer,
  text_excerpt text,
  bbox jsonb,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  natural_key text NOT NULL,
  content_hash text NOT NULL,
  is_active boolean NOT NULL DEFAULT true,
  superseded_by_id bigint REFERENCES council.source_citation(source_citation_id),
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_council_source_citation_pages
    CHECK (
      (page_start IS NULL OR page_start >= 1)
      AND (page_end IS NULL OR page_end >= 1)
      AND (page_start IS NULL OR page_end IS NULL OR page_end >= page_start)
    )
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_council_source_citation_active_key
  ON council.source_citation(natural_key)
  WHERE is_active;

CREATE INDEX IF NOT EXISTS idx_council_source_citation_source
  ON council.source_citation(source_document_id, page_start, page_end);

CREATE INDEX IF NOT EXISTS idx_council_source_citation_cited
  ON council.source_citation(cited_table, cited_id);
