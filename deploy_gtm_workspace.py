from google.oauth2 import service_account
from googleapiclient.discovery import build


def deploy_gtm_workspace(event, context):
  account_id = event['attributes']['account_id']
  print('Account: ' + account_id)
  
  container_id = event['attributes']['container_id']
  print('Container: ' + container_id)
  
  workspace_id = event['attributes']['workspace_id']
  print('Workspace id: ' + workspace_id)


  # Carica le credenziali dal file JSON scaricato da Google Cloud Console
  service_account_credentials = {
    # Your service account secret_key.json
  }

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
    print(f'Workspace name: {workspace_name}')
    print(f'Workspace descrpition: {workspace_description}')
    
    # Create a version from workspace
    create_version = service_create_version.accounts().containers().workspaces().create_version(path=f'accounts/{account_id}/containers/{container_id}/workspaces/{workspace_id}', body=workspace_details).execute()
    version_id = create_version['containerVersion']['containerVersionId']
    print(f'Version id {version_id} created from workspace id {workspace_id}.')

    # Publish a version
    publish_version = service_publish_version.accounts().containers().versions().publish(path=f'accounts/{account_id}/containers/{container_id}/versions/{version_id}').execute()
    print(f'Version id {version_id} published.')
    
    # Send email notification
    # ...
    
  except Exception as e:
    print(f'Errore nella pubblicazione del container: {e}')
    raise
