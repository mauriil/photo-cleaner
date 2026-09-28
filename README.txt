=========================================================
 CLASIFICADOR DE FOTOS - Guia paso a paso para Windows
=========================================================

Que hace este programa
-----------------------
Recorre una carpeta (y todas sus subcarpetas) buscando fotos,
analiza cada una con un modelo de IA que corre en tu propia PC
(no sube nada a internet) y las mueve a carpetas separadas:

  explicito/        -> fotos detectadas como contenido explicito
  no_explicito/      -> el resto de las fotos
  revisar_manual/    -> casos dudosos que conviene revisar a mano

Dentro de cada una de esas carpetas, las ordena por fecha de la
foto: AAAA/AAAA-MM/ (por ejemplo 2023/2023-07/).


Que archivos tenes que copiar al pendrive
------------------------------------------
De esta carpeta, copia SOLO estos archivos y pegalos en el pendrive:

  clasificar_fotos.py
  requirements.txt
  instalar.bat
  ejecutar.bat
  README.txt   (este archivo)

NO copies la carpeta ".venv" si existe: es especifica de Mac y no
sirve en Windows, solo ocupa espacio de mas.


PASO 1 - Llevar los archivos a la PC con Windows
--------------------------------------------------
1. Conecta el pendrive a la PC con Windows.
2. Crea una carpeta en el Escritorio o en Documentos, por ejemplo:
   "ClasificadorFotos"
3. Copia ahi adentro los 5 archivos del pendrive (los listados arriba).

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
1. Haz doble clic en "ejecutar.bat"
2. Te va a preguntar la ruta de la carpeta con las fotos a
   clasificar. Por ejemplo:
      D:\FotosMezcladas
   (podes copiar la ruta desde la barra de direcciones del
   Explorador de Windows)
3. Te va a proponer una carpeta destino por defecto, podes aceptarla
   apretando Enter, o escribir otra ruta.
4. Te muestra cuantas fotos encontro y pide confirmacion (escribi
   "s" y Enter para continuar).
5. Va a ir clasificando cada foto. La primera vez que corras el
   programa va a descargar el modelo de IA (unos 24 MB), despues
   ya queda guardado en la PC y no se vuelve a descargar.
6. Al terminar te muestra un resumen: cuantas fotos fueron a cada
   categoria.


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
