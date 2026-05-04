# Prompt para iniciar una sesion nueva de Claude

Copia y pega este texto en una nueva sesion de Claude Code, dentro del directorio
`d:\PruebaRealSgan\`. Cambia ``[mi pregunta de hoy]`` por lo que quieras hacer.

---

```
Hola. Estoy continuando el proyecto CubeSat-EdgeAI-Payload --- un payload de
microscopia FPM lensless para el satelite INTISAT, basado en Raspberry Pi 5.

Antes de responder cualquier cosa, lee estos 4 archivos en este orden:

  1. Documentos de Referencia/contexto_sesion/CONTEXTO.md
  2. Documentos de Referencia/contexto_sesion/ESTADO.md
  3. Documentos de Referencia/contexto_sesion/ARQUITECTURA.md
  4. Documentos de Referencia/contexto_sesion/INDEX.md

Despues, en MAXIMO 6 lineas, confirmame que entendiste:
  - el objetivo concreto del payload,
  - las dimensiones reales de las 3 mascaras (numeros),
  - el modo de ensamblaje preferido (A, B o C),
  - la tarea pendiente mas urgente,
  - cualquier ambiguedad que detectes en los documentos.

Si esta todo claro, esperas mi pregunta y NO empezas a escribir codigo
ni a tomar decisiones nuevas hasta que te lo pida explicitamente.

[mi pregunta de hoy]
```

---

## Por que este prompt

a) **Forza a leer el contexto** antes de actuar (evita que Claude reinvente la rueda).
b) **Pide confirmacion corta** (6 lineas) para verificar que entendio bien.
c) **Bloquea decisiones nuevas** hasta que vos preguntes (evita que se desvie).
d) **Lo deja escribir codigo solo si vos lo autorizas**.

## Cuando renovarlo

Cada vez que cambies algo importante (decision frozen, nueva mascara, nueva
hipotesis), actualiza el archivo correspondiente:

- Si cambia el objetivo  -> `CONTEXTO.md`
- Si cambia el progreso  -> `ESTADO.md`
- Si cambia el hardware  -> `ARQUITECTURA.md`
- Si agregas un doc      -> `INDEX.md`
