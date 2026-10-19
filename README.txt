=========================================================
 CLASIFICADOR DE FOTOS - Guia paso a paso (Windows y Mac)
=========================================================

DOS PASOS: consola primero, Tinder despues
------------------------------------------
1) La clasificacion CON IA sigue siendo por consola
   (ejecutar.bat / Clasificar Fotos.app / ejecutar.command).
   Deja una carpeta al lado de la original, con "_clasificado":

     explicito/         -> la IA las marco como explicitas
     no_explicito/      -> la IA las dio por seguras
     revisar_manual/    -> la IA no estuvo segura

2) El front Tinder actua SOBRE ESE RESULTADO, no sobre las fotos crudas.
   Sirve para lo que queda: partir las explicitas en "guardar" o "borrar",
   y decidir las dudosas. Podes repetirlo con varios *_clasificado y todo
   se acumula en UN destino con 3 carpetas:

  Se queda  (flecha derecha / swipe a la derecha)
      -> en realidad es normal, o una dudosa que se queda
      -> carpeta destino/normales/

  Aparte    (flecha arriba / swipe hacia arriba)
      -> explicita que queres CONSERVAR
      -> carpeta destino/explicitas_guardar/

  Se va     (flecha izquierda / swipe a la izquierda)
      -> explicita que queres BORRAR despues
      -> carpeta destino/explicitas_borrar/

Las no_explicito de la consola no pasan por Tinder (ya estan resueltas).
En el front hay un tilde para sumarlas de una al cumulo de normales.

Nada se borra solo; "Se va" las aparta para que vos borres esa carpeta
cuando estes seguro.

Windows: doble clic en "ejecutar_web.bat"
Mac:     doble clic en "ejecutar_web.command"

Se abre el navegador en http://127.0.0.1:5055
1. Confirmá la carpeta destino (el cumulo final de las 3 acciones).
2. Elegí la carpeta *_clasificado que salio de la consola.
3. Revisá lo pendiente. Cuando termines, elegí otro *_clasificado;
   el destino no se reinicia.

Atajos: flechas del teclado, Z para deshacer.


MODO AUTOMATICO CON IA (paso 1, consola)
------------------------------------
Recorre una carpeta (y todas sus subcarpetas) buscando fotos,
analiza cada una con un modelo de IA que corre en tu propia PC
(no sube nada a internet) y las mueve a carpetas separadas:

  explicito/        -> fotos detectadas como contenido explicito
  no_explicito/      -> el resto de las fotos
  revisar_manual/    -> casos dudosos que conviene revisar a mano

Dentro de cada una de esas carpetas se mantienen las subcarpetas
originales y, dentro de ellas, las fotos se ordenan por fecha:
AAAA/AAAA-MM/ (por ejemplo Camara/2023/2023-07/).


(Si usas Mac, saltea a la seccion "USO EN MAC" al final.)


Que archivos tenes que copiar al pendrive
------------------------------------------
De esta carpeta, copia SOLO estos archivos y pegalos en el pendrive:

  clasificar_fotos.py
  webapp.py
  static/          (toda la carpeta)
  requirements.txt
  instalar.bat
  ejecutar.bat
  ejecutar_web.bat
  README.txt   (este archivo)

NO copies la carpeta ".venv" si existe: es especifica de Mac y no
sirve en Windows, solo ocupa espacio de mas.


PASO 1 - Llevar los archivos a la PC con Windows
--------------------------------------------------
1. Conecta el pendrive a la PC con Windows.
2. Crea una carpeta en el Escritorio o en Documentos, por ejemplo:
   "ClasificadorFotos"
3. Copia ahi adentro los archivos del pendrive (los listados arriba).

Importante: no ejecutes el programa directamente desde el pendrive,
va a ser mucho mas lento. Siempre copia primero al disco de la PC.


