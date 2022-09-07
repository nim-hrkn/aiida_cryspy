import os
import io
import numpy as np

from pymatgen.io.vasp.inputs import Poscar

from aiida.plugins import DataFactory
from aiida.orm import Code
from aiida.orm import Str, Dict, Int, List, Float
from aiida.engine import calcfunction, WorkChain

from CrySPY.gen_struc.random.gen_pyxtal import Rnd_struc_gen_pyxtal


# load types
StructureData = DataFactory('structure')
FolderData = DataFactory('folder')
SinglefileData = DataFactory('singlefile')
ArrayData = DataFactory('array')
LammpsPotential = DataFactory('lammps.potential')
TrajectoryData = DataFactory('array.trajectory')


SIMULATOR_PREFIX = 'simulator_'


@calcfunction
def _pack_Structure_to_folder(**kwargs):
    prefix = SIMULATOR_PREFIX
    filename = '{key}.poscar'
    final_structure_folder = FolderData()
    for label, structure in kwargs.items():
        py_structure = structure.get_pymatgen()
        poscar = Poscar(py_structure)
        handler = io.StringIO(str(poscar))
        key = label.replace(prefix, "")
        _filename = filename.replace('{key}', key)
        final_structure_folder.put_object_from_filelike(handler, _filename)
    return final_structure_folder


class initial_structure_WorkChain(WorkChain):
    """parallen execution of lammps.force
    """

    @classmethod
    def define(cls, spec):
        super().define(spec)
        spec.input("tot_struc", valid_type=Int, help='number of strctures.')
        spec.input("natot", valid_type=Int, help='summation of the number of atoms in the cell.')
        spec.input('atype', valid_type=List, help='atomic types.')
        spec.input('nat', valid_type=List, help='number of each atoms.')
        spec.input('vol_factor', valid_type=List, help='volume factor of each atoms.')
        spec.input('spgnum', valid_type=Str, help='all for all the symmetries.')
        spec.input('symprec', valid_type=Float, help='symprec for spglib.')
        spec.input('params', valid_type=Dict, help='additional parameters')

        spec.outline(
            cls.generate_structures,
            cls.make_folderdata,
        )
        spec.output("structures", valid_type=FolderData, help='optimized structures')

    def generate_structures(self):
        tot_struc = self.inputs.tot_struc.value
        natot = self.inputs.natot.value
        atype = self.inputs.atype.get_list()
        nat = self.inputs.nat.get_list()
        vol_factor = self.inputs.vol_factor.get_list()
        spgnum = self.inputs.spgnum.value
        symprec = self.inputs.symprec.value
        key = "vol_sigma"
        if key in self.inputs.params.get_dict():
            vol_sigma = self.inputs.params[key]
        else:
            vol_sigma = None
        key = "mindist"
        if key in self.inputs.params.get_dict():
            mindist = self.inputs.params[key]
        else:
            mindist = None
        key = "vol_mu"
        if key in self.inputs.params.get_dict():
            vol_mu = self.inputs.params[key]
        else:
            vol_mu = None

        rsgx = Rnd_struc_gen_pyxtal(natot=natot, atype=atype,
                                    nat=nat, vol_factor=vol_factor,
                                    vol_mu=vol_mu, vol_sigma=vol_sigma,
                                    mindist=mindist,
                                    spgnum=spgnum, symprec=symprec)
        rsgx.gen_struc(nstruc=tot_struc, id_offset=0,
                       init_pos_path=None)
        self.ctx.init_struc_data = rsgx.init_struc_data

    def make_folderdata(self):
        init_struc_data = self.ctx.init_struc_data

        structures = {}
        for label in init_struc_data:
            key = SIMULATOR_PREFIX+str(label)
            structure = init_struc_data[label]
            structures[key] = StructureData(pymatgen=structure)

        final_structure_folder = _pack_Structure_to_folder(**structures)

        self.out('structures', final_structure_folder)


@calcfunction
def _pack_to_index_energy(**kwargs):
    result = {}
    label_list = []
    value_list = []
    for label, value in kwargs.items():
        label_list.append(int(label))
        value_list.append(value)

    label_list = np.array(label_list)
    value_list = np.array(value_list)

    _ilabel = np.argsort(label_list)
    value_list = value_list[_ilabel]
    label_list = label_list[_ilabel]
    result = {'index': label_list.tolist(), 'energy': value_list.tolist()}
    return Dict(dict=result)


class optimization_simulator_lammps_WorkChain(WorkChain):
    """paralle execution of lammps.optimize
    """
    _CWD = ""
    _WITHMPI = False
    _RESOURCE = {'withmpi': False,
                 'resources': {'num_machines': 1,
                               'num_mpiprocs_per_machine': 1}}

    @classmethod
    def define(cls, spec):
        super().define(spec)
        spec.input("code_string", valid_type=Str, help='label of your \'lammps.optimize\' code')
        spec.input("initial_structures", valid_type=FolderData, help='folder containing initial structures')
        spec.input('potential', valid_type=LammpsPotential, help='lammps potential')
        spec.input('parameters', valid_type=Dict, help='additional parameters to pass \'lammps.optimize\'')

        spec.input('options',
                   valid_type=Dict, default=lambda: Dict(dict=cls._RESOURCE), help='metadata.options')

        spec.outline(
            cls.submit_workchains,
            cls.inspect_workchains
        )
        spec.output("results", valid_type=Dict)
        spec.output("final_structures", valid_type=FolderData, help='optimized structures')

    def submit_workchains(self):
        structure_filenames = self.inputs.initial_structures.list_object_names()
        structure_folder = self.inputs.initial_structures
        potential = self.inputs.potential
        code = self.inputs.code_string.value
        metadata_options = self.inputs.options.get_dict()
        parameters = self.inputs.parameters

        code_lammps_force = Code.get_from_string(code)

        for filename in structure_filenames:
            head, ext = os.path.splitext(filename)
            with structure_folder.open(filename) as handle:
                from ase.io import read
                structure = read(handle)
            structure = StructureData(ase=structure)

            builder = code_lammps_force.get_builder()
            builder.structure = structure
            builder.potential = potential
            builder.parameters = parameters
            builder.metadata.options = metadata_options

            future = self.submit(builder)  # or self.submit

            key = f'simulator_{head}'
            self.to_context(**{key: future})
            # self.to_context(simulator=append_(future))
            # self.to_context(simulator=append_({key: future})) # NG way.

    def inspect_workchains(self):
        calculations = self.ctx

        for key in calculations:
            values = calculations[key]
            if key.startswith(SIMULATOR_PREFIX):
                assert values.is_finished_ok

        results = {}
        for key in calculations:
            if key.startswith(SIMULATOR_PREFIX):
                energy = calculations[key].outputs.results["energy"]
            key = key.replace(SIMULATOR_PREFIX, "")
            results[key] = energy

        results = _pack_to_index_energy(**results)
        self.out('results', results)

        structures = {}
        for key in calculations:
            if key.startswith(SIMULATOR_PREFIX):
                structure = calculations[key].outputs.structure
                structures[key] = structure

        final_structure_folder = _pack_Structure_to_folder(**structures)

        self.out('final_structures', final_structure_folder)
