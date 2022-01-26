import logging
# from sre_constants import SUCCESS
from decouple import config, UndefinedValueError
from fastapi import FastAPI, Request
from slack_bolt.adapter.fastapi.async_handler import AsyncSlackRequestHandler
from slack_bolt.async_app import AsyncApp
import datetime
from datetime import datetime, timezone, timedelta, date
import json
import pandas as pd
import mysql.connector
from mysql.connector.optionfiles import MySQLOptionsParser
import os
import sqlalchemy
import dataframe_image as dfi
from weinke_create import weinke_create


# def get_categories():
#     with open('categories.json') as c:
#         data = json.load(c)
#         return data


# def formatted_categories(filteredcats):
#     opts = []
#     for cat in filteredcats:
#         x = {
#             "text": {
#                 "type": "plain_text",
#                 "text": cat["name"]
#             },
#             "value": str(cat["id"])
#         }
#         opts.append(x)
#     return opts

# I think this is only used for email stuff at the moment
OPTIONAL_INPUT_VALUE = "None"

schedule_create_length_days = 365
results_load = 20

# Configure mysql db
db_config = {
    "host":"f3stlouis.cac36jsyb5ss.us-east-2.rds.amazonaws.com",
    "user":config('DATABASE_USER'), 
    "password":config('DATABASE_WRITE_PASSWORD'),
    "database":config('DATABASE_SCHEMA') 
}


logging.basicConfig(level=logging.DEBUG)
#categories = []

slack_app = AsyncApp(
    token=config('SLACK_BOT_TOKEN'),
    signing_secret=config('SLACK_SIGNING_SECRET')
)
app_handler = AsyncSlackRequestHandler(slack_app)

#categories = get_categories()


@slack_app.middleware  # or app.use(log_request)
async def log_request(logger, body, next):
    logger.debug(body)
    return await next()


@slack_app.event("app_mention")
async def event_test(body, say, logger):
    logger.info(body)
    await say("What's up yo?")


@slack_app.event("message")
async def handle_message():
    pass


def safeget(dct, *keys):
    for key in keys:
        try:
            dct = dct[key]
        except KeyError:
            return None
    return dct


def get_channel_id_and_name(body, logger):
    # returns channel_iid, channel_name if it exists as an escaped parameter of slashcommand
    user_id = body.get("user_id")
    # Get "text" value which is everything after the /slash-command
    # e.g. /slackblast #our-aggregate-backblast-channel
    # then text would be "#our-aggregate-backblast-channel" if /slash command is not encoding
    # but encoding needs to be checked so it will be "<#C01V75UFE56|our-aggregate-backblast-channel>" instead
    channel_name = body.get("text") or ''
    channel_id = ''
    try:
        channel_id = channel_name.split('|')[0].split('#')[1]
        channel_name = channel_name.split('|')[1].split('>')[0]
    except IndexError as ierr:
        logger.error('Bad user input - cannot parse channel id')
    except Exception as error:
        logger.error('User did not pass in any input')
    return channel_id, channel_name


async def get_channel_name(id, logger, client):
    channel_info_dict = await client.conversations_info(
        channel=id
    )
    channel_name = safeget(channel_info_dict, 'channel', 'name') or None
    logger.info('channel_name is {}'.format(channel_name))
    return channel_name


async def get_user_names(array_of_user_ids, logger, client):
    names = []
    for user_id in array_of_user_ids:
        user_info_dict = await client.users_info(
            user=user_id
        )
        user_name = safeget(user_info_dict, 'user', 'profile', 'display_name') or safeget(
            user_info_dict, 'user', 'profile', 'real_name') or None
        if user_name:
            names.append(user_name)
        logger.info('user_name is {}'.format(user_name))
    logger.info('names are {}'.format(names))
    return names


















