# Core libraries for data processing                                                                                                      
import json
import os                                                                                                                                                                                                                                                                                                                                                 
import numpy as np # type: ignore                                                                                                                                                             
import pandas as pd # type: ignore                                                                                                                                                            
import matplotlib.pyplot as plt  # type: ignore                                                                                                                                               
from matplotlib.patches import FancyArrowPatch # type: ignore                                                                                                                                 
import pydicom # type: ignore                                                                                                                                                                 
from PIL import Image # type: ignore  
                                                                                                                                                                                                                                                                                                                                                              
# Core libraries for rendering
from trame.app import get_server # type: ignore                                                                                                                                            
from trame.ui.vuetify import SinglePageLayout # type: ignore                                                                                                                                  
#from trame.ui.vuetify import SinglePageWithDrawerLayout # type: ignore                                                                                                                        
from trame.widgets import vuetify, matplotlib, html, router # type: ignore  
import dask.array as da                          # type: ignore
import dask_histogram as dh                      # type: ignore
import boost_histogram as bh                    # type: ignore                                                                                               
from trame.decorators import TrameApp, change   # type: ignore                                                                                                                                                                                                                                                                                             
from django.conf import settings # type: ignore                                                                                                                                               
from django.core.wsgi import get_wsgi_application # type: ignore                                                                                                                          
from trame.ui.router import RouterViewLayout # type: ignore  
                                                                                                                                                                                       
# Base class for the histogram application                                                                                                                                                    
from abc import abstractmethod                                                                                                                                                                
                                                                                                                                                                                              
