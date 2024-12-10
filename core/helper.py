import inspect
import json
import os
from typing import Dict

cmd_folder = os.path.split(inspect.getfile(inspect.currentframe()))[0]
imagecollections_json = os.path.join(cmd_folder, 'imagecollections.json')


def read_json() -> Dict:
    """
    Reads the JSON file and returns its content as a dictionary.

    Returns:
        Dict: The content of the JSON file.

    Raises:
        FileNotFoundError: If the JSON file does not exist.
    """
    if not os.path.exists(imagecollections_json):
        raise FileNotFoundError(f'{imagecollections_json} not found')
    with open(imagecollections_json) as f:
        data = json.load(f)
    return data


def write_json(data: Dict) -> None:
    """
    Writes the given dictionary to the JSON file.

    Args:
        data (Dict): The data to write to the JSON file.

    Raises:
        FileNotFoundError: If the JSON file does not exist.
    """
    if os.path.exists(imagecollections_json):
        with open(imagecollections_json, 'w') as f:
            json.dump(data, f, indent=4)
    else:
        raise FileNotFoundError(f'{imagecollections_json} not found')
