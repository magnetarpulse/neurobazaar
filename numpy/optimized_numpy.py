import numpy as np                           # type: ignore
import concurrent.futures               
import time                                
                                          
def compute_histogram(data, bins):         
    return np.histogram(data, bins)         
                                      
if __name__ == '__main__':   
    data = np.random.rand(1_000_000_000)

    start_time = time.time()                 
    num_threads = 20                         # Number of threads to use. 15-25, 30-45 is the best performance so far. 20 is the best for now (at 1-100 bins).
    chunk_size = len(data) // num_threads    # Number of elements to process per thread (chunk)
    bins = np.linspace(0, 1, 1001)           # 1000 bins, 1001 edges

    print(f"Number of workers (threads): {num_threads}")

    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [executor.submit(compute_histogram, data[i:i+chunk_size], bins) 
                   for i in range(0, len(data), chunk_size)]
        results = [future.result() for future in concurrent.futures.as_completed(futures)]

    final_hist = np.sum([result[0] for result in results], axis=0)
    bin_edges = results[0][1] 
    end_time = time.time()

    true_final_hist, true_bin_edges = np.histogram(data, bins)
    assert np.array_equal(final_hist, true_final_hist)
    assert np.array_equal(bin_edges, true_bin_edges)

    print("Histogram counts:", final_hist)
    print("Bin edges:", bin_edges)
    print("Execution time: {:.2f} seconds".format(end_time - start_time))