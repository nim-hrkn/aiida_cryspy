import pandas as pd
import io
from aiida.orm import Dict

class EAidData(Dict):
    """CrySPY ea_data
    
    """
    def __init__(self, ea_id_data=None, **kwargs):
        """
        SinglefileData requests file in __init__(), so ea_data must not be None.
        """
        super().__init__(**kwargs)
        if ea_id_data is not None:
            self.set_ea_id_data(ea_id_data)
        
    def _internal_validate(self, ea_id_data):
        if len(ea_id_data) != 3:
            raise TypeError('size of ea_id_data must be 3.')
        if ea_id_data[0] is not None:
            if not isinstance(ea_id_data[0], int):
                raise TypeError('ea_id_data[0] must be int')
        if ea_id_data[1] is not None:
            if not isinstance(ea_id_data[1], list):
                raise TypeError('ea_id_data[1] must be list')
            for value in ea_id_data[1]:
                if not isinstance(value, int):
                    raise TypeError('ea_id_data[1][*] must be int')
        if ea_id_data[2] is not None:
            if not isinstance(ea_id_data[2], list):
                raise TypeError('ea_id_data[2] must be list')
            for value in ea_id_data[2]:
                if not isinstance(value, int):
                    raise TypeError('ea_id_data[2][*] must be int')
        
    def set_ea_id_data(self, ea_id_data) -> Dict:
        self._internal_validate(ea_id_data)
        d = {"gen": ea_id_data[0], "id_queueing": ea_id_data[1], "id_running": ea_id_data[2]}
        d_node = self.set_dict(d)
        return d_node
    
    def get_ea_id_data(self) -> list:
        d = self.get_dict()
        return (d["gen"], d["id_queueing"], d["id_running"])
    
    @property
    def ea_id_data(self) -> list:
        return self.get_ea_id_data()
    
    @ea_id_data.setter
    def ea_id_data(self, ea_id_data) -> None:
        self.set_ea_id_data(ea_id_data)

