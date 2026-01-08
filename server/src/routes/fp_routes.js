import express from 'express';
import { getFiltresInicials, cercarOferta, getComarquesPerProvincia, getLocalitatsPerComarca, getLocalitatsPerProvincia } from '../controllers/fp_controller.js';

const router = express.Router();

// Aquesta ruta s'executarà quan carregue l'app de Flet
router.get('/filtres', getFiltresInicials);

// Aquesta quan l'usuari polse el botó de "Cercar"
router.post('/cercar', cercarOferta);


router.get('/comarques/:provincia', getComarquesPerProvincia);
router.get('/localitats/:comarca', getLocalitatsPerComarca);
router.get('/toteslocalitats/:provincia', getLocalitatsPerProvincia);

export default router;