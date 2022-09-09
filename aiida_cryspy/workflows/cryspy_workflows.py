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
TrajectoryData = DataFactory('array.trajectory')


SIMULATOR_PREFIX = 'simulator_'
ID_PREFIX = 'ID_'


class initialize_WorkChain(WorkChain):
    """start.initialize()
    """

    @classmethod
    def define(cls, spec):
        super().define(spec)
        spec.input("cryspy_in", valid_type=SinglefileData, help='cryspy_in. (temporary implementation)')

        spec.outline(
            cls.start_initialize,
            cls.make_aiidadata,
        )
        spec.output("init_struc", valid_type=Dict, help='initial structures')
        spec.output("opt_struc", valid_type=Dict, help='optimized structures')
        spec.output("rstl_data", valid_type=Dict, help='rst_data')
        spec.output("ea_info", valid_type=Dict, help='ea_info')
        spec.output("ea_origin", valid_type=Dict, help='ea_origin')
        spec.output("ea_id_gen", valid_type=Int, help='ea_origin')
        spec.output("ea_id_queueing", valid_type=List, help='ea_origin')
        spec.output("ea_id_running", valid_type=List, help='ea_origin')

    def start_initialize(self):
        from CrySPY.start import cryspy_init
        cryspy_init.initialize(self.inputs.cryspy_in)

    def make_aiidadata(self):
        """must handle
        EA_data.pkl  
        EA_id_data.pkl  
        init_struc_data.pkl  
        opt_struc_data.pkl  
        rslt_data.pkl
        """
        @calcfunction
        def aiida_load_init_struc():
            from CrySPY.IO.pkl_data import load_init_struc
            struc_dict = load_init_struc()
            structures = {}
            for _i, value in struc_dict.items():
                content = value.as_dict()
                key = f'ID_{_i}'
                structures[key] = content
            return Dict(dict=structures)
        self.out('init_struc', aiida_load_init_struc())

        @calcfunction
        def aiida_load_opt_struc():
            from CrySPY.IO.pkl_data import load_opt_struc
            struc_dict = load_opt_struc()
            structures = {}
            for _i, value in struc_dict.items():
                content = value.as_dict()
                key = f'ID_{_i}'
                structures[key] = content
            return Dict(dict=structures)
        self.out('opt_struc', aiida_load_opt_struc())

        @calcfunction
        def aiida_load_rslt():
            from CrySPY.IO.pkl_data import load_rslt
            rstl_data_dic = {}
            rstl_data = load_rslt()
            for key in rstl_data.columns:
                rstl_data_dic[key] = rstl_data[key].values.tolist()
            return Dict(dict=rstl_data_dic)
        self.out('rstl_data', aiida_load_rslt())

        @calcfunction
        def aiida_load_ea_info():
            from CrySPY.IO.pkl_data import load_ea_data
            ea_data = {}
            elite_struc, elite_fitness, ea_info, ea_origin = load_ea_data()
            ea_info_dic = {}
            for key in ea_info.columns:
                ea_info_dic[key] = ea_info[key].values.tolist()
            return Dict(dict=ea_info_dic)

        @calcfunction
        def aiida_load_ea_origin():
            from CrySPY.IO.pkl_data import load_ea_data
            ea_data = {}
            elite_struc, elite_fitness, ea_info, ea_origin = load_ea_data()

            ea_origin_dic = {}
            for key in ea_origin.columns:
                ea_origin_dic[key] = ea_origin[key].values.tolist()
            return Dict(dict=ea_origin_dic)
        self.out('ea_info', aiida_load_ea_info())
        self.out('ea_origin', aiida_load_ea_origin())

        @calcfunction
        def aiida_load_ea_id_gen():
            from CrySPY.IO.pkl_data import load_ea_id
            gen, id_queueing, id_running = load_ea_id()
            return Int(gen)

        @calcfunction
        def aiida_load_ea_id_queueing():
            from CrySPY.IO.pkl_data import load_ea_id
            gen, id_queueing, id_running = load_ea_id()
            return List(list=id_queueing)

        @calcfunction
        def aiida_load_ea_id_running():
            from CrySPY.IO.pkl_data import load_ea_id
            gen, id_queueing, id_running = load_ea_id()
            return List(list=id_running)
        self.out('ea_id_gen', aiida_load_ea_id_gen())
        self.out('ea_id_queueing', aiida_load_ea_id_queueing())
        self.out('ea_id_running', aiida_load_ea_id_running())


