from typing import Union
from extract_data import FECDataExtractor
import pandas as pd
import sqlite3
import os


class ContributionSearchEngine:
    def __init__(self, use_sqlite=True, db_path="contributions.db"):
        self.use_sqlite = use_sqlite
        self.db_path = db_path
        self.extractor = FECDataExtractor()
        
        if self.use_sqlite and os.path.exists(self.db_path):
            self.conn = sqlite3.connect(self.db_path)
        else:
            self.df = self.extractor.load_data()
            if self.use_sqlite:
                self._create_sqlite_db()
            else:
                # Pre-split NAME into FIRST/LAST for faster lookup
                name_split = self.df['NAME'].fillna('').str.split(',', n=1, expand=True)
                self.df['LAST_NAME_RAW'] = name_split[0].str.strip().str.lower()
                self.df['FIRST_NAME_RAW'] = name_split[1].str.strip().str.lower()

    def _create_sqlite_db(self):
        self.conn = sqlite3.connect(self.db_path)
        
        # Add processed name columns
        name_split = self.df['NAME'].fillna('').str.split(',', n=1, expand=True)
        self.df['LAST_NAME_RAW'] = name_split[0].str.strip().str.lower()
        self.df['FIRST_NAME_RAW'] = name_split[1].str.strip().str.lower()
        
        # Create table with indexes
        self.df.to_sql('contributions', self.conn, if_exists='replace', index=False)
        
        # Create indexes for faster searches
        cursor = self.conn.cursor()
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_last_name ON contributions(LAST_NAME_RAW)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_first_name ON contributions(FIRST_NAME_RAW)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_city ON contributions(CITY)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_names ON contributions(LAST_NAME_RAW, FIRST_NAME_RAW)')
        self.conn.commit()

    def search(self, first_name: str, last_name: str, city: str = None, limit=10) -> pd.DataFrame:
        if not first_name.strip() or not last_name.strip():
            return pd.DataFrame()
        
        if self.use_sqlite:
            return self._sqlite_search(first_name, last_name, city, limit)
        else:
            df = self.df
            if city:
                city_clean = city.strip().upper()
                df = df[df['CITY'].fillna('').str.upper() == city_clean]
            return self._multi_strategy_search(df, first_name, last_name, limit)

    def _sqlite_search(self, first_name: str, last_name: str, city: str = None, limit=10) -> pd.DataFrame:
        first_clean = first_name.strip().lower()
        last_clean = last_name.strip().lower()
        
        city_filter = ""
        params = [first_clean, last_clean]
        if city:
            city_filter = "AND UPPER(CITY) = UPPER(?)"
            params.append(city.strip())
        
        # Strategy 1: exact match
        query = f"""
        SELECT * FROM contributions 
        WHERE FIRST_NAME_RAW = ? AND LAST_NAME_RAW = ? {city_filter}
        LIMIT ?
        """
        params.append(limit)
        result = pd.read_sql_query(query, self.conn, params=params)
        if not result.empty:
            return result
        
        # Strategy 2: initial match
        params = [last_clean]
        if city:
            params.append(city.strip())
        if len(first_clean) <= 2:
            initial_char = first_clean.replace('.', '')
            query = f"""
            SELECT * FROM contributions 
            WHERE LAST_NAME_RAW = ? AND FIRST_NAME_RAW LIKE ? {city_filter}
            LIMIT ?
            """
            params.insert(1, f"{initial_char}%")
            params.append(limit)
            result = pd.read_sql_query(query, self.conn, params=params)
            if not result.empty:
                return result
        
        # Strategy 3: partial match
        params = [f"%{first_clean}%", f"%{last_clean}%"]
        if city:
            params.append(city.strip())
        query = f"""
        SELECT * FROM contributions 
        WHERE FIRST_NAME_RAW LIKE ? AND LAST_NAME_RAW LIKE ? {city_filter}
        LIMIT ?
        """
        params.append(limit)
        result = pd.read_sql_query(query, self.conn, params=params)
        if not result.empty:
            return result
        
        # Strategy 4: fuzzy fallback
        params = [last_clean, f"%{first_clean}%"]
        if city:
            params.append(city.strip())
        query = f"""
        SELECT * FROM contributions 
        WHERE LAST_NAME_RAW = ? AND FIRST_NAME_RAW LIKE ? {city_filter}
        LIMIT ?
        """
        params.append(limit)
        return pd.read_sql_query(query, self.conn, params=params)

    def _multi_strategy_search(self, df, first_name, last_name, limit):
        first_clean = first_name.strip().lower()
        last_clean = last_name.strip().lower()
        
        # Strategy 1: exact match on raw-split columns
        exact = df[
            (df['FIRST_NAME_RAW'] == first_clean) &
            (df['LAST_NAME_RAW'] == last_clean)
        ]
        if not exact.empty:
            return exact.head(limit)
        
        # Strategy 2: initial match (e.g. "J." with last name slice)
        if len(first_clean) <= 2:  # treat 1–2 chars as initial
            initial_char = first_clean.replace('.', '')
            starts = df[
                (df['LAST_NAME_RAW'] == last_clean) &
                (df['FIRST_NAME_RAW'].str.startswith(initial_char, na=False))
            ]
            if not starts.empty:
                return starts.head(limit)
        
        # Strategy 3: partial match for middle names/suffixes
        contains = df[
            (df['FIRST_NAME_RAW'].str.contains(first_clean, na=False)) &
            (df['LAST_NAME_RAW'].str.contains(last_clean, na=False))
        ]
        if not contains.empty:
            return contains.head(limit)
        
        # Strategy 4: fuzzy fallback (but only among same LAST_NAME_RAW to shrink space)
        narrowed = df[df['LAST_NAME_RAW'] == last_clean]
        fuzzy_matches = narrowed[narrowed['FIRST_NAME_RAW'].str.contains(first_clean, na=False)]
        return fuzzy_matches.head(limit)

    def bulk_search(self, names_input: str, city=None, limit_per_name=10):
        name_pairs = self._parse_comma_separated_names(names_input)
        all_results = []
        search_summary = []
        
        for first_name, last_name in name_pairs:
            results = self.search(first_name, last_name, city, limit_per_name)
            search_summary.append({
                'search_term': f"{first_name} {last_name}",
                'matches_found': len(results),
                'total_amount': float(results['TRANSACTION_AMT'].astype(float).sum()) if len(results) > 0 else 0.0
            })
            if len(results) > 0:
                r = results.copy()
                r['search_term'] = f"{first_name} {last_name}"
                all_results.append(r)
        
        combined_results = pd.concat(all_results, ignore_index=True) if all_results else pd.DataFrame()
        return combined_results, search_summary

    def _parse_comma_separated_names(self, names_input: str) -> list[tuple[str, str]]:
        full_names = [name.strip() for name in names_input.split(',') if name.strip()]
        name_pairs = []
        for name in full_names:
            parts = name.split()
            if len(parts) >= 2:
                first_name = parts[0]
                last_name = ''.join(parts[1:])
                name_pairs.append((first_name, last_name))
        return name_pairs
        
    def export_to_csv(self, results, filename="contribution_results.csv"):
        if len(results) == 0:
            print("No results to export")
            return False
        
        export_columns = [
            'search_name',
            'NAME',
            'CITY',
            'STATE',
            'TRANSACTION_AMT',
            'TRANSACTION_DT'
        ]
        available = [c for c in export_columns if c in results.columns]
        results[available].to_csv(filename, index=False)
        print(f"Exported {len(results)} results to {filename}")
        return True

    def __del__(self):
        if hasattr(self, 'conn') and self.use_sqlite:
            self.conn.close()


def main():
    search_engine = ContributionSearchEngine()
    #______________Uncomment to test individual search_____________________________
    # results, summary = search_engine.bulk_search("paul paul, victor tate")
    # print(results[['NAME', 'CITY', 'STATE', 'TRANSACTION_DT', 'TRANSACTION_AMT']].head())
    # print(f"Search Summary: {summary}")
    # Export results to CSV
    # search_engine.export_to_csv(results, "contribution_results.csv")
    #______________Uncomment to test individual search_____________________________
    # results = search_engine.search("victor", "tate")
    # if isinstance(results, str):
    #     print(results)
    # else: 
        # search_engine.export_to_csv(results, "contribution_results_2.csv")
        # print(results[['NAME', 'CITY', 'STATE', 'TRANSACTION_DT', 'TRANSACTION_AMT']])

if __name__ == "__main__":
    main()