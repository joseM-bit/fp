import express from 'express';
import cors from 'cors';
import routes from './routes/aws_routes.js';
import fpRoutes from './routes/fp_routes.js';

const app = express();

// Habilitar CORS
app.use(cors());

// Middleware per parsejar JSON
app.use(express.json());

// Us de les rutas
app.use('/api/bedrock', routes);
app.use('/api/fp', fpRoutes);

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`Servidor corrent en http://localhost:${PORT}`);
    console.log(`Endpoints: /api/bedrock/models, /api/bedrock/nova, /api/bedrock/agent`);
});