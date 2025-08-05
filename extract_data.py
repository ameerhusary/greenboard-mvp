import pandas as pd

class FECDataExtractor:
    def __init__(self):
        self.file_paths = ['./data/itcont_2018_20020411_20170529.txt', 
                           './data/itcont_2018_20170530_20170824.txt']
        self.data = self.load_data()

    def load_data(self) -> pd.DataFrame:
        # 3977069 rows x 21 columns
        columns = [
            'CMTE_ID', 'AMNDT_IND', 'RPT_TP', 'TRANSACTION_PGI', 'IMAGE_NUM', 
            'TRANSACTION_TP', 'ENTITY_TP', 'NAME', 'CITY', 'STATE', 'ZIP_CODE',
            'EMPLOYER', 'OCCUPATION', 'TRANSACTION_DT', 'TRANSACTION_AMT', 
            'OTHER_ID', 'TRAN_ID', 'FILE_NUM', 'MEMO_CD', 'MEMO_TEXT', 'SUB_ID'
        ]
        dataframes = []
        for file_path in self.file_paths:
            df = pd.read_csv(file_path, delimiter='|', names=columns, dtype=str)
            dataframes.append(df)
        return pd.concat(dataframes, ignore_index=True)

    # def search(self, name, city=None):
    #     q = self.data[self.data['NAME'].str.contains(name, case=False, na=False)]
    #     if city:
    #         q = q[q['CITY'].str.contains(city, case=False, na=False)]
    #     return q

# results = search("PAUL, PAUL", city="CINCINNATI")
# print(results[['NAME', 'CITY', 'STATE', 'TRANSACTION_DT', 'TRANSACTION_AMT']].head())