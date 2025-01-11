document.addEventListener('DOMContentLoaded', function() {
    const workerScript = new Worker('worker.js');

    const workerBlob = new Blob([workerScript], { type: 'application/javascript' });
    const workerUrl = URL.createObjectURL(workerBlob);

    const form = document.getElementById('datasetUploadForm');
    const fileInput = document.getElementById('singleFile');
    const progressDisplay = document.getElementById('uploadProgress');
    const uploadButton = form.querySelector('button[type="submit"]');
    const batchUploadCheckBox = document.getElementById('useBatchUpload');
    const compressionCheckbox = document.getElementById('useCompression');
    const parallelCheckbox = document.getElementById('useParallel');
    const chunkSizeInput = document.getElementById('chunkSize');
    const parallelCountInput = document.getElementById('parallelCount');
    const compressionLevelSelect = document.getElementById('compressionLevel');

    const CONFIG = {
        RETRY_ATTEMPTS: 3,
        BENCHMARK_LIMIT: 600000,
        DEBUG: true,
        LOG_LEVEL: 'TRACE',
        PRELOAD_CHUNKS: 2, 
        MEMORY_LIMIT: 500 * 1024 * 1024, 
        MAX_WORKERS: navigator.hardwareConcurrency || 4, 
        MIN_WORKERS: 2,  
        WORKER_TIMEOUT: 30000,  
        WORKER_RETRY_ATTEMPTS: 3,
        WORKER_PROCESSING_TIMEOUT: 60000,
        ARRAY_BUFFER_TIMEOUT: 30000 
    };

    const uploadState = {
        isUploading: false,
        currentChunk: 0,
        totalChunks: 0,
        preloadedChunks: new Map(),
        activeWorkers: new Set(),
        abortController: null,
        pause: false,
        workers: []
    };

    class WorkerPool {
        constructor(workerScript, maxWorkers) {
            this.workerScript = workerScript;
            this.maxWorkers = maxWorkers;
            this.workers = new Map(); 
            this.initializeWorkers();
        }

        initializeWorkers() {
            const workerCount = Math.min(CONFIG.MIN_WORKERS, this.maxWorkers);
            for (let i = 0; i < workerCount; i++) {
                this.createWorker();
            }
        }

        createWorker() {
            const worker = new Worker(this.workerScript);
            this.workers.set(worker, { busy: false, lastUsed: Date.now() });
            return worker;
        }

        async getAvailableWorker() {
            try {
                for (let [worker, status] of this.workers) {
                    if (!status.busy) {
                        return worker;
                    }
                }

                if (this.workers.size < this.maxWorkers) {
                    const worker = this.createWorker();
                    return worker;
                }

                return await new Promise((resolve, reject) => {
                    const timeout = setTimeout(() => {
                        clearInterval(checkWorkers);
                        reject(new Error('Timed out waiting for available worker'));
                    }, CONFIG.WORKER_TIMEOUT);

                    const checkWorkers = setInterval(() => {
                        for (let [worker, status] of this.workers) {
                            if (!status.busy) {
                                clearInterval(checkWorkers);
                                clearTimeout(timeout);
                                resolve(worker);
                                return;
                            }
                        }
                    }, 100);
                });
            } catch (error) {
                Logger.warn('WorkerPool', 'Failed to get available worker', { error });    
                this.cleanupStaleWorkers();     
                throw error;
            }
        }

        markWorkerAsBusy(worker) {
            const status = this.workers.get(worker);
            if (status) {
                status.busy = true;
                status.lastUsed = Date.now();
            }
        }

        markWorkerAsAvailable(worker) {
            const status = this.workers.get(worker);
            if (status) {
                status.busy = false;
                status.lastUsed = Date.now();
            }
        }
        cleanupStaleWorkers() {
            const now = Date.now();
            for (let [worker, status] of this.workers) {
                if (status.busy && (now - status.lastUsed > CONFIG.WORKER_TIMEOUT)) {
                    worker.terminate();
                    this.workers.delete(worker);
                    
                    if (this.workers.size < this.maxWorkers) {
                        this.createWorker();
                    }
                }
            }
        }

        terminateAll() {
            for (let [worker] of this.workers) {
                worker.terminate();
            }
            this.workers.clear();
        }
    }

    const workerPool = new WorkerPool(workerUrl, CONFIG.MAX_WORKERS);

    const Logger = {
        LEVELS: {
            TRACE: 0,
            DEBUG: 1,
            INFO: 2,
            WARN: 3,
            ERROR: 4
        },

        timestamp() {
            return new Date().toISOString();
        },

        safeStringify(obj, maxDepth = 3) {
            const seen = new WeakSet();
            
            return JSON.stringify(obj, (key, value) => {
                if (value === undefined) return '[undefined]';
                if (value === null) return null;
                if (Number.isNaN(value)) return '[NaN]';
                
                if (value instanceof Error) {
                    return {
                        message: value.message,
                        stack: value.stack,
                        name: value.name
                    };
                }

                if (value instanceof HTMLElement) {
                    return `[HTMLElement ${value.tagName.toLowerCase()}]`;
                }

                if (typeof value !== 'object' || 
                    value instanceof Number ||
                    value instanceof String ||
                    value instanceof Boolean) {
                    return value;
                }

                if (Array.isArray(value)) {
                    return value;
                }

                if (seen.has(value)) {
                    return '[Circular]';
                }
                seen.add(value);

                if (maxDepth <= 0) {
                    return '[Object]';
                }

                try {
                    const processed = {};
                    for (const [k, v] of Object.entries(value)) {
                        processed[k] = this.safeStringify(v, maxDepth - 1);
                    }
                    return processed;
                } catch (error) {
                    return `[Unable to stringify: ${error.message}]`;
                }
            });
        },

        formatMessage(level, context, message, data = null) {
            const timestamp = this.timestamp();
            let dataString = '';
            
            if (data !== null) {
                try {
                    dataString = ` | data: ${this.safeStringify(data)}`;
                } catch (error) {
                    dataString = ` | data: [Error stringifying data: ${error.message}]`;
                }
            }
            
            return `[${timestamp}] ${level.padEnd(5)} [${context}] ${message}${dataString}`;
        },

        shouldLog(level) {
            return CONFIG.DEBUG && this.LEVELS[level] >= this.LEVELS[CONFIG.LOG_LEVEL];
        },

        trace(context, message, data = null) {
            if (this.shouldLog('TRACE')) {
                this._log('TRACE', context, message, data);
            }
        },

        debug(context, message, data = null) {
            if (this.shouldLog('DEBUG')) {
                this._log('DEBUG', context, message, data);
            }
        },

        info(context, message, data = null) {
            if (this.shouldLog('INFO')) {
                this._log('INFO', context, message, data);
            }
        },

        warn(context, message, data = null) {
            if (this.shouldLog('WARN')) {
                this._log('WARN', context, message, data);
            }
        },

        error(context, message, error = null) {
            if (this.shouldLog('ERROR')) {
                const errorData = error ? {
                    message: error.message,
                    stack: error.stack,
                    name: error.name
                } : null;
                this._log('ERROR', context, message, errorData);
            }
        },

        _log(level, context, message, data) {
            const formattedMessage = this.formatMessage(level, context, message, data);
            switch (level) {
                case 'ERROR':
                    console.error(formattedMessage);
                    break;
                case 'WARN':
                    console.warn(formattedMessage);
                    break;
                default:
                    console.log(formattedMessage);
            }
        }
    };

    compressionCheckbox.addEventListener('change', function() {
        document.getElementById('compressionLevelContainer').style.display = 
            this.checked ? 'block' : 'none';
        Logger.info('Compression', 'Compression setting changed', { enabled: this.checked });
    });

    parallelCheckbox.addEventListener('change', function() {
        document.getElementById('parallelCountContainer').style.display = 
            this.checked ? 'block' : 'none';
        Logger.info('ParallelUpload', 'Parallel upload setting changed', { enabled: this.checked });
    });

    class UploadProgress {
        constructor(totalSize) {
            this.totalSize = totalSize;
            this.uploadedSize = 0;
            this.startTime = Date.now();
            this.chunkTimes = [];

            Logger.info('UploadProgress', 'Upload initiated', {
                totalSize: `${(totalSize / (1024 * 1024)).toFixed(2)} MB`
            });
        }

        addChunkTime(time) {
            this.chunkTimes.push(time);
            Logger.debug('UploadProgress', 'Chunk upload completed', {
                chunkNumber: this.chunkTimes.length,
                uploadTime: `${time.toFixed(2)}s`
            });
        }

        complete(totalChunks) {
            const totalTime = (Date.now() - this.startTime) / 1000;
            const averageChunkTime = (this.chunkTimes.reduce((a, b) => a + b, 0) / this.chunkTimes.length).toFixed(2);

            const completionData = {
                totalChunks,
                averageChunkTime: `${averageChunkTime}s`,
                totalTime: `${totalTime.toFixed(2)}s`,
                totalUploaded: `${(this.uploadedSize / (1024 * 1024)).toFixed(2)} MB`
            };

            Logger.info('UploadProgress', 'Upload completed', completionData);

            alert(`Upload Complete!\nTotal Chunks: ${totalChunks}` +
                  `\nAverage Chunk Time: ${averageChunkTime} seconds\nTotal Time: ${totalTime.toFixed(2)} seconds`);
            uploadButton.disabled = false;
        }
    }

    class MemoryManager {
        constructor(config = {}) {
            this.config = {
                warningThreshold: config.warningThreshold || 0.8, 
                criticalThreshold: config.criticalThreshold || 0.9, 
                checkInterval: config.checkInterval || 5000, 
                cleanupCallback: config.cleanupCallback || null
            };
            
            this.isMonitoring = false;
            this.monitorInterval = null;
        }

        async estimateMemoryPressure() {
            try {
                if (navigator.deviceMemory) {
                    const maxMemory = navigator.deviceMemory * 1024; // Convert to MB
                    const estimate = await this.getMemoryEstimate();
                    return estimate / maxMemory;
                }

                if ('scheduling' in window && 'isInputPending' in scheduling) {
                    const pressure = await navigator.scheduling.getCurrentPressure();
                    return pressure.value;
                }

                const resources = performance.getEntriesByType('resource');
                const totalTransferSize = resources.reduce((total, resource) => 
                    total + (resource.transferSize || 0), 0);
            
                return Math.min(totalTransferSize / (50 * 1024 * 1024), 1); 
            
            } catch (error) {
            console.warn('Memory estimation failed:', error);
            return 0;
            }
        }

        async getMemoryEstimate() {
            if ('memory' in performance) {
            return performance.memory.usedJSHeapSize;
            }

            try {
                const measurement = await performance.measureUserAgentSpecificMemory();
                return measurement.bytes;
            } catch {
            return 0;
            }
        }

        startMonitoring() {
            if (this.isMonitoring) return;
            
            this.isMonitoring = true;
            this.monitorInterval = setInterval(async () => {
            const pressure = await this.estimateMemoryPressure();
            
            if (pressure >= this.config.criticalThreshold) {
                this.handleCriticalMemory();
            } else if (pressure >= this.config.warningThreshold) {
                this.handleWarningMemory();
            }
            }, this.config.checkInterval);
        }

        stopMonitoring() {
            if (!this.isMonitoring) return;
            
            clearInterval(this.monitorInterval);
            this.isMonitoring = false;
        }

        async handleCriticalMemory() {
            if (this.config.cleanupCallback) {
                await this.config.cleanupCallback();
            }

            if (window.gc) {
                try {
                    window.gc();
                } catch (e) {
                    console.warn('Manual GC failed:', e);
                }
            }

            if ('caches' in window) {
                try {
                    const cacheNames = await caches.keys();
                    await Promise.all(
                    cacheNames.map(name => caches.delete(name))
                    );
                } catch (e) {
                    console.warn('Cache cleanup failed:', e);
                }
            }
        }

        handleWarningMemory() {
            window.dispatchEvent(new CustomEvent('memory-warning', {
            detail: {
                timestamp: Date.now()
            }
            }));
        }
    }

    let benchmarkTimer;

    function startBenchmarkTimer(progressTracker) {
        clearTimeout(benchmarkTimer);
        benchmarkTimer = setTimeout(() => {
            const elapsedTime = (Date.now() - progressTracker.startTime) / 1000;
            const uploadedMB = (progressTracker.uploadedSize / (1024 * 1024)).toFixed(2);

            Logger.warn('Benchmark', 'Benchmark timeout reached', {
                uploadedSize: `${uploadedMB} MB`,
                elapsedTime: `${elapsedTime.toFixed(2)}s`
            });

            alert(`Benchmark Timeout Reached:\nTotal Uploaded: ${uploadedMB} MB\nElapsed Time: ${elapsedTime.toFixed(2)} seconds`);
            uploadButton.disabled = false;
            throw new Error('Benchmark timer exceeded 5 minutes.');
        }, CONFIG.BENCHMARK_LIMIT);
    }

    async function processChunkWithWorker(chunk, compressionLevel, workerPool) {
        let worker;
        try {
            for (let attempt = 0; attempt < CONFIG.WORKER_RETRY_ATTEMPTS; attempt++) {
                try {
                    worker = await workerPool.getAvailableWorker();
                    break;
                } catch (error) {
                    if (attempt === CONFIG.WORKER_RETRY_ATTEMPTS - 1) {
                        throw new Error(`Failed to acquire worker after ${CONFIG.WORKER_RETRY_ATTEMPTS} attempts: ${error.message}`);
                    }
                    Logger.warn('WorkerManager', `Retry attempt ${attempt + 1} to acquire worker`, { error });
                    await new Promise(resolve => setTimeout(resolve, Math.pow(2, attempt) * 1000));
                }
            }

            workerPool.markWorkerAsBusy(worker);

            const arrayBuffer = await Promise.race([
                chunk.arrayBuffer(),
                new Promise((_, reject) => 
                    setTimeout(() => reject(new Error('ArrayBuffer conversion timeout')), 
                    CONFIG.ARRAY_BUFFER_TIMEOUT)
                )
            ]);

            const result = await new Promise((resolve, reject) => {
                const timeoutId = setTimeout(() => {
                    cleanup();
                    reject(new Error('Worker processing timeout'));
                }, CONFIG.WORKER_PROCESSING_TIMEOUT);

                const onMessage = (e) => {
                    if (e.data.success) {
                        clearTimeout(timeoutId);
                        cleanup();
                        resolve(e.data.data);
                    } else {
                        clearTimeout(timeoutId);
                        cleanup();
                        reject(new Error(e.data.error || 'Unknown worker error'));
                    }
                };

                const onError = (error) => {
                    clearTimeout(timeoutId);
                    cleanup();
                    reject(new Error(`Worker error: ${error.message}`));
                };

                const cleanup = () => {
                    worker.removeEventListener('message', onMessage);
                    worker.removeEventListener('error', onError);
                };

                worker.addEventListener('message', onMessage);
                worker.addEventListener('error', onError);

                try {
                    worker.postMessage({
                        mode: 'single',
                        data: {
                            chunk: arrayBuffer,
                            compressionLevel
                        }
                    }, [arrayBuffer]);
                } catch (error) {
                    clearTimeout(timeoutId);
                    cleanup();
                    reject(new Error(`Failed to post message to worker: ${error.message}`));
                }
            });

            return result;

        } catch (error) {
            Logger.error('WorkerManager', 'Chunk processing failed', {
                error: error.message,
                stack: error.stack
            });
            throw error;

        } finally {
            if (worker) {
                try {
                    workerPool.markWorkerAsAvailable(worker);
                } catch (error) {
                    Logger.warn('WorkerManager', 'Failed to mark worker as available', { error });
                }
            }
        }
    }

    async function processChunk(chunk, useCompression, compressionLevel, workerPool) {
        Logger.debug('ChunkProcessor', 'Processing chunk', {
            size: `${(chunk.size / (1024 * 1024)).toFixed(2)} MB`,
            compression: useCompression,
            level: compressionLevel
        });

        if (useCompression) {
            return processChunkWithWorker(chunk, compressionLevel, workerPool);
        }

        return new Promise((resolve) => {
            const reader = new FileReader();
            reader.onload = function(e) {
                Logger.trace('ChunkProcessor', 'Chunk processed without compression');
                resolve(new Uint8Array(e.target.result));
            };
            reader.readAsArrayBuffer(chunk);
        });
    }

    async function processBatchWithWorker(batch, compressionLevel, workerPool) {
        let worker;
        try {
            for (let attempt = 0; attempt < CONFIG.WORKER_RETRY_ATTEMPTS; attempt++) {
                try {
                    worker = await workerPool.getAvailableWorker();
                    break;
                } catch (error) {
                    if (attempt === CONFIG.WORKER_RETRY_ATTEMPTS - 1) {
                        throw new Error(`Failed to acquire worker after ${CONFIG.WORKER_RETRY_ATTEMPTS} attempts: ${error.message}`);
                    }
                    Logger.warn('WorkerManager', `Retry attempt ${attempt + 1} to acquire worker`, { error });
                    await new Promise(resolve => setTimeout(resolve, Math.pow(2, attempt) * 1000));
                }
            }

            workerPool.markWorkerAsBusy(worker);

            const arrayBuffers = await Promise.all(batch.map(chunk => chunk.arrayBuffer()));

            const result = await new Promise((resolve, reject) => {
                const timeoutId = setTimeout(() => {
                    cleanup();
                    reject(new Error('Worker processing timeout'));
                }, CONFIG.WORKER_PROCESSING_TIMEOUT);

                const onMessage = (e) => {
                    if (e.data.success) {
                        clearTimeout(timeoutId);
                        cleanup();
                        resolve(e.data.data);
                    } else {
                        clearTimeout(timeoutId);
                        cleanup();
                        reject(new Error(e.data.error || 'Unknown worker error'));
                    }
                };

                const onError = (error) => {
                    clearTimeout(timeoutId);
                    cleanup();
                    reject(new Error(`Worker error: ${error.message}`));
                };

                const cleanup = () => {
                    worker.removeEventListener('message', onMessage);
                    worker.removeEventListener('error', onError);
                };

                worker.addEventListener('message', onMessage);
                worker.addEventListener('error', onError);

                try {
                    worker.postMessage({
                        mode: 'batch',
                        data: {
                            chunks: arrayBuffers,
                            compressionLevel
                        }
                    }, arrayBuffers);
                } catch (error) {
                    clearTimeout(timeoutId);
                    cleanup();
                    reject(new Error(`Failed to post message to worker: ${error.message}`));
                }
            });

            return result;

        } catch (error) {
            Logger.error('WorkerManager', 'Chunk processing failed', {
                error: error.message,
                stack: error.stack
            });
            throw error;

        } finally {
            if (worker) {
                try {
                    workerPool.markWorkerAsAvailable(worker);
                } catch (error) {
                    Logger.warn('WorkerManager', 'Failed to mark worker as available', { error });
                }
            }
        }
    }

    class ChunkPreloader {
        constructor(file, chunkSize, maxPreloadChunks) {
            this.file = file;
            this.chunkSize = chunkSize;
            this.maxPreloadChunks = maxPreloadChunks;
            this.preloadedChunks = new Map();
            this.currentIndex = 0;
            this.lastLoadedIndex = -1;  
        }

        async preloadNextChunks() {
            while (this.preloadedChunks.size < this.maxPreloadChunks && 
                this.currentIndex < Math.ceil(this.file.size / this.chunkSize)) {
                const start = this.currentIndex * this.chunkSize;
                const end = Math.min(start + this.chunkSize, this.file.size);
                
                if (!this.preloadedChunks.has(this.currentIndex) && this.currentIndex > this.lastLoadedIndex) {
                    const chunk = this.file.slice(start, end);
                    this.preloadedChunks.set(this.currentIndex, {
                        chunk,
                        start,
                        end
                    });
                    this.lastLoadedIndex = this.currentIndex;
                }
                this.currentIndex++;
            }
        }

        getBatch(startIndex, batchSize) {
            const batch = [];
            for (let i = 0; i < batchSize; i++) {
                const index = startIndex + i;
                if (index >= Math.ceil(this.file.size / this.chunkSize)) break;
                batch.push(this.getChunk(index).chunk);
            }
            return batch;
        }

        getChunk(index) {
            const chunkData = this.preloadedChunks.get(index);
            if (chunkData) {
                this.preloadedChunks.delete(index);
                return chunkData;
            }
        
            const start = index * this.chunkSize;
            const end = Math.min(start + this.chunkSize, this.file.size);
            return {
                chunk: this.file.slice(start, end),
                start,
                end
            };
        }

        clear() {
            this.preloadedChunks.clear();
            this.lastLoadedIndex = -1;
        }
    }

    async function uploadChunk(chunkIndex, chunkData, formMetadata, csrfToken, progressTracker, useCompression, compressionLevel, workerPool) {
        const chunkFormData = new FormData();
        const chunkNumber = chunkIndex + 1;
        
        try {
            const startTime = Date.now();
            Logger.debug('ChunkUpload', `Starting chunk upload`, {
                chunkNumber,
                chunkStart: chunkData.start,
                chunkEnd: chunkData.end,
                size: `${(chunkData.chunk.size / (1024 * 1024)).toFixed(2)} MB`
            });

            const processedChunk = await processChunk(chunkData.chunk, useCompression, compressionLevel, workerPool);
            
            chunkFormData.append('dataset_file', new Blob([processedChunk], { type: 'application/octet-stream' }));
            chunkFormData.append('chunk_index', chunkIndex);
            chunkFormData.append('chunk_start', chunkData.start);
            chunkFormData.append('chunk_end', chunkData.end);
            chunkFormData.append('is_compressed', useCompression.toString());

            for (let [key, value] of formMetadata.entries()) {
                chunkFormData.append(key, value);
            }

            const signal = uploadState.abortController?.signal;
            const response = await fetch(form.action, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken
                },
                body: chunkFormData,
                signal
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const endTime = Date.now();
            const uploadTime = (endTime - startTime) / 1000;
            
            progressTracker.addChunkTime(uploadTime);
            progressTracker.uploadedSize += chunkData.chunk.size;

            Logger.info('ChunkUpload', `Chunk ${chunkNumber} completed successfully`, {
                uploadTime: `${uploadTime.toFixed(2)}s`,
                size: `${(chunkData.chunk.size / (1024 * 1024)).toFixed(2)} MB`,
                start: chunkData.start,
                end: chunkData.end
            });

        } catch (error) {
            if (error.name === 'AbortError') {
                Logger.info('ChunkUpload', 'Upload aborted by user');
                throw error;
            }
            
            Logger.error('ChunkUpload', `Chunk ${chunkNumber} upload failed`, {
                error: error.message,
                stack: error.stack,
                chunkStart: chunkData.start,
                chunkEnd: chunkData.end
            });
            throw error;
        }
    }

    async function uploadBatch(batchIndex, batch, formMetadata, csrfToken, progressTracker, useCompression, compressionLevel, workerPool) {
        const chunkFormData = new FormData();
        
        try {
            const startTime = Date.now();
            Logger.debug('BatchUpload', `Starting batch upload`, {
                batchIndex,
                batchSize: batch.length
            });

            const processedBatch = await processBatchWithWorker(batch, compressionLevel, workerPool);

            processedBatch.forEach((processedChunk, i) => {
                chunkFormData.append(`dataset_file_${batchIndex}_${i}`, 
                    new Blob([processedChunk], { type: 'application/octet-stream' }));
            });

            chunkFormData.append('batch_index', batchIndex);
            chunkFormData.append('batch_size', batch.length);
            chunkFormData.append('is_compressed', useCompression.toString());

            for (let [key, value] of formMetadata.entries()) {
                chunkFormData.append(key, value);
            }

            const signal = uploadState.abortController?.signal;
            const response = await fetch(form.action, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken
                },
                body: chunkFormData,
                signal
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const responseText = await response.text();
            Logger.debug('BatchUpload', `Server response for batch ${batchIndex}`, {
                response: responseText
            });

            const endTime = Date.now();
            const uploadTime = (endTime - startTime) / 1000;

            progressTracker.addChunkTime(uploadTime * batch.length);
            batch.forEach(chunk => {
                progressTracker.uploadedSize += chunk.size;
            });

            Logger.info('BatchUpload', `Batch ${batchIndex} completed successfully`, {
                uploadTime: `${uploadTime.toFixed(2)}s`,
                batchSize: batch.length
            });

        } catch (error) {
            if (error.name === 'AbortError') {
                Logger.info('BatchUpload', 'Upload aborted by user');
                throw error;
            }

            Logger.error('BatchUpload', `Batch ${batchIndex} upload failed`, {
                error: error.message,
                stack: error.stack
            });
            throw error;
        }
    }

    async function uploadLargeFile(file) {
        uploadState.isUploading = true;
        uploadState.abortController = new AbortController();
        const useBatchUpload = batchUploadCheckBox.checked;
        const chunkSize = parseInt(chunkSizeInput.value) * 1024 * 1024;
        const batchSize = 5; 
        const totalChunks = Math.ceil(file.size / chunkSize);
        const useCompression = compressionCheckbox.checked;
        const useParallel = parallelCheckbox.checked;
        const compressionLevel = compressionLevelSelect.value;
        const parallelCount = useParallel ? parseInt(parallelCountInput.value) : 1;
    
        const chunkPreloader = new ChunkPreloader(file, chunkSize, CONFIG.PRELOAD_CHUNKS);
        await chunkPreloader.preloadNextChunks();
    
        Logger.info('UploadManager', 'Starting file upload', {
            fileName: file.name,
            fileSize: `${(file.size / (1024 * 1024)).toFixed(2)} MB`,
            batchUpload: useBatchUpload ? true : false,
            ...(useBatchUpload
                ? { batchSize }
                : { chunkSize: `${chunkSizeInput.value} MB` }),
            totalChunks,
            compression: {
                enabled: useCompression,
                level: compressionLevel
            },
            parallel: {
                enabled: useParallel,
                count: parallelCount
            }
        });
    
        const progressTracker = new UploadProgress(file.size);
        const csrfToken = form.querySelector('[name=csrfmiddlewaretoken]').value;
        const formMetadata = new FormData(form);
        formMetadata.delete('dataset_file');
        formMetadata.append('total_chunks', totalChunks);
        formMetadata.append('original_filename', file.name);
        formMetadata.append('upload_session_id', generateUUID());
    
        let activeUploads = [];
        startBenchmarkTimer(progressTracker);
    
        if (!useBatchUpload) {
            const processedChunks = new Set();
    
            try {
                for (let i = 0; i < totalChunks; i++) {
                    if (uploadState.pause) {
                        await new Promise(resolve => {
                            const checkPause = () => {
                                if (!uploadState.pause) {
                                    resolve();
                                } else {
                                    setTimeout(checkPause, 100);
                                }
                            };
                            checkPause();
                        });
                    }
    
                    if (processedChunks.has(i)) continue;
    
                    const chunkData = chunkPreloader.getChunk(i);
    
                    const uploadPromise = (async () => {
                        for (let attempt = 0; attempt < CONFIG.RETRY_ATTEMPTS; attempt++) {
                            try {
                                await uploadChunk(i, chunkData, formMetadata, csrfToken, progressTracker, useCompression, compressionLevel, workerPool);
                                processedChunks.add(i);
                                return;
                            } catch (error) {
                                if (error.name === 'AbortError') throw error;
                                if (attempt === CONFIG.RETRY_ATTEMPTS - 1) throw error;
                                await new Promise(resolve => setTimeout(resolve, Math.pow(2, attempt) * 1000));
                            }
                        }
                    })();
    
                    uploadPromise.catch(error => {
                        Logger.error('UploadManager', `Failed to upload chunk ${i}`, { error });
                    }).finally(() => {
                        activeUploads = activeUploads.filter(p => p !== uploadPromise);
                    });
    
                    activeUploads.push(uploadPromise);
    
                    if (activeUploads.length >= parallelCount) {
                        await Promise.race(activeUploads);
                    }
    
                    await chunkPreloader.preloadNextChunks();
                }
                await Promise.all(activeUploads);
            } catch (error) {
                Logger.error('UploadManager', 'Upload failed', error);
                progressDisplay.textContent = `Error: ${error.message}`;
            }
        } else {
            try {
                for (let i = 0; i < totalChunks; i += batchSize) {
                    if (uploadState.pause) {
                        await new Promise(resolve => {
                            const checkPause = () => {
                                if (!uploadState.pause) {
                                    resolve();
                                } else {
                                    setTimeout(checkPause, 100);
                                }
                            };
                            checkPause();
                        });
                    }
    
                    const batch = chunkPreloader.getBatch(i, batchSize);
    
                    const uploadPromise = (async () => {
                        for (let attempt = 0; attempt < CONFIG.RETRY_ATTEMPTS; attempt++) {
                            try {
                                await uploadBatch(i / batchSize, batch, formMetadata, csrfToken, progressTracker, useCompression, compressionLevel, workerPool);
                                return;
                            } catch (error) {
                                if (attempt === CONFIG.RETRY_ATTEMPTS - 1) throw error;
                                await new Promise(resolve => setTimeout(resolve, Math.pow(2, attempt) * 1000));
                            }
                        }
                    })();
    
                    activeUploads.push(uploadPromise);
    
                    if (activeUploads.length >= CONFIG.MAX_WORKERS) {
                        await Promise.race(activeUploads);
                    }
    
                    await chunkPreloader.preloadNextChunks();
                }
                await Promise.all(activeUploads);
    
                progressTracker.complete(totalChunks);
            } catch (error) {
                Logger.error('UploadManager', 'Upload failed', error);
                progressDisplay.textContent = `Error: ${error.message}`;
            }
        }
    
        uploadButton.disabled = false;
        uploadState.isUploading = false;
        uploadState.abortController = null;
        chunkPreloader.clear();
        workerPool.terminateAll();
    }    

    function generateUUID(){
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    }

    const pauseButton = document.createElement('button');
    pauseButton.textContent = 'Pause Upload';
    pauseButton.onclick = () => {
        uploadState.pause = !uploadState.pause;
        pauseButton.textContent = uploadState.pause ? 'Resume Upload' : 'Pause Upload';
    };
    form.appendChild(pauseButton);

    const cancelButton = document.createElement('button');
    cancelButton.textContent = 'Cancel Upload';
    cancelButton.onclick = () => {
        if (uploadState.isUploading && uploadState.abortController) {
            uploadState.abortController.abort();
        }
    };
    form.appendChild(cancelButton);

    if (form) {
        form.addEventListener('submit', async function (event) {
            event.preventDefault();

            const file = fileInput.files[0];
            if (!file) {
                Logger.warn('FormValidation', 'No file selected');
                alert('Please select a file to upload');
                return;
            }

            if (file.size > 1024 * 1024 * 1024 * 1024) {
                Logger.warn('FormValidation', 'File size exceeds limit', {
                    fileSize: `${(file.size / (1024 * 1024 * 1024)).toFixed(2)} GB`,
                    limit: '1 TB'
                });
                alert('File size exceeds maximum upload limit');
                return;
            }

            uploadButton.disabled = true;
            await uploadLargeFile(file);
        });
    }
});

