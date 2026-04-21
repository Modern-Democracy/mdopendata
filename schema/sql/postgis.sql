CREATE EXTENSION IF NOT EXISTS postgis;

CREATE TABLE IF NOT EXISTS documents (
  document_id bigserial PRIMARY KEY,
  source_path text NOT NULL UNIQUE,
  title text NOT NULL,
  domain text NOT NULL,
  kind text NOT NULL,
  mime_type text,
  revision_date date,
  file_bytes bigint,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS document_pages (
  page_id bigserial PRIMARY KEY,
  document_id bigint NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
  page_number integer NOT NULL,
  width numeric,
  height numeric,
  page_image_path text,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
  UNIQUE (document_id, page_number)
);

CREATE TABLE IF NOT EXISTS text_spans (
  span_id bigserial PRIMARY KEY,
  document_id bigint NOT NULL REFERENCES documents(document_id) ON DELETE CASCADE,
  page_id bigint REFERENCES document_pages(page_id) ON DELETE SET NULL,
  section_path text,
  span_kind text NOT NULL,
  text_value text NOT NULL,
  bbox jsonb,
  citation_label text,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_text_spans_section_path ON text_spans(section_path);

CREATE TABLE IF NOT EXISTS spatial_features (
  feature_id bigserial PRIMARY KEY,
  feature_source text NOT NULL,
  feature_class text NOT NULL,
  feature_name text,
  external_id text,
  jurisdiction text NOT NULL DEFAULT 'Charlottetown',
  geom geometry(Geometry, 4326) NOT NULL,
  attributes jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_spatial_features_geom ON spatial_features USING gist (geom);
CREATE INDEX IF NOT EXISTS idx_spatial_features_class ON spatial_features(feature_class);

CREATE TABLE IF NOT EXISTS parcels (
  parcel_id bigserial PRIMARY KEY,
  pid text UNIQUE,
  address_text text,
  geom geometry(MultiPolygon, 4326) NOT NULL,
  attributes jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_parcels_geom ON parcels USING gist (geom);

CREATE TABLE IF NOT EXISTS land_use_rules (
  rule_id bigserial PRIMARY KEY,
  rule_type text NOT NULL,
  subject text,
  use_name text,
  value_text text,
  numeric_value numeric,
  unit text,
  comparator text,
  condition_text text,
  source_span_id bigint REFERENCES text_spans(span_id) ON DELETE SET NULL,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_land_use_rules_type ON land_use_rules(rule_type);
CREATE INDEX IF NOT EXISTS idx_land_use_rules_use_name ON land_use_rules(use_name);

CREATE TABLE IF NOT EXISTS rule_applicability (
  applicability_id bigserial PRIMARY KEY,
  rule_id bigint NOT NULL REFERENCES land_use_rules(rule_id) ON DELETE CASCADE,
  feature_id bigint REFERENCES spatial_features(feature_id) ON DELETE CASCADE,
  applies_citywide boolean NOT NULL DEFAULT false,
  notes text,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS meetings (
  meeting_id bigserial PRIMARY KEY,
  body_name text NOT NULL,
  meeting_type text,
  meeting_date date NOT NULL,
  title text NOT NULL,
  source_document_id bigint REFERENCES documents(document_id) ON DELETE SET NULL,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_meetings_date ON meetings(meeting_date);
CREATE INDEX IF NOT EXISTS idx_meetings_body ON meetings(body_name);

CREATE TABLE IF NOT EXISTS agenda_items (
  agenda_item_id bigserial PRIMARY KEY,
  meeting_id bigint NOT NULL REFERENCES meetings(meeting_id) ON DELETE CASCADE,
  item_number text,
  title text NOT NULL,
  description text,
  source_span_id bigint REFERENCES text_spans(span_id) ON DELETE SET NULL,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS decisions (
  decision_id bigserial PRIMARY KEY,
  agenda_item_id bigint NOT NULL REFERENCES agenda_items(agenda_item_id) ON DELETE CASCADE,
  decision_type text NOT NULL,
  outcome text,
  vote_text text,
  effective_date date,
  source_span_id bigint REFERENCES text_spans(span_id) ON DELETE SET NULL,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS topics (
  topic_id bigserial PRIMARY KEY,
  topic_name text NOT NULL UNIQUE,
  topic_kind text,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE TABLE IF NOT EXISTS entity_links (
  link_id bigserial PRIMARY KEY,
  left_entity_type text NOT NULL,
  left_entity_id bigint NOT NULL,
  relation_type text NOT NULL,
  right_entity_type text NOT NULL,
  right_entity_id bigint NOT NULL,
  confidence numeric,
  source_span_id bigint REFERENCES text_spans(span_id) ON DELETE SET NULL,
  metadata jsonb NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_entity_links_left ON entity_links(left_entity_type, left_entity_id);
CREATE INDEX IF NOT EXISTS idx_entity_links_right ON entity_links(right_entity_type, right_entity_id);
