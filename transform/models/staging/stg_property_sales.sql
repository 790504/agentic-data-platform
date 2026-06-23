-- Aggregate the property-transaction source to one row per (county, quarter).
select
    county,
    quarter,
    avg(median_sale_price) as property_sales_median_sale_price,
    avg(sales_count)       as property_sales_sales_count
from {{ source('raw', 'property_sales') }}
group by county, quarter
