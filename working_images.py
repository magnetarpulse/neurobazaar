# Core libraries for data processing
import os
import requests
import numpy as np # type: ignore
import pandas as pd # type: ignore
import matplotlib.pyplot as plt  # type: ignore
import pydicom # type: ignore
from PIL import Image # type: ignore


# Core libraries for rendering
from trame.app import get_server # type: ignore
from trame.ui.vuetify import SinglePageLayout # type: ignore
from trame.widgets import vuetify, matplotlib, html # type: ignore
from trame.decorators import TrameApp, change # type: ignore
from trame.tools.app import Path # type: ignore
from pathlib import Path
from django.conf import settings # type: ignore
from django.core.wsgi import get_wsgi_application # type: ignore
 
# Base class for the histogram application
from abc import abstractmethod

# Set up Django environment
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "neurobazaar.settings")  # replace with your project name
application = get_wsgi_application()

## ================================================================== ## 
## Visualization service.         
## ================================================================== ##

@TrameApp()
class BaseOoDHistogram:

    # ---------------------------------------------------------------------------------------------
    # Constructor for the BaseOoDHistogram class.
    # --------------------------------------------------------------------------------------------- 

    def __init__(self, name, port, csv_path = "", collection_path="",max_slices="",data_column = None, item_column=None,node_id=None):
        self.server = get_server(name, client_type="vue2")
        self.port = port
        self.state, self.ctrl = self.server.state, self.server.controller

        csv_path = os.path.join(settings.MEDIA_ROOT, csv_path)
        #print(csv_path)
        
        self.state.image_base_url= os.path.join(settings.MEDIA_ROOT, max_slices)  # Folder containing images /media/lidc_pixConvImg
        #print(self.state.image_base_url)
        
        self.state.collection_base_url= os.path.join(settings.MEDIA_ROOT, collection_path)  # Folder containing collections
        #print(self.state.collection_base_url)

        self.state.images_list=[]
        
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
        self.collection_path=self.state.collection_base_url
        self.max_slices=self.state.image_base_url
        self.state.bins = 10
        self.state.subset_items = []
        self.state.range_item = []
        self.state.data_items=[]
        self.state.image_paths=[]
        self.state.final_path=[]
        self.state.collection_images=[]
        self.state.pixel_array=[]
        self.state.dicom_images=[]
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

        self.state.data_headers = [
            {"text": "Range", "value": "range"},
            {"text": "Data_Item", "value": "data_item"},
            {"text": "Nodule_IDs", "value": "nodule_ids"},  
            {"text": "Image_Row", "value": "image_row"},    
            {"text": "Dicom_Images", "value": "dicom_imgs"},
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



        if self.csv_path:
            if self.collection_path and self.max_slices:
                if not data_column:
                    raise ValueError("data_column argument is required when csv_path is provided")
                self.df = pd.read_csv(csv_path)
                self.data = self.df[data_column].values
                self.item_list=self.df[item_column].tolist()
                self.nodule_ids=self.df[node_id]
                
                
        self.check_collection(self.collection_path)
        self.mapping(csv_path,self.state.image_paths)
        self.original_images(self.state.file_path)
        self.check_node_id(self.max_slices,self.csv_path,self.nodule_ids)
        self.fetch_images()
        

        self.register_triggers()
        self.render_ui_layout()
        self.update_range_count()

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
             
            
            

    # ---------------------------------------------------------------------------------------------
    # Method to display the subset data items
    # ---------------------------------------------------------------------------------------------

    def display_data(self):
        self.state.data_items.clear()

        for i, item in enumerate(self.state.subset_items):
            if i == 0:
                start = float(0)  
            else:
                start = self.state.subset_items[i - 1]["threshold"]
            
            end = item["threshold"]

            if start < end:
                mask = (self.data > start) & (self.data <= end)

                # Get the SOP UIDs that match the mask
                filtered_uids = [self.item_list[j] for j in range(len(self.data)) if mask[j]]
                
                data_values = [
                    path for uid in filtered_uids 
                    for path in self.state.final_path if uid in path
                ]

                
                filtered_nodule_ids = [self.nodule_ids[j] for j in range(len(self.data)) if mask[j]]
                filtered_nodule_ids_str = [str(id) for id in filtered_nodule_ids]

                nodule_ids = [
                    path for path in self.state.collection_images 
                    if any(str(id) in path for id in filtered_nodule_ids_str)
                ]

                nodule_ids = sorted(nodule_ids, key=lambda url: int(os.path.splitext(os.path.basename(url))[0])) # to sort nodule ids in ascending order

                dicom_images_list=[]
                for image in self.state.dicom_images:
                    base_name, ext = os.path.splitext(image)
                    if any(uid in base_name for uid in filtered_uids):
                        #print(f"Image found: {base_name}")
                        dicom_images_list.append(f"{base_name}.png")
                

                imgs={}
                for id in nodule_ids:
                    ss= f"{Path(id).name}"
                    base, ext = os.path.splitext(ss)
                    for item in self.state.images_list:
                        strip=Path(item).name
                        base_img, ext = os.path.splitext(strip)
                        if base==base_img:
                            imgs[base]=item
                
                # Map DICOM images to nodule IDs using the DataFrame
                base_names_list=[]
                for i in dicom_images_list:
                    base_name = os.path.splitext(os.path.basename(i))[0]
                    base_names_list.append(base_name)
                
                results = self.df[self.df[self.state.item_column].isin(base_names_list)][[self.state.node_id, self.state.item_column]]
                
                # dictionary to map node IDs to their respective image paths in sorted order
                id_to_image_mapping = {row[self.state.node_id]: row[self.state.item_column] for _, row in results.iterrows()}
               
                # Retrieve images in the sorted order of nodule_ids
                final_dicom_images={}
                for ni, sop in id_to_image_mapping.items():
                    for image in dicom_images_list:
                        base_name = os.path.splitext(os.path.basename(image))[0]
                        if base_name == sop:
                            final_dicom_images[ni]=image
                

            else:
                data_values = []
                nodule_ids=[]
            

            items = {
                #"index": i + 1,
                #"name": f"Subset{i + 1}",
                "range": f"Range = ({float(start)} , {float(end)}]",
                "data_item": f"CollectionPath = {data_values}",
                "nodule_ids": [f"{Path(nodule_id).name}" for nodule_id in nodule_ids],
                "image_row": imgs,
                "dicom_imgs": final_dicom_images
            }

            self.state.data_items.append(items)
            
        # Add a values for remaining items
        if self.state.subset_items:
            last_threshold = self.state.subset_items[-1]["threshold"]
            #max_value = np.max(self.data)
            max_value = np.nanmax(self.data)

            if last_threshold<= max_value:
                
                remaining_mask = (self.data > last_threshold) & (self.data <= max_value)

                # Get the SOP UIDs that match the mask
                remaining_uids = [self.item_list[j] for j in range(len(self.data)) if remaining_mask[j]]

                remaining_values = [
                    path for uid in remaining_uids 
                    for path in self.state.final_path if uid in path
                ]

                remaining_filtered_ids = [self.nodule_ids[j] for j in range(len(self.data)) if remaining_mask[j]]
                filtered_remaining_nodule_ids_str = [str(id) for id in remaining_filtered_ids]

                remaining_nodule_ids = [
                    path for path in self.state.collection_images 
                    if any(str(id) in path for id in filtered_remaining_nodule_ids_str)
                ]

                remaining_nodule_ids = sorted(remaining_nodule_ids, key=lambda url: int(os.path.splitext(os.path.basename(url))[0])) # to sort nodule ids in ascending order

                dicom_rem_images_list=[]
                for image in self.state.dicom_images:
                    base_name, ext = os.path.splitext(image)
                    if any(uid in base_name for uid in remaining_uids):
                        dicom_rem_images_list.append(f"{base_name}.png")
                
                

                rem_imgs={}
                for id in remaining_nodule_ids:
                    ss= f"{Path(id).name}"
                    
                    for item in self.state.images_list:
                        strip=Path(item).name
                        if ss==strip:
                            rem_imgs[id]=item
                
            
                # Map DICOM images to nodule IDs using the DataFrame
                base_names_list=[]
                for i in dicom_rem_images_list:
                    base_name = os.path.splitext(os.path.basename(i))[0]
                    base_names_list.append(base_name)
                
                results = self.df[self.df[self.state.item_column].isin(base_names_list)][[self.state.node_id, self.state.item_column]]
                
                # dictionary to map node IDs to their respective image paths in sorted order
                id_to_image_mapping = {row[self.state.node_id]: row[self.state.item_column] for _, row in results.iterrows()}
               
                # Retrieve images in the sorted order of nodule_ids
                final_dicom_rem_images={}
                for ni, sop in id_to_image_mapping.items():
                    for image in dicom_rem_images_list:
                        base_name = os.path.splitext(os.path.basename(image))[0]
                        if base_name == sop:
                            final_dicom_rem_images[ni]=image

                remaining_item = {
                    #"index": len(self.state.subset_items) + 1,
                    #"name": f"Subset{len(self.state.subset_items) + 1} (Remaining)",
                    "range": f"Range = ({float(last_threshold)} , {max_value}]",
                    "data_item": f"CollectionPath= {remaining_values}",
                    "nodule_ids": [f"{Path(nodule_id).name}" for nodule_id in remaining_nodule_ids], 
                    "image_row": rem_imgs,
                    "dicom_imgs": final_dicom_rem_images

                }

                self.state.data_items.append(remaining_item)

            #print(self.state.data_items)
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
        
        #print("Subset Items added:", self.state.subset_items)
        self.update_range_count()
        self.display_data()
        

    # ---------------------------------------------------------------------------------------------
    # Method to remove a subset.
    # ---------------------------------------------------------------------------------------------

    def remove_subset(self, index):
        if(index=="0"):
            self.state.subset_items.pop(index)
            self.state.range_item.pop(index)
            self.display_data()

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
            #(f"Subset at index {index} removed")


    # ---------------------------------------------------------------------------------------------
    # Method to show image.
    # ---------------------------------------------------------------------------------------------
    def show_image(self, url):
        print(f"Show image: {url}")
        

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
                            self.state.image_paths.append(full_path)
                           

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

        for dcm_path in self.state.image_paths:
            parts=dcm_path.split(os.sep)
            
            if len(parts)>=3:
                dcm_file=os.path.basename(dcm_path)
                if dcm_file.endswith(".dcm"):
                    dcm_file = os.path.splitext(dcm_file)[0]
                second_folder=parts[-2]
                first_folder = parts[-3]
                
                for i, (study_uid, series_uid, file_uid) in enumerate(zip(studies, series, files)):
                    if study_uid == first_folder and series_uid == second_folder and file_uid == dcm_file:
                        #path = f"{study_uid}/{series_uid}/{file_uid}.dcm"
                        self.state.final_path.append(dcm_path)

    # ---------------------------------------------------------------------------------------------
    # Displaying Pixel Array for original images from Collection
    # ---------------------------------------------------------------------------------------------

    def original_images(self,final_path):
        
        dicom_folder = "/home/cc/neurobazaar/neurobazaar/media/dicom_images"  # Folder where images will be saved
        
        if not os.path.exists(dicom_folder):
            os.makedirs(dicom_folder)
        
        for path in self.state.final_path:
            meta_data_path = pydicom.dcmread(f"{path}")
            pixel_array = meta_data_path.pixel_array
            img = Image.fromarray(pixel_array)
            self.state.pixel_array.append(pixel_array)
            base_name, ext = os.path.splitext(path)
            base_name= base_name.split('/').pop()
            filename = base_name + ".png"  # Use original filename with .png extension
            output_path = os.path.join(dicom_folder, filename)
            plt.imsave(output_path, img, cmap='gray')
            #print(f"Image saved at: {output_path}")
        

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
                                        self.state.collection_images.append(file_path)
        

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
        self.ctrl.trigger("show_image")(self.show_image_t)

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
    # Trigger to enlarge clicked image
    # ---------------------------------------------------------------------------------------------

    def show_image_t(self, url):
        self.show_image(url)


    # ---------------------------------------------------------------------------------------------
    # Fetching response from views.py 
    # ---------------------------------------------------------------------------------------------
    
    def fetch_images(self):
        try:
            # Ensure this matches your Django URL
            response_maxslices = requests.get('http://127.0.0.1:8000/images/')
            response_lidc = requests.get('http://127.0.0.1:8000/dicom/')
            
            # Debugging output to check the response
            print(f"Response status code for Max_Slices Images: {response_maxslices.status_code}")
            print(f"Response status code for LIDC images: {response_lidc.status_code}")
            
            if response_maxslices.status_code == 200 & response_lidc.status_code == 200:
                data = response_maxslices.json()
                dicom_data = response_lidc.json()
                #print(f"Data received max_slices: {data}")  
                #print(f"Data received lidc: {dicom_data}")  
                
                self.state.images_list = data.get('images', [])
                self.state.dicom_images = dicom_data.get('dicom_images', [])
                #print(f"From fetch: {self.state.images_list}")  # Check the images list
                #print(f"From fetch: {self.state.dicom_images}")  # Check the dicom images list
            
            else:
                print(f"Failed to fetch images: {response_maxslices.status_code}")
                print(f"Failed to fetch dicom images: {response_lidc.status_code}")
                
        
        except Exception as e:
            print(f"Error fetching images: {e}")


    # ---------------------------------------------------------------------------------------------
    # UI layout
    # ---------------------------------------------------------------------------------------------

    def render_ui_layout(self):
        with SinglePageLayout(self.server) as layout:
            layout.title.set_text(self.server.name)

            with layout.content:
                with vuetify.VContainer(fluid=True, classes="d-flex flex-row",style="padding-bottom: 40px;"):
                    # Left Column for the figure and data 
                    with vuetify.VCol(cols="8"):
                        with vuetify.VRow():
                            vuetify.VSubheader("Visualization:",
                            style="font-size: 18px;font-weight: bold;color: rgb(0, 71, 171);")

                            # Matplotlib Figure
                            self.html_figure = matplotlib.Figure(style="position: relative")
                            self.ctrl.update_plot = self.html_figure.update

                        with vuetify.VRow():
                            vuetify.VSubheader("Data View:",
                            style="font-size: 18px;font-weight: bold;color: rgb(0, 71, 171);")

                        with vuetify.VRow():   
                            with html.Tbody():
                                with html.Tr(v_for="(item, index) in data_items",key="index"):
                                            
                                    with vuetify.VContainer(style="overflow-x: auto; white-space: nowrap; overflow-y: hidden"):
                                            vuetify.VIcon(
                                                    "mdi-download",
                                                    color="blue",
                                                    click="const csvContent = 'Nodule_ids\\n' + item['nodule_ids'].join('\\n'); const fileName = `Subset_${index+1}.csv`; utils.download(fileName, csvContent, 'text/csv');",
                                                    size=25,
                                                    style="border: 2px solid blue; border-radius: 30%; padding: 3px; color: rgb(8, 24, 168);margin-top: 5px;margin-bottom: 5px;",
                                                    )
                                                
                                            with vuetify.VRow(): 
                                                html.Td("{{ item.range }}", classes="pa-4")
                                                
                                            #with vuetify.VRow(): 
                                            #    html.Td(("{{ item.data_item }}",), classes="pa-4")
                                                            
                                            #with vuetify.VRow():
                                            #    html.Td(("{{ item.nodule_ids }}",), classes="pa-4")
                                                    
                                            #with vuetify.VRow():
                                            #    html.Td(("{{ item.image_row }}",), classes="pa-4")

                                            #with vuetify.VRow():
                                            #    html.Td(("{{ item.dicom_imgs }}",), classes="pa-4")
                                            
                                            with vuetify.VRow(style="display: flex; flex-wrap: nowrap; white-space: nowrap; align-items: flex-start;",):
                                                        with vuetify.Template(v_for="(dicom, imgIndex) in item.dicom_imgs", key="imgIndex"):   
                                                            with vuetify.VCol(cols="auto", class_="d-inline-block", style="flex: 0 0 auto; padding: 5px;"):
                                                                with vuetify.VCard(style="padding: 0; max-height: 350px;"): 
                                                                    vuetify.VImg(
                                                                        src=("dicom", lambda name: f"{name}"),
                                                                        lazy_src="http://via.placeholder.com/150x150",
                                                                        alt=("imgIndex", lambda imgIndex: f"Dicom_Img{imgIndex}"),
                                                                        style="width: 150px; height: 150px; object-fit: contain;",
                                                                        eager=False,
                                                                        #click="trigger('show_image', [img])",
                                                                    )           
                                                                    html.Td("nodule_Id={{ imgIndex }}", classes="pa-4 center-text", style="font-size: 16px; display: flex; justify-content: center; align-items: center;")

                                                    
                                            with vuetify.VRow(style="display: flex; flex-wrap: nowrap; white-space: nowrap; align-items: flex-start;",):
                                                                    with vuetify.Template(v_for="(img, imgIndex2) in item.image_row", key="imgIndex2"):   
                                                                        #with vuetify.Template(v_if="imgIndex === imgIndex2"):
                                                                        with vuetify.VCol(cols="auto", class_="d-inline-block", style="flex: 0 0 auto; padding: 5px;"):
                                                                            with vuetify.VCard(style="padding: 0; max-height: 200px;"): 
                                                                                vuetify.VImg(
                                                                                    src=("img", lambda name: f"{name}"),
                                                                                    lazy_src="http://via.placeholder.com/150x150",
                                                                                    alt=("imgIndex2", lambda imgIndex2: f"Img{imgIndex2}"),
                                                                                    style="width: 150px; height: 150px; object-fit: contain;",
                                                                                    eager=False,
                                                                                    click="trigger('show_image', [img])",
                                                                                )           
                                                                                html.Td("{{ img.split('/').pop() }}", classes="pa-4 center-text", style="font-size: 16px; display: flex; justify-content: center; align-items: center;")
                                                                                
                    # Right Column for the dynamic grid tables for configuration and view
                    with vuetify.VCol(cols="4"):

                        with vuetify.VRow():
                            vuetify.VSubheader("Threshold Config:",
                            style="font-size: 18px;font-weight: bold;color: rgb(8, 24, 168);")
                        
                        with vuetify.VRow(classes="justify-center"):
                            vuetify.VDataTable(**self.table_subset_range)

                        with vuetify.VRow():
                            vuetify.VSubheader("Threshold View:",
                            style="font-size: 18px;font-weight: bold;color: rgb(8, 24, 168);margin-top: 70px;")

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
            
                        
    # ---------------------------------------------------------------------------------------------
    # Method to start a new server (main). Not to be used in a multi-process environment
    # ---------------------------------------------------------------------------------------------

    @abstractmethod   
    def start_server_immediately(self):
        print(f"Starting Server_Manager at http://localhost:{self.port}/index.html")
        #self.server.static_url_path = "/assets"
        #self.server.static_folder = "/home/cc/research_tests/lidc_pixConvImg"
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
# Main (Guard)
# ----------------------------------------------------------------------------- 

if __name__ == "__main__":
    server = BaseOoDHistogram("Ood Analyzer using Trame-Matplotlib", 8089, "MaxSlices_wOoDScore.csv", "LIDC_Dataset", "lidc_pixConvImg", "Log_Loss_ALL","imageSOP_UID","noduleID")
    server.start_server_immediately()
    
    
