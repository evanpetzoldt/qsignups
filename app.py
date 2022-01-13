import logging
from decouple import config, UndefinedValueError
from fastapi import FastAPI, Request
from slack_bolt.adapter.fastapi.async_handler import AsyncSlackRequestHandler
from slack_bolt.async_app import AsyncApp
import datetime
from datetime import datetime, timezone, timedelta, date
import json
from typing import Text
import sendmail
from numpy import nan
import os
from dotenv import load_dotenv
import pandas as pd


# Inputs
OPTIONAL_INPUT_VALUE = "None"
events_show = 10

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


# @slack_app.command("/backblast")
# async def command(ack, body, respond, client, logger):
#     await ack()
#     today = datetime.now(timezone.utc).astimezone()
#     today = today - timedelta(hours=6)
#     datestring = today.strftime("%Y-%m-%d")
#     user_id = body.get("user_id")

#     # Figure out where user sent slashcommand from to set current channel id and name
#     is_direct_message = body.get("channel_name") == 'directmessage'
#     current_channel_id = user_id if is_direct_message else body.get(
#         "channel_id")
#     current_channel_name = "Me" if is_direct_message else body.get(
#         "channel_id")

#     # The channel where user submitted the slashcommand
#     current_channel_option = {
#         "text": {
#             "type": "plain_text",
#             "text": "Current Channel"
#         },
#         "value": current_channel_id
#     }

#     # In .env, CHANNEL=USER
#     channel_me_option = {
#         "text": {
#             "type": "plain_text",
#             "text": "Me"
#         },
#         "value": user_id
#     }
#     # In .env, CHANNEL=THE_AO
#     channel_the_ao_option = {
#         "text": {
#             "type": "plain_text",
#             "text": "The AO Channel"
#         },
#         "value": "THE_AO"
#     }
#     # In .env, CHANNEL=<channel-id>
#     channel_configured_ao_option = {
#         "text": {
#             "type": "plain_text",
#             "text": "Preconfigured Backblast Channel"
#         },
#         "value": config('CHANNEL', default=current_channel_id)
#     }
#     # User may have typed /slackblast #<channel-name> AND
#     # slackblast slashcommand is checked to escape channels.
#     #   Escape channels, users, and links sent to your app
#     #   Escaped: <#C1234|general>
#     channel_id, channel_name = get_channel_id_and_name(body, logger)
#     channel_user_specified_channel_option = {
#         "text": {
#             "type": "plain_text",
#             "text": '# ' + channel_name
#         },
#         "value": channel_id
#     }

#     channel_options = []

#     # figure out which channel should be default/initial and then remaining operations
#     if channel_id:
#         initial_channel_option = channel_user_specified_channel_option
#         channel_options.append(channel_user_specified_channel_option)
#         channel_options.append(current_channel_option)
#         channel_options.append(channel_me_option)
#         channel_options.append(channel_the_ao_option)
#         channel_options.append(channel_configured_ao_option)
#     elif config('CHANNEL', default=current_channel_id) == 'USER':
#         initial_channel_option = channel_me_option
#         channel_options.append(channel_me_option)
#         channel_options.append(current_channel_option)
#         channel_options.append(channel_the_ao_option)
#     elif config('CHANNEL', default=current_channel_id) == 'THE_AO':
#         initial_channel_option = channel_the_ao_option
#         channel_options.append(channel_the_ao_option)
#         channel_options.append(current_channel_option)
#         channel_options.append(channel_me_option)
#     elif config('CHANNEL', default=current_channel_id) == current_channel_id:
#         # if there is no .env CHANNEL value, use default of current channel
#         initial_channel_option = current_channel_option
#         channel_options.append(current_channel_option)
#         channel_options.append(channel_me_option)
#         channel_options.append(channel_the_ao_option)
#     else:
#         # Default to using the .env CHANNEL value which at this point must be a channel id
#         initial_channel_option = channel_configured_ao_option
#         channel_options.append(channel_configured_ao_option)
#         channel_options.append(current_channel_option)
#         channel_options.append(channel_me_option)
#         channel_options.append(channel_the_ao_option)

