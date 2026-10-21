<!-- source: https://scriptingapp.github.io/guide/Device%20Capabilities/AVCaptureSession%20%26%20Camera%20Control/Device%20formats/index_example.md | title: Example -->

# Example

```tsx
import {
  Button, CaptureVideoPreviewView, HStack, List, Navigation, NavigationStack,
  Script, ScrollView, Section, Spacer, Text, Toolbar, ToolbarItem,
  useEffect, useMemo, useObservable, VStack
} from "scripting"

type FormatRow = {
  /** 同一 wrapper 引用, 传回 setActiveFormat 用 */
  ref: AVCaptureDeviceFormat
  index: number
  label: string
  fpsLabel: string
  flagsLabel: string
  isActive: boolean
}

function describeFormat(f: AVCaptureDeviceFormat): { fps: string, flags: string } {
  // 多 range 拼接, 因为单个 format 可能同时报多档 fps
  const fps = f.videoSupportedFrameRateRanges
    .map(r => r.minFrameRate === r.maxFrameRate
      ? `${Math.round(r.maxFrameRate)}`
      : `${Math.round(r.minFrameRate)}-${Math.round(r.maxFrameRate)}`)
    .join(" / ") + "fps"

  const flags: string[] = []
  if (f.isVideoBinned) flags.push("binned")
  if (f.isVideoHDRSupported) flags.push("hdr")
  if (f.isMultiCamSupported) flags.push("multiCam")
  if (f.isSpatialVideoCaptureSupported) flags.push("spatial")
  if (f.isCenterStageSupported) flags.push("centerStage")
  if (f.isPortraitEffectSupported) flags.push("portrait")
  if (f.isStudioLightSupported) flags.push("studioLight")
  if (f.isHighestPhotoQualitySupported) flags.push("photoHQ+")
  return { fps, flags: flags.join(", ") || "—" }
}

function View() {
  const dismiss = Navigation.useDismiss()
  const isRunning = useObservable(false)
  const lastError = useObservable("")
  const activeLabel = useObservable("")
  // bump 一下触发 UI 重读 activeFormat / activeColorSpace / 帧率 clamp 状态
  const tick = useObservable(0)

  const { session, camera } = useMemo(() => {
    const camera = AVCaptureDevice.default("video")!
    const session = new AVCaptureSession()
    const input = new AVCaptureDeviceInput(camera)

    session.configure(() => {
      // photo preset 让相机先以拍照模式跑起来, 后面 setActiveFormat 再覆盖具体维度
      session.sessionPreset = "photo"
      if (session.canAddInput(input)) session.addInput(input)
    })

    return { session, camera }
  }, [])

  // 一次性把 formats 包成行数据。`camera.formats` 对同一底层 format 始终返回同一实例,
  // 所以 `ref === camera.activeFormat` 用来高亮当前项是可靠的。
  const allRows = useMemo<FormatRow[]>(() => {
    return camera.formats.map((f, i) => {
      const { fps, flags } = describeFormat(f)
      return {
        ref: f,
        index: i,
        label: `${f.width}×${f.height} · ${f.mediaType}`,
        fpsLabel: fps,
        flagsLabel: flags,
        isActive: false,
      }
    })
  }, [camera])

  // 简单过滤: 4K / 1080p60 / spatial / multiCam — 用文档里给出的常见 filter
  const presets = useMemo(() => [
    { name: "All", filter: (_: AVCaptureDeviceFormat) => true },
    { name: "4K", filter: (f: AVCaptureDeviceFormat) => f.width === 3840 && f.height === 2160 },
    { name: "1080p60", filter: (f: AVCaptureDeviceFormat) =>
        f.width === 1920 && f.height === 1080 &&
        f.videoSupportedFrameRateRanges.some(r => r.maxFrameRate >= 60) },
    { name: "HDR", filter: (f: AVCaptureDeviceFormat) => f.isVideoHDRSupported },
    { name: "MultiCam", filter: (f: AVCaptureDeviceFormat) => f.isMultiCamSupported },
    { name: "Spatial", filter: (f: AVCaptureDeviceFormat) => f.isSpatialVideoCaptureSupported },
  ], [])

  const filter = useObservable<string>("All")
  const filteredRows = useMemo(() => {
    const pred = presets.find(p => p.name === filter.value)?.filter ?? (() => true)
    void tick.value // 让 active 高亮跟着切换重算
    return allRows
      .filter(r => pred(r.ref))
      .map(r => ({ ...r, isActive: r.ref === camera.activeFormat }))
  }, [allRows, filter.value, tick.value])

  function refreshActiveLabel() {
    const af = camera.activeFormat
    const minDur = camera.activeVideoMinFrameDuration
    const maxDur = camera.activeVideoMaxFrameDuration
    const fpsHi = minDur > 0 ? Math.round(1 / minDur) : null
    const fpsLo = maxDur > 0 ? Math.round(1 / maxDur) : null
    const fpsTag = (fpsHi || fpsLo) ? ` · ${fpsLo ?? "?"}-${fpsHi ?? "?"}fps` : ""
    activeLabel.setValue(
      `#${allRows.findIndex(r => r.ref === af)} · ${af.width}×${af.height} · ${camera.activeColorSpace}${fpsTag}`
    )
  }

  useEffect(() => {
    async function start() {
      try {
        await session.startRunning()
        isRunning.setValue(true)
        refreshActiveLabel()
      } catch (e) {
        await Dialog.alert({ message: `Failed to start: ${String(e)}` })
        dismiss()
      }
    }
    start()
    return () => {
      session.stopRunning().finally(() => session.dispose())
    }
  }, [])

  async function applyFormat(row: FormatRow) {
    try {
      camera.setActiveFormat(row.ref)
      tick.setValue(tick.value + 1)
      refreshActiveLabel()
      lastError.setValue("")
    } catch (e) {
      lastError.setValue(String(e))
    }
  }

  /** 把 active format 支持的色彩空间挨个尝一遍, 演示 setActiveColorSpace 的校验 */
  function cycleColorSpace() {
    try {
      const list = camera.activeFormat.supportedColorSpaces
      if (list.length === 0) {
        lastError.setValue("Active format reports no color spaces")
        return
      }
      const current = camera.activeColorSpace
      const idx = list.indexOf(current as any)
      const next = list[(idx + 1) % list.length]
      camera.setActiveColorSpace(next)
      tick.setValue(tick.value + 1)
      refreshActiveLabel()
      lastError.setValue(`color space → ${next}`)
    } catch (e) {
      lastError.setValue(String(e))
    }
  }

  /** 把 fps 锁到 active format 支持的最高档 — 走 setActiveVideoMin/MaxFrameDuration 的合法路径 */
  function lockToMaxFps() {
    try {
      const ranges = camera.activeFormat.videoSupportedFrameRateRanges
      if (ranges.length === 0) {
        lastError.setValue("Active format reports no fps ranges")
        return
      }
      const top = ranges.reduce((a, b) => a.maxFrameRate >= b.maxFrameRate ? a : b)
      // 锁死 = min duration === max duration = 1 / top.maxFrameRate
      const dur = 1 / top.maxFrameRate
      camera.setActiveVideoMinFrameDuration(dur)
      camera.setActiveVideoMaxFrameDuration(dur)
      tick.setValue(tick.value + 1)
      refreshActiveLabel()
      lastError.setValue(`locked to ${Math.round(top.maxFrameRate)}fps`)
    } catch (e) {
      lastError.setValue(String(e))
    }
  }

  /** 验证非法 fps duration 被拒: 用 1/1000 秒 (≈ 1000fps) 远超任何 format 的能力, 期望 throw */
  function probeInvalidFps() {
    try {
      camera.setActiveVideoMinFrameDuration(1 / 1000)
      lastError.setValue("Unexpected: invalid fps accepted")
    } catch (e) {
      lastError.setValue(`OK (rejected): ${String(e)}`)
    }
  }

  /** 验证跨 device 拒绝: 再取一次 default("video") 包成不同 wrapper, 把它的 format
   *  传给当前 camera, 期望抛 "does not belong to this device" */
  function probeForeignReject() {
    const another = AVCaptureDevice.default("video")
    if (!another) {
      lastError.setValue("No second device wrapper available")
      return
    }
    const foreign = another.formats[0]
    try {
      camera.setActiveFormat(foreign)
      lastError.setValue("Unexpected: foreign format accepted")
    } catch (e) {
      lastError.setValue(`OK (rejected): ${String(e)}`)
    }
  }

  return (
    <NavigationStack>
      <VStack
        navigationTitle="Device formats"
        toolbar={
          <Toolbar>
            <ToolbarItem placement="topBarTrailing">
              <Button title="Done" systemImage="xmark" action={dismiss} />
            </ToolbarItem>
          </Toolbar>
        }
      >
        <CaptureVideoPreviewView
          session={session}
          videoDevice={camera}
          videoGravity="resizeAspectFill"
          frame={{ height: 200 }}
          cornerRadius={12}
          masksToBounds
        />

        <VStack alignment="leading" spacing={4} padding={8}>
          <Text font="caption">Status</Text>
          <Text font="footnote">
            running: {String(isRunning.value)} · active: {activeLabel.value} · total: {allRows.length}
          </Text>
          {lastError.value ? (
            <Text font="footnote" foregroundStyle="red">{lastError.value}</Text>
          ) : null}
        </VStack>

        <ScrollView axes="horizontal" scrollIndicator={'hidden'}>
          <HStack padding={8} spacing={8}>
            {presets.map(p => (
              <Button
                key={p.name}
                title={`${p.name} (${allRows.filter(r => p.filter(r.ref)).length})`}
                buttonStyle={filter.value === p.name ? "borderedProminent" : "bordered"}
                controlSize="small"
                action={() => filter.setValue(p.name)}
              />
            ))}
          </HStack>
        </ScrollView>

        <ScrollView axes="horizontal" scrollIndicator={'hidden'}>
          <HStack padding={8} spacing={8}>
            <Button title="Cycle color space" buttonStyle="bordered" controlSize="small" action={cycleColorSpace} />
            <Button title="Lock to max fps"   buttonStyle="bordered" controlSize="small" action={lockToMaxFps} />
            <Button title="Probe bad fps"      buttonStyle="bordered" controlSize="small" action={probeInvalidFps} />
            <Button title="Probe foreign"      buttonStyle="bordered" controlSize="small" action={probeForeignReject} />
          </HStack>
        </ScrollView>

        <List>
          <Section header={<Text>{filteredRows.length} format(s)</Text>}>
            {filteredRows.map(r => (
              <Button
                key={r.index}
                action={() => applyFormat(r)}
              >
                <VStack alignment="leading" spacing={2}>
                  <HStack>
                    <Text font="footnote" fontWeight={r.isActive ? "bold" : "regular"}>
                      #{r.index} · {r.label}
                    </Text>
                    <Spacer />
                    {r.isActive ? <Text font="footnote" foregroundStyle="green">ACTIVE</Text> : null}
                  </HStack>
                  <Text font="caption" foregroundStyle="secondaryLabel">
                    {r.fpsLabel} · {r.flagsLabel}
                  </Text>
                </VStack>
              </Button>
            ))}
          </Section>
        </List>
      </VStack>
    </NavigationStack>
  )
}

async function run() {
  await Navigation.present({ element: <View /> })
  Script.exit()
}

run()

```
