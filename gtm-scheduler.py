from google.oauth2 import service_account
from googleapiclient.discovery import build
import smtplib
from email.mime.text import MIMEText

def deploy_gtm_workspace(event, context):
  print("👉🏻 Let's deploy a GTM workspace")
  
  account_id = event['attributes']['account_id']
  print('  👉🏻 Account: ' + account_id)
  
  container_id = event['attributes']['container_id']
  print('  👉🏻 Container: ' + container_id)
  
  workspace_id = event['attributes']['workspace_id']
  print('  👉🏻 Workspace id: ' + workspace_id)


  # Carica le credenziali dal file JSON scaricato da Google Cloud Console
  service_account_credentials = {} # YOUR SERVICE ACCOUNT SECRET KEY GOES HERE

  credentials_get_workspace_info = service_account.Credentials.from_service_account_info(service_account_credentials, scopes=['https://www.googleapis.com/auth/tagmanager.readonly'])
  credentials_create_version = service_account.Credentials.from_service_account_info(service_account_credentials, scopes=['https://www.googleapis.com/auth/tagmanager.edit.containerversions'])
  credentials_publish_version = service_account.Credentials.from_service_account_info(service_account_credentials, scopes=['https://www.googleapis.com/auth/tagmanager.publish'])
  
  # Inizializza il client delle API
  service_get_workspace_info = build('tagmanager', 'v2', credentials=credentials_get_workspace_info)
  service_create_version = build('tagmanager', 'v2', credentials=credentials_create_version)
  service_publish_version = build('tagmanager', 'v2', credentials=credentials_publish_version)

  try:
    # Get workspace name and description
    get_workspace_info = service_get_workspace_info.accounts().containers().workspaces().get(path=f'accounts/{account_id}/containers/{container_id}/workspaces/{workspace_id}').execute()
    workspace_name = get_workspace_info['name']

    if 'description' in get_workspace_info:
      workspace_description = get_workspace_info['description']
    else:
      workspace_description = ''

    workspace_details = {
      "name": workspace_name,
      "notes": workspace_description
    }
    print(f'  👉🏻 Workspace name: {workspace_name}')
    print(f'  👉🏻 Workspace descrpition: {workspace_description}')
    
    # Create a version from workspace
    create_version = service_create_version.accounts().containers().workspaces().create_version(path=f'accounts/{account_id}/containers/{container_id}/workspaces/{workspace_id}', body=workspace_details).execute()
    version_id = create_version['containerVersion']['containerVersionId']
    print(f'👍🏻 Version id {version_id} created from workspace id {workspace_id}.')

    # Publish a version
    publish_version = service_publish_version.accounts().containers().versions().publish(path=f'accounts/{account_id}/containers/{container_id}/versions/{version_id}').execute()
    print(f'👍🏻 Version id {version_id} published.')
    
    # Send email
    subject = f"GTM Alert | Workspace {workspace_id} published"
    body = f"All done. New version {version_id} created from workspace {workspace_id}."
    send_email_notification(subject, body)

  except Exception as e:
    print(f'🖕🏻 Errore nella pubblicazione del container: {e}')

    # Send email
    subject = f"GTM Alert | Workspace {workspace_id} not published"
    body = f"Error. Workspace {workspace_id} not exist."
    send_email_notification(subject, body)


# Send email with result
def send_email_notification(subject, body):
  sender = "worker@gmail.com" # YOUR GMAIL ACCOUNT THAT WILL SEND THE EMAIL GOES HERE
  recipients = [
    "user1@domain.com", # EMAIL RECIPIENT 1 GOES HERE
    "user2@domain.com"  # EMAIL RECIPIENT 2 GOES HERE
  ]
  password = "" # YOUR GMAIL APP PASSWORD GOES HERE

  msg = MIMEText(body)
  msg['Subject'] = subject
  msg['From'] = sender
  msg['To'] = ', '.join(recipients)
  
  with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp_server:
    smtp_server.login(sender, password)
    smtp_server.sendmail(sender, recipients, msg.as_string())

  print("👍🏻 Email sent")
