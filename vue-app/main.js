import { createApp } from 'vue'
console.log('vue imported');

import {createVuetify} from 'vuetify' // Importing Vuetify
import 'vuetify/dist/vuetify.min.css' // Import Vuetify CSS
console.log('vuetify imported');

import wslink from "./wslink";
console.log('wslink imported');

import { install } from "vue-vtk-js";
console.log('vue-vtk-js imported');

import App from './EditedMyApp.vue'
console.log('EditMyApp.vue imported');

const client = wslink.createClient();
console.log('Client created:', client);
console.log('Client details:', JSON.stringify(client, null, 2)); 
console.log('Attempting to connect to server...');

const config = {
    application: 'histogram',
    sessionURL: 'ws://localhost:8080/ws',
  };

client.connect(config).then(() => {
    console.log('Connected to server');
    debugger;
    console.log('Connection details:', JSON.stringify(client.connection, null, 2)); // Log connection details
    const vueApp = createApp(App);
    const vuetify = createVuetify();
    vueApp.use(vuetify); 
    install(vueApp);
    vueApp.provide("wsClient", client);
    vueApp.mount('#app')
}).catch((error) => {
    console.error('Failed to connect:', error);
});