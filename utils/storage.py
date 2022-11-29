"""The functions and classes needed to permanently store data are defined here
"""

import json
import os

__all__ = [
    "Storage"
]

class Storage:
    data: dict

    def __init__(
        self,
        file: str,
        default = {},
    ):
        """Initialize the storage object to the file at the path `file`.
        """
        self.file = file
        self.default = default

    def load(self):
        """Loads data from the file.
        Overrides any already and maybe modified data in memory."""
        with open(
            self.file,
            mode='r',
            encoding='utf-8',
        ) as file:
            self.data = json.load(file)
    
    def save(self):
        """Save the data from memory to the file.
        Overrides any data on the disk.
        """

        with open(
            self.file,
            mode='w',
            encoding='utf-8',
        ) as file:
            json.dump(self.data, file)
        
    def load_or_empty(self):
        if os.path.isfile(self.file):
            self.load()
        else:
            self.data = self.default
