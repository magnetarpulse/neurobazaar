<script setup>
console.log("This is my Vue.js code for the client side of the application.");
import { inject, ref, watch } from "vue"

console.log('Before wsClient injection'); 
const wsClient = inject("wsClient");
console.log('After wsClient injection:', wsClient); 

const bins = ref(5);

const file_input = ref(null);

const column_options = ref([]);

const selected_column = ref(null);

const viewId = ref(null);

// This would be need to be updated to interactively and automatically update the render_window, without the need for user_interaction, such as clicking on the application (render_window)
wsClient.getRemote().Trame.getState().then((s) => {
    viewId.value = s.state.viewId;
    // Initial load of column_options
    column_options.value = s.state.column_options || [];
    //console.log("Initial column options from server state:", column_options.value);
    bins.value = s.state.bins || 5;
    console.log("Initial bins from server state:", bins.value);
});

watch(
    bins,
    async (newVal, oldVal) => {
        console.log("bins changed from", oldVal, "to", newVal);
        const s = await wsClient.getRemote().Trame.getState();
        if (s.state.bins !== newVal) {
            console.log("Updating state...");
            await wsClient.getRemote().Trame.updateState([
                { key: "bins", value: newVal }
            ]);
            console.log("State updated with new bins value:", newVal);
        } else {
            console.log("No need to update state. Bins value is the same.");
        }
    },
    { deep: true }
);

watch(
    file_input,
    async (value) => {
        console.log("File input changed:", value);
        console.log("Sending file to server...");
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
    async (newVal, oldVal) => {
        //console.log("column_options changed from", oldVal, "to", newVal);
        const s = await wsClient.getRemote().Trame.getState();
        //console.log("Resolved new state:", s);
        column_options.value = s.state.column_options || [];
        //console.log("Updated column options from server state:", column_options.value);
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
    height: 50vh;
    width: 50vw;
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