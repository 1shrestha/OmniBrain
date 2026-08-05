import express from 'express';
import path from 'path';
import multer from 'multer';
import { createServer as createViteServer } from 'vite';
import { GoogleGenAI, Modality } from '@google/genai';
import { db } from './server/db.js';
import { processDocumentUpload } from './server/documentProcessor.js';
import { executeRAGPipeline } from './server/rag.js';

const upload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: 25 * 1024 * 1024 } // 25 MB max per document
});

async function startServer() {
  const app = express();
  const PORT = 3000;

  app.use(express.json({ limit: '50mb' }));

  // API ROUTE HANDLERS
  
  // Health check
  app.get('/api/health', (req, res) => {
    res.json({ status: 'ok', app: 'OmniBrain', timestamp: new Date().toISOString() });
  });

  // Get uploaded documents
  app.get('/api/documents', (req, res) => {
    const docs = Array.from(db.documents.values());
    res.json({ success: true, documents: docs });
  });

  // Upload document
  app.post('/api/upload', upload.single('file'), async (req, res) => {
    try {
      if (!req.file) {
        res.status(400).json({ success: false, error: 'No file provided in form data' });
        return;
      }
      const processedDoc = await processDocumentUpload({
        originalname: req.file.originalname,
        buffer: req.file.buffer,
        mimetype: req.file.mimetype
      });
      res.json({ success: true, document: processedDoc });
    } catch (err: any) {
      console.error('Document upload error:', err);
      res.status(500).json({ success: false, error: err.message || 'Failed to process document' });
    }
  });

  // Delete document
  app.delete('/api/documents/:id', (req, res) => {
    const docId = req.params.id;
    const deletedDoc = db.documents.delete(docId);
    db.chunks.delete(docId);
    res.json({ success: true, deletedDoc });
  });

  // Rename document
  app.post('/api/documents/rename', (req, res) => {
    const { id, newName } = req.body;
    const doc = db.documents.get(id);
    if (doc) {
      doc.name = newName;
      db.documents.set(id, doc);
      res.json({ success: true, document: doc });
    } else {
      res.status(404).json({ success: false, error: 'Document not found' });
    }
  });

  // Get chunks for a specific document (for preview/chunks visualizer)
  app.get('/api/documents/:id/chunks', (req, res) => {
    const chunks = db.chunks.get(req.params.id) || [];
    res.json({ success: true, chunks });
  });

  // Chat Execution endpoint
  app.post('/api/chat', async (req, res) => {
    try {
      const { conversationId, query, filterDocIds } = req.body;
      if (!query || typeof query !== 'string') {
        res.status(400).json({ success: false, error: 'Query string is required' });
        return;
      }

      // Find or create conversation
      let conv = db.conversations.get(conversationId);
      if (!conv) {
        const newConvId = conversationId || 'conv-' + Date.now();
        conv = {
          id: newConvId,
          title: query.length > 30 ? query.substring(0, 30) + '...' : query,
          createdAt: new Date().toISOString(),
          updatedAt: new Date().toISOString(),
          messages: [],
          docIds: filterDocIds || []
        };
        db.conversations.set(newConvId, conv);
      }

      // Append user message
      const userMsg = {
        id: 'msg-usr-' + Date.now(),
        sender: 'user' as const,
        text: query,
        timestamp: new Date().toISOString()
      };
      conv.messages.push(userMsg);

      // Execute RAG Pipeline with LangGraph reasoning steps
      const result = await executeRAGPipeline(query, filterDocIds || [], conv.messages);

      // Append AI message
      const aiMsg = {
        id: 'msg-ai-' + Date.now(),
        sender: 'ai' as const,
        text: result.replyText,
        timestamp: new Date().toISOString(),
        reasoningSteps: result.graphSteps,
        citations: result.citations,
        retrievedChunks: result.retrievedChunks,
        confidenceScore: result.confidenceScore,
        suggestedFollowUps: result.suggestedFollowUps,
        docIdsUsed: filterDocIds
      };
      conv.messages.push(aiMsg);
      conv.updatedAt = new Date().toISOString();
      db.conversations.set(conv.id, conv);

      res.json({
        success: true,
        conversationId: conv.id,
        userMessage: userMsg,
        aiMessage: aiMsg
      });
    } catch (err: any) {
      console.error('Chat API Error:', err);
      res.status(500).json({ success: false, error: err.message || 'Error executing RAG pipeline' });
    }
  });

  // Semantic search endpoint across chunks
  app.post('/api/search', async (req, res) => {
    const { query, docId } = req.body;
    let chunks: any[] = [];
    if (docId) {
      chunks = db.chunks.get(docId) || [];
    } else {
      db.chunks.forEach(c => chunks.push(...c));
    }
    
    const queryLower = (query || '').toLowerCase();
    const results = chunks.filter(c => c.text.toLowerCase().includes(queryLower) || queryLower.length < 2)
      .slice(0, 10);

    res.json({ success: true, results });
  });

  // Conversations API
  app.get('/api/conversations', (req, res) => {
    const convs = Array.from(db.conversations.values()).sort(
      (a, b) => new Date(b.updatedAt).getTime() - new Date(a.updatedAt).getTime()
    );
    res.json({ success: true, conversations: convs });
  });

  app.get('/api/conversations/:id', (req, res) => {
    const conv = db.conversations.get(req.params.id);
    if (conv) {
      res.json({ success: true, conversation: conv });
    } else {
      res.status(404).json({ success: false, error: 'Conversation not found' });
    }
  });

  app.post('/api/conversations', (req, res) => {
    const { title } = req.body;
    const newId = 'conv-' + Date.now();
    const newConv = {
      id: newId,
      title: title || 'New Conversation',
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
      messages: [],
      docIds: []
    };
    db.conversations.set(newId, newConv);
    res.json({ success: true, conversation: newConv });
  });

  app.delete('/api/conversations/:id', (req, res) => {
    const deleted = db.conversations.delete(req.params.id);
    res.json({ success: true, deleted });
  });

  // Analytics API
  app.get('/api/analytics', (req, res) => {
    const stats = db.getAnalytics();
    res.json({ success: true, analytics: stats });
  });

  // Settings API
  app.get('/api/settings', (req, res) => {
    res.json({ success: true, settings: db.settings });
  });

  app.post('/api/settings', (req, res) => {
    db.settings = { ...db.settings, ...req.body };
    res.json({ success: true, settings: db.settings });
  });

  // TTS Speech generation route
  app.post('/api/speech', async (req, res) => {
    const { text } = req.body;
    if (!text) {
      res.status(400).json({ success: false, error: 'Text is required for TTS' });
      return;
    }

    if (process.env.GEMINI_API_KEY) {
      try {
        const ai = new GoogleGenAI({
          apiKey: process.env.GEMINI_API_KEY,
          httpOptions: { headers: { 'User-Agent': 'aistudio-build' } }
        });

        const ttsResponse = await ai.models.generateContent({
          model: 'gemini-3.1-flash-tts-preview',
          contents: [{ parts: [{ text: text.substring(0, 300) }] }],
          config: {
            responseModalities: [Modality.AUDIO],
            speechConfig: {
              voiceConfig: { prebuiltVoiceConfig: { voiceName: 'Zephyr' } }
            }
          }
        });

        const base64Audio = ttsResponse.candidates?.[0]?.content?.parts?.[0]?.inlineData?.data;
        if (base64Audio) {
          res.json({ success: true, audioBase64: base64Audio });
          return;
        }
      } catch (err) {
        console.warn('TTS model fallback:', err);
      }
    }
    res.json({ success: false, message: 'TTS API not available or key missing' });
  });

  // Vite Middleware Setup
  if (process.env.NODE_ENV !== 'production') {
    const vite = await createViteServer({
      server: { middlewareMode: true },
      appType: 'spa',
    });
    app.use(vite.middlewares);
  } else {
    const distPath = path.join(process.cwd(), 'dist');
    app.use(express.static(distPath));
    app.get('*', (req, res) => {
      res.sendFile(path.join(distPath, 'index.html'));
    });
  }

  app.listen(PORT, '0.0.0.0', () => {
    console.log(`[OmniBrain] Full-Stack RAG Server listening on http://0.0.0.0:${PORT}`);
  });
}

startServer();
