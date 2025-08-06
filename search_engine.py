from typing import Union, List, Tuple, Dict, Any
import pandas as pd
import sqlite3
import os
from contextlib import contextmanager
from dataclasses import dataclass
import re


@dataclass
class SearchResult:
    """Structured search result with metadata"""
    data: pd.DataFrame
    search_term: str
    matches_found: int
    total_amount: float
    person_group_id: str = None


class ContributionSearchEngine:
    def __init__(self, use_sqlite=True, db_path="contributions.db"):
        self.use_sqlite = use_sqlite
        self.db_path = db_path
        
        if self.use_sqlite:
            assert os.path.exists(db_path), "Run python build_sqlite_db.py first."
            # Pre-compile regex patterns for name normalization
            self._title_pattern = re.compile(r'\b(mr|mrs|ms|dr|jr|sr|ii|iii|iv|v)\b\.?', re.IGNORECASE)
            self._initial_pattern = re.compile(r'\b[a-z]\.?\b', re.IGNORECASE)
            self._space_pattern = re.compile(r'\s+')
        else:
            self.df = self.extractor.load_data()
            # Pre-split NAME into FIRST/LAST for faster lookup
            name_split = self.df['NAME'].fillna('').str.split(',', n=1, expand=True)
            self.df['LAST_NAME_RAW'] = name_split[0].str.strip().str.lower()
            self.df['FIRST_NAME_RAW'] = name_split[1].str.strip().str.lower()
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections with proper cleanup"""
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
        finally:
            conn.close()

    def _normalize_name_parts(self, first_name: str, last_name: str, city: str = None) -> Tuple[str, str, str]:
        """
        Normalize name parts using the same logic as extract_data.py
        Returns (normalized_first, normalized_last, person_group_id)
        """
        first_clean = first_name.strip().lower()
        last_clean = last_name.strip().lower()
        
        # Normalize first name: remove titles, suffixes, and extra spaces
        first_normalized = self._title_pattern.sub('', first_clean)
        first_normalized = self._initial_pattern.sub('', first_normalized)
        first_normalized = self._space_pattern.sub(' ', first_normalized).strip()
        first_normalized = first_normalized.split()[0] if first_normalized else ''
        
        # Create person group ID for consistent identification (without state since you don't use it)
        city_clean = city.lower().strip() if city else ''
        person_group_id = f"{first_normalized}_{last_clean}_{city_clean}" 
        
        return first_normalized, last_clean, person_group_id

    def search(self, first_name: str, last_name: str, city: str = None, limit=10) -> SearchResult:
        """Single search - called by bulk_search for individual names"""
        if not first_name.strip() or not last_name.strip():
            return SearchResult(
                data=pd.DataFrame(),
                search_term=f"{first_name} {last_name}",
                matches_found=0,
                total_amount=0.0
            )
        
        if self.use_sqlite:
            return self._sqlite_search(first_name, last_name, city, limit)
        else:
            df = self.df
            if city:
                city_clean = city.strip().upper()
                df = df[df['CITY'].fillna('').str.upper() == city_clean]
            result_df = self._multi_strategy_search(df, first_name, last_name, limit)

            return SearchResult(
                data=result_df,
                search_term=f"{first_name} {last_name}",
                matches_found=len(result_df),
                total_amount=float(result_df['TRANSACTION_AMT'].astype(float).sum()) if len(result_df) > 0 else 0.0
            )

    def _sqlite_search(self, first_name: str, last_name: str, city: str = None, limit=10) -> SearchResult:
        """SQLite search with optimized strategy hierarchy"""
        first_clean = first_name.strip().lower()
        last_clean = last_name.strip().lower()
        search_term = f"{first_name} {last_name}"

        # Generate normalized names and person group ID
        first_normalized, last_normalized, person_group_id = self._normalize_name_parts(
            first_name, last_name, city
        )

        with self.get_connection() as conn:
            # Strategy 1: Person Group ID match (fastest - single index lookup)
            query = """
            SELECT * FROM contributions 
            WHERE PERSON_GROUP_ID = ?
            LIMIT ?
            """
            result = pd.read_sql_query(query, conn, params=[person_group_id, limit])
            if not result.empty:
                return SearchResult(
                    data=result,
                    search_term=search_term,
                    matches_found=len(result),
                    total_amount=float(result['TRANSACTION_AMT'].astype(float).sum()),
                    person_group_id=person_group_id
                )
            
            # Strategy 2: Exact match on normalized names
            city_filter = ""
            params = [first_normalized, last_normalized]
            if city:
                city_filter = "AND UPPER(CITY) = UPPER(?)"
                params.append(city.strip())
            
            query = f"""
            SELECT * FROM contributions 
            WHERE FIRST_NAME_NORMALIZED = ? AND LAST_NAME_NORMALIZED = ? {city_filter}
            LIMIT ?
            """
            params.append(limit)
            result = pd.read_sql_query(query, conn, params=params)
            if not result.empty:
                return SearchResult(
                    data=result,
                    search_term=search_term,
                    matches_found=len(result),
                    total_amount=float(result['TRANSACTION_AMT'].astype(float).sum()),
                    person_group_id=person_group_id
                )
            
            # Strategy 3: Fallback to raw name exact match
            params = [first_clean, last_clean]
            if city:
                params.append(city.strip())
            
            query = f"""
            SELECT * FROM contributions 
            WHERE FIRST_NAME_RAW = ? AND LAST_NAME_RAW = ? {city_filter}
            LIMIT ?
            """
            params.append(limit)
            result = pd.read_sql_query(query, conn, params=params)
            if not result.empty:
                return SearchResult(
                    data=result,
                    search_term=search_term,
                    matches_found=len(result),
                    total_amount=float(result['TRANSACTION_AMT'].astype(float).sum()),
                    person_group_id=person_group_id
                )
            
            # Strategy 4: Initial match (for single letter + last name)
            if len(first_clean) <= 2:
                initial_char = first_clean.replace('.', '')
                params = [last_clean, f"{initial_char}%"]
                if city:
                    params.append(city.strip())
                
                query = f"""
                SELECT * FROM contributions 
                WHERE LAST_NAME_RAW = ? AND FIRST_NAME_RAW LIKE ? {city_filter}
                LIMIT ?
                """
                params.append(limit)
                result = pd.read_sql_query(query, conn, params=params)
                if not result.empty:
                    return SearchResult(
                        data=result,
                        search_term=search_term,
                        matches_found=len(result),
                        total_amount=float(result['TRANSACTION_AMT'].astype(float).sum()),
                        person_group_id=person_group_id
                    )
            
            # Strategy 5: Partial match fallback
            params = [f"%{first_clean}%", f"%{last_clean}%"]
            if city:
                params.append(city.strip())
            
            query = f"""
            SELECT * FROM contributions 
            WHERE FIRST_NAME_RAW LIKE ? AND LAST_NAME_RAW LIKE ? {city_filter}
            LIMIT ?
            """
            params.append(limit)
            result = pd.read_sql_query(query, conn, params=params)
            
            return SearchResult(
                data=result,
                search_term=search_term,
                matches_found=len(result),
                total_amount=float(result['TRANSACTION_AMT'].astype(float).sum()) if len(result) > 0 else 0.0,
                person_group_id=person_group_id
            )

    def _multi_strategy_search(self, df, first_name, last_name, limit):
        """Pandas-based search for non-SQLite mode"""
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

    def bulk_search(self, names_input: str, city=None, limit_per_name=10) -> Tuple[pd.DataFrame, List[Dict[str, Any]]]:
        """
        Main endpoint for both single and multiple name searches
        Optimized with connection reuse for SQLite
        """
        # Handle single name case
        if ',' not in names_input:
            # Single name search
            parts = names_input.strip().split()
            if len(parts) >= 2:
                first_name = parts[0]
                last_name = ' '.join(parts[1:])
                result = self.search(first_name, last_name, city, limit_per_name)
                
                summary = [{
                    'search_term': result.search_term,
                    'matches_found': result.matches_found,
                    'total_amount': result.total_amount,
                    'person_group_id': result.person_group_id
                }]
                
                if result.matches_found > 0:
                    result_df = result.data.copy()
                    result_df['search_term'] = result.search_term
                    if result.person_group_id:
                        result_df['person_group_id'] = result.person_group_id
                    return result_df, summary
                else:
                    return pd.DataFrame(), summary
            else:
                return pd.DataFrame(), []
        
        # Multiple names search
        name_pairs = self._parse_comma_separated_names(names_input)
        all_results = []
        search_summary = []
        
        if self.use_sqlite:
            # Use single connection for all searches in bulk
            with self.get_connection() as conn:
                for first_name, last_name in name_pairs:
                    result = self._bulk_sqlite_search_single(conn, first_name, last_name, city, limit_per_name)
                    
                    search_summary.append({
                        'search_term': result.search_term,
                        'matches_found': result.matches_found,
                        'total_amount': result.total_amount,
                        'person_group_id': result.person_group_id
                    })
                    
                    if result.matches_found > 0:
                        result_df = result.data.copy()
                        result_df['search_term'] = result.search_term
                        if result.person_group_id:
                            result_df['person_group_id'] = result.person_group_id
                        all_results.append(result_df)
        else:
            # Pandas-based bulk search
            for first_name, last_name in name_pairs:
                result = self.search(first_name, last_name, city, limit_per_name)
                search_summary.append({
                    'search_term': result.search_term,
                    'matches_found': result.matches_found,
                    'total_amount': result.total_amount
                })
                if result.matches_found > 0:
                    result_df = result.data.copy()
                    result_df['search_term'] = result.search_term
                    all_results.append(result_df)
        
        combined_results = pd.concat(all_results, ignore_index=True) if all_results else pd.DataFrame()
        return combined_results, search_summary
    
    def _bulk_sqlite_search_single(self, conn: sqlite3.Connection, first_name: str, last_name: str, 
                                 city: str = None, limit=10) -> SearchResult:
        """Optimized single search operation within bulk search using existing connection"""
        if not first_name.strip() or not last_name.strip():
            return SearchResult(
                data=pd.DataFrame(),
                search_term=f"{first_name} {last_name}",
                matches_found=0,
                total_amount=0.0
            )
        
        search_term = f"{first_name} {last_name}"
        
        # Generate normalized names and person group ID
        first_normalized, last_normalized, person_group_id = self._normalize_name_parts(
            first_name, last_name, city
        )
        
        # Strategy 1: Person Group ID first (fastest)
        query = """
        SELECT * FROM contributions 
        WHERE PERSON_GROUP_ID = ?
        LIMIT ?
        """
        result = pd.read_sql_query(query, conn, params=[person_group_id, limit])
        if not result.empty:
            return SearchResult(
                data=result,
                search_term=search_term,
                matches_found=len(result),
                total_amount=float(result['TRANSACTION_AMT'].astype(float).sum()),
                person_group_id=person_group_id
            )
        
        # Strategy 2: Fallback to normalized name search
        city_filter = ""
        params = [first_normalized, last_normalized]
        if city:
            city_filter = " AND UPPER(CITY) = UPPER(?)"
            params.append(city.strip())
        
        query = f"""
        SELECT * FROM contributions 
        WHERE FIRST_NAME_NORMALIZED = ? AND LAST_NAME_NORMALIZED = ? {city_filter}
        LIMIT ?
        """
        params.append(limit)
        result = pd.read_sql_query(query, conn, params=params)
        
        return SearchResult(
            data=result,
            search_term=search_term,
            matches_found=len(result),
            total_amount=float(result['TRANSACTION_AMT'].astype(float).sum()) if len(result) > 0 else 0.0,
            person_group_id=person_group_id
        )

    def _parse_comma_separated_names(self, names_input: str) -> List[Tuple[str, str]]:
        """Parse comma-separated names into (first, last) tuples"""
        full_names = [name.strip() for name in names_input.split(',') if name.strip()]
        name_pairs = []
        for name in full_names:
            parts = name.split()
            if len(parts) >= 2:
                first_name = parts[0]
                last_name = ' '.join(parts[1:])  # Handle multi-word last names properly
                name_pairs.append((first_name, last_name))
        return name_pairs
        
    def export_to_csv(self, results: Union[pd.DataFrame, SearchResult], filename="contribution_results.csv") -> bool:
        """Export results to CSV with enhanced column selection"""
        if isinstance(results, SearchResult):
            df = results.data
        else:
            df = results
            
        if len(df) == 0:
            print("No results to export")
            return False
        
        export_columns = [
            'search_term',
            'person_group_id',
            'NAME',
            'CITY',
            'STATE',
            'TRANSACTION_AMT',
            'TRANSACTION_DT',
            'COMMITTEE_NAME'
        ]
        available = [c for c in export_columns if c in df.columns]
        df[available].to_csv(filename, index=False)
        print(f"Exported {len(df)} results to {filename}")
        return True


# def main():
#     search_engine = ContributionSearchEngine()
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

# if __name__ == "__main__":
#     main()