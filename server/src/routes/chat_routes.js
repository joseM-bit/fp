import express from 'express';
import { handleChat } from '../controllers/chat_controller2.js';

const router = express.Router();

// Ruta del agent interpret 
router.post('/chat', handleChat);


export default router;