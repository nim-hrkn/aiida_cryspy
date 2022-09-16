

from aiida.plugins import DataFactory
from aiida.orm import Str
from aiida.engine import WorkChain
import io

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
BOData = DataFactory('cryspy.bo_data')
EAidData = DataFactory('cryspy.ea_id_data')
RSidData = DataFactory('cryspy.rs_id_data')
BOidData = DataFactory('cryspy.bo_id_data')
RinData = DataFactory('cryspy.rin_data')

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
        spec.input("cryspy_in", valid_type=(Str, ConfigparserData, SinglefileData),
                   help='cryspy_in. (temporary implementation)')

        spec.outline(
            cls.call_cryspy_initialize
        )

        spec.output("initial_structures", valid_type=StructurecollectionData, help='initial structures')
        spec.output('rslt_data', valid_type=PandasFrameData, help='summary dataframe')
        spec.output('id_data', valid_type=(RSidData, EAidData, BOidData), help='cryspy ea_id_data')
        spec.output('detail_data', valid_type=(EAData, BOData), help='cryspy ea_data')
        spec.output('stat', valid_type=ConfigparserData, help='modified cryspy_in content')
        spec.output('cryspy_in', valid_type=RinData, help='cryspy_in content')

    def call_cryspy_initialize(self):
        from CrySPY.start import cryspy_init
        if isinstance(self.inputs.cryspy_in, ConfigparserData):
            init_struc_data, opt_struc_data, rin, stat, rslt_data, id_data, detail_data = cryspy_init.initialize(
                self.inputs.cryspy_in.configparser)
        elif isinstance(self.inputs.cryspy_in, Str):
            init_struc_data, opt_struc_data, rin, stat, rslt_data, id_data, detail_data = cryspy_init.initialize(
                self.inputs.cryspy_in.value)
        elif isinstance(self.inputs.cryspy_in, SinglefileData):
            content = self.inputs.cryspy_in.get_content()
            with io.StringIO(content) as handle:
                init_struc_data, opt_struc_data, rin, stat, rslt_data, id_data, detail_data = cryspy_init.initialize(
                    handle)
        else:
            raise TypeError(f'unknown type for cryspy_in. type={type(self.inputs.cryspy_in)}')

        pystructuredict = StructurecollectionData(init_struc_data)
        pystructuredict.store()

        self.out('initial_structures', pystructuredict)

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

        elif algo == "BO":
            bo_id_node = BOidData(id_data)
            bo_id_node.store()
            self.out('id_data', bo_id_node)
            bo_node = BOData(detail_data)
            bo_node.store()
            self.out('detail_data', bo_node)
        else:
            raise ValueError(f'algo not supported. algo={algo}')

        stat = ConfigparserData(stat)
        stat.store()
        self.out('stat', stat)

        cryspy_in = RinData(rin)
        cryspy_in.store()
        self.out("cryspy_in", cryspy_in)
