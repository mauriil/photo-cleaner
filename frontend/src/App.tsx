import { useCallback, useEffect, useState } from "react";
import { AnimatePresence, motion } from "motion/react";
import { Toaster, toast } from "sonner";
import { ACCIONES, ACCION_POR_DIR, backend, type Estado, type ResumenConsola } from "@/lib/api";
import { FolderPicker } from "@/components/FolderPicker";
import { SpotlightBackground } from "@/components/ui/spotlight-background";
import type { DeckIntent } from "@/components/ui/swipe-deck";
import { Done } from "@/screens/Done";
import { Review } from "@/screens/Review";
import { Setup } from "@/screens/Setup";

export default function App() {
  const [estado, setEstado] = useState<Estado | null>(null);
  const [picker, setPicker] = useState<"origen" | "destino" | null>(null);
  const [origen, setOrigen] = useState<string | null>(null);
  const [inspeccion, setInspeccion] = useState<ResumenConsola | null>(null);
  const [inspeccionando, setInspeccionando] = useState(false);
  const [pasarNormales, setPasarNormales] = useState(true);
  const [empezando, setEmpezando] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [intent, setIntent] = useState<DeckIntent>({ dir: null, amount: 0 });

  useEffect(() => {
    backend.estado().then(setEstado).catch((err) => setError(err.message));
  }, []);

  const limpiarOrigen = () => {
    setOrigen(null);
    setInspeccion(null);
    setError(null);
  };

  const elegir = async (path: string) => {
    const modo = picker;
    setPicker(null);
    if (modo === "destino") {
      try {
        setEstado(await backend.destino(path));
        toast.success("Destino actualizado", { description: path });
        if (origen) setInspeccion(await backend.inspeccionar(origen));
      } catch (err) {
        toast.error((err as Error).message);
      }
      return;
    }
    setInspeccionando(true);
    setError(null);
    try {
      const info = await backend.inspeccionar(path);
      setOrigen(path);
      setInspeccion(info);
    } catch (err) {
      setOrigen(null);
      setInspeccion(null);
      setError((err as Error).message);
    } finally {
      setInspeccionando(false);
    }
  };

  const empezar = async () => {
    if (!origen) return;
    setEmpezando(true);
    setError(null);
    try {
      const res = await backend.origen(origen, pasarNormales);
      if (res.movidas_normales) {
        toast.success(`${res.movidas_normales} no explícitas → normales/`, { description: "Ya están en el cúmulo." });
      }
      setEstado(res);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setEmpezando(false);
    }
  };

  const salir = useCallback(
    async (olvidar: boolean) => {
      const res = await backend.cerrar();
      if (olvidar) limpiarOrigen();
      else if (origen) {
        // Refrescamos los conteos: lo ya decidido salió de la carpeta.
        backend.inspeccionar(origen).then(setInspeccion).catch(() => limpiarOrigen());
      }
      setEstado(res);
    },
    [origen],
  );

  const fase = estado?.fase ?? "setup";
  const tint = intent.dir ? ACCIONES[ACCION_POR_DIR[intent.dir]].rgb : undefined;

  return (
    <SpotlightBackground tint={fase === "review" ? tint : undefined} intensity={intent.amount}>
      <AnimatePresence mode="wait">
        <motion.div
          key={fase}
          initial={{ opacity: 0, filter: "blur(8px)" }}
          animate={{ opacity: 1, filter: "blur(0px)" }}
          exit={{ opacity: 0, filter: "blur(8px)" }}
          transition={{ duration: 0.25 }}
        >
          {fase === "review" && estado ? (
            <Review estado={estado} setEstado={setEstado} onSalir={() => salir(false)} onIntent={setIntent} />
          ) : fase === "done" && estado ? (
            <Done estado={estado} onOtra={() => salir(true)} />
          ) : (
            <Setup
              estado={estado}
              inspeccion={inspeccion}
              inspeccionando={inspeccionando}
              pasarNormales={pasarNormales}
              setPasarNormales={setPasarNormales}
              error={error}
              empezando={empezando}
              onElegirDestino={() => setPicker("destino")}
              onElegirOrigen={() => setPicker("origen")}
              onEmpezar={empezar}
            />
          )}
        </motion.div>
      </AnimatePresence>
      <FolderPicker
        open={picker !== null}
        modo={picker ?? "origen"}
        inicial={picker === "destino" ? estado?.destino : origen ?? estado?.origen}
        onClose={() => setPicker(null)}
        onPick={elegir}
      />
      <Toaster theme="dark" position="bottom-right" richColors closeButton />
    </SpotlightBackground>
  );
}
