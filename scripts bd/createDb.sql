CREATE DATABASE IF NOT EXISTS fpdb;
USE fpdb;


CREATE TABLE centre (
    codi INT PRIMARY KEY,
    nom VARCHAR(255) NOT NULL,
    descripcio VARCHAR(255),
    titular VARCHAR(255),
    provincia VARCHAR(50),
    comarca VARCHAR(255),
    localitat VARCHAR(255),
    direccio VARCHAR(255),
    telefon VARCHAR(20),
    correu VARCHAR(100),
    web VARCHAR(100),
    latitud DECIMAL(10, 8),
    longitud DECIMAL(11, 8)
);


CREATE TABLE titulacio (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nom_cicle VARCHAR(255) NOT NULL,
    familia VARCHAR(255),
    grau VARCHAR(50),
    UNIQUE KEY (nom_cicle, familia, grau)
);


CREATE TABLE oferta (
    codcen INT,
    id_titulacio INT,
    regim_formatiu VARCHAR(100),
    torn VARCHAR(50),
    PRIMARY KEY (codcen, id_titulacio, torn),
    FOREIGN KEY (codcen) REFERENCES centre(codi) ON DELETE CASCADE,
    FOREIGN KEY (id_titulacio) REFERENCES titulacio(id) ON DELETE CASCADE
);


