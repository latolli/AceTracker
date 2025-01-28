"""
AceTracker Tkinter app for tracking PokerStars data
"""

import customtkinter as ctk
import csv
import os
import matplotlib.pyplot as plt
from matplotlib.figure import Figure 
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib import rcParams
from cycler import cycler
from re import findall
from tkinter import Listbox, Scrollbar
from utility import handle_txt_file, save_to_json, load_from_json, save_to_csv

# Set themes
ctk.set_appearance_mode("dark")  # Modes: system (default), light, dark
ctk.set_default_color_theme("dark-blue")  # Themes: blue (default), dark-blue, green

# Load config
config_data = load_from_json(source="./hud_data/config.json")
if config_data != 0:
    history_path = config_data["path_to_hand_history"]
    ps_username = config_data["pokerstars_username"]

ctk_default_blue = "#1f538d"
ctk_default_grey = "#212121"
ctk_default_grey_light = "#292929"

class MainApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Configure main window
        self.title("AceTracker")
        self.geometry("1200x900")

        # Menu Frame (for navigation)
        self.menu_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.menu_frame.pack(side="top")

        # Container for screens
        self.container = ctk.CTkFrame(self)
        self.container.pack(side="bottom", expand=True, fill="both")

        # Add navigation buttons in the menu frame
        self.stats_button = ctk.CTkButton(self.menu_frame, text="Stats", command=self.show_stats)
        self.stats_button.pack(side="left", pady=10, padx=10)

        self.ranges_button = ctk.CTkButton(self.menu_frame, text="Ranges", command=self.show_ranges)
        self.ranges_button.pack(side="left", pady=10, padx=10)

        self.settings_button = ctk.CTkButton(self.menu_frame, text="Hand DB", command=self.show_history)
        self.settings_button.pack(side="left", pady=10, padx=10)

        self.settings_button = ctk.CTkButton(self.menu_frame, text="Settings", command=self.show_settings)
        self.settings_button.pack(side="left", pady=10, padx=10)

        # Dictionary to store screens
        self.screens = {}

        # Create and store screens
        self.screens["Stats"] = StatsScreen(self.container, self)
        self.screens["Ranges"] = OpeningRanges(self.container, self)
        self.screens["Hand DB"] = HandDBScreen(self.container, self)
        self.screens["Settings"] = SettingsScreen(self.container, self)

        # Show the HUD screen by default
        self.current_screen = "Stats"
        self.show_screen("Stats")

    def show_screen(self, screen_name):
        """Display the requested screen."""
        self.current_screen = screen_name
        screen = self.screens[screen_name]
        screen.tkraise()
        screen.pack()

    def show_stats(self):
        self.screens[self.current_screen].forget()
        self.show_screen("Stats")

    def show_ranges(self):
        self.screens[self.current_screen].forget()
        self.show_screen("Ranges")

    def show_history(self):
        self.screens[self.current_screen].forget()
        self.show_screen("Hand DB")

    def show_settings(self):
        self.screens[self.current_screen].forget()
        self.show_screen("Settings")


