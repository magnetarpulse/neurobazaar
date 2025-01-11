import os
import glob
import shutil
import logging
import tempfile
import numpy as np
import polars as pl     # type: ignore

class GenerateSyntheticDataset:
    """
    A class to generate synthetic datasets and save them as CSV files.

    Attributes:
        data_size (int): The size of the dataset to generate.
        dir_path (str): The directory path where the generated dataset will be saved.
        file_name (str): The name of the generated dataset file.
        chunk_size (int): The size of each data chunk.
        accuracy (float): The accuracy factor for estimations.
            The higher the value, the more more likely the estimations will be on the higher side (more conservative/overestimation).
            The lower the value, the more likely the estimations will be on the lower side (less conservative/underestimation).
            Default is 1. Do not change unless there is some specific reason.
        log_file (str): The path to the log file.
    """

    def __init__(self, data_size: int = 0, dir_path: str = None, file_name: str = None, chunk_size: int = 50_000_000, accuracy: float = 1) -> None:
        """
        Initializes the GenerateSyntheticDataset class.

        Args:
            data_size (int): The size of the dataset to generate.
            dir_path (str): The directory path where the generated dataset will be saved.
            file_name (str): The name of the generated dataset file.
            chunk_size (int, optional): The size of each data chunk. Defaults to 50,000,000.
            accuracy (float, optional): The accuracy factor for estimations. Defaults to 1.
        """
        self.data_size = data_size
        self.dir_path = dir_path
        self.file_name = file_name
        self.file_path = self.dir_path + '/' + self.file_name
        self.chunk_size = chunk_size
        self.accuracy = accuracy
        self.log_file = 'temp_dir.log'
        
        logging.basicConfig(filename='dataset_generation.log', level=logging.INFO,
                            format='%(asctime)s - %(levelname)s - %(message)s')

    def generate(self, byte_size=None, bit_size=None) -> None:
        """
        Generates the synthetic dataset and saves it as a CSV file.

        This method estimates the file size of the synthetic dataset to be generated.
        It prompts the user for confirmation before proceeding, especially if the 
        estimated file size exceeds 50 GB. If the user confirms, the dataset is 
        generated and saved to the specified file path.

        Args:
            byte_size (int, optional): The desired file size in bytes.
            bit_size (int, optional): The desired file size in bits.

        Returns:
            None: This method does not return a value but generates and saves a CSV file.
        """
        if byte_size and bit_size:
            if byte_size * 8 != bit_size:
                raise ValueError("byte_size and bit_size must be mathematically equivalent if both are provided.")
        
        if byte_size:
            self.data_size = self._calculate_elements_for_size(byte_size)
        elif bit_size:
            byte_size = bit_size // 8
            self.data_size = self._calculate_elements_for_size(byte_size)

        estimated_size = self._accurate_file_size_estimate()
        human_readable_size = self._human_readable_size(estimated_size)
        
        print(f"\033[34mThe estimated file size will be \033[91m{human_readable_size}\033[34m.\033[0m")
        user_input = input("\033[34mDo you want to continue? (\033[32my\033[34m/\033[31mn\033[34m): \033[0m").strip().lower()
        
        if user_input in ['y', 'yes']:
            if estimated_size > 50 * 1024 * 1024 * 1024: 
                user_input = input(f"\033[34mAre you sure? The file size is \033[91m{human_readable_size}\033[34m. (\033[32my\033[34m/\033[31mn\033[34m): \033[0m").strip().lower()
                if user_input in ['y', 'yes']:
                    self._generate_data_as_csv(self.file_path)
                else:
                    print("\033[31mOperation cancelled.\033[0m")
            else:
                self._generate_data_as_csv(self.file_path)
        else:
            print("\033[31mOperation cancelled.\033[0m")

    def _accurate_file_size_estimate(self) -> float:
        """
        Estimates the file size of the generated dataset.

        This method creates a temporary file with a sample dataset to estimate the 
        file size of the entire dataset to be generated. It writes a sample DataFrame 
        to the temporary file, measures the file size, and scales it according to the 
        total data size and accuracy parameters during initialization of the class.

        Returns:
            float: The estimated file size in bytes.

        Note: This method should not be invoked directly. It is used internally by `generate` to estimate the file size.
        """
        with tempfile.NamedTemporaryFile(mode='w', delete=True) as temp:
            sample_df = pl.DataFrame({'data': np.random.normal(size=1000)})
            
            sample_df.write_csv(temp.name)
            temp.flush()
            
            sample_size = os.path.getsize(temp.name)
            estimated_size = (sample_size / 1000) * self.data_size * self.accuracy
        
        return estimated_size
    
    def _calculate_elements_for_size(self, target_byte_size: int) -> int:
        """
        Calculates the number of elements needed to generate a dataset of a specific byte size.

        This method uses the same sampling technique as _accurate_file_size_estimate 
        to determine the number of elements required to reach the target file size.

        Args:
            target_byte_size (int): The desired file size in bytes.

        Returns:
            int: The number of elements needed to generate a file of the specified size.
        
        Note: This method should not be invoked directly. It is used internally by `generate` to calculate the number of elements needed.
        """
        with tempfile.NamedTemporaryFile(mode='w', delete=True) as temp:
            sample_df = pl.DataFrame({'data': np.random.normal(size=1000)})
            
            sample_df.write_csv(temp.name)
            temp.flush()
            
            sample_size = os.path.getsize(temp.name)
            
            elements_needed = int((target_byte_size / sample_size) * 1000 * self.accuracy)
        
        return elements_needed

    def _generate_data_as_csv(self, file_path: str) -> None:
        """
        Generates the synthetic dataset and saves it as a CSV file.

        This method creates the synthetic dataset in chunks, saves each chunk as a 
        temporary CSV file, and then concatenates these chunks into the final CSV file 
        at the specified file path. It also verifies the integrity of the generated file 
        and cleans up temporary files.

        Args:
            file_path (str): The path where the generated dataset will be saved.

        Note:
            This method should not be invoked directly. Use the `generate` method instead.
        """
        temp_dir = 'temp_chunks'
        os.makedirs(temp_dir, exist_ok=True)
        
        with open(self.log_file, 'w') as log:
            log.write(temp_dir)
        
        num_full_chunks = self.data_size // self.chunk_size
        remaining_elements = self.data_size % self.chunk_size
        
        for i in range(num_full_chunks + (1 if remaining_elements > 0 else 0)):
            current_chunk_size = (self.chunk_size if i < num_full_chunks else remaining_elements)
            
            chunk_data = np.random.normal(loc=0, scale=1, size=current_chunk_size)
            
            df = pl.DataFrame({'data': chunk_data})
            
            temp_file_path = os.path.join(temp_dir, f'chunk-{i:04d}.csv')
            df.write_csv(temp_file_path)
        
        self._concatenate_files(os.path.join(temp_dir, 'chunk-*.csv'), file_path)
        self._verify_file_elements(file_path)
        self._cleanup_temp_files(temp_dir)

    def _concatenate_files(self, temp_file_pattern: str, output_file: str) -> None:
        """
        Concatenates multiple CSV files into a single CSV file.

        This method takes a pattern to match temporary chunk files, reads each chunk, 
        and writes their contents into a single output CSV file. The header is only 
        written once from the first chunk file to avoid duplication.

        Args:
            temp_file_pattern (str): The pattern to match temporary chunk files.
            output_file (str): The path where the concatenated CSV file will be saved.

        Note:
            This method should not be invoked directly. It is used internally by the 
            `generate` method to combine chunk files into the final dataset.
        """
        chunk_files = sorted(glob.glob(temp_file_pattern))
        
        with open(output_file, 'w') as outfile:
            for i, chunk_file in enumerate(chunk_files):
                with open(chunk_file, 'r') as infile:
                    if i != 0:
                        infile.readline() 
                    outfile.write(infile.read())

    def _verify_file_elements(self, file_path: str) -> None:
        """
        Verifies the number of elements in the generated CSV file.

        This method reads the generated CSV file and counts the number of elements 
        (rows) to ensure it matches the expected data size. It logs and raises an 
        error if there is a mismatch.

        Args:
            file_path (str): The path to the generated CSV file.

        Note:
            This method should not be invoked directly. It is used internally by the 
            `generate` method to verify the integrity of the generated dataset.
        """
        with open(file_path, 'r') as f:
            line_count = sum(1 for _ in f) - 1  # Subtract 1 for header
        print(f"\033[32mSuccessfully verified, there are {line_count} elements in the CSV.\033[0m")
        
        if line_count < self.data_size:
            print(f"\033[31mElement count mismatch: expected {self.data_size}, found {line_count}\033[0m")
            logging.error(f"Element count mismatch: expected {self.data_size}, found {line_count}")
            assert line_count == self.data_size, "Element count mismatch"
        elif line_count > self.data_size:
            print(f"\033[33mElement count exceeds expected: expected {self.data_size}, found {line_count}\033[0m")
            logging.warning(f"Element count exceeds expected: expected {self.data_size}, found {line_count}")

    def _cleanup_temp_files(self, temp_dir: str) -> None:
        """
        Cleans up temporary files and directories.

        This method removes the temporary directory and its contents, as well as 
        the log file used during the dataset generation process.

        Args:
            temp_dir (str): The path to the temporary directory.

        Note:
            This method should not be invoked directly. It is used internally by the 
            `generate` method to clean up temporary files after the dataset is generated.
        """
        shutil.rmtree(temp_dir)
        
        if os.path.exists(self.log_file):
            os.remove(self.log_file)

    def _human_readable_size(self, size_bytes: float) -> str:
        """
        Converts a file size in bytes to a human-readable format.

        This method takes a file size in bytes and converts it to a more readable 
        format with appropriate units (e.g., KB, MB, GB).

        Args:
            size_bytes (float): The file size in bytes.

        Returns:
            str: The human-readable file size.
        """
        if size_bytes == 0:
            return "0B"
        size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
        i = int(np.floor(np.log(size_bytes) / np.log(1024)))
        p = np.power(1024, i)
        s = round(size_bytes / p, 2)
        return f"{s} {size_name[i]}"

if __name__ == '__main__':
    dataset = GenerateSyntheticDataset(data_size=1_000_000_000, dir_path= "/home/huy/neurobazaar/benchmarks/utils/gen", file_name='small_test.csv', chunk_size=50_000_000, accuracy=1)
    dataset.generate() 