import pandas as pd
import numpy as np
from typing import Dict, Union, Tuple

class CsvReporter:
    """
    A class for analyzing and reporting information about CSV files.

    Attributes:
        df (pd.DataFrame): The DataFrame containing the CSV file data.
        file_path (str): The path to the input CSV file.
    """

    def __init__(self, file_path: str) -> None:
        """
        Initialize the CsvReporter with a CSV file.

        Args:
            file_path (str): Path to the CSV file to be analyzed.

        Raises:
            FileNotFoundError: If the specified file cannot be found.
            ValueError: If the file is empty.
            Exception: For other errors during file reading.
        """
        try:
            self.df: pd.DataFrame = pd.read_csv(file_path)
            self.file_path: str = file_path
        except FileNotFoundError:
            raise FileNotFoundError(f"The file {file_path} was not found.")
        except pd.errors.EmptyDataError:
            raise ValueError(f"The file {file_path} is empty.")
        except Exception as e:
            raise Exception(f"An error occurred while reading the file: {e}")

    def get_column_info(self) -> Dict[str, str]:
        """
        Get column names and their data types.

        Returns:
            Dict[str, str]: A dictionary with column names as keys and their data types as values.
                            Possible types are 'int', 'float', 'str/char', or the original dtype.
        """
        column_types: Dict[str, str] = {}
        for column in self.df.columns:
            dtype = self.df[column].dtype
            
            if pd.api.types.is_integer_dtype(dtype):
                column_types[column] = 'int'
            elif pd.api.types.is_float_dtype(dtype):
                column_types[column] = 'float'
            elif pd.api.types.is_string_dtype(dtype):
                column_types[column] = 'str/char'
            else:
                column_types[column] = str(dtype)
        
        return column_types

    def count_rows_and_columns(self) -> Tuple[int, int]:
        """
        Count the number of rows and columns in the CSV.

        Returns:
            Tuple[int, int]: A tuple containing (number of rows, number of columns).
        """
        return self.df.shape

    def search(self, column_name: str) -> Union[np.ndarray, list]:
        """
        Search and return data for a specific column.

        Args:
            column_name (str): Name of the column to search.

        Returns:
            Union[np.ndarray, list]: Column data in numpy array for numeric types, 
                                      list for string/character types.

        Raises:
            KeyError: If the column name does not exist in the DataFrame.
        """
        if column_name not in self.df.columns:
            raise KeyError(f"Column '{column_name}' not found in the CSV.")
        
        column_data = self.df[column_name]
        
        if pd.api.types.is_numeric_dtype(column_data.dtype):
            return column_data.to_numpy()
        else:
            return column_data.tolist()

    def __str__(self) -> str:
        """
        Generate a string representation of the CsvReporter.

        Returns:
            str: Summary information about the CSV file.
        """
        rows, cols = self.count_rows_and_columns()
        column_info = self.get_column_info()
        
        summary: str = f"CSV File: {self.file_path}\n"
        summary += f"Rows: {rows}\n"
        summary += f"Columns: {cols}\n\n"
        summary += "Column Types:\n"
        for col, dtype in column_info.items():
            summary += f"- {col}: {dtype}\n"
        
        return summary

# Example usage
if __name__ == "__main__":
    # Example of how to use the CsvReporter
    try:
        reporter = CsvReporter('/home/huy/neurobazaar/datastore/.datasets/8e66f108-945b-4d84-a4f6-b921ff061d96_diabetes_012_health_indicators_BRFSS2015.csv')
        
        # Print summary
        print(reporter)
        
        # Get column information
        print("\nColumn Types:")
        print(reporter.get_column_info())
        
        # Count rows and columns
        rows, cols = reporter.count_rows_and_columns()
        print(f"\nRows: {rows}, Columns: {cols}")
        
        # Search a column
        # column_name = 'NHR'  # Replace with an actual column name
        # result = reporter.search(column_name)
        # print(f"\nColumn '{column_name}' data: {result}")
    
    except Exception as e:
        print(f"An error occurred: {e}")