async def refresh_home_tab(client, user_id, logger, top_message):
    # list of upcoming Qs for user
    sql_upcoming_qs = f"""
    SELECT m.*, a.ao_display_name
    FROM schedule_master m
    LEFT JOIN schedule_aos a
    ON m.ao_channel_id = a.ao_channel_id
    WHERE m.q_pax_id = "{user_id}"
    ORDER BY m.event_date, m.event_time
    LIMIT 5;
    """
    upcoming_qs_df = pd.DataFrame()
    try:
        with mysql.connector.connect(**db_config) as mydb:
            upcoming_qs_df = pd.read_sql(sql_upcoming_qs, mydb, parse_dates=['event_date'])
    except Exception as e:
        logger.error(f"Error pulling upcoming qs: {e}")

    if len(upcoming_qs_df) > 0:
        top_message += ' You have some upcoming Qs:'
        for index, row in upcoming_qs_df.iterrows():
            dt_fmt = row['event_date'].strftime("%A, %B %-d")
            top_message += f"\n* {dt_fmt} @ {row['event_time']} at {row['ao_display_name']}" 
    
    # list of AOs for dropdown
    sql_ao_list = "SELECT * FROM schedule_aos ORDER BY ao_display_name;"
    try:
        with mysql.connector.connect(**db_config) as mydb:
            ao_list = pd.read_sql(sql_ao_list, mydb)
    except Exception as e:
        logger.error(f"Error pulling AO list: {e}")

    # Build AO options list
    options = []
    for index, row in ao_list.iterrows():
        new_option = {
            "text": {
                "type": "plain_text",
                "text": row['ao_display_name']
            },
            "value": row['ao_channel_id']
        }
        options.append(new_option)
    
    # Build view blocks
    blocks = [
        {
            "type": "section",
            "block_id": "section678",
            "text": {
                "type": "mrkdwn",
                "text": top_message
            }
        },
        {
            "type": "divider"
        },
        {
            "type": "section",
            "block_id": "ao_select_block",
            "text": {
                "type": "mrkdwn",
                "text": "Please select an AO to take a Q slot:"
            },
            "accessory": {
                "action_id": "ao-select",
                "type": "static_select",
                "placeholder": {
                    "type": "plain_text",
                    "text": "Select an AO"
            },
            "options": options
            }
        }
    ]

    # Optionally add admin button
    user_info_dict = await client.users_info(
        user=user_id
    )
    if user_info_dict['user']['is_admin']:
        admin_button = {
            "type":"actions",
            "elements":[
                {
                    "type":"button",
                    "text":{
                        "type":"plain_text",
                        "text":"Manage Region Calendar",
                        "emoji":True
                    },
                    "action_id":"manage_schedule_button"
                }
            ]
        }
        blocks.append(admin_button)

    # Attempt to publish view
    try:
        await client.views_publish(
            user_id=user_id,
            token=config('SLACK_BOT_TOKEN'),
            view={
                "type": "home",
                "blocks":blocks
            }
        )
    except Exception as e:
        logger.error(f"Error publishing home tab: {e}")
        print(e)



# triggered when user selects home screen
@slack_app.event("app_home_opened")
async def update_home_tab(client, event, logger):
    logger.info(event)
    user_id = event["user"]
    user_name = (await get_user_names([user_id], logger, client))[0]
    top_message = f'Welcome to QSignups, {user_name}!' 
    await refresh_home_tab(client, user_id, logger, top_message)

# triggers when user chooses to schedule a q
@slack_app.action("schedule_q_button")
async def handle_take_q_button(ack, body, client, logger):
    await ack()
    logger.info(body)
    user_id = body["user"]["id"]
    await refresh_home_tab(client, user_id, logger)

# triggers when user chooses to manager the schedule
@slack_app.action("manage_schedule_button")
async def handle_manager_schedule_button(ack, body, client, logger):
    await ack()
    logger.info(body)
    user_id = body["user"]["id"]
    
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Choose an option for managing the schedule:"
            }
        }
    ]

    button_list = [
        "Add an AO",
        "Add an event"
    ]

    for button in button_list:
        new_block = {
            "type":"actions",
            "elements":[
                {
                    "type":"button",
                    "text":{
                        "type":"plain_text",
                        "text":button,
                        "emoji":True
                    },
                    "action_id":"manage_schedule_option_button",
                    "value":button
                }
            ]
        }
        blocks.append(new_block)

    try:
        await client.views_publish(
            user_id=user_id,
            token=config('SLACK_BOT_TOKEN'),
            view={
                "type": "home",
                "blocks": blocks
            }
        )
    except Exception as e:
        logger.error(f"Error publishing home tab: {e}")
        print(e)

