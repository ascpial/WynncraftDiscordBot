import json
import os.path

__all__ = [
    "Configuration",
]

class Configuration():
    raw_config: dict

    def __init__(
        self,
        file: str = "./config.json"
    ):
        self.config_file_path = file

        self.load()
    
    def load(self):
        """Loads the configuration from the file to the memory.
        Automatically called by the `__init__` method, can be used to refresh
        the configuration.
        Raises:
          FileNotFoundError when the configuration file has not been set.
        """
        if os.path.isfile(self.config_file_path):
            with open(
                self.config_file_path,
                mode='r',
                encoding='utf-8',
            ) as config_file:
                self.raw_config = json.load(config_file)
        else:
            raise FileNotFoundError("The configuration file has not been set.")
    
    @property
    def token(self) -> str:
        """Returns the token set for the bot"""

        token = self.raw_config.get('token')

        if token is None:
            raise ValueError('The token has not been set')
        
        return token