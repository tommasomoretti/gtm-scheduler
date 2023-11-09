# GTM workspace scheduled deploy

Nel caso tu abbia bisogno di pubblicare un workspace di Google Tag Manager ad un orario preciso, ecco una soluzione per farlo:

## Architecting components:
- 1 x Service account
- 1 x Cloud Scheduler
- 1 x Pub/Sub
- 1 x Event Arc
- 1 x Cloud Functions
- 1 x Google Tag Manager Client-side or Server-side

## Architecting schema:
<img alt="Screenshot 2023-11-09 alle 10 59 35" src="https://github.com/tommasomoretti/gtm-scheduled-deploy/assets/29273232/ffbe6b7e-5519-49ba-a372-4a2e51d5dd3a">


### Service Account
Va su https://console.cloud.google.com/iam-admin/serviceaccounts e crea un nuovo service account. 

<img alt="Screenshot 2023-11-09 alle 09 36 14" src="https://github.com/tommasomoretti/gtm-scheduled-deploy/assets/29273232/ea92d0a4-8297-443b-bb0e-d0c98961c2ac">

Assegna al service account il ruolo di editor del progetto Google Cloud e clicca su Fine. 

<img alt="Screenshot 2023-11-09 alle 09 37 13" src="https://github.com/tommasomoretti/gtm-scheduled-deploy/assets/29273232/d71cc143-2c39-4d10-bcdb-8fb48300cbde">

Entra nel nuovo service account appena creato e genera una nuova chiave segreta in formato JSON, verrà scaricato un file che dovrai inserire nel codice della Cloud Functions.

<img alt="Screenshot 2023-11-09 alle 09 38 22" src="https://github.com/tommasomoretti/gtm-scheduled-deploy/assets/29273232/f46c99b8-884a-4ab3-a2b3-f157a6bc23ac">

<img alt="Screenshot 2023-11-09 alle 09 39 11" src="https://github.com/tommasomoretti/gtm-scheduled-deploy/assets/29273232/51cbb746-d926-421f-b6ba-697f72941e3c">


### Cloud Scheduler
Vai su https://console.cloud.google.com/cloudscheduler e crea un nuovo job di Cloud Scheduler come segue:
- Nome: gtm-scheduled-deploy
- Espressione cron: Data e ora in cui dev'essere eseguito il deploy (see https://crontab.guru/ for help).
- Fuso orario: UTC
- Tipo di target: Cloud Pub/Sub
- Argomento Cloud Pub/Sub: Crea un argomento chiamato ```gtm-scheduled-deploy```
- Attributi del messaggio:
  - account_id: {GTM account id}
  - container_id: {GTM container id}
  - workspace_id: {GTM workspace id}
 

### Cloud Functions
Crea una nuova funzione Gen 2 chiamata ```deploy-gtm-workspace```. Aggiungi un trigger Pub/Sub e crea un trigger Eventarc selezionando deploy-gtm-workspace come nome argomento.

<img alt="Screenshot 2023-11-09 alle 12 02 29" src="https://github.com/tommasomoretti/gtm-scheduled-deploy/assets/29273232/3ca31fbc-3e5e-4ed7-8ce8-6949f3f2726f">

<img alt="Screenshot 2023-11-09 alle 12 02 45" src="https://github.com/tommasomoretti/gtm-scheduled-deploy/assets/29273232/927d57b7-7685-46e4-adcf-8421159223ee">

Clicca su avanti e aggiungi il codice seguente nel file main.py, selezionando Python 3.12 come runtime.

<img alt="Screenshot 2023-11-09 alle 12 06 14" src="https://github.com/tommasomoretti/gtm-scheduled-deploy/assets/29273232/ad2fc128-f6b3-4f76-9831-4cbc995ca659">
&nbsp;

``` python
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
```

Nel file requirements.txt aggiungere le seguenti librerie

<img alt="Screenshot 2023-11-09 alle 12 06 34" src="https://github.com/tommasomoretti/gtm-scheduled-deploy/assets/29273232/a2eab7d8-da53-458b-937e-e6181eb0e160">
&nbsp;

```
requests
google-auth
google-auth-oauthlib
google-api-python-client
```


### Google Tag Manager
Aggiungi il Service Account creato inizialmente a Google Tag Manager con privilegi di pubblicazione, l'accettazione dell'invito avverrà in maniera automatica.
