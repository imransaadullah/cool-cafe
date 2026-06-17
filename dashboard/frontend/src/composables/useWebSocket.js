import { ref, onMounted, onUnmounted } from 'vue'

export function useWebSocket(url) {
  const isConnected = ref(false)
  const lastMessage = ref(null)
  const messages = ref([])
  
  let ws = null
  let reconnectTimer = null
  let heartbeatTimer = null
  
  const connect = () => {
    try {
      ws = new WebSocket(url)
      
      ws.onopen = () => {
        isConnected.value = true
        console.log('WebSocket connected')
        send({ type: 'dashboard_register' })
        startHeartbeat()
      }
      
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data)
        lastMessage.value = data
        messages.value.push(data)
        
        // Keep only last 100 messages
        if (messages.value.length > 100) {
          messages.value.shift()
        }
      }
      
      ws.onclose = () => {
        isConnected.value = false
        stopHeartbeat()
        console.log('WebSocket disconnected, reconnecting...')
        reconnectTimer = setTimeout(connect, 5000)
      }
      
      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
      }
    } catch (error) {
      console.error('WebSocket connection failed:', error)
      reconnectTimer = setTimeout(connect, 5000)
    }
  }
  
  const disconnect = () => {
    if (reconnectTimer) {
      clearTimeout(reconnectTimer)
    }
    stopHeartbeat()
    if (ws) {
      ws.close()
    }
  }
  
  const send = (data) => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(data))
    }
  }
  
  const subscribeToPC = (pcId) => {
    send({ type: 'subscribe_pc', pc_id: pcId })
  }
  
  const startHeartbeat = () => {
    heartbeatTimer = setInterval(() => {
      send({ type: 'ping' })
    }, 30000)
  }
  
  const stopHeartbeat = () => {
    if (heartbeatTimer) {
      clearInterval(heartbeatTimer)
    }
  }
  
  onMounted(() => {
    connect()
  })
  
  onUnmounted(() => {
    disconnect()
  })
  
  return {
    isConnected,
    lastMessage,
    messages,
    connect,
    disconnect,
    send,
    subscribeToPC,
  }
}
