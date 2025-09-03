#!/usr/bin/env node

/**
 * 文档获取脚本 - 从各个仓库获取并整合文档
 * 使用方法: node --loader ts-node/esm scripts/fetch-docs.mts [--force]
 */

import { exec } from 'child_process'
import { promisify } from 'util'
import * as fs from 'fs/promises'
import * as path from 'path'
import repos from '../.vitepress/config/repos.mts'

const execAsync = promisify(exec)

// 配置
const TEMP_DIR = path.resolve(process.cwd(), './temp')
const DOCS_DIR = path.resolve(process.cwd(), './docs')

// 解析参数
const FORCE = process.argv.includes('--force')

/**
 * 执行 shell 命令并返回输出
 */
async function runCommand(command: string, cwd?: string): Promise<string> {
  try {
    const { stdout } = await execAsync(command, { cwd })
    return stdout.trim()
  } catch (error: any) {
    console.error(`命令执行失败: ${command}`)
    console.error(error.message)
    return ''
  }
}

/**
 * 确保目录存在
 */
async function ensureDir(dir: string): Promise<void> {
  try {
    await fs.mkdir(dir, { recursive: true })
  } catch (error) {
    // 目录已存在，忽略错误
  }
}

/**
 * 清空目录但保留目录结构
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
 * 使用 sparse checkout 获取特定目录，带有重试机制
 */
async function sparseCheckout(repo: string, branch: string, sourceDir: string, repoTempDir: string): Promise<boolean> {
  const MAX_RETRIES = 3
  const RETRY_DELAY = 3000 // 3秒延迟

  for (let retryCount = 0; retryCount <= MAX_RETRIES; retryCount++) {
    try {
      if (retryCount > 0) {
        console.log(`重试第 ${retryCount} 次获取仓库 ${repo}...`)
        // 重试前删除可能已经部分克隆的目录
        if (await dirExists(repoTempDir)) {
          await fs.rm(repoTempDir, { recursive: true, force: true })
        }
        // 延迟一段时间后再重试
        await new Promise((resolve) => setTimeout(resolve, RETRY_DELAY))
      }

      if (!(await dirExists(repoTempDir))) {
        // 克隆仓库
        console.log(`克隆仓库 ${repo}...`)
        const cloneResult = await runCommand(
          `git clone --no-checkout --depth 1 -b ${branch} https://github.com/${repo}.git ${repoTempDir}`
        )

        // 如果克隆成功，检查目录是否创建
        if (!(await dirExists(repoTempDir))) {
          throw new Error(`仓库克隆失败，未创建目录: ${repoTempDir}`)
        }

        // 配置 sparse checkout
        // 不使用 --cone 模式，以确保能够递归获取子目录
        await runCommand('git sparse-checkout init', repoTempDir)

        // 准备 sparse-checkout 配置，确保递归获取所有子目录和文件
        let checkoutPattern
        if (!sourceDir || sourceDir === '.') {
          // 如果源目录为空或为根目录，获取整个仓库
          checkoutPattern = '*'
        } else {
          // 使用通配符确保获取指定目录下的所有子目录和文件
          checkoutPattern = `${sourceDir}/**/*`
        }

        // 确保 sparse-checkout 配置文件所在目录存在
        const sparseDir = path.join(repoTempDir, '.git', 'info')
        await fs.mkdir(sparseDir, { recursive: true })

        // 写入 sparse-checkout 配置文件
        const sparsePath = path.join(sparseDir, 'sparse-checkout')
        await fs.writeFile(sparsePath, checkoutPattern)

        console.log(`配置 sparse checkout: ${checkoutPattern}`)

        // 检出指定分支
        await runCommand(`git checkout ${branch}`, repoTempDir)
      } else {
        // 更新现有的仓库
        console.log(`更新仓库 ${repo}...`)
        await runCommand(`git fetch origin ${branch}`, repoTempDir)
        await runCommand(`git checkout ${branch}`, repoTempDir)
        await runCommand(`git pull origin ${branch}`, repoTempDir)
      }

      return true
    } catch (error) {
      console.error(`获取仓库 ${repo} 尝试 ${retryCount + 1}/${MAX_RETRIES + 1} 失败`)
      console.error(error)

      // 如果已经达到最大重试次数，返回失败
      if (retryCount === MAX_RETRIES) {
        console.error(`在 ${MAX_RETRIES + 1} 次尝试后，获取仓库 ${repo} 失败`)
        return false
      }
      // 否则继续下一次重试
    }
  }

  return false
}

/**
 * 检查目录是否存在
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
 * 复制文档到目标目录
 */
async function copyDocs(sourceDir: string, targetDir: string): Promise<boolean> {
  try {
    // 确保目标目录存在
    await ensureDir(targetDir)

    // 清空目标目录
    await cleanDir(targetDir)

    // 检查源目录是否存在
    if (!(await dirExists(sourceDir))) {
      console.error(`错误：源目录不存在：${sourceDir}`)
      console.error(`请修改 repos.mts 文件中相应仓库的 source 字段`)
      return false
    }

    // 复制文件
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
    console.error(`复制文档失败: ${sourceDir} -> ${targetDir}`)
    console.error(error)
    return false
  }
}

/**
 * 清理临时目录
 */
async function cleanupTempDir(): Promise<void> {
  if (FORCE) {
    console.log('清理临时目录...')
    await fs.rm(TEMP_DIR, { recursive: true, force: true }).catch(() => {})
  }
}

/**
 * 主函数
 */
async function main() {
  console.log('开始从仓库获取文档...')

  // 确保目录存在
  await ensureDir(TEMP_DIR)
  await ensureDir(DOCS_DIR)

  // 处理每个仓库
  for (let i = 0; i < repos.length; i++) {
    const { repo, target, source, branch } = repos[i]

    console.log(`[${i + 1}/${repos.length}] 处理 ${repo} -> ${target}`)

    // 设置目标目录
    const targetDir = path.join(DOCS_DIR, target)

    // 如果目标目录已存在且不强制更新，则跳过
    if ((await dirExists(targetDir)) && !FORCE) {
      console.log(`跳过 ${targetDir} (已存在，使用 --force 强制更新)`)
      continue
    }

    // 仓库临时目录
    const repoName = repo.split('/').pop() || ''
    const repoTempDir = path.join(TEMP_DIR, repoName)

    // 使用 sparse checkout 获取特定目录
    if (await sparseCheckout(repo, branch, source, repoTempDir)) {
      // 复制文档到目标目录
      const sourceDir = path.join(repoTempDir, source)
      if (await copyDocs(sourceDir, targetDir)) {
        console.log(`成功复制 ${repo} 的文档到 ${targetDir}`)
      }
    }
  }

  // 清理临时目录
  await cleanupTempDir()

  console.log('文档获取完成！')
}

// 执行主函数
main().catch((error) => {
  console.error('文档获取失败')
  console.error(error)
  process.exit(1)
})
