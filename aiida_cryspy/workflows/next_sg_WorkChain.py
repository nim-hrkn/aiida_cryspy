

from aiida.engine import WorkChain, calcfunction
from aiida.plugins import DataFactory
from CrySPY.BO.select_descriptor import select_descriptor
from CrySPY.job.ctrl_job import Ctrl_job

PandasFrameData = DataFactory('dataframe.frame')
StructurecollectionData = DataFactory('cryspy.structurecollection')

EAData = DataFactory('cryspy.ea_data')
BOData = DataFactory('cryspy.bo_data')

EAidData = DataFactory('cryspy.ea_id_data')
BOidData = DataFactory('cryspy.bo_id_data')

ConfigparserData = DataFactory('cryspy.configparser')
RinData = DataFactory('cryspy.rin_data')


def _update_bo_data(rin_node, bo_data_node, rslt_data_node, optimized_structures_node):
    """
    update descriptors for the optimize structures.
    """
    rin = rin_node.rin
    bo_data = bo_data_node.bo_data
    opt_dscrpt_data = {}
    for ID in rslt_data_node.df["Opt"].index:
        status = rslt_data_node.df["Opt"].loc[ID]
        # Must be 'status' used?
        opt_struc = optimized_structures_node.structurecollection[ID]
        tmp_dscrpt = select_descriptor(rin, {ID: opt_struc})
        opt_dscrpt_data.update(tmp_dscrpt)
    opt_dscrpt_data.keys()
    detail_data_node = BOData((bo_data[0], opt_dscrpt_data, bo_data[3], bo_data[3], bo_data[4]))
    return detail_data_node


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
        spec.input("id_data", valid_type=(EAidData, BOidData), help='id_data')
        spec.input("detail_data", valid_type=(EAData, BOData), help='detail_data')
        spec.input("stat", valid_type=ConfigparserData, help='cryspy_in content')
        spec.input('cryspy_in', valid_type=RinData, help='cryspy_in')

        spec.outline(
            cls.validate_inputdata,
            cls.call_next_sg
        )

        spec.output('id_data', valid_type=(EAidData, BOidData))
        spec.output('detail_data', valid_type=(EAData, BOData))
        spec.output('rslt_data', valid_type=PandasFrameData)
        spec.output('initial_structures', valid_type=StructurecollectionData)
        spec.output("stat", valid_type=ConfigparserData)
        spec.output('cryspy_in', valid_type=RinData)

    def validate_inputdata(self):
        id_data = self.inputs.id_data
        detail_data = self.inputs.detail_data
        # both data must be consistent
        if isinstance(id_data, EAidData):
            algo = "EA"
        elif isinstance(id_data, BOidData):
            algo = "BO"
        else:
            raise TypeError(f'unknown type for id_data. type={type(id_data)}')

        if isinstance(detail_data, EAData):
            algo_data = "EA"
        elif isinstance(detail_data, BOData):
            algo_data = "BO"
        else:
            raise TypeError(f'unknown type for detail_data. type={type(detail_data)}')

        if algo != algo_data:
            raise TypeError(f'type(id_data) != type(detail_data), type={type(id_data)}, type={type(detail_data)}')
        self.ctx.algo = algo

    def call_next_sg(self):

        initial_structures = self.inputs.initial_structures.structurecollection
        opt_struc = self.inputs.optimized_structures.structurecollection
        rslt_data = self.inputs.rslt_data.df
        algo = self.ctx.algo

        id_data = self.inputs.id_data
        if isinstance(id_data, EAidData):
            algo = 'EA'
            id_data = id_data.ea_id_data
        elif isinstance(id_data, BOidData):
            algo = "BO"
            id_data = id_data.bo_id_data
        # the other types are added.
        else:
            raise TypeError(f'internal error: unknown type for id_data, type={type(id_data)}')

        if algo == "EA":
            detail_data = self.inputs.detail_data.ea_data
        # algo=="RS" doesn't come to this function.
        elif algo == "BO":
            detail_data_node = _update_bo_data(self.inputs.cryspy_in,
                                               self.inputs.detail_data,
                                               self.inputs.rslt_data, 
                                               self.inputs.optimized_structures)
            detail_data = detail_data_node.bo_data
        # the other types are added.
        else:
            raise TypeError(f'internal error: unknown type for id_data, type={type(id_data)}')

        rin = self.inputs.cryspy_in.rin
        stat = self.inputs.stat.configparser

        jobs = Ctrl_job(rin, stat, initial_structures,
                        opt_struc,
                        rslt_data, id_data, detail_data
                        )

        if algo == "BO":
            # BO doesn't increase structures.
            rin, stat, _, id_data, detail_data, rslt_data = jobs.next_sg()
            id_data_node = BOidData(id_data)
            id_data_node.store()
            detail_data_node = BOData(detail_data)
            detail_data_node.store()
            struc_node = self.inputs.initial_structures  # the same node
        elif algo == "EA":
            rin, stat, init_struc_data, id_data, detail_data, rslt_data = jobs.next_sg()
            id_data_node = EAidData(id_data)
            id_data_node.store()
            detail_data_node = EAData(detail_data)
            detail_data_node.store()
            struc_node = StructurecollectionData(init_struc_data)
            struc_node.store()

        rslt_data_node = PandasFrameData(rslt_data)
        rslt_data_node.store()

        stat_node = ConfigparserData(stat)
        stat_node.store()

        rin_node = RinData(rin)
        rin_node.store()

        self.out("id_data", id_data_node)
        self.out("detail_data", detail_data_node)
        self.out("rslt_data", rslt_data_node)
        self.out('initial_structures', struc_node)
        self.out('stat', stat_node)
        self.out('cryspy_in', rin_node)
