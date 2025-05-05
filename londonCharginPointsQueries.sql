create database london_ev_db_rds;

use london_ev_db_rds;
create table charingpointssatustable(
  id int, 
  sourcesystemplaceid varchar(50),
  status varchar(50),
  record_insert_time timestamp);


select * from charingpointssatustable
where status like '%Out%'
order by sourcesystemplaceid ;

-- pivot and calculate duration for each of the status for every charging station
with cte as (
select id,sourcesystemplaceid,status,record_insert_time as start_time,
timestampdiff(minute,record_insert_time,
		lead(record_insert_time,1,current_timestamp) over(partition by sourcesystemplaceid order by record_insert_time)
        ) duration
from charingpointssatustable
-- where sourcesystemplaceid like 'ChargePointESB-UT063R-1'
),
cte2 as (
select sourcesystemplaceid,
case when status='Charging' then duration else 0 end as Charging,
case when status='Available' then duration else 0 end as Available,
case when status='Unavailable' then (duration) else 0 end as Unavailable,
case when status='OutOfService' then (duration) else 0 end as OutOfService,
case when status='Unknown' then (duration) else 0 end as 'Unknown'
from cte)
select sourcesystemplaceid,
sum(Charging) Charging,
sum(Available) Available,
sum(Unavailable) Unavailable,
sum(OutOfService) OutOfService,
sum(Unknown) 'Unknown'
from cte2
group by sourcesystemplaceid;


