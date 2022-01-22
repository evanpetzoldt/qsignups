# QSignups

Welcome to QSignups! This is a Slack App built specifically to manage the Q signups and calendar for F3 regions.

## Installation Instructions (Code)

To get this working in your region, please follow these steps:

1. Fork this repo (upper right side of Github)
2. Pull down to a local repo on your machine. This can be done by clicking "Code" on your forked repo, and copying the https link. From a command line (bash, git bash, etc.), navigate to where you want to store the repo and then use ```git clone copied-git-https-link```
3. If you want to run locally, you'll need to install the required packages (I recommend a virtual environment, see below):
```bash
cd path/to/repo
python3 -m venv env 
python3 -m pip install -r requirements.txt
```
4. Create a `.env` file. This should have the following format:
```
ENV_VARIABLE1 = 'xoxb-abc'
ENV_VARIABLE2 = 'oinsegln'
...
```
* The environment variables that are required to make QSignups run:

| Variable      | Description      |
| ---------| ------------|
| SLACK_BOT_TOKEN | A value from the token on the OAuth page in the slack app |
| SLACK_VERIFICATION_TOKEN | A value from the Basic Information -> Verification Token field in the settings for your slack app |
| SLACK_SIGNING_SECRET | Secret from the App Credentials page for your app in Slack |
| DATABASE_SCHEMA | The name of your schema on the central PAXMiner db. This is often your region name |
| DATABASE_USER | This is the name of the db user that has **write permissions** on the Schema above. This may also be your region name |
| DATABASE_WRITE_PASSWORD | A write-access password associated with the DB user above. This will be provided by Beaker |

5. This `.env` file will be ignored by the git / github repo (because of `.gitignore`), so you should not get angry emails from github about exposing your secrets.
6. One this is created (and after you've set up the App Service in Azure), you can upload these variables into your app. If you're using VSCode, install and sign into the Azure App Service extension. On the App Service tree, right click 'Application Settings' and select 'Upload Local Settings...'. When prompted, select your local .env file

## Azure App Instructions

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
10. [placeholder for instructions on using Uptimebot to keep the app from falling asleep]

## Database Setup

QSignups uses the same central MySQL database as PAXMiner. You will need to request a write-access user and password from Beaker associated with your region's schema. The following empty tables will then need to be created (currently demonstrated in `db_initialize.py`):

* `schedule_aos`: this table stores the AO's full name, associated slack channel id, and location (township, park, etc. - this is shown as a subtitle on the Weinke)
* `schedule_weekly`: this table store the AO's weekly schedule, with one entry for each day of week / time
* `schedule_master`: this table stores the individual events

Once these tables are created, you will be able to manage them through QSignups UI. **I have made it so the "Manage Region Calendar" button only shows up for Slack admins - if you're not already, you will need to be made an admin of your region's space**

## Project Status

The app is functional but pretty barebones at the moment. I welcome all beta testers and co-developers! Hit me up if you'd like to help out [@Moneyball (F3 St. Charles)] on the Nation space, or feel free to submit pull requests!

If you find bugs, you can reach out on Slack or (even better) add the issue to my github Issues log.

### What's Working
* AOs can be added to the list via the UI
* Weekly beatdown schedules can be added to the calendar via the UI
* Users can take Q slots and the calendar db will be updated

### Feature Requests / Roadmap
* More calendar management UI functionality:
  * Add single (non-recurring) events
  * Delete single and / or recurring events
  * Remove Q from slot (ideally non-admin users could do this for themselves)
  * Edit an AO (name change, etc.)
  * Edit an event (time change, special qualifier like VQ, etc.)
* Ability for users to edit their own events (special qualifiers like birthday Q or VQ)
* Automated posting of a weekly Weinke / schedule (creation code is in `weinke_create.py`)
* Reminder messages to users about upcoming Qs (a couple days in advance?)
* Automated messages in AO channels when there are open Q slots at the beginning of the week
* Posting of weekly Weinke / schedule to other mediums (email, etc.)

Any other ideas you have would be greatly appreciated! For organization purposes, I plan to use github's Issues to track them. Feel free to add an Issue with the tag 'enhancement'.
