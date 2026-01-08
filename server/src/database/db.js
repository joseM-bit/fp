import dotenv from 'dotenv';
import { createPool } from 'mysql2';

// Cargar variables de entorno
dotenv.config();

// Validar variables de entorno
if (!process.env.DB_HOST || !process.env.DB_USER || !process.env.DB_NAME || !process.env.DB_PORT) {
  console.error("Falten variables d'entorn crítiques en el .env");
  process.exit(1);
}

// Crear pool de conexiones
const db = createPool({
  host: process.env.DB_HOST,
  port: process.env.DB_PORT,
  user: process.env.DB_USER,
  password: process.env.DB_PASSWORD,
  database: process.env.DB_NAME,
  waitForConnections: true,
  connectionLimit: 10,
  queueLimit: 0,
});

// Verificar conexión inicial
db.getConnection((err, connection) => {
  if (err) {
    console.error('Error al conectar con la base de datos:', err);
    process.exit(1);
  }
  console.log('Conexión exitosa al pool de la base de datos');
  connection.release(); // Liberar la conexión
});

// Función para ejecutar consultas con promesas
const query = async (sql, params) => {
  try {
    const [rows] = await db.promise().query(sql, params);
    return rows || [];
  } catch (error) {
    return [];
  }
};

export default { db, query };