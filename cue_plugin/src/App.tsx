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
type Caption = {
  type: 'caption'
  source: string
  target: string
  target_lang: string
}
type Incoming = IncomingCard | ClearCard | Caption

type Outgoing =
  | { type: 'temple_tap'; side: 'left' | 'right'; count: number }
  | { type: 'head_shake' }
  | { type: 'save_captions' }
  | { type: 'clear_captions' }

type CaptionEntry = {
  id: number
  source: string
  target: string
  target_lang: string
  ts: number
}

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

function truncate(s: string, n: number): string {
  return s.length <= n ? s : s.slice(0, n - 1) + '~'
}

function formatCaption(c: Caption): string {
  return [
    `Live: ${c.target_lang}`,
    DIVIDER,
    truncate(c.source, 28),
    '',
    truncate(c.target, 28),
  ].join('\n')
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
  const [captions, setCaptions] = useState<CaptionEntry[]>([])
  const [savedToast, setSavedToast] = useState<string>('')

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

  const onSaveClick = () => {
    sendToPython({ type: 'save_captions' })
    setSavedToast(`Asked Python to save ${captions.length} captions...`)
    window.setTimeout(() => setSavedToast(''), 2500)
  }
  const onClearClick = () => {
    setCaptions([])
    sendToPython({ type: 'clear_captions' })
  }
  const onCopyClick = async () => {
    const text = captions
      .slice()
      .reverse()
      .map((c) => `${c.source}\n→ ${c.target}`)
      .join('\n\n')
    try {
      await navigator.clipboard.writeText(text)
      setSavedToast('Copied all captions to clipboard')
      window.setTimeout(() => setSavedToast(''), 2000)
    } catch {
      setSavedToast('Copy failed — clipboard blocked')
      window.setTimeout(() => setSavedToast(''), 2000)
    }
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
        } else if (msg.type === 'caption') {
          setHudText(formatCaption(msg))
          if (ttlTimerRef.current != null)
            window.clearTimeout(ttlTimerRef.current)
          setCaptions((prev) =>
            [
              {
                id: Date.now() + Math.random(),
                source: msg.source,
                target: msg.target,
                target_lang: msg.target_lang,
                ts: Date.now(),
              },
              ...prev,
            ].slice(0, 100),
          )
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

  const inTranslateMode = captions.length > 0

  return (
    <main
      style={{
        padding: 24,
        fontFamily: 'system-ui',
        color: '#111',
        maxWidth: 980,
      }}
    >
      <header style={{ marginBottom: 16 }}>
        <h1 style={{ margin: 0 }}>Cue — plugin bridge</h1>
        <p style={{ marginTop: 4, fontSize: 14, color: '#555' }}>
          SDK: <code>{bridgeStatus}</code> · WS: <code>{wsStatus}</code> · Last
          touch: <code>{lastTouch}</code> · Mode:{' '}
          <code>{inTranslateMode ? 'translate' : 'recognition'}</code>
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
      </section>

      {/* ----------------- Translation panel (main UI) ----------------- */}
      <section
        style={{
          marginBottom: 16,
          padding: 16,
          border: '1px solid #ddd',
          borderRadius: 8,
          background: '#fafafa',
        }}
      >
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: 12,
          }}
        >
          <h3 style={{ ...h3, margin: 0 }}>
            Live translation{' '}
            <span style={{ color: '#999', fontWeight: 400 }}>
              ({captions.length} captured)
            </span>
          </h3>
          <div style={{ display: 'flex', gap: 8 }}>
            <button style={btnSave} onClick={onSaveClick} disabled={!captions.length}>
              💾 Save
            </button>
            <button style={btnSecondary} onClick={onCopyClick} disabled={!captions.length}>
              ⧉ Copy
            </button>
            <button style={btnDanger} onClick={onClearClick} disabled={!captions.length}>
              ✕ Clear
            </button>
          </div>
        </div>
        {savedToast && (
          <div
            style={{
              background: '#0f9d58',
              color: '#fff',
              padding: '6px 10px',
              borderRadius: 4,
              fontSize: 13,
              marginBottom: 10,
            }}
          >
            {savedToast}
          </div>
        )}
        {captions.length === 0 ? (
          <p style={{ fontSize: 14, color: '#888', margin: 0 }}>
            Start <code>cue translate --to Spanish</code> in a terminal, then
            speak. Lines appear here and on the HUD. Click <b>Save</b> to persist
            to <code>~/.cue/translations/</code>.
          </p>
        ) : (
          <ul style={captionList}>
            {captions.map((c) => (
              <li key={c.id} style={captionItem}>
                <div style={captionHeader}>
                  <span>{new Date(c.ts).toLocaleTimeString()}</span>
                  <span>→ {c.target_lang}</span>
                </div>
                <div style={captionSrc}>{c.source}</div>
                <div style={captionDst}>{c.target}</div>
              </li>
            ))}
          </ul>
        )}
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

const btn: React.CSSProperties = {
  padding: '8px 14px',
  fontSize: 13,
  border: '1px solid #111',
  borderRadius: 4,
  cursor: 'pointer',
  background: '#fff',
}
const btnSave: React.CSSProperties = {
  ...btn,
  background: '#00b86f',
  color: '#fff',
  borderColor: '#00955a',
  fontWeight: 600,
}
const btnSecondary: React.CSSProperties = { ...btn }
const btnDanger: React.CSSProperties = {
  ...btn,
  background: '#fff',
  color: '#c62828',
  borderColor: '#c62828',
}

const captionList: React.CSSProperties = {
  listStyle: 'none',
  padding: 0,
  margin: 0,
  display: 'flex',
  flexDirection: 'column',
  gap: 8,
  maxHeight: 400,
  overflow: 'auto',
}
const captionItem: React.CSSProperties = {
  background: '#fff',
  border: '1px solid #e5e5e5',
  borderRadius: 6,
  padding: '8px 12px',
}
const captionHeader: React.CSSProperties = {
  display: 'flex',
  justifyContent: 'space-between',
  fontSize: 11,
  color: '#888',
  marginBottom: 4,
  fontFamily: 'monospace',
}
const captionSrc: React.CSSProperties = {
  fontSize: 14,
  color: '#555',
  marginBottom: 4,
}
const captionDst: React.CSSProperties = {
  fontSize: 15,
  color: '#111',
  fontWeight: 500,
}

export default App
