import mysql.connector
import os
from dotenv import load_dotenv
import pandas as pd

# Import secrets
database_write_password = os.environ.get('database_write_password')

# Establish connection
mydb = mysql.connector.connect(
  host="f3stlouis.cac36jsyb5ss.us-east-2.rds.amazonaws.com",
  user="f3stcharles",
  password=database_write_password,
  database="f3stcharles"
)

schedule_master_create = """
CREATE TABLE schedule_master (
	ao_channel_id varchar(255) NOT NULL,
	event_date date NOT NULL,
	event_time time NOT NULL,
    event_day_of_week varchar(255) NOT NULL,
	event_type varchar(255) NOT NULL,
	event_special varchar(255),
	event_recurring boolean NOT NULL,
	CONSTRAINT pk_schedule_master PRIMARY KEY (ao_channel_id, event_date, event_time)
);
"""
schedule_weekly_create = """
CREATE TABLE schedule_weekly (
	ao_channel_id varchar(255) NOT NULL,
	event_day_of_week varchar(255) NOT NULL,
	event_time time NOT NULL,
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

# Execute
mycursor = mydb.cursor()
mycursor.execute(schedule_master_create)
mycursor.execute(schedule_weekly_create)
mycursor.execute(schedule_aos_create)
mycursor.execute("COMMIT;")

# Test
master_df = pd.read_sql('SELECT * FROM schedule_master;', mydb)
weekly_df = pd.read_sql('SELECT * FROM schedule_weekly;', mydb)
aos_df = pd.read_sql('SELECT * FROM schedule_aos;', mydb)

# Insert some data