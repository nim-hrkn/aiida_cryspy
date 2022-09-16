import pickle
import io
from aiida.plugins import DataFactory
SinglefileData = DataFactory('singlefile')


class RinData(SinglefileData):
    """CrySPY rin
    """

    def __init__(self, rin, **kwargs):
        """
        SinglefileData requests file in __init__(), so rin must not be None.
        """
        self._internal_validate(rin)

        content = pickle.dumps(rin)
        handle = io.BytesIO(content)
        super().__init__(file=handle, **kwargs)

    def _internal_validate(self, rin):
        pass

    def get_rin(self):
        with self.open(mode='rb') as handle:
            content = handle.read()
        return pickle.loads(content)

    @property
    def rin(self):
        return self.get_rin()

