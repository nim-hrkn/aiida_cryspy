from CrySPY.LAQA.calc_score import calc_laqa_bias
import pandas as pd
from aiida.engine import WorkChain
from aiida.plugins import DataFactory
import numpy as np
from aiida.engine import calcfunction


RinData = DataFactory('cryspy.rin_data')
StepData = DataFactory('cryspy.step_data')
PandasFrameData = DataFactory('dataframe.frame')
LAQAData = DataFactory('cryspy.laqa_data')
LAQAidData = DataFactory('cryspy.laqa_id_data')


def _calculate_laqa_scores(step_data_node, wf_laqa=1.0, ws_laqa=1.0):
    """calculate LAQA scores.

    calculate -energy + wf_laqa* force_bias + ws_lawa * stress.

    Args:
        step_data_node (StepData): history data of energy, force and stresses.
        wf_laqa (float): force factor.
        ws_laqa (float): stress factor.
    """
    step_data = step_data_node.step_data
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


def laqa_next_selection(laqa_score, nselect_laqa):
    id_queueing = []
    for k, v in sorted(laqa_score.items(), key=lambda x: -x[1]):
        print(k, v)
        # if v == -float('int'):
        #    break
        id_queueing.append(k)
        if len(id_queueing) >= nselect_laqa:
            break
    return id_queueing


class generatte_laqa_data_WorkChain(WorkChain):

    @classmethod
    def define(cls, spec):
        super().define(spec)
        spec.input('cryspy_in', valid_type=RinData, help='parsed cryspy_in content.')
        spec.input('step_data', valid_type=StepData, help='step data.')
        spec.outline(cls.generate_laqa_data)
        spec.output('laqa_data', valid_type=LAQAData, help='LAQA data.')
        spec.output('laqa_summary', valid_type=PandasFrameData, help='laqa summary as dataframe.')

    def generate_laqa_data(self):

        rin_node = self.inputs.cryspy_in
        step_data_node = self.inputs.step_data

        rin = rin_node.rin
        laqa_df = _calculate_laqa_scores(step_data_node, rin.wf_laqa, rin.ws_laqa)
        df_node = PandasFrameData(df=laqa_df)

        laqa_score = _extract_laqa_score(laqa_df)

        values = (None, None, None, None, None, laqa_score)
        laqa_data_node = LAQAData(values)
        laqa_data_node.store()
        df_node = PandasFrameData(df=laqa_df)
        df_node.store()

        self.out('laqa_data', laqa_data_node)
        self.out('laqa_summary', df_node)
