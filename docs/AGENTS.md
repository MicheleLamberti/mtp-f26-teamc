# Norma de documentación de MTP

Instrucción expresa del usuario, 19/10/2026. Se aplica a esta carpeta y a todos sus subdirectorios.

- Toda documentación nueva o modificada (informes, respuestas, apuntes, índices de fuentes y resultados narrativos) debe tener su fuente editable en LaTeX (`.tex`).
- Todos los PDF generados deben compilarse desde esas fuentes LaTeX. No crear informes con ReportLab, Word o Markdown.
- Conservar las fuentes del curso en `course_material/`, las referencias descargadas en `encoding_references/` y las capturas de Task 11 en `task_11_unicode/source_images/`, en sus formatos originales. Estas fuentes externas permanecen locales y excluidas de Git; el informe propio, sus fuentes LaTeX y las pruebas reproducibles de `task_11_unicode/` se versionan.
- El código, los datos estructurados y las muestras de prueba conservan sus formatos funcionales (`.py`, `.json`, `.txt`, `.bin`, etc.). La explicación de esos archivos se redacta en LaTeX.
- Mantener juntos y accesibles el PDF final y su proyecto LaTeX. Compilar y revisar visualmente el resultado antes de entregarlo.
- Este `AGENTS.md` es la excepción técnica necesaria para que futuros agentes descubran y cumplan la norma.
