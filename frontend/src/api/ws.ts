import { getSessionToken } from './client'
import type { HaltCommand, ServerEvent } from './types'

// The caller fetches /halts/pending and history after every connection/reconnection.
export function connectEvents(
  onEvent: (event: ServerEvent) => void,
  onConnected?: () => void,
): { close: () => void; decide: (command: HaltCommand['data']) => void } {
  let socket: WebSocket | undefined
  let retry: ReturnType<typeof setTimeout> | undefined
  let stopped = false
  let delay = 500

  const open = () => {
    if (stopped) return
    const token = getSessionToken()
    if (!token) throw new Error('Missing SentriFlow session token')
    const scheme = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    socket = new WebSocket(`${scheme}//${window.location.host}/ws`, ['sentriflow', token])
    socket.onopen = () => {
      delay = 500
      onConnected?.()
    }
    socket.onmessage = (event: MessageEvent<string>) => {
      onEvent(JSON.parse(event.data) as ServerEvent)
    }
    socket.onclose = (event) => {
      // Invalid sessions need the new launch URL, not an endless reconnect loop.
      if (stopped || event.code === 1008) return
      retry = setTimeout(open, delay)
      delay = Math.min(delay * 2, 10_000)
    }
  }
  open()
  return {
    close: () => {
      stopped = true
      clearTimeout(retry)
      socket?.close()
    },
    decide: (data) => {
      if (socket?.readyState !== WebSocket.OPEN) throw new Error('SentriFlow is disconnected')
      const command: HaltCommand = { type: 'halt.decide', data }
      socket.send(JSON.stringify(command))
    },
  }
}
