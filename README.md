# Control System

Sistema de Control de Facturación Médica para EPS MALLAMAS (indígena).

## Qué hace

Procesa archivos Excel de facturas médicas (principalmente odontología):

- **Cruce de facturas**: Ok / Pendientes / PDFs
- **Validaciones automáticas**: decimales, duplicados, convenios incorrectos, cantidades anómalas
- **Formato condicional**: colores para detección visual de problemas
- **Hoja de revisión**: facturas con problemas agrupadas por tipo

## Stack

| Componente | Tecnología |
|------------|------------|
| Framework | Flask |
| Procesamiento | Polars (motor calamine/fastexcel) |
| Escritura Excel | openpyxl |
| Servidor prod | waitress |
| Config | python-dotenv |

## Estructura

```
control_system/
├── app/
│   ├── routes/       # Endpoints HTTP
│   ├── services/     # Lógica de negocio
│   ├── utils/        # Helpers
│   └── data/
│       ├── input/    # Excel de entrada
│       └── output/   # Excel procesados
├── config/           # Configuraciones dev/prod
├── tests/            # pytest
└── logs/             # Logs por nivel
```

## Instalación

```bash
# Clonar repositorio
git clone <repo-url>
cd control_system

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# Instalar dependencias
pip install -r requirements.txt

# Crear directorio de logs (requerido)
mkdir -p logs
```

## Uso

### Desarrollo

```bash
source venv/bin/activate
python run_dev.py
```

Servidor en: `http://127.0.0.1:5000`

### Producción

```bash
python run_prod.py
```

Servidor en: `http://0.0.0.0:8080`

## Endpoints

| Endpoint | Método | Descripción |
|----------|--------|-------------|
| `/` | GET | Health check |
| `/excel/headers` | POST | Lee headers de archivo Excel |

## Archivos de entrada

Colocar archivos Excel en `app/data/input/`.

Formatos soportados: `.xlsx`, `.xls`, `.xlsm`, `.xlsb`

## Documentación

- `CONVENTIONS.md` — Convenciones del proyecto (fuente de verdad)
- `AGENTS.md` — Instrucciones para agentes IA
- `.atl/skill-registry.md` — Skills disponibles

## Desarrollo

### Tests

```bash
pytest -v
```

### Convenciones

- Routes solo delegan a servicios
- Servicios tienen una sola responsabilidad
- Response format: `{"status": "success|error", "data": {}, "errors": []}`
- Funciones < 50 líneas

Ver `CONVENTIONS.md` para detalle completo.

## Estado del Proyecto

- ✅ Procesamiento de facturas funcionando
- ✅ Validaciones de negocio implementadas
- ✅ Refactor de módulos completado (exporter, cruce_sheet, revision_sheet, formatting, column_filter)
- ⚠️ Tests de nuevos módulos pendientes

---

*Sistema interno para EPS MALLAMAS*
