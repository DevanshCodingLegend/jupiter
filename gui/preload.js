const { ipcRenderer } = require('electron')

window.jupiterBridge = {
  onStateUpdate: (callback) => {
    ipcRenderer.on('state-update', (event, state) => callback(state))
  },
  hide: () => ipcRenderer.send('hide-window'),
  show: () => ipcRenderer.send('show-window'),
}