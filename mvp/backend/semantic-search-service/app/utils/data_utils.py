from enum import Enum
from typing import Any, List, Dict, Optional, Callable
import os
import json
from jsonschema import validate


class DataSource(Enum):
    STORAGE = "loaded index data from storage"
    JSON = "initialized index with data from JSON"


class DataLoader:
    @staticmethod
    def load_json_data_files(
        data_folder_path: str, data_schema: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Load and validate data from JSON files in a specified folder.

        Args:
            data_folder_path (str): Path to the folder containing JSON files.
            data_schema (Dict[str, Any]): JSON schema to validate the data against.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries representing the loaded and validated data.
        """
        print(f"Retrieving data from JSON files in folder: {data_folder_path}")

        data: List[Dict[str, Any]] = []

        try:
            os.listdir(data_folder_path)
        except FileNotFoundError as e:
            print(f"Folder not found: {data_folder_path}. Error: {e}")
            return data

        for filename in os.listdir(data_folder_path):
            json_file_path = os.path.join(data_folder_path, filename)
            print(f"Reading data from {json_file_path}")
            try:
                with open(json_file_path, "r", encoding="utf-8") as f:
                    current_data = json.load(f)
                    validate(current_data, data_schema)
            except FileNotFoundError as e:
                print(f"File not found: {json_file_path}. Error: {e}")
                continue
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON from {json_file_path}. Error: {e}")
                continue
            except Exception as e:
                print(f"An error occurred: {str(e)}")
                continue

            print(f"Read {len(current_data)} items from {json_file_path}")
            data.extend(current_data)

        print(f"Read a total of {len(data)} items from all files in folder")

        return data

    @staticmethod
    def load_json_data_files_with_progress(
        data_folder_path: str,
        data_schema: Dict[str, Any],
        progress_callback: Optional[Callable[[str, int, int], None]] = None,
    ) -> List[Dict[str, Any]]:
        """
        Load and validate data from JSON files with progress reporting.

        Args:
            data_folder_path (str): Path to the folder containing JSON files.
            data_schema (Dict[str, Any]): JSON schema to validate the data against.
            progress_callback (Optional[Callable]): Callback function called for each file processed.
                                                   Parameters: (filename, current_index, total_files)

        Returns:
            List[Dict[str, Any]]: A list of dictionaries representing the loaded and validated data.
        """
        print(f"Retrieving data from JSON files in folder: {data_folder_path}")

        data: List[Dict[str, Any]] = []

        try:
            all_files = [f for f in os.listdir(data_folder_path) if f.endswith(".json")]
        except FileNotFoundError as e:
            print(f"Folder not found: {data_folder_path}. Error: {e}")
            return data

        total_files = len(all_files)
        print(f"Found {total_files} JSON files to process")

        for file_index, filename in enumerate(all_files):
            json_file_path = os.path.join(data_folder_path, filename)

            # Call progress callback before processing each file
            if progress_callback:
                progress_callback(filename, file_index, total_files)

            print(f"Reading data from {json_file_path}")
            try:
                with open(json_file_path, "r", encoding="utf-8") as f:
                    current_data = json.load(f)
                    validate(current_data, data_schema)
            except FileNotFoundError as e:
                print(f"File not found: {json_file_path}. Error: {e}")
                continue
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON from {json_file_path}. Error: {e}")
                continue
            except Exception as e:
                print(f"An error occurred: {str(e)}")
                continue

            print(f"Read {len(current_data)} items from {json_file_path}")
            data.extend(current_data)

        print(f"Read a total of {len(data)} items from all files in folder")
        return data
