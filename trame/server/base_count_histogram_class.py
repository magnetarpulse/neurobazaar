# Core libraries for data processing
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# Core libraries for rendering
from trame.app import get_server
from trame.ui.vuetify import SinglePageLayout
from trame.widgets import vuetify, matplotlib
from trame.decorators import TrameApp, change

# Base class for the histogram application
from abc import abstractmethod

## ================================================================== ## 
## Visualization service. Finds the counts in ranges. The base class. ##         
## ================================================================== ##

@TrameApp()
class BaseRangeCountHistogram:

    # ---------------------------------------------------------------------------------------------
    # Constructor for the BaseRangeCountHistogram class.
    # --------------------------------------------------------------------------------------------- 

    def __init__(self, name, port, csv_path = "", data_column = None):
        self.server = get_server(name, client_type="vue2")
        self.port = port
        self.state, self.ctrl = self.server.state, self.server.controller

        if csv_path and not data_column:
            raise ValueError("data_column argument is required when csv_path is provided")

        self.state.data_column = data_column if data_column else "Area"
        self.state.bins = 10
        self.state.subset_items = []
        self.state.range_item = []
        self.df = pd.DataFrame()
        self.html_figure = None
        self.data = []

        self.state.subset_config = [
            {"text": "Index", "value": "index"},
            {"text": "Name", "value": "name"},
            {"text": "Threshold", "value": "threshold"},
            {"text": "Actions", "value": "actions"},
        ]

        self.table = {
            "headers": ("subset_config", self.state.subset_config),
            "items": ("subset_items", self.state.subset_items),
            "search": ("query", ""),
            "classes": "elevation-1 ma-4",
            "multi_sort": True,
            "dense": True,
            "items_per_page": 5,
        }

        self.state.subset_range = [
            {"text": "Index", "value": "index"},
            {"text": "Name", "value": "name"},
            {"text": "Range", "value": "range"},
            {"text":"Count","value":"count"},
        ]

        self.table_subset_range = {
            "headers": ("subset_range", self.state.subset_range),
            "items": ("range_item", self.state.range_item),
            "classes": "elevation-1 ma-4",
            "multi_sort": True,
            "dense": True,
            "items_per_page": 5,
        }

        if csv_path:
            if not data_column:
                raise ValueError("data_column argument is required when csv_path is provided")
            self.df = pd.read_csv(csv_path)
            self.data = self.df[data_column].values

        self.register_triggers()
        self.render_ui_layout()

    # ---------------------------------------------------------------------------------------------
    # Method to get the figure size (static method).
    # --------------------------------------------------------------------------------------------- 

    def get_figure_size(self):
        return {"figsize": (10, 6), "dpi": 80}
    
    # ---------------------------------------------------------------------------------------------
    # Method to update the plot.
    # ---------------------------------------------------------------------------------------------

    def update_plot(self, extra_lines=None):
        plt.close('all')
        fig, ax = plt.subplots(**self.get_figure_size())

        ax.hist(self.data, bins=self.state.bins, edgecolor='black')

        y_limits = ax.get_ylim() 
        colors= ['blue','green','red','orange','black']
        if extra_lines: 
            for i,line in enumerate(extra_lines):
                line_color = colors[i % len(colors)]
                ax.plot([line, line], y_limits, color=line_color, linestyle='--')

        ax.set_xlabel('OoD Scores')
        ax.set_ylabel('Frequency')
        return fig
    
    # ---------------------------------------------------------------------------------------------
    # Method to update the range count.
    # ---------------------------------------------------------------------------------------------
    
    def update_range_count(self):
        self.state.range_item.clear() 
        for i, item in enumerate(self.state.subset_items):
            if i == 0:
                start = float(0) 
            else:
                start = self.state.subset_items[i - 1]["threshold"]
            end = item["threshold"]

            count_values = self.data[(self.data > start) & (self.data <= end)] if start < end else np.array([])

            ranges = {
                "index": i + 1,
                "name": f"Subset{i + 1}",
                "range": f"({float(start)} , {float(end)}]",
                "count": f"{len(count_values)}"
            }

            self.state.range_item.append(ranges)

        if self.state.subset_items:
            last_threshold = self.state.subset_items[-1]["threshold"]
            remaining_values = self.data[self.data > last_threshold]
            remaining_range = {
                "index": len(self.state.subset_items) + 1,
                "name": f"Subset{len(self.state.subset_items) + 1} (Remaining)",
                "range": f"({float(last_threshold)} ,{max(self.data)} ]",
                "count": f"{len(remaining_values)}"
            }
            self.state.range_item.append(remaining_range)

        print("Ranges: ", self.state.range_item)
        self.server.state.dirty("range_item")  

    # ---------------------------------------------------------------------------------------------
    # Method to update the threshold.
    # ---------------------------------------------------------------------------------------------

    def update_threshold(self, index, new_threshold): 
        
        new_threshold = float(new_threshold) 

        for i, item in enumerate(self.state.subset_items):
            if item["index"] == index:
            
                if i > 0:
                    prev_item_threshold = self.state.subset_items[i - 1]["threshold"]
                    
                    if new_threshold <= float(prev_item_threshold):
                        print(f"Threshold should be greater than previous threshold value: {prev_item_threshold}")
                        return  

                if i < len(self.state.subset_items) - 1:
                    next_item_threshold = self.state.subset_items[i + 1]["threshold"]
                    if new_threshold >= float(next_item_threshold):
                        print(f"Threshold should be less than the next threshold value: {next_item_threshold}")
                        return  

                item["threshold"] = new_threshold
                break

        self.update_range_count() 
        self.update_chart() 

    # ---------------------------------------------------------------------------------------------
    # Method to add a subset.
    # ---------------------------------------------------------------------------------------------
   
    def add_subset(self):
        original_val=[1,2,3,4]

        if self.state.subset_items:
            last_threshold = self.state.subset_items[-1]["threshold"]
            new_line = last_threshold+1
        else:
            new_line = original_val[0]
        
        new_item = {"index": len(self.state.subset_items) + 1, "name": f"Subset{len(self.state.subset_items) + 1}", "threshold": float(new_line), "actions": "Remove"}
        

        self.state.subset_items.append(new_item)

        self.server.state.dirty("subset_items") 
        # self.ctrl.dirty("subset_items")

        print("Subset Items added:", self.state.subset_items)
        self.update_range_count()

    # ---------------------------------------------------------------------------------------------
    # Method to remove a subset.
    # ---------------------------------------------------------------------------------------------

    def remove_subset(self, index):
        if(index=="0"):
            self.state.subset_items.pop(index)
            self.state.range_item.pop(index)
        
        if 0 < index <= len(self.state.subset_items):  
            self.state.subset_items.pop(index-1)  
            self.state.range_item.pop(index-1)

            for i, item in enumerate(self.state.subset_items): 
                item["index"] = i + 1  
                item["name"]=f"Subset{i+1}" 
                
            self.server.state.dirty("subset_items") 
            # self.ctrl.dirty("subset_items")

            for i, item in enumerate(self.state.range_item): 
                item["index"] = i + 1 
                item["name"]=f"Subset{i+1}"

            self.update_range_count()

            self.server.state.dirty("range_item")
            # self.ctrl.dirty("subset_items")

            print(f"Subset at index {index} removed")
    
    # ---------------------------------------------------------------------------------------------
    # State change handler to update the chart.
    # ---------------------------------------------------------------------------------------------

    @change("subset_items")
    def update_chart(self, **trame_scripts):
        extra_lines = [float(item["threshold"]) for item in self.state.subset_items]
        fig = self.update_plot(extra_lines)
        self.html_figure.update(fig)

    # ---------------------------------------------------------------------------------------------
    # Method to register triggers with the controller
    # ---------------------------------------------------------------------------------------------

    def register_triggers(self):
        self.ctrl.trigger("update_threshold")(self.update_threshold_t)
        self.ctrl.trigger("remove_subset")(self.remove_subset_t)

    # ---------------------------------------------------------------------------------------------
    # Trigger to update threshold.
    # ---------------------------------------------------------------------------------------------

    def update_threshold_t(self, index, new_threshold):
        self.update_threshold(index, new_threshold)

    # ---------------------------------------------------------------------------------------------
    # Trigger to remove a subset.
    # ---------------------------------------------------------------------------------------------

    def remove_subset_t(self, index):
        self.remove_subset(index)

    # ---------------------------------------------------------------------------------------------
    # UI layout
    # ---------------------------------------------------------------------------------------------

    def render_ui_layout(self):
        with SinglePageLayout(self.server) as layout:
            layout.title.set_text(self.server.name)

            with layout.toolbar:
                vuetify.VSpacer()

            with layout.content:
                with vuetify.VContainer(fluid=True, classes="d-flex flex-row"):
                    with vuetify.VCol(cols="8"):
                        with vuetify.VRow():
                            self.html_figure = matplotlib.Figure(style="position: relative")
                            self.ctrl.update_plot = self.html_figure.update

                            vuetify.VDataTable(**self.table_subset_range)
                            
                    with vuetify.VCol(cols="4"):
                        with vuetify.VRow(classes="justify-center"):
                            
                                vuetify.VIcon("mdi-plus", 
                                                color="blue", 
                                                click=self.add_subset, 
                                                style="border: 2px solid blue; border-radius: 50%; padding: 8px;",
                                                classes="d-flex align-center justify-center",)
                        
                        with vuetify.VRow(classes="justify-center"):
                            with vuetify.VDataTable(**self.table):
                                with vuetify.Template(
                                actions="{ item }",
                                __properties=[("actions", "v-slot:item.actions")],
                                ):
                                    vuetify.VIcon("mdi-delete", color="red", click="trigger('remove_subset', [item.index])")
                                    
                                with vuetify.Template(
                                threshold="{ item }",
                                __properties=[("threshold", "v-slot:item.threshold")],
                                ):
                                    vuetify.VTextField(
                                        v_model=("item.threshold",), 
                                        type="number",
                                        dense=True,
                                        hide_details=True,
                                        change="trigger('update_threshold', [item.index, item.threshold])",
                                        classes="d-flex align-center",
                                        step=0.1,
                                    )

    # ---------------------------------------------------------------------------------------------
    # Method to start a new server (main). Not to be used in a multi-process environment
    # ---------------------------------------------------------------------------------------------

    @abstractmethod   
    def start_server_immediately(self):
        print(f"Starting Server_Manager at http://localhost:{self.port}/index.html")
        self.server.start(exec_mode="main", port=self.port)

    # ---------------------------------------------------------------------------------------------
    # Method to start a new server (async). To be used in a multi-process environment
    # ---------------------------------------------------------------------------------------------

    @abstractmethod   
    async def start_server_async(self):
        print(f"Starting Server_Manager at http://localhost:{self.port}/index.html")
        return await self.server.start(exec_mode="task", port=self.port)

    # ---------------------------------------------------------------------------------------------
    # Method to kill a server. Child/derived classes should implement this method
    # ---------------------------------------------------------------------------------------------

    @abstractmethod
    def kill_server(self):
        pass

    # ---------------------------------------------------------------------------------------------
    # Method to input data. Child/derived classes should implement this method
    # ---------------------------------------------------------------------------------------------

    @abstractmethod
    def input_data(self):
        pass

    # ---------------------------------------------------------------------------------------------
    # Method to fetch data. Child/derived classes should implement this method
    # ---------------------------------------------------------------------------------------------

    @abstractmethod
    def fetch_data(self):
        pass

# ----------------------------------------------------------------------------- 
# Main (Guard) # Commented out for import. Uncomment for testing
# ----------------------------------------------------------------------------- 
'''
if __name__ == "__main__":
    server = BaseRangeCountHistogram("Test", 1235, "/home/demo/neurobazaar/MaxSlices_newMode_Manuf_Int.csv", "Area") # Testing passed
    # server = BaseRangeCountHistogram("Test", 1235, "/home/demo/neurobazaar/MaxSlices_newMode_Manuf_Int.csv") # Testing passed 
    # server = BaseRangeCountHistogram("Test", 1235) # Testing passed 
    fig = server.update_plot()
    server.html_figure.update(fig)
    server.start_server_immediately()
'''