class StatsScreen(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        global history_path
        self.controller = controller

        # Add content to the HUD screen
        ctk.CTkLabel(self, text=f"{ps_username}", font=("Arial", 24, "bold")).pack(padx=10, pady=10)

        # Button for refreshing data
        self.hud_button = ctk.CTkButton(self, text="Refresh", command=self.refresh_data)
        self.hud_button.pack(side="top", pady=5, padx=10)
        
        # Create frame for showing data
        self.hud_frame = ctk.CTkFrame(self)
        self.hud_frame.pack(side="top", padx=20, pady=10)

        # Add optimal stats for REG
        ctk.CTkLabel(self, text=f"REG: 23 / 19 / 7 / 65 / 50", font=("Arial", 14, "bold")).pack(padx=10, pady=5)

        # Create frame for profit graph
        self.plot_frame = ctk.CTkFrame(self)
        self.plot_frame.pack(side="top", pady=10, fill="both", expand=True)

        # Load initial data and display hero statistics
        self.refresh_data()

    def display_data(self, statistics):
        """Displays the provided JSON data in the hud_frame.""" 
        # Clear any existing widgets in the frame
        for widget in self.hud_frame.winfo_children():
            widget.destroy()
        
        # Add a label for each key-value pair in the JSON
        for key in statistics:
            # Create a sub-frame for each stat
            stat_frame = ctk.CTkFrame(self.hud_frame)
            stat_frame.pack(fill="x", pady=3, padx=5)
            
            # Add a label for the stat name
            stat_label = ctk.CTkLabel(stat_frame, text=f"{key.upper()}:", font=("Arial", 14, "bold"))
            stat_label.pack(side="left", padx=10)
            
            # Add a label for the stat value (assuming a nested 'value' key in the JSON)
            if key == "profit": statistics[key]['value'] = f"{statistics[key]['value']:.2f}"
            value_label = ctk.CTkLabel(stat_frame, text=f"{statistics[key]['value']}", font=("Arial", 14))
            value_label.pack(side="right", padx=10)

    def refresh_data(self):
        # Go through all data and calculate stats for Hero
        files = [os.path.join(history_path, f) for f in os.listdir(history_path) if os.path.isfile(os.path.join(history_path, f)) and "USD No Limit Hold'em" in f]
        if not files:
            print("No files found from", history_path)
        else:
            statistics = {}
            bank_roll_data = []
            for f in files:
                single_table_stats, _, tmp_bank_roll_data = handle_txt_file(f, ps_username)
                if single_table_stats:
                    single_table_stats = single_table_stats[f"{ps_username}"]
                    bank_roll_data.append(tmp_bank_roll_data)
                    for key in single_table_stats:
                        if key in statistics:
                            if key in ["played_hands", "profit"]:
                                statistics[key]["value"] += single_table_stats[key]["value"]
                            else:
                                statistics[key]["true"] += single_table_stats[key]["true"]
                                statistics[key]["false"] += single_table_stats[key]["false"]
                        else:
                            # This is first file, we can just copy values to total stats
                            statistics = single_table_stats
                            break

            # Final tuning on statistics
            for stat in statistics:
                if stat not in ["played_hands", "profit"]:
                    if statistics[stat]["true"] > 0:
                        # Calculate percentage
                        statistics[stat]["value"] = statistics[stat]["true"] / (statistics[stat]["true"] + statistics[stat]["false"])
                        statistics[stat]["value"] = int(100 * statistics[stat]["value"])
                    else:
                        statistics[stat]["value"] = 0
            
            # Save to JSON file
            save_to_json(target="./hud_data/hero_stats.json", json_data=statistics)

            # Save bank roll data to CSV
            save_to_csv(target="./hud_data/bank_roll_data.csv", csv_data=bank_roll_data)

            self.display_data(statistics)
            self.display_plot(bank_roll_data)
    
    def display_plot(self, plot_data):
        # Clear the plot frame
        for widget in self.plot_frame.winfo_children():
            widget.destroy()

        # Combine multiple lists into one list and add values together sequentially
        combined_data = []
        current_val = 0
        for sub_list in plot_data:
            for val in sub_list:
                current_val += val
                combined_data.append(current_val)

        # Create a figure and axis for the plot
        plt.style.use('dark_background')
        rcParams['axes.prop_cycle'] = cycler('color', ['red', ctk_default_blue, 'green'])
        fig = Figure(figsize = (50, 10), dpi = 100, facecolor=ctk_default_grey_light)
        plot1 = fig.add_subplot(111)
        plot1.set_title("Profit over time", 
            fontdict={'fontsize': 14})
        plot1.set_facecolor(ctk_default_grey)
        plot1.grid(linestyle='--', linewidth=0.5, axis='y')
        plot1.plot(combined_data)
        canvas = FigureCanvasTkAgg(fig, master=self.plot_frame)
        canvas.draw()
        canvas.get_tk_widget().pack()

class OpeningRanges(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        # Create initial list for cells that have been clicked
        self.selected_cells = []
        self.player_data = []
        self.active_pos = "SB"
        
        # Create frame for showing data
        self.hud_frame = ctk.CTkFrame(self)
        self.hud_frame.pack(side="top", expand=True)

        # Menu Frame (for navigation)
        self.menu_frame = ctk.CTkFrame(self, width=200)
        self.menu_frame.pack(side="top", fill="x")

        # Button frame
        self.button_frame = ctk.CTkFrame(self.menu_frame, fg_color=ctk_default_grey)
        self.button_frame.pack(side="bottom", pady=(0, 10))

        # Create the frame for the table
        self.table_frame = ctk.CTkFrame(self)
        self.table_frame.pack(side="top", fill="both", expand=True)

        # Create the frame for the table
        self.bottom_frame = ctk.CTkFrame(self)
        self.bottom_frame.pack(side="bottom")

        # Button for refreshing data
        self.hud_button = ctk.CTkButton(self.menu_frame, text="Refresh", command=self.refresh_data)
        self.hud_button.pack(side="top", pady=5, padx=10)

        # Load initial data
        self.refresh_data()

        # Load hands
        with open('./hud_data/openingHands.csv') as csv_file:
            csv_reader = csv.reader(csv_file)
            self.tableTexts = [row for row in csv_reader]

        # Add navigation buttons and title
        self.position_display = ctk.CTkLabel(self.menu_frame, text=f"{self.active_pos}".upper(), font=("Arial", 24, "bold"))
        self.position_display.pack(side="top", pady=3, padx=10)

        self.sb = ctk.CTkButton(self.button_frame, text="SB", command=lambda: self.change_active_position("sb"))
        self.sb.pack(side="left", padx=5)

        self.bb = ctk.CTkButton(self.button_frame, text="BB", command=lambda: self.change_active_position("bb"))
        self.bb.pack(side="left", padx=5)

        self.utg = ctk.CTkButton(self.button_frame, text="UTG", command=lambda: self.change_active_position("utg"))
        self.utg.pack(side="left", padx=5)

        self.hj = ctk.CTkButton(self.button_frame, text="HJ", command=lambda: self.change_active_position("hj"))
        self.hj.pack(side="left", padx=5)

        self.co = ctk.CTkButton(self.button_frame, text="CO", command=lambda: self.change_active_position("co"))
        self.co.pack(side="left", padx=5)

        self.bu = ctk.CTkButton(self.button_frame, text="BU", command=lambda: self.change_active_position("bu"))
        self.bu.pack(side="left", padx=5)

        # Add stuff to bottom frame
        self.edit_button = ctk.CTkButton(self.bottom_frame, text="Clear", command=lambda: self.clear_selected()).pack(side="left", pady=15, padx=15)
        self.edit_button = ctk.CTkButton(self.bottom_frame, text="Confirm", command=lambda: self.confirm_selection()).pack(side="left", pady=15, padx=15)
        self.selected_cells_display = ctk.CTkLabel(self.bottom_frame, text=f"Selected cells: {self.selected_cells}")
        self.selected_cells_display.pack(padx=15, pady=15)

        # Create initial table with SB position selected
        self.change_active_position("sb")

    def create_table(self):
        # Clear the frame first
        for widget in self.table_frame.winfo_children():
            widget.destroy()

        for row in range(13):
            for col in range(13):
                # Create a clickable cell
                cell_text = f"{self.tableTexts[row][col]}"
                cell_color = None
                if self.active_open_range[cell_text]:
                    cell_color = "brown"

                cell = ctk.CTkButton(
                    self.table_frame,
                    text=f"{self.tableTexts[row][col]}",
                    command=lambda c=cell_text: self.on_cell_click(c),
                    corner_radius=5,
                    fg_color=cell_color
                )
                cell.grid(row=row, column=col, padx=3, pady=3, sticky="nsew")

        # Configure grid weights for dynamic resizing
        for i in range(13):
            self.table_frame.rowconfigure(i, weight=1)
        for j in range(13):
            self.table_frame.columnconfigure(j, weight=1)

    def on_cell_click(self, cell_text):
        """Handles cell click event."""
        if cell_text in self.selected_cells:
            for i, cell in enumerate(self.selected_cells):
                if cell == cell_text:
                    self.selected_cells.pop(i)
        else:
            self.selected_cells.append(cell_text)
        self.refresh_selected_list()

    def change_active_position(self, new_pos):
        """Change position and load opening range for selected position"""
        self.active_pos = new_pos
        self.active_open_range = load_from_json(source=f"./hud_data/open_{new_pos}.json")

        # Refresh table and active pos
        self.position_display.destroy()
        self.position_display = ctk.CTkLabel(self.menu_frame, text=f"{self.active_pos}".upper(), font=("Arial", 24, "bold"))
        self.position_display.pack(side="top", pady=5)
        self.create_table()

    def clear_selected(self):
        # Empty selected cells list
        self.selected_cells = []
        self.refresh_selected_list()

    def confirm_selection(self):
        # Loop selected cells and change their values
        for cell in self.selected_cells:
            self.active_open_range[cell] = (self.active_open_range[cell]+1) % 2 # Change to 0 or 1
        self.selected_cells = []

        # Save to JSON file
        save_to_json(target=f"./hud_data/open_{self.active_pos}.json", json_data=self.active_open_range)

        # Refresh table and list
        self.create_table()
        self.refresh_selected_list()

    def refresh_selected_list(self):
        self.selected_cells_display.destroy()
        self.selected_cells_display = ctk.CTkLabel(self.bottom_frame, text=f"Selected cells: {self.selected_cells}")
        self.selected_cells_display.pack(padx=10, pady=10)

    def refresh_data(self):
        # Check latest table from hand_history
        files = [os.path.join(history_path, f) for f in os.listdir(history_path) if os.path.isfile(os.path.join(history_path, f)) and "USD No Limit Hold'em" in f]
        if files:
            latest_file = max(files, key=os.path.getmtime)

        # Parse data from latest table
        if latest_file:
            table_stats, last_hand_stats, _ = handle_txt_file(latest_file, ps_username)
            if table_stats:
                self.display_hud(table_stats, last_hand_stats)
    
    def display_hud(self, long_stats, short_stats):
        """Displays the provided JSON data in the hud_frame.""" 
        # Clear any existing widgets in the frame
        for widget in self.hud_frame.winfo_children():
            widget.destroy()

        # Create a table displaying stats for each player
        header = ["Player", "VPIP", "PFR", "3Bet", "Fold vs Btn", "Fold vs C-bet", "Hands"]
        row, col = 0, 0
        for h in header:
            cell_text = f"{h}"

            cell = ctk.CTkLabel(
                self.hud_frame,
                text=f"{cell_text}",
                corner_radius=0,
                font=("Arial", 14)
            )
            cell.grid(row=row, column=col, padx=5, pady=3, sticky="nsew")
            col += 1

        # Display players in a descending order based on played hands
        active_players = []
        for seat in short_stats:
            player = short_stats[seat]["usr"]
            played_hands = long_stats[player]["played_hands"]["value"]
            active_players.append((player, played_hands))

        # Sort players by played hands in descending order
        active_players.sort(key=lambda x: x[1], reverse=True)

        for player, _ in active_players:
            row += 1
            col = 0
            cell = ctk.CTkLabel(
                self.hud_frame,
                text=f"{player}",
                corner_radius=0,
                font=("Arial", 14, "bold")
            )
            cell.grid(row=row, column=col, padx=5, pady=3, sticky="nsew")
            for stat in long_stats[player]:
                if stat != "profit":
                    col += 1
                    cell_text = f"{long_stats[player][stat]['value']}"

                    cell = ctk.CTkLabel(
                        self.hud_frame,
                        text=f"{cell_text}",
                        corner_radius=0,
                        font=("Arial", 14)
                    )
                    cell.grid(row=row, column=col, padx=5, pady=3, sticky="nsew")

class HandDBScreen(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        # Init active filters for listbox
        self.active_filters = {
            "won": 0,
            "lost": 0,
            "post-flop": 0,
            "showdown": 0
        }

        # Load hands data from JSON files
        self.hands_data = self.load_hands_data()

        # Create frames for displaying data
        self.selection_frame = ctk.CTkFrame(self, width=50)
        self.selection_frame.pack(side="left", padx=5, pady=5, expand=False)

        self.display_frame = ctk.CTkFrame(self)
        self.display_frame.pack(side="right", fill="both", expand=True)

        self.stages_frame = ctk.CTkFrame(self.display_frame, corner_radius=0)
        self.stages_frame.pack(side="top", fill="both", expand=True)

        self.summary_frame = ctk.CTkFrame(self.display_frame, corner_radius=0)
        self.summary_frame.pack(side="bottom", fill="x")

        # Frame for listbox
        self.listbox_frame = ctk.CTkFrame(self.selection_frame)
        self.listbox_frame.pack(fill="both")

        # Filter checkboxes
        self.checkbox_frame = ctk.CTkFrame(self.selection_frame, fg_color=ctk_default_grey)
        self.checkbox_frame.pack(side="top", pady=5)

        self.won_checkbox = ctk.CTkCheckBox(self.checkbox_frame, text="Won", command=self.update_listbox)
        self.won_checkbox.grid(row=0, column=0, padx=3, pady=3, sticky="nsew")

        self.lost_checkbox = ctk.CTkCheckBox(self.checkbox_frame, text="Lost", command=self.update_listbox)
        self.lost_checkbox.grid(row=0, column=1, padx=3, pady=3, sticky="nsew")

        self.post_flop_checkbox = ctk.CTkCheckBox(self.checkbox_frame, text="Post-flop", command=self.update_listbox)
        self.post_flop_checkbox.grid(row=1, column=0, padx=3, pady=3, sticky="nsew")

        self.showdown_checkbox = ctk.CTkCheckBox(self.checkbox_frame, text="Showdown", command=self.update_listbox)
        self.showdown_checkbox.grid(row=1, column=1, padx=3, pady=3, sticky="nsew")

        # Create listbox for selecting hands with a scrollbar
        self.hand_listbox = Listbox(self.listbox_frame, bg=ctk_default_grey, fg="white", activestyle='none',
            selectbackground=ctk_default_blue, selectforeground="white", height=38, font=("Arial", 11))
        self.hand_listbox.pack(side="left", fill="both")

        self.scrollbar = Scrollbar(self.listbox_frame, command=self.hand_listbox.yview)
        self.scrollbar.pack(side="right", fill="y")

        self.hand_listbox.config(yscrollcommand=self.scrollbar.set)
        self.hand_listbox.bind("<<ListboxSelect>>", self.on_hand_select)

        # Populate listbox with hand IDs
        for hand_id in self.hands_data.keys():
            self.hand_listbox.insert("end", hand_id)

        # Create frames for each stage of the hand
        self.preflop_frame = ctk.CTkFrame(self.stages_frame)
        self.preflop_frame.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        self.flop_frame = ctk.CTkFrame(self.stages_frame)
        self.flop_frame.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        self.turn_frame = ctk.CTkFrame(self.stages_frame)
        self.turn_frame.pack(side="left", fill="both", expand=True, padx=5, pady=5)

        self.river_frame = ctk.CTkFrame(self.stages_frame)
        self.river_frame.pack(side="left", fill="both", expand=True, padx=5, pady=5)

    def load_hands_data(self):
        hands_data = {}
        hands_db_path = "./hands_db"
        for file_name in os.listdir(hands_db_path):
            if file_name.endswith("_db.json"):
                data = load_from_json(source=os.path.join(hands_db_path, file_name))
                hands_data.update(data)
        # Filter hands to be displayed
        for filter in self.active_filters:
            # Update list every iteration
            hand_ids = list(hands_data.keys())
            if filter == "won" and self.active_filters["won"] == 1:
                for hand in hand_ids:
                    profit = hand.split("_")[-1]
                    if float(profit) <= 0:
                        hands_data.pop(hand)
            elif filter == "lost" and self.active_filters["lost"] == 1:
                for hand in hand_ids:
                    profit = hand.split("_")[-1]
                    if float(profit) >= 0:
                        hands_data.pop(hand)
            elif filter == "post-flop" and self.active_filters["post-flop"] == 1:
                for hand in hand_ids:
                    hero_found = 0
                    if "flop" in hands_data[hand]:
                        for action in hands_data[hand]["flop"]:
                            if ps_username in action:
                                hero_found = 1
                                break
                    if not hero_found: hands_data.pop(hand)
            elif filter == "showdown" and self.active_filters["showdown"] == 1:
                for hand in hand_ids:
                    hero_folded = 1
                    for stage in ["flop", "turn", "river"]:
                        if stage in hands_data[hand]:
                            for action in hands_data[hand][stage]:
                                if ps_username in action:
                                    hero_folded = 0
                                    if "folds" in action:
                                        hero_folded = 1
                                        break
                        else:
                            hero_folded = 1
                            break
                    if hero_folded: hands_data.pop(hand)

        return hands_data

    def update_listbox(self):
        # Update active filters based on checkboxes
        self.active_filters["won"] = self.won_checkbox.get()
        self.active_filters["lost"] = self.lost_checkbox.get()
        self.active_filters["post-flop"] = self.post_flop_checkbox.get()
        self.active_filters["showdown"] = self.showdown_checkbox.get()

        # Update listbox data
        self.hand_listbox.delete(0, "end")
        self.hands_data = self.load_hands_data()
        for hand_id in self.hands_data.keys():
            self.hand_listbox.insert("end", hand_id)

    def on_hand_select(self, event):
        # Get selected hand ID
        selection = event.widget.curselection()
        if selection:
            hand_id = event.widget.get(selection[0])
            hand_data = self.hands_data[hand_id]
            self.display_hand_data(hand_data)

    def display_hand_data(self, hand_data):
        # Clear existing data in frames
        for frame in [self.preflop_frame, self.flop_frame, self.turn_frame, self.river_frame, self.summary_frame]:
            for widget in frame.winfo_children():
                widget.destroy()

        # Display data for each stage
        stages = {
            "pre-flop": self.preflop_frame,
            "flop": self.flop_frame,
            "turn": self.turn_frame,
            "river": self.river_frame,
            "summary": self.summary_frame
        }
        pot_size = 0.0
        for s in stages.keys():
            title = f"- - - - - -   {s.capitalize()}   - - - - - -"
            if s in hand_data:
                if s != "summary":
                    pot_size = self.display_stage_data(stages[s], title, hand_data[s], pot_size)
                else:
                    self.display_summary_data(stages[s], hand_data[s])
            else:
                # Display empty box with title
                ctk.CTkLabel(stages[s], text=f"{title}", font=("Arial", 19, "bold")).pack(anchor="n", padx=10, pady=2)

    def display_stage_data(self, frame, stage_name, stage_data, pot_size=0.0):
        ctk.CTkLabel(frame, text=f"{stage_name}", font=("Arial", 19, "bold")).pack(anchor="n", padx=10, pady=2)
        for action in stage_data:
            if action.startswith("board:"):
                # Extract the board cards
                board_cards = action.split("board: ")[1].split()
                self.text_to_cards(frame, board_cards)
            else:
                # Check pot size
                if "posts" in action or "bets" in action or "raises" in action or "calls" in action:
                    amount = float(findall(r"\$(\d+\.\d+)", action)[-1])
                    pot_size += amount

                # Set text color and font options based on action type
                box_color = None
                if ps_username in action:
                    action = action.replace(ps_username, "HERO")
                    box_color = "#383838"
                if "raises" in action:
                    txt_color = "#ce2029"
                elif "bets" in action:
                    txt_color = "#ff4d00"
                elif "calls" in action or "checks" in action:
                    txt_color = "#e4cd05"
                elif "posts" in action:
                    txt_color = "green"
                else:
                    txt_color = "white"

                # Split action to two parts: Username, action
                usr, act = action.split(":")

                # If action is check or fold, display in a single line
                if "folds" in act or "checks" in act:
                    usr = usr + act
                    act = None

                action_frame = ctk.CTkFrame(frame, fg_color=box_color)
                action_frame.pack(anchor="w", padx=10, pady=2, fill="x")

                usr_label = ctk.CTkLabel(
                    action_frame,
                    text=usr.strip(),
                    font=("Arial", 12, "normal"),
                    text_color=txt_color
                )
                usr_label.pack(anchor="nw", padx=10, pady=0)

                if act:
                    act_label = ctk.CTkLabel(
                        action_frame,
                        text=act.strip(),
                        font=("Arial", 14, "bold"),
                        text_color=txt_color
                    )
                    act_label.pack(anchor="w", padx=10, pady=0)
        # Display final pot size for the stage
        pot_label = ctk.CTkLabel(
            frame,
            text=f"Pot size: ${pot_size:.2f}",
            font=("Arial", 14, "bold"),
            text_color="white"
        )
        pot_label.pack(side="bottom", anchor="w", padx=10, pady=5)
        return pot_size

    def display_summary_data(self, frame, stage_data):
        for player in stage_data:
            player_frame = ctk.CTkFrame(frame)
            player_frame.pack(side="left", fill="x", expand=True, padx=5, pady=5)
            
            # Display player name and position
            player_txt = player
            if player == ps_username:
                player_txt = "HERO"
            position = f"{stage_data[player]['position']}".upper()
            player_label = ctk.CTkLabel(
                player_frame,
                text=f"{position} - {player_txt}",
                font=("Arial", 16, "bold"),
                text_color="white"
            )
            player_label.pack(side="top", padx=5, pady=5)

            # Display player cards
            self.text_to_cards(player_frame, stage_data[player]['cards'].split())

            # Display player profit
            amount = float(stage_data[player]['profit'])
            profit_color = "white"
            if amount > 0:
                profit_color = "#008000"
            elif amount < 0:
                profit_color = "#ff0000"
            profit_label = ctk.CTkLabel(
                player_frame,
                text=f"${stage_data[player]['profit']:.2f}",
                font=("Arial", 16, "bold"),
                text_color=profit_color
            )
            profit_label.pack(side="top", padx=10, pady=5)

    def text_to_cards(self, frame, cards_list):
        board_frame = ctk.CTkFrame(frame, fg_color=ctk_default_grey)
        board_frame.pack(side="top", padx=5, pady=5)

        for card in cards_list:
            rank = card[:-1]
            suit = card[-1]
            suit_symbol = {
                'h': '♥',
                'd': '♦',
                'c': '♣',
                's': '♠',
                '?': '?' # For unknown cards
            }[suit]
            suit_color = {
                'h': '#ff0000',
                'd': '#f94449',
                'c': '#000020',
                's': '#000000',
                '?': '#111111' # For unknown cards
            }[suit]
            card_label = ctk.CTkLabel(
                board_frame,
                text=f"{rank}\n{suit_symbol}",
                font=("Arial", 22, "bold"),
                width=50,
                height=70,
                corner_radius=5,
                fg_color=suit_color,
                text_color="white"
            )
            card_label.pack(side="left", padx = 5)

class SettingsScreen(ctk.CTkFrame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        # Add content to the About screen
        ctk.CTkLabel(self, text="Welcome to the Settings Screen!").pack(padx=10, pady=10)

if __name__ == "__main__":
    app = MainApp()
    app.mainloop()
