import pandas as pd
from aiida.orm import Dict


class DataframeData(Dict):

    INDEX = "@INDEX"

    def __init__(self, df: pd.DataFrame = None, **kwargs):
        super().__init__(**kwargs)
        if df is not None:
            self._internal_validate(df)
            self.set_df(df)

    def _internal_validate(self, df):
        if not isinstance(df, pd.DataFrame):
            raise TypeError('df must be pd.DataFrame')

    def set_df(self, df: pd.DataFrame) -> None:
        if df is not None:
            self._internal_validate(df)
        dic = {}
        for key in df.columns:
            dic[key] = df[key].values.tolist()
        dic[self.INDEX] = df.index.tolist()
        self.set_dict(dic)
        return Dict(dict=dic)

    def get_df(self) -> pd.DataFrame:
        d = self.get_dict()
        index = None
        if self.INDEX in d:
            index = d.pop(self.INDEX)
        df = pd.DataFrame(d, index=index)
        return df

    @property
    def df(self) -> pd.DataFrame:
        return self.get_df()

    @df.setter
    def df(self, df: pd.DataFrame) -> None:
        self.set_df(df)
