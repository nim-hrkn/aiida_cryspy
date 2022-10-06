import pickle
import io
from aiida.plugins import DataFactory
from numpy import savez_compressed
SinglefileData = DataFactory('singlefile')


class LAQAData(SinglefileData):
    """CrySPY laqa_data

        laqa_data = (tot_step_select, laqa_step, laqa_struc,
                 laqa_energy, laqa_bias, laqa_score)

    """

    def __init__(self, laqa_data, **kwargs):
        """
        SinglefileData requests file in __init__(), so laqa_data must not be None.
        """
        self._internal_validate(laqa_data)

        content = pickle.dumps(laqa_data)
        handle = io.BytesIO(content)
        super().__init__(file=handle, **kwargs)

    def _internal_validate(self, laqa_data):
        if len(laqa_data) != 2:
            raise TypeError('size of laqa_data must be 2.')
        if laqa_data[0] is not None:
            if not isinstance(laqa_data[0], dict):
                raise TypeError('laqa_data[0] must be list')
        if laqa_data[1] is not None:
            if not isinstance(laqa_data[1], dict):
                raise TypeError('laqa_data[0] must be dict')

    def get_laqa_data(self):
        with self.open(mode='rb') as handle:
            content = handle.read()
        return pickle.loads(content)

    @property
    def laqa_data(self):
        return self.get_laqa_data()
