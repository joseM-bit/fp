import express from 'express';
import { getModels, invokeNova, invokeAgent } from '../controllers/aws_controller.js';

const router = express.Router();

router.get('/models', getModels);
router.post('/nova', invokeNova);
router.post('/agent', invokeAgent);

export default router;