#     blocks = [
#         {
#             "type": "input",
#             "block_id": "title",
#             "element": {
#                 "type": "plain_text_input",
#                 "action_id": "title",
#                 "placeholder": {
#                     "type": "plain_text",
#                     "text": "Snarky Title?"
#                 }
#             },
#             "label": {
#                 "type": "plain_text",
#                 "text": "Title"
#             }
#         },
#         {
#             "type": "input",
#             "block_id": "the_ao",
#             "element": {
#                 "type": "channels_select",
#                 "placeholder": {
#                     "type": "plain_text",
#                     "text": "Select the AO",
#                     "emoji": True
#                 },
#                 "action_id": "channels_select-action"
#             },
#             "label": {
#                 "type": "plain_text",
#                 "text": "The AO",
#                 "emoji": True
#             }
#         },
#         {
#             "type": "input",
#             "block_id": "date",
#             "element": {
#                 "type": "datepicker",
#                 "initial_date": datestring,
#                 "placeholder": {
#                     "type": "plain_text",
#                     "text": "Select a date",
#                     "emoji": True
#                 },
#                 "action_id": "datepicker-action"
#             },
#             "label": {
#                 "type": "plain_text",
#                 "text": "Workout Date",
#                 "emoji": True
#             }
#         },
#         {
#             "type": "input",
#             "block_id": "the_q",
#             "element": {
#                 "type": "users_select",
#                 "placeholder": {
#                     "type": "plain_text",
#                     "text": "Tag the Q",
#                     "emoji": True
#                 },
#                 "action_id": "users_select-action"
#             },
#             "label": {
#                 "type": "plain_text",
#                 "text": "The Q",
#                 "emoji": True
#             }
#         },
#         {
#             "type": "input",
#             "block_id": "the_pax",
#             "element": {
#                 "type": "multi_users_select",
#                 "placeholder": {
#                     "type": "plain_text",
#                     "text": "Tag the PAX",
#                     "emoji": True
#                 },
#                 "action_id": "multi_users_select-action"
#             },
#             "label": {
#                 "type": "plain_text",
#                 "text": "The PAX",
#                 "emoji": True
#             }
#         },
#         {
#             "type": "input",
#             "block_id": "fngs",
#             "element": {
#                 "type": "plain_text_input",
#                 "action_id": "fng-action",
#                 "initial_value": "None",
#                 "placeholder": {
#                     "type": "plain_text",
#                     "text": "FNGs"
#                 }
#             },
#             "label": {
#                 "type": "plain_text",
#                 "text": "List untaggable names separated by commas (FNGs, Willy Lomans, etc.)"
#             }
#         },
#         {
#             "type": "input",
#             "block_id": "count",
#             "element": {
#                 "type": "plain_text_input",
#                 "action_id": "count-action",
#                 "placeholder": {
#                     "type": "plain_text",
#                     "text": "Total PAX count including FNGs"
#                 }
#             },
#             "label": {
#                 "type": "plain_text",
#                 "text": "Count"
#             }
#         },
#         {
#             "type": "input",
#             "block_id": "moleskine",
#             "element": {
#                 "type": "plain_text_input",
#                 "multiline": True,
#                 "action_id": "plain_text_input-action",
#                 "initial_value": "WARMUP: \nTHE THANG: \nMARY: \nANNOUNCEMENTS: \nCOT: ",
#                 "placeholder": {
#                     "type": "plain_text",
#                     "text": "Tell us what happened\n\n"
#                 }
#             },
#             "label": {
#                 "type": "plain_text",
#                 "text": "The Moleskine",
#                 "emoji": True
#             }
#         },
#         {
#             "type": "divider"
#         },
#         {
#             "type": "section",
#             "block_id": "destination",
#             "text": {
#                 "type": "plain_text",
#                 "text": "Choose where to post this"
#             },
#             "accessory": {
#                 "action_id": "destination-action",
#                 "type": "static_select",
#                 "placeholder": {
#                     "type": "plain_text",
#                     "text": "Choose where"
#                 },
#                 "initial_option": initial_channel_option,
#                 "options": channel_options
#             }
#         }
#     ]

