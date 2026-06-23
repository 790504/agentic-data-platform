-- Aggregate the flood-insurance source to one row per (county, quarter).
select
    county,
    quarter,
    avg(policies_count) as fema_policies_policies_count,
    avg(total_premium)  as fema_policies_total_premium
from {{ source('raw', 'fema_policies') }}
group by county, quarter
