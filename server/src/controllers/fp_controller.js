import db from '../database/db.js';

// Obtenir les opcions per als dropdowns de la interfície al inici
export const getFiltresInicials = async (req, res) => {
    try {
        // Fem les consultes per separat per omplir cada desplegable
        const [provincies] = await db.db.promise().query('SELECT DISTINCT provincia FROM centre WHERE provincia IS NOT NULL ORDER BY provincia');
        const [comarques] = await db.db.promise().query('SELECT DISTINCT comarca FROM centre WHERE comarca IS NOT NULL ORDER BY comarca');
        const [localitats] = await db.db.promise().query('SELECT DISTINCT localitat FROM centre WHERE localitat IS NOT NULL ORDER BY localitat');
        const [graus] = await db.db.promise().query('SELECT DISTINCT grau FROM titulacio WHERE grau IS NOT NULL ORDER BY grau');

        res.json({
            success: true,
            data: {
                provincies: provincies.map(p => p.provincia),
                comarques: comarques.map(c => c.comarca),
                localitats: localitats.map(l => l.localitat),
                graus: graus.map(g => g.grau)
            }
        });
    } catch (error) {
        console.error('Error carregant filtres:', error);
        res.status(500).json({ success: false, message: 'Error al carregar els filtres' });
    }
};

// Cercar oferta de FP segons els filtres seleccionats
export const cercarOferta = async (req, res) => {
    // Extraiem els nous filtres del cos de la petició
    const { provincia, comarca, localitat, grau } = req.body;

    let sql = `
        SELECT c.nom AS centre, c.localitat, c.comarca, c.provincia, t.nom_cicle, t.grau
        FROM oferta o
        JOIN centre c ON o.codcen = c.codi
        JOIN titulacio t ON o.id_titulacio = t.id
        WHERE 1=1`;
    
    const params = [];

    // Filtre de Província
    if (provincia) {
        sql += " AND c.provincia = ?";
        params.push(provincia);
    }
    // Filtre de Comarca
    if (comarca) {
        sql += " AND c.comarca = ?";
        params.push(comarca);
    }
    // Filtre de Localitat
    if (localitat) {
        sql += " AND c.localitat = ?";
        params.push(localitat);
    }
    // Filtre de Grau
    if (grau) {
        sql += " AND t.grau = ?";
        params.push(grau);
    }

    sql += " ORDER BY c.nom ASC LIMIT 100";

    try {
        const resultats = await db.query(sql, params);
        res.json({ success: true, data: resultats });
    } catch (error) {
        console.error('Error en la cerca:', error);
        res.status(500).json({ success: false, message: error.message });
    }
};

// Obtenir comarques filtrades per província
export const getComarquesPerProvincia = async (req, res) => {
    const { provincia } = req.params;
    try {
        const [rows] = await db.db.promise().query(
            'SELECT DISTINCT comarca FROM centre WHERE provincia = ? AND comarca IS NOT NULL ORDER BY comarca',
            [provincia]
        );
        res.json({ success: true, data: rows.map(r => r.comarca) });
    } catch (error) {
        res.status(500).json({ success: false, message: error.message });
    }
};

// Obtenir comarques filtrades per província
export const getLocalitatsPerComarca = async (req, res) => {
    const { comarca } = req.params;
    try {
        const [rows] = await db.db.promise().query(
            'SELECT DISTINCT localitat FROM centre WHERE comarca = ? AND localitat IS NOT NULL ORDER BY localitat',
            [comarca]
        );
        res.json({ success: true, data: rows.map(l => l.localitat) });
    } catch (error) {
        res.status(500).json({ success: false, message: error.message });
    }
};

// Obtenir titulacions filtrades per grau
export const getTitulacionsPerGrau = async (req, res) => {
    const { grau } = req.params;
    try {
        const [rows] = await db.db.promise().query(
            'SELECT DISTINCT nom_cicle FROM titulacio WHERE grau = ? AND nom_cicle IS NOT NULL ORDER BY nom_cicle',
            [grau]
        );
        res.json({ success: true, data: rows.map(r => r.nom_cicle) });
    } catch (error) {
        res.status(500).json({ success: false, message: error.message });
    }
};