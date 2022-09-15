import pandas as pd
import io
from aiida.orm import Dict


class RSidData(Dict):
    """CrySPY rs_data

    """

    def __init__(self, rs_id_data=None, **kwargs):
        """
        SinglefileData requests file in __init__(), so ea_data must not be None.
        """
        super().__init__(**kwargs)
        if rs_id_data is not None:
            self.set_rs_id_data(rs_id_data)

    def _internal_validate(self, rs_id_data):
        if len(rs_id_data) != 2:
            raise TypeError('size of rs_id_data must be 3.')

        if rs_id_data[0] is not None:
            if not isinstance(rs_id_data[1], list):
                raise TypeError('rs_id_data[0] must be list')
            for value in rs_id_data[0]:
                if not isinstance(value, int):
                    raise TypeError('rs_id_data[0][*] must be int')
        if rs_id_data[1] is not None:
            if not isinstance(rs_id_data[1], list):
                raise TypeError('rs_id_data[1] must be list')
            for value in rs_id_data[1]:
                if not isinstance(value, int):
                    raise TypeError('rs_id_data[1][*] must be int')

    def set_rs_id_data(self, rs_id_data) -> Dict:
        self._internal_validate(rs_id_data)
        d = {"id_queueing": rs_id_data[0], "id_running": rs_id_data[1]}
        d_node = self.set_dict(d)
        return d_node

    def get_rs_id_data(self) -> list:
        d = self.get_dict()
        return (d["id_queueing"], d["id_running"])

    @property
    def rs_id_data(self) -> list:
        return self.get_rs_id_data()

    @rs_id_data.setter
    def rs_id_data(self, rs_id_data) -> None:
        self.set_rs_id_data(rs_id_data)
