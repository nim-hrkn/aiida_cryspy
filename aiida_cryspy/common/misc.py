
import copy
from typing import Union
from aiida.engine import calcfunction
from aiida.plugins import DataFactory
from aiida.orm import Dict
import numpy as np


PandasFrameData = DataFactory('dataframe.frame')
StructurecollectionData = DataFactory('cryspy.structurecollection')
EAData = DataFactory('cryspy.ea_data')
EAidData = DataFactory('cryspy.ea_id_data')
RSidData = DataFactory('cryspy.rs_id_data')
BOidData = DataFactory('cryspy.bo_id_data')

ConfigparserData = DataFactory('cryspy.configparser')


@calcfunction
def generate_rlst(all_initial_structures_node: StructurecollectionData,
                  all_optimized_structures_node: StructurecollectionData,
                  optimize_result: Dict,
                  id_data_node: Union[RSidData, EAidData, BOidData],
                  rslt_data_node: PandasFrameData,
                  stat_node: ConfigparserData):
    init_struc_data = all_initial_structures_node.structurecollection
    opt_struc = all_optimized_structures_node.structurecollection
    opt_results = optimize_result.get_dict()
    rslt_data = rslt_data_node.df
    if isinstance(id_data_node, EAidData):
        gen = id_data_node.ea_id_data[0]
        algo = "EA"
    elif isinstance(id_data_node, RSidData):
        gen = 1
        algo = "RS"
    elif isinstance(id_data_node, BOidData):
        gen = id_data_node.bo_id_data[0]
        algo = "BO"
    else:
        raise TypeError(f'unknown type for id_data_node, type={type(id_data_node)}')
    magmon = None
    check_opt = 'done'

    stat = stat_node.configparser
    symprec = float(stat["structure"]["symprec"])

    for i, energy in zip(opt_results["index"], opt_results["energy"]):

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
        if algo == "EA":
            row = [gen, in_spg[1], in_spg[0], opt_spg[1], opt_spg[0],
                   energy, magmon, check_opt]
        elif algo == "RS":
            row = [in_spg[1], in_spg[0], opt_spg[1], opt_spg[0],
                   energy, magmon, check_opt]
        elif algo == "BO":
            row = [gen, in_spg[1], in_spg[0], opt_spg[1], opt_spg[0],
                   energy, magmon, check_opt]
        rslt_data.loc[i] = row

    return PandasFrameData(rslt_data)


@calcfunction
def merge_structurecollection(struc1: StructurecollectionData, struc2: StructurecollectionData):
    struc1 = struc1.structurecollection
    struc2 = struc2.structurecollection
    for key, value in struc2.items():
        if key not in struc1:
            struc1[key] = value
        else:
            print(f"Warning: key {key} is in struc1.")
    return StructurecollectionData(struc1)
