import matplotlib
matplotlib.use('Agg')  # Use Agg backend which doesn't require a display

import os
import shutil
from django.conf import settings
from django.shortcuts import render, HttpResponse, redirect
import pandas as pd
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt


def process_pca(request):
    if request.method == 'POST':
        selected_columns = request.POST.getlist('selected_columns')
        uploaded_file_name = request.POST.get('uploaded_file_name')

        # Ensure that the uploaded file exists in the user's workspace directory
        username = request.user.username
        workspace_dir = os.path.join(settings.MEDIA_ROOT, 'workspace', username)

        # Check if the latest workspace directory exists
        latest_workspace_dir = max([d for d in os.listdir(workspace_dir) if os.path.isdir(os.path.join(workspace_dir, d))], key=lambda x: int(x.split('_')[1]), default=None)

        if latest_workspace_dir:
            file_path = os.path.join(workspace_dir, latest_workspace_dir, uploaded_file_name)

            if os.path.exists(file_path):
                # Load the uploaded CSV file
                df = pd.read_csv(file_path)

                # Select columns for PCA
                pca_data = df[selected_columns]

                # Perform PCA
                pca = PCA(n_components=2)
                pca_result = pca.fit_transform(pca_data)

                # Get the names of the selected columns (features)
                feature_names = selected_columns

                # Create a scatter plot for PCA result
                plt.figure(figsize=(10, 6))
                plt.scatter(pca_result[:, 0], pca_result[:, 1])
                
                # Update x and y labels with feature names
                plt.xlabel(feature_names[0])
                plt.ylabel(feature_names[1])
                
                plt.title('PCA Result')
                plt.grid(True)

                # Save the plot inside the workspace directory
                plot_path = os.path.join(workspace_dir, latest_workspace_dir, 'pca_plot.png')
                plt.savefig(plot_path)
                plt.close()  # Close the plot to release resources

                # Redirect to results page
                return redirect('/results/')
            else:
                # File not found, redirect to upload page
                return HttpResponse("File not found. Please upload the file again.")

        else:
            # No workspace directory found, redirect to upload page
            return HttpResponse("No workspace directory found. Please upload the file again.")

    return redirect('/upload/')

