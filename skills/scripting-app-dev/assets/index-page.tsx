// 一次性页面模板：present 页面 → 关闭后退出。
// 注意：toolbar 是「视图属性」(ToolBarProps 对象)，不是 SwiftUI 的 .toolbar {} 修饰器，
//      也不要挂在 NavigationStack 上，要挂在 List / VStack / ScrollView 等可见页面上。
import {
  Button,
  List,
  Navigation,
  NavigationStack,
  Script,
  Text,
} from "scripting"

function Page() {
  const dismiss = Navigation.useDismiss()

  return (
    <NavigationStack>
      <List
        navigationTitle="示例"
        navigationBarTitleDisplayMode="inline"
        toolbar={{
          cancellationAction: (
            <Button title="关闭" action={() => dismiss()} />
          ),
        }}
      >
        <Text>内容</Text>
      </List>
    </NavigationStack>
  )
}

async function run() {
  await Navigation.present(<Page />)
  Script.exit()
}

run()
