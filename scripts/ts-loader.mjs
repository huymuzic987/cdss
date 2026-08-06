import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath, pathToFileURL } from 'node:url'

const extensions = ['.ts', '.tsx', '.js', '.mjs', '.json']

export async function resolve(specifier, context, nextResolve) {
  if (specifier.startsWith('.') && !path.extname(specifier)) {
    const parent = context.parentURL ? path.dirname(fileURLToPath(context.parentURL)) : process.cwd()
    for (const extension of extensions) {
      const candidate = path.resolve(parent, `${specifier}${extension}`)
      if (fs.existsSync(candidate)) return nextResolve(pathToFileURL(candidate).href, context)
    }
  }
  return nextResolve(specifier, context)
}

export async function load(url, context, nextLoad) {
  if (url.endsWith('.json')) {
    const value = fs.readFileSync(fileURLToPath(url), 'utf8')
    return { format: 'module', shortCircuit: true, source: `export default ${value}` }
  }
  return nextLoad(url, context)
}
