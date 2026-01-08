// sockets/socketHandler.js
import { Server } from 'socket.io';
import dbModule from '../database/db.js';

const { db, query } = dbModule;

let io;

function init(server) {
  io = new Server(server, {
    cors: {
      origin: "*", // Permitir conexiones desde cualquier origen (Hay que ajústarlo en producción)
      methods: ['GET', 'POST', 'PUT'],
    },
  });

  io.on("connection", (socket) => {
    //console.log("📱 Nuevo cliente conectado:", socket.id);

    // Escuchar el evento de envío de mensaje
    socket.on("sendMessage", async (message) => {

      try {
        // Si message es un string en lugar de un objeto, lo parseamos
        if (typeof message === "string") {
          message = JSON.parse(message);
          //console.log("MENSAJE CONVERTIDO A JSON:", message);
        }
      } catch (error) {
        //console.error("Error al convertir mensaje a JSON:", error);
        return;
      }

      // Validar los datos recibidos
      if (
        typeof message.chatid !== "number" ||
        typeof message.rolemisor !== "string" ||
        typeof message.mensaje !== "string" ||
        typeof message.visto !== "boolean"
      ) {
        //console.error("Error: Mensaje con datos incorrectos:", message);
        return;
      }

      // Insertar el mensaje en la base de datos
      db.query(
        'INSERT INTO mensajes (chatid, rolemisor, mensaje, visto) VALUES (?, ?, ?, ?)',
        [message.chatid, message.rolemisor, message.mensaje, message.visto],
        async (err, result) => {
          if (err) {
            //console.error("Error al guardar en la BD:", err);
            return;
          }

          //console.log("Mensaje guardado con ID:", result.insertId);

          try {
            // Recuperar el mensaje recién insertado
            const rows = await query('SELECT * FROM mensajes WHERE mensajeid = ?', [result.insertId]);

            if (!rows || rows.length === 0) {
              //console.error("No se encontró ningún mensaje con mensajeid:", result.insertId);
              return;
            }

            const newMessage = rows[0];
            //console.log("Emitiendo evento receiveMessage con datos:", newMessage);

            // Emitir el evento a todos los clientes conectados
            io.emit('receiveMessage', newMessage);
          } catch (error) {
            //console.error("Error al recuperar el mensaje:", error);
          }
        }
      );
    });

    // Manejar desconexión
    socket.on("disconnect", () => {
      //console.log("Cliente desconectado:", socket.id);
    });
  });

  return io;
}

export { init };