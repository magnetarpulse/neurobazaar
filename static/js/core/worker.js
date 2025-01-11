importScripts('https://cdn.jsdelivr.net/npm/fflate@0.8.2/umd/index.min.js');

self.onmessage = async function (e) {
    const { mode, data } = e.data;

    try {
        if (mode === 'batch') {
            const { chunks, compressionLevel } = data;
            const results = [];
            for (const chunk of chunks) {
                const compressed = await compressChunk(chunk, compressionLevel);
                results.push(compressed);
            }
            self.postMessage({ success: true, data: results });
        } else if (mode === 'single') {
            const { chunk, compressionLevel } = data;
            const compressed = await compressChunk(chunk, compressionLevel);
            self.postMessage({ success: true, data: compressed });
        } else {
            throw new Error('Invalid mode specified.');
        }
    } catch (error) {
        self.postMessage({ success: false, error: error.message });
    }
};

function compressChunk(chunk, compressionLevel) {
    return new Promise((resolve, reject) => {
        const gzs = new fflate.AsyncGzip({ level: parseInt(compressionLevel) });
        let compressedChunks = [];
        let totalSize = 0;

        gzs.ondata = (err, chunk, final) => {
            if (err) {
                reject(err);
                return;
            }

            compressedChunks.push(chunk);
            totalSize += chunk.length;

            if (final) {
                const compressedData = new Uint8Array(totalSize);
                let offset = 0;
                for (let chunk of compressedChunks) {
                    compressedData.set(chunk, offset);
                    offset += chunk.length;
                }
                resolve(compressedData);
            }
        };

        gzs.push(new Uint8Array(chunk), true);
    });
}