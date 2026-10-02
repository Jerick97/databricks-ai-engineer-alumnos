# Aula E2E · SBS

Abre `index.html` directamente en tu navegador. Es un archivo autocontenido, sin instalaciones ni servicios externos. También está servido durante esta sesión en http://127.0.0.1:8876.

Para volver a iniciar el servidor desde esta carpeta:

```sh
python3 -m http.server 8876 --bind 127.0.0.1
```

## Recorrido de enseñanza

1. Mapa general: distinguir qué decidir, qué preparar y dónde implementar cada responsabilidad.
2. Explorador: 30 fichas con definición, aspectos que revisar, tres opciones con ventajas/límites, evidencias, error frecuente y aplicación SBS.
3. Modo docente: plantear la pregunta de cada ficha y revelar la guía de discusión.
4. Capas × sesiones: consultar el cruce original S02–S08.
5. Taller SBS: comparar versiones sintéticas, responder y discutir cuatro situaciones: plazo, renumeración, anexo ausente e instrucción maliciosa dentro del corpus.
6. Notas: registrar decisiones por ficha y exportarlas a Markdown. Las marcas representan lectura, no implementación.

Las alternativas pueden combinarse. Las etapas son iterativas. Las doce decisiones son una síntesis propia v0.1, no un estándar oficial. El caso aplicado sigue en diseño: los ejercicios no ejecutan Genie ni certifican conclusiones jurídicas.

## Edición y comprobaciones

Contenido: `frameworks.json` y `decisions.json`. Interfaz: `template.html`.

```sh
python3 build.py
node --check check.js
node verify.cjs
```

El build comprueba IDs, campos y referencias; el test ejecuta la lógica con un doble mínimo del DOM. Esto no sustituye la prueba visual en navegador. Consulta `VALIDACION.md`.