# triggers when user selects a manage schedule option
@slack_app.action("manage_schedule_option_button")
async def handle_manage_schedule_option_button(ack, body, client, logger):
    await ack()
    logger.info(body)

    selected_action = body['actions'][0]['value']
    user_id = body["user"]["id"]

    # 'Add an AO' selected
    if selected_action == 'Add an AO':
        logger.info('gather input data')
        blocks = [
            {
                "type": "input",
                "block_id": "ao_display_name",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "ao_display_name",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Weasel's Ridge"
                    }
                },
                "label": {
                    "type": "plain_text",
                    "text": "AO Title"
                }
            },
            {
                "type": "input",
                "block_id": "ao_channel_id",
                "element": {
                    "type": "channels_select",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Select the AO",
                        "emoji": True
                    },
                    "action_id": "ao_channel_id"
                },
                "label": {
                    "type": "plain_text",
                    "text": "Slack channel",
                    "emoji": True
                }
            },
            {
                "type": "input",
                "block_id": "ao_location_subtitle",
                "element": {
                    "type": "plain_text_input",
                    "action_id": "ao_location_subtitle",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Oompa Loompa Kingdom"
                    }
                },
                "label": {
                    "type": "plain_text",
                    "text": "Location (township, park, etc.)"
                }
            }
        ]

        action_button = {
            "type":"actions",
            "elements":[
                {
                    "type":"button",
                    "text":{
                        "type":"plain_text",
                        "text":"Submit",
                        "emoji":True
                    },
                    "action_id":"submit_add_ao_button",
                    "style":"primary",
                    "value":"Submit"
                }
            ]    
        }
        cancel_button = {
            "type":"actions",
            "elements":[
                {
                    "type":"button",
                    "text":{
                        "type":"plain_text",
                        "text":"Cancel",
                        "emoji":True
                    },
                    "action_id":"cancel_button_select",
                    "style":"danger",
                    "value":"Cancel"
                }
            ]    
        }
        blocks.append(action_button)
        blocks.append(cancel_button)

        try:
            await client.views_publish(
                user_id=user_id,
                token=config('SLACK_BOT_TOKEN'),
                view={
                    "type": "home",
                    "blocks": blocks
                }
            )
        except Exception as e:
            logger.error(f"Error publishing home tab: {e}")
            print(e)
    elif selected_action == 'Add an event':
        logging.info('add an event')

        # list of AOs for dropdown
        sql_ao_list = "SELECT ao_display_name FROM schedule_aos ORDER BY ao_display_name;"
        try:
            with mysql.connector.connect(**db_config) as mydb:
                ao_list = pd.read_sql(sql_ao_list, mydb)
                ao_list = ao_list['ao_display_name'].values.tolist()
        except Exception as e:
            logger.error(f"Error pulling AO list: {e}")

        ao_options = []
        for option in ao_list:
            new_option = {
                "text": {
                    "type": "plain_text",
                    "text": option,
                    "emoji": True
                },
                "value": option
            }
            ao_options.append(new_option)

        day_list = [
            'Monday',
            'Tuesday',
            'Wednesday',
            'Thursday',
            'Friday',
            'Saturday',
            'Sunday'
        ]
        day_options = []
        for option in day_list:
            new_option = {
                "text": {
                    "type": "plain_text",
                    "text": option,
                    "emoji": True
                },
                "value": option
            }
            day_options.append(new_option)

        blocks = [
            {
                "type": "input",
                "block_id": "ao_display_name_select",
                "element": {
                    "type": "static_select",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Select an AO",
                        "emoji": True   
                    },
                    "options": ao_options,
                    "action_id": "ao_display_name_select_action"
                },
                "label": {
                    "type": "plain_text",
                    "text": "AO",
                    "emoji": True
                }  
            },
            {
                "type": "input",
                "block_id": "event_day_of_week_select",
                "element": {
                    "type": "static_select",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Select a day",
                        "emoji": True   
                    },
                    "options": day_options,
                    "action_id": "event_day_of_week_select_action"
                },
                "label": {
                    "type": "plain_text",
                    "text": "Day of Week",
                    "emoji": True
                }  
            },
            {
                "type": "input",
                "block_id": "event_time_select",
                "element": {
                    "type": "timepicker",
                    "initial_time": "05:30",
                    "placeholder": {
                        "type": "plain_text",
                        "text": "Select time",
                        "emoji": True
                    },
                    "action_id": "event_time_select"
                },
                "label": {
                    "type": "plain_text",
                    "text": "Beatdown Start",
                    "emoji": True
                }
		    },
            {
                "type": "actions",
                "block_id": "submit_cancel_buttons",
                "elements": [
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Submit",
                            "emoji": True
                        },
                        "value": "submit",
                        "action_id": "submit_add_event_button",
                        "style": "primary"
                    },
                    {
                        "type": "button",
                        "text": {
                            "type": "plain_text",
                            "text": "Cancel",
                            "emoji": True
                        },
                        "value": "cancel",
                        "action_id": "cancel_button_select",
                        "style": "danger"
                    }
                ]
            }
        ]
        try:
            await client.views_publish(
                user_id=user_id,
                token=config('SLACK_BOT_TOKEN'),
                view={
                    "type": "home",
                    "blocks": blocks
                }
            )
        except Exception as e:
            logger.error(f"Error publishing home tab: {e}")
            print(e)

