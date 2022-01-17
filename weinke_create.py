import os
from sqlite3.dbapi2 import Timestamp
from typing import Text
from numpy import nan
from pandas.core.reshape.merge import merge

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dotenv import load_dotenv
import pickle
import pandas as pd
import sqlite3
import sys
from datetime import datetime, date, timedelta
from slack_sdk import WebClient
import dataframe_image as dfi

query = """
SELECT *
FROM schedule_master
"""

with sqlite3.connect('data/schedule.db') as conn:
    df = pd.read_sql_query(query, conn)

df['date_time'] = pd.to_datetime(df['date'] + ' ' + df['time'], infer_datetime_format=True)
df['date'] = df['date_time'].dt.strftime("%m/%d")  #.dt.date
df['month_name'] = pd.DatetimeIndex(df['date_time']).month_name()
df['day_of_week'] = pd.DatetimeIndex(df['date_time']).day_name()
df['year_num'] = pd.DatetimeIndex(df['date_time']).year
df['week_num'] = pd.Int64Index(pd.DatetimeIndex(df['date_time']).isocalendar().week)
df['day_num'] = pd.DatetimeIndex(df['date_time']).day

year_select = 2022
week_select = 2

df = df[(df.year_num==year_select) & (df.week_num==week_select)]
df.reset_index(inplace=True)

df.loc[0, 'pax_name'] = 'SlowPitch'
df.loc[2, 'pax_name'] = 'Moneyball'
df.loc[3, 'pax_name'] = 'DD'
df.loc[4, 'pax_name'] = 'Tinkle'
df.loc[5, 'pax_name'] = 'Default'
df.loc[6, 'pax_name'] = 'Moneyball\nThe Forge'
df.loc[6, 'time'] = '5:15'
df.loc[7, 'pax_name'] = 'Elway'
df.loc[8, 'pax_name'] = 'Moneyball'
df.loc[9, 'pax_name'] = 'Audible'
df.loc[10, 'pax_name'] = 'Moneyball'
df.loc[11, 'pax_name'] = 'Clapper'
df.loc[12, 'pax_name'] = 'Pothole'
df.loc[13, 'pax_name'] = 'Peter Parker'
df.loc[14, 'pax_name'] = 'Moneyball'
df.loc[15, 'pax_name'] = 'SlowPitch'

df.loc[df['pax_name'].isna(), 'pax_name'] = 'OPEN!'
df['label'] = df['pax_name'] + '\n' + df['time']

ao_list = pd.read_csv('data/ao_list.csv')
df = pd.merge(df, ao_list, on=['ao'], how='left')
df['AO\nLocation'] = df['ao_name_fmt'] + '\n' + df['ao_location']

df.sort_values(by=['AO\nLocation'], inplace=True)
df2 = df.pivot(index='AO\nLocation', columns=['day_of_week', 'date'], values='label').fillna("")

df2.sort_index(axis=1, level=['date'], inplace=True)
df2.columns = df2.columns.map('\n'.join).str.strip('\n')
df2.reset_index(inplace=True)

# Set CSS properties for th elements in dataframe
th_props = [
  ('font-size', '15px'),
  ('text-align', 'center'),
  ('font-weight', 'bold'),
#   ('color', '#6d6d6d'),
#   ('background-color', '#f7f7f9'),
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


df_styled = df2.style.set_table_styles(styles).hide_index()

dfi.export(df_styled,"mytable.png")
