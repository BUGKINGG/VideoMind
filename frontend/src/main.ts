import { createApp } from 'vue'
import {createPinia} from "pinia";
import './style.css'
import router from './router'
import piniaPluginPersistedstate from 'pinia-plugin-persistedstate'
import App from './App.vue'
import './assets/main.css'

const pinia = createPinia()
pinia.use(piniaPluginPersistedstate)

createApp(App).use(router).use(pinia).mount('#app')
