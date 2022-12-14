from CrySPY import utility
import pandas as pd
import re
from ase.io.lammpsdata import read_lammps_data
from ase.io.lammpsrun import read_lammps_dump_text
import io
import os
import numpy as np


from aiida.plugins import DataFactory
from aiida.orm import Code
from aiida.orm import Str, Dict, List, Int
from aiida.engine import calcfunction, WorkChain

from CrySPY.IO import read_input as rin
from pymatgen.io.vasp.inputs import Poscar
from pymatgen.core import Structure

# load types
StructureData = DataFactory('structure')
FolderData = DataFactory('folder')
SinglefileData = DataFactory('singlefile')
ArrayData = DataFactory('array')
LammpsPotential = DataFactory('lammps.potential')
StructurecollectionData = DataFactory('cryspy.structurecollection')
StepData = DataFactory('cryspy.step_data')


SIMULATOR_PREFIX = 'simulator_'
ID_PREFIX = 'ID_'


def _opt_result_to_step_data(trajectory_data, retrieved, log_filename='log.lammps', tolist=True):
    """
    parse opt_result to get *_step_data.

    Note:
    1. force_step_data is obtained from tarjectory data.
    2. energy_step_data and stress_step_data are obtained from lammps log file in the retrieved folder.
    Therefore, the number of steps may be different between force_step_data and {energy|stress}_step_data.

    Args:
        trajectory_data (LammpsTrajectory): lammps trajectory data.
        retrieved (FolderData): lammps.optimize retrieved folder.

    Returns:
        Tuple containing,
        list: energy_step_data.
        list: force_step_data.
        list: stress_step_data.
    """
    force_step_data = []
    for step in trajectory_data.time_steps:
        traj_block = trajectory_data.get_step_string(step)
        with io.StringIO(traj_block) as handle:
            lammps_traj = read_lammps_dump_text(handle)
        force = lammps_traj.get_forces()
        natot = len(lammps_traj.get_atomic_numbers())
        if tolist:
            force = force.tolist()
        force_step_data.append(force)

    content = retrieved.get_object_content(log_filename).splitlines()
    lines = iter(content)
    while True:
        line = next(lines)
        if line.startswith('Step Temp Press TotEng '):
            columns = re.split(' +', line.strip())
            break
    values = []
    while True:
        line = next(lines)
        if line.startswith('Loop time of'):
            break
        value = re.split(' +', line.strip())
        values.append(value)
    df = pd.DataFrame(values, columns=columns)

    energy_step_data = df["TotEng"].astype(float).values/natot
    if tolist:
        energy_step_data = energy_step_data.tolist()

    stress_columns = ['Pxx', 'Pxy', 'Pxz', 'Pxy', 'Pyy', 'Pyz',  'Pxz', 'Pyz', 'Pzz']
    stress_step_data = df[stress_columns].astype(float).values * 1.0e-3 * utility.kbar2ev_ang3
    if tolist:
        stress_step_data = stress_step_data.tolist()

    return {'energy': energy_step_data, 'force': force_step_data, 'stress': stress_step_data}