@slack_app.action("submit_add_ao_button")
async def handle_submit_add_ao_button(ack, body, client, logger):
    await ack()
    logger.info(body)
    user_id = body['user']['id']

    # Gather inputs from form
    input_data = body['view']['state']['values']
    ao_channel_id = input_data['ao_channel_id']['ao_channel_id']['selected_channel']
    ao_display_name = input_data['ao_display_name']['ao_display_name']['value']
    ao_location_subtitle = input_data['ao_location_subtitle']['ao_location_subtitle']['value']

    # Generate SQL INSERT statement
    sql_insert = f"""
    INSERT INTO schedule_aos (ao_channel_id, ao_display_name, ao_location_subtitle)
    VALUES ("{ao_channel_id}", "{ao_display_name}", "{ao_location_subtitle}")
    """

    # Write to AO table
    logger.info(f"Attempting SQL INSERT: {sql_insert}")
    success_status = False
    try:
        with mysql.connector.connect(**db_config) as mydb:
            mycursor = mydb.cursor()
            mycursor.execute(sql_insert)
            mycursor.execute("COMMIT;")
            success_status = True
    except Exception as e:
        logger.error(f"Error writing to db: {e}")
        error_msg = e

    # Take the user back home
    if success_status:
        top_message = f"Success! Added {ao_display_name} to the list of AOs on the schedule"
    else:
        top_message = f"Sorry, there was a problem of some sort; please try again or contact your local administrator / Weasel Shaker. Error:\n{error_msg}"
    
    await refresh_home_tab(client, user_id, logger, top_message)

@slack_app.action("submit_add_event_button")
async def handle_submit_add_event_button(ack, body, client, logger):
    await ack()
    logger.info(body)  
    user_id = body['user']['id']

    # Gather inputs from form
    input_data = body['view']['state']['values']
    ao_display_name = input_data['ao_display_name_select']['ao_display_name_select_action']['selected_option']['value']
    event_day_of_week = input_data['event_day_of_week_select']['event_day_of_week_select_action']['selected_option']['value']
    event_time = input_data['event_time_select']['event_time_select']['selected_time'].replace(':','')
    event_type = 'Beatdown' # eventually this will be dynamic
    event_recurring = True # this would be false for one-time events

    # Grab channel id
    try:
        with mysql.connector.connect(**db_config) as mydb:
            mycursor = mydb.cursor()
            mycursor.execute(f'SELECT ao_channel_id FROM schedule_aos WHERE ao_display_name = "{ao_display_name}";')
            ao_channel_id = mycursor.fetchone()[0]
    except Exception as e:
           logger.error(f"Error pulling from db: {e}")

    # Generate SQL INSERT statement
    sql_insert = f"""
INSERT INTO schedule_weekly (ao_channel_id, event_day_of_week, event_time, event_type)
VALUES ("{ao_channel_id}", "{event_day_of_week}", "{event_time}", "{event_type}");
    """

    # Write to weekly table
    logger.info(f"Attempting SQL INSERT: {sql_insert}")
    try:
        with mysql.connector.connect(**db_config) as mydb:
            mycursor = mydb.cursor()
            mycursor.execute(sql_insert)
            mycursor.execute("COMMIT;")
    except Exception as e:
           logger.error(f"Error writing to db: {e}")

    # Write to master schedule table
    logger.info(f"Attempting SQL INSERT into schedule_master")
    success_status = False
    try:
        with mysql.connector.connect(**db_config) as mydb:
            mycursor = mydb.cursor()
            iterate_date = date.today()
            while iterate_date < (date.today() + timedelta(days=schedule_create_length_days)):
                if iterate_date.strftime('%A') == event_day_of_week:
                    sql_insert = f"""
            INSERT INTO schedule_master (ao_channel_id, event_date, event_time, event_day_of_week, event_type, event_recurring)
            VALUES ("{ao_channel_id}", DATE("{iterate_date}"), "{event_time}", "{event_day_of_week}", "{event_type}", {event_recurring})    
                    """
                    mycursor.execute(sql_insert)
                    # print(sql_insert)
                iterate_date += timedelta(days=1)

            mycursor.execute("COMMIT;")
            success_status = True
    except Exception as e:
           logger.error(f"Error writing to schedule_master: {e}")
           error_msg = e

    # Give status message and return to home
    if success_status:
        top_message = f"Thanks, I got it! I've added {round(schedule_create_length_days/365)} year's worth of {event_type}s to the schedule for {event_day_of_week}s at {event_time} at {ao_display_name}."
    else:
        top_message = f"Sorry, there was an error of some sort; please try again or contact your local administrator / Weasel Shaker. Error:\n{error_msg}"
    await refresh_home_tab(client, user_id, logger, top_message)


