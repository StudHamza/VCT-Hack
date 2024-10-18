import gzip
import json
import os
import shutil
import time
from io import BytesIO

import requests

S3_BUCKET_URL = "https://vcthackathon-data.s3.us-west-2.amazonaws.com"
LOCAL_DIR_PREFIX = "data/raw"

# (game-changers, vct-international, vct-challengers)
LEAGUE = "game-changers"

# (2022, 2023, 2024)
YEAR = 2024


def download_gzip_and_write_to_file(file_name):
    actual_file = f"{LOCAL_DIR_PREFIX}/{file_name.replace(":", "_")}"
    if os.path.isfile(f"{actual_file}.json"):
        return False

    remote_file = f"{S3_BUCKET_URL}/{file_name}.json.gz"
    response = requests.get(remote_file, stream=True)

    if response.status_code == 200:
        try:
            # Try decoding as gzip first
            gzip_bytes = BytesIO(response.content)
            with gzip.GzipFile(fileobj=gzip_bytes, mode="rb") as gzipped_file:
                with open(f"{actual_file}.json", 'wb') as output_file:
                    shutil.copyfileobj(gzipped_file, output_file)
            print(f"{actual_file}.json written (gzip)")
        except (gzip.BadGzipFile,):
            # If decoding as gzip fails, try as raw bytes
            with open(f"{actual_file}.json", 'wb') as output_file:
                output_file.write(response.content)
            print(f"{actual_file}.json written (raw)")
        return True


def download_esports_files():
    directory = f"{LEAGUE}/esports-data"

    local_directory = f"{LOCAL_DIR_PREFIX}/{directory}"
    if not os.path.exists(local_directory):
        os.makedirs(local_directory)

    esports_data_files = ["leagues", "tournaments", "players", "teams", "mapping_data"]
    for file_name in esports_data_files:
        download_gzip_and_write_to_file(f"{directory}/{file_name}", "json")


def download_fandom_data():
    directory = "fandom"

    local_directory = f"{LOCAL_DIR_PREFIX}/{directory}"
    if not os.path.exists(local_directory):
        os.makedirs(local_directory)

    file_names = ["valorant_esports_pages", "valorant_pages"]
    for file_name in file_names:
        download_gzip_and_write_to_file(f"{directory}/{file_name}", "xml")


def download_games():
    start_time = time.time()

    local_mapping_file = f"{LOCAL_DIR_PREFIX}/{LEAGUE}/esports-data/mapping_data.json"
    with open(local_mapping_file, "r") as json_file:
        mappings_data = json.load(json_file)

    local_directory = f"{LOCAL_DIR_PREFIX}/{LEAGUE}/games/{YEAR}"
    if not os.path.exists(local_directory):
        os.makedirs(local_directory)

    game_counter = 0

    for esports_game in mappings_data:
        s3_game_file = f"{LEAGUE}/games/{YEAR}/{esports_game['platformGameId']}"

        response = download_gzip_and_write_to_file(s3_game_file)

        if response:
            game_counter += 1
            if game_counter % 10 == 0:
                print(
                    f"----- Processed {game_counter} games, current run time: {round((time.time() - start_time)/60, 2)} minutes"
                )
        else:
            print(f"Response: {response}")


if __name__ == "__main__":
    # download_fandom_data()
    # download_esports_files()
    download_games()