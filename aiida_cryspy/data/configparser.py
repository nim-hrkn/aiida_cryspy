from aiida.orm import Dict
from configparser import ConfigParser

class ConfigParserData(Dict):
    """AiiDA ConfigParserData

    """
    def __init__(self, configparser:dict=None, **kwargs):
        super().__init__(**kwargs)
        if configparser is not None:
            super().set_dict(configparser._sections)

    def set_configparser(self, configparser:dict=None):
        self.set_dict(configparser._sections)

    def get_configparser(self)  -> ConfigParser:
        configparser = ConfigParser()
        dic = self.get_dict()
        configparser.read_dict(dictionary=dic)
        return configparser

    @property
    def configparser(self) -> ConfigParser:
        return self.get_configparser()
    
    @configparser.setter
    def configparser(self, configparser: ConfigParser) -> None:
        """
        Update the associated dataframe
        """
        self.set_configparser(configparser)
        
        