from configparser import ConfigParser
from monitor import MonitorApi
from loguru import logger
from shutil import rmtree
import sqlite3
import time
import sys
import os


class ProgramManager:

    def __init__(self, config_path):
        # Access to config
        config = ConfigParser()
        config.read(config_path, encoding="utf-8")

        # Connect to an existing local DB. If it doesn't exist, create a new DB.
        self.db = sqlite3.connect(config['PATHS']['LOCAL_DB'])
        self.cursor = self.db.cursor()
        self.create_table()

        self.monitor_api = MonitorApi(config_path)

    def create_table(self):
        """Create an empty table named 'code_table' if the table has not been created."""
        self.cursor.execute("CREATE TABLE IF NOT EXISTS code_table ("
                            "AlternatePreparationCode text UNIQUE, "
                            "EAN text UNIQUE)"
                            )

    def save_localdb(self, prep_code, next_ean):
        """Accept a prep code and an EAN as inputs. Add inputs in a new row to 'code_table' table."""
        self.cursor.execute(f"INSERT INTO code_table VALUES ('{prep_code}', '{next_ean}')")
        self.db.commit()

    def read_localdb(self):
        """Access 'code_table' table from Local DB and select all data."""
        return self.cursor.execute("SELECT * FROM code_table")

    def update_ean(self, prep_code, ean, next_ean, warning_num, ean_warning, row_id, count_updates,
                   headers, is_new_code):
        """
        If prep code is new, generate a new EAN. Save the EAN and prep code to Local DB, and update EAN to Monitor.
        Otherwise, use the input 'ean' to update Monitor.
        """
        if is_new_code:
            next_ean += 1
            self.save_localdb(prep_code, next_ean)
            logger.info(f"A pair of EAN {next_ean} and prep code {prep_code} saved to Local DB")

            self.monitor_api.update(row_id, next_ean, headers)
            logger.info(f"RowId {row_id} was updated with EAN {next_ean}")
            count_updates += 1

            # Log a warning if the program has reached its EAN_WARNING
            if next_ean == warning_num:
                logger.warning(f"The program has less than {ean_warning} EAN numbers to generate.")
        else:
            self.monitor_api.update(row_id, ean, headers)
            logger.info(f"RowId {row_id} was updated with EAN {ean}")
            count_updates += 1

        return count_updates, next_ean

    def verify_ean(self, prep_code, ref_num, ean, row_id, count_checks, count_updates, headers):
        """
        If Row has a correct EAN, log an info.
        Otherwise, update the Row with the correct EAN
        """
        if ref_num == ean:
            logger.info(
                f"RowId {row_id} with prep code {prep_code} was verified to have correct EAN {ref_num}")
            count_checks += 1

        else:
            self.monitor_api.update(row_id, ean, headers)
            count_updates += 1
            logger.info(f"Discrepancy detected in RowId {row_id}. "
                        f"Code {prep_code} and EAN {ref_num} do not match with Local DB. "
                        f"EAN was updated to {ean}.")

        return count_checks, count_updates

    def delete_tempfiles(self):
        mei_bundle = getattr(sys, "_MEIPASS", False)
        logger.debug(f"Current _MEIPASS: {mei_bundle}")
        if mei_bundle:
            dir_mei, current_mei = mei_bundle.split("_MEI")
            logger.debug(f"Scanning _MEI dir: {dir_mei}")
            for entry in os.scandir(dir_mei):
                if entry.name.startswith('_MEI') and "_MEI" + current_mei != entry.name and entry.is_dir():
                    dtime = time.time() - entry.stat().st_mtime
                    logger.debug(f"Found extra _MEI, name: {entry.name}, time diff: {dtime}")
                    if dtime > 1200:
                        logger.debug(f"Deleting _MEI older 1200 sec: {dir_mei}{entry.name}")
                        try:
                            rmtree(os.path.join(dir_mei, entry.name))
                        except PermissionError:
                            pass