# Set up Django environment                                                                                                                                                                   
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "neurobazaar.settings")                                                                                                                                                                                                                                                                        
application = get_wsgi_application() 
                                                                                                                                                         
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                          
@TrameApp()                                                                                                                                                                                   
class BaseOoDHistogram:                                                                                                                                                                       
    
    # --------------------------------------------------------------------------                                                                                                           -------------------                                                                                                                                                                           
    # Constructor for the BaseOoDHistogram class.                                                                                                                                             
    # --------------------------------------------------------------------------                                                                                                              ------------------- 
    def __init__(self, name, port, csv_path = "", collection_path="",max_slices="",ood_column = None, study_column=None, series_column=None, image_column=None,node_id=None):                                                                                                                                                                                                                                       
        self.server = get_server(name, client_type="vue2")                                                                                                                                    
        self.port = port                                                                                                                                                                      
        self.state, self.ctrl = self.server.state, self.server.controller                                                                                                                     
        global SERVER_IP                                                                                                                                                                      
        SERVER_IP = '192.168.56.1'   # add your server ip address                                                                                                                                                     
        global PORT                                                                                                                                                                           
        PORT ='8000' 
        self.state.thresholds = [1, 2, 3, 4] 

        # Data paths
        self.state.no_image = [f"http://{SERVER_IP}:{PORT}{settings.MEDIA_URL}no_image_available.png"]  
        csv_path = os.path.join(settings.MEDIA_ROOT, csv_path)
        self.state.image_base_url= os.path.join(settings.MEDIA_ROOT, max_slices)  # Folder containing images /media/lidc_pixConvImg
        self.state.collection_base_url= os.path.join(settings.MEDIA_ROOT, collection_path)  # Folder containing media/LIDC_Dataset
        self.csv_path=csv_path
        self.collection_path=self.state.collection_base_url
        self.max_slices=self.state.image_base_url
        self.state.files = r"media/dicom_images" #Folder containing dicom downloaded images                                                                                                                                

        # Columns                                                                                                                                                                      
        self.state.ood_column = ood_column if ood_column else "Log_Loss_ALL"  
        self.state.study_column =  study_column if study_column else "StudyInstanceUID"  
        self.state.series_column = series_column if series_column else "SeriesInstanceUid"                                                                                                          
        self.state.image_column= image_column if image_column else "imageSOP_UID"                                                                                                                
        self.state.node_id= node_id if node_id else "noduleID"                                                                                                                                
                                                                                                                                                                                              
        # State variables
        self.state.subset_items = []                                                                                                                                                          
        self.state.range_item = []
        
        self.state.data_items = []
        self.state.image_list=[]                                                                                                                                                              
        self.state.final_image_data = []                                                                                                                                                      
        self.state.image_paths=[]                                                                                                                                                             
        self.state.final_path=[]                                                                                                                                                              
        self.state.collection_images=[]                                                                                                                                                       
        self.state.pixel_array=[]                                                                                                                                                             
        self.state.dicom_images=[]
        self.state.ood = ""
        self.state.selected_nodule ="" 
        self.state.image_items={}                                                                                                                                                             
        self.state.image_details=[] 
        self.state.compare_details=[]                                                                                                                                                          
        self.state.coords_dict={}                                                                                                                                                             
        self.state.checkboxed_images=[] 
        self.state.compare_images=[]
        self.df = pd.DataFrame()                                                                                                                                                                                                                                                                                                                             
        self.data = []                                                                                                                                                                        
                                      
        self.state.subset_config = [                                                                                                                                                          
                {"text": "Index", "value": "index"},                                                                                                                                              
                {"text": "Name", "value": "name"},                                                                                                                                                
                {"text": "Threshold", "value": "threshold"},                                                                                                                                      
                {"text": "Actions", "value": "actions"},                                                                                                                                          
            ]                                                                                                                                                                                     
                                                                                                                                                                                              
        self.table_config = {                                                                                                                                                                        
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
                                                                                                                                                                      
        if self.csv_path:
            if self.collection_path and self.max_slices:
                if not ood_column:
                    raise ValueError("ood_column argument is required when csv_path is provided")
                self.df = pd.read_csv(csv_path)
                self.data = self.df[ood_column].values #np.array
                self.state.bins = 10
                if isinstance(self.data, np.ndarray):
                    print("Data size is a numpy array")
                    self.data_dask = da.from_array(self.data, chunks='auto')
                    
                   
                self.data_min, self.data_max = self._compute_min_max(self.data_dask) # calculating min max from the dask data
                self.hist, self.bin_edges = self._compute_hist(self.data_dask, self.state.bins) # computing histogram with dask data
                self.item_list = self.df[image_column].tolist()
                self.nodule_ids = self.df[node_id]


        self.check_collection(self.collection_path)
        self.mapping(csv_path)
        #self.create_dict() 
        #self.original_images(self.state.files)
        
        self.check_node_id(self.max_slices, self.csv_path, self.nodule_ids)
        self.register_triggers()
        self.render_ui_layout()
        self.update_range_count()  
                                                                                                                                                        
                                                                                                                                                                                              
    # ---------------------------------------------------------------------------------------------                                                                                                                                                                                                                                                                                      
    # Method to get the figure size (static method).                                                                                                                                          
    # ---------------------------------------------------------------------------------------------                                                                                                                                                                                                                                                                                                                                                                                                                                                            
    def get_figure_size(self):                                                                                                                                                                
        return {"figsize": (10, 6), "dpi": 85}  


    # ---------------------------------------------------------------------------------------------                                                                                                                                                                                                                                                                                      
    # Compute min max for Dask Data                                                                                                                                          
    # ---------------------------------------------------------------------------------------------
    def _compute_min_max(self, dask_data):
        """Compute min and max efficiently"""
        if hasattr(dask_data, "compute"):
            return dask_data.min().compute(), dask_data.max().compute()
        else:
            return dask_data.min(), dask_data.max()    


    # ---------------------------------------------------------------------------------------------                                                                                                                                                                                                                                                                                      
    # Compute histogram for Dask Data                                                                                                                                         
    # ---------------------------------------------------------------------------------------------
    def _compute_hist(self, dask_data, bins):
        bins = int(bins)
        dask_hist = dh.factory(dask_data, axes=(bh.axis.Regular(bins, self.data_min, self.data_max),))
        hist_result = dask_hist.persist().compute(scheduler='threads')
        frequencies = hist_result.to_numpy()[0]
        _ , bin_edges = da.histogram(dask_data, bins=bins, range=(self.data_min, self.data_max))
        return frequencies, bin_edges 
    

    # ---------------------------------------------------------------------------------------------                                                                                                                                                                                                                                                    
    # Method to update the plot.                                                                                                                                                              
    # ---------------------------------------------------------------------------------------------                                                                                                                                                                                                                                                                                                    
    def update_plot(self, extra_lines=None):                                                                                                                                                       
        plt.close('all')
        fig, ax = plt.subplots(**self.get_figure_size()) 
        ax.bar(self.bin_edges[:-1], self.hist, width=np.diff(self.bin_edges), align='edge', edgecolor='black',color="#00a8e8")                                                                                                                                             
        #ax.set_xticks(self.bin_edges)
        #ax.set_xlim(left=self.bin_edges[0], right=self.bin_edges[-1])
        min_bin = min(0, min(self.data))  
        max_bin = np.ceil(max(self.data) * 2) / 2 
        ax.set_xticks(np.arange(min_bin, max_bin, step=0.5))
        ax.set_xlim(left=min_bin, right=max_bin)
        y_limits = ax.get_ylim() 
        new_ymax = y_limits[1] + (y_limits[1] - y_limits[0]) * 0.1  # Increase the upper limit y_limit[1] by 10%
        ax.set_ylim(y_limits[0], new_ymax)                                                                                                                                                       
        
        colors= ['#006400','#873e23','blue','red']                                                                                                                                            
        OOD_sections=['EASY','MODERATE','HARD']                                                                                                                                               
        if extra_lines:                                                                                                                                                                       
            for i, line in enumerate(extra_lines):                                                                                                                                             
                line_color = colors[i % len(colors)]                                                                                                                                          
                ax.plot([line, line], y_limits, color=line_color, linestyle='--')                                                                                                            
                label_x_position = line - 0.4                                                                                                                                                                                                                                                                                                                        
                if i < len(extra_lines) - 1:                                                                                                                                                  
                    label_x_position = (line + (extra_lines[i + 1]- line ) / 2)- 1.11 # on adding new line, move it to the left                                                                                                                                                                                                                                                                                                                                                                                                                   
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
                    arrow = FancyArrowPatch((line, y_limits[1] * 0.97 ),                                                                                                                       
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
        ax.set_title('OoD Scores Distribution', fontsize=15, fontweight='bold', color='black', loc='center')                                               
        ax.set_xlabel('OoD Scores', fontsize=12)                                                                                                                                              
        ax.set_ylabel('Frequency', fontsize=12)  
        fig.tight_layout()                                                                                                                                            
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
                "name": f"Subset{len(self.state.subset_items) + 1}(OOD)",
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
        self.server.state.dirty("data_items")
        self.server.state.dirty("range_item")
        self.server.state.dirty("subset_items")     

    # ---------------------------------------------------------------------------------------------                                                                                                                                                                                                                                                                                         
    # Method to display the subset data items                                                                                                                                                 
    # ---------------------------------------------------------------------------------------------   
    def display_data(self):
        self.state.data_items.clear()
        for i, subset in enumerate(self.state.subset_items):
            if i == 0:                                                                                                                                                                      
                start = float(0)                                                                                                                                                              
            else:                                                                                                                                                                             
                start = self.state.subset_items[i - 1]["threshold"]                                                                                                                           

            end = subset["threshold"]  
                                                                                                                                                                     

            if start < end:          
                mask = (self.df[self.state.ood_column] > start) & (self.df[self.state.ood_column] <= end)
                filtered_df = self.df[mask]

                filtered_uids = filtered_df[self.state.image_column].tolist()  # SOP UIDs
                filtered_nodule_ids = filtered_df[self.state.node_id].tolist()  # Nodule IDs
                filtered_nodule_ids_str = [str(id) for id in filtered_nodule_ids]

                # Get relevant nodule image paths
                nodule_ids = [
                    path for path in self.state.collection_images 
                    if any(str(id) in path for id in filtered_nodule_ids_str)
                ]

                node_basename = [int(os.path.splitext(os.path.basename(nid))[0]) for nid in nodule_ids]

                base_names_list = []
                for image in os.listdir(self.state.files):
                    if image.endswith('.png'):
                        if any(uid in image for uid in filtered_uids):
                            image = os.path.splitext(image)[0]
                            base_names_list.append(image)

                # Filter results by both the node_basename and the filtered DataFrame
                results = filtered_df[filtered_df[self.state.node_id].isin(node_basename)][
                    [self.state.node_id, self.state.study_column, self.state.series_column, self.state.image_column, self.state.ood_column]
                ]

                # List of tuples containing the Nodule IDs, Study, Series, SOP UIDs, and OoD scores
                mappings = [
                    (row[self.state.node_id],
                    row[self.state.study_column],
                    row[self.state.series_column],
                    row[self.state.image_column],
                    row[self.state.ood_column]) for _, row in results.iterrows()
                ]

                # Sort by OoD score (ascending)
                mappings.sort(key=lambda x: x[4])

                # Populate final results in sorted order
                final_dicom_images = {}
                max_slices = {}
                log_loss_values = {}

                for item in mappings:
                    nodule_id = item[0]  # Nodule ID
                    dicom = f"http://{SERVER_IP}:{PORT}{settings.MEDIA_URL}dicom_images/{item[3]}.png"
                    img = f"http://{SERVER_IP}:{PORT}{settings.MEDIA_URL}lidc_pixConvImg/{nodule_id}.png"

                    final_dicom_images[nodule_id] = dicom
                    max_slices[nodule_id] = img
                    #log_loss_values.append(float(item[4]))  # Ensure sorted 
                    log_loss_values[nodule_id] = float(item[4])  # Ensure sorted order
                    

                # Prepare items to be added to state
                items = {
                    "range": f"Range = ({float(start)} , {float(end)}]",
                    "image_row": max_slices,
                    "dicom_imgs": final_dicom_images,
                    "log_loss": log_loss_values,
                    "download": mappings,
                }

                self.state.data_items.append(items)
    

        if self.state.subset_items:
                last_threshold = self.state.subset_items[-1]["threshold"]
                max_value = np.nanmax(self.data)

                if last_threshold <= max_value:
                    # Create the mask that includes max_value as well
                    remaining_mask = (self.df[self.state.ood_column] >= last_threshold) & (self.df[self.state.ood_column] <= max_value)

                    # Get the SOP UIDs that match the mask
                    remaining_uids = self.df[remaining_mask][self.state.image_column].tolist()
                    remaining_filtered_ids = self.df[remaining_mask][self.state.node_id].tolist()
                    filtered_remaining_nodule_ids_str = [str(id) for id in remaining_filtered_ids]

                    remaining_nodule_ids = [
                        path for path in self.state.collection_images
                        if any(str(id) in path for id in filtered_remaining_nodule_ids_str)
                    ]

                    rem_node_basename = []
                    for nodule_id in remaining_nodule_ids:
                        node_base = os.path.basename(nodule_id)
                        node_base = os.path.splitext(node_base)[0]
                        rem_node_basename.append(int(node_base))

                    # DICOM Image SOP UID with filtered UIDs if matched
                    rem_base_names_list = []
                    for image in os.listdir(self.state.files):
                        if image.endswith('.png'):
                            if any(uid in image for uid in remaining_uids):
                                image = os.path.splitext(image)[0]
                                rem_base_names_list.append(image)

                    # Map DICOM images to nodule IDs and OoD scores
                    rem_results = self.df[remaining_mask][[
                        self.state.node_id, self.state.study_column, self.state.series_column, 
                        self.state.image_column, self.state.ood_column
                    ]]

                    # List of tuples containing the SOP UIDs, Nodule IDs, and respective OoD scores
                    rem_mappings = [
                        (row[self.state.node_id],
                        row[self.state.study_column],
                        row[self.state.series_column],
                        row[self.state.image_column],
                        row[self.state.ood_column]) for _, row in rem_results.iterrows()
                    ]

                    
                    
                    #print(f"Remaining OoD Scores: {[item[4] for item in rem_mappings]}")
                    # Sort by OoD score (ascending)
                    rem_mappings.sort(key=lambda x: x[4])

                    # Create empty lists and dictionaries
                    rem_max_slices = {}
                    rem_final_dicom_images = {}
                    rem_log_loss_values = {}

                    # Populate sorted dictionaries
                    for item in rem_mappings:
                        nodule_id = item[0]  # Nodule ID
                        dicom = f"http://{SERVER_IP}:{PORT}{settings.MEDIA_URL}dicom_images/{item[3]}.png"
                        img = f"http://{SERVER_IP}:{PORT}{settings.MEDIA_URL}lidc_pixConvImg/{nodule_id}.png"

                        # Map sorted nodule ID to images and log loss
                        rem_final_dicom_images[str(nodule_id)] = dicom
                        rem_max_slices[str(nodule_id)] = img
                        #rem_log_loss_values.append(float(item[4]))  # Maintain sorted order
                        rem_log_loss_values[str(nodule_id)] = float(item[4])

                    # Ensure all data structures are sorted in the same order
                    remaining_item = {
                        "range": f"Range = ({float(last_threshold)} , {max_value}]",  # Ensures max_value is included
                        "image_row": rem_max_slices,
                        "dicom_imgs": rem_final_dicom_images,
                        "log_loss": rem_log_loss_values,
                        "download": rem_mappings
                    }
                    #print(f"Remaining Item: {rem_log_loss_values}")
                    #print(f"value: {remaining_item}")

                    self.state.data_items.append(remaining_item)
                    #print(rem_log_loss_values)
        self.server.state.dirty("data_items")
        #print(self.state.data_items)
        
                                                                                                                                   
                                                                            
    # ---------------------------------------------------------------------------------------------                                                                                                                                                                                                                                                                                   
    # Method to add a subset.                                                                                                                                                                 
    # ---------------------------------------------------------------------------------------------                                                                                                                                                                                                                                                                                                      
    def add_subset(self):
        if not self.state.thresholds:
            print("No thresholds available.")
            return
        
        if self.state.subset_items:
            last_threshold = self.state.subset_items[-1]["threshold"]
            new_line = next((t for t in self.state.thresholds if t > last_threshold), None) # Find the next available threshold that is greater than last_threshold

            if new_line is None:
                print("Cannot add more subsets. Maximum threshold reached.")
                return
        else:
            new_line = self.state.thresholds[0] # First subset, pick the smallest threshold

        new_item = {
            "index": len(self.state.subset_items) + 1,
            "name": f"Subset{len(self.state.subset_items) + 1}",
            "threshold": float(new_line),
            "actions": "Remove"
        }
        self.state.subset_items.append(new_item)
        self.server.state.dirty("subset_items") 
        self.update_range_count()
        self.display_data()
        self.update_chart()
                                                                                                                                                                                                                                                                                                                                                                                     
    # ---------------------------------------------------------------------------------------------                                                                                                                                                                                                                                                                       
    # Method to remove a subset.                                                                                                                                                              
    # ---------------------------------------------------------------------------------------------                                                                                                                                                                                                                                                                                            
    def remove_subset(self, index):                                                                                                                                                           
        if(index=="0"):                                                                                                                                                                       
            self.state.subset_items.pop(index)                                                                                                                                                
            self.state.range_item.pop(index)                                                                                                                                                  
            self.display_data()                                                                                                                                                               
                                                                                                                                                                                              
        elif 0 < index <= len(self.state.subset_items):                                                                                                                                         
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
        self.server.state.dirty("data_items")                                                                                                                                                                                                                                                                                                                                 
        self.update_range_count()                                                                                                                                                         
        self.display_data()                                                                                                                                                               
        self.update_chart()                                                                                                                                                               
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
                            self.state.image_paths.append(full_path) 
                            
    #-------------------------------------------------------------------------------------------------                                                                                                                                                                           
    # Mapping records from .csv to the collection folder                                                                                                                                      
    # ---------------------------------------------------------------------------------------------                                                                                                                                                                                                                                                                                                                                                                                                                                                                            
    def mapping(self,csv_path):                                                                                                                                                   
        if not os.path.isfile(csv_path):                                                                                                                                                      
            print(f"CSV file does not exist at the path: {csv_path}")                                                                                                                         
            return                                                                                                                                                                            
                                                                                                                                                                                              
        column_1= self.state.study_column
        column_2= self.state.series_column
        file_name = self.state.image_column                                                                                                                                                              
                                                                                                                                                                                              
        studies = self.df[column_1].values                                                                                                                                                    
        series = self.df[column_2].values                                                                                                                                                     
        image_sop= self.df[file_name].values                                                                                                                                                      
                                                                                                                                                                                              
        for dcm_path in self.state.image_paths:                                                                                                                                               
            parts=dcm_path.split(os.sep)                                                                                                                                                      
                                                                                                                                                                                              
            if len(parts)>=3:                                                                                                                                                                 
                dcm_file=os.path.basename(dcm_path)                                                                                                                                           
                if dcm_file.endswith(".dcm"):                                                                                                                                                 
                    dcm_file = os.path.splitext(dcm_file)[0]                                                                                                                                  
                second_folder=parts[-2]                                                                                                                                                       
                first_folder = parts[-3]                                                                                                                                                      
                                                                                                                                                                                              
                for _, (study_uid, series_uid, file_uid) in enumerate(zip(studies, series, image_sop)):                                                                                                                                                                                                                                                                 
                    if study_uid == first_folder and series_uid == second_folder and file_uid == dcm_file:                                                                                                                                                                                                                                                             
                        #path = f"{study_uid}/{series_uid}/{file_uid}.dcm"                                                                                                                    
                        self.state.final_path.append(dcm_path)      

    # ---------------------------------------------------------------------------------------------                                                                                                                                                                                                                                                                                         
    # Create dictionary for ImageSOPUid and coordinates                                                                                                                                       
    # ---------------------------------------------------------------------------------------------                                                                                                                                                                                                                                                                                                   
    def create_dict(self):                                                                                                                                                                    
        for i in self.df.index:                                                                                                                                                               
            sop_uid = self.df.loc[i, 'imageSOP_UID']  # Get the 'imageSOP_UID'                                                                                                                
            coords = self.df.loc[i, 'coords']        # Get the 'coords'                                                                                                                       
            self.state.coords_dict[sop_uid] = coords # Add the SOP UID and coordinates to the dictionary                                                                                                                                                                                                                                                                                    
        self.server.state.dirty("coords_dict")


    # ---------------------------------------------------------------------------------------------                                                                                                                                                                                                                                                                                         
    # Displaying Pixel Array for original images from Collection                                                                                                                              
    # ---------------------------------------------------------------------------------------------                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  
    def original_images(self,files):                                                                                                                                                                
        if not os.path.exists(files):                                                                                                                                                  
            os.makedirs(files)                                                                                                                                                                                                                                                                                                                                                 
        for path in self.state.final_path:                                                                                                                                                    
            meta_data_path = pydicom.dcmread(f"{path}")                                                                                                                                       
            pixel_array = meta_data_path.pixel_array                                                                                                                                          
            img = Image.fromarray(pixel_array)                                                                                                                                                
            self.state.pixel_array.append(pixel_array)                                                                                                                                        
                                                                                                                                                                                              
            base_name= os.path.splitext(path)[0]                                                                                                                                              
            base_name= base_name.split('/').pop()                                                                                                                                             
            filename = base_name + ".png"  # Use original filename with .png extension                                                                                                                                                                                                                                                                                                      
            output_path = os.path.join(files, filename)                                                                                                                                
                                                                                                                                                                                              
            if os.path.exists(output_path):                                                                                                                                                   
                print(f"Skipping: {filename} (already exists)")                                                                                                                               
                continue                          
	        
            for key, value in self.state.coords_dict.items():                                                                                                                                 
                if key == base_name:                                                                                                                                                          
                    coords=value                                                                                                                                                              
                    x_coords = []                                                                                                                                                             
                    y_coords = []                                                                                                                                                             
                    for point in coords.split("|"):                                                                                                                                           
                        if point.strip():  # Ensure the point is not empty                                                                                                                    
                            x, y = map(int, point.split(";"))                                                                                                                                 
                            x_coords.append(x)                                                                                                                                                
                            y_coords.append(y)                                                                                                                                                                                                                                                                                                                    
                            plt.imshow(pixel_array, cmap="gray")                                                                                                                              
                            plt.plot(x_coords, y_coords, color="red", linewidth=1)  # Overlay the contours on the image                                                                                                                                                                                                                                                     
                            plt.axis("off")  # Remove axes                                                                                                                                    
                            plt.savefig(output_path, bbox_inches="tight", pad_inches=0)                                                                                                                                                                                                                                                                                                     
                            plt.close()    

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
                                        break                                                                                                                             

    # ---------------------------------------------------------------------------------------------                                                                                                                                                                                                                                                                                   
    # Refresh the Layout                                                                                                                                                                      
    # ---------------------------------------------------------------------------------------------                                                                                                                                                                                                                                                                                          
    def refresh_data(self):                                                                                                                                                                    
        self.state.subset_items.clear() 
        self.state.range_item.clear()
        self.state.data_items.clear()                                                                                                                                                           
        self.server.state.dirty("subset_items")                                                                                                                                               
        self.server.state.dirty("range_item")                                                                                                                                                 
        self.server.state.dirty("data_items")      

    #-------------------------------------------------------------------------------------------------                                                                                                                                                                           
    # State change handler to update the chart.                                                                                                                                               
    # ---------------------------------------------------------------------------------------------                                                                                                                                                                                                                                                                                        
    @change("subset_items")                                                                                                                                                                   
    def update_chart(self, **trame_scripts):                                                                                                                                                  
        extra_lines = [float(item["threshold"]) for item in self.state.subset_items]                                                                                                                                                                                                                                                                                                                                                                                                                                             
        self.html_figure.update(self.update_plot(extra_lines))                                                                                                                                                         
                                                                                                                                                                                              
    # --------------------------------------------------------------------------------------------                                                                                                                                                                                                                                                                                         
    # Method to register triggers with the controller                                                                                                                                         
    # ---------------------------------------------------------------------------------------------                                                                                                                                                                                                                                                                                         
                                                                                                                                                                                              
    def register_triggers(self):                                                                                                                                                              
        self.ctrl.trigger("update_threshold")(self.update_threshold)                                                                                                                          
        self.ctrl.trigger("remove_subset")(self.remove_subset)                                                                                                                                                                                                                                      
        self.ctrl.trigger("navigate_to_data_view")(self.navigate_to_data_view)  
        self.ctrl.trigger("checkbox_method")(self.checkbox_method)                                                                                                                            
        self.ctrl.trigger("compare_page")(self.compare_page)  
        self.ctrl.trigger("restore_checkboxed_state")(self.restore_checkboxed_state)

    # ---------------------------------------------------------------------------------------------                                                                                                                                                                                                                                                                         
    # To restore state of checkboxes after Take me Back button is clicked                                                                                                                                                                                                                                                                         
    # ---------------------------------------------------------------------------------------------
    def restore_checkboxed_state(self):
        if hasattr(self.state, 'checkboxed_images'):
            self.state.checkboxed_images = []
            self.state.compare_images =[]   
        self.server.state.dirty("checkboxed_images")

                                                                                                                                                                                                                                                                                                                                                                                                       
    # ---------------------------------------------------------------------------------------------                                                                                                                                                                                                                                                                         
    # Navigate to Selected Image View on Clicking a Dicom or a Segmented Lung Nodule image                                                                                                                                                                                                                                                                                
    # ---------------------------------------------------------------------------------------------                                                                                                                                                                                                                                                                                         
    def navigate_to_data_view(self, dicom, imgIndex):                                                                                                                                         
        self.all_node_ids = self.df[self.state.node_id]                                                                                                                                       
        for i, node_id in enumerate(self.all_node_ids):                                                                                                                                       
            if str(node_id) == str(imgIndex):                                                                                                                                                 
                row_data = self.df.iloc[i].to_dict()                                                                                                                                          
                break                                                                                                                                                                         
        self.state.image_items = {                                                                                                                                                            
            "Original_Dicom": [dicom],                                                                                                                                                        
            "Segmented_Nodule": [f"http://{SERVER_IP}:{PORT}{settings.MEDIA_URL}lidc_pixConvImg/{imgIndex}.png"],                                                                                                                                                                                                                                                       
        }                                                                                                                                                                                                                                                                                                                                                     
        image_info = { **row_data }                                                                                                                                                           
        self.state.image_details = [{"Property": key, "Value": value} for key, value in image_info.items()]
        
        for item in self.state.image_details:  
            if item["Property"] == self.state.node_id:
                self.state.selected_nodule= item["Value"]
            if item["Property"] == self.state.ood_column:
                self.state.ood= item["Value"]


    # ---------------------------------------------------------------------------------------------                                                                                                                                                                                                                                                                                         
    # Trigger for clickable checkbox                                                                                                                                                             
    # ---------------------------------------------------------------------------------------------                                                                                                                                                                                                                                                                                         
    def checkbox_method(self, dicom, imgIndex):
        imgIndex = int(imgIndex) if isinstance(imgIndex, str) else imgIndex # Ensure imgIndex is an integer

        if dicom and imgIndex is not None:
            if {imgIndex: dicom} not in self.state.checkboxed_images: # Add to the list if it's not already there
                self.state.checkboxed_images.append({imgIndex: dicom})
            else:
                self.state.checkboxed_images = [   # Remove from the list if it's already there
                    entry for entry in self.state.checkboxed_images if imgIndex not in entry
                ]
                #print(f"Image {imgIndex} removed from the list.")
        #print("Updated Checkbox Contents:", self.state.checkboxed_images)
                
    # ---------------------------------------------------------------------------------------------                                                                                                                                                                                                                                                                         
    # For side by side comparison of features                                                                                                                                                                                                                                                                                
    # ---------------------------------------------------------------------------------------------                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               
    def compare_page(self):
        # Retrieve the checkboxes list from state
        if hasattr(self.state, 'checkboxed_images'):
            for entry in self.state.checkboxed_images:
                for imgIndex, dicom in entry.items():
                    ood = self.df.loc[self.df[self.state.node_id] == imgIndex, self.state.ood_column].values[0]
                    self.state.compare_images.append(
                        { "Original_Dicom": [dicom],                                                                                                                                                        
                            "Segmented_Nodule": [f"http://{SERVER_IP}:{PORT}{settings.MEDIA_URL}lidc_pixConvImg/{imgIndex}.png"], 
                            "OOD_Score": str(ood),
                        })
                    self.server.state.dirty("compare_images")
                    #print(self.state.compare_images)
                    self.all_node_ids = self.df[self.state.node_id] 
                    for i, node_id in enumerate(self.all_node_ids):                                                                                                                                       
                        if str(node_id) == str(imgIndex):                                                                                                                                                 
                            compare_data = self.df.iloc[i].to_dict()                                                                                                                                          
                            break                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                        
                    compare_info = { **compare_data }                                                                                                                                                           
                    details = [{"Property": key, "Value": value} for key, value in compare_info.items()]
                    self.state.compare_details.append(details)
            self.server.state.dirty("compare_details")
            #print(f"Details: {self.state.compare_details}")

        else:
            self.state.compare_images = []
            #print("No images selected for comparison.")


    # ---------------------------------------------------------------------------------------------                                                                                                                                                                                                                                                                                         
    # UI layout                                                                                                                                                                               
    # ---------------------------------------------------------------------------------------------                                                                                                              
                                                                                                                                                                                                                                                                                                                                                                   
    def render_ui_layout(self):                                                                                                                                                               
        
        with RouterViewLayout(self.server, "/"):                                                                                                                                                                                                                                                                                                                          
            with vuetify.VContainer(fluid=True, classes="d-flex flex-column flex-md-row",style="max-width: 100%; padding-bottom:10px"):                                                                                                                                                                                                                                   
                # Left Column for the figure and data                                                                                                                                                                                                                                                                                             
                with vuetify.VCol(xs="12", sm="12", md="8", lg="9",xl="9"):                                                                                                                                                                                                                                                                          
                    with vuetify.VRow(classes="justify-start"):                                                                                                                                                                                                                                                                                                  
                        vuetify.VSubheader("Visualization:",style="font-size: 18px;font-weight: bold;color: rgb(0, 71, 171); padding:0; margin:0;")                                                                                                                                                                                                                                           
                        # Matplotlib Figure 
                    with vuetify.VRow(classes="justify-start"):                                                                                                                                      
                        self.html_figure = matplotlib.Figure(style="position: relative; padding-top: 10px; margin: 0; display: block; align-self: flex-start; justify-content: start;")                                                                                                                                                                                                   
                        #self.ctrl.update_plot = self.html_figure.update                                                                                                               
                                                                                                                                                             
                    with vuetify.VRow(classes="justify-start"):                                                                                                                                          
                        vuetify.VSubheader("Data View:",style="font-size: 18px;font-weight: bold;color: rgb(0, 71, 171); padding-top:10px")                                                                                                                                                                                                                                                                                      
                                                                                                                                                                                                                                                                                
                    with vuetify.VRow(classes="justify-start", style="padding:0"):                                                                                                                                          
                        with vuetify.Template(v_for="(item, index) in data_items",key="index"): 
                            with vuetify.VCol(xs="12", sm="12", md="8", lg="8",xl="9"):                                                                                                                                                                                                                                                                                
                                #with vuetify.VContainer(style="overflow-x: auto; white-space: nowrap; overflow-y: hidden;"):                                                                                                    
                                        vuetify.VIcon(                                                                                                                            
                                            "mdi-download",                                                                                                                   
                                            color="blue",                                                                                                                     
                                            click="utils.download('Subset_'+(index + 1)+'.csv','Nodule ID , Study Instance UID, Series Instance UID, Image SOP UID, Log Loss\\n'+item['download'].join('\\n'), 'text/csv')",                                                                                                                      
                                            size=25, 
                                            style="border: 2px solid blue; border-radius: 30%; padding: 2px; color: rgb(8, 24, 168);margin-top:5px;margin-bottom: 5px;",)                                                                                                                
                                                                                                                                                                                                                                                  
                                        with vuetify.VRow():                                                                                                                      
                                            html.Td("{{ item.range }}", classes="pa-4")                                                                                                                                                                                                                                                                                  
                                                                                                                                                                 
                                        with vuetify.VContainer(style="overflow-x: auto; white-space: nowrap; overflow-y: hidden; padding-bottom: 2px; padding:0;",classes="d-flex flex-column flex-md-row"):                                                                                                                                                                                         
                                                with vuetify.VRow(style="display: flex; flex-wrap: nowrap; white-space: nowrap; align-items: flex-start;",):                                                                                                                                                                                                                                                                                                                                                                                                  
                                                    with vuetify.Template(v_for="(dicom, imgIndex) in item.dicom_imgs", key="imgIndex"):                                                                                                                                                               
                                                        with vuetify.VCol(cols="auto", class_="d-inline-block", style="flex: 0 0 auto; padding: 5px; max-width:100%"):                                                                                                                                                               
                                                            vuetify.VCheckbox(
                                                                          color="blue",
                                                                            change="trigger('checkbox_method',[dicom,imgIndex])",
                                                                            style="padding:0; margin-left:60px",)
                                                            with vuetify.VCard(style="padding-top: 0;padding-left:12px; max-height: 800px;"): 
                                                                with vuetify.VRow(style="display: flex; flex-wrap: nowrap; white-space: nowrap; align-items: flex-start;padding-top:50px;padding-right:15px",):                                                                                                           
                                                                        with vuetify.VBtn(
                                                                                    to=("'/data/'",), 
                                                                                    style="padding: 0; border: none; background: none; cursor: pointer;",
                                                                                    elevation=0,  
                                                                                    outlined=False,  
                                                                                ):
                                                                                    vuetify.VImg(                                                                                                                                                                                                                                                                                                                                                                                                                                                        
                                                                                    src=("dicom", lambda name: f"{name}"),                                                                                                                                                                                                                                                                                                                                                   
                                                                                    lazy_src="http://picsum.photos/id/114/150/150",                                                                                                                                                                                                                                                                                                                                           
                                                                                    alt=("imgIndex", lambda imgIndex: f"Dicom_Img{imgIndex}"),                                                                                                                                                                                                                                                                                                                               
                                                                                    style="width: 150px; height: 150px; object-fit: contain;",                                                                                                                                                                                                                                                                                                             
                                                                                      eager=False,                                                                                                                                                                                                                                                                                                                                                                      
                                                                                    click= "trigger('navigate_to_data_view', [dicom, imgIndex])"                                                                                                                                                                                                                                   
                                                                                    ) 
                                                                with vuetify.VRow(style="display: flex; flex-wrap: nowrap; white-space: nowrap; align-items: flex-start;padding-top:120px;padding-right:15px;",): 
                                                                        with vuetify.VBtn(
                                                                            to=("'/data/'",),  
                                                                            style="padding: 0; border: none; background: none; cursor: pointer;",
                                                                            elevation=0,  
                                                                            outlined=False,  
                                                                        ):                                                                                                           
                                                                            vuetify.VImg(                                                                                                                                                                                                                                                                                                                                                                                                                                            
                                                                            src=("item.image_row[imgIndex]", lambda name: f"{name}"),                                                                                                                                                                                                                                                                                                                                                                                            
                                                                            lazy_src="http://picsum.photos/id/114/150/150",                                                                                                                                                                                                                                                                                                                                                                                                       
                                                                            alt=("imgIndex", lambda imgIndex: f"Img{imgIndex}"),                                                                                                                                                                                                                                                                                                                                                                                                 
                                                                            style="width: 150px; height: 150px; object-fit: contain;",                                                                                                                                                                                                                                                                                                        
                                                                            eager=False,                                                                                                                                                                                                                                                                                                                                                             
                                                                            click= "trigger('navigate_to_data_view', [dicom, imgIndex]);"                                                                                                                                                                                                                                                                                                                                                                                      
                                                                        )                                                     
                                                                vuetify.VCardText("NoduleId:<b>{{imgIndex}}</b><br>OOD:<b>{{item.log_loss[imgIndex]}}</b>",style="font-size: 16px; text-align: center; margin-top: 60px; margin-padding:2px",v_html=True) 
                                                                                                                                                                              
                                                                                                                                                                                              
                # Right Column for the dynamic grid tables for configuration and view                                                                                                                                                                                                                                                        
                with vuetify.VCol(xs="12", sm="12", md="4", lg="4",xl="3"):                                                                                                                                                                                                                                                                              
                    
                    with vuetify.VRow(classes="justify-start"):                                                                                                                                          
                        vuetify.VSubheader("Threshold Config:",style="font-size: 18px;font-weight: bold;color: rgb(8, 24, 168);") 
                        vuetify.VSpacer()                                                                                                                                                                                                                                                
                        with vuetify.VBtn(color="#0000FF", click=self.refresh_data, size=20,):                                                                                                                                                                                                                                                                                  
                            vuetify.VIcon("mdi-refresh",                                                                                                                          
                            color="white",                                                                                                                            
                            size=35,                                                                                                                                  
                            classes="d-flex align-center justify-center",)

                    with vuetify.VRow(classes="justify-start"):                                                                                                                  
                        vuetify.VDataTable(**self.table_subset_range,style="width: 100%;")                                                                                                               
                                                                                                                                                             
                    with vuetify.VRow(classes="justify-start"):                                                                                                                                          
                        vuetify.VSubheader("Threshold View:",style="font-size: 18px;font-weight: bold;color: rgb(8, 24, 168);margin-top: 15px;")                                                                                                                                                                                                                                                                                                                                                                                                           
                    
                    with vuetify.VRow(classes="justify-center"):                                                                                                                                                                                                                                                                       
                        vuetify.VIcon("mdi-plus",                                                                                                                             
                        color="blue",                                                                                                                         
                        click=self.add_subset,                                                                                                                
                        style="border: 2px solid blue; border-radius: 40%; padding: 5px; color: rgb(8, 24, 168);",                                                                                                                                                                                  
                        classes="d-flex align-center justify-center", size=30)                                                                                                              
                                                                                                                                                 
                    with vuetify.VRow(classes="justify-start"):                                                                                                                  
                        with vuetify.VDataTable(**self.table_config, style="width: 100%;"):                                                                                                               
                                     
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
                                #step=0.1,
					        )  
                    with vuetify.VRow(classes="justify-center"):     
                        with vuetify.VBtn("Compare Images",color="#f0f0f0",                                                                                                                                                                                                                                 
                                #to = "compare/",    
                                click="""
                                trigger('compare_page')
                                $router.push('/compare')
                                """,                                                                                                                                                                                          
                                size=70,                                                                                                                                              
                                style="color: black; font-weight: bold; width: 200px; height: 40px; padding:20px;",                                                                                                                                                                                                                  
                                classes="d-flex align-center justify-center",):                                                                                                                                                                                                                                        
                                vuetify.VIcon("mdi-compare",                                                                                                                      
                                color="black",                                                                                                                                    
                                size=30,   
                                #click="trigger('compare_page')",                                                                                                                                       
                                classes="d-flex align-center justify-center",) 
                                                                                                                                                                                                                                                                                                                                                                                                                                                             
                                                                                                                                                                                              
        # Data route                                                                                                                                                                          
        with RouterViewLayout(self.server, "/data", style="max-width: 100%; max-height:100%; padding: 0; margin: 0;"):                                                                                                                                                                                                                                                           
            with vuetify.VRow(style="width: 100%; padding-top: 2px; margin: 0;"):                                                                                                                                                                                                                                                                                                                          
                with vuetify.VBtn("Take me back", click="$router.back()", style="margin: 5px; font-size: 16px; padding-left:8px;"):                                                                                                                                                                                                                                                                                           
                    vuetify.VIcon("mdi-arrow-left-bold", color="red", size=25)                                                                                                                                                                                                                                                                                         
            with vuetify.VRow(style="display: flex; justify-content: center;"):
                with vuetify.VContainer(style="overflow-x: auto; white-space: nowrap; overflow-y: hidden; padding-right: 15px; max-width: 100%; max-height:100%"):  
                        with vuetify.VRow(style="display: flex; justify-content: space-between;"):  
                            # Left Column (Images)
                            with vuetify.VCol(xs="12", sm="12", md="3", lg="5", xl="5"):  
                                with vuetify.VRow(style="justify-content: center; align-items: center; padding-top: 5px; padding-bottom:10px;"):
                                    vuetify.VSubheader("Selected Image:", style="font-size: 28px; font-weight: bold; color: rgb(0, 71, 171);")
                                with vuetify.VRow(style="justify-content: center; align-items: center; padding-top: 5px;"):
                                    with vuetify.VCard():
                                        vuetify.VCardText("Nodule ID: <b>{{selected_nodule}}</b>", style="font-size: 25px; text-align: center; padding: 10px; color: black;", v_html=True)
                                        vuetify.VCardText("OOD Score: <b>{{ood}}</b>", style="font-size: 25px; text-align: center; padding: 10px; color: black;", v_html=True)
                                           
                                with vuetify.VContainer(fluid=True):
                                    with vuetify.VRow(align="center", justify="center"):
                                        # Left Column: Original Scan
                                        with vuetify.VCol(cols="6"):
                                            with vuetify.VCard(class_="d-flex flex-column align-center", style="margin-top:30px; padding: 5px; height: 100%;"):
                                                vuetify.VCardText("ORIGINAL SCAN", style="font-size: 20px; font-weight: bold; text-align: center; padding-bottom: 5px; color: rgb(0, 71, 171);")
                                                with vuetify.Template(v_for="(dicom, dicomIndex) in image_items.Original_Dicom", key="dicomIndex"):
                                                    vuetify.VImg(
                                                        src=("dicom", lambda name: f"{name}"),
                                                        lazy_src="http://picsum.photos/id/114/320/320",
                                                        alt=("Selected Dicom Image"),
                                                        style="width: 320px; height: 320px; object-fit: contain; padding: 5px; display: block; margin: 0 auto;",  # Ensures the image is centered
                                                        eager=False,
                                                    )

                                        # Right Column: Lesion Mask
                                        with vuetify.VCol(cols="6"):
                                            with vuetify.VCard(class_="d-flex flex-column align-center", style="margin-top:30px; padding: 5px; height: 100%;"):
                                                vuetify.VCardText("LESION MASK", style="font-size: 20px; font-weight: bold; text-align: center; padding-bottom: 5px; color: rgb(0, 71, 171);")
                                                with vuetify.Template(v_for="(segment, segmentIndex) in image_items.Segmented_Nodule", key="segmentIndex"):
                                                    vuetify.VImg(
                                                        src=("segment", lambda name: f"{name}"),
                                                        lazy_src="http://picsum.photos/id/114/320/320",
                                                        alt=("Selected Max Slice Image"),
                                                        style="width: 320px; height: 320px; object-fit: contain; padding: 5px; display: block; margin: 0 auto;",  # Ensures the image is centered
                                                        eager=False,
                                                    )



                                         

                            # Right Column (Table)
                            with vuetify.VCol(xs="12", sm="12", md="9", lg="7", xl="7"):
                                with vuetify.VRow(style="justify-content: center; align-items: center; padding-top: 20px;"):
                                    vuetify.VSubheader("Image Features:", style="font-size: 28px; font-weight: bold; color: rgb(0, 71, 171);")

                                with vuetify.VRow(style="display: flex; flex-wrap: nowrap; white-space: nowrap; align-items: flex-start; justify-content: center",):
                                    with vuetify.VContainer(style="max-height:900px;max-width:100%; overflow-x: auto; overflow-y:auto; padding: 2px; border: 2.5px solid black; margin: 5px; justify-content: end;"):
                                        with vuetify.VSimpleTable(style="padding-left: 100px;",):
                                            with html.Thead():
                                                with html.Tr():
                                                    html.Th(children=["FEATURES"], classes="font-weight-bold", style="font-size: 22px;color: rgb(0, 71, 171); ")
                                                    html.Th(children=["FEATURE DATA"], classes="font-weight-bold", style="font-size: 22px;color: rgb(0, 71, 171);")
                                            with html.Tbody():
                                                with vuetify.Template(v_for="(value, key) in image_details", key="key"):
                                                    with html.Tr():
                                                        html.Td(children=["{{ value.Property }}"], classes="font-weight-bold", style="font-size: 20px;")
                                                        html.Td(children=["{{ value.Value }}"], style="font-size: 18px;")
                    
            
        # Compare Images route                                                                                                                                                                                                                                                                                                                             
        with RouterViewLayout(self.server, "/compare/", style="width: 100%; padding-bottom: 20px; margin: 0;"):   
            with vuetify.VRow():                                                                                                                                                                                                                                                                                                                         
                with vuetify.VBtn("Take me back", 
                #click="$router.back()",
                click = """trigger('restore_checkboxed_state')
                $router.back()""", style="margin: 10px; justify-content: flex-start; align-items: center; font-size: 16px; padding-left:10px;"):                                                                                                                                                                                                                                                                                           
                    vuetify.VIcon("mdi-arrow-left-bold", color="red", size=25)  
            
            with vuetify.VRow(v_if="compare_images.length > 0 && compare_details.length > 0",
                style="display: flex; justify-content: center; align-items: center;",):                                                                                                                                                                                                                                                                                   
                vuetify.VSubheader("Image Comparison:", style="font-size: 28px; font-weight: bold; color: rgb(0, 71, 171); justify-content: center; align-items: center;")
                                
                # Container for Images
                with vuetify.VContainer(style="overflow-y: auto; overflow-x:hidden; max-height: 100%; max-width: 100%; display: flex; justify-content: center; align-items: center;", classes="d-flex flex-column flex-md-row"):
                    with vuetify.VCol(cols="auto", style="flex: 0 0 auto; max-width: 300px; justify-content: center; align-items: center; max-height: 400px; padding: 45px;"):
                        with vuetify.VRow(style="display: flex; flex-direction: column; align-items: center; margin-bottom: 10px;"):    
                            with vuetify.VCardText("Original Scan", style="font-size: 20px; text-align: start; padding-bottom: 70px; color: rgb(0, 71, 171);"):
                                vuetify.VIcon("mdi-arrow-right-bold", color="rgb(0, 71, 171)", size=25)
                            with vuetify.VCardText("Lesion Mask", style="font-size: 20px; color: rgb(0, 71, 171); text-align: start; padding-top: 110px;"):
                                vuetify.VIcon("mdi-arrow-right-bold", color="rgb(0, 71, 171)", size=25)

                    with vuetify.Template(v_for="(item, index) in compare_images", key="index"):
                        with vuetify.VCol(cols="auto", style="flex: 0 0 auto; padding-top: 5px; max-width: 300px; padding-right:30px; padding-left: 30px; text-align: center;"):
                            with vuetify.VCard(style="padding-left:20px; padding-right:20px; padding-top:0;"):
                                vuetify.VCardText("OOD: <b>{{ item.OOD_Score }}</b>", style="font-size: 20px; text-align: center; color: black;", v_html=True)
                                with vuetify.Template(v_for="(dicom, dicomIndex) in item.Original_Dicom", key="dicomIndex"):
                                    vuetify.VImg(
                                        src=("dicom", lambda name: f"{name}"),
                                        lazy_src="http://picsum.photos/id/114/200/200",
                                        alt=("dicom", lambda img: f"{img}"),
                                        style="width: 200px; height: 200px; object-fit: contain;",
                                        )
                                with vuetify.Template(v_for="(img, imgIndex) in item.Segmented_Nodule", key="imgIndex"):
                                    vuetify.VImg(
                                        src=("img", lambda name: f"{name}"),
                                        lazy_src="http://picsum.photos/id/114/200/200",
                                        alt=("img", lambda img: f"{img}"),
                                        style="width: 200px; height: 200px; object-fit: contain;",
                                        )

                # Container for Features Table
                with vuetify.VRow():
                    with vuetify.VContainer(style="overflow-y: auto; overflow-x:auto; max-height: 400px; max-width: 100%; margin-right:50px; margin-left:50px; justify-content: center; align-items: center;", classes="d-flex flex-column flex-md-row"):
                        with vuetify.VCol(cols="auto", style="flex: 0 0 auto; max-width: 340px; max-height: 850px; padding: 50px "):        
                            with vuetify.VCard(style="margin-top:160px;"):
                                with vuetify.VSimpleTable():
                                    with html.Thead():
                                        with html.Tr():
                                            html.Th("FEATURES", 
                                            classes="font-weight-bold", style="font-size:18px; text-align: left; color: rgb(0, 71, 171);",)
                                    with html.Tbody():
                                        with vuetify.Template(v_for="(feature, featureIndex) in compare_details[0]", key="featureIndex"):
                                            with html.Tr():
                                                html.Td("{{ feature.Property }}", style="font-size: 16px; text-align: left;", classes="font-weight-bold")

                        # Feature Data Table (Inside Feature Container)
                        with vuetify.VRow(style="flex: 0 0 auto; justify-content: center; align-items: center;"):
                            with vuetify.Template(v_for="(item, index) in compare_images", key="index"):
                                with vuetify.VCol(cols="auto", style="flex: 0 0 auto; padding-top: 15px; padding-bottom:50px; max-height:850px; max-width: 300px; text-align: center; margin-top:370px"):
                                    with vuetify.VCard():
                                        with vuetify.VSimpleTable(style="margin-top: 10px;"):            
                                                with html.Thead():
                                                    with html.Tr():
                                                        html.Th("FEATURE DATA", classes="font-weight-bold", style="font-size:18px; text-align: left; color: rgb(0, 71, 171);")
                                                with html.Tbody():
                                                    with vuetify.Template(v_for="(feature, featureIndex) in compare_details[index]", key="featureIndex"):             
                                                        with html.Tr():
                                                            html.Td("{{ feature.Value }}", style="font-size: 16px; text-align: left;")

            with vuetify.VRow(v_else=True):    
                        with vuetify.VRow(style="display: flex; justify-content: center; align-items: center; padding-top: 30px;"):
                            with vuetify.VCard(style="max-height: 700px;"):
                                with vuetify.Template(v_for="(item, index) in no_image", key="index"):
                                    vuetify.VImg(
                                        src=("item", lambda name: f"{name}"),
                                        lazy_src="http://picsum.photos/id/114/500/500",
                                        alt="No Image Selected",
                                        style="width: 600px; height: 600px; object-fit: contain; justify-content: center; align-items: center;",
                                        eager=True,
                                    )
                                with vuetify.VCardText(style="font-size: 20px; text-align: center;"):
                                    vuetify.VAlert(
                                    "No image selected. Please choose an image to continue.",
                                    type="warning",
                                    prominent=True,
                                    icon="mdi-alert",
                                    style="font-size: 16px; margin-bottom: 20px; justify-content: center; align-items: center;"
                                )
                            

        # Main layout and navigation drawer                                                                                                                                                   
        #with SinglePageWithDrawerLayout(self.server) as layout:                                                                                                                              
        with SinglePageLayout(self.server) as layout:                                                                                                                                         
            layout.title.set_text(self.server.name)                                                                                                                                                                                                                                                                
            # Drawer for navigation                                                                                                                                                           
            '''with layout.drawer:                                                                                                                                                            
                    layout.drawer.style = "background-color: #f0f0f0; max-height: 400;"                                                                                                                                                                                       
                    with vuetify.VList(shaped=True, dense=True, style="max-width: 100%;"):                                                                                                                                                                                    
                            #vuetify.VIcon("mdi-refresh", color="black", size="20px", classes="d-flex align-center justify-center",padding="2px", click=self.refresh_drawer)                                                                                                                                                                                  
                            vuetify.VSubheader("Routes", style="font-size: 18px;color: black;")                                                                                                                                                                              
                                                                                                                                                                                              
                            # Define navigation links for routing                                                                                                                             
                                                                                                                                                                                              
                            with vuetify.VListItem(to="/"):                                                                                                                                   
                                vuetify.VIcon("mdi-home",color= "#00008B", size= "20px",classes="d-flex align-center justify-center",padding="2px")                                                                                                                       
                                with vuetify.VListItemContent():                                                                                                                          
                                    vuetify.VListItemTitle("Home",style="font-size: 20px;padding: 2px;")                                                                                                                                                                  
                                                                                                                                                                                              
                            if self.state.data_view_visible:                                                                                                                                  
                                #self.server.state.dirty("data_view_visible")                                                                                                                 
                                with vuetify.VListItem(to="/data/None/None"):                                                                                                                 
                                    vuetify.VIcon("mdi-database",color= "#00008B", size= "20px",classes="d-flex align-center justify-center",padding="2px")                                                                                                                   
                                    with vuetify.VListItemContent():                                                                                                                          
                                        vuetify.VListItemTitle("Data View",style="font-size: 20px;padding: 2px;")       

                            if self.state.compare_view_visible:                                                                                                                               
                                with vuetify.VListItem(to="/compare"):                                                                                                                        
                                    vuetify.VIcon("mdi-compare",color= "#00008B", size= "20px",classes="d-flex align-center justify-center",padding="2px")                                                                                                                    
                                    with vuetify.VListItemContent():                                                                                                                          
                                        vuetify.VListItemTitle("Compare Images",style="font-size: 20px;padding: 2px;")'''                                                                                                                                                     
                                                                                                                                                                                              
        # Main content area                                                                                                                                                               
            with layout.content:                                                                                                                                                              
                with vuetify.VContainer(fluid=True, style="padding-left: 0px;"):                                                                                                                
                        router.RouterView(                                                                                                                                                        
                        style="padding-left: 20px; margin: 0px; width: 100%; height: 100%; box-sizing: border-box;",)            

    # ---------------------------------------------------------------------------------------------                                                                                                                                                                                                                                                                                             
    # Method to start a new server (main). Not to be used in a multi-process environment                                                                                                                                                                                                                                                                                                    
    # ---------------------------------------------------------------------------------------------                                                                                                                                                                                                                                                                                         
                                                                                                                                                                                              
    @abstractmethod                                                                                                                                                                           
    def start_server_immediately(self):                                                                                                                                                       
        print(f"Starting Server_Manager at http://localhost:{self.port}/index.html")                                                                                                                                                                                                                                                                                                        
        #self.server.start(exec_mode="main", port=self.port)                                                                                                                                  
        #self.server.start(host="0.0.0.0", port=self.port, auth_key="key", username = "admin", password = "admin", client_ip = "127.0.0.1", allowed_ips=["75.102.253.4","76.136.2.21"])                                                                                                                        
        self.server.start(host="0.0.0.0", port=self.port)

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
    '''@abstractmethod                                                                                                                                                                           
    def fetch_data(self):                                                                                                                                                                     
        pass'''                                                                                                                                                                                  
                                                                                                                                                                                                                                                                                                                                                                                        
                                                                                                                                                                                              
# -----------------------------------------------------------------------------                                                                                                               
# Main (Guard)                                                                                                                                                                                
# -----------------------------------------------------------------------------                                                                                                               
                                                                                                                                                                                              
if __name__ == "__main__":                                                                                                                                                                    
    server = BaseOoDHistogram("Ood Visualizer", 8091, "MaxSlices_wOoDScore.csv", "LIDC_Dataset", "lidc_pixConvImg", "Log_Loss_ALL","StudyInstanceUID","SeriesInstanceUid","imageSOP_UID","noduleID")                                                                                                                                                                                                                              
    server.start_server_immediately()                                                                                              
