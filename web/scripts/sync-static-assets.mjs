import { cp, rm } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { fileURLToPath } from 'node:url'

const scriptDir = dirname(fileURLToPath(import.meta.url))
const webRoot = resolve(scriptDir, '..')
const repoRoot = resolve(webRoot, '..')

const copies = [
  ['assets/images', 'public/assets/images'],
  ['data/locales', 'public/data/locales'],
  ['data/difficulty', 'public/data/difficulty'],
]

for (const [source, destination] of copies) {
  const sourcePath = resolve(repoRoot, source)
  const destinationPath = resolve(webRoot, destination)
  await rm(destinationPath, { recursive: true, force: true })
  await cp(sourcePath, destinationPath, {
    recursive: true,
    filter: (path) => !path.endsWith('.DS_Store'),
  })
}

console.log('Synced Hangperson static assets and data.')
