

from aiida.engine import WorkChain
from aiida.plugins import DataFactory
from aiida.orm import Str

from CrySPY.job.ctrl_job import Ctrl_job

PandasFrameData = DataFactory('dataframe.frame')
StructurecollectionData = DataFactory('cryspy.structurecollection')
EAData = DataFactory('cryspy.ea_data')
EAidData = DataFactory('cryspy.ea_id_data')
ConfigparserData = DataFactory('cryspy.configparser')


class next_sg_WorkChain(WorkChain):
    """next_sg()

    Q. Why are the initial_strucutures as input  necessary?
    A. It is to add new structures to the initial_structures.

    """
    @classmethod
    def define(cls, spec):
        super().define(spec)
        spec.input("initial_structures", valid_type=StructurecollectionData, help='initial structures')
        spec.input("optimized_structures", valid_type=StructurecollectionData, help='optimized structures')
        spec.input("rslt_data", valid_type=PandasFrameData, help='summary data')
        spec.input("ea_id_data", valid_type=EAidData, help='ea_id_data')
        spec.input("ea_data", valid_type=EAData, help='ea_data')
        spec.input("stat", valid_type=ConfigparserData, help='cryspy_in content')
        spec.input('cryspy_in', valid_type=(Str, ConfigparserData), help='cryspy_in')

        spec.outline(
            cls.call_next_sg
        )

        spec.output('ea_id_data', valid_type=EAidData)
        spec.output('ea_data', valid_type=EAData)
        spec.output('rslt_data', valid_type=PandasFrameData)
        spec.output('initial_structures', valid_type=StructurecollectionData)
        spec.output("stat", valid_type=ConfigparserData)

    def call_next_sg(self):

        initial_structures = self.inputs.initial_structures.structurecollection
        opt_struc = self.inputs.optimized_structures.structurecollection
        rslt_data = self.inputs.rslt_data.df
        ea_id_data = self.inputs.ea_id_data.ea_id_data
        ea_data = self.inputs.ea_data.ea_data
        stat = self.inputs.stat.configparser
        cryspy_in_node = self.inputs.cryspy_in
        if isinstance(cryspy_in_node, Str):
            cryspy_in = cryspy_in_node.value
        elif isinstance(cryspy_in_node, ConfigparserData):
            cryspy_in = cryspy_in_node.configparser
        else:
            raise TypeError(f'internal error, unknown type of cryspy_in {type(cryspy_in)}')

        jobs = Ctrl_job(cryspy_in, stat, initial_structures,
                        opt_struc,
                        rslt_data, ea_id_data,
                        )

        stat, ea_id_data, ea_data, rslt_data, init_struc_data = jobs.next_sg(ea_data)

        ea_id_data_node = EAidData(ea_id_data)
        ea_id_data_node.store()
        ea_data_node = EAData(ea_data)
        ea_data_node.store()
        rslt_data_node = PandasFrameData(rslt_data)
        rslt_data_node.store()
        struc_node = StructurecollectionData(init_struc_data)
        struc_node.store()
        stat_node = ConfigparserData(stat)
        stat_node.store()

        self.out("ea_id_data", ea_id_data_node)
        self.out("ea_data", ea_data_node)
        self.out("rslt_data", rslt_data_node)
        self.out('initial_structures', struc_node)
        self.out('stat', stat_node)
