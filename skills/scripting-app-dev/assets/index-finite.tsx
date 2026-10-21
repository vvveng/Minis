// 一次性任务模板：做完后必须 Script.exit()，否则事件循环不结束、脚本挂住。
import { Script } from "scripting"

async function run() {
  try {
    // 写具体逻辑；用到 Scripting 专有 API 前先查 references/api/ 或官方 llms.txt
    console.log("script:", Script.name, "env:", Script.env)
  } catch (error) {
    console.error(error)
  } finally {
    Script.exit()
  }
}

run()
