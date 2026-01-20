import db from '../database/db.js';

// Obtenir totes les titulacions de FP
export const getTotesTitulacionsFP = async (req, res) => {
    try {
        const sql = `
            SELECT id, nom_cicle, familia, grau 
            FROM titulacio 
            WHERE nom_cicle IS NOT NULL 
              AND grau NOT IN ('CE MEDIO', 'CE SUPERIOR')
            ORDER BY nom_cicle`;

        const [rows] = await db.db.promise().query(sql);

        res.json({ 
            success: true, 
            data: rows 
        });
    } catch (error) {
        console.error('Error a getTotesTitulacions:', error);
        res.status(500).json({ success: false, message: error.message });
    }
};

// Obtenir totes les titulacions de CE
export const getTotesTitulacionsCE = async (req, res) => {
    try {
        const sql = `
            SELECT id, nom_cicle, familia, grau 
            FROM titulacio 
            WHERE nom_cicle IS NOT NULL 
              AND grau IN ('CE MEDIO', 'CE SUPERIOR')
            ORDER BY nom_cicle`;

        const [rows] = await db.db.promise().query(sql);

        res.json({ 
            success: true, 
            data: rows 
        });
    } catch (error) {
        console.error('Error a getTotesTitulacions:', error);
        res.status(500).json({ success: false, message: error.message });
    }
};

// Obtenir titulacions amb tots els filtres
export const getCiclesFiltrats = async (req, res) => {
    const { provincia, comarca, localitat, familia, grau } = req.body;

    // Base de la consulta: volem les titulacions uniques
    let sql = `
        SELECT DISTINCT t.id, t.nom_cicle, t.familia, t.grau
        FROM titulacio t
        JOIN oferta o ON t.id = o.id_titulacio
        JOIN centre c ON o.codcen = c.codi
        WHERE t.grau NOT IN ('CE MEDIO', 'CE SUPERIOR')`;

    const params = [];

    // Filtre de Provincia
    if (provincia && provincia !== "---NINGUNA---") {
        sql += " AND c.provincia = ?";
        params.push(provincia);
    }
    // Filtre de Comarca
    if (comarca && comarca !== "---NINGUNA---") {
        sql += " AND c.comarca = ?";
        params.push(comarca);
    }
    // Filtre de Localitat
    if (localitat && localitat !== "---NINGUNA---") {
        sql += " AND c.localitat = ?";
        params.push(localitat);
    }
    // Filtre de Familia
    if (familia && familia !== "---NINGUNA---") {
        sql += " AND t.familia = ?";
        params.push(familia);
    }
    // Filtre de Grau
    if (grau && grau !== "---NINGÚN---") {
        sql += " AND t.grau = ?";
        params.push(grau);
    }

    sql += " ORDER BY t.nom_cicle ASC";

    try {
        const [rows] = await db.db.promise().query(sql, params);
        res.json({ success: true, data: rows });
    } catch (error) {
        res.status(500).json({ success: false, message: error.message });
    }
};

// Obtenir titulacions amb tots els filtres
export const getCursosFiltrats = async (req, res) => {
    const { provincia, comarca, localitat, familia, grau } = req.body;

    // Base de la consulta: volem les titulacions uniques
    let sql = `
        SELECT DISTINCT t.id, t.nom_cicle, t.familia, t.grau
        FROM titulacio t
        JOIN oferta o ON t.id = o.id_titulacio
        JOIN centre c ON o.codcen = c.codi
        WHERE t.grau IN ('CE MEDIO', 'CE SUPERIOR')`;

    const params = [];

    // Filtre de Provincia
    if (provincia && provincia !== "---NINGUNA---") {
        sql += " AND c.provincia = ?";
        params.push(provincia);
    }
    // Filtre de Comarca
    if (comarca && comarca !== "---NINGUNA---") {
        sql += " AND c.comarca = ?";
        params.push(comarca);
    }
    // Filtre de Localitat
    if (localitat && localitat !== "---NINGUNA---") {
        sql += " AND c.localitat = ?";
        params.push(localitat);
    }
    // Filtre de Familia
    if (familia && familia !== "---NINGUNA---") {
        sql += " AND t.familia = ?";
        params.push(familia);
    }
    // Filtre de Grau
    if (grau && grau !== "---NINGÚN---") {
        sql += " AND t.grau = ?";
        params.push(grau);
    }

    sql += " ORDER BY t.nom_cicle ASC";

    try {
        const [rows] = await db.db.promise().query(sql, params);
        res.json({ success: true, data: rows });
    } catch (error) {
        res.status(500).json({ success: false, message: error.message });
    }
};