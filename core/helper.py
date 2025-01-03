import inspect
import json
import os
from typing import Dict, Optional

import pandas as pd
import yaml
from qgis.core import QgsProcessingException, QgsProcessingFeedback


class Assistant:
    CMD_FOLDER = os.path.split(inspect.getfile(inspect.currentframe()))[0]
    IMAGECOLLECTIONS_JSON = os.path.join(CMD_FOLDER, 'imagecollections.json')
    PREFERENCES_YAML = os.path.join(
        CMD_FOLDER.replace(r'\core', ''), 'preferences.yaml')
    DISCLAIMER = "error due to intense computation. \
        Please consider the following suggestions. \
        1. Reduce the number of features in the AOI layer. \
        2. Reduce the number of years in the date range. \
        3. Change the scale and tileScale values as per the requirements."
    DRIVE_MSG = {
        'Output': 'Output will be saved in the Google Drive.',
        'Status': 'visit \
            https://code.earthengine.google.co.in/tasks or \
            https://console.cloud.google.com/earth-engine/tasks',
        'If_Failed': DISCLAIMER
    }

    @staticmethod
    def read_preferences() -> Dict:
        """
        Reads the preferences from a YAML file specified by the PREFERENCES_YAML
        attribute of the Assistant class.

        Returns:
            Dict: A dictionary containing the preferences loaded from the YAML file.
        """
        with open(Assistant.PREFERENCES_YAML, 'r') as file:
            preferences = yaml.safe_load(file)
        return preferences

    @staticmethod
    def read_json() -> Dict:
        """
        Reads the JSON file and returns its content as a dictionary.

        Returns:
            Dict: The content of the JSON file.

        Raises:
            FileNotFoundError: If the JSON file does not exist.
        """
        if not os.path.exists(Assistant.IMAGECOLLECTIONS_JSON):
            raise QgsProcessingException(
                f'{Assistant.IMAGECOLLECTIONS_JSON} not found')
        with open(Assistant.IMAGECOLLECTIONS_JSON) as f:
            data = json.load(f)
        return data

    @staticmethod
    def write_json(data: Dict) -> None:
        """
        Writes the given dictionary to the JSON file.

        Args:
            data (Dict): The data to write to the JSON file.

        Raises:
            FileNotFoundError: If the JSON file does not exist.
        """
        if os.path.exists(Assistant.IMAGECOLLECTIONS_JSON):
            with open(Assistant.IMAGECOLLECTIONS_JSON, 'w') as f:
                json.dump(data, f, indent=4)
        else:
            raise QgsProcessingException(
                f'{Assistant.IMAGECOLLECTIONS_JSON} not found')

    @staticmethod
    def logger(feedback: QgsProcessingFeedback, msg: str, console: bool = False) -> None:
        """Log Informations. console used to report the output from executing an 
        external command or subprocess.

        Args:
            feedback (QgsProcessingFeedback): feedback object
            msg (str): text to log
            console (bool, optional): True for ConsoleInfo. Defaults to False.
        """
        if console:
            feedback.pushConsoleInfo(msg)
        else:
            feedback.pushInfo(msg)

    @staticmethod
    def set_progressbar_perc(feedback: QgsProcessingFeedback, perc: int, text: Optional[str] = None) -> None:
        """Set the feedback percentage in Progess bar

        Args:
            feedback (QgsProcessingFeedback): feadback object
            perc (int): progressbar percentage to set
            text (Optional[str]): progress text to set

        Raises:
            QgsProcessingException: Cancel button clicked
        """
        if feedback.isCanceled():
            raise QgsProcessingException('Processing Canceled.')
        feedback.setProgress(perc)
        if text:
            feedback.setProgressText(text)

    @staticmethod
    def export2csv(data: Dict, filepath: str, reducer_key: str, unique_key: str, date_key: str) -> None:
        """Export data to a CSV file.

        Args:
            data (Dict): The data to export.
            filepath (str): The path where the CSV file will be saved.
            reducer_key (str): The key used to reduce the data.
            unique_key (str): The key used to uniquely identify each entry.
            date_key (str): The key used to identify the date in the data.
        """
        reducer_key = reducer_key.lower()
        out_dict = {}
        for feature in data['features']:
            props = feature['properties']
            if (
                date_key not in props
                or unique_key not in props
                or reducer_key not in props
            ):
                raise QgsProcessingException(
                    f'{date_key}, {unique_key}, or {reducer_key} not found in stats properties')
            date = props[date_key]
            name = props[unique_key]
            val = props[reducer_key]
            if name in out_dict:
                out_dict[name][date] = val
            else:
                out_dict[name] = {date: val}
        df = pd.DataFrame(out_dict).T
        df.to_csv(filepath)

    @staticmethod
    def default_path():
        """
        Determines the default path for GeoCogs output.
        This function reads the user's preferences to find the default path for saving GeoCogs output.
        If a default path is specified in the preferences, it checks if the directory exists.
        If no default path is specified, it sets the default path to the user's Desktop with the filename 'GeoCogs_Output.csv'.
        Returns:
            str: The default path for GeoCogs output.
        """
        if DEFAULT_PATH := Assistant.read_preferences()['defaults']['defaultPath']:
            Assistant._check_directory(DEFAULT_PATH)
        else:
            DEFAULT_PATH = os.path.join(os.path.expanduser(
                "~"), 'Desktop', 'GeoCogs_Output.csv')
        return DEFAULT_PATH

    @staticmethod
    def _check_directory(path: str) -> None:
        """
        Checks if the directory of the given path exists.
        Args:
            path (str): The file path for which the directory needs to be checked.
        Raises:
            QgsProcessingException: If the directory does not exist.
        """
        dir_name = os.path.dirname(path)
        if not os.path.exists(dir_name):
            raise QgsProcessingException(f'{dir_name} not found')
