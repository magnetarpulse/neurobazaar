import os
import sys
import mmap
import fcntl

def get_neurobazaar_dir() -> str:
    """Returns the neurobazaar directory."""
    cwd = os.getcwd()
    index = cwd.index('neurobazaar')
    return cwd[:index + len('neurobazaar')]

neurobazaar = get_neurobazaar_dir()
sys.path.insert(0, neurobazaar)

import ctypes
import psutil                                       # type: ignore                                                                                                                       
import resource

import asyncio        
from queue import Queue   
from threading import Thread                                                                                                            
from concurrent.futures import ThreadPoolExecutor

from typing import Any, List, Dict, AsyncGenerator, Generator, Tuple
from cpp.distribution_queues import SimpleQueue, ConcurrentQueue

RED = "\033[31m"
GREEN = "\033[32m"
BLUE = "\033[34m"
PURPLE = "\033[38;5;105m"   
MAGENTA = "\033[95m"
RESET = "\033[0m"

CHUNK_SIZE = 10 * 1024 * 1024               
BUFFER_SIZE = 32                            
MAX_WORKERS = min(os.cpu_count() or 4, 8)   
PAGE_SIZE = resource.getpagesize()          

class ByteMe:
    class _ByteMeUp:
        def __init__(self, chunk_size: int, file_size: int, num_consumers: int):
            self.chunk_size = chunk_size
            self.total_chunks = (file_size + chunk_size - 1) // chunk_size

            print(f"{BLUE}Initializing ByteMeUp with file_size={file_size}, chunk_size={chunk_size}{RESET}")
            print(f"{BLUE}Calculated total chunks={self.total_chunks}{RESET}")
            
            chunks_per_consumer = self.total_chunks // num_consumers 
            remaining_chunks = self.total_chunks % num_consumers
            
            print(f"{MAGENTA}Base chunks per consumer: {chunks_per_consumer}{RESET}")
            print(f"{BLUE}Remaining chunks to distribute: {remaining_chunks}{RESET}")

            self.consumer_ranges = []
            start_chunk = 0
            
            for i in range(num_consumers):
                extra_chunk = 1 if i < remaining_chunks else 0
                consumer_chunk_count = chunks_per_consumer + extra_chunk
                end_chunk = start_chunk + consumer_chunk_count
                
                self.consumer_ranges.append((start_chunk, end_chunk))
                print(f"{MAGENTA}Consumer {i}: chunks {start_chunk} to {end_chunk} " \
                    f"({consumer_chunk_count} chunks){RESET}")
                
                start_chunk = end_chunk
            
            total_assigned = sum(end - start for start, end in self.consumer_ranges)
            print(f"{MAGENTA}Total chunks assigned to consumers: {total_assigned}{RESET}")
            assert total_assigned == self.total_chunks, \
                f"{RED}Chunk assignment mismatch: {total_assigned} != {self.total_chunks}{RESET}"
                
            self.chunk_stores = [dict() for _ in range(num_consumers)]
            self.next_positions = [range[0] for range in self.consumer_ranges]
            
        def _identity(self, byte_position: int) -> int:
            chunk_pos = byte_position // self.chunk_size
            left, right = 0, len(self.consumer_ranges) - 1
            while left <= right:
                mid = (left + right) // 2
                start, end = self.consumer_ranges[mid]
                if start <= chunk_pos < end:
                    return mid
                elif chunk_pos < start:
                    right = mid - 1
                else:
                    left = mid + 1
            return len(self.consumer_ranges) - 1
            
        def _add_chunk(self, byte_position: int, data: bytes) -> int:
            chunk_pos = byte_position // self.chunk_size
            consumer_id = self._identity(byte_position)
            print(f"{GREEN}Adding chunk at position {byte_position} to consumer {consumer_id}{RESET}")
            self.chunk_stores[consumer_id][chunk_pos] = data
            return consumer_id
            
        def _get_chunk(self, consumer_id: int) -> List[Tuple[int, bytes]]:
            ready_chunks = []
            store = self.chunk_stores[consumer_id]
            current_pos = self.next_positions[consumer_id]
            end_pos = self.consumer_ranges[consumer_id][1]

            # print(f"{MAGENTA}Consumer {consumer_id} store keys: {list(store.keys())}{RESET}")
            # print(f"{MAGENTA}Consumer {consumer_id} requesting chunks from {current_pos} to {end_pos}{RESET}")
            
            while current_pos < end_pos and current_pos in store:
                data = store.pop(current_pos)
                byte_position = current_pos * self.chunk_size
                ready_chunks.append((byte_position, data))
                current_pos += 1
                
            self.next_positions[consumer_id] = current_pos
            return ready_chunks

    def __init__(self, optimized: bool = True) -> None:
        self.__is_optimized = optimized
        self.__executor = ThreadPoolExecutor(
            max_workers=MAX_WORKERS,
            thread_name_prefix='streamer'
        )

        self._VALID_IO_METHODS = {'mmap', 'aiofile', 'aiofiles', 'vectored', 'direct_read', 'traditional_read'}

        self._set_simulation_flags()

    def __setattr__(self, name: str, value: any) -> None:
        if name == 'PREFERRED_IO_METHOD' and hasattr(self, 'PREFERRED_IO_METHOD'):
            raise AttributeError(f"{RED}Cannot modify 'PREFERRED_IO_METHOD' once it is set.{RESET}")

        if name.startswith("SIMULATE_") and hasattr(self, name):
            raise AttributeError(f"{RED}Cannot modify '{name}' once it is set.{RESET}")

        super().__setattr__(name, value)

    @property
    def PREFERRED_IO_METHOD(self) -> str:
        get_attr = getattr(self, '_PREFERRED_IO_METHOD', None)
        valid_io_methods = getattr(self, '_VALID_IO_METHODS', [])
        formatted_methods = []

        for method in valid_io_methods:
            if method == get_attr:
                formatted_methods.append(f"{GREEN}>>> {method}{RESET}")
            else:
                formatted_methods.append(f"{RED}>>> {method}{RESET}")

        preferred_io_method_header = f"{BLUE}=== Preferred IO Method ==={RESET}"     
        formatted_methods_str = "\n".join(formatted_methods)
        return f"\n{preferred_io_method_header}\n{formatted_methods_str}\n"

    @property
    def VALID_IO_METHODS(self) -> str:
        get_attr = getattr(self, '_VALID_IO_METHODS', [])
        formatted_methods = [f"{GREEN}>>> {method}{RESET}" for method in get_attr]
        valid_io_methods_str = "\n".join(formatted_methods)

        valid_io_methods_header = f"{BLUE}=== Valid IO Methods ==={RESET}\n"
        return f"\n{valid_io_methods_header}{valid_io_methods_str}\n"

    @property
    def SIMULATION_FLAGS(self) -> str:
        simulation_flags = [
            attr for attr in dir(self) if attr.startswith("SIMULATE_")
        ]

        formatted_flags = []
        for attr in simulation_flags:
            value = getattr(self, attr)
            if value:  
                formatted_flags.append(f"{RED}>>> {attr}: {value}{RESET}")
            else:
                formatted_flags.append(f"{GREEN}{attr}: {value}{RESET}")

        simulation_flags_str = "\n".join(formatted_flags)
        simulation_flags_header = f"{BLUE}=== Simulation Flags Status ==={RESET}\n"
        return f"\n{simulation_flags_header}{simulation_flags_str}\n"
    
    def stream_file(self, compressed: bool = False, file_path: str = None, io_method: str = "mmap") -> Generator[bytes, None, None]:
        self.__is_compressed = compressed
        self.path = file_path

        if self.__is_compressed:
            raise RuntimeError("This service is still under development.")
        
        if self.path is None:
            raise ValueError("File path is required for streaming.")
        
        self.__io_method = io_method
        self._set_preferred_io_method(self.__io_method)

        uncompressed_stream = self._stream_uncompressed_file(file_path)
        generator = self._make_sync_generator(uncompressed_stream)

        return generator

    def _set_simulation_flags(self) -> None:
        if not hasattr(self, 'SIMULATE_MMAP_FAILURE'):  
            self.SIMULATE_MMAP_FAILURE = os.getenv('DEBUG_SIMULATE_MMAP_FAILURE', 'false').lower() == 'true'
            self.SIMULATE_AIOFILE_FAILURE = os.getenv('DEBUG_SIMULATE_AIOFILE_FAILURE', 'false').lower() == 'true'
            self.SIMULATE_AIOFILES_FAILURE = os.getenv('DEBUG_SIMULATE_AIOFILES_FAILURE', 'false').lower() == 'true'
            self.SIMULATE_VECTORED_IO_FAILURE = os.getenv('DEBUG_SIMULATE_VECTORED_IO_FAILURE', 'false').lower() == 'true'
            self.SIMULATE_DIRECT_READ_FAILURE = os.getenv('DEBUG_SIMULATE_DIRECT_READ_FAILURE', 'false').lower() == 'true'
    
    def _set_preferred_io_method(self, method: str) -> None:
        method = method.lower()
        
        if method not in self._VALID_IO_METHODS:
            raise ValueError(f"{RED}Invalid IO method: {method}. Valid methods are: {', '.join(self._VALID_IO_METHODS)} {RESET}")

        if hasattr(self, '_PREFERRED_IO_METHOD'):
            raise AttributeError(f"{RED}Cannot modify 'PREFERRED_IO_METHOD' once it is set.{RESET}")

        self._PREFERRED_IO_METHOD = method
        print(f"{GREEN}Preferred IO method set to: {method}{RESET}")

    def _optimize_system(self) -> None:
        try:
            libc = ctypes.CDLL('libc.so.6')
            PR_SET_IO_PRIORITY = 40
            IOPRIO_CLASS_RT = 1
            ioprio = (IOPRIO_CLASS_RT << 13) | 7
            libc.syscall(PR_SET_IO_PRIORITY, 0, ioprio)
            print(f"{GREEN}I/O priority optimization successful.{RESET}")
        except Exception as e:
            print(f"{RED}I/O priority optimization not available: {e}{RESET}")

        try:
            process = psutil.Process()
            cpu_count = os.cpu_count() or 4
            cpu_list = list(range(cpu_count // 2))
            process.cpu_affinity(cpu_list)
            print(f"{GREEN}CPU affinity successfully set.{RESET}")
        except Exception as e:
            print(f"{RED}CPU affinity setting not available: {e}{RESET}")

        try:
            libc = ctypes.CDLL('libc.so.6')
            MCL_CURRENT = 1
            MCL_FUTURE = 2
            libc.mlockall(MCL_CURRENT | MCL_FUTURE)
            print(f"{GREEN}Memory locking successful.{RESET}")
        except Exception as e:
            print(f"{RED}Memory locking not available: {e}{RESET}")

    def _file_producer(self, file_path: str, chunk_size: int, buffer: Queue, start: int, end: int) -> None:
        aligned_chunk_size: int = (chunk_size + PAGE_SIZE - 1) & ~(PAGE_SIZE - 1)
        self.total_bytes_produced: int = 0

        with open(file_path, "rb") as f:
            try:
                fcntl.fcntl(f.fileno(), fcntl.F_SETFL, os.O_DIRECT)
                # print(f"{GREEN}Direct I/O enabled successfully.{RESET}")
            except Exception as e:
                print(f"{RED}Direct I/O not available: {e}{RESET}")

            try:
                if hasattr(os, 'posix_fadvise'):
                    os.posix_fadvise(f.fileno(), 0, 0, os.POSIX_FADV_SEQUENTIAL)
                    # print(f"{GREEN}posix_fadvise set to sequential.{RESET}")
            except Exception as e:
                print(f"{RED}posix_fadvise not available: {e}{RESET}")

            try:
                import subprocess
                subprocess.run(['ionice', '-c2', '-n0', str(os.getpid())],
                            stderr=subprocess.DEVNULL,
                            stdout=subprocess.DEVNULL)
                # print(f"{GREEN}ionice set to real-time priority.{RESET}")
            except Exception as e:
                print(f"{RED}ionice setting not available: {e}{RESET}")

            if self._PREFERRED_IO_METHOD != 'mmap':
                print(f"{BLUE}Attempting preferred IO method: {self._PREFERRED_IO_METHOD}{RESET}")
                if self._PREFERRED_IO_METHOD == 'aiofile':
                    try:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        
                        from aiofile import async_open as aiofile_open
                        async def _aiofile_read() -> None:
                            async with aiofile_open(file_path, 'rb') as aio_f:
                                aio_f.seek(start)
                                remaining: int = end - start
                                while remaining > 0:
                                    read_size: int = min(aligned_chunk_size, remaining)
                                    chunk: bytes = await aio_f.read(read_size)
                                    if not chunk:
                                        break
                                    buffer.put(chunk)
                                    self.total_bytes_produced
                                    self.total_bytes_produced += len(chunk)
                                    remaining -= len(chunk)
                                    print(f"{PURPLE}Producer: Produced chunk of size {len(chunk)} using aiofile{RESET}")

                        loop.run_until_complete(_aiofile_read())
                        loop.close()
                        return
                    except Exception as e:
                        print(f"{RED}Preferred method (aiofile) failed: {e}. Falling back to mmap.{RESET}")

                elif self._PREFERRED_IO_METHOD == 'aiofiles':
                    try:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        
                        from aiofiles import open as aiofiles_open  # type: ignore
                        async def _aiofiles_read() -> None:
                            async with aiofiles_open(file_path, mode='rb') as af:
                                await af.seek(start)
                                remaining: int = end - start
                                while remaining > 0:
                                    read_size: int = min(aligned_chunk_size, remaining)
                                    chunk: bytes = await af.read(read_size)
                                    if not chunk:
                                        break
                                    buffer.put(chunk)
                                    nonlocal total_bytes_produced
                                    total_bytes_produced += len(chunk)
                                    remaining -= len(chunk)
                                    print(f"{PURPLE}Producer: Produced chunk of size {len(chunk)} using aiofiles{RESET}")

                        loop.run_until_complete(_aiofiles_read())
                        loop.close()
                        return
                    except Exception as e:
                        print(f"{RED}Preferred method (aiofiles) failed: {e}. Falling back to mmap.{RESET}")

                elif self._PREFERRED_IO_METHOD == 'vectored':
                    try:
                        def _vectored_read(size: int, offset: int) -> bytes:
                            block_size: int = PAGE_SIZE
                            aligned_offset: int = (offset // block_size) * block_size
                            offset_adjust: int = offset - aligned_offset

                            total_aligned_size: int = ((size + offset_adjust + block_size - 1) // block_size) * block_size
                            num_vectors: int = (total_aligned_size + block_size - 1) // block_size

                            buffers: List[bytearray] = []
                            for _ in range(num_vectors):
                                buf: bytearray = bytearray(block_size)
                                buffers.append(buf)

                            os.lseek(f.fileno(), aligned_offset, os.SEEK_SET)
                            bytes_read: int = os.readv(f.fileno(), buffers)

                            if bytes_read <= 0:
                                return b''

                            result: bytearray = bytearray()
                            remaining: int = size
                            buffer_offset: int = offset_adjust

                            for buf in buffers:
                                if remaining <= 0:
                                    break
                                chunk: bytes = buf[buffer_offset:buffer_offset + remaining]
                                result.extend(chunk)
                                remaining -= len(chunk)
                                buffer_offset = 0

                            return bytes(result)

                        current_offset: int = start
                        remaining: int = end - start

                        while remaining > 0:
                            read_size: int = min(aligned_chunk_size, remaining)
                            chunk: bytes = _vectored_read(read_size, current_offset)
                            if not chunk:
                                break
                            buffer.put(chunk)
                            total_bytes_produced += len(chunk)
                            print(f"{PURPLE}Producer: Produced chunk of size {len(chunk)} using vectored I/O{RESET}")
                            remaining -= len(chunk)
                            current_offset += len(chunk)
                        return
                    except Exception as e:
                        print(f"{RED}Preferred method (vectored) failed: {e}. Falling back to mmap.{RESET}")
                
                elif self._PREFERRED_IO_METHOD == 'direct_read':
                    try:
                        def _direct_read(size: int, aligned_chunk_size: int, offset: int, fd: int) -> bytes:
                            block_size = PAGE_SIZE  

                            if aligned_chunk_size % block_size != 0:
                                raise ValueError("Aligned chunk size must be a multiple of the system's page size.")

                            aligned_buffer = ctypes.create_string_buffer(aligned_chunk_size + block_size)
                            aligned_address = ctypes.addressof(aligned_buffer)
                            address_offset = aligned_address % block_size

                            if address_offset != 0:
                                aligned_address += (block_size - address_offset)

                            aligned_memory = ctypes.cast(aligned_address, ctypes.POINTER(ctypes.c_char * aligned_chunk_size))
                            aligned_offset = (offset // block_size) * block_size
                            offset_adjustment = offset - aligned_offset

                            os.lseek(fd, aligned_offset, os.SEEK_SET)
                            bytes_read = os.read(fd, aligned_chunk_size)

                            if not bytes_read:
                                return b''

                            ctypes.memmove(aligned_memory, bytes_read, len(bytes_read))

                            return bytes(aligned_memory.contents[offset_adjustment:offset_adjustment + size])

                        f.seek(start)
                        remaining: int = end - start
                        current_offset: int = start

                        while remaining > 0:
                            read_size: int = min(aligned_chunk_size, remaining)
                            chunk: bytes = _direct_read(read_size, aligned_chunk_size, current_offset, f.fileno())
                            if not chunk:
                                break
                            buffer.put(chunk)
                            total_bytes_produced += len(chunk)
                            print(f"{PURPLE}Producer: Produced chunk of size {len(chunk)} using Direct I/O{RESET}")
                            remaining -= len(chunk)
                            current_offset += len(chunk)
                        return
                    except Exception as e:
                        print(f"{RED}Preferred method (direct_read) failed: {e}. Falling back to mmap.{RESET}")

                elif self._PREFERRED_IO_METHOD == 'traditional_read':
                    try:
                        print(f"{BLUE}Attempting to turn off O_DIRECT flag for preferred traditional read.{RESET}")
                        fd_flags: int = fcntl.fcntl(f.fileno(), fcntl.F_GETFL)
                        fd_flags &= ~os.O_DIRECT  
                        fcntl.fcntl(f.fileno(), fcntl.F_SETFL, fd_flags)
                        print(f"{GREEN}O_DIRECT flag turned off successfully.{RESET}")

                        f.seek(start)
                        remaining: int = end - start
                        while remaining > 0:
                            read_size: int = min(aligned_chunk_size, remaining)
                            chunk: bytes = f.read(read_size)
                            if not chunk:
                                break
                            buffer.put(chunk)
                            total_bytes_produced += len(chunk)
                            print(f"{PURPLE}Producer: Produced chunk of size {len(chunk)} with preferred traditional read{RESET}")
                            remaining -= len(chunk)
                        return
                    except Exception as e:
                        print(f"{RED}Preferred method (traditional_read) failed: {e}. Falling back to mmap.{RESET}")
                        try:
                            print(f"{BLUE}Attempting to re-enable O_DIRECT flag for fallback mmap.{RESET}")
                            fcntl.fcntl(f.fileno(), fcntl.F_SETFL, os.O_DIRECT)
                            print(f"{GREEN}Direct I/O enabled successfully.{RESET}")
                        except Exception as e:
                            print(f"{RED}Direct I/O not available: {e}{RESET}")

            try:
                if self.SIMULATE_MMAP_FAILURE:
                    raise Exception("Simulated mmap failure for testing fallbacks")
                    
                aligned_start: int = (start // PAGE_SIZE) * PAGE_SIZE
                offset: int = start - aligned_start

                with mmap.mmap(f.fileno(), end - aligned_start, offset=aligned_start, access=mmap.ACCESS_READ) as mm:
                    pos: int = 0
                    while pos < (end - start):
                        chunk_end: int = min(pos + aligned_chunk_size, end - start)
                        # actual_remaining = end - start - pos
                        # if actual_remaining < aligned_chunk_size:
                        #     print("Last chunk")
                        #     chunk: bytes = mm[offset + pos:offset + pos + actual_remaining]
                        # else:
                        #     chunk: bytes = mm[offset + pos:offset + chunk_end]
                        # print(f"{PURPLE}Producer: Adding chunk position {pos} to buffer of size {len(chunk)}{RESET}")
                        chunk: bytes = mm[offset + pos:offset + chunk_end]
                        chunk_info = {
                            'position': start + pos,
                            'data': chunk
                        }
                        buffer.put(chunk_info)
                        self.total_bytes_produced += len(chunk)
                        # print(f"{PURPLE}Producer: Produced chunk of size {len(chunk)} at position {pos}{RESET}")
                        pos += aligned_chunk_size
                    return
            except Exception as e:
                print(f"{RED}mmap failed: {e}. Falling back to aiofile.{RESET}")
                
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
                try:
                    from aiofile import async_open as aiofile_open
                    async def _aiofile_read() -> None:
                        if self.SIMULATE_AIOFILE_FAILURE:
                            raise Exception("Simulated aiofile failure for testing fallbacks")
                        
                        async with aiofile_open(file_path, 'rb') as aio_f:
                            aio_f.seek(start)
                            remaining: int = end - start
                            while remaining > 0:
                                read_size: int = min(aligned_chunk_size, remaining)
                                chunk: bytes = await aio_f.read(read_size)
                                if not chunk:
                                    break
                                buffer.put(chunk)
                                nonlocal total_bytes_produced
                                total_bytes_produced += len(chunk)
                                remaining -= len(chunk)
                                print(f"{PURPLE}Producer: Produced chunk of size {len(chunk)} using aiofile{RESET}")

                    loop.run_until_complete(_aiofile_read())
                    loop.close()
                    return
                except ImportError:
                    print(f"{RED}aiofile not available; falling back to aiofiles.{RESET}")
                except Exception as e:
                    print(f"{RED}aiofile failed: {e}. Falling back to aiofiles.{RESET}")

                try:
                    from aiofiles import open as aiofiles_open  # type: ignore
                    async def _aiofiles_read():
                        if self.SIMULATE_AIOFILES_FAILURE:
                            raise Exception("Simulated aiofiles failure for testing fallbacks")
                        
                        async with aiofiles_open(file_path, mode='rb') as af:
                            await af.seek(start)
                            remaining: int = end - start
                            while remaining > 0:
                                read_size: int = min(aligned_chunk_size, remaining)
                                chunk: bytes = await af.read(read_size)
                                if not chunk:
                                    break
                                buffer.put(chunk)
                                nonlocal total_bytes_produced
                                total_bytes_produced += len(chunk)
                                remaining -= len(chunk)
                                print(f"{PURPLE}Producer: Produced chunk of size {len(chunk)} using aiofiles{RESET}")
                    
                    loop.run_until_complete(_aiofiles_read())
                    loop.close()
                    return
                except ImportError:
                    print(f"{RED}aiofiles not available; falling back to Vectored I/O  read.{RESET}")
                except Exception as e:
                    print(f"{RED}aiofiles failed: {e}. Falling back to Vectored I/O  read.{RESET}")

                try:                    
                    def _vectored_read(size: int, offset: int) -> bytes:
                        if self.SIMULATE_VECTORED_IO_FAILURE:
                            raise Exception("Simulated aligned read failure for testing fallbacks")
                
                        block_size: int = PAGE_SIZE
                        aligned_offset: int = (offset // block_size) * block_size
                        offset_adjust: int = offset - aligned_offset

                        total_aligned_size: int = ((size + offset_adjust + block_size - 1) // block_size) * block_size
                        num_vectors: int = (total_aligned_size + block_size - 1) // block_size

                        buffers: List[bytearray] = []
                        for _ in range(num_vectors):
                            buf: bytearray = bytearray(block_size)
                            buffers.append(buf)

                        os.lseek(f.fileno(), aligned_offset, os.SEEK_SET)
                        bytes_read: int = os.readv(f.fileno(), buffers)

                        if bytes_read <= 0:
                            return b''

                        result: bytearray = bytearray()
                        remaining: int = size
                        buffer_offset: int = offset_adjust

                        for buf in buffers:
                            if remaining <= 0:
                                break
                            chunk: bytes = buf[buffer_offset:buffer_offset + remaining]
                            result.extend(chunk)
                            remaining -= len(chunk)
                            buffer_offset = 0

                        return bytes(result)

                    current_offset: int = start
                    remaining: int = end - start

                    while remaining > 0:
                        read_size: int = min(aligned_chunk_size, remaining)
                        chunk: bytes = _vectored_read(read_size, current_offset)
                        if not chunk:
                            break
                        buffer.put(chunk)
                        total_bytes_produced += len(chunk)
                        print(f"{PURPLE}Producer: Produced chunk of size {len(chunk)} using vectored I/O{RESET}")
                        remaining -= len(chunk)
                        current_offset += len(chunk)
                    return
                except Exception as e:
                    print(f"{RED}Vectored I/O read failed: {e}. Falling back to direct I/O read.{RESET}")

                try:
                    def _direct_read(size: int, aligned_chunk_size: int, offset: int, fd: int) -> bytes:
                        if self.SIMULATE_DIRECT_IO_FAILURE:
                            raise Exception("Simulated direct read failure for testing fallbacks")
                        
                        block_size = PAGE_SIZE  

                        if aligned_chunk_size % block_size != 0:
                            raise ValueError("Aligned chunk size must be a multiple of the system's page size.")

                        aligned_buffer = ctypes.create_string_buffer(aligned_chunk_size + block_size)
                        aligned_address = ctypes.addressof(aligned_buffer)
                        address_offset = aligned_address % block_size

                        if address_offset != 0:
                            aligned_address += (block_size - address_offset)

                        aligned_memory = ctypes.cast(aligned_address, ctypes.POINTER(ctypes.c_char * aligned_chunk_size))
                        aligned_offset = (offset // block_size) * block_size
                        offset_adjustment = offset - aligned_offset

                        os.lseek(fd, aligned_offset, os.SEEK_SET)
                        bytes_read = os.read(fd, aligned_chunk_size)

                        if not bytes_read:
                            return b''

                        ctypes.memmove(aligned_memory, bytes_read, len(bytes_read))

                        return bytes(aligned_memory.contents[offset_adjustment:offset_adjustment + size])

                    f.seek(start)
                    remaining: int = end - start
                    current_offset: int = start

                    while remaining > 0:
                        read_size: int = min(aligned_chunk_size, remaining)
                        chunk: bytes = _direct_read(read_size, aligned_chunk_size, current_offset, f.fileno())
                        if not chunk:
                            break
                        buffer.put(chunk)
                        total_bytes_produced += len(chunk)
                        print(f"{PURPLE}Producer: Produced chunk of size {len(chunk)} using Direct I/O{RESET}")
                        remaining -= len(chunk)
                        current_offset += len(chunk)
                    return
                except Exception as e:
                    print(f"{RED}Direct I/O read failed: {e}. Falling back to traditional read.{RESET}")

                try:
                    print(f"{BLUE}Attempting to turn off O_DIRECT flag for traditional read.{RESET}")
                    fd_flags: int = fcntl.fcntl(f.fileno(), fcntl.F_GETFL)
                    fd_flags &= ~os.O_DIRECT  
                    fcntl.fcntl(f.fileno(), fcntl.F_SETFL, fd_flags)
                    print(f"{GREEN}O_DIRECT flag turned off successfully.{RESET}")

                    f.seek(start)
                    remaining: int = end - start
                    while remaining > 0:
                        read_size: int = min(aligned_chunk_size, remaining)
                        chunk: bytes = f.read(read_size)
                        if not chunk:
                            break
                        buffer.put(chunk)
                        total_bytes_produced += len(chunk)
                        print(f"{PURPLE}Producer: Produced chunk of size {len(chunk)} with traditional read{RESET}")
                        remaining -= len(chunk)
                    return
                except Exception as e:
                    print(f"{RED}Fallback read failed: {e}. Exiting.{RESET}")
                    print(f"{RED}All fallback methods failed. Exiting.{RESET}")
                    return

        print(f"{GREEN}Total bytes produced: {total_bytes_produced}{RESET}")

    async def _file_consumer(self, buffer: Queue, consumer_id: int, chunk_map) -> AsyncGenerator[bytes, None]:
        start_chunk, end_chunk = chunk_map.consumer_ranges[consumer_id - 1]
        print(f"{MAGENTA}Consumer {consumer_id} handling chunks {start_chunk} to {end_chunk}{RESET}")
        
        total_bytes_consumed: int = 0
        total_chunks_received: int = 0
        
        try:
            while True:
                # print(f"{MAGENTA}Consumer {consumer_id}: Waiting for next chunk...{RESET}")
                chunk_info = await asyncio.get_event_loop().run_in_executor(
                    # self.__executor, lambda: buffer.get(timeout=10)
                    self.__executor, lambda: buffer.get()
                )
                
                if chunk_info is None:
                    # print(f"{MAGENTA}Consumer {consumer_id}: Received termination signal{RESET}")
                    break
                    
                # print(f"{MAGENTA}Consumer {consumer_id}: Processing chunk at position {chunk_info['position']}{RESET}")
                actual_consumer = chunk_map._add_chunk(chunk_info['position'], chunk_info['data'])
                
                if actual_consumer == consumer_id - 1:
                    # print(f"{MAGENTA}Consumer {consumer_id}: Retrieving ready chunks{RESET}")
                    ready_chunks = chunk_map._get_chunk(actual_consumer)
                    for position, data in ready_chunks:
                        total_bytes_consumed += len(data)
                        total_chunks_received += 1
                        print(f"{MAGENTA}Consumer {consumer_id}: Yielding chunk {position}, size: {len(data)} bytes " \
                                f"(Total: {total_bytes_consumed} bytes, {total_chunks_received} chunks){RESET}")
                        yield {'position': position, 'data': data}
                        
        finally:
            # print(f"{MAGENTA}Consumer {consumer_id}: Processing final chunks{RESET}")
            final_chunks = chunk_map._get_chunk(consumer_id - 1)
            for position, data in final_chunks:
                print(f"{MAGENTA}Consumer {consumer_id}: Yielding final chunk {position}, size: {len(data)} bytes{RESET}")
                yield {'position': position, 'data': data}

    async def _stream_uncompressed_file(self, file_path: str, num_consumers: int = 4) -> AsyncGenerator[bytes, None]:
        if self.__is_optimized:
            print(f"{BLUE}Attempting to optimize system for streaming uncompressed file(s)...{RESET}")
            self._optimize_system()

        file_size: int = os.path.getsize(file_path)
        if file_size <= 0:
            raise ValueError("File size must be greater than zero.")

        buffer: Queue = Queue(maxsize=BUFFER_SIZE)
        # buffer = SimpleQueue("Disruptor")
        # buffer = ConcurrentQueue()
        byte_map = self._ByteMeUp(CHUNK_SIZE, file_size, num_consumers)

        expected_chunks = set()
        produced_chunks = set()

        chunk_ranges: List[Tuple[int, int]] = []
        chunk_size_per_worker: int = max(CHUNK_SIZE, file_size // MAX_WORKERS)

        current_pos = 0
        while current_pos < file_size:
            expected_chunks.add(current_pos)
            current_pos += CHUNK_SIZE

        for start in range(0, file_size, chunk_size_per_worker):
            end = min(start + chunk_size_per_worker, file_size)
            chunk_ranges.append((start, end))
        
        print(f"{BLUE}End position: {end}{RESET}")
        print(f"{BLUE}Chunk ranges (position): {chunk_ranges}{RESET}")

        def _monitor_completion() -> None:
            for thread in producer_threads:
                thread.join()
            print(f"{PURPLE}All producer threads have completed.{RESET}")
            print(f"{PURPLE}Total chunks produced: {len(produced_chunks)}{RESET}")
            print(f"{PURPLE}Produced chunks: {sorted(produced_chunks)}{RESET}")

            for _ in range(num_consumers):
                buffer.put(None)

        def _file_producer_manager(file_path: str, chunk_size: int, buffer: Queue, start: int, end: int) -> None:
            try:
                self._file_producer(file_path, chunk_size, buffer, start, end)
                current_pos = start
                while current_pos < end:
                    produced_chunks.add(current_pos)
                    current_pos += chunk_size
            except Exception as e:
                print(f"{RED}Producer error: {e}{RESET}")
                raise

        producer_threads: List[Thread] = []
        for start, end in chunk_ranges:
            thread: Thread = Thread(
                target=_file_producer_manager,
                args=(file_path, CHUNK_SIZE, buffer, start, end),
                daemon=True
            )
            producer_threads.append(thread)
            thread.start()

        monitor_thread: Thread = Thread(target=_monitor_completion, daemon=True)
        monitor_thread.start()

        result_queue: asyncio.Queue = asyncio.Queue()
        ordered_results: Dict[int, bytes] = {}
        next_expected_position: int = 0  

        async def _consume_and_queue(consumer_id: int) -> None:
            chunks_processed = 0
            consumer_range = byte_map.consumer_ranges[consumer_id - 1]
            expected_chunks = consumer_range[1] - consumer_range[0]
            try:
                async for chunk_info in self._file_consumer(buffer, consumer_id, byte_map):
                    chunks_processed += 1
                    await result_queue.put(chunk_info)
                    print(f"{MAGENTA}Consumer {consumer_id}: processed chunk {chunks_processed}/{expected_chunks}{RESET}")
            except Exception as e:
                print(f"{RED}Consumer {consumer_id} error in consume_and_queue: {e}{RESET}")
            finally:
                print(f"{MAGENTA}Consumer {consumer_id} finished: processed {chunks_processed}/{expected_chunks} chunks{RESET}")
                await result_queue.put(None)

        try:
            consumer_tasks = [
                asyncio.create_task(_consume_and_queue(i+1))
                for i in range(num_consumers)
            ]

            completed_consumers: int = 0
            positions_received = set()  
            total_received_size: int = 0

            while completed_consumers < num_consumers:
                result = await result_queue.get()
                if result is None:
                    completed_consumers += 1
                    print(f"{BLUE}Consumer completed. {completed_consumers}/{num_consumers} done{RESET}")
                    continue

                position = result['position']
                data = result['data']
                
                if position in positions_received:
                    print(f"{RED}Duplicate chunk received for position {position}. Skipping.{RESET}")
                    continue
                    
                positions_received.add(position)
                chunk_size = len(data)
                total_received_size += chunk_size
                ordered_results[position] = data
                print(f"{GREEN}Received chunk at position {position}, chunk size: {chunk_size} bytes, total received: {total_received_size} bytes{RESET}")
                
                while next_expected_position in ordered_results:
                    chunk = ordered_results.pop(next_expected_position)
                    # print(f"{GREEN}Yielding chunk at position {next_expected_position}{RESET}")
                    yield chunk
                    next_expected_position = next_expected_position + CHUNK_SIZE  

            remaining_positions = sorted(ordered_results.keys())
            if remaining_positions:
                print(f"{RED}Processing {len(remaining_positions)} remaining chunks{RESET}")
                for position in remaining_positions:
                    if position >= file_size:
                        print(f"{RED}Skipping chunk at position {position} as it's beyond file size {file_size}{RESET}")
                        continue
                    print(f"{RED}Yielding remaining chunk at position {position}{RESET}")
                    yield ordered_results[position]
        
            print(f"{GREEN}All consumers have completed their tasks.{RESET}")
            print(f"{BLUE}Size of the original file: {file_size} bytes{RESET}")
            print(f"{GREEN}Total bytes received: {total_received_size} bytes{RESET}")
            print(f"{GREEN}Total chunks received: {len(positions_received)}{RESET}")

            if total_received_size > file_size:
                print(f"{RED}Total bytes received exceed the original file size. Something went wrong.{RESET}")
                print(f"{RED}There are {total_received_size - file_size} extra bytes received{RESET}")
            
            if total_received_size < file_size:
                print(f"{RED}Total bytes received are less than the original file size. Something went wrong.{RESET}")
                print(f"{RED}There are {file_size - total_received_size} bytes missing{RESET}")

                if buffer.qsize() > 0:
                    print(f"{RED}There are chunks remaining in the buffer{RESET}")
                    while not buffer.empty():
                        chunk_info = buffer.get()
                        position = chunk_info['position']
                        data = chunk_info['data']
                        chunk_size = len(data)
                        total_received_size += chunk_size
                        ordered_results[position] = data
                        print(f"{RED}Received chunk at position {position}, chunk size: {chunk_size} bytes, total received: {total_received_size} bytes{RESET}")
                else:
                    print(f"{RED}No chunks remaining in the buffer{RESET}")

            if total_received_size == file_size:
                print(f"{GREEN}Total bytes received match the original file size. File successfully streamed.{RESET}")
                    
        finally:
            print(f"{BLUE}Cleaning up producer threads and consumer tasks...{RESET}")
            for task in consumer_tasks:
                task.cancel()

            await asyncio.gather(*consumer_tasks, return_exceptions=True)

            for thread in producer_threads:
                if thread.is_alive():
                    print(f"{BLUE}Producer thread still running. Attempting to join...{RESET}")
                    thread.join(timeout=1.0)
            if monitor_thread.is_alive():
                monitor_thread.join(timeout=1.0)
            print(f"{GREEN}All producer threads and consumer tasks have been cleaned up.{RESET}")
            print(f"{BLUE}Attempting to shut down the executor...{RESET}")
            self.__executor.shutdown(wait=False)
            print(f"{GREEN}Executor has been shut down.{RESET}")

    def _make_sync_generator(self, async_gen: AsyncGenerator[Any, None]) -> Generator[Any, None, None]:
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        async_gen = async_gen.__aiter__() 
        
        while True:
            try:
                item = loop.run_until_complete(async_gen.__anext__())
                yield item
            except StopAsyncIteration:
                break