# Core libraries for data processing
import os
import requests
import numpy as np # type: ignore
import pandas as pd # type: ignore
import matplotlib.pyplot as plt  # type: ignore
from matplotlib.patches import FancyArrowPatch # type: ignore
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
        global SERVER_IP 
        SERVER_IP = '192.5.87.63'
        global PORT
        PORT ='8000'
        self.state.thresholds=[1,2,3,4]

        csv_path = os.path.join(settings.MEDIA_ROOT, csv_path)
        #print(csv_path)
        
        self.state.image_base_url= os.path.join(settings.MEDIA_ROOT, max_slices)  # Folder containing images /media/lidc_pixConvImg
        #print(self.state.image_base_url)
        
        self.state.collection_base_url= os.path.join(settings.MEDIA_ROOT, collection_path)  # Folder containing media/LIDC_Dataset
        #print(self.state.collection_base_url)
        
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
        #self.original_images(self.state.final_path)
        global files
        files="/home/cc/neurobazar_share/neurobazaar/media/dicom_images"
        self.check_node_id(self.max_slices,self.csv_path,self.nodule_ids)
        

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
        min_bin = min(0, min(self.data))  # Use the minimum of 0 and the minimum data point
        max_bin = np.ceil(max(self.data) * 2) / 2 # Use the maximum data point
        ax.set_xticks(np.arange(min_bin, max_bin, step=0.5))
        bin_edges = np.linspace(min_bin, max_bin, num=self.state.bins + 1) 
        ax.hist(self.data, bins=bin_edges, color="#00a8e8",alpha=0.85)
        
        ax.set_xlim(left=min_bin, right=max_bin)
        y_limits = ax.get_ylim() 
        colors= ['#006400','#7D26CD','blue','red']
        OOD_sections=['EASY','MEDIUM','HARD']
        if extra_lines: 
            for i,line in enumerate(extra_lines):
                line_color = colors[i % len(colors)]
                ax.plot([line, line], y_limits, color=line_color, linestyle='--')
                
                # Add section labels based on thresholds
                label_x_position = line - 0.4
                
                if i < len(extra_lines) - 1:
                    label_x_position = (line + (extra_lines[i + 1]- line ) / 2) - 1.11 # on adding new line, move it to the left
                
                else:
                    label_x_position = line - 0.4  # For the last line, just move it to the left

                if i==0:
                    section_text = f'ID'
                
                    arrow = FancyArrowPatch((0, y_limits[1] * 0.97),  # Start at the y-axis (x=0)
                                        (line, y_limits[1] * 0.97),  # End at the position of the first line
                                        color=line_color, 
                                        arrowstyle='<->', 
                                        mutation_scale=15, 
                                        alpha=0.5)
                    ax.add_patch(arrow)  
                    
                elif i >= len(OOD_sections):  # If more lines than sections, use the last section "HARD"
                    section_text = 'HARD'
                
                else:
                    section_index = (i - 1) 
                    section_text = OOD_sections[section_index]
       
                if i > 0:  # Draw an arrow only if there's a previous line
                    arrow = FancyArrowPatch((line, y_limits[1] * 0.97), 
                                            (extra_lines[i - 1], y_limits[1] * 0.97), 
                                            color=line_color, 
                                            arrowstyle='<->', 
                                            mutation_scale=15, alpha=0.5)
                                           
                    ax.add_patch(arrow)
                # Place the label
                ax.text(label_x_position, y_limits[1] * 1.0, section_text, color=line_color, horizontalalignment='center', verticalalignment='bottom', )
            
            # Ood Arrow from the first extra line to the end of the x-axis
            last_arrow = FancyArrowPatch(
                (extra_lines[0], y_limits[1] * 0.92),  # Start from first extra line
                (self.state.thresholds[-1], y_limits[1] * 0.92),  # End at the max x-axis value
                color='black', arrowstyle='simple', mutation_scale=15, alpha=0.5
            )
            ax.add_patch(last_arrow)
            ax.text(self.state.thresholds[-1] - 0.5, y_limits[1] * 0.90, 'OoD', color='black', horizontalalignment='center', verticalalignment='top',alpha=0.5)

        plt.title("Distribution of OoD Scores", fontweight='bold', fontsize=16, ha='center',pad=23)
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
                for file in os.listdir(files):
                    if file.endswith('.png'):
                        if any(uid in file for uid in filtered_uids):
                            file2=f"http://{SERVER_IP}:{PORT}{settings.MEDIA_URL}dicom_images/{file}"
                            dicom_images_list.append(file2)
                

                imgs={}
                for id in nodule_ids:
                    ss= f"{Path(id).name}"
                    base, ext = os.path.splitext(ss)
                    ss2=f"http://{SERVER_IP}:{PORT}{settings.MEDIA_URL}lidc_pixConvImg/{ss}"
                    imgs[base]=ss2
                

                # Map DICOM images to nodule IDs using the DataFrame
                base_names_list=[]
                for i in dicom_images_list:
                    base_name = os.path.splitext(os.path.basename(i))[0]
                    base_names_list.append(base_name)
               
                
                results = self.df[self.df[self.state.item_column].isin(base_names_list)][[self.state.node_id, self.state.item_column]]
                
                
                id_to_image_mapping = {row[self.state.node_id]: row[self.state.item_column] for _, row in results.iterrows()}
               
                
                final_dicom_images={}
                for ni, sop in id_to_image_mapping.items():
                    for image in dicom_images_list:
                        base_name = os.path.splitext(os.path.basename(image))[0]
                        if base_name == sop:
                            final_dicom_images[ni]=image
                
                los_results = self.df[self.df[self.state.item_column].isin(base_names_list)][[self.state.node_id, self.state.data_column]]
                id_to_los_mapping = {row[self.state.node_id]: row[self.state.data_column] for _, row in los_results.iterrows()}
                log_loss_values = [float(value) for value in id_to_los_mapping.values()]  # Extract and convert values
                log_loss_values.sort()
                

            else:
                data_values = []
                nodule_ids=[]
            

            items = {
                #"index": i + 1,
                #"name": f"Subset{i + 1}",
                "range": f"Range = ({float(start)} , {float(end)}]",
                #"data_item": f"CollectionPath = {data_values}",
                #"nodule_ids": [f"{Path(nodule_id).name}" for nodule_id in nodule_ids],
                "image_row": imgs,
                "dicom_imgs": final_dicom_images,
                "log_loss": log_loss_values
                
            }

            self.state.data_items.append(items)
            
        # Add a values for remaining items
        if self.state.subset_items:
            last_threshold = self.state.subset_items[-1]["threshold"]
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
                for file in os.listdir(files):
                    if file.endswith('.png'):
                        if any(uid in file for uid in remaining_uids):
                            file2=f"http://{SERVER_IP}:{PORT}{settings.MEDIA_URL}dicom_images/{file}"
                            dicom_rem_images_list.append(file2)
                
                
                rem_imgs={}
                for id in remaining_nodule_ids:
                    ss= f"{Path(id).name}"
                    base, ext = os.path.splitext(ss)
                    ss2=f"http://{SERVER_IP}:{PORT}{settings.MEDIA_URL}lidc_pixConvImg/{ss}"
                    rem_imgs[base]=ss2
                

                # Map DICOM images to nodule IDs using the DataFrame
                base_names_list=[]
                for i in dicom_rem_images_list:
                    base_name = os.path.splitext(os.path.basename(i))[0]
                    base_names_list.append(base_name)
                
                results = self.df[self.df[self.state.item_column].isin(base_names_list)][[self.state.node_id, self.state.item_column]]
                
                
                id_to_image_mapping = {row[self.state.node_id]: row[self.state.item_column] for _, row in results.iterrows()}
                
               
                final_dicom_rem_images={}
                for ni, sop in id_to_image_mapping.items():
                    for image in dicom_rem_images_list:
                        base_name = os.path.splitext(os.path.basename(image))[0]
                        if base_name == sop:
                            final_dicom_rem_images[ni]=image

                rem_los_results = self.df[self.df[self.state.item_column].isin(base_names_list)][[self.state.node_id, self.state.data_column]]
                id_to_los_mapping = {row[self.state.node_id]: row[self.state.data_column] for _, row in rem_los_results.iterrows()}
                rem_log_loss_values = [float(value) for value in id_to_los_mapping.values()]  # Extract and convert values
                rem_log_loss_values.sort()

                
                remaining_item = {
                    #"index": len(self.state.subset_items) + 1,
                    #"name": f"Subset{len(self.state.subset_items) + 1} (Remaining)",
                    "range": f"Range = ({float(last_threshold)} , {max_value}]",
                    #"data_item": f"CollectionPath= {remaining_values}",
                    #"nodule_ids": [f"{Path(nodule_id).name}" for nodule_id in remaining_nodule_ids], 
                    "image_row": rem_imgs,
                    "dicom_imgs": final_dicom_rem_images,
                    "log_loss": rem_log_loss_values

                }

                self.state.data_items.append(remaining_item)
            #print(self.state.data_items)
            server.state.dirty("data_items")  

     
    # ---------------------------------------------------------------------------------------------
    # Method to add a subset.
    # ---------------------------------------------------------------------------------------------
   
    def add_subset(self):
        threshold_count=len(self.state.thresholds)

        if len(self.state.subset_items) >= threshold_count:
            print("Cannot add more subsets. Maximum threshold reached.")
            return  # Exit the method if the threshold is reached

        if self.state.subset_items:
            last_threshold = self.state.subset_items[-1]["threshold"]
            if last_threshold < self.state.thresholds[-1]:
                new_line = last_threshold+1
            else:
                print("Cannot add more subsets. Maximum threshold reached.")
                return
        
        else:
            new_line = self.state.thresholds[0]
        
        new_item = {"index": len(self.state.subset_items) + 1, "name": f"Subset{len(self.state.subset_items) + 1}", "threshold": float(new_line), "actions": "Remove"}
        

        self.state.subset_items.append(new_item)

        self.server.state.dirty("subset_items") 
        
        self.update_range_count()
        self.display_data()
        self.update_chart()
        #self.update_plot()
        

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

            self.server.state.dirty("range_item")
            
            self.update_range_count()
            self.display_data()
            self.update_chart()
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
        
        dicom_folder = "/home/cc/neurobazar_share/neurobazaar/media/dicom_images"  # Folder where images will be saved
        
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
                                                    click="const csvContent = 'Ood Scores\\n' + item['log_loss'].join('\\n'); const fileName = `Subset_${index+1}.csv`; utils.download(fileName, csvContent, 'text/csv');",
                                                       
                                                    size=25,
                                                    style="border: 2px solid blue; border-radius: 30%; padding: 3px; color: rgb(8, 24, 168);margin-top: 5px;margin-bottom: 5px;",
                                                    )
                                                
                                            with vuetify.VRow(): 
                                                html.Td("{{ item.range }}", classes="pa-4")
                                              
                                        
                                            with vuetify.VContainer(style="overflow-x: auto; white-space: nowrap; overflow-y: hidden; max-width: 1100px;"):
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

                                            with vuetify.VContainer(style="overflow-x: auto; white-space: nowrap; overflow-y: hidden; max-width: 1100px;"):           
                                                with vuetify.VRow(style="display: flex; flex-wrap: nowrap; white-space: nowrap; align-items: flex-start;",):
                                                                        with vuetify.Template(v_for="(img, imgIndex2) in item.image_row", key="imgIndex2"):   
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
        #self.server.start(exec_mode="main", port=self.port)
        self.server.start(host="0.0.0.0", port=self.port)

    # ---------------------------------------------------------------------------------------------
    # Method to start a new server (async). To be used in a multi-process environment
    # ---------------------------------------------------------------------------------------------

    '''@abstractmethod   
    async def start_server_async(self):
        print(f"Starting Server_Manager at http://localhost:{self.port}/index.html")
        return await self.server.start(exec_mode="task", port=self.port)'''

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
    
    
