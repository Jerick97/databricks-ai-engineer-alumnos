## Frame 1
status: animated
src: compositions/scene01.html
Motion: spring-pop-entrance
Start: 0
Duration: 28.5
Beat: El objetivo: conservar evidencia
Narración: SBS Radar ayuda a localizar, comparar y conversar sobre documentos normativos. En este primer video seguimos la preparación: desde los PDF oficiales hasta los datos que podrá consumir el agente. Trabajamos con dos familias: seguridad de la información y ciberseguridad, y conducta de mercado. La pregunta que guía todo el flujo es sencilla: ¿podemos reconstruir de qué documento salió cada afirmación? Por eso, antes de usar un modelo, definimos el alcance y los contratos de los datos.

## Frame 2
status: animated
src: compositions/scene02.html
Motion: spring-pop-entrance
Start: 28.5
Duration: 28.833
Beat: Capturar y preservar el original
Narración: La ingesta comienza con direcciones explícitas de fuentes oficiales de la SBS. Se comprueba que el destino esté permitido, se descarga el PDF y se valida su formato. Después calculamos una huella SHA doscientos cincuenta y seis. Esta huella permite identificar contenidos idénticos y evitar duplicados. Conservamos el original, la dirección de origen y el momento de captura. Atención: la huella identifica los bytes del archivo. No confirma la vigencia jurídica de una norma.

## Frame 3
status: animated
src: compositions/scene03.html
Motion: spring-pop-entrance
Start: 57.333
Duration: 31.333
Beat: Del PDF a pasajes verificables
Narración: Extraemos el texto conservando página y posición dentro del documento. Así podemos volver desde un fragmento hasta su fuente. Luego identificamos disposiciones correspondientes en dos copias de la misma norma y alineamos el antes y el después. Separamos tres cosas: diferencia textual, interpretación del cambio e implicancia propuesta. Un salto de línea distinto no demuestra una nueva obligación. Las tablas, anexos y errores de extracción necesitan controles, y la cobertura parcial debe permanecer visible.

## Frame 4
status: animated
src: compositions/scene04.html
Motion: spring-pop-entrance
Start: 88.667
Duration: 30.2
Beat: Qué contiene este piloto
Narración: El inventario verificado contiene seis copias documentales de cuatro resoluciones. Hay dos copias de la resolución quinientos cuatro de dos mil veintiuno y dos de la tres mil doscientos setenta y cuatro de dos mil diecisiete. Además, hay una copia de la dos mil doscientos ochenta y seis de dos mil veinticuatro y otra de la dos mil doscientos veinte de dos mil veinticinco. Los dos pares visibles usan cuatro de esos seis documentos. Una opción del selector representa un par: contiene dos copias, no una sola versión.

## Frame 5
status: animated
src: compositions/scene05.html
Motion: spring-pop-entrance
Start: 118.867
Duration: 38.2
Beat: Preparar dos formas de consultar
Narración: A partir de los pasajes preparamos un índice local para recuperación aumentada, o RAG. Los embeddings representan el significado mediante vectores, y los metadatos conservan familia, versión y fuente. En paralelo, curamos ocho tablas para consultas estructuradas: documentos, versiones, disposiciones, pares, cambios, evidencias, revisiones y procesos. Los procesos bancarios son ficticios. Genie permite contar y relacionar estas filas; RAG permite recuperar evidencia textual. Son capacidades complementarias. Este piloto utiliza un índice local: no debemos presentarlo como un servicio Vector Search desplegado.

## Frame 6
status: animated
src: compositions/scene06.html
Motion: spring-pop-entrance
Start: 157.067
Duration: 37.767
Beat: Publicar no equivale a actualizar la App
Narración: Hay dos publicadores diferentes. El publicador de Genie escribe las tablas en Delta, dentro de Unity Catalog. El publicador de artefactos escribe en Volumes y mantiene un control en Delta. Después se verifican las escrituras mediante lectura de retorno. La aplicación consume un paquete de datos verificado. Publicar artefactos nuevos no actualiza automáticamente ese paquete. En el estado documentado, el trabajo diario está pausado y la promoción automática a la aplicación sigue pendiente. Cerramos el recorrido con evidencia publicada y límites explícitos, sin confundir un piloto probado con operación continua completa.