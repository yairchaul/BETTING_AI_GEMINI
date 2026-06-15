# Requirements Document

## Introduction

BETTING_AI es un sistema de análisis de apuestas deportivas (MLB, NBA, UFC, Fútbol) construido en Python + Streamlit. El punto de entrada es `main_vision_completo.py`, que importa código "vivo" desde los paquetes `motors/`, `scrapers/`, `visualizers/` y `utils/`.

El problema central que motiva este esfuerzo es que **los cambios autorizados sobre el código no se reflejan en la aplicación**. La causa raíz es la existencia de archivos duplicados: hay ~123 archivos `.py` sueltos en la raíz del proyecto cuyo nombre y propósito coinciden con módulos vivos dentro de los paquetes. Editar un duplicado de la raíz no afecta a la aplicación porque la aplicación importa la versión del paquete. El problema se agrava por cadenas de importación con *fallback* dentro de `motors/__init__.py` (por ejemplo `predictor_hr` → `hr_analyzer_v24_1`, y un `from motor_mlb import ...` que alcanza un archivo de la raíz), lo que hace que la versión efectivamente cargada sea ambigua.

Este documento define los requisitos para consolidar la arquitectura: eliminar/aislar duplicados, unificar motores por deporte a una sola implementación canónica, reorganizar la raíz, sincronizar la documentación de arquitectura y establecer una suite de pruebas ejecutable. El esfuerzo es de **reorganización y unicidad del código**; **no debe cambiar el comportamiento funcional** de la aplicación, y debe **preservar íntegramente la lógica de cálculo heurístico** conforme a las reglas de steering del proyecto.

## Glossary

- **Sistema_Consolidacion**: Conjunto de procesos y artefactos de este esfuerzo que reorganiza el código y elimina duplicación. Sujeto de la mayoría de los requisitos.
- **Modulo_Canonico**: Única implementación oficial de una funcionalidad (motor, scraper o visualizador) que la aplicación importa y ejecuta.
- **Modulo_Duplicado**: Archivo cuyo nombre o propósito coincide con un Modulo_Canonico y que no es importado por la aplicación en su flujo de ejecución efectivo.
- **Archivo_Raiz**: Cualquier archivo `.py` ubicado directamente en el directorio raíz del proyecto (`d:\ÚLTIMO\BETTING_AI`).
- **Paquete_Vivo**: Uno de los paquetes `motors/`, `scrapers/`, `visualizers/`, `utils/` desde los que la aplicación importa código en tiempo de ejecución.
- **Entrypoint**: El archivo `main_vision_completo.py`, punto de entrada de la aplicación Streamlit.
- **Cadena_Fallback**: Bloque `try/except ImportError` que importa un módulo alternativo cuando el preferido falla, definido principalmente en `motors/__init__.py`.
- **Funcion_Heuristica**: Función de cálculo matemático/estadístico de análisis (por ejemplo cálculo de HR, ponches, over/under, momentum, pilares UFC) cuyo comportamiento debe preservarse.
- **Manifiesto_Inventario**: Documento generado que clasifica cada Archivo_Raiz y cada módulo de los Paquete_Vivo como Canonico, Duplicado, Script de un solo uso, Test o Documentación.
- **Grafo_Importaciones**: Conjunto de relaciones de importación reales partiendo del Entrypoint, usado para determinar qué módulos son alcanzables (vivos) y cuáles no.
- **Modulo_Archivado**: Modulo_Duplicado o script obsoleto movido a una ubicación de archivo (por ejemplo `_deprecated/`) en lugar de eliminarse permanentemente.
- **Suite_Pruebas**: Conjunto ejecutable de pruebas automatizadas que verifica que la aplicación carga y que los flujos por deporte conservan su comportamiento.
- **Documentacion_Arquitectura**: Los archivos `ARQUITECTURA.md` y `ARCHITECTURE_V24.md`.
- **Base_Datos**: La base de datos SQLite ubicada en `data/betting_stats.db`.
- **Linea_Base_Comportamiento**: Conjunto de salidas registradas de las Funcion_Heuristica para entradas representativas, capturado antes de la consolidación y usado como referencia de equivalencia.

## Requirements

### Requirement 1: Inventario y clasificación de duplicados

**User Story:** Como desarrollador, quiero un inventario clasificado de todos los archivos del proyecto, para saber con certeza qué archivo es el canónico y cuál es duplicado antes de mover o archivar nada.

#### Acceptance Criteria

