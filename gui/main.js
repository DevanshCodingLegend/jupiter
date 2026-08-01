const { app, BrowserWindow, ipcMain, screen } = require('electron')
const path = require('path')
const http = require('http')

let mainWindow
let isVisible = true

function createWindow() {
  const { width, height } = screen.getPrimaryDisplay().workAreaSize

  mainWindow = new BrowserWindow({
    width: width,
    height: height,
    x: 0,
    y: 0,
    frame: false,
    transparent: true,
    alwaysOnTop: true,
    skipTaskbar: false,
    resizable: true,
    webPreferences: {
      nodeIntegration: true,
      contextIsolation: false,
      preload: path.join(__dirname, 'preload.js')
    }
  })

  mainWindow.loadFile('jupiter_gui.html')
  mainWindow.maximize()

  setInterval(pollState, 500)
}

function pollState() {
  const options = {
    hostname: 'localhost',
    port: 5000,
    path: '/state',
    method: 'GET',
    timeout: 400
  }

  const req = http.request(options, (res) => {
    let data = ''
    res.on('data', chunk => data += chunk)
    res.on('end', () => {
      try {
        const state = JSON.parse(data)
        if (mainWindow && !mainWindow.isDestroyed()) {
          mainWindow.webContents.send('state-update', state)
          
          // Smart visibility
          const active = state.listening || state.thinking || 
                         state.jupiter_speaking || state.user_text || 
                         state.response_text
          
          if (active && !isVisible) {
            mainWindow.showInactive()
            isVisible = true
          }
        }
      } catch(e) {}
    })
  })

  req.on('error', () => {})
  req.on('timeout', () => req.destroy())
  req.end()
}

ipcMain.on('hide-window', () => {
  mainWindow.hide()
  isVisible = false
})

ipcMain.on('show-window', () => {
  mainWindow.show()
  isVisible = true
})

app.whenReady().then(createWindow)
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})