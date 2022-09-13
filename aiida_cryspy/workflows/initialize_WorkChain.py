

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
        spec.input("cryspy_in", valid_type=Str, help='cryspy_in. (temporary implementation)')

        spec.outline(
            cls.call_cryspy_initialize
        )

        spec.output("init_struc", valid_type=StructurecollectionData, help='initial structures')
        spec.output('rslt_data', valid_type=PandasFrameData, help='summary dataframe')
        spec.output('ea_id_data', valid_type=EAidData, help='cryspy ea_id_data')
        spec.output('ea_data', valid_type=EAData, help='cryspy ea_data')

    def call_cryspy_initialize(self):
        from CrySPY.start import cryspy_init
        init_struc_data, opt_struc_data, _, rslt_data, ea_id_data, ea_data = cryspy_init.initialize(
            self.inputs.cryspy_in.value)

        pystructuredict = StructurecollectionData(init_struc_data)
        pystructuredict.store()

        self.out('init_struc', pystructuredict)

        rslt_node = PandasFrameData(rslt_data)
        rslt_node.store()
        self.out('rslt_data', rslt_node)

        ea_id_node = EAidData(ea_id_data)
        ea_id_node.store()
        self.out('ea_id_data', ea_id_node)

        ea_node = EAData(ea_data)
        ea_node.store()
        self.out('ea_data', ea_node)
