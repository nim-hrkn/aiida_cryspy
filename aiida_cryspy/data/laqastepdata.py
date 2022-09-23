from aiida.orm import Dict
from pymatgen.core import Structure


class LAQAStepData(Dict):
    """
    step_data is a dict of dict.
    step_data= {0: dict, 1: dict, ...}    

    The internal type is
    {'0': dict, '1': dict, ...}   
    """

    def __init__(self, step_data: dict = None, **kwargs):
        """
        step_data is a dict of dict.

        Args:
            step_data (dict): structure.
        """
        super().__init__(**kwargs)

        if step_data is not None:
            self._internal_validate(step_data)
            self.set_step_data(step_data)

    def _internal_validate(self, step_data: dict):
        """
        Check that 
        all the keys of step_data are int.
        all the values of step_data are dict.

        Args:
            step_data (dict): dict.
        """

        for ID, value in step_data.items():
            ID_flag = True
            if isinstance(ID, int):
                pass
            elif isinstance(ID, str):
                if not ID.isdigit():
                    ID_flag = False
            if not ID_flag:
                raise TypeError('step_data.keys must be a type of int of str isdigit().')
            if not isinstance(value, dict):
                raise TypeError('step_data.values must be a type of dict.')

    def set_step_data(self, step_data: dict):
        """
        set step_data.

        The step_data format is
        {0: dict, 1: dict, ...}

        The internal format is
        {'0': dict, '1': dict, ...}

        Args:
            step_data (dict): step_data
        """
        if step_data is not None:
            self._internal_validate(step_data)
        stepdata_dict = {}
        for ID, value in step_data.items():
            key = str(ID)
            stepdata_dict[key] = value
        self.set_dict(dictionary=stepdata_dict)

    def get_step_data(self) -> dict:
        """change internal format to output format.

        output format:
        {0: dict, 1: dict, ...}

        Returns:
            dict: step_data.
        """
        stepdata_dict = self.get_dict()
        _stepdata_dict = {}
        for key, value in stepdata_dict.items():
            ID = int(key)
            _stepdata_dict[ID] = value
        return _stepdata_dict

    @property
    def step_data(self) -> dict:
        return self.get_step_data()

    @step_data.setter
    def step_data(self, step_data: dict) -> None:
        """
        Update step_data
        """
        self.set_step_data(step_data)
