from aiida.engine import WorkChain, calcfunction
from aiida.plugins import DataFactory
from CrySPY.BO.select_descriptor import select_descriptor
from CrySPY.job.ctrl_job import Ctrl_job
from CrySPY.LAQA.calc_score import calc_laqa_bias

PandasFrameData = DataFactory('dataframe.frame')
StructurecollectionData = DataFactory('cryspy.structurecollection')

EAData = DataFactory('cryspy.ea_data')
BOData = DataFactory('cryspy.bo_data')
LAQAData = DataFactory('cryspy.laqa_data')

EAidData = DataFactory('cryspy.ea_id_data')
BOidData = DataFactory('cryspy.bo_id_data')
LAQAidData = DataFactory('cryspy.laqa_id_data')

LAQAStepData = DataFactory('cryspy.laqa_step_data')


ConfigparserData = DataFactory('cryspy.configparser')
RinData = DataFactory('cryspy.rin_data')


def _update_bo_data(rin_node, bo_data_node, rslt_data_node, optimized_structures_node):
    """
    update detail_data_node for the optimize structures.

    from ctrl_collect_bo.
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


def _calculate_laqa_scores(step_data, wf_laqa=1.0, ws_laqa=1.0):
    """calculate LAQA scores.

    calculate -energy + wf_laqa* force_bias + ws_lawa * stress.

    Args:
        step_data (dict): history data of energy, force and stresses.
        wf_laqa (float): force factor.
        ws_laqa (float): stress factor.
    """
    lines = []
    for key, each_step_data in step_data.items():
        wf_laqa_bias = calc_laqa_bias(each_step_data["force"], wf_laqa)
        ws_laqa_bias = np.linalg.norm(each_step_data["stress"][-1]) * ws_laqa
        energy = each_step_data["energy"][-1]
        nstep = len(each_step_data["energy"])
        laqa_score = -energy + wf_laqa_bias + ws_laqa_bias
        lines.append([key, energy, wf_laqa_bias, ws_laqa_bias, nstep, laqa_score])
    columns = ['ID', 'energy', 'wf_laqa_bias', 'ws_laqa_bias', 'nstep', 'score']
    laqa_df = pd.DataFrame(lines,  columns=columns)
    return laqa_df


def _extract_laqa_score(laqa_df):
    IDs = laqa_df["ID"].astype(int).values.tolist()
    scores = laqa_df["score"].astype(float).values.tolist()
    laqa_score = {}
    for ID, score in zip(IDs, scores):
        ID = int(ID)
        laqa_score.update({ID: score})
    return laqa_score


def _update_step_data(laqa_data_node, step_data_node):
    step_data = laqa_data_node.laqa_data[0]
    new_step_data = step_data_node.step_data
    for key,value in new_step_data.items():
        step_data.update({key: value})
    return step_data


def _generate_laqa_data(rin_node, laqa_data_node, step_data_node):
    rin = rin_node.rin
    updated_step_data = _update_step_data(laqa_data_node, step_data_node)
    laqa_df = _calculate_laqa_scores(updated_step_data, rin.wf_laqa, rin.ws_laqa)
    laqa_score = _extract_laqa_score(laqa_df)
    laqa_node = LAQAData((updated_step_data, laqa_score))
    df_node = PandasFrameData(df=laqa_df)
    return laqa_node, df_node


def _laqa_next_selection(laqa_data_node, nselect_laqa):
    laqa_score = laqa_data_node.laqa_data[1]
    id_queueing = []
    for k, v in sorted(laqa_score.items(), key=lambda x: -x[1]):
        print(k, v)
        # if v == -float('int'):
        #    break
        id_queueing.append(k)
        if len(id_queueing) >= nselect_laqa:
            break
    return id_queueing


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
        spec.input("id_data", valid_type=(EAidData, BOidData, LAQAidData), help='id_data')
        spec.input('step_data', valid_type=LAQAStepData, required=False, help='optimization step data')
        spec.input("detail_data", valid_type=(EAData, BOData, LAQAData), help='detail_data')
        spec.input("stat", valid_type=ConfigparserData, help='cryspy_in content')
        spec.input('cryspy_in', valid_type=RinData, help='cryspy_in')

        spec.outline(
            cls.validate_inputdata,
            cls.call_next_sg
        )

        spec.output('id_data', valid_type=(EAidData, BOidData, LAQAidData))
        spec.output('detail_data', valid_type=(EAData, BOData, LAQAData))
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
        elif isinstance(id_data, LAQAidData):
            algo = 'LAQA'
        else:
            raise TypeError(f'unknown type for id_data. type={type(id_data)}')

        if isinstance(detail_data, EAData):
            algo_data = "EA"
        elif isinstance(detail_data, BOData):
            algo_data = "BO"
        elif isinstance(detail_data, LAQAData):
            algo_data = "LAQA"
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
        elif isinstance(id_data, LAQAidData):
            algo = 'LAQA'
            id_data = id_data.laqa_id_data
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
        elif algo == 'LAQA':
            step_data_node = self.inputs.step_data
            detail_data_node = self.inputs.detail_data
            detail_data_node, df_laqa_score = _generate_laqa_data(self.inputs.cryspy_in, detail_data_node, step_data_node)
            detail_data_node.store()
            # df_laqa_score.store()
        else:
            raise TypeError(f'internal error: unknown type for id_data, type={type(id_data)}')

        rin = self.inputs.cryspy_in.rin
        stat = self.inputs.stat.configparser

        if algo == "BO":
            # BO doesn't increase structures.
            jobs = Ctrl_job(rin, stat, initial_structures,
                            opt_struc,
                            rslt_data, id_data, detail_data
                            )
            rin, stat, _, id_data, detail_data, rslt_data = jobs.next_sg()
            id_data_node = BOidData(id_data)
            id_data_node.store()
            detail_data_node = BOData(detail_data)
            detail_data_node.store()
            struc_node = self.inputs.initial_structures  # the same node
        elif algo == "EA":
            jobs = Ctrl_job(rin, stat, initial_structures,
                            opt_struc,
                            rslt_data, id_data, detail_data
                            )
            rin, stat, init_struc_data, id_data, detail_data, rslt_data = jobs.next_sg()
            id_data_node = EAidData(id_data)
            id_data_node.store()
            detail_data_node = EAData(detail_data)
            detail_data_node.store()
            struc_node = StructurecollectionData(init_struc_data)
            struc_node.store()
        elif algo == 'LAQA':
            id_queueing = _laqa_next_selection(detail_data_node, rin.nselect_laqa)
            id_data_node = LAQAidData((id_queueing, [], []))
            id_data_node.store()
            struc_node = self.inputs.optimized_structures

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
