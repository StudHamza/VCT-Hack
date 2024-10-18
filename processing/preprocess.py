from parsers import get_game_mappings,process_game_file,get_fixture_data
import os
import polars as pl







def get_user_input(prompt):
    return input(prompt)

def main():
    local_dir_prefix = get_user_input("Enter the local directory prefix (Defualt data/raw): ")
    if not local_dir_prefix:
        local_dir_prefix = "./data/raw"
    
    
    league_options = ["game-changers", "vct-international", "vct-challengers"]

    print(f"Please choose a league from the following options: {league_options}")

    league = get_user_input("Enter the league: ")

    while league not in league_options:
        print(f"Invalid option. Please choose from: {league_options}")
        league = get_user_input("Enter the league: ")
    
    output_dir = get_user_input("Enter the output directory (where you want generated files to be stored): ")
    if not output_dir:
        output_dir = '.'
    
    year = get_user_input("Enter the year for the game data (e.g., 2024): ")
    game_dir = f"{local_dir_prefix}/{league}/games/{year}"
    game_mapping_dir = f"{local_dir_prefix}/{league}/esports-data/mapping_data.json"

    # Validate directories and files
    if not os.path.exists(local_dir_prefix):
        print(f"Error: The directory '{local_dir_prefix}' does not exist.")
        return

    if not os.path.exists(game_dir):
        print(f"Error: The directory '{game_dir}' does not exist.")
        return

    if not os.path.exists(game_mapping_dir):
        print(f"Error: The file '{game_mapping_dir}' does not exist.")
        return
    
    print("\n--- Set Variables ---")
    print(f"LOCAL_DIR_PREFIX = '{local_dir_prefix}'")
    print(f"LEAGUE = '{league}'")
    print(f"OUTPUT_DIR = '{output_dir}'")
    print(f"GAME_DIR = '{game_dir}'")
    print(f"GAME_MAPPING_DIR = '{game_mapping_dir}'")


    #################### PROCESS DATA #############################
    #Fixture_data
    # fixture_data = get_fixture_data(f"{local_dir_prefix}/{league}")
    # fixture_data.write_csv(f"{output_dir}\{league}_{year}_fixture.csv")

    # GAME DATA
    game_mapping = get_game_mappings(game_mapping_dir)

    game_summaries = []

    for game_map in game_mapping:
        platform_game_id = game_map.platform_game_id.replace(":", "_")
        game_file = f"{game_dir}/{platform_game_id}.json"

        if not os.path.exists(game_file):
            print(f" No such file or directory: {game_file}")
        else:
            try:
                game_stats= process_game_file(game_dir,game_map)

                if not game_stats.is_empty():
                    game_summaries.append(game_stats)
            except Exception as e:
                print(f"Error in game data: {e}")

            #Debug
            # stop = get_user_input("Do you want to stop? ")
            # if stop=='y':
            #     break

    game_data = pl.concat(game_summaries)
    csv_name = f"{output_dir}\{league}_{year}_gamedata.csv"
    game_data.write_csv(csv_name.replace('-','_'))




if __name__ == "__main__":
    main()



