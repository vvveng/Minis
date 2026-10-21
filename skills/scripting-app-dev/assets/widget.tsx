// 小组件模板：Widget.present() 之前把数据准备好，widget 上下文在 present 后立刻结束。
import { Text, VStack, Widget } from "scripting"

function WidgetView() {
  return (
    <VStack>
      <Text>Hello Scripting!</Text>
    </VStack>
  )
}

Widget.present(<WidgetView />)
