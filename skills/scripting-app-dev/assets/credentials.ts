/**
 * 🐝密码管理器 凭据读取模块（可直接复制进用户脚本使用）
 *
 * 规则（来自用户上游 skill「数据读取辅助」）：
 *  1. 存储路径必须用 FileManager.appGroupDocumentsDirectory 动态拼接
 *     （App Group 的 UUID 每台设备不同，绝对路径禁止硬编码）。
 *  2. 定位优先级：projectCode（5 位项目码，全库唯一） > service(+key)。
 *     两者都传且指向不同账号时以项目码为准，并回传 serviceConflict / note。
 *  3. 敏感字段（secure：密码 / Token / API Key）默认打码返回，
 *     只有用户明确要求使用时才传 confirm: true 取明文。
 *  4. 明文拿到后不要打印进日志、不要写文件/记忆，只在调用处直接使用。
 */

export interface CredentialField {
  key?: string
  title: string
  value: string
  secure?: boolean
}

export interface CredentialAccount {
  id: string
  /** 项目码：5 位数字，全库唯一，优先用它定位账号 */
  code?: string
  fields: CredentialField[]
}

export interface CredentialsFile {
  updatedAt?: string
  services: Record<string, CredentialAccount[]>
  security?: unknown
  templates?: unknown
  viewMode?: "grouped" | "independent"
  showGuide?: boolean
  autoBackupEnabled?: boolean
  autoBackupPassword?: string
  autoBackupAt?: string
}

export interface ReadOptions {
  /** 项目码，5 位数字，优先 */
  projectCode?: string
  /** 服务名，大小写不敏感 */
  service?: string
  /** 字段 key：account / password / userId / token / custom */
  key?: string
  /** 是否允许返回敏感字段明文，默认 false */
  confirm?: boolean
}

export interface CredentialResult {
  success: boolean
  found?: boolean
  error?: string
  hint?: string
  requiresConfirm?: boolean
  service?: string
  code?: string
  key?: string
  value?: string
  accountId?: string
  account?: { id: string; code?: string; fields: CredentialField[] }
  accounts?: Array<{ id: string; code?: string; fields: CredentialField[] }>
  accountCount?: number
  codes?: string[]
  flatMap?: Record<string, string>
  availableServices?: string[]
  serviceConflict?: boolean
  note?: string
}

const MASK = "*** (加密隐藏)"

/** 项目码格式校验：5 位数字，首位不为 0（10000–99999） */
export function normalizeProjectCode(value: unknown): string | undefined {
  const s = String(value ?? "").trim()
  return /^[1-9]\d{4}$/.test(s) ? s : undefined
}

/** 凭据文件绝对路径（动态拼接，勿硬编码） */
export function credentialsPath(): string {
  return FileManager.appGroupDocumentsDirectory + "/🐝密码管理器/credentials.json"
}

/** 打码：secure 字段只保留 key/title，不给 value */
function maskAccount(account: CredentialAccount) {
  return {
    id: account.id,
    code: account.code,
    fields: account.fields.map(f => ({
      key: f.key,
      title: f.title,
      value: f.secure ? MASK : f.value,
      secure: !!f.secure,
    })),
  }
}

/** 只含非敏感字段的键值映射 */
function flatMapOf(account: CredentialAccount): Record<string, string> | undefined {
  if (!account) return undefined
  const flat: Record<string, string> = {}
  for (const f of account.fields) {
    if (f.key && !f.secure && f.value) flat[f.key] = f.value
  }
  if (account.code) flat["code"] = account.code
  return Object.keys(flat).length > 0 ? flat : undefined
}

function extractKeys(accounts: CredentialAccount[]): string[] {
  const keys = new Set<string>()
  for (const a of accounts) for (const f of a.fields) if (f.key) keys.add(f.key)
  return Array.from(keys)
}

/**
 * 读取凭据。返回纯对象，由调用方决定怎么用（Script.exit / 继续处理）。
 * 不抛异常：失败一律通过返回值里的 success/error/hint 表达。
 */
