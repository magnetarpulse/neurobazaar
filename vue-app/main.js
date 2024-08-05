// wslink.js

// Imports
import vtkURLExtract from "@kitware/vtk.js/Common/Core/URLExtract";
import SmartConnect from "wslink/src/SmartConnect";
import vtkWSLinkClient from "@kitware/vtk.js/IO/Core/WSLinkClient";
import { createApp } from 'vue';
import { createVuetify } from 'vuetify'; // Importing Vuetify
import 'vuetify/dist/vuetify.min.css'; // Import Vuetify CSS
import { install } from "vue-vtk-js";
import App from './MyApp.vue';

// Protocol definition (trame.js content)
const Trame = (session) => ({
  lifeCycleUpdate(phaseName) {
    return session.call("trame.lifecycle.update", [phaseName]);
  },
  sendError(message) {
    return session.call("trame.error.client", [message]);
  },
  getState() {
    return session.call("trame.state.get", []);
  },
  trigger(name, args = [], kwargs = {}) {
    return session.call("trame.trigger", [name, args, kwargs]);
  },
  updateState(changes) {
    return session.call("trame.state.update", [changes]);
  },
  subscribeToStateUpdate(callback) {
    return session.subscribe("trame.state.topic", callback);
  },
  subscribeToActions(callback) {
    return session.subscribe("trame.actions.topic", callback);
  },
  unsubscribe(subscription) {
    return session.unsubscribe(subscription);
  },
});

// Protocols (index.js content)
const protocols = {
  Trame,
};

// wslink client setup (index.js content)
vtkWSLinkClient.setSmartConnectClass(SmartConnect);

const WS_PROTOCOL = {
  "http:": "ws:",
  "https:": "wss:",
  "ws:": "ws:",
  "wss:": "wss:",
};

const NOT_BUSY_LIST = [
  "unsubscribe",
  "subscribeToViewChange",
  "subscribeToStateUpdate",
  "subscribeToActions",
  "subscribeToViewChange",
];

function configDecorator(config) {
  const outputConfig = { ...config };

  // Process sessionURL
  if (outputConfig.sessionURL) {
    let sessionURL = outputConfig.sessionURL.toLowerCase();
    const httpURL = window.location;

    // handle protocol mapping http(s) => ws(s)
    if (sessionURL.includes("use_")) {
      const wsURL = new URL(sessionURL);
      wsURL.protocol = WS_PROTOCOL[httpURL.protocol];
      sessionURL = wsURL.toString();
    }

    // handle variable replacement
    const use_mapping = {
      use_hostname: httpURL.hostname,
      use_host: httpURL.host,
    };
    for (const [key, value] of Object.entries(use_mapping)) {
      sessionURL = sessionURL.replaceAll(key, value);
    }

    // update config
    outputConfig.sessionURL = sessionURL;
  }

  // Extract app-name from html
  outputConfig.application =
    document.querySelector("html").dataset.appName || outputConfig.application;

  const sessionManagerURL =
    document.querySelector("html").dataset.sessionManagerUrl ||
    outputConfig.sessionManagerURL;
  if (sessionManagerURL) {
    outputConfig.sessionManagerURL = sessionManagerURL;
  }

  // Process arguments from URL
  if (outputConfig.useUrl) {
    return {
      ...outputConfig,
      ...vtkURLExtract.extractURLParameters(),
    };
  }
  return outputConfig;
}

function createClient() {
  return vtkWSLinkClient.newInstance({
    protocols,
    configDecorator,
    notBusyList: NOT_BUSY_LIST,
  });
}

// Vue application setup and wslink client connection
const client = createClient();

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
  vueApp.mount('#app');
}).catch((error) => {
  console.error('Failed to connect:', error);
});

export default {
  configDecorator,
  createClient,
};