1. THE Sistema_Consolidacion SHALL generar un Manifiesto_Inventario que liste el 100% de los Archivo_Raiz y el 100% de los módulos dentro de los Paquete_Vivo, registrando una ruta relativa única por cada entrada.
2. THE Sistema_Consolidacion SHALL clasificar cada entrada del Manifiesto_Inventario en exactamente una de las categorías: Canonico, Duplicado, Script de un solo uso, Test o Documentación.
3. IF una entrada del Manifiesto_Inventario no puede clasificarse en ninguna categoría, THEN THE Sistema_Consolidacion SHALL marcarla como "No resuelta" y conservarla en el Manifiesto_Inventario sin descartarla.
4. THE Sistema_Consolidacion SHALL construir un Grafo_Importaciones partiendo del Entrypoint, recorriendo las importaciones directas y transitivas hasta agotar todos los módulos alcanzables, sin límite de profundidad.
5. WHEN un módulo es alcanzable en el Grafo_Importaciones, THE Sistema_Consolidacion SHALL marcar ese módulo como Modulo_Canonico en el Manifiesto_Inventario.
6. WHEN un Archivo_Raiz tiene un nombre de archivo idéntico a un Modulo_Canonico o comparte su objetivo declarado, y no es alcanzable en el Grafo_Importaciones, THE Sistema_Consolidacion SHALL marcar ese Archivo_Raiz como Modulo_Duplicado.
7. THE Manifiesto_Inventario SHALL registrar, para cada Modulo_Duplicado, la ruta del Modulo_Canonico equivalente.
8. IF un Modulo_Duplicado corresponde a más de un Modulo_Canonico candidato, THEN THE Sistema_Consolidacion SHALL registrar todas las rutas candidatas y marcar la entrada para revisión manual.

### Requirement 2: Unicidad de resolución de importaciones

**User Story:** Como desarrollador, quiero que cada funcionalidad se resuelva a un único módulo, para que al editar ese módulo el cambio siempre se refleje en la aplicación.

#### Acceptance Criteria

1. THE Sistema_Consolidacion SHALL garantizar que, para cada funcionalidad importada por el Entrypoint, exista exactamente un (1) Modulo_Canonico alcanzable en el Grafo_Importaciones.
2. THE Sistema_Consolidacion SHALL reemplazar cada Cadena_Fallback en `motors/__init__.py` por exactamente una (1) importación directa hacia el Modulo_Canonico correspondiente, sin dejar ninguna Cadena_Fallback remanente.
3. IF el Entrypoint o un Paquete_Vivo importa un módulo mediante una ruta que resuelve a un Archivo_Raiz, THEN THE Sistema_Consolidacion SHALL redirigir esa importación al Modulo_Canonico dentro del Paquete_Vivo.
4. WHEN la consolidación de importaciones finaliza, THE Sistema_Consolidacion SHALL verificar que ningún Archivo_Raiz clasificado como Modulo_Duplicado sea alcanzable en el Grafo_Importaciones.
5. IF un símbolo importado por el Entrypoint resuelve a cero o a más de un (1) Modulo_Canonico, THEN THE Sistema_Consolidacion SHALL detener la operación de consolidación.
6. WHEN la operación de consolidación se detiene por un símbolo que no resuelve a un único Modulo_Canonico, THE Sistema_Consolidacion SHALL reportar el identificador de cada símbolo no resuelto y conservar sin modificaciones el estado previo de todos los archivos afectados.

### Requirement 3: Consolidación de motores por deporte

**User Story:** Como desarrollador, quiero una sola implementación canónica de motor por cada función de cada deporte, para eliminar la ambigüedad entre versiones múltiples del mismo motor.

#### Acceptance Criteria

1. THE Sistema_Consolidacion SHALL designar exactamente un (1) Modulo_Canonico por cada combinación única de función de motor y deporte (por ejemplo HR, ponches, over/under, momentum, decisión MLB; over/under NBA; pilares UFC; jerárquico Fútbol).
2. WHEN existan múltiples implementaciones de la misma función de motor (por ejemplo `predictor_hr.py`, `predictor_hr_pro.py`, `predictor_hr_v5.py`, `predictor_hr_corregido.py`, `hr_analyzer_v24_1.py`) y exactamente una sea alcanzable desde el Entrypoint mediante importación directa o transitiva, THE Sistema_Consolidacion SHALL seleccionarla como Modulo_Canonico y registrar en el Manifiesto_Inventario su ruta y la justificación de la selección.
3. IF más de una implementación de la misma función de motor es alcanzable desde el Entrypoint, THEN THE Sistema_Consolidacion SHALL abstenerse de auto-seleccionar y reportar el conflicto para resolución manual.
4. IF ninguna implementación de una función de motor es alcanzable desde el Entrypoint, THEN THE Sistema_Consolidacion SHALL abstenerse de archivar y registrar la ausencia en el Manifiesto_Inventario, solicitando una selección manual.
5. WHEN un Modulo_Canonico ha sido designado para una función de motor, THE Sistema_Consolidacion SHALL archivar las implementaciones no seleccionadas como Modulo_Archivado y registrar sus rutas en el Manifiesto_Inventario.
6. WHERE una implementación no seleccionada contiene una Funcion_Heuristica ausente del Modulo_Canonico, THE Sistema_Consolidacion SHALL reportar la ruta y el nombre de esa Funcion_Heuristica al usuario y conservar el módulo sin modificación hasta recibir autorización.
7. IF el usuario no autoriza el archivo de una implementación que contiene una Funcion_Heuristica ausente del Modulo_Canonico, THEN THE Sistema_Consolidacion SHALL conservar esa implementación en su ubicación original.

