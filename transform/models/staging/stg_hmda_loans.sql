-- Aggregate the mortgage source to one row per (county, quarter).
select
    county,
    quarter,
    avg(loan_count)        as hmda_loans_loan_count,
    avg(total_loan_amount) as hmda_loans_total_loan_amount
from {{ source('raw', 'hmda_loans') }}
group by county, quarter
