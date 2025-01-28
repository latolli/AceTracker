"""
Library of utility functions for AceTracker.py
"""
import json
import os
import csv
from re import findall

def reset_counters(short_stats):
    """
    Function for resetting certain counters
    """
    for seat in short_stats:
        short_stats[seat]["raises"] = 0
    return short_stats

def handle_txt_file(source_file, hero_name):
    """
    Function for parsing txt files containing all hands played in one table
    """
    temp_stats = {} # For keeping track of player positions, blinds, money betted etc on a single hand
    long_stats = {} # For keeping track of long term stats like VPIP and PFR
    state = "none"
    positions_assigned = 0
    seat_id = 0
    current_seat = None
    data_from_hand = {}
    total_hands_data = {}
    bank_roll_data = []
    # DEBUG SHIT
    super_debug = 0
    with open(source_file, 'r') as source:
        hand_db_file = source_file.split("\\")[-1].split("-")[0].replace(" ", "_") + "db.json"
        for line in source:
            # Check hand state
            if "PokerStars Hand #" in line:
                # Skip tournaments
                if "Tournament #" in line:
                    break
                state = "start-hand"
                # Reset variables
                temp_stats = {}
                positions_assigned = 0
                seat_id = 0
                hand_id = str(line.split(" ")[2]).strip("#").strip(":")
                if "Psadfasdfasdfasdfasdfdas" in line:
                    print("SUPER DEBUG ACTIVATED ######################################")
                    super_debug = 1
                else:
                    super_debug = 0
                data_from_hand = {"summary": {}, "pre-flop": []}
            elif "*** HOLE CARDS ***" in line:
                state = "pre-flop"
            elif "*** FLOP ***" in line:
                state = "flop"
                temp_stats = reset_counters(temp_stats)
                cards = line.split("[")[1].split("]")[0]
                data_from_hand["flop"] = [f"board: {cards}"]
            elif "*** TURN ***" in line:
                state = "turn"
                temp_stats = reset_counters(temp_stats)
                cards = line.split("] [")[1].split("]")[0]
                data_from_hand["turn"] = [f"board: {cards}"]
            elif "*** RIVER ***" in line:
                state = "river"
                temp_stats = reset_counters(temp_stats)
                cards = line.split("] [")[1].split("]")[0]
                data_from_hand["river"] = [f"board: {cards}"]
            elif "*** SHOW DOWN ***" in line:
                state = "show-down"
            elif "*** SUMMARY ***" in line:
                state = "end-hand"


            if super_debug: print("State:", state, line)

            if state == "start-hand" and positions_assigned == 0:
                # Check active players
                if line.startswith("Seat") and "is sitting out" not in line:
                    usr = line.split(":")[1]
                    usr = usr.split("(")[0].strip()
                    if super_debug: print("User found:", usr)
                    temp_stats[f"seat{seat_id}"] = {
                        "usr": usr,
                        "pos": None,
                        "raises": 0,
                        "chips_at_start": 0.0,
                    }
                    # Create data to hand DB for player
                    data_from_hand["summary"][usr] = {"position": "??", "cards": "?? ??", "profit": 999}
                    # Check if player exists in long term stats
                    if usr in long_stats:
                        long_stats[usr]["played_hands"]["value"] += 1
                        temp_stats[f"seat{seat_id}"]["chips_at_start"] = long_stats[usr]["profit"]["value"]
                        if super_debug: print("Long stats exist")
                    else:
                        # Create new player to track
                        long_stats[usr] = {
                            "vpip": {"false": 0,"true": 0},
                            "pfr": {"false": 0,"true": 0},
                            "3bet_pre_flop": {"false": 0,"true": 0},
                            "fold_vs_btn_raise": {"false": 0,"true": 0},
                            "fold_c_bet": {"false": 0,"true": 0},
                            "played_hands": {"value": 1},
                            "profit": {"value": 0.0}
                        }
                        if super_debug: print("Long stats created")
                    seat_id += 1

                elif "posts big blind" in line:
                    # Find player with BB
                    player_count = len(temp_stats)
                    if super_debug: print("Assigning positions")
                    for i in range(player_count):
                        if temp_stats[f"seat{i}"]["usr"] in line:
                            # Set positions
                            six_positions = ["bb", "sb", "bu", "co", "hj", "utg"]
                            for j in range(player_count):
                                if i < j:
                                    i = player_count + j - 1
                                temp_seat_id = i - j
                                temp_stats[f"seat{temp_seat_id}"]["pos"] = six_positions[j]
                                # Save position to hand DB as well
                                tmp_usr = temp_stats[f"seat{temp_seat_id}"]["usr"]
                                data_from_hand["summary"][tmp_usr]["position"] = six_positions[j]
                            positions_assigned = 1                      
                            break

            # Find user_name in current text line
            current_seat = None
            for seat in temp_stats:
                if temp_stats[seat]["usr"] in line:
                    current_seat = seat
                    current_player = temp_stats[current_seat]["usr"]
                    if super_debug: print("Found seat and username", current_seat, current_player)

            # If valid seat number found
            if current_seat:
                # Check money betted / won
                find_dollars = findall(r"\$(\d+\.\d+)", line)
                if find_dollars:
                    if super_debug: print("Profit before:", long_stats[current_player]["profit"]["value"])
                    if state not in ["end-hand", "show-down"]:
                        if "bets" in line or "raises" in line or "calls" in line:
                            long_stats[current_player]["profit"]["value"] -= float(find_dollars[-1])
                        elif "posts" in line and "blind" in line:
                            long_stats[current_player]["profit"]["value"] -= float(find_dollars[-1])
                            data_from_hand["pre-flop"].append(f"{temp_stats[current_seat]['usr']}: posts ${find_dollars[-1]}")
                        elif "Uncalled bet" in line:
                            long_stats[current_player]["profit"]["value"] += float(find_dollars[-1])
                    elif state == "end-hand":
                        if "collected" in line or "won" in line:
                            long_stats[current_player]["profit"]["value"] += float(find_dollars[-1])
                    if super_debug: print("Profit after:", long_stats[current_player]["profit"]["value"])
                
                if state == "end-hand":
                    # Calculate money won/lost in this hand
                    if super_debug: print("Checking profit", long_stats[current_player]["profit"]["value"], temp_stats[current_seat]["chips_at_start"])
                    profit = float(long_stats[current_player]["profit"]["value"]) - float(temp_stats[current_seat]["chips_at_start"])
                    data_from_hand["summary"][current_player]["profit"] = profit
                    if super_debug: print("Checked profit for", current_player, profit)
                    # Check if profit calculated for all players
                    profit_checked = 0
                    for player in data_from_hand["summary"]:
                        if data_from_hand["summary"][player]["profit"] != 999:
                            profit_checked += 1
                    # If profit checked for all players, save data to database
                    if profit_checked == len(temp_stats):
                        dict_key = f"{hand_id}_{data_from_hand['summary'][hero_name]['profit']:.2f}"
                        bank_roll_data.append(float(data_from_hand['summary'][hero_name]['profit']))
                        total_hands_data[dict_key[3:]] = data_from_hand
                        if super_debug: print("Hand data saved to database")

                # Check dealt cards to hero and show-down cards
                if (state == "pre-flop" and "Dealt to " in line) or (state == "show-down" and "shows" in line):
                    cards = line.split("[")[1].split("]")[0]
                    data_from_hand["summary"][current_player]["cards"] = cards
                    if super_debug: print("Cards found:", cards)

                # Update long term stats for user
                long_stats, player_action = check_player_actions(current_seat, current_player, line, state, long_stats, temp_stats, super_debug)
                # Check if action was done
                if player_action:
                    if "and is all-in" in player_action:
                        player_action = player_action.replace("and is all-in", "(all-in)")
                    data_from_hand[state].append(player_action)

    # Calculate value field for stats
    for player in long_stats:
        for stat in long_stats[player]:
            if stat not in ["played_hands", "profit"]:
                if long_stats[player][stat]["true"] > 0:
                    long_stats[player][stat]["value"] = long_stats[player][stat]["true"] / (long_stats[player][stat]["true"] + long_stats[player][stat]["false"])
                    long_stats[player][stat]["value"] = int(100 * long_stats[player][stat]["value"])
                else:
                    long_stats[player][stat]["value"] = 0
    
    # If valid data, save to database and return collected data
    if long_stats:
        # Save hands to database
        save_to_json(f"./hands_db/{hand_db_file}", total_hands_data)
        return long_stats, temp_stats, bank_roll_data
    # Return 0 to indicate, that data not valid
    return 0, 0, 0