#     if config('EMAIL_TO', default='') and not config('EMAIL_OPTION_HIDDEN_IN_MODAL', default=False, cast=bool):
#         blocks.append({
#             "type": "input",
#             "block_id": "email",
#             "element": {
#                 "type": "plain_text_input",
#                 "action_id": "email-action",
#                 "initial_value": config('EMAIL_TO', default=OPTIONAL_INPUT_VALUE),
#                 "placeholder": {
#                     "type": "plain_text",
#                     "text": "Type an email address or {}".format(OPTIONAL_INPUT_VALUE)
#                 }
#             },
#             "label": {
#                 "type": "plain_text",
#                 "text": "Send Email"
#             }
#         })

#     res = await client.views_open(
#         trigger_id=body["trigger_id"],
#         view={
#             "type": "modal",
#             "callback_id": "backblast-id",
#             "title": {
#                 "type": "plain_text",
#                 "text": "Create a Backblast"
#             },
#             "submit": {
#                 "type": "plain_text",
#                 "text": "Submit"
#             },
#             "blocks": blocks
#         },
#     )
#     logger.info(res)


# @slack_app.view("backblast-id")
# async def view_submission(ack, body, logger, client):
#     await ack()
#     result = body["view"]["state"]["values"]
#     title = result["title"]["title"]["value"]
#     date = result["date"]["datepicker-action"]["selected_date"]
#     the_ao = result["the_ao"]["channels_select-action"]["selected_channel"]
#     the_q = result["the_q"]["users_select-action"]["selected_user"]
#     pax = result["the_pax"]["multi_users_select-action"]["selected_users"]
#     fngs = result["fngs"]["fng-action"]["value"]
#     count = result["count"]["count-action"]["value"]
#     moleskine = result["moleskine"]["plain_text_input-action"]["value"]
#     destination = result["destination"]["destination-action"]["selected_option"]["value"]
#     email_to = safeget(result, "email", "email-action", "value")
#     the_date = result["date"]["datepicker-action"]["selected_date"]

#     pax_formatted = await get_pax(pax)

#     logger.info(result)

#     chan = destination
#     if chan == 'THE_AO':
#         chan = the_ao

#     logger.info('Channel to post to will be {} because the selected destination value was {} while the selected AO in the modal was {}'.format(
#         chan, destination, the_ao))

#     ao_name = await get_channel_name(the_ao, logger, client)
#     q_name = (await get_user_names([the_q], logger, client) or [''])[0]
#     pax_names = ', '.join(await get_user_names(pax, logger, client) or [''])

#     msg = ""
#     try:
#         # formatting a message
#         # todo: change to use json object
#         header_msg = f"*Slackblast*: "
#         title_msg = f"*" + title + "*"

#         date_msg = f"*DATE*: " + the_date
#         ao_msg = f"*AO*: <#" + the_ao + ">"
#         q_msg = f"*Q*: <@" + the_q + ">"
#         pax_msg = f"*PAX*: " + pax_formatted
#         fngs_msg = f"*FNGs*: " + fngs
#         count_msg = f"*COUNT*: " + count
#         moleskine_msg = moleskine

#         # Message the user via the app/bot name
#         if config('POST_TO_CHANNEL', cast=bool):
#             body = make_body(date_msg, ao_msg, q_msg, pax_msg,
#                              fngs_msg, count_msg, moleskine_msg)
#             msg = header_msg + "\n" + title_msg + "\n" + body
#             await client.chat_postMessage(channel=chan, text=msg)
#             logger.info('\nMessage posted to Slack! \n{}'.format(msg))
#     except Exception as slack_bolt_err:
#         logger.error('Error with posting Slack message with chat_postMessage: {}'.format(
#             slack_bolt_err))
#         # Try again and bomb out without attempting to send email
#         await client.chat_postMessage(channel=chan, text='There was an error with your submission: {}'.format(slack_bolt_err))
#     try:
#         if email_to and email_to != OPTIONAL_INPUT_VALUE:
#             subject = title

