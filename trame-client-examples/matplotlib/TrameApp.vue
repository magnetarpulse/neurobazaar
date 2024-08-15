<script setup>
import { inject, ref, watch } from "vue"
import * as mpld3 from "mpld3"; 

const wsClient = inject("wsClient");
const bins = ref(5);
const file_input = ref(null);
const column_options = ref([]);
const selected_column = ref(null);
const viewId = ref(null);

const figureData = ref(null);

wsClient.getRemote().Trame.getState().then((s) => {
    viewId.value = s.state.viewId;
    column_options.value = s.state.column_options || [];
    bins.value = s.state.bins || 5;
    figureData.value = s.state.figure_data;
});

watch(
    figureData,
    (data) => {
        const container = document.getElementById("histogram_matplotlib");

        if (data && container) {
            container.innerHTML = '';

            mpld3.draw_figure("histogram_matplotlib", data);
        } else {
            console.warn('Cannot draw figure: either data is missing or element does not exist');
        }
    },
    { immediate: true }
);

watch(
    bins,
    async (newVal, oldVal) => {
        const s = await wsClient.getRemote().Trame.getState();
        if (s.state.bins !== newVal) {
            await wsClient.getRemote().Trame.updateState([
                { key: "bins", value: newVal }
            ]);
        }
        figureData.value = await wsClient.getRemote().Trame.getState().then(s => s.state.figure_data);
    },
    { immediate: true }
);

watch(
    file_input,
    async (value) => {
        if (value) {
            const fileData = await value.arrayBuffer();
            const base64Data = btoa(new Uint8Array(fileData).reduce((data, byte) => data + String.fromCharCode(byte), ''));
            wsClient.getRemote().Trame.updateState([
                { key: "file_input", value: { name: value.name, size: value.size, content: base64Data } }
            ]);
        }
    }
)

watch(
    () => column_options,
    async () => {
        const s = await wsClient.getRemote().Trame.getState();
        column_options.value = s.state.column_options || [];
    },
    { deep: true }
)

watch(
    selected_column,
    (value) => {
        wsClient.getRemote().Trame.updateState([
            { key: "selected_column", value }
        ]);
    }
)
</script>

<template>
    <div id="app">
        <div id="histogram_matplotlib"></div>
        <vtk-remote-view
            v-if="viewId"
            :viewId="viewId"
            :wsClient="wsClient"
        />
        <div class="select-file-container">
            <v-slider
                v-model.number="bins"
                min="1"
                max="100"
                step="1"
                label="Number of Bins"
                class="slider"
            />
            <v-select
                v-model="selected_column"
                :items="column_options"
                label="Select Column"
                class="select"
            />
            <v-file-input
                v-model="file_input"
                label="Upload CSV"
                accept=".csv"
                class="file-input"
            />
        </div>
    </div>
</template>

<style scoped>
#app {
    display: flex;
    flex-direction: column-reverse;
    justify-content: flex-start;
    align-items: center;
    height: 100vh;
    width: 100vw;
    margin: auto;
    position: relative;
    bottom: 0;
    left: 0;
    right: 0;
}

.select-file-container {
    position: absolute;
    top: 10px;
    right: 0px;
    left: 0px;
    display: flex;
    flex-direction: row-reverse;
}

.file-input {
    margin-left: 20px;
}

.select {
    margin-left: 10px;
}

.slider {
    margin-left: 10px;
}
</style>