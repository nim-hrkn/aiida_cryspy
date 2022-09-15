

from aiida.plugins import DataFactory
from aiida.orm import Str
from aiida.engine import WorkChain


# load types
StructureData = DataFactory('structure')
FolderData = DataFactory('folder')
SinglefileData = DataFactory('singlefile')
ArrayData = DataFactory('array')
LammpsPotential = DataFactory('lammps.potential')
TrajectoryData = DataFactory('array.trajectory')

# PandasFrameData = DataFactory('cryspy.dataframe')
PandasFrameData = DataFactory('dataframe.frame')

ConfigparserData = DataFactory('cryspy.configparser')
StructurecollectionData = DataFactory('cryspy.structurecollection')
EAData = DataFactory('cryspy.ea_data')
EAidData = DataFactory('cryspy.ea_id_data')
RSidData = DataFactory('cryspy.rs_id_data')


SIMULATOR_PREFIX = 'simulator_'
ID_PREFIX = 'ID_'


class initialize_WorkChain(WorkChain):
    """ corresponds to cryspy_init.initialize().

    Output data are
    - rslt_data
    and
    - EA: ea_id_data, ea_data

    - ea_id_data: gen, id_queueing, id_running
    - ea_data: elite_struc, elite_fitness, ea_info, ea_origin

    """

    @classmethod
    def define(cls, spec):
        super().define(spec)
        spec.input("cryspy_in", valid_type=(Str, ConfigparserData), help='cryspy_in. (temporary implementation)')

        spec.outline(
            cls.call_cryspy_initialize
        )

        spec.output("init_struc", valid_type=StructurecollectionData, help='initial structures')
        spec.output('rslt_data', valid_type=PandasFrameData, help='summary dataframe')
        spec.output('id_data', valid_type=(RSidData, EAidData), help='cryspy ea_id_data')
        spec.output('detail_data', valid_type=EAData, help='cryspy ea_data')
        spec.output('stat', valid_type=ConfigparserData, help='cryspy_in content')

    def call_cryspy_initialize(self):
        from CrySPY.start import cryspy_init
        if isinstance(self.inputs.cryspy_in, ConfigparserData):
            init_struc_data, opt_struc_data, stat, rslt_data, id_data, detail_data = cryspy_init.initialize(
                self.inputs.cryspy_in.configparser)
        elif isinstance(self.inputs.cryspy_in, Str):
            init_struc_data, opt_struc_data, stat, rslt_data, id_data, detail_data = cryspy_init.initialize(
                self.inputs.cryspy_in.value)

        pystructuredict = StructurecollectionData(init_struc_data)
        pystructuredict.store()

        self.out('init_struc', pystructuredict)

        rslt_node = PandasFrameData(rslt_data)
        rslt_node.store()
        self.out('rslt_data', rslt_node)

        algo = stat["basic"]["algo"]

        if algo == "EA":
            ea_id_node = EAidData(id_data)
            ea_id_node.store()
            self.out('id_data', ea_id_node)

            ea_node = EAData(detail_data)
            ea_node.store()
            self.out('detail_data', ea_node)
        elif algo == "RS":
            rs_id_node = RSidData(id_data)
            rs_id_node.store()
            self.out('id_data', rs_id_node)
            # not detail_data output
        else:
            raise ValueError(f'algo not supported. algo={algo}')

        stat = ConfigparserData(stat)
        stat.store()
        self.out('stat', stat)