#             date_msg = f"DATE: " + the_date
#             ao_msg = f"AO: " + (ao_name or '').replace('the', '').title()
#             q_msg = f"Q: " + q_name
#             pax_msg = f"PAX: " + pax_names
#             fngs_msg = f"FNGs: " + fngs
#             count_msg = f"COUNT: " + count
#             moleskine_msg = moleskine

#             body_email = make_body(
#                 date_msg, ao_msg, q_msg, pax_msg, fngs_msg, count_msg, moleskine_msg)
#             sendmail.send(subject=subject, recipient=email_to, body=body_email)

#             logger.info('\nEmail Sent! \n{}'.format(body_email))
#     except UndefinedValueError as email_not_configured_error:
#         logger.info('Skipping sending email since no EMAIL_USER or EMAIL_PWD found. {}'.format(
#             email_not_configured_error))
#     except Exception as sendmail_err:
#         logger.error('Error with sendmail: {}'.format(sendmail_err))


def make_body(date, ao, q, pax, fngs, count, moleskine):
    return date + \
        "\n" + ao + \
        "\n" + q + \
        "\n" + pax + \
        "\n" + fngs + \
        "\n" + count + \
        "\n" + moleskine


# @slack_app.options("es_categories")
# async def show_categories(ack, body, logger):
#     await ack()
#     lookup = body["value"]
#     filtered = [x for x in categories if lookup.lower() in x["name"].lower()]
#     output = formatted_categories(filtered)
#     options = output
#     logger.info(options)

#     await ack(options=options)


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

# App home screen
async def refresh_home_tab(client, user_id, logger):
    # list of AOs for dropdown (eventually this will be dynamic)
    ao_list = [
        'ao-braveheart',
        'ao-bums-hollow',
        'ao-eagles-nest',
        'ao-field-of-dreams',
        'ao-running-with-animals',
        'ao-the-citadel',
        'ao-the-last-stop'
    ]

    options = []
    for option in ao_list:
        new_option = {
            "text": {
                "type": "plain_text",
                "text": option
            },
            "value": option
        }
        options.append(new_option)
    
    # Try to pubish view to 
    try:
        await client.views_publish(
            user_id=user_id,
            token=config('SLACK_BOT_TOKEN'),
            view={
                "type": "home",
                "blocks": [
                    {
                        "type": "section",
                        "block_id": "section678",
                        "text": {
                            "type": "mrkdwn",
                            "text": "Please select an AO"
                        },
                        "accessory": {
                            "action_id": "ao-select",
                            "type": "static_select",
                            "placeholder": {
                                "type": "plain_text",
                                "text": "Select an item"
                        },
                        "options": options
                        }
                    }
                ]
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
    refresh_home_tab(client, user_id, logger)

# triggered when user makes an ao selection
@slack_app.action("ao-select")
async def ao_select_slot(ack, client, body, logger):
    # acknowledge action and log payload
    await ack()
    logger.info(body)

    # Gather info from body
    region = 'f3saintcharles'
    ao = body['actions'][0]['selected_option']['value']
    user_id = body['user']['id']
    
    query = \
    f"""
    SELECT * 
    FROM schedule_master
    WHERE ao = '{ao}'
        AND region = '{region}';
    """

    # Pull from db into pandas
    with sqlite3.connect('data/schedule.db') as conn:
        df = pd.read_sql_query(query, conn)

    # Parse date and time fields, and filter on future events
    df['date_time'] = pd.to_datetime(df['date'] + ' ' + df['time'], infer_datetime_format=True)
    df = df[df['date_time'] > datetime.today()]

    # Top of view
    blocks = [{
        "type": "section",
        "text": {"type": "mrkdwn", "text": "Please select an open Q slot for:"}
    },
    {
        "type": "section",
        "text": {"type": "mrkdwn", "text": f"*{ao}*"}
    }]

    # Show next x number of events
    # TODO: future add: make a "show more" button?
    for i in range(events_show):
        # Pretty format date
        date_fmt = df.loc[i, 'date_time'].strftime("%A, %B %-d @ %H%M")
        
        # If slot is empty, show green button with primary (green) style button
        if df.loc[i, 'pax_id'] is None:
            date_status = "OPEN!"
            date_style = "primary"
            action_id = "date-select-button"
        # Otherwise default (grey) button, listing Qs name
        else:
            date_status = df.loc[i, 'pax_name']
            date_style = "default"
            action_id = "date-select-button-ignore" # this button action is ignore for now
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
                    "value":str(df.loc[i, 'date_time'])
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
                "action_id":"cancel-date-select-button",
                "value":"cancel",
                "style":"danger"
            }
        ]
    }
    blocks.append(new_button)
    try:
        await client.views_publish(
            # Use the user ID associated with the event
            user_id=user_id,
            token=config('SLACK_BOT_TOKEN'),
            view={
                "type": "home",
                "blocks": blocks
            }
        )
    except Exception as e:
        logger.error(f"Error publishing date options: {e}")