def check_player_actions(user_seat, user_name, txt_line, hand_state, long_stats, short_stats, debug):
    """
    Function that updates statistics for player specified by user_name
    """
    if debug:
        print(txt_line)
    # Init some general variables
    action = None
    button_raised = 0
    villain_raises = 0
    for seat_num in short_stats:
        if seat_num != user_seat and short_stats[seat_num]["raises"]:
            villain_raises += short_stats[seat_num]["raises"]
            # Check if this was button raise
            if villain_raises == 1 and short_stats[seat_num]["pos"] == "bu":
                button_raised = 1

    # VPIP
    if hand_state in ["pre-flop", "flop", "turn", "river"]:
        action = txt_line.strip("\n")#.replace("$", "")
        if "folds" in txt_line:
            long_stats[user_name]["vpip"]["false"] += 1
        elif "checks" in txt_line:
            long_stats[user_name]["vpip"]["false"] += 1
        elif "bets" in txt_line or "raises" in txt_line or "calls" in txt_line:
            long_stats[user_name]["vpip"]["true"] += 1
            if "bets" in txt_line or "raises" in txt_line:
                short_stats[user_seat]["raises"] += 1
        else:
            action = None   # If no action done, reset action to None

    if hand_state == "pre-flop":
        # PFR
        if villain_raises == 0:
            if "raises" in txt_line:
                long_stats[user_name]["pfr"]["true"] += 1
            elif "folds" in txt_line or "checks" in txt_line:
                long_stats[user_name]["pfr"]["false"] += 1
        # 3Bet pre-flop
        elif villain_raises:
            if "raises" in txt_line:
                long_stats[user_name]["3bet_pre_flop"]["true"] += 1
            elif "calls" in txt_line or "folds" in txt_line:
                long_stats[user_name]["3bet_pre_flop"]["false"] += 1
        # Fold vs button raise
        if button_raised:
            if "raises" in txt_line or "calls" in txt_line:
                long_stats[user_name]["fold_vs_btn_raise"]["false"] += 1
            elif "folds" in txt_line:
                long_stats[user_name]["fold_vs_btn_raise"]["true"] += 1
    
    # Fold to C bet
    if hand_state == "flop" and villain_raises and short_stats[user_seat]["raises"] == 0:
        if "folds" in txt_line:
            long_stats[user_name]["fold_c_bet"]["true"] += 1
        else:
            long_stats[user_name]["fold_c_bet"]["false"] += 1

    return long_stats, action

