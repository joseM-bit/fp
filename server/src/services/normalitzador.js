import Fuse from 'fuse.js';
import db from '../database/db.js';

class Normalitzador {
    constructor() {
        this.engines = {
            localitats: null,
            families: null,
            comarques: null
        };
    }

    async inicialitzar() {
        try {
            const [provs, coms, locs, fams, graus, cicles, centres] = await Promise.all([
                db.query('SELECT DISTINCT provincia AS nom FROM centre WHERE provincia IS NOT NULL'),
                db.query('SELECT DISTINCT comarca AS nom FROM centre WHERE comarca IS NOT NULL'),
                db.query('SELECT DISTINCT localitat AS nom FROM centre WHERE localitat IS NOT NULL'),
                db.query('SELECT DISTINCT familia AS nom FROM titulacio WHERE familia IS NOT NULL'),
                db.query('SELECT DISTINCT grau AS nom FROM titulacio WHERE grau IS NOT NULL'),
                db.query('SELECT DISTINCT nom_cicle AS nom FROM titulacio WHERE nom_cicle IS NOT NULL'),
                db.query('SELECT DISTINCT nom AS nom FROM centre WHERE nom IS NOT NULL')
            ]);

            const opts = { keys: ['nom'], threshold: 0.3 };

            this.engines.provincia = new Fuse(provs, opts);
            this.engines.comarca = new Fuse(coms, opts);
            this.engines.poblacio = new Fuse(locs, opts);
            this.engines.familia = new Fuse(fams, opts);
            this.engines.grau = new Fuse(graus, opts);
            this.engines.nom_cicle = new Fuse(cicles, opts);
            this.engines.nom = new Fuse(centres, opts);

            console.log("✅ Normalitzador llest amb dades de la BD");
        } catch (error) {
            console.error("❌ Error carregant dades de normalització:", error);
        }
    }

    normalitzar(params) {
        if (!params) return {};
        const n = { ...params };

        // Corregim cada camp si existeix en la resposta de Gemini
        Object.keys(this.engines).forEach(key => {
            if (n[key]) {
                const result = this.engines[key].search(n[key]);
                if (result.length > 0) n[key] = result[0].item.nom;
            }
        });

        return n;
    }
}

export default new Normalitzador();