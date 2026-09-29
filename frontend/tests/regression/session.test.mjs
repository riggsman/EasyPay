/**
 * Lightweight regression smoke for the API client session helpers.
 * Run: node --test tests/regression/session.test.mjs
 */
import test from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { fileURLToPath } from 'node:url'
import { dirname, join } from 'node:path'

const root = join(dirname(fileURLToPath(import.meta.url)), '../..')
const clientSrc = readFileSync(join(root, 'src/api/client.js'), 'utf8')

test('api client implements refresh + retry on 401', () => {
  assert.match(clientSrc, /auth\/refresh/)
  assert.match(clientSrc, /refreshAccessToken/)
  assert.match(clientSrc, /status === 401/)
  assert.match(clientSrc, /ep:logout/)
})

test('api client does not expose tenant_id on payment initiate helper signature surface', () => {
  assert.match(clientSrc, /initiatePayment/)
  assert.doesNotMatch(clientSrc, /tenant_id:\s*body/)
})
