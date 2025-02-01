"""
Library of utility functions for AceTracker.py
"""
import json
import os
import csv
from re import findall
import re

def street_start_actions(short_stats, hand_db_data, line, current_state, previous_state, debug=0):
    """
    Function for handling actions required in start of every street
    """
    streets = ["pre-flop", "flop", "turn", "river"]
    # Check cards
    cards = None
    if current_state == "flop":
        cards = line.split("[")[1].split("]")[0]
    elif current_state in ["turn", "river"]:
        cards = line.split("] [")[1].split("]")[0]
    
    # Reset raise counter and check money betted
    pot_size = 0.0
    for seat in short_stats:
        short_stats[seat]["raises"] = 0
        short_stats[seat]["money_betted_total"] += short_stats[seat]["money_betted_this_state"]
        pot_size += short_stats[seat]["money_betted_this_state"]
        short_stats[seat]["money_betted_this_state"] = 0

    # Check pot size for previous street
    if previous_state in streets:
        hand_db_data[previous_state].append(f"pot size: ${pot_size:.2f}")
        if debug: print(f"ADDED pot size: ${pot_size:.2f}")
    return short_stats, hand_db_data, cards

def handle_txt_file(source_file, hero_name, tournament_mode=0):
    """
    Function for parsing txt files containing all hands played in one table
    """
    # Pre-compile regex patterns
    dollar_pattern = re.compile(r"\$(\d+\.\d+)")
    digits_pattern = re.compile(r"(\d)")
    hand_id_pattern = re.compile(r"PokerStars Hand #(\d+)")
    
    # Initialize variables outside the loop
    temp_stats = {}
    long_stats = {}
    bank_roll_data = []
    
    # Read file in chunks for better performance
    with open(source_file, 'r', buffering=8192) as source:
        if tournament_mode:
            source_file = source_file.replace("No Limit", "- No Limit")
        hand_db_file = source_file.split("\\")[-1].split("-")[0].replace(" ", "_") + "db.json"
        
        # Process file in larger chunks
        content = source.read()
        lines = content.splitlines()
        
        state = "none"
        positions_assigned = 0
        seat_id = 0
        current_seat = None
        data_from_hand = {}
        total_hands_data = {}
        # DEBUG SHIT
        super_debug = 0
        for line in lines:
            # Check hand state
            if "PokerStars Hand #" in line:
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
                temp_stats, data_from_hand, cards = street_start_actions(temp_stats, data_from_hand, line, state, "pre-flop", super_debug)
                data_from_hand["flop"] = [f"board: {cards}"]
                if super_debug: print("HAND_DB 1: ", data_from_hand["pre-flop"])
            elif "*** TURN ***" in line:
                state = "turn"
                temp_stats, data_from_hand, cards = street_start_actions(temp_stats, data_from_hand, line, state, "flop", super_debug)
                data_from_hand["turn"] = [f"board: {cards}"]
                if super_debug: print("HAND_DB 2: ", data_from_hand["flop"])
            elif "*** RIVER ***" in line:
                state = "river"
                temp_stats, data_from_hand, cards = street_start_actions(temp_stats, data_from_hand, line, state, "turn", super_debug)
                data_from_hand["river"] = [f"board: {cards}"]
                if super_debug: print("HAND_DB 3: ", data_from_hand["turn"])
            elif "*** SHOW DOWN ***" in line:
                state = "showdown"
                temp_stats, data_from_hand, _ = street_start_actions(temp_stats, data_from_hand, line, state, "river", super_debug)
                if super_debug: print("HAND_DB 4: ", data_from_hand["river"])
            elif "*** SUMMARY ***" in line:
                # Calculate pot size, total money betted etc. one last time to update values for previous street
                last_street = state
                state = "end-hand"
                temp_stats, data_from_hand, _ = street_start_actions(temp_stats, data_from_hand, line, state, last_street, super_debug)


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
                        "money_betted_this_state": 0.0,
                        "money_betted_total": 0.0
                    }
                    # Create data to hand DB for player and check if player exists in long term stats
                    data_from_hand["summary"][usr] = {"position": "??", "cards": "?? ??", "profit": 999}
                    if usr in long_stats:
                        long_stats[usr]["played_hands"]["value"] += 1
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
                if tournament_mode:
                    tmp_line = line.replace(f"{current_player}", "")   # Remove player name from line to not confuse digit finding
                    find_dollars = digits_pattern.findall(tmp_line)
                else:
                    find_dollars = dollar_pattern.findall(line)
                if find_dollars:
                    if state not in ["end-hand", "showdown"]:
                        if "bets" in line or "calls" in line:
                            temp_stats[current_seat]["money_betted_this_state"] += float(find_dollars[-1])
                        elif "posts" in line and "blind" in line:
                            temp_stats[current_seat]["money_betted_this_state"] += float(find_dollars[-1])
                            data_from_hand["pre-flop"].append(f"{temp_stats[current_seat]['usr']}: posts ${find_dollars[-1]}")
                        elif "raises" in line:
                            # Special case: If hero raises after call / bet / raise, we can just override previous money betted
                            temp_stats[current_seat]["money_betted_this_state"] = float(find_dollars[-1])
                        elif "Uncalled bet" in line:
                            temp_stats[current_seat]["money_betted_this_state"] -= float(find_dollars[-1])
                    elif state == "showdown":
                        # Check cash out
                        if "cashed out the hand" in line:
                            cash_out_amount = float(find_dollars[0])
                            temp_stats[current_seat]["money_betted_total"] -= cash_out_amount
                            data_from_hand["river"].append(f"{temp_stats[current_seat]['usr']}: cashed out ${cash_out_amount}")
                    elif state == "end-hand":
                        if ("collected" in line or "won" in line) and ("player cashed out" not in line):
                            temp_stats[current_seat]["money_betted_total"] -= float(find_dollars[-1])
                
                if state == "end-hand":
                    # Calculate money won/lost in this hand
                    profit_before = float(long_stats[current_player]["profit"]["value"])
                    long_stats[current_player]["profit"]["value"] = profit_before - temp_stats[current_seat]["money_betted_total"]
                    if super_debug: print("Checking profit", long_stats[current_player]["profit"]["value"], profit_before)
                    
                    data_from_hand["summary"][current_player]["profit"] = long_stats[current_player]["profit"]["value"] - profit_before

                    # Check if profit calculated for all players
                    profit_checked = 0
                    for player in data_from_hand["summary"]:
                        if data_from_hand["summary"][player]["profit"] != 999:
                            profit_checked += 1

                    # If profit checked for all players, save data to database
                    if profit_checked == len(temp_stats):
                        dict_key = f"{hand_id}_{data_from_hand['summary'][hero_name]['profit']:.2f}"
                        if tournament_mode:
                            dict_key = f"T_{dict_key}"
                        bank_roll_data.append(float(data_from_hand['summary'][hero_name]['profit']))
                        total_hands_data[dict_key] = data_from_hand
                        if super_debug: print("Hand data saved to database", data_from_hand)

                # Check dealt cards to hero and showdown cards
                if (state == "pre-flop" and "Dealt to " in line) or (state == "showdown" and "shows" in line):
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
        json.dump(json_data, outfile, indent=4, separators=(',', ': '))

def load_from_json(source):
    """
    Function that loads data from json file
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
        elif "opening_ranges.json" in source:
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
    """Create initial opening ranges JSON with empty ranges for each position"""
    opening_ranges = {
        "SB": [],
        "BB": [],
        "UTG": [],
        "HJ": [],
        "CO": [],
        "BU": []
    }
    save_to_json("./hud_data/opening_ranges.json", opening_ranges)

def save_to_csv(target, csv_data):
    """
    Function that saves data to json file
    """
    with open(target, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerows(csv_data)
