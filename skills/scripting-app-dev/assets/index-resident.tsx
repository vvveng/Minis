// 常驻/可恢复模板：需要保留内存状态，或需要被通知/小组件/URL 再次唤醒时使用。
// 关键：注册 Script.onResume；**不要**在后面无条件 Script.exit()。
// 重复触发必须幂等：不能重复注册监听、重复写数据、重复弹 UI。
import { Button, List, Navigation, NavigationStack, Script, Text } from "scripting"

function ResidentView() {
  return (
    <NavigationStack>
      <List navigationTitle="常驻脚本">
        <Text>脚本保持存活，可接收 resume 事件。</Text>
        {Script.supportsMinimization() ? (
          <Button title="隐藏" action={() => Script.minimize()} />
        ) : null}
      </List>
    </NavigationStack>
  )
}

Script.onResume(details => {
  // 校验 details / queryParameters，并保证重复触发幂等
  console.log("Resumed", details.queryParameters)
})

Navigation.present(<ResidentView />)
