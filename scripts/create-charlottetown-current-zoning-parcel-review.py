from __future__ import annotations

import os

from sqlalchemy import create_engine, text


REVIEW_TABLE = "CHTWN_Current_Zoning_Parcel_Review"


def database_url() -> str:
    host = os.getenv("PGHOST", "localhost")
    port = os.getenv("PGPORT", "54329")
    database = os.getenv("PGDATABASE", "mdopendata")
    user = os.getenv("PGUSER", "mdopendata")
    password = os.getenv("PGPASSWORD", "mdopendata_dev")
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{database}"


def create_review_table(engine) -> None:
    sql = f"""
create index if not exists "CHTWN_Parcel_Map_geom_idx"
    on public."CHTWN_Parcel_Map"
    using gist (geom);

create index if not exists "CHTWN_Draft_Zoning_Boundaries_geom_idx"
    on public."CHTWN_Draft_Zoning_Boundaries"
    using gist (geom);

analyze public."CHTWN_Parcel_Map";
analyze public."CHTWN_Draft_Zoning_Boundaries";

drop table if exists public."{REVIEW_TABLE}";

create table public."{REVIEW_TABLE}" as
with draft_hits as (
    select
        p.fid,
        d.zone_code as draft_zone_code,
        d.zone_name as draft_zone_name,
        st_area(st_intersection(p.geom, d.geom)) as draft_match_area_m2
    from public."CHTWN_Parcel_Map" p
    join public."CHTWN_Draft_Zoning_Boundaries" d
        on p.geom && d.geom
        and st_intersects(p.geom, d.geom)
    where not st_isempty(st_intersection(p.geom, d.geom))
),
ranked_draft as (
    select
        *,
        row_number() over (
            partition by fid
            order by draft_match_area_m2 desc, draft_zone_code
        ) as draft_rank
    from draft_hits
),
best_draft as (
    select
        fid,
        draft_zone_code,
        draft_zone_name,
        draft_match_area_m2
    from ranked_draft
    where draft_rank = 1
)
select
    p.fid::bigint as fid,
    p.parcel_candidate_id::bigint as parcel_candidate_id,
    p.source_map::varchar as source_map,
    st_area(p.geom)::double precision as parcel_area_m2,
    b.draft_zone_code::text as draft_zone_code,
    b.draft_zone_name::text as draft_zone_name,
    case
        when st_area(p.geom) > 0 and b.draft_match_area_m2 is not null
            then (b.draft_match_area_m2 / st_area(p.geom))::double precision
        else null::double precision
    end as draft_match_fraction,
    null::text as map_legend_code_guess,
    null::text as zoning_code_guess,
    null::text as final_class_code_guess,
    null::text as zone_name_guess,
    0::integer as sample_count,
    0::integer as matched_sample_count,
    null::double precision as sample_match_fraction,
    null::text as mean_rgb,
    null::text as dominant_rgb,
    null::double precision as rgb_distance,
    false::boolean as pattern_detected,
    null::text as ambiguous_group,
    'draft_context_assist'::text as assignment_method,
    'low'::text as confidence,
    'needs_review'::text as review_status,
    50::integer as review_priority,
    null::text as final_map_legend_code,
    null::text as final_zoning_code,
    null::text as final_class_code,
    null::text as final_zone_name,
    null::text as review_notes,
    'maps/Charlottetown Zoning Map - March 9, 2026.pdf'::text as source_pdf,
    'data/spatial/charlottetown/charlottetown-zoning-map-2026-raster.gpkg'::text as source_raster,
    now()::timestamptz as created_at,
    null::timestamptz as updated_at,
    p.geom::geometry(MultiPolygon, 2954) as geom
from public."CHTWN_Parcel_Map" p
left join best_draft b
    on p.fid = b.fid;

alter table public."{REVIEW_TABLE}"
    add primary key (fid);

alter table public."{REVIEW_TABLE}"
    alter column parcel_area_m2 set not null,
    alter column sample_count set not null,
    alter column matched_sample_count set not null,
    alter column pattern_detected set not null,
    alter column assignment_method set not null,
    alter column confidence set not null,
    alter column review_status set not null,
    alter column review_priority set not null,
    alter column source_pdf set not null,
    alter column source_raster set not null,
    alter column created_at set not null,
    alter column geom set not null;

alter table public."{REVIEW_TABLE}"
    add constraint "{REVIEW_TABLE}_review_status_chk"
    check (review_status in ('auto_assigned', 'needs_review', 'reviewed', 'defer', 'exclude'));

alter table public."{REVIEW_TABLE}"
    add constraint "{REVIEW_TABLE}_confidence_chk"
    check (confidence in ('high', 'medium', 'low', 'manual'));

alter table public."{REVIEW_TABLE}"
    add constraint "{REVIEW_TABLE}_assignment_method_chk"
    check (assignment_method in ('solid_fill_raster_sample', 'pattern_raster_sample', 'draft_context_assist', 'manual_qgis_review', 'legacy_or_pseudo_zone'));

alter table public."{REVIEW_TABLE}"
    add constraint "{REVIEW_TABLE}_pseudo_zone_final_chk"
    check (
        final_class_code is null
        or final_class_code in ('NA', 'U')
        or final_zoning_code is not null
    );

create index "{REVIEW_TABLE}_geom_idx"
    on public."{REVIEW_TABLE}"
    using gist (geom);

create index "{REVIEW_TABLE}_status_idx"
    on public."{REVIEW_TABLE}" (review_status, review_priority);

create index "{REVIEW_TABLE}_final_class_idx"
    on public."{REVIEW_TABLE}" (final_class_code);

create index "{REVIEW_TABLE}_draft_zone_idx"
    on public."{REVIEW_TABLE}" (draft_zone_code);

analyze public."{REVIEW_TABLE}";
"""
    with engine.begin() as conn:
        conn.execute(text(sql))


def print_summary(engine) -> None:
    sql = f"""
select
    count(*) as parcels,
    count(*) filter (where draft_zone_code is null) as parcels_without_draft_context,
    count(*) filter (where geom is null) as null_geometries,
    count(*) filter (where not st_isvalid(geom)) as invalid_geometries,
    count(*) filter (where review_status = 'needs_review') as needs_review
from public."{REVIEW_TABLE}";
"""
    draft_sql = f"""
select draft_zone_code, count(*) as parcels
from public."{REVIEW_TABLE}"
group by draft_zone_code
order by parcels desc, draft_zone_code
limit 20;
"""
    with engine.begin() as conn:
        print(dict(conn.execute(text(sql)).mappings().one()))
        for row in conn.execute(text(draft_sql)).mappings():
            print(dict(row))


def main() -> None:
    engine = create_engine(database_url())
    create_review_table(engine)
    print_summary(engine)


if __name__ == "__main__":
    main()
