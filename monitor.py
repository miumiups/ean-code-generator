from configparser import ConfigParser
from loguru import logger
import requests
import urllib3
import json


class MonitorApi:

    def __init__(self, config_path):
        # Access to config
        config = ConfigParser()
        config.read(config_path, encoding="utf-8")

        # Constants
        monitor_api_server = config['API']['MONITOR_API_SERVER']
        monitor_api_company = config['API']['MONITOR_API_COMPANY']
        monitor_api_lang = config['API']['MONITOR_API_LANG']
        monitor_api_username = config['API']['MONITOR_API_USERNAME']
        monitor_api_password = config['API']['MONITOR_API_PASSWORD']

        self.session_id = None
        self.url = f"{monitor_api_server}/{monitor_api_lang}/{monitor_api_company}"
        self.auth_headers = {'Content-type': 'application/json', 'Accept': 'application/json'}
        self.api_auth_json = {
            'Username': monitor_api_username,
            'Password': monitor_api_password,
            'ForceRelogin': True
        }

    def execute_login(self):
        try:
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
            login_endpoint = f"{self.url}/login"
            session_id_r = requests.post(
                login_endpoint,
                data=json.dumps(self.api_auth_json),
                headers=self.auth_headers,
                verify=False
            )
            session_id_r.raise_for_status()
            self.session_id = session_id_r.json()['SessionId']
        except Exception as e:
            logger.error(e)
            raise SystemExit()
        else:
            logger.info("Logged in to Monitor")

    def monitor_headers(self):
        headers = {
            'Content-type': 'application/json',
            'Accept': 'application/json',
            'Cache-Control': 'no-cache',
            'X-Monitor-SessionId': self.session_id
        }
        return headers

    def query_changelog(self, entity_type_id, changelog_id, headers):
        endpoint = f"{self.url}/api/v1/Common/EntityChangeLogs?" \
                   f"$select=Id,ChangeType,ModifiedTimestamp,EntityTypeId,EntityId&" \
                   f"$filter=EntityTypeId%20eq%20'{entity_type_id}'" \
                   f"%20and%20Id%20gt%20'{changelog_id}'"

        response = requests.get(endpoint, headers=headers, verify=False)
        response.raise_for_status()
        all_changelogs = response.json()

        return all_changelogs

    def query_order_row(self, entity_id, headers):
        endpoint = f"{self.url}/api/v1/Sales/CustomerOrderRows?" \
                   f"$Select=Id,AlternatePreparationCode,ParentOrderId,ReferenceNumberDelivery&" \
                   f"$Filter=ParentOrderId%20eq%20'{entity_id}'" \
                   f"%20and%20LifeCycleState%20eq%20'10'"

        response = requests.get(endpoint, headers=headers, verify=False)
        response.raise_for_status()

        return response

    def update(self, row_id, ean, headers):
        body = {
            "RowId": row_id,
            "ReferenceNumberDelivery": {
                "Value": ean
            }
        }
        endpoint = f"{self.url}/api/v1/Sales/CustomerOrders/UpdateRow"
        response = requests.post(endpoint, data=json.dumps(body), headers=headers, verify=False)
        response.raise_for_status()