### Requirement 4: Preservación de la lógica de cálculo heurístico

**User Story:** Como propietario del sistema, quiero que toda la lógica de cálculo matemático se preserve intacta, para que el refactor no altere los resultados de análisis de la aplicación.

#### Acceptance Criteria

1. THE Sistema_Consolidacion SHALL conservar el cuerpo de cada Funcion_Heuristica presente en un Modulo_Canonico de modo que, para entradas idénticas, sus salidas sean equivalentes a la Linea_Base_Comportamiento dentro de una tolerancia de 0.0001 para valores numéricos y coincidencia exacta para valores no numéricos.
2. THE Sistema_Consolidacion SHALL capturar la Linea_Base_Comportamiento registrando las entradas y salidas de cada Funcion_Heuristica para cada rama lógica y para los casos de borde de entrada vacía, nula, cero y valor máximo, antes de iniciar la reorganización.
3. IF la consolidación requiere eliminar o sobrescribir una Funcion_Heuristica, THEN THE Sistema_Consolidacion SHALL solicitar autorización explícita al usuario y esperar hasta 60 segundos su respuesta antes de aplicar el cambio.
4. IF el usuario no responde dentro de 60 segundos o deniega la solicitud, THEN THE Sistema_Consolidacion SHALL conservar la Funcion_Heuristica intacta.
5. WHEN la reorganización finaliza, THE Sistema_Consolidacion SHALL verificar que cada Funcion_Heuristica produce, para las entradas registradas en la Linea_Base_Comportamiento, salidas equivalentes dentro de la tolerancia de 0.0001 para valores numéricos y coincidencia exacta para valores no numéricos.
6. IF una Funcion_Heuristica produce una salida distinta de la Linea_Base_Comportamiento, THEN THE Sistema_Consolidacion SHALL reportar la función, la entrada, el valor esperado y el valor obtenido, y revertir al estado previo a la reorganización.

### Requirement 5: Reorganización del directorio raíz

**User Story:** Como desarrollador, quiero una raíz limpia que contenga solo lo esencial, para navegar el proyecto sin confundir scripts desechables con código vivo.

#### Acceptance Criteria

1. WHEN la reorganización finaliza, THE directorio raíz SHALL contener únicamente el Entrypoint, archivos de configuración, archivos de requisitos de dependencias y documentación, y NO SHALL contener scripts de un solo uso, archivos con prefijo `test_` ni ningún Modulo_Duplicado.
2. THE Sistema_Consolidacion SHALL mover cada script de un solo uso de la raíz cuyo nombre comience con uno de los prefijos `fix_`, `diagnostico_`, `solucion_` o `reparador` al directorio `tools/`.
3. THE Sistema_Consolidacion SHALL mover cada archivo con prefijo `test_` de la raíz al directorio `tests/`.
4. WHEN un Archivo_Raiz se mueve a `tools/` o `tests/`, THE Sistema_Consolidacion SHALL actualizar cada referencia de importación a ese archivo para que apunte a su nueva ubicación.
5. IF en el destino ya existe un archivo con el mismo nombre que el archivo a mover, THEN THE Sistema_Consolidacion SHALL conservar ambos archivos, omitir el movimiento y registrar el conflicto.
6. IF la actualización de una referencia de importación falla, THEN THE Sistema_Consolidacion SHALL revertir el movimiento asociado y registrar el fallo.
7. THE Sistema_Consolidacion SHALL mover cada Modulo_Duplicado de la raíz a una ubicación de Modulo_Archivado, conservando el archivo en disco en lugar de eliminarlo permanentemente.
8. THE Sistema_Consolidacion SHALL preservar la ruta `data/betting_stats.db` de la Base_Datos sin cambios.

### Requirement 6: Sincronización de la documentación de arquitectura

**User Story:** Como desarrollador, quiero que la documentación de arquitectura describa el código real, para confiar en ella al hacer cambios.

#### Acceptance Criteria

