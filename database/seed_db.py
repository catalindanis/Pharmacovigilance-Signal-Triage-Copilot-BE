import json
import argparse
import requests
import zipfile
import io
from app.transform import extract_cases_from_record, deduplicate_cases
from database.db_manager import get_connection, init_db, bulk_insert_cases

FDA_DOWNLOADS_URL = "https://api.fda.gov/download.json"

def get_download_links():
    print("Loading openFDA links...")
    response = requests.get(FDA_DOWNLOADS_URL)
    response.raise_for_status()
    data = response.json()

    try:
        partitions = data['results']['drug']['event']['partitions']
        links = [partition['file'] for partition in partitions]
        print(f"Found {len(links)} archives for download.")
        return links
    except KeyError:
        print("JSON structure changed or invalid endpoint.")
        return []


def main():
    parser = argparse.ArgumentParser(description="Download openFDA archives and populate database.")
    parser.add_argument("--db", default="faers_local.db", help="Database name (default: faers_local.db)")
    parser.add_argument("--limit", type=int, default=2, help="Max numbers of archives to download (default: 2)")
    args = parser.parse_args()

    links = get_download_links()
    if not links:
        return

    if args.limit and args.limit > 0:
        links = links[:args.limit]
        print(f"Only the first {args.limit} archives will be downloaded.")

    conn = get_connection(args.db)
    init_db(conn)

    for idx, url in enumerate(links, start=1):
        print(f"\n[{idx}/{len(links)}] Now processing: {url}")

        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()

            with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                json_filename = z.namelist()[0]
                with z.open(json_filename) as f:
                    data = json.load(f)

            records = data.get("results", [])
            print(f" -> Extracted {len(records)} reports")

            all_cases = []
            for record in records:
                all_cases.extend(extract_cases_from_record(record))

            all_cases = deduplicate_cases(all_cases)
            print(f" -> Ready for insert: {len(all_cases)} unique cases.")

            bulk_insert_cases(conn, all_cases)
            print(" Archive saved successfully.")

        except Exception as e:
            print(f" Processing error for {url}: {e}")

    conn.close()
    print("\nFinished loading the archives into the database.")


if __name__ == "__main__":
    main()