PASO 2 - Instalar el programa (una sola vez)
------------------------------------------------
No hace falta instalar Python a mano: "instalar.bat" lo detecta y,
si no esta, lo descarga e instala solo (queda instalado nada mas
para tu usuario de Windows, NO hace falta ser administrador ni
tener permisos especiales).

1. Entra a la carpeta "ClasificadorFotos" que creaste en el Paso 1.
2. Haz doble clic en "instalar.bat"

   Si Windows muestra una ventana azul que dice "Windows protegio
   su PC" (SmartScreen), hace clic en "Mas informacion" y despues
   en "Ejecutar de todas formas". Esto pasa porque el archivo .bat
   es nuevo y no tiene firma digital, es normal y seguro ya que vos
   mismo lo copiaste al pendrive.

3. Se va a abrir una ventana negra (consola) que instala todo lo
   necesario (Python si hace falta, y despues las dependencias).
   Esto puede tardar entre 5 y 20 minutos dependiendo de la PC y
   la conexion a internet. Necesita internet SOLO en este paso.
4. Cuando termine vas a ver el mensaje "Instalacion completa".
   Podes cerrar la ventana.

Si algo falla en la descarga o instalacion automatica de Python,
el mismo script te va a avisar y te va a dar el link para
instalarlo manualmente desde https://www.python.org/downloads/
(en ese caso, al instalarlo a mano, marca la casilla
"Add python.exe to PATH").


PASO 3 - Usar el programa (cada vez que quieras clasificar fotos)
----------------------------------------------------------------------
1. Arrastra la carpeta con las fotos y soltala sobre "ejecutar.bat".
   (Tambien podes hacer doble clic en "ejecutar.bat" y pegar la
   ruta de la carpeta, por ejemplo D:\FotosMezcladas, copiandola
   de la barra de direcciones del Explorador de Windows.)
2. Las fotos clasificadas van a una carpeta nueva al lado de la
   original, con el mismo nombre y "_clasificado" al final
   (por ejemplo D:\FotosMezcladas_clasificado).
3. Te muestra cuantas fotos encontro y pide confirmacion (escribi
   "s" y Enter para continuar).
4. Va a ir clasificando cada foto. La primera vez que corras el
   programa va a descargar el modelo de IA (unos 24 MB), despues
   ya queda guardado en la PC y no se vuelve a descargar.
5. Al terminar te muestra un resumen: cuantas fotos fueron a cada
   categoria.
6. Recien ahi, doble clic en "ejecutar_web.bat" para revisar en el
   navegador lo que queda (explicito + revisar_manual) y acumularlo
   en las 3 carpetas finales.


Notas importantes
-------------------
- Las fotos se MUEVEN, no se copian. Si la PC es de bajos recursos
  y se corta la luz o se cuelga a mitad de proceso, las fotos ya
  movidas van a estar en la carpeta destino y las que faltan siguen
  en el origen; podes volver a correr el programa sin problema.
- Necesitas al menos 3 GB libres en el disco para las dependencias
  (sobre todo la primera vez, en el Paso 2).
- En una PC de bajos recursos el analisis de cada foto puede tardar
  unos segundos; con miles de fotos el proceso puede llevar bastante
  tiempo. Es normal, dejalo correr.
- Para ajustar que tan estricto es el corte entre categorias, abri
  "clasificar_fotos.py" con el Bloc de notas y modifica estos
  valores cerca del principio del archivo:
      UMBRAL_BAJO = 0.2
      UMBRAL_ALTO = 0.7
  Valores mas bajos en UMBRAL_ALTO clasifican como "explicito" con
  menos exigencia; valores mas altos en UMBRAL_BAJO mandan mas fotos
  a "revisar_manual" en vez de darlas por seguras automaticamente.


Problemas comunes
--------------------
- "No se pudo descargar/instalar Python" automaticamente: instalalo
  vos mismo desde https://www.python.org/downloads/ marcando la
  casilla "Add python.exe to PATH", y volve a correr "instalar.bat".
