# Core libraries for data processing                                                                                                      #
import os                                                                                                                                                                                                                                                                                                                                                 
import numpy as np # type: ignore                                                                                                                                                             
import pandas as pd # type: ignore                                                                                                                                                            
import matplotlib.pyplot as plt  # type: ignore                                                                                                                                               
from matplotlib.patches import FancyArrowPatch # type: ignore  
from trame.widgets.matplotlib import Figure                                                                                                                               
import pydicom # type: ignore                                                                                                                                                                 
#from PIL import Image # type: ignore 


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
        self.state.thresholds = [1.0001, 2.0001, 3.0001, 4.0001] 
        self.state.check = False
        self.state.add=True
        

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
        self.state.image_paths=[]                                                                                                                                                             
        self.state.final_path=[]                                                                                                                                                                                                                                                                                                                     
        self.state.ood = ""
        self.state.selected_nodule ="" 
        self.state.image_items={}                                                                                                                                                             
        self.state.image_details=[] 
        self.state.compare_details=[]                                                                                                                                                                                                                                                                                                                      
        self.state.checkboxed_images=[] 
        self.state.compare_images=[]
        self.df = pd.DataFrame()                                                                                                                                                                                                                                                                                                                             
        self.data = []                                                                                                                                                                        

        # Tables for UI Layout                   
        self.state.subset_config = [                                                                                                                                                          
                {"text": "Index", "value": "index"},                                                                                                                                              
                {"text": "Name", "value": "name"},                                                                                                                                                
                {"text": "Threshold", "value": "threshold"},                                                                                                                                      
                {"text": "Actions", "value": "actions"},                                                                                                                                          
            ]                                                                                                                                                                                     
                                                                                                                                                                                              
        self.table_config = {                                                                                                                                                                        
            "headers": ("subset_config", self.state.subset_config),                                                                                                                           
            "items": ("subset_items", self.state.subset_items),                                                                                                                                                                                                                                                                                         
            "classes": "elevation-1 ma-4",                                                                                                                                                    
            "multi_sort": True,                                                                                                                                                               
            "dense": True,                                                                                                                                                                    
            #"dark": True, 
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
            #"dark": True,
            
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

        self.register_triggers()
        self.render_ui_layout()
        self.update_range_count()  
                                                                                                                                                                                                                                                                                                                      
    # ---------------------------------------------------------------------------------------------                                                                                                                                                                                                                                                                                      
    # Method to get the figure size (static method).                                                                                                                                          
    # ---------------------------------------------------------------------------------------------                                                                                                                                                                                                                                                                                                                                                                                                                                                            
    def get_figure_size(self):                                                                                                                                                                
        return {"figsize": (10, 6), "dpi": 110}  

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
        
        log_values = np.log10(self.hist)
        log_values_clean = np.where(np.isinf(log_values), 0, log_values)
        
        ax.bar(self.bin_edges[:-1], log_values_clean , width=np.diff(self.bin_edges), align='edge', edgecolor='black', color="#00a8e8")
        
        yticklabels = []
        for x in ax.get_yticks():
            x = round(x, 1)
            if x==0.0 or x == 1.0 or x == 2.0 or x == 3.0 or x == 4.0:
                yticklabels.append(f'10^{int(x)}')
            else:
                yticklabels.append('')
        ax.set_yticklabels(yticklabels)
    
        ax.set_xlim(left=0)
        #ax.set_xlim(left=min_bin, right=max_bin)
        
        y_limits = ax.get_ylim() 
        #new_ymax = y_limits[1] + (y_limits[1] - y_limits[0]) * 0.1  # Increase the upper limit y_limit[1] by 10%
        #ax.set_ylim(y_limits[0], new_ymax) 
                                                                                                                                            
        colors= ['#006400','#873e23','blue','red']                                                                                                                                            
        OOD_sections = [subset["name"] for subset in self.state.subset_items]
        if extra_lines:
            for i, line in enumerate(extra_lines):
                line_color = colors[i % len(colors)]  
                ax.plot([line, line], y_limits, color=line_color, linestyle='--') 
                if i==0:                                                                                                                                                                      
                    section_text = OOD_sections[0]                                                                                                                                                                                                                                                                                                                                 
                    arrow = FancyArrowPatch((0, y_limits[1] * 0.97),  # Start at the y-axis (x=0)                                                                                                                                                                                                                                                                                     
                            (line, y_limits[1] * 0.97),  # End at the position of the first line                                                                                                                                                                                                                                              
                            color=line_color,                                                                                                                                     
                            arrowstyle='<->',                                                                                                                                     
                            mutation_scale=15,                                                                                                                                    
                            alpha=0.5)                                                                                                                                            
                    ax.add_patch(arrow)                                                                                                                                                                                                                                                                                                                               
                else:                                                                                                                                                                                                                                                                                                                            
                    section_text = OOD_sections[(i)]                                                                                                                                                                                                                                                                                                             
                if i > 0:  # Draw an arrow only if there's a previous line                                                                                                                    
                    arrow = FancyArrowPatch((line, y_limits[1] * 0.97 ),                                                                                                                       
                                            (extra_lines[i - 1], y_limits[1] * 0.97),                                                                                                                                                                                                                                                          
                                            color=line_color,                                                                                                                                 
                                            arrowstyle='<->',                                                                                                                                 
                                            mutation_scale=15, alpha=0.5)                                                                                                                                                                                                                                                                                               
                    ax.add_patch(arrow)                                                                                                                                                                                                                                                                                                                    
                ax.text(line-0.5, y_limits[1] * 1.0, section_text, color=line_color, horizontalalignment='center', verticalalignment='bottom',fontsize=18 )                                                                                                                                                                                                                                                                                                                                                                              
            
            # Ood Arrow from the first extra line to the end of the x-axis                                                                                                                    
            last_arrow = FancyArrowPatch(                                                                                                                                                     
                (extra_lines[0], y_limits[1] * 0.92),  # Start from first extra line                                                                                                                                    
		        (self.state.thresholds[-1], y_limits[1] * 0.92),  # End at the max x-axis value                                                                                                                                                                                                                                                                          
                color='black', arrowstyle='simple', mutation_scale=15, alpha=0.5)                                                                                                                                                                                                                                                                                          
            ax.add_patch(last_arrow)                                                                                                                                                          
            ax.text((extra_lines[0] + self.state.thresholds[-1]) / 2 , y_limits[1] * 0.90, 'OoD', color='black', horizontalalignment='center', verticalalignment='top',fontsize=18)                                                                                                               
        
        ax.tick_params(axis='x', labelsize=14)  # Set x-axis tick label size
        ax.tick_params(axis='y', labelsize=14)  # Set y-axis tick label size
        ax.set_title('OoD Scores Distribution', fontsize=19, fontweight='bold', color='black', loc='center')                                               
        ax.set_xlabel('OoD Scores', fontsize=16)                                                                                                                                              
        ax.set_ylabel('Frequency', fontsize=16)  
        fig.tight_layout()                                                                                                               
        return fig       

    # ---------------------------------------------------------------------------------------------                                                                                                                                                                                                                                                                                    
    # Method to update the range count.                                                                                                                                                       
    # ---------------------------------------------------------------------------------------------                                                                                                                                                                                                                                                                                                                                                                                                                                                                         
    def update_range_count(self):
        self.state.range_item.clear() 
        for i, item in enumerate(self.state.subset_items):
            if i == 0:
                start = round(min(self.data),4)
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
                "name": f"Subset{len(self.state.subset_items) + 1}(OoD)",
                "range": f"({float(last_threshold)} , {round(max(self.data),4)} ]",
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
                    self.state.add = True
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
                start = round(min(self.data),4)                                                                                                                                                             
            else:                                                                                                                                                                             
                start = self.state.subset_items[i - 1]["threshold"]                                                                                                                           

            end = subset["threshold"]  
                                                                                                                                                                     
            if start < end:          
                filtered_df = self.df[(self.df[self.state.ood_column] > start) & (self.df[self.state.ood_column] <= end)]
                mappings = [
                    (
                        row[self.state.node_id],  # Nodule ID
                        row[self.state.study_column],
                        row[self.state.series_column],
                        row[self.state.image_column],  # SOP UID
                        row[self.state.ood_column]  # OoD Score
                    )
                    for _, row in filtered_df.iterrows()
                    ]
                mappings.sort(key=lambda x: x[4]) # Sort results by OoD score (ascending)

                list_all = []
                for item in mappings:
                    nodule_id = item[0]
                    dicom = f"http://{SERVER_IP}:{PORT}{settings.MEDIA_URL}dicom_images/{item[3]}.png"
                    img = f"http://{SERVER_IP}:{PORT}{settings.MEDIA_URL}lidc_pixConvImg/{nodule_id}.png"

                    list_all.append([nodule_id, dicom, img, round(float(item[4]), 4)])

                items = {
                    "name": f"Subset{i + 1}",
                    "range": f"({float(start)} , {float(end)}]",
                    "download": mappings,
                    "new": list_all  
                    }

                self.state.data_items.append(items)               
    
        if self.state.subset_items:
                last_threshold = self.state.subset_items[-1]["threshold"]
                max_value = round(np.nanmax(self.data),4)

                if last_threshold <= max_value:
                    rem_filtered_df = self.df[(self.df[self.state.ood_column] > last_threshold) & (self.df[self.state.ood_column] <= max_value)]
                    rem_mappings = [
                    (
                        row[self.state.node_id],  # Nodule ID
                        row[self.state.study_column],
                        row[self.state.series_column],
                        row[self.state.image_column],  # SOP UID
                        row[self.state.ood_column]  # OoD Score
                    )
                    for _, row in rem_filtered_df.iterrows()
                    ]

                    rem_mappings.sort(key=lambda x: x[4])

                    rem_list_all = []
                    for item in rem_mappings:
                        nodule_id = item[0]  
                        dicom = f"http://{SERVER_IP}:{PORT}{settings.MEDIA_URL}dicom_images/{item[3]}.png"
                        img = f"http://{SERVER_IP}:{PORT}{settings.MEDIA_URL}lidc_pixConvImg/{nodule_id}.png"
                        rem_list_all.append([nodule_id, dicom, img, round(float(item[4]),4)])
                    
                    remaining_item= {
                        "name": f"Subset{len(self.state.subset_items) + 1}(OoD)",
                        "range": f"({float(last_threshold)} , {max_value}]",
                        "download": rem_mappings,
                        "new": rem_list_all
                        }

                    self.state.data_items.append(remaining_item)
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
                self.state.add=False
                print("Cannot add more subsets. Maximum threshold reached.")
                return
        else:
            new_line = self.state.thresholds[0] # First subset, pick the smallest threshold
        
        new_item = {
            "index": len(self.state.subset_items) + 1,
            "name": f"Subset{len(self.state.subset_items) + 1}",
            "threshold": round(float(new_line), 4),
            "actions": "Remove"
        }
        self.state.subset_items.append(new_item)
        self.server.state.dirty("subset_items") 
        #print(self.state.subset_items)
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
        self.ctrl.trigger("add_subset")(self.add_subset)                                                                                                                                                                                                                                    
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
            self.state.check = False
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
        self.state.check=True
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
                        })
                    self.server.state.dirty("compare_images")
                    self.all_node_ids = self.df[self.state.node_id] 
                    for i, node_id in enumerate(self.all_node_ids):                                                                                                                                       
                        if str(node_id) == str(imgIndex):                                                                                                                                                 
                            compare_data = self.df.iloc[i].to_dict()                                                                                                                                          
                            break 
                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                           
                    compare_info = { **compare_data }  
                    details = [{"Property": "Nodule ID", "Value": imgIndex}] 
                    details += [{"Property": "OOD Score", "Value": ood}]                                                                                                                                                          
                    details += [{"Property": key, "Value": value} for key, value in compare_info.items()]
                    self.state.compare_details.append(details)
            
            self.server.state.dirty("compare_details")
            #print(f"Details: {self.state.compare_details}")

        else:
            self.state.compare_images = []

    # ---------------------------------------------------------------------------------------------                                                                                                                                                                                                                                                                                         
    # UI layout                                                                                                                                                                               
    # ---------------------------------------------------------------------------------------------                                                                                                              
                                                                                                                                                                                                                                                                                                                                                                   
    def render_ui_layout(self):                                                                                                                                                                  
        with RouterViewLayout(self.server, "/"):                                                                                                                                                                                                                                                                                                                          
            with vuetify.VContainer(fluid=True, classes="d-flex flex-column flex-md-row",style="max-width: 100%; padding-bottom:10px"):                                                                                                                                                                                                                                   
                # Left Column for the figure and data                                                                                                                                                                                                                                                                                             
                with vuetify.VCol(xs="12", sm="12", md="7", lg="7",xl="7"):                                                                                                                                                                                                                                                                          
                    with vuetify.VRow(classes="justify-start"):
                        vuetify.VIcon("mdi-information", style="color: grey;", classes="d-flex align-center justify-center", size=30, 
                            click="""
                                alert('Use + button to add subsets. Click on any image to view its properties. Checkbox and click Compare Images button to compare multiple images.')     
                                """)           

                    with vuetify.VRow(classes="justify-start"):                                                                                                                                                                                                                                                                                                  
                        vuetify.VSubheader("Visualization:",style="font-size: 20px;font-weight: bold;color: rgb(0, 71, 171); padding:0; margin:0;")                                                                                                                                                                                                                                           
                        # Matplotlib Figure 
                    with vuetify.VRow(classes="justify-start"):                                                                                                                                      
                        self.html_figure = Figure(style="position: relative; padding-top: 5px; margin: 0; display: block; align-self: flex-start; justify-content: start;")                                                                                                                                                                                                                                                                                                    
                
                # Right Column for the dynamic grid tables for configuration and view                                                                                                                                                                                                                                                        
                with vuetify.VCol(xs="12", sm="12", md="5", lg="5",xl="5"):                                                                                                                                                                                                                                                                              
                    
                    with vuetify.VRow(classes="justify-start"):                                                                                                                                          
                        vuetify.VSubheader("Threshold View:",style="font-size: 20px;font-weight: bold;color: rgb(8, 24, 168);") 
                        vuetify.VSpacer()                                                                                                                                                                                                                                                
                        with vuetify.VBtn(color="#0000FF", click=self.refresh_data, size=20,):                                                                                                                                                                                                                                                                                  
                            vuetify.VIcon("mdi-refresh",                                                                                                                          
                            color="white",                                                                                                                            
                            size=35,                                                                                                                                  
                            classes="d-flex align-center justify-center",)

                    with vuetify.VRow(classes="justify-start"):                                                                                                           
                        with vuetify.VRow(classes="text-h4 font-weight-bold",):
                            vuetify.VDataTable(**self.table_subset_range,style="width: 100%; font-size:26px",)
                                                                                                                                         
                    with vuetify.VRow(classes="justify-start"):                                                                                                                                          
                        vuetify.VSubheader("Threshold Configuration:",style="font-size: 20px;font-weight: bold;color: rgb(8, 24, 168);margin-top: 5px;")                                                                                                                                                                                                                                                                                                                                                                                                           
                    
                    with vuetify.VRow(classes="justify-center"):   
                        vuetify.VIcon("mdi-plus",                                                                                                                             
                        color="blue",                                                                                                                         
                        click= 
                        """
                        if(add) {trigger('add_subset')} 
                        else {alert('Cannot add more subsets. Maximum threshold reached.')}""",                                                                                                                
                        style="border: 2px solid blue; border-radius: 40%; padding: 5px; color: rgb(8, 24, 168);",                                                                                                                                                                                  
                        classes="d-flex align-center justify-center", size=30)                                                                                                              
                                                                                                                                                 
                    with vuetify.VRow(classes="justify-start"): 
                        with vuetify.VRow(classes="text-h4 font-weight-bold",):                                                                                                                 
                            with vuetify.VDataTable(**self.table_config, style="width: 100%; font-size: 26px;",):                                                                                                              
                                with vuetify.Template(                                                                                                                                
                                actions="{ item }",                                                                                                                                   
                                __properties=[("actions", "v-slot:item.actions")],                                                                                                                                                                                                                                                                                                  
                                ):                                                                                                                                                    
                                    vuetify.VIcon("mdi-delete", color="red", click="trigger('remove_subset', [item.index])",style="cursor: pointer;",)                                                                                                              
                                                                                                                                                        
                                with vuetify.Template(                                                                                                                                
                                threshold="{ item }",                                                                                                                                 
                                __properties=[("threshold", "v-slot:item.threshold")],                                                                                                                                                                                                                                                                                              
                                ):                                                                                                                                                    
                                    vuetify.VTextField(                                                                                                                               
                                    v_model=("item.threshold",),                                                                                                                      
                                    type="number",                                                                                                                                    
                                    dense=True,                                                                                                                                       
                                    hide_details=True,
                                    min = "thresholds[0]",
                                    max= "thresholds[thresholds.length-1]",
                                    change="trigger('update_threshold', [item.index, item.threshold])",                                                                                                                                                                                                                                   
                                    classes="d-flex align-center",                                                                                                                    
                                    step="any",
                                )  
                    with vuetify.VRow(classes="justify-center"):     
                        with vuetify.VBtn("Compare Images",color="#f0f0f0",                                                                                                                                                                                                                                 
                                #to = "compare/",    
                                click="""
                                if (check) {
                                trigger('compare_page')
                                $router.push('/compare')
                                }
                                else {
                                alert('Oops!! No Images selected for comparison.')
                                }
                                """,                                                                                                                                                                                          
                                size=70,                                                                                                                                              
                                style="color: black; font-weight: bold; width: 200px; height: 40px; padding-top:5px;",                                                                                                                                                                                                                  
                                classes="d-flex align-center justify-center",):                                                                                                                                                                                                                                        
                                vuetify.VIcon("mdi-compare",                                                                                                                      
                                color="black",                                                                                                                                    
                                size=30,   
                                #click="trigger('compare_page')",                                                                                                                                       
                                classes="d-flex align-center justify-center",) 
            
            with vuetify.VRow(classes="justify-start"):                                                                                                                                          
                vuetify.VSubheader("Data View:",style="font-size: 20px;font-weight: bold;color: rgb(0, 71, 171); padding-top:10px")                                                                                                                                                                                                                                                                                      
                                                                                                                                                                                                                                                                                
            with vuetify.VRow(classes="justify-start", style="padding:0"):                                                                            
                with vuetify.Template(v_for="(item, index) in data_items",key="index"): 
                    with vuetify.VCol(xs="12", sm="12", md="12", lg="12",xl="12"):                                                                                                                                                                                                                                                                                                                                                                                   
                        vuetify.VIcon(                                                                                                                            
                        "mdi-download",                                                                                                                   
                        color="blue",                                                                                                                     
                        click="utils.download('Subset_'+(index + 1)+'.csv','Nodule ID , Study Instance UID, Series Instance UID, Image SOP UID, OoD Score\\n'+item['download'].join('\\n'), 'text/csv')",                                                                                                                      
                        size=31, 
                        style="border: 2px solid blue; border-radius: 30%; padding: 2px; color: rgb(8, 24, 168);margin-top:5px;margin-bottom: 5px;",)                                                                                                                
                                                                                                                                                                                                                                                  
                        with vuetify.VRow():                                                                                                                      
                            html.Td("<b>{{item.name}}</b><br>Range: <b>{{ item.range }}</br>", classes="pa-4", style ="font-size: 20px; text-align: left; margin-top: 0px; margin-bottom: 0px;"),
                                                                                                                                                                
                        with vuetify.VContainer(style="overflow-x: auto; white-space: nowrap; overflow-y: hidden; padding-bottom: 2px; padding-left:10px; padding-right:40px; max-width:100%"):                                                                                                                                                                                         
                                with vuetify.VRow(style="display: flex; flex-wrap: nowrap; white-space: nowrap; align-items: flex-start; max-width:100%; padding-right:40px;",):                                                                                                                                                                                                                                                                                                                                                                                                     
                                    
                                    with vuetify.VCol(cols="auto", class_="d-inline-block", style="flex: 0 0 auto; padding: 0; max-width:100%;;align-items: flex-start"):
                                        vuetify.VCardText("Original CT Scan",style="font-size: 18px; text-align: center; margin-top: 85px;",v_html=True)
                                        vuetify.VCardText("Nodule Image",style="font-size: 18px; text-align: center; margin-top: 90px;",v_html=True)
                                        vuetify.VCardText("Nodule ID <br> OoD Score",style="font-size: 18px; text-align: center; margin-top: 60px;",v_html=True)

                                    with vuetify.Template(v_for="(entry, i) in item.new", key="i"):                                                                                                                                                            
                                        with vuetify.VCol(cols="auto", class_="d-inline-block", style="flex: 0 0 auto; padding: 5px; max-width:100%"):                                                                                                                                                               
                                            vuetify.VCheckbox(
                                                color="blue",
                                                change="trigger('checkbox_method',[entry[1],entry[0]])",
                                                style="padding:0; margin-left:60px",)
                                            with vuetify.VCard(style="padding-top: 0;padding-left:12px; max-height: 800px;"): 
                                                with vuetify.VRow(style="display: flex; flex-wrap: nowrap; white-space: nowrap; align-items: flex-start;padding-top:50px;padding-right:15px",):                                                                                                           
                                                    with vuetify.VBtn(
                                                        to=("'/data/'",), 
                                                        style="padding: 0; border: none; background: none; cursor: pointer;",
                                                        elevation=0,  
                                                        outlined=False, ):
                                                                                        
                                                        vuetify.VImg(                                                                                                                                                                                                                                                                                                                                                                                                                                                        
                                                        src=("entry[1]", lambda name: f"{name}"),                                                                                                                                                                                                                                                                                                                                                   
                                                        lazy_src="http://picsum.photos/id/114/150/150",                                                                                                                                                                                                                                                                                                                                           
                                                        alt=("entry[1]", lambda imgIndex: f"Dicom_Img{imgIndex}"),                                                                                                                                                                                                                                                                                                                               
                                                        style="width: 150px; height: 150px; object-fit: contain;",                                                                                                                                                                                                                                                                                                             
                                                        eager=False,                                                                                                                                                                                                                                                                                                                                                                      
                                                        click= "trigger('navigate_to_data_view', [entry[1], entry[0]])" )                                                                                                                                                                                                                                 
                                                                                            
                                                with vuetify.VRow(style="display: flex; flex-wrap: nowrap; white-space: nowrap; align-items: flex-start;padding-top:120px;padding-right:15px;",): 
                                                    with vuetify.VBtn(
                                                        to=("'/data/'",),  
                                                        style="padding: 0; border: none; background: none; cursor: pointer;",
                                                        elevation=0,  
                                                        outlined=False,  
                                                        ):                                                                                                           
                                                        vuetify.VImg(                                                                                                                                                                                                                                                                                                                                                                                                                                            
                                                        src=("entry[2]", lambda name: f"{name}"),                                                                                                                                                                                                                                                                                                                                                                                            
                                                        lazy_src="http://picsum.photos/id/114/150/150",                                                                                                                                                                                                                                                                                                                                                                                                       
                                                        alt=("entry[2]", lambda imgIndex: f"Img{imgIndex}"),                                                                                                                                                                                                                                                                                                                                                                                                 
                                                        style="width: 150px; height: 150px; object-fit: contain;",                                                                                                                                                                                                                                                                                                        
                                                        eager=False,                                                                                                                                                                                                                                                                                                                                                             
                                                        click= "trigger('navigate_to_data_view', [entry[1], entry[0]]);"                                                                                                                                                                                                                                                                                                                                                                                      
                                                        )                                                     
                                                vuetify.VCardText("<b>{{entry[0]}}</b><br><b>{{entry[3]}}</b>",style="font-size: 18px; text-align: center; margin-top: 60px; margin-padding:2px",v_html=True)                                                                                                                                                                                                                                                                                                                                                                                                                                     
                                                                                                                                                                                              
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
                                        vuetify.VCardText("OoD Score: <b>{{ood}}</b>", style="font-size: 25px; text-align: center; padding: 10px; color: black;", v_html=True)
                                           
                                with vuetify.VContainer(fluid=True):
                                    with vuetify.VRow(align="center", justify="center"):
                                        # Left Column: Original Scan
                                        with vuetify.VCol(cols="6"):
                                            with vuetify.VCard(class_="d-flex flex-column align-center", style="margin-top:30px; padding: 5px; height: 100%;"):
                                                vuetify.VCardText("ORIGINAL CT SCAN", style="font-size: 20px; font-weight: bold; text-align: center; padding-bottom: 5px; color: rgb(0, 71, 171);")
                                                with vuetify.Template(v_for="(dicom, dicomIndex) in image_items.Original_Dicom", key="dicomIndex"):
                                                    vuetify.VImg(
                                                        src=("dicom", lambda name: f"{name}"),
                                                        lazy_src="http://picsum.photos/id/114/320/320",
                                                        alt=("Selected Dicom Image"),
                                                        style="width: 320px; height: 320px; object-fit: contain; padding: 5px; display: block; margin: 0 auto;",  # Ensures the image is centered
                                                        eager=False,
                                                    )
                                    with vuetify.VRow(align="center", justify="center"):
                                        # Right Column: Nodule Image
                                        with vuetify.VCol(cols="6"):
                                            with vuetify.VCard(class_="d-flex flex-column align-center", style="margin-top:30px; padding: 5px; height: 100%;"):
                                                vuetify.VCardText("NODULE IMAGE", style="font-size: 20px; font-weight: bold; text-align: center; padding-bottom: 5px; color: rgb(0, 71, 171);")
                                                with vuetify.Template(v_for="(segment, segmentIndex) in image_items.Segmented_Nodule", key="segmentIndex"):
                                                    vuetify.VImg(
                                                        src=("segment", lambda name: f"{name}"),
                                                        lazy_src="http://picsum.photos/id/114/320/320",
                                                        alt=("Selected Max Slice Image"),
                                                        style="width: 280px; height: 280px; object-fit: contain; padding: 5px; display: block; margin: 0 auto;",  # Ensures the image is centered
                                                        eager=False,
                                                    )      

                            # Right Column (Table)
                            with vuetify.VCol(xs="12", sm="12", md="9", lg="7", xl="7"):
                                with vuetify.VRow(style="justify-content: center; align-items: center; padding-top: 20px;"):
                                    vuetify.VSubheader("Image Properties:", style="font-size: 28px; font-weight: bold; color: rgb(0, 71, 171);")

                                with vuetify.VRow(style="display: flex; flex-wrap: nowrap; white-space: nowrap; align-items: flex-start; justify-content: center",):
                                    with vuetify.VContainer(style="max-height:900px;max-width:100%; overflow-x: auto; overflow-y:auto; padding: 2px; border: 2.5px solid black; margin: 5px; justify-content: end;"):
                                        with vuetify.VSimpleTable(style="padding-left: 100px;",):
                                            with html.Thead():
                                                with html.Tr():
                                                    html.Th(children=["PROPERTIES"], classes="font-weight-bold", style="font-size: 22px;color: rgb(0, 71, 171); ")
                                                    html.Th(children=["VALUES"], classes="font-weight-bold", style="font-size: 22px;color: rgb(0, 71, 171);")
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
                    with vuetify.VCol(cols="auto", style="flex: 0 0 auto; margin-right:55px; max-width: 300px; justify-content: center; align-items: center; max-height: 400px; padding: 45px;"):
                        with vuetify.VRow(style="display: flex; flex-direction: column; align-items: center; margin-bottom: 10px;"):    
                            with vuetify.VCardText("Original CT Scan", style="font-size: 20px; text-align: start; padding-bottom: 70px; color: rgb(0, 71, 171);"):
                                vuetify.VIcon("mdi-arrow-right-bold", color="rgb(0, 71, 171)", size=25)
                            with vuetify.VCardText("Nodule Image", style="font-size: 20px; color: rgb(0, 71, 171); text-align: start; padding-top: 110px;"):
                                vuetify.VIcon("mdi-arrow-right-bold", color="rgb(0, 71, 171)", size=25)

                    with vuetify.Template(v_for="(item, index) in compare_images", key="index"):
                        with vuetify.VCol(cols="auto", style="flex: 0 0 auto; padding-top: 5px; max-width: 300px; padding-right:30px; padding-left: 30px; text-align: center;"):
                            with vuetify.VCard(style="padding-left:20px; padding-right:20px; padding-top:0;"):
                                with vuetify.Template(v_for="(dicom, dicomIndex) in item.Original_Dicom", key="dicomIndex"):
                                    vuetify.VImg(
                                        src=("dicom", lambda name: f"{name}"),
                                        lazy_src="http://picsum.photos/id/114/200/200",
                                        alt=("dicom", lambda img: f"{img}"),
                                        style="width: 200px; height: 200px; object-fit: contain;",
                                        )
                            with vuetify.VCard(style="padding-left:35px; padding-right:35px; padding-top:0;"):
                                with vuetify.Template(v_for="(img, imgIndex) in item.Segmented_Nodule", key="imgIndex"):
                                    vuetify.VImg(
                                        src=("img", lambda name: f"{name}"),
                                        lazy_src="http://picsum.photos/id/114/170/170",
                                        alt=("img", lambda img: f"{img}"),
                                        style="width: 170px; height: 170px; object-fit: contain; margin-top: 10px;",
                                        classes="d-flex flex-column align-center",
                                        )

                # Container for Features Table
                with vuetify.VRow():
                    with vuetify.VContainer(style="overflow-y: auto; overflow-x: auto; max-height: 400px; max-width: 100%; margin-right:50px; margin-left:50px; justify-content: center; align-items: center;", classes="d-flex flex-column flex-md-row"):
                        with vuetify.VCol(cols="auto", style="flex: 0 0 auto; max-width: 340px; max-height: 850px; padding: 50px "):        
                            with vuetify.VCard(style="margin-top:160px;"):
                                with vuetify.VSimpleTable():
                                    with html.Thead():
                                        with html.Tr():
                                            html.Th("PROPERTIES", 
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
                                                        html.Th("VALUES", classes="font-weight-bold", style="font-size:18px; text-align: left; color: rgb(0, 71, 171);")
                                                with html.Tbody():
                                                    with vuetify.Template(v_for="(feature, featureIndex) in compare_details[index]", key="featureIndex"):             
                                                        with html.Tr():
                                                            html.Td("{{ feature.Value }}", style="font-size: 16px; text-align: left;")

        # Main layout and navigation drawer                                                                                                                                                   
        #with SinglePageWithDrawerLayout(self.server) as layout:                                                                                                                              
        with SinglePageLayout(self.server) as layout:                                                                                                                                         
            layout.title.set_text(self.server.name)                                                                                                                                                                                                                                                                
                             
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