@calcfunction
def _pack_Structure_to_StructurecollectionData(**kwargs):
    final_structures = {}
    for label, structure in kwargs.items():
        ID = label.replace(SIMULATOR_PREFIX, "")
        ID = int(ID)
        final_structures[ID] = structure.get_pymatgen()
    return StructurecollectionData(final_structures)


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
        spec.input("initial_structures", valid_type=StructurecollectionData, help='initial structures')
        spec.input("cwd", valid_type=Dict, help='directories to save resulting files of each structure')
        spec.input('potential', valid_type=LammpsPotential, help='lammps potential')
        spec.input('parameters', valid_type=Dict, help='additional parameters to pass \'lammps.optimize\'')

        spec.input('options',
                   valid_type=Dict, default=lambda: Dict(dict=cls._RESOURCE), help='metadata.options')

        spec.outline(
            cls.submit_workchains,
            cls.inspect_workchains
        )
        spec.output("results", valid_type=Dict)
        spec.output("final_structures", valid_type=StructurecollectionData, help='optimized structures')
        spec.output('step_data', valid_type=StepData, help='data during optimization')

    def submit_workchains(self):
        initial_structures_dict = self.inputs.initial_structures.structurecollection
        potential = self.inputs.potential
        code = self.inputs.code_string.value
        metadata_options = self.inputs.options.get_dict()
        parameters = self.inputs.parameters

        code_lammps_force = Code.get_from_string(code)
        for _ID, _structure in initial_structures_dict.items():
            structure = StructureData(pymatgen=_structure)

            builder = code_lammps_force.get_builder()
            builder.structure = structure
            builder.potential = potential
            builder.parameters = parameters
            builder.metadata.options = metadata_options

            future = self.submit(builder)  # or self.submit

            # head = _ID.replace(ID_PREFIX, "")
            key = f'{SIMULATOR_PREFIX}{_ID}'
            print("submit key", key)
            self.to_context(**{key: future})

            # self.to_context(simulator=append_(future)) # It can't send ID.
            # self.to_context(simulator=append_({key: future})) # NG way.

    def inspect_workchains(self):
        calculations = self.ctx

        for key in calculations:
            values = calculations[key]
            if key.startswith(SIMULATOR_PREFIX):
                assert values.is_finished_ok

        # check whether the same IDs are come.
        initial_structures_dict = self.inputs.initial_structures.structurecollection
        cwd_dict = self.inputs.cwd.get_dict()
        structure_id_list = []
        for ID, struc_dict in cwd_dict.items():
            structure_id_list.append(ID)
        calculations_id_list = []
        for key in calculations:
            if key.startswith(SIMULATOR_PREFIX):
                key = key.replace(SIMULATOR_PREFIX, "")
                calculations_id_list.append(key)
        structure_id_list = set(structure_id_list)
        calculations_id_list = set(calculations_id_list)
        if structure_id_list != calculations_id_list:
            print("calculations_id_list", calculations_id_list)
            print("structure_id_list", structure_id_list)
            raise ValueError('inconsistent ID')

        # retrieve all the files
        for key in calculations:
            if key.startswith(SIMULATOR_PREFIX):
                folderdata = calculations[key].outputs.retrieved
                # copy all
                for filename in folderdata.list_object_names():
                    # content = folderdata.get_object_content(filename)
                    ID = key.replace(SIMULATOR_PREFIX, "")
                    cwd = cwd_dict[ID]
                    os.makedirs(cwd, exist_ok=True)

                    # copy content from folderdata.filename to cwd.filename
                    content = None
                    with folderdata.open(filename, "rb") as input_hander:
                        content = input_hander.read()
                    if filename == "_scheduler-stdout.txt":
                        filename = "out.lammps"
                    filepath = os.path.join(cwd, filename)
                    with open(filepath, "wb") as f:
                        f.write(content)

        # process parsed items
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
                ID = key.replace(SIMULATOR_PREFIX, "")
                structures[key] = structure
                cwd = cwd_dict[ID]
                # write lammps final structure to cwd+log.struc
                poscar = Poscar(structure.get_pymatgen())
                poscar.write_file(os.path.join(cwd, "log.struc"))

        final_structures = _pack_Structure_to_StructurecollectionData(**structures)

        self.out('final_structures', final_structures)

        # step_data
        step_data = {}
        for key in calculations:
            if key.startswith(SIMULATOR_PREFIX):
                ID = key.replace(SIMULATOR_PREFIX, "")
                step_data[ID] = _opt_result_to_step_data(calculations[key].outputs.trajectory_data,
                                                         calculations[key].outputs.retrieved)
        step_data_node = StepData(step_data)
        step_data_node.store()

        self.out('step_data', step_data_node)