- El instalador se cuelga o da error de conexion: revisa que la PC
  tenga internet y volve a correr "instalar.bat".
- Windows Defender u otro antivirus tarda mucho o marca el archivo:
  es un falso positivo comun con paquetes de IA (TensorFlow), es
  seguro, podes permitirlo si el antivirus te lo pide.


=========================================================
 USO EN MAC
=========================================================
En Mac se usa toda la carpeta del proyecto tal cual (no hace
falta el pendrive ni los .bat). Lo importante:

  - "Clasificar Fotos.app" y "ejecutar.command" tienen que quedar
    DENTRO de esta carpeta, junto a "clasificar_fotos.py" y ".venv".
    Si queres tener la app a mano, crea un alias (clic derecho ->
    Crear alias) y movelo al Escritorio o arrastralo al Dock.
    No muevas la app original.


PASO 1 - Instalar (una sola vez)
---------------------------------
Si en esta carpeta ya existe ".venv" (carpeta oculta; en Finder
se ve con Cmd+Shift+.), ya esta instalado: salta al Paso 2.

1. Si no tenes "uv", instalalo desde la Terminal:
       brew install uv
2. En la Terminal, entra a esta carpeta (escribi "cd ", arrastra
   la carpeta a la ventana y presiona Enter) y ejecuta:
       uv venv --python 3.12 .venv
       uv pip install --python .venv/bin/python -r requirements.txt
   Necesita internet y puede tardar varios minutos.


PASO 2 - Clasificar una carpeta
---------------------------------
1. En Finder, arrastra la carpeta con fotos y soltala sobre el
   icono "Clasificar Fotos.app" (o sobre su alias).
2. Se abre la Terminal, muestra la carpeta de origen, la de
   destino y cuantas fotos encontro. Escribi "s" y Enter.
3. Al terminar muestra el resumen. Presiona una tecla y cerra la
   ventana de la Terminal.

Las fotos clasificadas quedan en una carpeta nueva al lado de la
original, con el mismo nombre y "_clasificado" al final:

  Vacaciones/               <- queda sin las fotos que se movieron
      Playa/
  Vacaciones_clasificado/
      no_explicito/2023/2023-07/...        <- fotos sueltas de Vacaciones
      no_explicito/Playa/2023/2023-07/...  <- fotos de la subcarpeta Playa
      explicito/...
      revisar_manual/...

Alternativa sin la app: doble clic en "ejecutar.command",
arrastra la carpeta a la ventana de la Terminal y presiona Enter.

Paso siguiente (lo que queda): doble clic en "ejecutar_web.command"
y en el navegador elegí "Vacaciones_clasificado". Ahi revisas a mano
explicito y revisar_manual; las no_explicito se pueden sumar de una
al cumulo de normales.


La primera vez
---------------
- macOS puede preguntar si "Clasificar Fotos" puede controlar la
  Terminal: hace clic en "Permitir". Si lo rechazaste por error,
  habilitalo en Ajustes del Sistema -> Privacidad y seguridad ->
  Automatizacion.
- Si dice que la app no se puede abrir porque no se pudo verificar
  el desarrollador: clic derecho sobre la app -> Abrir -> Abrir.
- La primera corrida descarga el modelo de IA (unos 24 MB).


Hacer una prueba antes de usarlo en serio
-------------------------------------------
Como las fotos se MUEVEN, conviene probar primero con una copia:

1. Crea una carpeta nueva, por ejemplo "Prueba", y copia adentro
   (Cmd+C / Cmd+V, no arrastrar) unas 10-20 fotos variadas.
2. Solta "Prueba" sobre "Clasificar Fotos.app" y confirma con "s".
3. Abri "Prueba_clasificado" y revisa que cada foto haya quedado
   en la categoria y la fecha esperadas.
4. Si estas conforme, borra "Prueba" y "Prueba_clasificado" y
   usalo con tus carpetas reales.


En Windows tambien podes soltar la carpeta directamente sobre
"ejecutar.bat".
