<script setup>
console.log("This is my Vue.js code for the client side of the application.");
import { inject, ref, watch } from "vue"

console.log('Before wsClient injection'); 
const wsClient = inject("wsClient");
console.log('After wsClient injection:', wsClient); 

const bins = ref(5);

const file_input = ref(null);

//const selected_option = ref([]);

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

/*watch(
    bins,
    (value) => {
        wsClient.getRemote().Trame.updateState([
            { key: "bins", value }
        ]);
    }
)*/

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

// TODO: Someone else, who is more knowledgeable and experienced in JavaScript and or Vue.js should review the response from Copilot, and make sure what copilot is saying is correct.
// If copilot's response is incorrect, please tell me (Huy Nguyen) and provide the correct response, so that I can update the server-side code accordingly.
// This is important because the latency between the client and server when sending the file is higher and very noticable, and it is important to reduce this latency as much as possible.
// The reason for the increased latency is because the file is not being sent as a File object, but instead as a base64 encoded string, which is not the most efficient way to send files.
// Because it takes more resouces, time and is a more computationally intensive process to encode and decode the file, in comparison to sending the file as a File object.
// This is why it is important to send the file as a File object, then there won't be any need to encode or decode the file, and the file can be directly sent and received as a File object.
// Unfortunately, I am not experienced enough in JavaScript/Vue.js/web-development and do not have enough time to review if what ChatGPT is saying is true or not, so I am asking for someone else to review this code and provide the correct response.


// THIS IS THE RESPONSE FROM COPILOT:
// This is likely because the File object from the client-side cannot be serialized directly and sent over the network.
// In JavaScript, File objects represent data from the file system and can't be directly serialized or sent over a network connection. 
// Instead, you typically need to read the file into memory and send the file data as a string or binary data.
// Here's a potential solution: Instead of sending the File object directly, you could send the file's metadata (like the name and size) and a Blob object containing the file data.

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

// TODO: Biggest issue is that the selecte_column is not being updated.
// RESOLVED: The issue was that the watch function was not being triggered, this was due to the fact that the column_options was not getting the state from the server, instead it was only updating the state (updateState).
// IMPORTANT: For the client to be able to recieve information from the server, we need to use the getState instead of the updateState, this is because the updateState is only used to send information to the server, not to recieve it.
// I will be leaving this TODO here for future reference, in case I or anyone else need to remember how recieve information from the server.

/*watch(
    column_options,
    (value) => {
        console.log("Column options received from server:", value);
        selected_column.value = value[0] || null;  // Automatically select the first option
    }
)*/

// TODO: This watch function is not working, this is meant to watch the column_options but it is failing miserably, no console logs are being printed, not sure why.
// TODO: TO DELETE THIS, but I will delete it later (in production), for now I will leave it here for reference in case for some reason I need it.
/*
watch(
    () => {
        console.log("Checking server state...");
        return wsClient.getRemote().Trame.getState();
    },
    async (newState, oldState) => {
        console.log("Server state has changed.");
        console.log("Old state:", oldState);
        console.log("New state:", newState);
        const s = await newState;
        console.log("Resolved new state:", s);
        column_options.value = s.state.column_options || [];
        console.log("Updated column options from server state:", column_options.value);
    },
    { deep: true } // This ensures that the watch function is triggered even when nested properties change
)*/

// OMG THIS WORKS, RESOLVED THE ISSUE!!! Took close to eight hours to figure this entire client-side out, with at least 5-6 hours spent on this issue alone.
// I hate JavaScript lol. This language is so weird, but I am starting to get the hang of it (praying so at least).
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