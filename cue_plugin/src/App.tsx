import { useEffect, useRef, useState } from 'react'
import {
  CreateStartUpPageContainer,
  EventSourceType,
  OsEventTypeList,
  TextContainerProperty,
  TextContainerUpgrade,
  waitForEvenAppBridge,
  type EvenAppBridge,
} from '@evenrealities/even_hub_sdk'

const CANVAS_WIDTH = 576
const CANVAS_HEIGHT = 288
const MAIN_CONTAINER_ID = 1
const MAIN_CONTAINER_NAME = 'cue'
const DIVIDER = '-'.repeat(28)
const IDLE_HUD_TEXT = ['Cue', '', DIVIDER, '', 'Listening...'].join('\n')

// Use the host that served this page so the plugin also works when loaded
// from a phone on the LAN (real glasses). Fall back to the env override or
// localhost when running in a dev browser without a host header (rare).
const DEFAULT_BRIDGE_URL = (() => {
  const envUrl = (import.meta.env as { VITE_CUE_BRIDGE_URL?: string })
    .VITE_CUE_BRIDGE_URL
  if (envUrl) return envUrl
  const host =
    typeof window !== 'undefined' && window.location.hostname
      ? window.location.hostname
      : '127.0.0.1'
  return `ws://${host}:8765`
})()

type IncomingCard = {
  type: 'send_card'
  title: string
  lines: string[]
  ttl_ms: number
}
type ClearCard = { type: 'clear_card' }
type Incoming = IncomingCard | ClearCard

type Outgoing =
  | { type: 'temple_tap'; side: 'left' | 'right'; count: number }
  | { type: 'head_shake' }

function sourceSide(src?: EventSourceType): 'left' | 'right' | null {
  switch (src) {
    case EventSourceType.TOUCH_EVENT_FROM_GLASSES_L:
      return 'left'
    case EventSourceType.TOUCH_EVENT_FROM_GLASSES_R:
    case EventSourceType.TOUCH_EVENT_FROM_RING:
      return 'right'
    default:
      return null
  }
}

function countFor(type?: OsEventTypeList): number | null {
  switch (type) {
    case OsEventTypeList.CLICK_EVENT:
      return 1
    case OsEventTypeList.DOUBLE_CLICK_EVENT:
      return 2
    case OsEventTypeList.SCROLL_TOP_EVENT:
      return 3
    default:
      return null
  }
}

function formatCard(card: IncomingCard): string {
  return [card.title, DIVIDER, ...card.lines].join('\n')
}

