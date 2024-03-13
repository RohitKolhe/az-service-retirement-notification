import datetime
import logging
import azure.functions as func
import os
import feedparser
from azure.data.tables import TableClient
from azure.communication.email import EmailClient
from dotenv import load_dotenv
from azure.core.exceptions import ResourceNotFoundError
import requests
import json
from base64 import b64encode

app = func.FunctionApp()

@app.function_name(name="azretirementannoucement")
@app.timer_trigger(schedule="0 0 9 * * MON", #0 * * * * * #0 */5 * * * * #0 0 9 * * MON
              arg_name="azretirementannoucement",
              run_on_startup=True) 
def test_function(azretirementannoucement: func.TimerRequest) -> None:
    utc_timestamp = datetime.datetime.utcnow().replace(
        tzinfo=datetime.timezone.utc).isoformat()
    if azretirementannoucement is not None and azretirementannoucement.past_due:
        logging.info('The timer is past due!')
    
    logging.info('Python timer trigger function ran at %s', utc_timestamp)

    if azretirementannoucement is not None:

      # Load environment variables from .env file
      load_dotenv()
  
      # Read environment variables
      updates_url = os.environ['UpdatesURL']
      storage_connection_string = os.environ['AzureWebJobsStorage']
      rssFeed_table_name = os.environ['RssFeedTableName']
      partition_key = os.environ['RssFeedEntityPartitionKey']
      row_key = os.environ['RssFeedEntityRowKey']
      communcation_connection_string = os.environ['AzureCommunicationService']
      alert_recipient = os.environ['AlertRecipient']
      alert_subject_line = os.environ['AlertSubjectLine']
      alert_sender_email = os.environ['AlertSenderEmail']

      # Jira
      jira_project_id = os.environ['JiraProjectId']
      jira_url = os.environ['JiraUrl']
      jira_token = os.environ['JiraToken']
      jira_user = os.environ['JiraUser']

  
      # Initialize Azure Table Service
      with TableClient.from_connection_string(conn_str=storage_connection_string, table_name=rssFeed_table_name) as table_client:
      # Read the last processed item from Azure Table Storage
        try: 
          last_processed_item = table_client.get_entity(partition_key=partition_key, row_key=row_key)
        # Convert last processed item's published date to datetime object
        
        # Handle the case where the entity is not found in the table
        except ResourceNotFoundError:
          last_processed_item = {
              'PartitionKey': partition_key,
              'RowKey': row_key,
              'published': 'Fri, 01 Sep 1999 00:00:00 Z',  # Provide a default initial value for the published date
              'guid': 'initial_value'         # Provide a default initial value for the guid
    
          }
          # Create the entity in Azure Table Storage
          table_client.create_entity(entity=last_processed_item)
  
        last_processed_date = datetime.datetime.strptime(last_processed_item.get('published'), '%a, %d %b %Y %H:%M:%S %z')
        logging.debug(" last_processed_date " + last_processed_item.get('published'))
        
        # Parse the RSS feed
        feed = feedparser.parse(updates_url)
        new_articles = []
  
        
        for entry in feed.entries:
            entry_published_date = datetime.datetime.strptime(entry.get('published'), '%a, %d %b %Y %H:%M:%S %z')
            #print(" entry_published_date " + entry.get('published'))
            
            # Check if the entry's published date is after the last processed date
            if entry_published_date > last_processed_date:
              new_articles.append(entry)
    
        if new_articles:
          # Update last processed item in Azure Table Storage
          most_recent_post = new_articles[0]
          logging.info("most_recent_post " + most_recent_post.published)
          logging.info("most_recent_post " + most_recent_post.get("guid"))
  
          last_processed_item["published"] = most_recent_post.get("published")
          last_processed_item["guid"] = most_recent_post.guid
          
          table_client.update_entity(last_processed_item)
          logging.info(f'Updated RssFeed table with most recent post: {most_recent_post.guid}')

          # Send email alert
          email_body = build_email_body(new_articles)
          send_email(communcation_connection_string, alert_sender_email, alert_recipient, alert_subject_line, email_body)
  
          # Create Jira issue
          #create_jira_issue(new_articles[0], jira_project_id, jira_url, jira_user, jira_token)

        else:
          logging.info('No new retirement updates since last execution.')

# Authorization token: we need to base 64 encode it
def basic_auth(username, password):
    token = b64encode(f"{username}:{password}".encode('utf-8')).decode("ascii")
    return f'Basic {token}'

def create_jira_issue(article, jira_project_id, jira_url, jira_user, jira_token):
    # Calculate the due date (7 days from today)
    due_date = (datetime.datetime.now() + datetime.timedelta(days=7)).strftime("%Y-%m-%d")

    # Update description with article.Summary and article.link
    description = f"\n\nSummary: {article.summary}\nLink: {article.link}\n\n"

    # Update summary with "Azure Service Retirement Announcement for Service" + article.title
    summary = f"Azure Service Retirement Announcement: {article.title}"

    # Define the issue data
    issue_data = {
        "fields": {
            "project": {
                "key": jira_project_id  # Change this to your project key
            },
            "summary": summary,
            "description": description,
            "issuetype": {
                "name": "Service request" #Change Bug  # Change this to your issue type
            },
            "priority": {
                "id": "1"  # Change this to the desired priority id
            },
            "duedate": due_date
        }
    }

    # Convert the issue data to JSON format
    payload = json.dumps(issue_data)

    # Define the Jira REST API URL and credentials
    headers = {
        "Content-Type": "application/json",
        "Authorization": basic_auth(jira_user, jira_token)
    }
    print("Call jira post request: " + payload)
    # Make the POST request to create the issue
    response = requests.post(jira_url, headers=headers, data=payload)

    # Check if the request was successful
    if response.status_code == 201:
        logging.info("Issue created successfully!")
        logging.info("Issue Key:", response.json()["key"])
    else:
        logging.error("Failed to create issue. Status code:", response.status_code)
        logging.error("Response:", response.text)

def build_email_body(articles):
    headings = "<html><body><h1>Azure Retirement announcements</h1>"
    body_items = ""
    for article in articles:
        if isinstance(article, str):
            logging.warning("Article is a string, expected object with 'link' and 'title' attributes.")
            continue

        body_items += f"<p><strong>{article.title}</strong> - <a href=\"{article.link}\">read more &gt;&gt;</a></p>"
    if not body_items:
        body_items = "<p><strong>No new retirement updates since last email.</strong></p>"
    return headings + body_items + "</body></html>"

def send_email(communcation_connection_string, sender_email, recipient_email, subject, body):
    client = EmailClient.from_connection_string(communcation_connection_string);
    message = {
        "content": {
            "subject": subject,
            "html": body
        },
        "recipients": {
            "to": [
                {
                    "address": recipient_email,
                    "displayName": "Customer Name"
                }
            ]
        },
        "senderAddress": sender_email
    }
    
    poller = client.begin_send(message)
    result = poller.result()
    print(result)