from program_manager import ProgramManager
from configparser import ConfigParser
from flask.cli import load_dotenv
from monitor import MonitorApi
from datetime import datetime
from pointer import Pointer
from loguru import logger
import sys
# from pprint import pprint

# to_stop = 0
timer_start = datetime.now()

# Get working path
arg0_split = sys.argv[0].split("/")

# Access to config
config = ConfigParser()
config_path = sys.argv[0].replace(arg0_split[-1], 'config.ini')
is_found = load_dotenv(path=config_path)
if not is_found:
    SystemExit("The program could not find config.ini file. "
               "Make sure you keep the file in the same directory as the executable file.")
config.read(config_path, encoding="utf-8")

# Log settings
logger.add("fail.log", rotation="00:00", level=config['SYSTEM']['loglevel'],
           format="<green>{time}</green> | <level>{level}</level> | <level>{message}</level>")

# Logging program version
program_info = "EAN-KOODI-GENERATOR, version: 1.0.1 (2022-05-10)"
logger.info(program_info)

ENTITY_TYPE_ID = config['CODES']['ENTITY_TYPE_ID']
EAN_NUMBER_START = int(config['EAN']['EAN_NUMBER_START'])
EAN_NUMBER_END = int(config['EAN']['EAN_NUMBER_END'])
EAN_WARNING = int(config['EAN']['EAN_WARNING'])
WARNING_NUMBER = EAN_NUMBER_END - EAN_WARNING

# Get starting ean and changelog id
pointer = Pointer(config_path)
pointer_path = sys.argv[0].replace(arg0_split[-1], 'POINTER.txt')
is_found = load_dotenv(path=pointer_path)
if not is_found:
    SystemExit("The program could not find POINTER.txt file. "
               "Make sure you keep the file in the same directory as the executable file.")
start_ean = pointer.get_ean(pointer_path)
start_changelog_id = pointer.get_changelog_id()
logger.info("Retrieved the starting EAN and the starting changelog Id")

# Log a warning if the program starts with ean number below warning number
if start_ean >= WARNING_NUMBER:
    logger.warning(f"The program has less than {EAN_NUMBER_END - start_ean} EAN numbers to generate.")
if start_ean >= EAN_NUMBER_END:
    logger.error(f"[End of Program] "
                 f"The program has reached its EAN_NUMBER_END {start_ean} at the start of the program.")
    raise SystemExit()

pm = ProgramManager(config_path)  # connect to local DB and create a table
pm.delete_tempfiles()  # delete .exe temporary files

# # # # # # # # ------------------------ Monitor APIs ------------------------ # # # # # # # #

monitor_api = MonitorApi(config_path)
monitor_api.execute_login()  # login Monitor API and get session id
headers = monitor_api.monitor_headers()
all_changelogs = monitor_api.query_changelog(ENTITY_TYPE_ID, start_changelog_id, headers)
logger.info(f"Queried {len(all_changelogs)} changelogs")
# pprint(all_changelogs)
monitor_calls = 2
next_ean = start_ean
count_rows, count_checks, count_updates = 0, 0, 0
for changelog in all_changelogs:
    entity_id = changelog['EntityId']
    if changelog['ChangeType'] == 0 or 1:  # 0 is 'update' change type, 1 is 'create' change type
        try:
            all_order_rows = monitor_api.query_order_row(entity_id, headers).json()
            count_rows += len(all_order_rows)
            logger.info(f"Queried {len(all_order_rows)} CustomerOrderRows for EntityId {entity_id}")
            # pprint(all_order_rows)
            monitor_calls += 1

            for order_row in all_order_rows:
                try:
                    row_id = order_row['Id']
                    prep_code = order_row['AlternatePreparationCode']
                    ref_num = order_row['ReferenceNumberDelivery']
                    # to_stop += 1
                    # print(f"to_stop: {to_stop}")
                    # If prep code is not None, proceed with the remaining steps. Else, log info and skip.
                    if prep_code is not None:

                        is_new_code = True
                        for row in pm.read_localdb():
                            (code, ean) = (row[0], row[1])
                            if prep_code == code:
                                is_new_code = False

                                if ref_num is None:
                                    count_updates, next_ean = pm.update_ean(prep_code, ean, next_ean, WARNING_NUMBER,
                                                                            EAN_WARNING, row_id, count_updates, headers,
                                                                            is_new_code)

                                else:
                                    count_checks, count_update = pm.verify_ean(prep_code, ref_num, ean, row_id,
                                                                               count_checks, count_updates, headers)
                                break
                        if is_new_code:
                            ean = None
                            count_updates, next_ean = pm.update_ean(prep_code, ean, next_ean, WARNING_NUMBER,
                                                                    EAN_WARNING, row_id, count_updates, headers,
                                                                    is_new_code)
                    else:
                        logger.info(f"AlternatePreparationCode is {prep_code} "
                                    f"for CustomerOrderRow Id {row_id} "
                                    f"with ParentOrderId {entity_id}")

                    # Exit program if the program has reached EAN_NUMBER_END
                    if next_ean >= EAN_NUMBER_END:
                        logger.error(f"The program has reached its EAN_NUMBER_END {next_ean}.")
                        logger.info(f"[End of Program] Time: {datetime.now() - timer_start}, "
                                    f"Changelogs: {len(all_changelogs)}, CustomerOrderRows: {count_rows} "
                                    f"(Successful {count_checks} checks, {count_updates} updates "
                                    f"& {count_rows - count_checks - count_updates} problems), "
                                    f"EANs generated: {next_ean - start_ean}, "
                                    f"Monitor API calls: {monitor_calls + count_updates}")
                        raise SystemExit()

                    # if to_stop == 3:
                    #     logger.info(f"[End of Program] Time: {datetime.now() - timer_start}, "
                    #                 f"Changelogs: {len(all_changelogs)}, CustomerOrderRows: {count_rows} "
                    #                 f"(Successful {count_checks} checks, {count_updates} updates "
                    #                 f"& {count_rows - count_checks - count_updates} problems), "
                    #                 f"EANs generated: {next_ean - start_ean}, "
                    #                 f"Monitor API calls: {monitor_calls + count_updates}")
                    #     raise SystemExit()
                except Exception as e:
                    logger.error(e)

        except IndexError as index_error:
            logger.info(f"CustomerOrderRow is missing for EntityId {entity_id}")
        except Exception as e:
            logger.error(e)
        finally:
            pointer.write(changelog['Id'], next_ean)
            logger.info(f"ChangelogId {changelog['Id']} and EAN {next_ean} are saved to POINTER.txt file")

    elif changelog['ChangeType'] == 2:  # 2 is 'delete' change type
        pass  # do nothing

logger.info(f"[End of Program] Time: {datetime.now() - timer_start}, "
            f"Changelogs: {len(all_changelogs)}, CustomerOrderRows: {count_rows} "
            f"(Successful {count_checks} checks, {count_updates} updates "
            f"& {count_rows - count_checks - count_updates} problems), "
            f"EANs generated: {next_ean - start_ean}, "
            f"Monitor API calls: {monitor_calls + count_updates}")
