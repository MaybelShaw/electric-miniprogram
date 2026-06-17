const fs = require('fs')
const path = require('path')

const frontendRoot = path.resolve(__dirname, '..')
const distPath = path.resolve(frontendRoot, 'dist')

if (!distPath.startsWith(frontendRoot + path.sep)) {
  throw new Error(`Refusing to remove unexpected path: ${distPath}`)
}

try {
  fs.rmSync(distPath, { recursive: true, force: true, maxRetries: 3, retryDelay: 200 })
} catch (error) {
  if (error && (error.code === 'EPERM' || error.code === 'EBUSY')) {
    console.warn(`[clean:dist] skipped because dist is locked: ${distPath}`)
    console.warn('[clean:dist] close WeChat DevTools or stop the old watch process if stale page errors continue.')
  } else {
    throw error
  }
}
