import { readFileSync, statSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { join } from 'node:path'

const DIST_DIR = fileURLToPath(new URL('../dist/', import.meta.url))
const DIST_ASSETS_DIR = join(DIST_DIR, 'assets')
const DIST_INDEX_HTML = join(DIST_DIR, 'index.html')
const MAX_JS_CHUNK_SIZE = 500 * 1024

const html = readFileSync(DIST_INDEX_HTML, 'utf8')
const assetRefs = [...html.matchAll(/\/assets\/([^"'?#]+\.js)/g)].map((match) => match[1])
const visited = new Set()
const queue = [...assetRefs]

while (queue.length > 0) {
  const fileName = queue.pop()
  if (!fileName || visited.has(fileName)) {
    continue
  }

  visited.add(fileName)

  const content = readFileSync(join(DIST_ASSETS_DIR, fileName), 'utf8')
  const importRefs = [
    ...content.matchAll(/(?:from|import)\s*\(?["']\.\/([^"'?#]+\.js)["']\)?/g),
    ...content.matchAll(/assets\/([^"'?#]+\.js)/g),
  ].map((match) => match[1])

  for (const ref of importRefs) {
    if (!visited.has(ref)) {
      queue.push(ref)
    }
  }
}

const oversizedChunks = [...visited]
  .map((fileName) => ({
    fileName,
    size: statSync(join(DIST_ASSETS_DIR, fileName)).size,
  }))
  .filter((entry) => entry.size > MAX_JS_CHUNK_SIZE)

if (oversizedChunks.length > 0) {
  console.error('Oversized JS chunks found:')
  for (const chunk of oversizedChunks) {
    console.error(`- ${chunk.fileName}: ${chunk.size} bytes`)
  }
  process.exit(1)
}

console.log('All active JS chunks are within the 500 KB limit.')
