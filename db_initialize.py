import mysql.connector
import pandas as pd
from decouple import config, UndefinedValueError


# db config
db_config = {
    "host":"f3stlouis.cac36jsyb5ss.us-east-2.rds.amazonaws.com",
    "user":config('DATABASE_USER'), 
    "password":config('DATABASE_WRITE_PASSWORD'),
    "database":config('DATABASE_SCHEMA') 
}

# Table schemas
schedule_master_create = """
CREATE TABLE schedule_master (
	ao_channel_id varchar(255) NOT NULL,
	event_date date NOT NULL,
	event_time varchar(255) NOT NULL,
    event_day_of_week varchar(255) NOT NULL,
	event_type varchar(255) NOT NULL,
	event_special varchar(255),
	event_recurring boolean NOT NULL,
	q_pax_id varchar(255),
	q_pax_name varchar(255),
	CONSTRAINT pk_schedule_master PRIMARY KEY (ao_channel_id, event_date, event_time)
);
"""
schedule_weekly_create = """
CREATE TABLE schedule_weekly (
	ao_channel_id varchar(255) NOT NULL,
	event_day_of_week varchar(255) NOT NULL,
	event_time varchar(255) NOT NULL,
	event_type varchar(255) NOT NULL,
	CONSTRAINT pk_schedule_weekly PRIMARY KEY (ao_channel_id, event_day_of_week, event_time)
);
"""

schedule_aos_create = """
CREATE TABLE schedule_aos (
	ao_channel_id varchar(255) NOT NULL,
	ao_display_name varchar(255) NOT NULL,
	ao_location_subtitle varchar(255) NOT NULL,
	CONSTRAINT pk_schedule_aos PRIMARY KEY (ao_channel_id)
);
"""

schedule_weinkes_create = """
CREATE TABLE schedule_weinkes (
	region_schema varchar(255) NOT NULL,
	current_week_weinke varchar(255),
	next_week_weinke varchar(255),
	CONSTRAINT pk_schedule_weinkes PRIMARY KEY (region_schema)
);
"""

# Execute
with mysql.connector.connect(**db_config) as mydb:
	mycursor = mydb.cursor()
	mycursor.execute(schedule_master_create)
	mycursor.execute(schedule_weekly_create)
	mycursor.execute(schedule_aos_create)
	mycursor.execute(schedule_weinkes_create)
	mycursor.execute("COMMIT;")

