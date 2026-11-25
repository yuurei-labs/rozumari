#!/usr/bin/env bun

import { tegami } from 'tegami'
import { runCli } from 'tegami/cli'
import { github } from 'tegami/plugins/github'

const paper = tegami({
  npm: {
    client: 'bun',
    updateLockFile: true,
    onBreakPeerDep: 'set',
  },

  plugins: [
    github({
      repo: 'yuurei-labs/rozumari',
      versionPr: { base: 'dev' },
    }),
  ],

  ignore: ['docs'],
})

await runCli(paper)
