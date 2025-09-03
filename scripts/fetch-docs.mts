#!/usr/bin/env node

/**
 * Documentation fetch script - Fetch and integrate docs from various repositories
 * Usage: node --loader ts-node/esm scripts/fetch-docs.mts [--force]
 */

import { exec } from 'child_process'
import { promisify } from 'util'
import * as fs from 'fs/promises'
import * as path from 'path'
import repos from '../.vitepress/config/repos.mts'

const execAsync = promisify(exec)

// Configuration
const TEMP_DIR = path.resolve(process.cwd(), './temp')
const DOCS_DIR = path.resolve(process.cwd(), './docs')

// Parse arguments
const FORCE = process.argv.includes('--force')

/**
 * Execute shell command and return output
 */
async function runCommand(command: string, cwd?: string): Promise<string> {
  try {
    const { stdout } = await execAsync(command, { cwd })
    return stdout.trim()
  } catch (error: any) {
    console.error(`Command execution failed: ${command}`)
    console.error(error.message)
    return ''
  }
}

/**
 * Ensure directory exists
 */
async function ensureDir(dir: string): Promise<void> {
  try {
    await fs.mkdir(dir, { recursive: true })
  } catch (error) {
    // Directory already exists, ignore error
  }
}

/**
 * Clean directory but preserve directory structure
 */
async function cleanDir(dir: string): Promise<void> {
  try {
    const files = await fs.readdir(dir)

    for (const file of files) {
      const filePath = path.join(dir, file)
      const stat = await fs.stat(filePath)

      if (stat.isDirectory()) {
        await fs.rm(filePath, { recursive: true, force: true })
      } else {
        await fs.unlink(filePath)
      }
    }
  } catch (error: any) {
    if (error.code !== 'ENOENT') {
      throw error
    }
  }
}

/**
 * Use sparse checkout to fetch specific directory with retry mechanism
 */
async function sparseCheckout(repo: string, branch: string, sourceDir: string, repoTempDir: string): Promise<boolean> {
  const MAX_RETRIES = 3
  const RETRY_DELAY = 3000 // 3 second delay

  for (let retryCount = 0; retryCount <= MAX_RETRIES; retryCount++) {
    try {
      if (retryCount > 0) {
        console.log(`Retrying ${retryCount} time(s) to fetch repository ${repo}...`)
        // Delete potentially partially cloned directory before retry
        if (await dirExists(repoTempDir)) {
          await fs.rm(repoTempDir, { recursive: true, force: true })
        }
        // Delay for a period before retrying
        await new Promise((resolve) => setTimeout(resolve, RETRY_DELAY))
      }

      if (!(await dirExists(repoTempDir))) {
        // Clone repository
        console.log(`Cloning repository ${repo}...`)
        const cloneResult = await runCommand(
          `git clone --no-checkout --depth 1 -b ${branch} https://github.com/${repo}.git ${repoTempDir}`
        )

        // If clone is successful, check if directory is created
        if (!(await dirExists(repoTempDir))) {
          throw new Error(`Repository clone failed, directory not created: ${repoTempDir}`)
        }

        // Configure sparse checkout
        // Don't use --cone mode to ensure recursive fetching of subdirectories
        await runCommand('git sparse-checkout init', repoTempDir)

        // Prepare sparse-checkout configuration, ensure recursive fetching of all subdirectories and files
        let checkoutPattern
        if (!sourceDir || sourceDir === '.') {
          // If source directory is empty or root directory, fetch entire repository
          checkoutPattern = '*'
        } else {
          // Use wildcards to ensure fetching all subdirectories and files under specified directory
          checkoutPattern = `${sourceDir}/**/*`
        }

        // Ensure sparse-checkout config file directory exists
        const sparseDir = path.join(repoTempDir, '.git', 'info')
        await fs.mkdir(sparseDir, { recursive: true })

        // Write sparse-checkout configuration file
        const sparsePath = path.join(sparseDir, 'sparse-checkout')
        await fs.writeFile(sparsePath, checkoutPattern)

        console.log(`Configure sparse checkout: ${checkoutPattern}`)

        // Checkout specified branch
        await runCommand(`git checkout ${branch}`, repoTempDir)
      } else {
        // Update existing repository
        console.log(`Updating repository ${repo}...`)
        await runCommand(`git fetch origin ${branch}`, repoTempDir)
        await runCommand(`git checkout ${branch}`, repoTempDir)
        await runCommand(`git pull origin ${branch}`, repoTempDir)
      }

      return true
    } catch (error) {
      console.error(`Failed to fetch repository ${repo} attempt ${retryCount + 1}/${MAX_RETRIES + 1}`)
      console.error(error)

      // If maximum retry attempts reached, return failure
      if (retryCount === MAX_RETRIES) {
        console.error(`Failed to fetch repository ${repo} after ${MAX_RETRIES + 1} attempts`)
        return false
      }
      // Otherwise continue to next retry
    }
  }

  return false
}