# triggers when an open slot is selected
@slack_app.action("date-select-button")
async def process_date_selection(ack, client, body, logger):
    # acknowledge and log body
    await ack()
    logger.info(body)
    
    # gather and format selected date
    selected_date = body['actions'][0]['value']
    selected_date_dt = datetime.strptime(selected_date, '%Y-%m-%d %H:%M:%S')
    selected_date_db = datetime.date(selected_date_dt).strftime('%-m/%-d/%Y')
    selected_time_db = datetime.time(selected_date_dt).strftime('%-H:%M')

    # Pull Slack user list for display name
    member_list = pd.DataFrame(client.users_list()['members'])
    member_list = member_list.drop('profile', axis=1).join(pd.DataFrame(member_list.profile.values.tolist()), rsuffix='_profile')
    member_list['pax_name'] = member_list['display_name']
    member_list.loc[member_list['display_name']=='', 'pax'] = member_list['real_name']

    # gather info needed for message and SQL
    ao = body['view']['blocks'][1]['text']['text'].replace('*','')
    region = 'f3saintcharles'
    user_id = body['user']['id']
    pax_name = member_list.loc[member_list['id']==user_id, 'pax_name'].iat[0]
    
    # text block for confirmation
    blocks = [{"type":"section", "text":{"type":"mrkdwn", "text":f"Got it! I have you down for the Q at *{ao}* on *{selected_date_dt.strftime('%A, %B %-d @ %H%M')}*"}}]

    # return to home button
    go_to_home = {
        "type":"actions",
        "elements":[{
            "type":"button",
            "text":{
                "type":"plain_text",
                "text":"Take another Q slot",
                "emoji":True
            },
            "action_id":"cancel-date-select-button",
            "value":"cancel"
        }]
    }
    blocks.append(go_to_home)

    # Update SQL
    query = \
    f"""
    UPDATE schedule_master 
    SET pax_id = '{user_id}'
        , pax_name = '{pax_name}'
    WHERE region = '{region}'
        AND ao = '{ao}'
        AND date = '{selected_date_db}'
        AND time = '{selected_time_db}'
    ;
    """

    with sqlite3.connect('data/schedule.db') as conn:
        cur = conn.cursor()
        cur.execute(query)
    
    # Publish view
    try:
        await client.views_publish(
            # Use the user ID associated with the event
            user_id=user_id,
            token=config('SLACK_BOT_TOKEN'),
            view={
                "type": "home",
                "blocks": blocks
            }
        )
    except Exception as e:
        logger.error(f"Error confirming request: {e}")

# triggers when user selects cancel button
@slack_app.action("cancel-date-select-button")
async def handle_some_action(ack, body, client, logger):
    await ack()
    logger.info(body)
    user_id = body['user']['id']
    refresh_home_tab(client, user_id, logger)

# triggers when users selects button that is already taken
# TODO: add functionality to take self off list from here?
@slack_app.action("date-select-button-ignore")
async def handle_some_action2(ack, body, logger):
    await ack()
    logger.info(body)

# Template for taking slash commands
# @app.command("/bot-test")
# def repeat_text(ack, respond, command):
#     # Acknowledge command request
#     ack()

#     user_message = command['text']
#     print(user_message)

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
