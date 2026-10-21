import { Script } from "scripting"

// 凭据桥：在设备上读取「🐝密码管理器」的凭据，并回传给 iSH 侧的一次性接收器。
// 设计要点：
//  1. 凭据明文只从设备 → 127.0.0.1 的一次性通道，不进聊天、不进日志、不落盘（除 iSH 侧临时文件）。
//  2. 定位优先级：projectCode（5 位项目码，全库唯一） > service(+key)。
//  3. secure 字段（密码/Token/API Key）必须显式 confirm=true 才回传明文，否则回传打码值。
//  4. console.log 只打印状态，不打印凭据本身。

type Field = { key?: string; title: string; value: string; secure?: boolean }
type Account = { id: string; code?: string; fields: Field[] }
type CredFile = { services: Record<string, Account[]> }

const MASK = "*** (加密隐藏)"

function normalizeCode(v: unknown): string | undefined {
  const s = String(v ?? "").trim()
  return /^[1-9]\d{4}$/.test(s) ? s : undefined
}

function extractKeys(accounts: Account[]): string[] {
  const keys = new Set<string>()
  for (const a of accounts) for (const f of a.fields) if (f.key) keys.add(f.key)
  return Array.from(keys)
}

function maskAccount(a: Account) {
  return {
    id: a.id,
    code: a.code,
    fields: a.fields.map(f => ({
      key: f.key,
      title: f.title,
      value: f.secure ? MASK : f.value,
      secure: !!f.secure,
    })),
  }
}

async function main() {
  const q: any = (Script as any).queryParameters ?? {}
  const service = String(q.service ?? "").trim().toLowerCase()
  const codeRaw = String(q.projectCode ?? "").trim()
  const code = codeRaw ? normalizeCode(codeRaw) : undefined
  const key = String(q.key ?? "").trim().toLowerCase()
  const confirm = q.confirm === true || String(q.confirm).toLowerCase() === "true"
  const callback = String(q.callback ?? "http://127.0.0.1:8765/cred")
  const token = String(q.token ?? "")

  const send = async (payload: any) => {
    try {
      const res = await fetch(callback, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-Cred-Token": token },
        body: JSON.stringify(payload),
        allowInsecureRequest: true,
        timeout: 15,
      })
      console.log(`凭据桥: 已回传 status=${res.status}`)
    } catch (e) {
      console.log(`凭据桥: 回传失败 ${String(e)}`)
    }
  }

  if (codeRaw && !code) {
    await send({ ok: false, error: `项目码「${codeRaw}」格式不正确（应为 5 位数字）` })
    Script.exit()
    return
  }
  if (!service && !code) {
    await send({ ok: false, error: "缺少参数：需要 service 或 projectCode" })
    Script.exit()
    return
  }

  const path = FileManager.appGroupDocumentsDirectory + "/🐝密码管理器/credentials.json"
  if (!FileManager.existsSync(path)) {
    await send({
      ok: false,
      error: "🐝密码管理器的存储文件不存在",
      hint: "请先在 Scripting App 中运行「🐝密码管理器」并保存账号",
    })
    Script.exit()
    return
  }

  let data: CredFile
  try {
    data = JSON.parse(FileManager.readAsStringSync(path))
  } catch (e) {
    await send({ ok: false, error: `凭据文件解析失败: ${String(e)}` })
    Script.exit()
    return
  }
  if (!data || typeof data.services !== "object" || data.services === null) {
    await send({ ok: false, error: "凭据文件结构异常：缺少 services" })
    Script.exit()
    return
  }

  const serviceKeys = Object.keys(data.services)

  // ---- 按项目码精确定位 ----
  if (code) {
    const hits: Array<{ service: string; account: Account }> = []
    for (const svc of serviceKeys) {
      const list = data.services[svc]
      if (!Array.isArray(list)) continue
      for (const acc of list) if (acc.code === code) hits.push({ service: svc, account: acc })
    }
    if (hits.length === 0) {
      await send({ ok: false, error: `没有找到项目码为「${code}」的账号` })
      Script.exit()
      return
    }
    const hit = hits[0]
    const conflict =
      service && hit.service.toLowerCase() !== service
        ? { serviceConflict: true, note: `service「${service}」与项目码「${code}」不一致，已以项目码为准（实际服务：${hit.service}）` }
        : {}

    if (key) {
      const field = hit.account.fields.find(f => f.key && f.key.toLowerCase() === key && f.value)
      if (!field) {
        await send({
          ok: false,
          error: `项目码「${code}」的账号中没有字段 key 为「${key}」的值`,
          hint: `可用字段 key：${extractKeys([hit.account]).join("、")}`,
          service: hit.service,
          code,
          ...conflict,
        })
        Script.exit()
        return
      }
      if (field.secure && !confirm) {
        await send({
          ok: false,
          requiresConfirm: true,
          masked: true,
          value: MASK,
          service: hit.service,
          code,
          key,
          hint: "敏感字段默认不返回明文，请加 confirm=true 重试",
          ...conflict,
        })
        Script.exit()
        return
      }
      await send({ ok: true, value: field.value, service: hit.service, code, key, ...conflict })
      Script.exit()
      return
    }

    await send({
      ok: true,
      service: hit.service,
      code,
      account: maskAccount(hit.account),
      ...conflict,
    })
    Script.exit()
    return
  }

  // ---- 按服务名读取 ----
  const serviceKey = serviceKeys.find(k => k.toLowerCase() === service)
  const accounts = serviceKey ? data.services[serviceKey] : undefined
  if (!accounts || !Array.isArray(accounts) || accounts.length === 0) {
    await send({
      ok: false,
      error: `服务「${service}」没有找到凭据`,
      availableServices: serviceKeys,
    })
    Script.exit()
    return
  }

  if (key) {
    for (const acc of accounts) {
      for (const f of acc.fields) {
        if (f.key && f.key.toLowerCase() === key && f.value) {
          if (f.secure && !confirm) {
            await send({
              ok: false,
              requiresConfirm: true,
              masked: true,
              value: MASK,
              service,
              key,
              accountId: acc.id,
              code: acc.code,
              hint: "敏感字段默认不返回明文，请加 confirm=true 重试",
            })
            Script.exit()
            return
          }
          await send({ ok: true, value: f.value, service, key, accountId: acc.id, code: acc.code })
          Script.exit()
          return
        }
      }
    }
    await send({
      ok: false,
      error: `服务「${service}」中未找到字段 key 为「${key}」的值`,
      hint: `可用字段 key：${extractKeys(accounts).join("、")}`,
    })
    Script.exit()
    return
  }

  await send({
    ok: true,
    service,
    accountCount: accounts.length,
    codes: accounts.map(a => a.code).filter(Boolean),
    accounts: accounts.map(maskAccount),
  })
  Script.exit()
}

main()
