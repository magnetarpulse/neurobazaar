# Core libraries for data processing
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import os

# Core libraries for rendering
from trame.app import get_server
from trame.ui.vuetify import SinglePageLayout
from trame.widgets import vuetify, matplotlib, html
from trame.decorators import TrameApp, change
from trame.tools.app import Path
from flask import send_from_directory
from trame.assets.local import LocalFileManager
from pathlib import Path
import trame
import base64

# Base class for the histogram application
from abc import abstractmethod

# Import Flask for serving images
from flask import Flask, send_from_directory

## ================================================================== ## 
## Visualization service. Finds the counts in ranges. The base class. ##         
## ================================================================== ##

@TrameApp()
class BaseRangeCountHistogram:

    # ---------------------------------------------------------------------------------------------
    # Constructor for the BaseRangeCountHistogram class.
    # --------------------------------------------------------------------------------------------- 

    def __init__(self, name, port, csv_path = "", collection_path="",max_slices="",data_column = None, item_column=None,node_id=None):
        self.server = get_server(name, client_type="vue2")
        self.port = port
        self.state, self.ctrl = self.server.state, self.server.controller
        self.file_manager = LocalFileManager(base_path="/home/cc/neurobazaar/neurobazaar/lidc_pixConvImg")
        self.server.state.image_cache = {}  # Add this line
        self.image_cache = {}
        self.server.state.image_paths = []  # Store image paths instead of base64 data

        # Change this line to use port 5000 for image serving
        self.image_server_url = "http://localhost:5000/images"
        
        if csv_path and not data_column:
            raise ValueError("data_column argument is required when csv_path is provided")

        if not collection_path:
            raise ValueError("No collection to map") 

        if not max_slices:
            raise ValueError("No collection for max slices")

        self.state.data_column = data_column if data_column else "Log_Loss_ALL"
        self.state.item_column= item_column if item_column else "imageSOP_UID"
        self.state.node_id= node_id if node_id else "noduleID"

        self.csv_path=csv_path
        self.collection_path=collection_path
        self.max_slices=max_slices
        self.state.bins = 10
        self.state.subset_items = []
        self.state.range_item = []
        self.state.data_items=[]
        self.image_paths=[]
        self.final_path=[]
        self.collection_images=[]
        self.df = pd.DataFrame()
        self.html_figure = None
        self.data = []
        self.state.first_nodule_image = ""
        self.state.image_base_url = "http://localhost:5000/images"
        self.state.nodule_images = []  # List to store all nodule image paths

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

        self.state.data_headers = [
            {"text": "Data_Item", "value": "data_item"},
        ]

        self.table_data_items = {
            "headers": ("headers", self.state.data_headers),
            "items": ("data_items", self.state.data_items),
            "classes": "elevation-1 ma-4",
            "multi_sort": True,
            "dense": False,
            "hide_default_footer":True,
            "hide_default_header": True,
            "style":"overflow-x: auto;max-height: 400px;",
    
        }



        if csv_path:
            if collection_path:
                if not data_column:
                    raise ValueError("data_column argument is required when csv_path is provided")
                self.df = pd.read_csv(csv_path)
                self.data = self.df[data_column].values
                self.item_list=self.df[item_column].tolist()
                self.nodule_ids=self.df[node_id]
                
           
        self.check_collection(collection_path)
        self.mapping(csv_path,self.image_paths)
        self.check_node_id(max_slices,csv_path,self.nodule_ids)
        #print(self.collection_images)
        
        self.register_triggers()
        self.render_ui_layout()

        # Add this line to set up the static file serving
        self.setup_static_directory()

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

        ax.hist(self.data, bins=self.state.bins, edgecolor='black',color=(70/255, 130/255, 180/255))
        

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

        #print("Ranges: ", self.state.range_item)
        self.server.state.dirty("range_item")  



    # ---------------------------------------------------------------------------------------------
    # Method to update the threshold.
    # ---------------------------------------------------------------------------------------------

    def update_threshold(self, index, new_threshold): 
        
        new_threshold = float(new_threshold) 
        max_value = np.max(self.data)

        if new_threshold<=max_value:
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
            self.display_data()
            self.insert_row_above_data() 
            



    # ---------------------------------------------------------------------------------------------
    # Method to display the subset data items
    # ---------------------------------------------------------------------------------------------

    def display_data(self):
        self.state.data_items.clear()
        self.state.nodule_images.clear()
        first_image_set = False  # Flag to ensure we only set the first image once

        for i, item in enumerate(self.state.subset_items):
            if i == 0:
                start = float(0)  
            else:
                start = self.state.subset_items[i - 1]["threshold"]
            end = item["threshold"]

            if start < end:
                mask = (self.data > start) & (self.data <= end)

                # Get the UIDs that match the mask
                filtered_uids = [self.item_list[j] for j in range(len(self.data)) if mask[j]]
                
                data_values = [
                    path for uid in filtered_uids 
                    for path in self.final_path if uid in path
                ]

                
                filtered_nodule_ids = [self.nodule_ids[j] for j in range(len(self.data)) if mask[j]]
                filtered_nodule_ids_str = [str(id) for id in filtered_nodule_ids]

                nodule_ids = [
                    path for path in self.collection_images 
                    if any(str(id) in path for id in filtered_nodule_ids_str)
                ]

                # Set the first nodule image as the source for the img tag
                if nodule_ids and not first_image_set:
                    self.state.first_nodule_image = Path(nodule_ids[0]).name  # Just the filename
                    self.state.first_nodule_image = f"{self.image_server_url}/{self.state.first_nodule_image}"
                    first_image_set = True
                    print(f"First nodule image set to: {self.state.first_nodule_image}")  # Debug print

                for nodule_id in nodule_ids:
                    image_name = Path(nodule_id).name
                    image_name = f"{self.image_server_url}/{image_name}"
                    self.state.nodule_images.append(image_name)
            
            else:
                data_values = []
                nodule_ids=[]
            

            items = {
                "index": i + 1,
                "name": f"Subset{i + 1}",
                "range": f"({float(start)} , {float(end)}]",
                "data_item": f"{data_values}",
                "nodule_ids": f"{nodule_ids}"
            }

            self.state.data_items.append(items)
            
            # Add a values for remaining items
        if self.state.subset_items:
            last_threshold = self.state.subset_items[-1]["threshold"]
            max_value = np.max(self.data)

            if last_threshold<= max_value:
                
                remaining_mask = (self.data > last_threshold) & (self.data <= max_value)

                remaining_uids = [self.item_list[j] for j in range(len(self.data)) if remaining_mask[j]]

                remaining_values = [
                    path for uid in remaining_uids 
                    for path in self.final_path if uid in path
                ]

                remaining_filtered_ids = [self.nodule_ids[j] for j in range(len(self.data)) if remaining_mask[j]]
                filtered_remaining_nodule_ids_str = [str(id) for id in remaining_filtered_ids]

                remaining_nodule_ids = [
                    path for path in self.collection_images 
                    if any(str(id) in path for id in filtered_remaining_nodule_ids_str)
                ]

                for nodule_id in remaining_nodule_ids:
                    image_name = Path(nodule_id).name
                    self.state.nodule_images.append(image_name)
            
                remaining_item = {
                    "index": len(self.state.subset_items) + 1,
                    "name": f"Subset{len(self.state.subset_items) + 1} (Remaining)",
                    "range": f"({float(last_threshold)} , {max_value}]",
                    "data_item": f"{remaining_values}",
                    "nodule_ids":f"{remaining_nodule_ids}"
                }

                self.state.data_items.append(remaining_item)

            server.state.dirty("data_items")  # Refresh the state of the server to update the data table
            

        # After the loop, check if an image was set
        if not first_image_set:
            print("Warning: No nodule image was set. Check your data and filters.")

        # Force a refresh of the state
        self.server.state.dirty("first_nodule_image")
        self.server.state.dirty("nodule_images")

    # ---------------------------------------------------------------------------------------------
    # Method to add a threshold row before data row
    # ---------------------------------------------------------------------------------------------

    def insert_row_above_data(self):
        updated_data_items=[]
        
        for item in self.state.data_items:
            new_row={"data_item":item['range'],}
            nodule_id={"data_item":item['nodule_ids'],}
        

            updated_data_items.append(new_row)
            updated_data_items.append(item)
            updated_data_items.append(nodule_id)

        self.state.data_items=updated_data_items
        server.state.dirty("data_items")
     
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

        #print("Subset Items added:", self.state.subset_items)
        self.update_range_count()
        self.display_data()
        self.insert_row_above_data()

    # ---------------------------------------------------------------------------------------------
    # Method to remove a subset.
    # ---------------------------------------------------------------------------------------------

    def remove_subset(self, index):
        if(index=="0"):
            self.state.subset_items.pop(index)
            self.state.range_item.pop(index)
            self.display_data()
            self.insert_row_above_data()

        
        if 0 < index <= len(self.state.subset_items):  
            self.state.subset_items.pop(index-1)  
            self.state.range_item.pop(index-1)

            for i, item in enumerate(self.state.subset_items): 
                item["index"] = i + 1  
                item["name"]=f"Subset{i+1}" 
                
            self.server.state.dirty("subset_items") 
          
            for i, item in enumerate(self.state.range_item): 
                item["index"] = i + 1 
                item["name"]=f"Subset{i+1}"

            self.update_range_count()

            self.server.state.dirty("range_item")
            
            self.display_data()
            self.server.state.dirty("data_items")
            self.insert_row_above_data()
             
            #(f"Subset at index {index} removed")


    # ---------------------------------------------------------------------------------------------
    # Getting path for each .dcm file 
    # ---------------------------------------------------------------------------------------------

    def check_collection(self, collection_path):
        if os.path.exists(collection_path):
            if os.path.isdir(collection_path):
                for name in os.listdir(collection_path):
                    full_path= os.path.join(collection_path, name)
                    if os.path.isdir(full_path):
                        self.check_collection(full_path)
                    else:
                        if full_path.endswith('.dcm'):
                            self.image_paths.append(full_path)
                            

                            

    # ---------------------------------------------------------------------------------------------
    # Mapping records from .csv to the collection folder
    # ---------------------------------------------------------------------------------------------

    def mapping(self,csv_path,image_paths):
        if not os.path.isfile(csv_path):
            print(f"CSV file does not exist at the path: {csv_path}")
            return

        column_1='StudyInstanceUID'
        column_2='SeriesInstanceUid'
        file_name='imageSOP_UID'

        studies = self.df[column_1].values
        series = self.df[column_2].values
        files= self.df[file_name].values

        for dcm_path in self.image_paths:
            parts=dcm_path.split(os.sep)
            
            if len(parts)>=3:
                dcm_file=os.path.basename(dcm_path)
                if dcm_file.endswith(".dcm"):
                    dcm_file = os.path.splitext(dcm_file)[0]
                second_folder=parts[-2]
                first_folder = parts[-3]
                
                for i, (study_uid, series_uid, file_uid) in enumerate(zip(studies, series, files)):
                    # Compare first, second folder and file names
                    if study_uid == first_folder and series_uid == second_folder and file_uid == dcm_file:
                        #path = f"{study_uid}/{series_uid}/{file_uid}.dcm"
                        self.final_path.append(dcm_path)
        
        #print(f"Match found:{self.final_path}")
        #print(f"CSV path: {csv_path}")
        #print(f"Counted DICOM paths:{len(self.image_paths)}")
        
    
    # ---------------------------------------------------------------------------------------------
    # Mapping Max_slices collection with csv file
    # ---------------------------------------------------------------------------------------------


    def check_node_id(self,img_collection,csv_path,node_id):
        if os.path.exists(img_collection):
            if os.path.exists(csv_path):
                if os.path.isdir(img_collection):
                    for file in os.listdir(img_collection):
                        file_path= os.path.join(img_collection, file)
                        if os.path.isdir(file_path):
                            self.check_node_id(file_path,csv_path,node_id)
                        else:
                            png_file=os.path.basename(file_path)
                            if png_file.endswith('.jpeg') or png_file.endswith('.png') or png_file.endswith('.jpg'):
                                img_name = os.path.splitext(png_file)[0]
                                for i in node_id:
                                    if img_name==str(i):
                                        self.collection_images.append(file_path)
    
    
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

            with layout.content:
                with vuetify.VContainer(fluid=True, classes="d-flex flex-row"):
                    # Left Column for the figure and data 
                    with vuetify.VCol(cols="8"):
                        with vuetify.VRow():
                            vuetify.VSubheader("Interactive Figure:",
                            style="font-size: 20px;font-weight: bold;color: rgb(0, 71, 171);")

                            # Matplotlib Figure
                            self.html_figure = matplotlib.Figure(style="position: relative")
                            self.ctrl.update_plot = self.html_figure.update

                        with vuetify.VRow():
                            vuetify.VSubheader("Data Items:",
                            style="font-size: 20px;font-weight: bold;color: rgb(0, 71, 171); margin-top: 40px;")
                        
                        # Add the image here
                        with vuetify.VRow():
                            with vuetify.VContainer(fluid=True):
                                with vuetify.VRow(align="center", justify="center"):
                                    html.Img(
                                        src=("first_nodule_image", lambda name: f"http://localhost:5000/images/{name}"),
                                        alt="First Nodule Image",
                                        style="max-width: 100%; max-height: 400px; object-fit: contain;",
                                    )

                        with vuetify.VRow():  
                            with vuetify.VContainer(style="overflow-x: auto; white-space: nowrap;"):
                                
                                with vuetify.VDataTable(**self.table_data_items):
                                    with vuetify.Template():
       
                                        with html.Tr():
                                            for value in self.state.data_items:
                                                html.Td(value, classes="pa-4 text-center")
                                                
                                                        
                                
                    # Right Column for the dynamic grid tables for configuration and view
                    with vuetify.VCol(cols="4"):

                        with vuetify.VRow():
                            vuetify.VSubheader("Threshold Config:",
                            style="font-size: 16px;font-weight: bold;color: rgb(8, 24, 168);")
                        
                        with vuetify.VRow(classes="justify-center"):
                            vuetify.VDataTable(**self.table_subset_range)

                        with vuetify.VRow():
                            vuetify.VSubheader("Threshold View:",
                            style="font-size: 16px;font-weight: bold;color: rgb(8, 24, 168);margin-top: 70px;")

                        with vuetify.VRow(classes="justify-center"):
                            
                                vuetify.VIcon("mdi-plus", 
                                                color="blue", 
                                                click=self.add_subset, 
                                                style="border: 2px solid blue; border-radius: 50%; padding: 8px; color: rgb(8, 24, 168);",
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

                        with vuetify.VRow():
                            with vuetify.VContainer(fluid=True, style="max-height: 400px; overflow-y: auto;"):
                                with vuetify.VRow(align="center", justify="center"):
                                    with vuetify.VCarousel(
                                        v_model=("active_image", 0),
                                        height="400",
                                        hide_delimiter_background=True,
                                        delimiter_icon="mdi-minus",
                                        show_arrows=True,
                                    ):
                                        with vuetify.Template(v_for="(image, index) in nodule_images", v_slot="{ item }"):
                                            with vuetify.VCarouselItem(key="index"):
                                                html.Img(
                                                    src=("image", lambda name: f"{self.state.image_base_url}/{name}"),
                                                    alt="Nodule Image",
                                                    style="max-width: 100%; max-height: 400px; object-fit: contain;",
                                                )

    # ---------------------------------------------------------------------------------------------
    # Method to start a new server (main). Not to be used in a multi-process environment
    # ---------------------------------------------------------------------------------------------

    @abstractmethod   
    def start_server_immediately(self):
        print(f"Starting Server_Manager at http://localhost:{self.port}/index.html")
        self.server.static_url_path = "/assets"
        self.server.static_folder = "/home/cc/neurobazaar/neurobazaar/lidc_pixConvImg"
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

    def setup_static_directory(self):
        image_dir = Path("/home/cc/neurobazaar/neurobazaar/lidc_pixConvImg")
        if image_dir.exists() and image_dir.is_dir():
            self.server.state.image_paths = [
                str(file) for file in image_dir.iterdir() 
                if file.suffix.lower() in ['.png', '.jpg', '.jpeg']
            ]
            print(f"Static directory set up: {image_dir}")
            print(f"Number of images found: {len(self.server.state.image_paths)}")
        else:
            print(f"Warning: Directory {image_dir} does not exist or is not a directory")
        
        self.server.state.dirty("image_paths")

        # Set up Flask app for serving images
        app = Flask(__name__)

        @app.route('/images/<path:filename>')
        def serve_image(filename):
            return send_from_directory(image_dir, filename)

        # Run Flask app in a separate thread
        import threading
        threading.Thread(target=lambda: app.run(port=5000, debug=False, use_reloader=False)).start()

# ----------------------------------------------------------------------------- 
# Main (Guard)
# ----------------------------------------------------------------------------- 

if __name__ == "__main__":
    
    server = BaseRangeCountHistogram("Ood Analyzer using Trame-Matplotlib", 1235, "/home/cc/neurobazaar/neurobazaar/MaxSlices_wOoDScore.csv", "/home/cc/neurobazaar/neurobazaar/LIDC_Dataset", "/home/cc/neurobazaar/neurobazaar/lidc_pixConvImg", "Log_Loss_ALL","imageSOP_UID","noduleID")
    server.start_server_immediately()