/**
 * Check if directory exists
 */
async function dirExists(dir: string): Promise<boolean> {
  try {
    const stat = await fs.stat(dir)
    return stat.isDirectory()
  } catch (error) {
    return false
  }
}

/**
 * Copy documents to target directory
 */
async function copyDocs(sourceDir: string, targetDir: string): Promise<boolean> {
  try {
    // Ensure target directory exists
    await ensureDir(targetDir)

    // Clean target directory
    await cleanDir(targetDir)

    // Check if source directory exists
    if (!(await dirExists(sourceDir))) {
      console.error(`Error: Source directory does not exist: ${sourceDir}`)
      console.error(`Please modify the source field of the corresponding repository in repos.mts file`)
      return false
    }

    // Copy files
    const files = await fs.readdir(sourceDir)

    for (const file of files) {
      const sourceFile = path.join(sourceDir, file)
      const targetFile = path.join(targetDir, file)
      const stat = await fs.stat(sourceFile)

      if (stat.isDirectory()) {
        await fs.cp(sourceFile, targetFile, { recursive: true })
      } else {
        await fs.copyFile(sourceFile, targetFile)
      }
    }

    return true
  } catch (error) {
    console.error(`Failed to copy documents: ${sourceDir} -> ${targetDir}`)
    console.error(error)
    return false
  }
}

/**
 * Clean up temporary directory
 */
async function cleanupTempDir(): Promise<void> {
  if (FORCE) {
    console.log('Cleaning up temporary directory...')
    await fs.rm(TEMP_DIR, { recursive: true, force: true }).catch(() => {})
  }
}

/**
 * Main function
 */
async function main() {
  console.log('Starting to fetch documents from repositories...')

  // Ensure directories exist
  await ensureDir(TEMP_DIR)
  await ensureDir(DOCS_DIR)

  // Process each repository
  for (let i = 0; i < repos.length; i++) {
    const { repo, target, source, branch } = repos[i]

    console.log(`[${i + 1}/${repos.length}] Processing ${repo} -> ${target}`)

    // Set target directory
    const targetDir = path.join(DOCS_DIR, target)

    // If target directory exists and not forcing update, skip
    if ((await dirExists(targetDir)) && !FORCE) {
      console.log(`Skipping ${targetDir} (already exists, use --force to force update)`)
      continue
    }

    // Repository temporary directory
    const repoName = repo.split('/').pop() || ''
    const repoTempDir = path.join(TEMP_DIR, repoName)

    // Use sparse checkout to fetch specific directory
    if (await sparseCheckout(repo, branch, source, repoTempDir)) {
      // Copy documents to target directory
      const sourceDir = path.join(repoTempDir, source)
      if (await copyDocs(sourceDir, targetDir)) {
        console.log(`Successfully copied documents from ${repo} to ${targetDir}`)
      }
    }
  }

  // Clean up temporary directory
  await cleanupTempDir()

  console.log('Document fetching completed!')
}

// Execute main function
main().catch((error) => {
  console.error('Document fetching failed')
  console.error(error)
  process.exit(1)
})
