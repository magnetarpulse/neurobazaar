import { createApp } from 'vue'

import {createVuetify} from 'vuetify' 
import 'vuetify/dist/vuetify.min.css' 

import wslink from "./wslink";

import { install } from "vue-vtk-js";

import App from './VueClient.vue'

const client = wslink.createClient();

const config = {
    application: 'histogram',
    sessionURL: 'ws://localhost:8080/ws',
  };

client.connect(config).then(() => {
    const vueApp = createApp(App);
    const vuetify = createVuetify();
    vueApp.use(vuetify); 
    install(vueApp);
    vueApp.provide("wsClient", client);
    vueApp.mount('#app')
}).catch((error) => {
    console.error('Failed to connect:', error);
});