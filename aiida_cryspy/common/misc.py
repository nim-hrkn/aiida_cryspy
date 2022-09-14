
from aiida.engine import calcfunction
from aiida.plugins import DataFactory
from aiida.orm import Dict
import numpy as np


PandasFrameData = DataFactory('dataframe.frame')
StructurecollectionData = DataFactory('cryspy.structurecollection')
EAData = DataFactory('cryspy.ea_data')
EAidData = DataFactory('cryspy.ea_id_data')
ConfigparserData = DataFactory('cryspy.configparser')


@calcfunction
def generate_rlst(all_initial_structures_node: StructurecollectionData,
                  all_optimized_structures_node: StructurecollectionData,
                  optimize_result: Dict,
                  ea_id_data_node: EAidData,
                  rslt_data_node: PandasFrameData,
                  stat_node: ConfigparserData):
    init_struc_data = all_initial_structures_node.structurecollection
    opt_struc = all_optimized_structures_node.structurecollection
    opt_results = optimize_result.get_dict()
    rslt_data = rslt_data_node.df
    gen = ea_id_data_node.ea_id_data[0]
    magmon = None
    check_opt = 'done'

    stat = stat_node.configparser
    symprec = float(stat["structure"]["symprec"])

    symprec = symprec
    for i, energy in zip(opt_results["index"], opt_results["energy"]):
        print("check_structure i, energy", i, energy)
        print(init_struc_data[i])
        print(opt_struc[i])
        if energy is not None:
            check_opt = 'done'
        else:
            check_opt = 'not_yet'
        if energy is None:
            energy = np.nan
        else:
            natot = len(init_struc_data[i].atomic_numbers)
            energy /= natot

        in_spg = init_struc_data[i].get_space_group_info(symprec=symprec)
        opt_spg = opt_struc[i].get_space_group_info(symprec=symprec)
        rslt_data.loc[i] = [gen, in_spg[1], in_spg[0], opt_spg[1], opt_spg[0],
                            energy, magmon, check_opt]

    return PandasFrameData(rslt_data)
