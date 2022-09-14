
import os

from aiida.engine import WorkChain
from aiida.plugins import DataFactory
from aiida.orm import Dict


PandasFrameData = DataFactory('dataframe.frame')
StructurecollectionData = DataFactory('cryspy.structurecollection')
EAData = DataFactory('cryspy.ea_data')
EAidData = DataFactory('cryspy.ea_id_data')
ConfigparserData = DataFactory('cryspy.configparser')


class select_structure_to_run_WorkChain(WorkChain):
    @classmethod
    def define(cls, spec):
        super().define(spec)
        spec.input("ea_id_data", valid_type=EAidData, help='ea_id_data.')
        spec.input("init_struc", valid_type=StructurecollectionData, help='initial structures.')
        spec.outline(
            cls.select_structures
        )

        spec.output("init_struc", valid_type=StructurecollectionData, help='selected initial structures.')
        spec.output("work_path", valid_type=Dict, help='directory to saved results.')
        spec.output("ea_id_data", valid_type=EAidData)

    def select_structures(self):
        ea_id_node = self.inputs.ea_id_data
        structure_node = self.inputs.init_struc

        ea_id_data = ea_id_node.ea_id_data
        structures = structure_node.structurecollection
        id_queueing = ea_id_data[1]
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
        ea_id = EAidData((ea_id_data[0], id_queueing, ea_id_data[2]))
        ea_id.store()
        self.out('ea_id_data', ea_id)
