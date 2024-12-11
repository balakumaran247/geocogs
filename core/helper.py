import inspect
import json
import os
from typing import Dict, Optional

from qgis.core import QgsProcessingException, QgsProcessingFeedback


class Assistant:
    CMD_FOLDER = os.path.split(inspect.getfile(inspect.currentframe()))[0]
    IMAGECOLLECTIONS_JSON = os.path.join(CMD_FOLDER, 'imagecollections.json')

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
            raise FileNotFoundError(
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
            raise FileNotFoundError(
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
