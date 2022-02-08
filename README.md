# QSignups

Welcome to QSignups! This is a Slack App built specifically to manage the Q signups and calendar for F3 regions.

<img src='https://github.com/evanpetzoldt/qsignups/blob/master/screens/qsignups-logo.png?raw=true' width=25% height=25%>

There are 4 major components of getting this app working in your region, with more detailed instructions below:
1. **[Code](#code-instructions)** - primary steps are forking this repo and uploading your region's settings / secrets
2. **[Azure](#azure-instructions)** - this sets up the App Service in Azure which will host the web app and serves the requests from Slack
3. **[Slack](#slack-instructions)** - this step sets up the app on the Slack side, including what to listen for, proper permissions, etc.
4. **[Database](#database-instructions)** - this app relies on some additional tables on the PAXMiner MySQL database

## Code Instructions

To get this working in your region, please follow these steps:

1. Fork this repo (upper right side of Github)
2. Pull down to a local repo on your machine. This can be done by clicking "Code" on your forked repo, and copying the https link. From a command line (bash, git bash, etc.), navigate to where you want to store the repo and then use ```git clone copied-git-https-link```
3. If you want to run locally, you'll need to install the required packages (I recommend a virtual environment, see below):
```bash
cd path/to/repo
python3 -m venv env 
source env/bin/activate
python3 -m pip install -r requirements.txt
```
4. Create a `.env` file. This should have the following format:
```
ENV_VARIABLE1 = 'xoxb-abc'
ENV_VARIABLE2 = 'oinsegln'
...
```
* This `.env` file will be ignored by the git / github repo (because of `.gitignore`), so you should not get angry emails from github about exposing your secrets.
* The environment variables that are required to make QSignups run:

| Variable      | Description      |
| ---------| ------------|
| SLACK_BOT_TOKEN | A value from the token on the OAuth page in the slack app |
| SLACK_VERIFICATION_TOKEN | A value from the Basic Information -> Verification Token field in the settings for your slack app |
| SLACK_SIGNING_SECRET | Secret from the App Credentials page for your app in Slack |
| SLACK_USER_TOKEN | Secret from Slack that will allow you to upload files - only required if you will be running weinkes. This starts with `xoxp` and will show up under OAuth & Permissions if you have enabled a **user token scope** |
| DATABASE_SCHEMA | The name of your schema on the central PAXMiner db. This is often your region name |
| DATABASE_USER | This is the name of the db user that has **write permissions** on the Schema above. This may also be your region name |
| DATABASE_WRITE_PASSWORD | A write-access password associated with the DB user above. This will be provided by Beaker |

5. Once this is created (and after you've set up the App Service in Azure), you can upload these variables into your app. If you're using VSCode, install and sign into the Azure App Service extension. On the App Service tree, right click 'Application Settings' and select 'Upload Local Settings...'. When prompted, select your local .env file

## Azure Instructions

1. Set up an account on https://portal.azure.com if you don't already have one
  * You will probably need to use a credit card to activate the account - you should NOT have to incur any charges **as long as you use the free tier**, see below
2. Once the account is set up, click on App Services from https://portal.azure.com then hit Create
3. If you already have an app (such as Slackblast), you should already have a Resource Group you can use. Otherwise, create a new one
4. Give the Instance a name. This will define the url that the app uses
5. Publish should be set to Code, Runtime stack to `Python 3.8` (I have not tested the app on other versions of Python)
6. Under App Service Plan **make sure to select the free F1 tier Sku/size**. This is a basic server but should be able to handle our loads.
7. Hit Review+create to create the app. It may take the new app some time to initialize.
8. Navigate to your app by clicking on it on the left hand side. Then go to Deployment Center on the left toolbar.
9. [placeholder for more instructions syncing your github to the app]
10. Based on how I set mine up, it sort of falls asleep after a bit of inactivity. One way to keep this from happening is to use a service that pings the app every so often. I am using [uptimerobot.com](https://uptimerobot.com/) to do this with the following settings: 

## Slack Instructions

Go to https://api.slack.com/start/overview#creating to read up on how to create a slack app. Click their `Create a Slack app` while signed into your F3 region's Slack.

When you finish setting up and installing the slackblast app in Slack, you will get a bot token also available under the OAuth & Permissions settings. You'll also get a verification token and signing secret on the Basic Information settings. You will plug that information into your own `.env` file (see above). When you finish creating the Azure app, you will need to get the URL and add it (with `/slack/events` added to it) into three locations within the slackblast app settings:

1. Interactivity and Shortcuts
   - Request URL
   - Options Load URL
2. Slash Commands
   - Request URL

**Format of the URL to be used**

```
https://<YOUR-AZURE-APP-NAME>/slack/events
```

**Scopes**

Lastly, you will need to add several Scopes to the Bot Token Scopes on the OAuth & Permissions settings:

```
app_mentions:read
channels:read
chat:write
chat:write.public
commands
im:write
users:read
users:read.email
```

If you will be running weinkes, you will need to add a User Token Scope in order to upload and publicize weinkes:

```
files:write
```

## Database Instructions

QSignups uses the same central MySQL database as PAXMiner. You will need to request a write-access user and password from Beaker associated with your region's schema. The following empty tables will then need to be created (currently demonstrated in `db_initialize.py`):

* `schedule_aos`: this table stores the AO's full name, associated slack channel id, and location (township, park, etc. - this is shown as a subtitle on the Weinke)
* `schedule_weekly`: this table store the AO's weekly schedule, with one entry for each day of week / time
* `schedule_master`: this table stores the individual events

Once these tables are created, you will be able to manage them through QSignups UI. **I have made it so the "Manage Region Calendar" button only shows up for Slack admins - if you're not already, you will need to be made an admin of your region's space**

## Weinke Posting

![Alt text](/screens/mytable.png?raw=true "Sample Weekly Q Weinke")

`weinke_create.py` is capable of automatically producing something like the table above. Unfortunately, the python package that produces this relies on having a Chrome executable on the host machine, which to my knowledge isn't something we could set up on the Azure App Service. In addition, I'm not sure it's possible to set up a scheduled event in an app service. So for now, I'm planning on setting up a scheduled run on my local machine. I will post instructions on doing that for those interested.

We may be able to set that up on a free Azure VM at some point in the future.

## Project Status

The app is functional but pretty barebones at the moment. I welcome all beta testers and co-developers! Hit me up if you'd like to help out [@Moneyball (F3 St. Charles)] on the Nation space, or feel free to submit pull requests!

If you find bugs, you can reach out on Slack or (even better) add the issue to my github Issues log.

### What's Working
* AOs can be added to the list via the UI
* Weekly beatdown schedules can be added to the calendar via the UI
* Users can take Q slots and the calendar db will be updated
* Users can take themselves off Q slots (Slack admins can also do this for others)

### Feature Requests / Roadmap
* More calendar management UI functionality:
  * Add single (non-recurring) events
  * Delete single and / or recurring events
  * Edit an AO (name change, etc.)
  * Edit an event (time change, special qualifier like VQ, etc.)
* Ability for users to edit their own events (special qualifiers like birthday Q or VQ)
* Support for other event types (most notably QSource)
* Automated posting of a weekly Weinke / schedule (creation code is in `weinke_create.py`)
* Reminder messages to users about upcoming Qs (a couple days in advance?)
* Automated messages in AO channels when there are open Q slots at the beginning of the week
* Posting of weekly Weinke / schedule to other mediums (email, etc.)
* Conditional formatting of Weinke to highlight open slots, VQs, etc.

Any other ideas you have would be greatly appreciated! For organization purposes, I plan to use github's Issues to track them. Feel free to add an Issue with the tag 'enhancement'.
