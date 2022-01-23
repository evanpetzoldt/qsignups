
from decouple import config, UndefinedValueError
import pandas as pd
import mysql.connector
from datetime import datetime, date, timedelta
import dataframe_image as dfi

# DB config
db_config = {
    "host":"f3stlouis.cac36jsyb5ss.us-east-2.rds.amazonaws.com",
    "user":config('DATABASE_USER'), 
    "password":config('DATABASE_WRITE_PASSWORD'),
    "database":config('DATABASE_SCHEMA') 
}

async def weinke_create(db_config):

  # Figure out current and next weeks based on current start of day
  # I have the week start on Monday and end on Sunday - if this is run on Sunday, "current" week will start tomorrow
  tomorrow_day_of_week = (date.today() + timedelta(days=1)).weekday()
  current_week_start = date.today() + timedelta(days=-tomorrow_day_of_week+1)
  current_week_end = date.today() + timedelta(days=7-tomorrow_day_of_week)
  next_week_start = current_week_start + timedelta(weeks=1)
  next_week_end = current_week_end + timedelta(weeks=1)

  # Generate SQL pulls
  sql_current = f"""
  SELECT m.*, a.ao_display_name, a.ao_location_subtitle
  FROM schedule_master m
  LEFT JOIN schedule_aos a
  ON m.ao_channel_id = a.ao_channel_id
  WHERE m.event_date >= DATE('{current_week_start}')
    AND m.event_date <= DATE('{current_week_end}');
  """

  sql_next = f"""
  SELECT m.*, a.ao_display_name, a.ao_location_subtitle
  FROM schedule_master m
  LEFT JOIN schedule_aos a
  ON m.ao_channel_id = a.ao_channel_id
  WHERE m.event_date >= DATE('{next_week_start}')
    AND m.event_date <= DATE('{next_week_end}');
  """

  # Pull data
  try:
    with mysql.connector.connect(**db_config) as mydb:
      df_current = pd.read_sql_query(sql_current, mydb, parse_dates=['event_date'])
      df_next = pd.read_sql_query(sql_next, mydb, parse_dates=['event_date'])
  except Exception as e:
    print(f'There was a problem pull from the db: {e}')

  df_list = [
    [df_current, 'current_week_weinke'],
    [df_next, 'next_week_weinke']
  ]

  for week in df_list:
    df = week[0]
    output_name = week[1]

    # date operations
    df['event_date_fmt'] = df['event_date'].dt.strftime("%m/%d")

    # Reset index
    df.reset_index(inplace=True)

    # Build cell labels
    df.loc[df['q_pax_name'].isna(), 'q_pax_name'] = 'OPEN!'
    df['label'] = df['q_pax_name'] + '\n' + df['event_time']
    df['AO\nLocation'] = df['ao_display_name'] + '\n' + df['ao_location_subtitle']

    # Reshape to wide format by date
    df.sort_values(by=['AO\nLocation'], inplace=True)
    df2 = df.pivot(index='AO\nLocation', columns=['event_day_of_week', 'event_date_fmt'], values='label').fillna("")

    # Sort and enforce word wrap on labels
    df2.sort_index(axis=1, level=['event_date_fmt'], inplace=True)
    df2.columns = df2.columns.map('\n'.join).str.strip('\n')
    df2.reset_index(inplace=True)

    # Set CSS properties for th elements in dataframe
    th_props = [
      ('font-size', '15px'),
      ('text-align', 'center'),
      ('font-weight', 'bold'),
      ('color', '#F0FFFF'),
      ('background-color', '#000000'),
      ('white-space', 'pre-wrap'),
      ('border', '1px solid #F0FFFF')
      ]

    # Set CSS properties for td elements in dataframe
    td_props = [
      ('font-size', '15px'),
      ('text-align', 'center'),
      ('white-space', 'pre-wrap'),
      ('background-color', '#000000'),
      ('color', '#F0FFFF'),
      ('border', '1px solid #F0FFFF')
      ]

    # Set table styles
    styles = [
      dict(selector="th", props=th_props),
      dict(selector="td", props=td_props)
      ]

    # set style and export png
    df_styled = df2.style.set_table_styles(styles).hide_index()
    dfi.export(df_styled,f"weinkes/{output_name}.png")
