from aiida.orm import Dict
from pymatgen.core import Structure


class PyStructureDictData(Dict):
    """
    structures is a dict of pymatgen.core.Structure.,
    structures= {0: pymatgen.core.Structure, 1: pymatgen.core.Structure, ...}    

    The internal type is
    {'0': pymatgen.core.Structure.as_dict(), '1': pymatgen.core.Structure.as_dict(), ...}   
    """

    def __init__(self, structures: dict=None, **kwargs):
        """
        structures is a dict of pymatgen.core.Structure.,

        Args:
            structures (List[Structure]): structure.
        """
        super().__init__(**kwargs)

        if structures is not None:
            self._internal_validate(structures)
        if False:
            struc_dict_dict = {}
            for ID, value in structures.items():
                struc = value.as_dict()
                key = str(ID)
                struc_dict_dict[key] = struc
            self.set_dict(struc_dict_dict)
        else:
            if structures is not None:
                self.set_pystructuredict(structures)

    def _internal_validate(self, structures: dict):
        """
        Check that 
        all the keys of structures are int.
        all the values of structures are Structure.

        Args:
            structures (List[Structure]): structure.
        """

        
        for ID, value in structures.items():
            ID_flag = True
            if isinstance(ID, int):
                pass
            elif isinstance(ID,str):
                if not ID.isdigit():
                    ID_flag = False
            if not ID_flag:
                raise TypeError('structures.keys must be a type of int of str isdigit().')
            if not isinstance(value, Structure):
                raise TypeError('structures.values must be a type of Structure.')

    def set_pystructuredict(self, structures: dict):
        """
        set StrucDict

        Args:
            structures (dict): Structures
        """
        if structures is not None:
            self._internal_validate(structures)
        struc_dict_dict = {}
        for ID, value in structures.items():
            struc = value.as_dict()
            key = str(ID)
            struc_dict_dict[key] = struc
        self.set_dict(dictionary=struc_dict_dict)

    def get_pystructuredict(self) -> dict:
        structuresdic = self.get_dict()
        _structuresdic = {}
        for key, value in structuresdic.items():
            ID = int(key)
            struc = Structure.from_dict(value)
            _structuresdic[ID] = struc
        return _structuresdic

    @property
    def pystructuredict(self) -> dict:
        return self.get_pystructuredict()

    @pystructuredict.setter
    def pystructuredict(self, structures: dict) -> None:
        """
        Update PyStructureDict
        """
        self.set_pystructuredict(structures)