def save_to_json(target, json_data):
    """
    Function that saves data to json file
    """
    if "hands_db" in target and not os.path.exists("./hands_db"):
        os.makedirs("./hands_db")
    with open(target, "w") as outfile: 
        json.dump(json_data, outfile, indent=1, separators=(',', ': '))

def load_from_json(source):
    """
    Function that saves data to json file
    """
    if os.path.exists(source):
        with open(source) as json_file:
            json_data = json.load(json_file)
        return json_data
    else:
        # Create initial files
        if "./hud_data/config.json" in source:
            print("\n####################  ERROR ####################")
            print("Config file not found, created one with default values")
            print("Please fill in the config file with your own values\n")
            create_opening_ranges()
            create_hero_stats("./hud_data/hero_stats.json")
            create_config(source)
        elif "hud_data/hero_stats.json" in source:
            create_hero_stats(source)
        elif "hud_data/open_" in source:
            create_opening_ranges()
        print(f"Couldn't find file: {source}")
        return 0

def create_hero_stats(target_file):
    hero_statistics = {
        "vpip": {"false": 0, "true": 0, "value": 0},
        "pfr": {"false": 0, "true": 0, "value": 0},
        "3bet_pre_flop": {"false": 0, "true": 0, "value": 0},
        "fold_vs_btn_raise": {"false": 0, "true": 0, "value": 0},
        "fold_c_bet": {"false": 0, "true": 0, "value": 0},
        "played_hands": {"value": 0},
        "profit": {"value": 0.0}
    }
    save_to_json(target_file, hero_statistics)

def create_config(target_file):
    config_data = {
        "path_to_hand_history": "C:\\path\\to\\your\\PokerStars\\HandHistory\\Username",
        "pokerstars_username": "TBA",
    }
    save_to_json(target_file, config_data)

def create_opening_ranges():
    # Filepath for the CSV
    csv_file = "./hud_data/openingHands.csv"

    json_dict = {}

    # Read and process the CSV file
    try:
        with open(csv_file, mode='r') as file:
            csv_reader = csv.reader(file)
            for row in csv_reader:
                for cell in row:
                    json_dict[cell] = 0
    except FileNotFoundError:
        print(f"File '{csv_file}' not found. Please make sure the file exists.")

    # Save initial opening ranges for each position
    positions = ["sb", "bb", "utg", "hj", "co", "bu"]
    for pos in positions:
        file_name = f"./hud_data/open_{pos}.json"
        save_to_json(file_name, json_dict)

def save_to_csv(target, csv_data):
    """
    Function that saves data to json file
    """
    with open(target, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerows(csv_data)
