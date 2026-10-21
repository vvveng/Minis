# Scripting 高频 API 速查（均已对照本地官方文档核对）

> 全部条目来自 `references/api/` 下的官方文档副本（源头 `https://scriptingapp.github.io/llms.txt`）。
> 写代码前若本表没有的 API，**去 `references/api/` 用 rg 检索**，不要凭记忆写。

---

## Script（`references/api/Script.md`）

| 成员 | 说明 |
|---|---|
| `Script.name: string` | 当前脚本名 |
| `Script.directory: string` | 脚本所在目录绝对路径 |
| `Script.env: string` | 运行环境：`index` / `widget` / `control_widget` / `notification` / `intent` / `app_intents` / `assistant_tool` / `keyboard` / `live_activity` |
| `Script.widgetParameter: string` | 从小组件启动时传入的参数 |
| `Script.queryParameters: Record<string, any>` | 启动参数。JSON 对象启动保留类型；`run` URL scheme 启动全是字符串 |
| `Script.metadata` | `icon` / `color` / `localizedName(s)` / `description` / `version` / `author{name,email,homepage}` / `contributors[]` / `remoteResource{url,autoUpdateInterval}` |
| `Script.exit(result?)` | 结束脚本，可带返回值 |
| `Script.run<T>(options): Promise<T \| null>` | 以编程方式运行其它脚本 |
| `Script.createRunURLScheme(scriptName, queryParameters?)` | 生成 `scripting://run/...` 链接 |
| `Script.createRunSingleURLScheme(...)` / `createOpenURLScheme(...)` / `createDocumentationURLScheme(title?)` | 其它 scheme 构造 |
| `Script.createImportScriptsURLScheme(urls)` | 生成导入脚本链接 |
| `Script.hasFullAccess(): boolean` | 是否有完全访问权限 |

## 最小化与恢复（`Script_Minimization_and_Resume.md`）

`Script.supportsMinimization()`、`Script.isMinimized()`、`Script.minimize(): Promise<boolean>`、
`Script.enableMinimize(enabled?)`、`Script.onMinimize(cb)`、`Script.onResume(cb)`。
`ResumeEventDetails`：`resumeFromMinimized` / `widgetParameter` / `controlWidgetParameter` / `queryParameters` / `notificationInfo`。

## FileManager（`references/api/Utilities_FileManager_md.md`）

**目录常量**：`documentsDirectory` `iCloudDocumentsDirectory` `appGroupDocumentsDirectory` `scriptsDirectory` `temporaryDirectory`
`webDAVDocumentsDirectory`（+ `isWebDAVAvailable`）`safariBrowserDirectory` `safariBrowserStorageDirectory` `safariBrowserDownloadsDirectory` `safariBrowserUserscriptsDirectory`
`isiCloudEnabled` / `isFileStoredIniCloud(path)` / `isiCloudFileDownloaded(path)` / `downloadFileFromiCloud(path)` / `getShareUrlOfiCloudFile(path, expiration?)`

**读写**：每个都有同步/异步两版 —— `createDirectory` `createLink` `copyFile` `readDirectory` `exists` `rename` `remove`
`readAsString` `readAsBytes` `readAsData` `writeAsString` `writeAsBytes` `writeAsData`
`stat` `mimeType` `destinationOfSymbolicLink` `zip` `unzip` `isFile` `isDirectory` `isLink` `isBinaryFile`
书签：`bookmarkExists` `getAllFileBookmarks` `bookmarkedPath`

> 同步方法会阻塞；能 async 就 async。路径里**不要**硬编码 App Group / iCloud 的 UUID。

## Storage（`references/api/Utilities_Storage_md.md`）

轻量键值持久化，支持 `string` / `number` / `boolean` / JSON / `Data`；默认私有域（仅当前脚本），`{ shared: true }` 用共享域（所有脚本可读）。

- `Storage.set<T>(key, value, options?): boolean`
- `Storage.get<T>(key, options?): T | null`
- `Storage.setData(key, data, options?)` / `Storage.getData(key, options?)`
- 删除/清空类方法见文档

## Navigation（`Views_Modal_presentaions_index_md.md`、`Views_Present_views_Dismissing_a_presented_view_index_md.md`）

- `Navigation.present(element)` 或 `Navigation.present({ element, modalPresentationStyle? })`
- `Navigation.useDismiss()` — **只能在被 present 的组件树内使用**
- 页面级模态：SwiftUI 风格属性 `sheet` / `popover` / `fullScreenCover` / `alert` / `confirmationDialog`（配 `isPresented` / `onChanged` / `content` / `actions` / `presentationDetents` / `presentationDragIndicator` / `presentationCompactAdaptation`）

## Widget（`Widget_Widget_API_md.md`）

- `Widget.present(element, { reloadPolicy? })` — 在 `widget.tsx` 里用；**present 前把数据准备好**
- `Widget.family: WidgetFamily`（用户配置的小组件尺寸）、`Widget.displaySize`
- `Widget.reloadAll()`、`WidgetReloadPolicy`（默认 `atEnd`）
- 锁屏/StandBy 用 `AccessoryWidgetBackground`；染色模式见 `Widget_Background_in_Tinted_Mode.md`

## 常用原生能力（均在 `references/api/Device_Capabilities_*`）

`Notification`（本地通知 + 富通知 `Notification.present(element)`）、`Calendar` / `CalendarEvent`、`Reminder`、
`Location`、`Photos`、`Speech` / `SpeechRecognition`、`DocumentPicker`、`DocumentInteraction`、`ShareSheet`、`Send_Mail`、`Send_Message`、
`Safari`、`Pasteboard`、`Keychain`、`LocalAuth`、`Vision`、`Weather`、`MapKit`、`Device`、`BackgroundKeeper`、`CloudSharedData`、
`Crypto` / `JWT`、`WebScraper`、`fetch`（`Utilities_Request_fetch_md.md`）、`LanguageModelSession`、`MediaLibrary`、`AlarmManager`、`PDF`、`QuickLook`。

## 视图组件（TSX）

容器/布局：`VStack` `HStack` `ZStack` `Grid` `ScrollView` `List` `Form` `Section` `Group` `NavigationStack` `TabView` `Spacer` `Divider`
控件：`Text` `Button` `Toggle` `TextField` `SecureField` `Slider` `Picker` `DatePicker` `ProgressView` `Label` `Image` `Link`
修饰器文档：`buttonStyle` `listStyle` `formStyle` `textFieldStyle` `toggleStyle` `datePickerStyle` `contextMenu` `refreshable_list` `widgetBackground` `Text_View_Modifiers` `Navigation_View_Modifiers` `Chaining_View_Modifiers`

## CLI（Mac 端真机同步调试，非 iPhone）

```bash
npx scripting-cli start --bonjour     # 桌面编辑器 → App 实时同步
npx -p typescript tsc --noEmit -p tsconfig.json
```
App 同步后会在工作区生成 `.d.ts` 声明，**需要精确签名时以本地同步的声明为准**（配合官方文档理解行为与权限）。
