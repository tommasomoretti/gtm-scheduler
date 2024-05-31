# GTM workspace scheduled deploy

Nel caso tu abbia bisogno di pubblicare un workspace di Google Tag Manager ad un orario preciso, ecco una soluzione per farlo:

## Architecting components:
- 1 x Service account
- 1 x Cloud Scheduler
- 1 x Pub/Sub
- 1 x Cloud Functions
- 1 x Google Tag Manager Client-side or Server-side

## Architecting schema:
<img alt="Screenshot 2023-11-09 alle 13 59 33" src="https://github.com/tommasomoretti/gtm-scheduled-deploy/assets/29273232/cf4d5bf4-3da2-4a84-80fc-feb2889d6ce8">


### Service Account
Va su https://console.cloud.google.com/iam-admin/serviceaccounts e crea un nuovo service account. 

<img alt="Screenshot 2023-11-09 alle 14 41 04" src="https://github.com/tommasomoretti/gtm-scheduled-deploy/assets/29273232/2a7cb2b6-bb22-4386-94c3-69160674d59f">

Assegna al service account il ruolo di editor del progetto Google Cloud e clicca su Fine. 

<img alt="Screenshot 2023-11-09 alle 15 21 37" src="https://github.com/tommasomoretti/gtm-scheduled-deploy/assets/29273232/57e5e2fc-2fa6-407c-9c9f-de64d7f8f46f">

Entra nel nuovo service account appena creato e genera una nuova chiave.

<img alt="Screenshot 2023-11-09 alle 14 44 19" src="https://github.com/tommasomoretti/gtm-scheduled-deploy/assets/29273232/fde742f0-c539-4d5f-bdab-77d8fa6e3fd0">

Seleziona formato JSON e scarica la chiave, dovrai inserirla nel codice della Cloud Functions.

<img alt="Screenshot 2023-11-09 alle 14 44 28" src="https://github.com/tommasomoretti/gtm-scheduled-deploy/assets/29273232/4a1c9c96-8297-4313-bb57-f6f8d729379a">


### Cloud Pub/Sub
Vai su https://console.cloud.google.com/cloudpubsub/topic/list e crea un nuovo job di Cloud Pub/Sub come segue:

<img alt="Screenshot 2023-11-09 alle 15 06 54" src="https://github.com/tommasomoretti/gtm-scheduled-deploy/assets/29273232/eb9a484f-72d6-4c48-98b3-0f382f61785c">


### Cloud Scheduler
Vai su https://console.cloud.google.com/cloudscheduler e crea un nuovo job di Cloud Scheduler come segue:
 
<img alt="Screenshot 2023-11-09 alle 14 56 09" src="https://github.com/tommasomoretti/gtm-scheduled-deploy/assets/29273232/1dbeab48-bde9-4b4c-90eb-d935d3261eb5">

<img alt="Screenshot 2023-11-09 alle 15 06 00" src="https://github.com/tommasomoretti/gtm-scheduled-deploy/assets/29273232/7f1679a9-ca48-4031-9f83-799a455596d6">
See https://crontab.guru/ for help woth cron expressions)

### Cloud Functions
Crea una nuova funzione Gen 1 chiamata ```deploy-gtm-workspace```.



Aggiungi un trigger Pub/Sub selezionando ```deploy-gtm-workspace``` come nome argomento.



Clicca su avanti e aggiungi il codice seguente nel file main.py, selezionando Python 3.12 come runtime.

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

Nel file requirements.txt aggiungere le seguenti librerie:

<img alt="Screenshot 2023-11-09 alle 12 06 34" src="https://github.com/tommasomoretti/gtm-scheduled-deploy/assets/29273232/a2eab7d8-da53-458b-937e-e6181eb0e160">

```
requests
google-auth
google-auth-oauthlib
google-api-python-client
```


### Google Tag Manager
Aggiungi il Service Account creato inizialmente a Google Tag Manager con privilegi di pubblicazione, l'accettazione dell'invito avverrà in maniera automatica.

<img alt="Screenshot 2023-11-09 alle 15 56 22" src="https://github.com/tommasomoretti/gtm-scheduled-deploy/assets/29273232/913172b6-dcf4-4476-b7a7-c1e48153b6f0">

---

Reach me at: [Email](mailto:hello@tommasomoretti.com) | [Website](https://tommasomoretti.com/?utm_source=github.com&utm_medium=referral&utm_campaign=gtm_scheduler) | [Twitter](https://twitter.com/tommoretti88) | [Linkedin](https://www.linkedin.com/in/tommasomoretti/)