export function readCredentials(options: ReadOptions): CredentialResult {
  const service = (options.service ?? "").toString().trim().toLowerCase()
  const codeRaw = (options.projectCode ?? "").toString().trim()
  const code = codeRaw ? normalizeProjectCode(codeRaw) : undefined
  const key = (options.key ?? "").toString().trim().toLowerCase() || undefined
  const confirm = options.confirm === true

  if (codeRaw && !code) {
    return {
      success: false,
      error: `项目码「${codeRaw}」格式不正确`,
      hint: "项目码是 5 位数字（如 12345），在🐝密码管理器账号详情页服务名尾部，点击可复制。",
    }
  }

  if (!service && !code) {
    return {
      success: false,
      error: "缺少参数：至少需要 service（服务名）或 projectCode（5 位项目码）之一",
      hint: "service=github 或 projectCode=12345",
    }
  }

  const path = credentialsPath()
  if (!FileManager.existsSync(path)) {
    return {
      success: false,
      error: "🐝密码管理器的存储文件不存在",
      hint: "请先在 Scripting App 中运行「🐝密码管理器」脚本并保存账号。",
    }
  }

  let data: CredentialsFile
  try {
    data = JSON.parse(FileManager.readAsStringSync(path))
  } catch (e) {
    return { success: false, error: "凭据文件读取或解析失败", hint: String(e) }
  }
  if (!data || typeof data.services !== "object" || data.services === null) {
    return { success: false, error: "凭据文件结构异常：缺少 services 字段" }
  }

  const serviceKeys = Object.keys(data.services)

  // ---- 1) 项目码精确定位（跨服务唯一） ----
  if (code) {
    const hits: Array<{ service: string; account: CredentialAccount }> = []
    for (const svcName of serviceKeys) {
      const list = data.services[svcName]
      if (!Array.isArray(list)) continue
      for (const account of list) if (account.code === code) hits.push({ service: svcName, account })
    }
    if (hits.length === 0) {
      return {
        success: false,
        found: false,
        error: `没有找到项目码为「${code}」的账号`,
        hint: "项目码在账号详情页服务名尾部显示，也可在首页搜索框直接搜。",
      }
    }

    const hit = hits[0]
    const conflict =
      service && hit.service.toLowerCase() !== service
        ? {
            serviceConflict: true,
            note: `传入的 service「${service}」与项目码「${code}」指向不同账号；已按优先级以项目码为准（该账号实际在服务「${hit.service}」下）。`,
          }
        : {}

    if (key) {
      const field = hit.account.fields.find(
        f => f.key && f.key.toLowerCase() === key && f.value
      )
      if (!field) {
        return {
          success: false,
          found: false,
          error: `项目码「${code}」的账号中没有字段 key 为「${key}」的值`,
          hint: `可用字段 key：${extractKeys([hit.account]).join("、")}`,
          service: hit.service,
          code,
          ...conflict,
        }
      }
      if (field.secure && !confirm) {
        return {
          success: true,
          found: false,
          requiresConfirm: true,
          service: hit.service,
          code,
          key,
          value: MASK,
          hint: "敏感字段默认不返回明文；确需读取请显式传 confirm: true。",
          ...conflict,
        }
      }
      return { success: true, service: hit.service, code, key, value: field.value, ...conflict }
    }

    if (hits.length > 1) {
      return {
        success: true,
        service: hit.service,
        code,
        accountCount: hits.length,
        accounts: hits.map(h => ({ service: h.service, ...maskAccount(h.account) })),
        ...conflict,
      }
    }

    return {
      success: true,
      service: hit.service,
      code,
      accountCount: 1,
      account: maskAccount(hit.account),
      flatMap: flatMapOf(hit.account),
      ...conflict,
    }
  }

  // ---- 2) 按服务名读取 ----
  const serviceKey = serviceKeys.find(k => k.toLowerCase() === service)
  const accounts = serviceKey ? data.services[serviceKey] : undefined
  if (!accounts || !Array.isArray(accounts) || accounts.length === 0) {
    return {
      success: false,
      found: false,
      error: `服务「${service}」没有找到凭据`,
      hint: serviceKeys.length ? `目前已保存的服务：${serviceKeys.join("、")}` : "还未保存任何服务凭据。",
      availableServices: serviceKeys,
    }
  }

  if (key) {
    for (const account of accounts) {
      for (const field of account.fields) {
        if (field.key && field.key.toLowerCase() === key && field.value) {
          if (field.secure && !confirm) {
            return {
              success: true,
              found: false,
              requiresConfirm: true,
              service,
              key,
              value: MASK,
              accountId: account.id,
              code: account.code,
              hint: "敏感字段默认不返回明文；确需读取请显式传 confirm: true。",
            }
          }
          return {
            success: true,
            service,
            key,
            value: field.value,
            accountId: account.id,
            code: account.code,
          }
        }
      }
    }
    return {
      success: false,
      found: false,
      error: `服务「${service}」的账号中未找到字段 key 为「${key}」的值`,
      hint: `可用字段 key：${extractKeys(accounts).join("、")}`,
    }
  }

  const flat = flatMapOf(accounts[0])
  return {
    success: true,
    service,
    accounts: accounts.map(a => maskAccount(a)),
    accountCount: accounts.length,
    codes: accounts.map(a => a.code).filter(Boolean) as string[],
    flatMap: flat && Object.keys(flat).length > 0 ? flat : undefined,
  }
}

/**
 * 用法示例（写在 index.tsx 里）：
 *
 * import { readCredentials } from "./credentials"
 *
 * const token = readCredentials({ projectCode: "12345", key: "token", confirm: true })
 * if (!token.success) { console.error(token.error, token.hint) }
 * else {
 *   // 明文只在本地使用，不要 console.log 出去
 *   const res = await fetch("https://api.example.com/me", {
 *     headers: { Authorization: `Bearer ${token.value}` },
 *   })
 * }
 */
