-- Singular test: (county, quarter) must be unique in the panel.
-- Passes when this query returns zero rows.
select
    county,
    quarter,
    count(*) as n
from {{ ref('county_quarter_panel') }}
group by county, quarter
having count(*) > 1
