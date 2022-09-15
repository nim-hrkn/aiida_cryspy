import pickle
import io
from aiida.plugins import DataFactory
SinglefileData = DataFactory('singlefile')


class BOData(SinglefileData):
    """CrySPY bo_data
    """

    def __init__(self, bo_data, **kwargs):
        """
        SinglefileData requests file in __init__(), so bo_data must not be None.
        """
        self._internal_validate(bo_data)

        content = pickle.dumps(bo_data)
        handle = io.BytesIO(content)
        super().__init__(file=handle, **kwargs)

    def _internal_validate(self, bo_data):
        if len(bo_data) != 5:
            raise TypeError('size of bo_data must be 5.')
        if bo_data[0] is not None:
            if not isinstance(bo_data[0], dict):
                raise TypeError('bo_data[0] must be dict')
            # must check that bo_data[0] is {0:Structure, 1:Structure, ...}
        if bo_data[1] is not None:
            if not isinstance(bo_data[1], dict):
                raise TypeError('bo_data[0] must be dict')
        if bo_data[2] is not None:
            if not isinstance(bo_data[2], dict):
                raise TypeError('bo_data[2] must be dict')
        if bo_data[3] is not None:
            if not isinstance(bo_data[3], dict):
                raise TypeError('bo_data[3] must be dict')
        if bo_data[4] is not None:
            if not isinstance(bo_data[4], dict):
                raise TypeError('bo_data[4] must be dict')

    def get_bo_data(self):
        with self.open(mode='rb') as handle:
            content = handle.read()
        return pickle.loads(content)

    @property
    def bo_data(self):
        return self.get_bo_data()
