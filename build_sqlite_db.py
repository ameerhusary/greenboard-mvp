from extract_data import FECDataExtractor

if __name__ == "__main__":
    extractor = FECDataExtractor()
    extractor.ensure_sqlite_exists(db_path="contributions.db")