# triggered when user makes an ao selection
@slack_app.action("ao-select")
async def ao_select_slot(ack, client, body, logger):
    # acknowledge action and log payload
    await ack()
    logger.info(body)
    
    user_id = body['user']['id']
    ao_display_name = body['actions'][0]['selected_option']['text']['text']
    ao_channel_id = body['actions'][0]['selected_option']['value']

    # Generate SQL pull
    # TODO: make this specific to event type
    sql_pull = f"""
    SELECT *
    FROM schedule_master
    WHERE ao_channel_id = '{ao_channel_id}'
        AND event_date > DATE('{date.today()}')
    LIMIT {results_load};
    """

    # Pull upcoming schedule from db
    logging.info(f'Pulling from db, attempting SQL: {sql_pull}')
    try:
        with mysql.connector.connect(**db_config) as mydb:
            results_df = pd.read_sql_query(sql_pull, mydb, parse_dates=['event_date'])
    except Exception as e:
        logger.error(f"Error pulling from schedule_master: {e}")

    # Construct view
    # Top of view
    blocks = [{
        "type": "section",
        "text": {"type": "mrkdwn", "text": "Please select an open Q slot for:"}
    },
    {
        "type": "section",
        "text": {"type": "mrkdwn", "text": f"*{ao_display_name}*"}
    },
    {
        "type": "divider"
    }]

    # Show next x number of events
    # TODO: future add: make a "show more" button?
    results_df['event_date_time'] = pd.to_datetime(results_df['event_date'].dt.strftime('%Y-%m-%d') + ' ' + results_df['event_time'], infer_datetime_format=True)
    for index, row in results_df.iterrows():
        # Pretty format date
        date_fmt = row['event_date_time'].strftime("%A, %B %-d @ %H%M")
        
        # If slot is empty, show green button with primary (green) style button
        if row['q_pax_id'] is None:
            date_status = "OPEN!"
            date_style = "primary"
            action_id = "date_select_button"
        # Otherwise default (grey) button, listing Qs name
        else:
            date_status = row['q_pax_name']
            date_style = "default"
            action_id = "date_select_button_ignore" # this button action is ignored for now
        
        # TODO: add functionality to take self off schedule by clicking your already taken slot?
        # Button template
        new_button = {
            "type":"actions",
            "elements":[
                {
                    "type":"button",
                    "text":{
                        "type":"plain_text",
                        "text":f"{date_fmt}: {date_status}",
                        "emoji":True
                    },
                    "action_id":action_id,
                    "value":str(row['event_date_time'])
                }
            ]
        }
        if date_style == "primary":
            new_button['elements'][0]["style"] = "primary"
        
        # Append button to list
        blocks.append(new_button)
    
    # Cancel button
    new_button = {
        "type":"actions",
        "elements":[
            {
                "type":"button",
                "text":{
                    "type":"plain_text",
                    "text":"Cancel",
                    "emoji":True
                },
                "action_id":"cancel_button_select",
                "value":"cancel",
                "style":"danger"
            }
        ]
    }
    blocks.append(new_button)
    
    # Publish view
    try:
        await client.views_publish(
            user_id=user_id,
            token=config('SLACK_BOT_TOKEN'),
            view={
                "type": "home",
                "blocks": blocks
            }
        )
    except Exception as e:
        logger.error(f"Error publishing home tab: {e}")
        print(e)