@calcfunction
def _pack_Structure_to_Dict(**kwargs):

    final_structures = {}
    for label, structure in kwargs.items():
        py_structure = structure.get_pymatgen()
        struc_dic = py_structure.as_dict()
        final_structures[label] = struc_dic
    return Dict(dict=final_structures)


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
        spec.input("initial_structures", valid_type=Dict, help='initial structures')
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
        spec.output("final_structures", valid_type=Dict, help='optimized structures')

    def submit_workchains(self):
        initial_structures_dict = self.inputs.initial_structures.get_dict()
        potential = self.inputs.potential
        code = self.inputs.code_string.value
        metadata_options = self.inputs.options.get_dict()
        parameters = self.inputs.parameters

        code_lammps_force = Code.get_from_string(code)
        for _ID, struc_dict in initial_structures_dict.items():
            _structure = Structure.from_dict(struc_dict)
            structure = StructureData(pymatgen=_structure)

            builder = code_lammps_force.get_builder()
            builder.structure = structure
            builder.potential = potential
            builder.parameters = parameters
            builder.metadata.options = metadata_options

            future = self.submit(builder)  # or self.submit

            head = _ID.replace(ID_PREFIX, "")
            key = f'{SIMULATOR_PREFIX}{head}'

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
        initial_structures_dict = self.inputs.initial_structures.get_dict()
        cwd_dict = self.inputs.cwd.get_dict()
        structure_id_list = []
        for _ID, struc_dict in cwd_dict.items():
            ID = _ID.replace(ID_PREFIX, "")
            structure_id_list.append(ID)
        calculations_id_list = []
        for key in calculations:
            if key.startswith(SIMULATOR_PREFIX):
                key = key.replace(SIMULATOR_PREFIX, "")
                calculations_id_list.append(key)
        structure_id_list = set(structure_id_list)
        calculations_id_list = set(calculations_id_list)
        if structure_id_list != calculations_id_list:
            raise ValueError('inconsistent ID')

        # retrieve all the files
        for key in calculations:
            if key.startswith(SIMULATOR_PREFIX):
                folderdata = calculations[key].outputs.retrieved
                # copy all
                for filename in folderdata.list_object_names():
                    # content = folderdata.get_object_content(filename)
                    ID = key.replace(SIMULATOR_PREFIX, "")
                    ID_key = f'{ID_PREFIX}{ID}'
                    cwd = cwd_dict[ID_key]
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

        # change stat_job
        for _ID, struc_dict in initial_structures_dict.items():
            cwd = cwd_dict[_ID]
            os.makedirs(cwd, exist_ok=True)
            filepath = os.path.join(cwd, 'stat_job')
            with open(filepath, "r") as f:
                content = f.read().splitlines()

            content2 = [content[0], content[1]]
            content2.append('done')
            with open(filepath, "w") as f:
                f.write("\n".join(content2))

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
                structures[key] = structure

                ID = key.replace(SIMULATOR_PREFIX, "")
                ID_key = f"{ID_PREFIX}{ID}"
                cwd = cwd_dict[ID_key]
                # write lammps final structure to cwd+log.struc
                poscar = Poscar(structure.get_pymatgen())
                poscar.write_file(os.path.join(cwd, "log.struc"))

        final_structures = _pack_Structure_to_Dict(**structures)

        self.out('final_structures', final_structures)
