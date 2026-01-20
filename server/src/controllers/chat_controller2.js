import normalitzador from '../services/normalitzador.js';
import {interpretarPregunta} from '../services/gemini_ai_service.js'
import {getCentresPerCicleOFamilia} from './fp_controller.js';

export const handleChat = async (req, res) => {
    try {
        const { message } = req.body;
        const aiOutput = await interpretarPregunta(message);
        const paramsNets = normalitzador.normalitzar(aiOutput.params);

        let dadesFinals;

        // Simulem l'objecte 'res' d'Express
        const resSimulat = {
            // Simulem la funció .json() per capturar les dades en la nostra variable
            json: (contingut) => {
                dadesFinals = contingut;
            },
            // Simulem .status() per si hi haguera un error (encara que no l'usarem molt ací)
            status: function(codi) {
                return this; 
            }
        };

        
        // Cridem a la funció passant el body simulat i el res simulat
        await getCentresPerCicleOFamilia({ body: paramsNets }, resSimulat);

        // Ara enviem la resposta real a l'aplicació
        res.json({
            success: true,
            data: dadesFinals.data || [],
            // Si dadesFinals.message no existeix, intenta agafar dadesFinals.msg o posa null
            message: dadesFinals.message || dadesFinals.msg || null, 
            params_aplicats: paramsNets
        });

    } catch (error) {
        console.error("Error en el xat:", error);
        res.status(500).json({ success: false, error: error.message });
    }
};