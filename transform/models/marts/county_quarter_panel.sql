-- Integrate the three staged sources into one analysis-ready county-quarter panel.
-- USING(...) joins keep this portable across DuckDB / MotherDuck / BigQuery.
select
    f.county,
    f.quarter,
    f.fema_policies_policies_count,
    f.fema_policies_total_premium,
    p.property_sales_median_sale_price,
    p.property_sales_sales_count,
    h.hmda_loans_loan_count,
    h.hmda_loans_total_loan_amount
from {{ ref('stg_fema_policies') }} as f
inner join {{ ref('stg_property_sales') }} as p using (county, quarter)
inner join {{ ref('stg_hmda_loans') }} as h using (county, quarter)
