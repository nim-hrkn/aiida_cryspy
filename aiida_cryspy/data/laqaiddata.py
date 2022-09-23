import pickle
import io
from aiida.plugins import DataFactory
SinglefileData = DataFactory('singlefile')


class LAQAidData(SinglefileData):
    """CrySPY laqa_id_data
    """

    def __init__(self, laqa_id_data, **kwargs):
        """
        SinglefileData requests file in __init__(), so laqa_id_data must not be None.
        """
        self._internal_validate(laqa_id_data)

        content = pickle.dumps(laqa_id_data)
        handle = io.BytesIO(content)
        super().__init__(file=handle, **kwargs)

    def _internal_validate(self, laqa_id_data):
        if len(laqa_id_data) != 3:
            raise TypeError('size of laqa_id_data must be 4.')
        if laqa_id_data[0] is not None:
            if not isinstance(laqa_id_data[0], list):
                raise TypeError('laqa_id_data[0] must be list')
        if laqa_id_data[1] is not None:
            if not isinstance(laqa_id_data[1], list):
                raise TypeError('laqa_id_data[0] must be list')
        if laqa_id_data[2] is not None:
            if not isinstance(laqa_id_data[2], list):
                raise TypeError('laqa_id_data[2] must be list')



    def get_laqa_id_data(self):
        with self.open(mode='rb') as handle:
            content = handle.read()
        return pickle.loads(content)

    @property
    def laqa_id_data(self):
        return self.get_laqa_id_data()
