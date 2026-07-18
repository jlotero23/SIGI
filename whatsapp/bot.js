/**
 * Bridge gratuito de WhatsApp usando whatsapp-web.js
 *
 * Flujo:
 * 1. Escanea el código QR con tu WhatsApp (como WhatsApp Web)
 * 2. Recibe mensajes entrantes
 * 3. Los reenvía al backend FastAPI (Agente 2)
 * 4. Responde al usuario con las recomendaciones
 *
 * Requisitos: Node.js 18+
 * Ejecutar: npm install && npm start
 */

import express from 'express'
import qrcode from 'qrcode-terminal'
import whatsappWeb from 'whatsapp-web.js'

const { Client, LocalAuth } = whatsappWeb
const API_URL = process.env.API_URL || 'http://localhost:8000/api'

const app = express()
app.use(express.json())

let clientReady = false
let lastQr = null

const client = new Client({
  authStrategy: new LocalAuth({ dataPath: './.wwebjs_auth' }),
  puppeteer: {
    headless: true,
    args: ['--no-sandbox', '--disable-setuid-sandbox'],
  },
})

client.on('qr', (qr) => {
  lastQr = qr
  console.log('\n📱 Escanea este código QR con WhatsApp:\n')
  qrcode.generate(qr, { small: true })
})

client.on('ready', () => {
  clientReady = true
  lastQr = null
  console.log('✅ WhatsApp conectado. El Agente 2 está listo para responder.')
})

client.on('message', async (msg) => {
  // Ignorar mensajes de grupos y propios
  if (msg.from.includes('@g.us') || msg.fromMe) return

  const text = msg.body?.trim()
  if (!text) return

  console.log(`📩 Mensaje de ${msg.from}: ${text}`)

  try {
    const res = await fetch(`${API_URL}/whatsapp/query`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ from_number: msg.from, message: text }),
    })
    const data = await res.json()
    await msg.reply(data.reply || 'Sin respuesta del sistema.')
  } catch (err) {
    console.error('Error consultando API:', err.message)
    await msg.reply(
      '⚠️ No pude conectar con el sistema. Verifique que el backend esté ejecutándose en el puerto 8000.',
    )
  }
})

client.initialize()

// Endpoint de estado para el dashboard
app.get('/status', (_req, res) => {
  res.json({ connected: clientReady, has_qr: !!lastQr })
})

app.listen(3001, () => {
  console.log('🌐 Bridge WhatsApp escuchando en http://localhost:3001')
})