1. WHEN la consolidación finaliza, THE Sistema_Consolidacion SHALL actualizar la Documentacion_Arquitectura de modo que cada módulo referenciado corresponda a un Modulo_Canonico existente en el árbol de archivos resultante.
2. WHEN la consolidación finaliza, THE Sistema_Consolidacion SHALL eliminar de la Documentacion_Arquitectura todas las referencias a módulos clasificados como Modulo_Duplicado o Modulo_Archivado.
3. THE Documentacion_Arquitectura SHALL describir el flujo de datos de cada deporte (MLB, NBA, UFC, Fútbol) usando las rutas de los Modulo_Canonico vigentes, entendiendo por vigente todo Modulo_Canonico presente en el árbol de archivos resultante tras la consolidación.
4. WHERE la Documentacion_Arquitectura menciona un módulo, THE Sistema_Consolidacion SHALL verificar que la ruta citada exista en el árbol de archivos resultante.
5. IF la ruta citada por un módulo en la Documentacion_Arquitectura no existe en el árbol de archivos resultante, THEN THE Sistema_Consolidacion SHALL marcar dicha referencia como inválida e indicar en un reporte de verificación la ruta no encontrada, sin sobrescribir el resto de la Documentacion_Arquitectura.
6. WHEN la verificación de todas las referencias finaliza, THE Sistema_Consolidacion SHALL producir un reporte que liste el total de referencias verificadas y el total de referencias marcadas como inválidas.

### Requirement 7: Suite de pruebas de verificación

**User Story:** Como desarrollador, quiero una suite de pruebas ejecutable, para confirmar que la consolidación no rompió la aplicación.

#### Acceptance Criteria

1. THE Sistema_Consolidacion SHALL proveer una Suite_Pruebas ejecutable mediante un único comando documentado en el README que no requiera argumentos obligatorios.
2. WHEN la Suite_Pruebas se ejecuta, THE Suite_Pruebas SHALL verificar que el Entrypoint y cada Paquete_Vivo se importan sin lanzar excepción.
3. IF la importación del Entrypoint o de un Paquete_Vivo lanza una excepción, THEN THE Suite_Pruebas SHALL reportar el módulo y la excepción ocurrida.
4. THE Suite_Pruebas SHALL verificar que cada símbolo exportado por `motors/__init__.py` resuelve a un objeto que no es None ni queda sin definir.
5. THE Suite_Pruebas SHALL verificar, para cada deporte (MLB, NBA, UFC, Fútbol), que su Modulo_Canonico de motor produce, para un conjunto fijo y versionado de al menos 3 entradas predefinidas por deporte, salidas idénticas a la Linea_Base_Comportamiento.
6. IF una verificación por deporte difiere de la Linea_Base_Comportamiento, THEN THE Suite_Pruebas SHALL reportar el deporte, el valor esperado y el valor obtenido.
7. WHEN la Suite_Pruebas finaliza, THE Suite_Pruebas SHALL retornar un código de salida igual a cero si todas las verificaciones pasan y distinto de cero si alguna falla.

### Requirement 8: Reversibilidad y seguridad de la operación

**User Story:** Como propietario del sistema, quiero que la consolidación sea reversible, para poder recuperar cualquier archivo si algo sale mal.

#### Acceptance Criteria

1. THE Sistema_Consolidacion SHALL archivar los Modulo_Duplicado y scripts obsoletos como Modulo_Archivado, conservándolos en estado recuperable durante al menos 30 días, sin eliminarlos de forma permanente.
2. WHEN un archivo se mueve o archiva, THE Sistema_Consolidacion SHALL registrar la ruta de origen y la ruta de destino en el Manifiesto_Inventario antes de iniciar la siguiente operación.
3. IF el registro de una ruta de origen o destino en el Manifiesto_Inventario falla, THEN THE Sistema_Consolidacion SHALL revertir el movimiento o archivo asociado restaurando el archivo a su ruta de origen, y reportar un mensaje de error que indique la operación afectada.
4. IF una operación de movimiento o archivo dejaría una importación viva sin resolver, THEN THE Sistema_Consolidacion SHALL cancelar esa operación, conservar todos los archivos en su estado original sin aplicar ningún cambio, y reportar el conflicto identificando el archivo y la importación no resuelta afectados.
5. WHEN un grupo de cambios de la reorganización se completa, THE Sistema_Consolidacion SHALL ejecutar la Suite_Pruebas antes de iniciar el siguiente grupo de cambios.
6. IF la Suite_Pruebas falla tras ejecutarse sobre un grupo de cambios, THEN THE Sistema_Consolidacion SHALL detener la reorganización, revertir los cambios de ese grupo a su estado anterior, y reportar un mensaje de error que indique el grupo de cambios afectado.