# triggered when user selects open slot
@slack_app.action("date_select_button")
async def handle_date_select_button(ack, client, body, logger):
    # acknowledge action and log payload
    await ack()
    logger.info(body)
    user_id = body['user']['id']
    user_name = (await get_user_names([user_id], logger, client))[0]

    # gather and format selected date and time
    selected_date = body['actions'][0]['value']
    selected_date_dt = datetime.strptime(selected_date, '%Y-%m-%d %H:%M:%S')
    selected_date_db = datetime.date(selected_date_dt).strftime('%Y-%m-%d')
    selected_time_db = datetime.time(selected_date_dt).strftime('%H%M')
    
    # gather info needed for message and SQL
    ao_display_name = body['view']['blocks'][1]['text']['text'].replace('*','')
    sql_channel_pull = f'SELECT ao_channel_id FROM schedule_aos WHERE ao_display_name = "{ao_display_name}";'
    
    try:
        with mysql.connector.connect(**db_config) as mydb:
            ao_channel_id = pd.read_sql_query(sql_channel_pull, mydb).iloc[0,0]
    except Exception as e:
        logger.error(f"Error pulling channel id: {e}")

    # Generate SQL Statement
    sql_update = \
    f"""
    UPDATE schedule_master 
    SET q_pax_id = '{user_id}'
        , q_pax_name = '{user_name}'
    WHERE ao_channel_id = '{ao_channel_id}'
        AND event_date = DATE('{selected_date_db}')
        AND event_time = '{selected_time_db}'
    ;
    """
    
    # Attempt db update
    logging.info(f'Attempting SQL UPDATE: {sql_update}')
    success_status = False
    try:
        with mysql.connector.connect(**db_config) as mydb:
            mycursor = mydb.cursor()
            mycursor.execute(sql_update)
            mycursor.execute("COMMIT;")
            success_status = True
    except Exception as e:
        logger.error(f"Error updating schedule: {e}")
        error_msg = e

    # Generate top message and go back home
    if success_status:
        top_message = f"Got it, {user_name}! I have you down for the Q at *{ao_display_name}* on *{selected_date_dt.strftime('%A, %B %-d @ %H%M')}*"
        # TODO: if selected date was in weinke range (current or next week), update local weinke png
    else:
        top_message = f"Sorry, there was an error of some sort; please try again or contact your local administrator / Weasel Shaker. Error:\n{error_msg}"
    
    await refresh_home_tab(client, user_id, logger, top_message)

# triggered when user selects an already-taken slot
@slack_app.action("date_select_button_ignore")
async def handle_date_select_button_ignore(ack, client, body, logger):
    # acknowledge action and log payload
    await ack()
    logger.info(body)


# triggered when user hits cancel
@slack_app.action("cancel_button_select")
async def cancel_button_select(ack, client, body, logger):
    # acknowledge action and log payload
    await ack()
    logger.info(body)
    user_id = body['user']['id']
    user_name = (await get_user_names([user_id], logger, client))[0]
    top_message = f"Welcome to QSignups, {user_name}!"
    await refresh_home_tab(client, user_id, logger, top_message)











@slack_app.command("/post-weinke")
async def command(ack, body, respond, client, logger):
    await ack()
    logger.info(body)
    # placeholder for now
    try:
        # await weinke_create(db_config)
        await client.files_upload(
            file='weinkes/current_week_weinke.png',
            initial_comment="This week's schedule",
            channels=body['channel_id']
        )
    except Exception as e:
        logger.error(e)


async def get_pax(pax):
    p = ""
    for x in pax:
        p += "<@" + x + "> "
    return p


app = FastAPI()


@app.post("/slack/events")
async def endpoint(req: Request):
    logging.debug('[In app.post("/slack/events")]')
    return await app_handler.handle(req)


@app.get("/")
async def status_ok():
    logging.debug('[In app.get("/")]')
    return "ok"