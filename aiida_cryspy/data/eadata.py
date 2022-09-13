import pickle 
import pandas as pd
import io
from aiida.plugins import DataFactory
SinglefileData = DataFactory('singlefile')


class EAData(SinglefileData):
    """CrySPY ea_data
    
    """
    def __init__(self, ea_data, **kwargs):
        """
        SinglefileData requests file in __init__(), so ea_data must not be None.
        """
        self._internal_validate(ea_data)
        
        content = pickle.dumps(ea_data)
        handle = io.BytesIO(content)
        super().__init__(file=handle, **kwargs)
        
        
    def _internal_validate(self, ea_data):
        if len(ea_data) != 4:
            raise TypeError('size of ea_data must be 4.')
        if ea_data[0] is not None:
            if not isinstance(ea_data[0], dict):
                raise TypeError('ea_data[0] must be dict')
            # must check that ea_data[0] is {0:Structure, 1:Structure, ...}
        if ea_data[1] is not None:
            if not isinstance(ea_data[1], dict):
                raise TypeError('ea_data[0] must be list')
        if ea_data[2] is not None:
            if not isinstance(ea_data[2], pd.DataFrame):
                raise TypeError('ea_data[2] must be pd.DataFrame')
        if ea_data[3] is not None:
            if not isinstance(ea_data[3], pd.DataFrame):
                raise TypeError('ea_data[3] must be pd.DataFrame')
        
    def get_ea_data(self):
        with self.open(mode='rb') as handle:
            content = handle.read()
        return pickle.loads(content)
    
    @property
    def ea_data(self):
        return self.get_ea_data()
