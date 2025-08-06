import os
import pandas as pd
import sqlite3

class FECDataExtractor:
    def __init__(self):
        self.file_paths = ['./data/itcont_2018_20020411_20170529.txt', 
                           './data/itcont_2018_20170530_20170824.txt']
        self.data = None

    def load_data(self) -> pd.DataFrame:
        if self.data is None:
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
            self.data = pd.concat(dataframes, ignore_index=True)
        return self.data
    
    def ensure_sqlite_exists(self, db_path="contributions.db"):
        """Create SQLite database if it doesn't exist"""
        if not os.path.exists(db_path):
            print(f"Creating SQLite database at {db_path}...")
            df = self.load_data()
            
            # Add processed name columns
            name_split = df['NAME'].fillna('').str.split(',', n=1, expand=True)
            df['LAST_NAME_RAW'] = name_split[0].str.strip().str.lower()
            df['FIRST_NAME_RAW'] = name_split[1].str.strip().str.lower()
            
            # Add normalized columns for consistent person grouping
            df['LAST_NAME_NORMALIZED'] = df['LAST_NAME_RAW']
            # Normalize first names: remove titles, suffixes, and extra spaces
            df['FIRST_NAME_NORMALIZED'] = (
                df['FIRST_NAME_RAW']
                .str.replace(r'\b(mr|mrs|ms|dr|jr|sr|ii|iii|iv|v)\b\.?', '', regex=True, case=False)
                .str.replace(r'\s+', ' ', regex=True)  # Compress whitespace
                .str.strip()
                .str.split().str[0].str.lower()        # Take only the first name
            )
            
            # Create person group ID for consistent coloring
            df['PERSON_GROUP_ID'] = (df['FIRST_NAME_NORMALIZED'] + '_' + 
                                   df['LAST_NAME_NORMALIZED'] + '_' + 
                                   df['CITY'].fillna('').str.lower())

            # Create SQLite database
            conn = sqlite3.connect(db_path)
            df.to_sql('contributions', conn, if_exists='replace', index=False)
            
            # Create indexes for faster searches
            cursor = conn.cursor()
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_last_name ON contributions(LAST_NAME_RAW)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_first_name ON contributions(FIRST_NAME_RAW)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_names ON contributions(LAST_NAME_RAW, FIRST_NAME_RAW)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_first_normalized ON contributions(FIRST_NAME_NORMALIZED)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_last_normalized ON contributions(LAST_NAME_NORMALIZED)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_city ON contributions(CITY)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_normalized_names ON contributions(FIRST_NAME_NORMALIZED, LAST_NAME_NORMALIZED)')
            cursor.execute('CREATE INDEX IF NOT EXISTS idx_person_group ON contributions(PERSON_GROUP_ID)')
            conn.commit()
            conn.close()
            print(f"SQLite database created successfully at {db_path}")
        else: 
            print(f"SQLite database already exists at {db_path}")

# Create database on import if needed
# extractor = FECDataExtractor()
# extractor.ensure_sqlite_exists()