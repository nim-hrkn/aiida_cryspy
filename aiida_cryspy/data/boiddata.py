import pickle
import io
from aiida.plugins import DataFactory
SinglefileData = DataFactory('singlefile')


class BOidData(SinglefileData):
    """CrySPY bo_id_data
    """

    def __init__(self, bo_id_data, **kwargs):
        """
        SinglefileData requests file in __init__(), so bo_id_data must not be None.
        """
        self._internal_validate(bo_id_data)

        content = pickle.dumps(bo_id_data)
        handle = io.BytesIO(content)
        super().__init__(file=handle, **kwargs)

    def _internal_validate(self, bo_id_data):
        if len(bo_id_data) != 4:
            raise TypeError('size of bo_id_data must be 4.')
        if bo_id_data[0] is not None:
            if not isinstance(bo_id_data[0], int):
                raise TypeError('bo_id_data[0] must be int')
        if bo_id_data[1] is not None:
            if not isinstance(bo_id_data[1], list):
                raise TypeError('bo_id_data[0] must be list')
        if bo_id_data[2] is not None:
            if not isinstance(bo_id_data[2], list):
                raise TypeError('bo_id_data[2] must be list')
        if bo_id_data[3] is not None:
            if not isinstance(bo_id_data[3], list):
                raise TypeError('bo_id_data[3] must be list')


    def get_bo_id_data(self):
        with self.open(mode='rb') as handle:
            content = handle.read()
        return pickle.loads(content)

    @property
    def bo_id_data(self):
        return self.get_bo_id_data()