function App() {
  const bridgeRef = useRef<EvenAppBridge | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const ttlTimerRef = useRef<number | null>(null)

  const [bridgeStatus, setBridgeStatus] = useState('initializing…')
  const [wsStatus, setWsStatus] = useState('disconnected')
  const [hudText, setHudText] = useState(IDLE_HUD_TEXT)
  const [lastCard, setLastCard] = useState<IncomingCard | null>(null)
  const [lastTouch, setLastTouch] = useState('(none)')
  const [events, setEvents] = useState<string[]>([])
  const [sent, setSent] = useState<string[]>([])

  const hudTextRef = useRef(hudText)
  hudTextRef.current = hudText

  const pushToGlasses = async (text: string) => {
    const bridge = bridgeRef.current
    if (!bridge) return
    const upgrade = new TextContainerUpgrade({
      containerID: MAIN_CONTAINER_ID,
      containerName: MAIN_CONTAINER_NAME,
      content: text,
      contentOffset: 0,
      contentLength: text.length,
    })
    await bridge.textContainerUpgrade(upgrade)
  }

  useEffect(() => {
    pushToGlasses(hudText).catch(() => {})
  }, [hudText])

  const scheduleClear = (ttl_ms: number) => {
    if (ttlTimerRef.current != null) window.clearTimeout(ttlTimerRef.current)
    ttlTimerRef.current = window.setTimeout(() => {
      setHudText(IDLE_HUD_TEXT)
      setLastCard(null)
    }, ttl_ms)
  }

  const sendToPython = (msg: Outgoing) => {
    const ws = wsRef.current
    if (!ws || ws.readyState !== WebSocket.OPEN) return
    const payload = JSON.stringify(msg)
    ws.send(payload)
    setSent((prev) => [payload, ...prev].slice(0, 10))
  }

  const sendRawEvent = (raw: unknown) => {
    const ws = wsRef.current
    if (!ws || ws.readyState !== WebSocket.OPEN) return
    ws.send(JSON.stringify({ type: 'raw_event', payload: raw }))
  }

  useEffect(() => {
    let unsubscribe: (() => void) | undefined
    let disposed = false
    let retryTimer: number | null = null

    const connectWs = () => {
      if (disposed) return
      const ws = new WebSocket(DEFAULT_BRIDGE_URL)
      wsRef.current = ws
      setWsStatus(`connecting ${DEFAULT_BRIDGE_URL}`)
      ws.onopen = () => setWsStatus(`connected ${DEFAULT_BRIDGE_URL}`)
      ws.onclose = () => {
        setWsStatus('disconnected — retrying in 2s')
        wsRef.current = null
        if (!disposed) retryTimer = window.setTimeout(connectWs, 2000)
      }
      ws.onerror = () => setWsStatus('error')
      ws.onmessage = (ev) => {
        let msg: Incoming
        try {
          msg = JSON.parse(String(ev.data))
        } catch {
          return
        }
        if (msg.type === 'send_card') {
          setHudText(formatCard(msg))
          setLastCard(msg)
          scheduleClear(msg.ttl_ms || 6000)
        } else if (msg.type === 'clear_card') {
          setHudText(IDLE_HUD_TEXT)
          setLastCard(null)
        }
      }
    }

    ;(async () => {
      const bridge = await waitForEvenAppBridge()
      bridgeRef.current = bridge
      const page = new CreateStartUpPageContainer({
        containerTotalNum: 1,
        textObject: [
          new TextContainerProperty({
            containerID: MAIN_CONTAINER_ID,
            containerName: MAIN_CONTAINER_NAME,
            xPosition: 0,
            yPosition: 0,
            width: CANVAS_WIDTH,
            height: CANVAS_HEIGHT,
            borderWidth: 1,
            borderColor: 15,
            borderRadius: 4,
            paddingLength: 16,
            isEventCapture: 1,
            content: hudTextRef.current,
          }),
        ],
      })
      const result = await bridge.createStartUpPageContainer(page)
      setBridgeStatus(`createStartUpPageContainer → ${result}`)

      unsubscribe = bridge.onEvenHubEvent((event) => {
        setEvents((prev) => [JSON.stringify(event), ...prev].slice(0, 10))
        const type = event.textEvent?.eventType ?? event.sysEvent?.eventType
        const src = event.sysEvent?.eventSource
        const side = sourceSide(src) ?? 'right'
        const count = countFor(type)
        // Always forward a sanitized copy of the raw event to Python for
        // diagnostics; it's cheap and helps us see what the real G2 fires.
        sendRawEvent({
          raw: JSON.parse(JSON.stringify(event)),
          classifiedSide: side,
          classifiedCount: count,
        })
        if (count != null) {
          setLastTouch(`${side} · tap x${count}`)
          sendToPython({ type: 'temple_tap', side, count })
        }
      })

      connectWs()
    })().catch((err) => setBridgeStatus(`error: ${String(err)}`))

    return () => {
      disposed = true
      unsubscribe?.()
      if (retryTimer != null) window.clearTimeout(retryTimer)
      if (ttlTimerRef.current != null) window.clearTimeout(ttlTimerRef.current)
      wsRef.current?.close()
    }
  }, [])

  return (
    <main
      style={{
        padding: 24,
        fontFamily: 'system-ui',
        color: '#111',
        maxWidth: 880,
      }}
    >
      <header style={{ marginBottom: 16 }}>
        <h1 style={{ margin: 0 }}>Cue — plugin bridge</h1>
        <p style={{ marginTop: 4, fontSize: 14, color: '#555' }}>
          SDK: <code>{bridgeStatus}</code> · WS: <code>{wsStatus}</code> · Last
          touch: <code>{lastTouch}</code>
        </p>
      </header>

      <section style={{ marginBottom: 16 }}>
        <h3 style={h3}>Canvas preview (576 × 288)</h3>
        <div
          style={{
            width: CANVAS_WIDTH,
            height: CANVAS_HEIGHT,
            background: '#000',
            color: '#0f0',
            fontFamily: 'monospace',
            fontSize: 22,
            lineHeight: 1.25,
            padding: 16,
            boxSizing: 'border-box',
            whiteSpace: 'pre-wrap',
            border: '1px solid #0f0',
            borderRadius: 4,
            letterSpacing: 0.5,
          }}
        >
          {hudText}
        </div>
        <p style={{ fontSize: 12, color: '#555', marginTop: 8 }}>
          Tap temple → forwarded to Python over WebSocket. Python sends a card
          → renders here and on the G2 HUD.
        </p>
      </section>

      <section
        style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}
      >
        <div>
          <h3 style={h3}>Last card</h3>
          <pre style={codeBlock}>
            {lastCard ? JSON.stringify(lastCard, null, 2) : '(none)'}
          </pre>
        </div>
        <div>
          <h3 style={h3}>Sent to Python</h3>
          <pre style={codeBlock}>
            {sent.length ? sent.join('\n') : '(none)'}
          </pre>
        </div>
      </section>

      <section style={{ marginTop: 16 }}>
        <h3 style={h3}>Recent SDK events</h3>
        <pre style={codeBlock}>
          {events.length ? events.join('\n') : '(none yet)'}
        </pre>
      </section>
    </main>
  )
}

const h3: React.CSSProperties = {
  margin: '0 0 8px',
  fontSize: 14,
  textTransform: 'uppercase',
  letterSpacing: 1,
  color: '#555',
}

const codeBlock: React.CSSProperties = {
  background: '#f4f4f4',
  padding: 12,
  fontSize: 12,
  borderRadius: 4,
  maxHeight: 320,
  overflow: 'auto',
  margin: 0,
}

export default App
