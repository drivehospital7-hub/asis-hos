#!/bin/bash
# Configurar PostgreSQL para acceso desde Windows/WSL

# Cambio 1: Configurar listen_addresses = '*'
sudo sed -i "s/#listen_addresses = 'localhost'/listen_addresses = '*'/" /etc/postgresql/16/main/postgresql.conf

# Cambio 2: Agregar regla en pg_hba.conf para red WSL
echo "host    all             all             172.25.0.0/16           scram-sha-256" | sudo tee -a /etc/postgresql/16/main/pg_hba.conf

# Reiniciar PostgreSQL
sudo systemctl restart postgresql

# Verificar estado
sudo systemctl status postgresql