document.addEventListener('DOMContentLoaded', function() {

    const workerBlob = new Blob([workerScript], { type: 'application/javascript' });
    const workerUrl = URL.createObjectURL(workerBlob);

    const form = document.getElementById('datasetUploadForm');
    const fileInput = document.getElementById('singleFile');
    const progressDisplay = document.getElementById('uploadProgress');
    const uploadButton = form.querySelector('button[type="submit"]');
    const compressionCheckbox = document.getElementById('useCompression');
    const parallelCheckbox = document.getElementById('useParallel');
    const chunkSizeInput = document.getElementById('chunkSize');
    const parallelCountInput = document.getElementById('parallelCount');
    const compressionLevelSelect = document.getElementById('compressionLevel');

    const CONFIG = {
        RETRY_ATTEMPTS: 3,
        BENCHMARK_LIMIT: 600000,
        DEBUG: true,
        LOG_LEVEL: 'INFO',
        PRELOAD_CHUNKS: 2, 
        MEMORY_LIMIT: 500 * 1024 * 1024, 
        MAX_WORKERS: navigator.hardwareConcurrency || 4, 
        MIN_WORKERS: 2,  
        WORKER_TIMEOUT: 30000,  
        WORKER_RETRY_ATTEMPTS: 3,
        WORKER_PROCESSING_TIMEOUT: 60000,
        ARRAY_BUFFER_TIMEOUT: 30000 
    };

    const uploadState = {
        isUploading: false,
        currentChunk: 0,
        totalChunks: 0,
        preloadedChunks: new Map(),
        activeWorkers: new Set(),
        abortController: null,
        pause: false,
        workers: []
    };

    class WorkerPool {
        constructor(workerScript, maxWorkers) {
            this.workerScript = workerScript;
            this.maxWorkers = maxWorkers;
            this.workers = new Map(); 
            this.initializeWorkers();
        }

        initializeWorkers() {
            const workerCount = Math.min(CONFIG.MIN_WORKERS, this.maxWorkers);
            for (let i = 0; i < workerCount; i++) {
                this.createWorker();
            }
        }

        createWorker() {
            const worker = new Worker(this.workerScript);
            this.workers.set(worker, { busy: false, lastUsed: Date.now() });
            return worker;
        }

        async getAvailableWorker() {
            try {
                for (let [worker, status] of this.workers) {
                    if (!status.busy) {
                        return worker;
                    }
                }

                if (this.workers.size < this.maxWorkers) {
                    const worker = this.createWorker();
                    return worker;
                }

                return await new Promise((resolve, reject) => {
                    const timeout = setTimeout(() => {
                        clearInterval(checkWorkers);
                        reject(new Error('Timed out waiting for available worker'));
                    }, CONFIG.WORKER_TIMEOUT);

                    const checkWorkers = setInterval(() => {
                        for (let [worker, status] of this.workers) {
                            if (!status.busy) {
                                clearInterval(checkWorkers);
                                clearTimeout(timeout);
                                resolve(worker);
                                return;
                            }
                        }
                    }, 100);
                });
            } catch (error) {
                Logger.warn('WorkerPool', 'Failed to get available worker', { error });    
                this.cleanupStaleWorkers();     
                throw error;
            }
        }

        markWorkerAsBusy(worker) {
            const status = this.workers.get(worker);
            if (status) {
                status.busy = true;
                status.lastUsed = Date.now();
            }
        }

        markWorkerAsAvailable(worker) {
            const status = this.workers.get(worker);
            if (status) {
                status.busy = false;
                status.lastUsed = Date.now();
            }
        }
        cleanupStaleWorkers() {
            const now = Date.now();
            for (let [worker, status] of this.workers) {
                if (status.busy && (now - status.lastUsed > CONFIG.WORKER_TIMEOUT)) {
                    worker.terminate();
                    this.workers.delete(worker);
                    
                    if (this.workers.size < this.maxWorkers) {
                        this.createWorker();
                    }
                }
            }
        }

        terminateAll() {
            for (let [worker] of this.workers) {
                worker.terminate();
            }
            this.workers.clear();
        }
    }

    const workerPool = new WorkerPool(workerUrl, CONFIG.MAX_WORKERS);

    const Logger = {
        LEVELS: {
            TRACE: 0,
            DEBUG: 1,
            INFO: 2,
            WARN: 3,
            ERROR: 4
        },

        timestamp() {
            return new Date().toISOString();
        },

        safeStringify(obj, maxDepth = 3) {
            const seen = new WeakSet();
            
            return JSON.stringify(obj, (key, value) => {
                if (value === undefined) return '[undefined]';
                if (value === null) return null;
                if (Number.isNaN(value)) return '[NaN]';
                
                if (value instanceof Error) {
                    return {
                        message: value.message,
                        stack: value.stack,
                        name: value.name
                    };
                }

                if (value instanceof HTMLElement) {
                    return `[HTMLElement ${value.tagName.toLowerCase()}]`;
                }

                if (typeof value !== 'object' || 
                    value instanceof Number ||
                    value instanceof String ||
                    value instanceof Boolean) {
                    return value;
                }

                if (Array.isArray(value)) {
                    return value;
                }

                if (seen.has(value)) {
                    return '[Circular]';
                }
                seen.add(value);

                if (maxDepth <= 0) {
                    return '[Object]';
                }

                try {
                    const processed = {};
                    for (const [k, v] of Object.entries(value)) {
                        processed[k] = this.safeStringify(v, maxDepth - 1);
                    }
                    return processed;
                } catch (error) {
                    return `[Unable to stringify: ${error.message}]`;
                }
            });
        },

        formatMessage(level, context, message, data = null) {
            const timestamp = this.timestamp();
            let dataString = '';
            
            if (data !== null) {
                try {
                    dataString = ` | data: ${this.safeStringify(data)}`;
                } catch (error) {
                    dataString = ` | data: [Error stringifying data: ${error.message}]`;
                }
            }
            
            return `[${timestamp}] ${level.padEnd(5)} [${context}] ${message}${dataString}`;
        },

        shouldLog(level) {
            return CONFIG.DEBUG && this.LEVELS[level] >= this.LEVELS[CONFIG.LOG_LEVEL];
        },

        trace(context, message, data = null) {
            if (this.shouldLog('TRACE')) {
                this._log('TRACE', context, message, data);
            }
        },

        debug(context, message, data = null) {
            if (this.shouldLog('DEBUG')) {
                this._log('DEBUG', context, message, data);
            }
        },

        info(context, message, data = null) {
            if (this.shouldLog('INFO')) {
                this._log('INFO', context, message, data);
            }
        },

        warn(context, message, data = null) {
            if (this.shouldLog('WARN')) {
                this._log('WARN', context, message, data);
            }
        },

        error(context, message, error = null) {
            if (this.shouldLog('ERROR')) {
                const errorData = error ? {
                    message: error.message,
                    stack: error.stack,
                    name: error.name
                } : null;
                this._log('ERROR', context, message, errorData);
            }
        },

        _log(level, context, message, data) {
            const formattedMessage = this.formatMessage(level, context, message, data);
            switch (level) {
                case 'ERROR':
                    console.error(formattedMessage);
                    break;
                case 'WARN':
                    console.warn(formattedMessage);
                    break;
                default:
                    console.log(formattedMessage);
            }
        }
    };

    compressionCheckbox.addEventListener('change', function() {
        document.getElementById('compressionLevelContainer').style.display = 
            this.checked ? 'block' : 'none';
        Logger.info('Compression', 'Compression setting changed', { enabled: this.checked });
    });

    parallelCheckbox.addEventListener('change', function() {
        document.getElementById('parallelCountContainer').style.display = 
            this.checked ? 'block' : 'none';
        Logger.info('ParallelUpload', 'Parallel upload setting changed', { enabled: this.checked });
    });

    class UploadProgress {
        constructor(totalSize) {
            this.totalSize = totalSize;
            this.uploadedSize = 0;
            this.startTime = Date.now();
            this.chunkTimes = [];

            Logger.info('UploadProgress', 'Upload initiated', {
                totalSize: `${(totalSize / (1024 * 1024)).toFixed(2)} MB`
            });
        }

        addChunkTime(time) {
            this.chunkTimes.push(time);
            Logger.debug('UploadProgress', 'Chunk upload completed', {
                chunkNumber: this.chunkTimes.length,
                uploadTime: `${time.toFixed(2)}s`
            });
        }

        complete(totalChunks) {
            const totalTime = (Date.now() - this.startTime) / 1000;
            const averageChunkTime = (this.chunkTimes.reduce((a, b) => a + b, 0) / this.chunkTimes.length).toFixed(2);

            const completionData = {
                totalChunks,
                averageChunkTime: `${averageChunkTime}s`,
                totalTime: `${totalTime.toFixed(2)}s`,
                totalUploaded: `${(this.uploadedSize / (1024 * 1024)).toFixed(2)} MB`
            };

            Logger.info('UploadProgress', 'Upload completed', completionData);

            alert(`Upload Complete!\nTotal Chunks: ${totalChunks}` +
                  `\nAverage Chunk Time: ${averageChunkTime} seconds\nTotal Time: ${totalTime.toFixed(2)} seconds`);
            uploadButton.disabled = false;
        }
    }

    class MemoryManager {
        constructor(config = {}) {
            this.config = {
                warningThreshold: config.warningThreshold || 0.8, 
                criticalThreshold: config.criticalThreshold || 0.9, 
                checkInterval: config.checkInterval || 5000, 
                cleanupCallback: config.cleanupCallback || null
            };
            
            this.isMonitoring = false;
            this.monitorInterval = null;
        }

        async estimateMemoryPressure() {
            try {
                if (navigator.deviceMemory) {
                    const maxMemory = navigator.deviceMemory * 1024; // Convert to MB
                    const estimate = await this.getMemoryEstimate();
                    return estimate / maxMemory;
                }

                if ('scheduling' in window && 'isInputPending' in scheduling) {
                    const pressure = await navigator.scheduling.getCurrentPressure();
                    return pressure.value;
                }

                const resources = performance.getEntriesByType('resource');
                const totalTransferSize = resources.reduce((total, resource) => 
                    total + (resource.transferSize || 0), 0);
            
                return Math.min(totalTransferSize / (50 * 1024 * 1024), 1); 
            
            } catch (error) {
            console.warn('Memory estimation failed:', error);
            return 0;
            }
        }

        async getMemoryEstimate() {
            if ('memory' in performance) {
            return performance.memory.usedJSHeapSize;
            }

            try {
                const measurement = await performance.measureUserAgentSpecificMemory();
                return measurement.bytes;
            } catch {
            return 0;
            }
        }

        startMonitoring() {
            if (this.isMonitoring) return;
            
            this.isMonitoring = true;
            this.monitorInterval = setInterval(async () => {
            const pressure = await this.estimateMemoryPressure();
            
            if (pressure >= this.config.criticalThreshold) {
                this.handleCriticalMemory();
            } else if (pressure >= this.config.warningThreshold) {
                this.handleWarningMemory();
            }
            }, this.config.checkInterval);
        }

        stopMonitoring() {
            if (!this.isMonitoring) return;
            
            clearInterval(this.monitorInterval);
            this.isMonitoring = false;
        }

        async handleCriticalMemory() {
            if (this.config.cleanupCallback) {
                await this.config.cleanupCallback();
            }

            if (window.gc) {
                try {
                    window.gc();
                } catch (e) {
                    console.warn('Manual GC failed:', e);
                }
            }

            if ('caches' in window) {
                try {
                    const cacheNames = await caches.keys();
                    await Promise.all(
                    cacheNames.map(name => caches.delete(name))
                    );
                } catch (e) {
                    console.warn('Cache cleanup failed:', e);
                }
            }
        }

        handleWarningMemory() {
            window.dispatchEvent(new CustomEvent('memory-warning', {
            detail: {
                timestamp: Date.now()
            }
            }));
        }
    }

    let benchmarkTimer;

    function startBenchmarkTimer(progressTracker) {
        clearTimeout(benchmarkTimer);
        benchmarkTimer = setTimeout(() => {
            const elapsedTime = (Date.now() - progressTracker.startTime) / 1000;
            const uploadedMB = (progressTracker.uploadedSize / (1024 * 1024)).toFixed(2);

            Logger.warn('Benchmark', 'Benchmark timeout reached', {
                uploadedSize: `${uploadedMB} MB`,
                elapsedTime: `${elapsedTime.toFixed(2)}s`
            });

            alert(`Benchmark Timeout Reached:\nTotal Uploaded: ${uploadedMB} MB\nElapsed Time: ${elapsedTime.toFixed(2)} seconds`);
            uploadButton.disabled = false;
            throw new Error('Benchmark timer exceeded 5 minutes.');
        }, CONFIG.BENCHMARK_LIMIT);
    }

    async function processChunkWithWorker(chunk, compressionLevel, workerPool) {
        let worker;
        try {
            for (let attempt = 0; attempt < CONFIG.WORKER_RETRY_ATTEMPTS; attempt++) {
                try {
                    worker = await workerPool.getAvailableWorker();
                    break;
                } catch (error) {
                    if (attempt === CONFIG.WORKER_RETRY_ATTEMPTS - 1) {
                        throw new Error(`Failed to acquire worker after ${CONFIG.WORKER_RETRY_ATTEMPTS} attempts: ${error.message}`);
                    }
                    Logger.warn('WorkerManager', `Retry attempt ${attempt + 1} to acquire worker`, { error });
                    await new Promise(resolve => setTimeout(resolve, Math.pow(2, attempt) * 1000));
                }
            }

            workerPool.markWorkerAsBusy(worker);

            const arrayBuffer = await Promise.race([
                chunk.arrayBuffer(),
                new Promise((_, reject) => 
                    setTimeout(() => reject(new Error('ArrayBuffer conversion timeout')), 
                    CONFIG.ARRAY_BUFFER_TIMEOUT)
                )
            ]);

            const result = await new Promise((resolve, reject) => {
                const timeoutId = setTimeout(() => {
                    cleanup();
                    reject(new Error('Worker processing timeout'));
                }, CONFIG.WORKER_PROCESSING_TIMEOUT);

                const onMessage = (e) => {
                    if (e.data.success) {
                        clearTimeout(timeoutId);
                        cleanup();
                        resolve(e.data.data);
                    } else {
                        clearTimeout(timeoutId);
                        cleanup();
                        reject(new Error(e.data.error || 'Unknown worker error'));
                    }
                };

                const onError = (error) => {
                    clearTimeout(timeoutId);
                    cleanup();
                    reject(new Error(`Worker error: ${error.message}`));
                };

                const cleanup = () => {
                    worker.removeEventListener('message', onMessage);
                    worker.removeEventListener('error', onError);
                };

                worker.addEventListener('message', onMessage);
                worker.addEventListener('error', onError);

                try {
                    worker.postMessage({
                        chunk: arrayBuffer,
                        compressionLevel
                    }, [arrayBuffer]);
                } catch (error) {
                    clearTimeout(timeoutId);
                    cleanup();
                    reject(new Error(`Failed to post message to worker: ${error.message}`));
                }
            });

            return result;

        } catch (error) {
            Logger.error('WorkerManager', 'Chunk processing failed', {
                error: error.message,
                stack: error.stack
            });
            throw error;

        } finally {
            if (worker) {
                try {
                    workerPool.markWorkerAsAvailable(worker);
                } catch (error) {
                    Logger.warn('WorkerManager', 'Failed to mark worker as available', { error });
                }
            }
        }
    }

    async function processChunk(chunk, useCompression, compressionLevel, workerPool) {
        Logger.debug('ChunkProcessor', 'Processing chunk', {
            size: `${(chunk.size / (1024 * 1024)).toFixed(2)} MB`,
            compression: useCompression,
            level: compressionLevel
        });

        if (useCompression) {
            return processChunkWithWorker(chunk, compressionLevel, workerPool);
        }

        return new Promise((resolve) => {
            const reader = new FileReader();
            reader.onload = function(e) {
                Logger.trace('ChunkProcessor', 'Chunk processed without compression');
                resolve(new Uint8Array(e.target.result));
            };
            reader.readAsArrayBuffer(chunk);
        });
    }

    async function uploadChunk(chunkIndex, chunkData, formMetadata, csrfToken, progressTracker, useCompression, compressionLevel, workerPool) {
        const chunkFormData = new FormData();
        const chunkNumber = chunkIndex + 1;
        
        try {
            const startTime = Date.now();
            Logger.debug('ChunkUpload', `Starting chunk upload`, {
                chunkNumber,
                chunkStart: chunkData.start,
                chunkEnd: chunkData.end,
                size: `${(chunkData.chunk.size / (1024 * 1024)).toFixed(2)} MB`
            });

            const processedChunk = await processChunk(chunkData.chunk, useCompression, compressionLevel, workerPool);
            
            chunkFormData.append('dataset_file', new Blob([processedChunk], { type: 'application/octet-stream' }));
            chunkFormData.append('chunk_index', chunkIndex);
            chunkFormData.append('chunk_start', chunkData.start);
            chunkFormData.append('chunk_end', chunkData.end);
            chunkFormData.append('is_compressed', useCompression.toString());

            for (let [key, value] of formMetadata.entries()) {
                chunkFormData.append(key, value);
            }

            const signal = uploadState.abortController?.signal;
            const response = await fetch(form.action, {
                method: 'POST',
                headers: {
                    'X-CSRFToken': csrfToken
                },
                body: chunkFormData,
                signal
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const endTime = Date.now();
            const uploadTime = (endTime - startTime) / 1000;
            
            progressTracker.addChunkTime(uploadTime);
            progressTracker.uploadedSize += chunkData.chunk.size;

            Logger.info('ChunkUpload', `Chunk ${chunkNumber} completed successfully`, {
                uploadTime: `${uploadTime.toFixed(2)}s`,
                size: `${(chunkData.chunk.size / (1024 * 1024)).toFixed(2)} MB`,
                start: chunkData.start,
                end: chunkData.end
            });

        } catch (error) {
            if (error.name === 'AbortError') {
                Logger.info('ChunkUpload', 'Upload aborted by user');
                throw error;
            }
            
            Logger.error('ChunkUpload', `Chunk ${chunkNumber} upload failed`, {
                error: error.message,
                stack: error.stack,
                chunkStart: chunkData.start,
                chunkEnd: chunkData.end
            });
            
            throw error;
        }
    }

    async function uploadLargeFile(file) {
        uploadState.isUploading = true;
        uploadState.abortController = new AbortController();
        const chunkSize = parseInt(chunkSizeInput.value) * 1024 * 1024;
        const totalChunks = Math.ceil(file.size / chunkSize);
        const useCompression = compressionCheckbox.checked;
        const useParallel = parallelCheckbox.checked;
        const compressionLevel = compressionLevelSelect.value;
        const parallelCount = useParallel ? parseInt(parallelCountInput.value) : 1;

        const processedChunks = new Set();
        const chunkPreloader = new ChunkPreloader(file, chunkSize, CONFIG.PRELOAD_CHUNKS);
        await chunkPreloader.preloadNextChunks();

        Logger.info('UploadManager', 'Starting file upload', {
            fileName: file.name,
            fileSize: `${(file.size / (1024 * 1024)).toFixed(2)} MB`,
            chunkSize: `${chunkSizeInput.value} MB`,
            totalChunks,
            compression: {
                enabled: useCompression,
                level: compressionLevel
            },
            parallel: {
                enabled: useParallel,
                count: parallelCount
            }
        });

        const progressTracker = new UploadProgress(file.size);
        const csrfToken = form.querySelector('[name=csrfmiddlewaretoken]').value;
        const formMetadata = new FormData(form);
        formMetadata.delete('dataset_file');
        formMetadata.append('total_chunks', totalChunks);
        formMetadata.append('original_filename', file.name);
        formMetadata.append('upload_session_id', generateUUID());

        let activeUploads = [];

        try {
            for (let i = 0; i < totalChunks; i++) {
                if (uploadState.pause) {
                    await new Promise(resolve => {
                        const checkPause = () => {
                            if (!uploadState.pause) {
                                resolve();
                            } else {
                                setTimeout(checkPause, 100);
                            }
                        };
                        checkPause();
                    });
                }

                if (processedChunks.has(i)) {
                    continue;
                }

                const chunkData = chunkPreloader.getChunk(i);
                
                const uploadPromise = (async () => {
                    for (let attempt = 0; attempt < CONFIG.RETRY_ATTEMPTS; attempt++) {
                        try {
                            await uploadChunk(i, chunkData, formMetadata, csrfToken, progressTracker, useCompression, compressionLevel, workerPool);
                            processedChunks.add(i);
                            return;
                        } catch (error) {
                            if (error.name === 'AbortError') throw error;
                            if (attempt === CONFIG.RETRY_ATTEMPTS - 1) throw error;
                            await new Promise(resolve => setTimeout(resolve, Math.pow(2, attempt) * 1000));
                        }
                    }
                })();

                uploadPromise.catch(error => {
                    Logger.error('UploadManager', `Failed to upload chunk ${i}`, { error });
                }).finally(() => {
                    activeUploads = activeUploads.filter(p => p !== uploadPromise);
                });

                activeUploads.push(uploadPromise);

                if (activeUploads.length >= parallelCount) {
                    await Promise.race(activeUploads);
                }

                // Preload next batch of chunks
                await chunkPreloader.preloadNextChunks();
            }

            await Promise.all(activeUploads);
            
            if (processedChunks.size !== totalChunks) {
                throw new Error(`Missing chunks: expected ${totalChunks}, got ${processedChunks.size}`);
            }

            progressTracker.complete(totalChunks);

        } catch (error) {
            Logger.error('UploadManager', 'Upload failed', error);
            progressDisplay.textContent = `Error: ${error.message}`;
        } finally {
            uploadButton.disabled = false;
            uploadState.isUploading = false;
            uploadState.abortController = null;
            chunkPreloader.clear();
            workerPool.terminateAll();
        }
    }

    function generateUUID(){
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            var r = Math.random() * 16 | 0, v = c == 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    }

    const pauseButton = document.createElement('button');
    pauseButton.textContent = 'Pause Upload';
    pauseButton.onclick = () => {
        uploadState.pause = !uploadState.pause;
        pauseButton.textContent = uploadState.pause ? 'Resume Upload' : 'Pause Upload';
    };
    form.appendChild(pauseButton);

    const cancelButton = document.createElement('button');
    cancelButton.textContent = 'Cancel Upload';
    cancelButton.onclick = () => {
        if (uploadState.isUploading && uploadState.abortController) {
            uploadState.abortController.abort();
        }
    };
    form.appendChild(cancelButton);

    if (form) {
        form.addEventListener('submit', async function (event) {
            event.preventDefault();

            const file = fileInput.files[0];
            if (!file) {
                Logger.warn('FormValidation', 'No file selected');
                alert('Please select a file to upload');
                return;
            }

            if (file.size > 1024 * 1024 * 1024 * 1024) {
                Logger.warn('FormValidation', 'File size exceeds limit', {
                    fileSize: `${(file.size / (1024 * 1024 * 1024)).toFixed(2)} GB`,
                    limit: '1 TB'
                });
                alert('File size exceeds maximum upload limit');
                return;
            }

            uploadButton.disabled = true;
            await uploadLargeFile(file);
        });
    }
});