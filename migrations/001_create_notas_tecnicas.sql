-- Schema: Asis-Hos Notas Técnicas
-- Created: 2026-04-15

-- Table: eps_contratado
CREATE TABLE eps_contratado (
    id SERIAL PRIMARY KEY,
    cod_contrato TEXT NOT NULL UNIQUE,
    eps TEXT NOT NULL,
    regimen TEXT NOT NULL DEFAULT 'SUBSIDIADO'
);

CREATE INDEX idx_eps_contratado_cod_contrato ON eps_contratado(cod_contrato);
CREATE INDEX idx_eps_contratado_eps ON eps_contratado(eps);

-- Table: procedimiento
CREATE TABLE procedimiento (
    id SERIAL PRIMARY KEY,
    cups TEXT NOT NULL UNIQUE,
    procedimiento TEXT NOT NULL
);

CREATE INDEX idx_procedimiento_cups ON procedimiento(cups);
CREATE INDEX idx_procedimiento_nombre ON procedimiento(procedimiento);

-- Table: nota_hoja
CREATE TABLE nota_hoja (
    id SERIAL PRIMARY KEY,
    nota TEXT NOT NULL
);

CREATE INDEX idx_nota_hoja_nota ON nota_hoja(nota);

-- Table: notas_tecnicas
CREATE TABLE notas_tecnicas (
    id SERIAL PRIMARY KEY,
    id_procedimiento INTEGER NOT NULL,
    id_nota_hoja INTEGER NOT NULL,
    tariff NUMERIC(12, 2) NOT NULL,
    CONSTRAINT fk_notas_tecnicas_id_procedimiento_procedimiento_nota
        FOREIGN KEY (id_procedimiento) REFERENCES procedimiento(id)
        ON DELETE NO ACTION ON UPDATE NO ACTION,
    CONSTRAINT fk_notas_tecnicas_id_nota_hoja_nota_hoja
        FOREIGN KEY (id_nota_hoja) REFERENCES nota_hoja(id)
        ON DELETE NO ACTION ON UPDATE NO ACTION
);

CREATE INDEX idx_notas_tecnicas_id_procedimiento ON notas_tecnicas(id_procedimiento);
CREATE INDEX idx_notas_tecnicas_id_nota_hoja ON notas_tecnicas(id_nota_hoja);

-- Table: eps_nota
CREATE TABLE eps_nota (
    id SERIAL PRIMARY KEY,
    id_nota_hoja INTEGER NOT NULL,
    id_eps_contratado INTEGER NOT NULL,
    CONSTRAINT fk_eps_nota_id_eps_contratado_eps_contratado
        FOREIGN KEY (id_eps_contratado) REFERENCES eps_contratado(id)
        ON DELETE NO ACTION ON UPDATE NO ACTION,
    CONSTRAINT fk_eps_nota_id_nota_hoja_nota_hoja
        FOREIGN KEY (id_nota_hoja) REFERENCES nota_hoja(id)
        ON DELETE NO ACTION ON UPDATE NO ACTION
);

CREATE INDEX idx_eps_nota_id_nota_hoja ON eps_nota(id_nota_hoja);
CREATE INDEX idx_eps_nota_id_eps_contratado ON eps_nota(id_eps_contratado);