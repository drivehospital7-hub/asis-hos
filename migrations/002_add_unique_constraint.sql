-- Agregar constraint unique compuesto a eps_contratado
-- Unique: (cod_contrato, eps, regimen)

ALTER TABLE eps_contratado 
ADD CONSTRAINT uq_eps_contratado_cod_eps_regimen UNIQUE (cod_contrato, eps, regimen);