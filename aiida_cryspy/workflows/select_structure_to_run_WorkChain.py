
import os

from aiida.engine import WorkChain
from aiida.plugins import DataFactory
from aiida.orm import Dict


PandasFrameData = DataFactory('dataframe.frame')
StructurecollectionData = DataFactory('cryspy.structurecollection')
EAData = DataFactory('cryspy.ea_data')
EAidData = DataFactory('cryspy.ea_id_data')
RSidData = DataFactory('cryspy.rs_id_data')
ConfigparserData = DataFactory('cryspy.configparser')


class select_structure_to_run_WorkChain(WorkChain):
    @classmethod
    def define(cls, spec):
        super().define(spec)
        spec.input("id_data", valid_type=(RSidData, EAidData), help='ea_id_data.')
        spec.input("init_struc", valid_type=StructurecollectionData, help='initial structures.')
        spec.outline(
            cls.select_structures
        )

        spec.output("init_struc", valid_type=StructurecollectionData, help='selected initial structures.')
        spec.output("work_path", valid_type=Dict, help='directory to saved results.')
        spec.output("id_data", valid_type=(RSidData, EAidData))

    def select_structures(self):

        id_node = self.inputs.id_data
        if isinstance(id_node, EAidData):
            id_data = id_node.ea_id_data
            id_queueing = id_data[1]
        elif isinstance(id_node, RSidData):
            id_data = id_node.rs_id_data
            id_queueing = id_data[0]

        structure_node = self.inputs.init_struc
        structures = structure_node.structurecollection

        work_path_dic = {}
        structures_dic = {}
        for cid in id_queueing:
            work_path = './work/{:06}/'.format(cid)
            work_path = os.path.abspath(work_path)
            structures_dic[cid] = structures[cid]
            ID = str(cid)
            work_path_dic[ID] = work_path

        struc = StructurecollectionData(structures_dic)
        struc.store()
        self.out('init_struc', struc)

        d = Dict(dict=work_path_dic)
        d.store()
        self.out('work_path', d)

        id_queueing = []
        if isinstance(id_node, EAidData):
            id_node = EAidData((id_data[0], id_queueing, id_data[2]))
        elif isinstance(id_node, RSidData):
            id_node = RSidData((id_queueing, id_data[1]))
        id_node.store()
        self.out('id_data', id_node)
