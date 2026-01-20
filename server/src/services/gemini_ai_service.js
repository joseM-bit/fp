import { GoogleGenerativeAI } from "@google/generative-ai";
import dotenv from 'dotenv';

dotenv.config();

const genAI = new GoogleGenerativeAI(process.env.GEMINI_API_KEY);

const systemPrompt = `Extreu paràmetres de FP Valenciana en JSON pur.

    Params: nom_cicle, familia, provincia, comarca, localitat, grau (BÁSICO 2a Oport., BÁSICO, MEDIO, SUPERIOR, CE MEDIO, CE SUPERIOR).

    Exemples:
    "On fer DAW a Safor?"->{"params":{"nom_cicle":"DAW","comarca":"la Safor"}}
    "Cicles informàtica"->{"params":{"familia":"Informàtica"}}
    "Master IA"->{"params":{"nom_cicle":"IA","grau":"CE SUPERIOR"}}
    "Grau mitjà cuina"->{"params":{"familia":"Hostelería","grau":"MEDIO"}}`;

const model = genAI.getGenerativeModel({ 
    model: process.env.GEMINI_MODEL,
    systemInstruction: systemPrompt,
    generationConfig: {
        temperature: 0.7,
        responseMimeType: "application/json"}
});

export const interpretarPregunta = async (missatgeUsuari) => {
    try {
        const result = await model.generateContent({
            contents: [{ role: "user", parts: [{ text: missatgeUsuari }] }]
        });

        // Convertim el text de la IA directament a un objecte JS
        return JSON.parse(result.response.text());
    } catch (error) {
        console.error("Error Gemini:", error);
        throw new Error("No s'ha pogut interpretar la pregunta");
    }
};