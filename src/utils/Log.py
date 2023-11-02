import json
import os
from os.path import exists
from typing import Any, Dict


class Log:

    def __init__(self, log_file_name: str = None):
        self.log_file_name = log_file_name
        self.json_content = []

        if self.log_file_name is not None and exists(log_file_name):
            os.remove(log_file_name)

        if self.log_file_name is not None:
            f = open(log_file_name, 'x')
            f.close()

        self.content = ''

    def add(self, content):
        if self.log_file_name is not None:
            self.content += content

            with open(self.log_file_name, "a") as f:
                f.write(content)

    def add_json(self, content: Dict[str, Any]):
        self.json_content.append(content)

        if self.log_file_name is not None:
            json_string = json.dumps(self.json_content, indent=6)

            with open(self.log_file_name, "w") as f:
                f.write(json_string)
                f.write("\n")
