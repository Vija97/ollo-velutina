# Ollo Velutina

Filtra los avisos de avispa velutina antes de que lleguen al 012: haces una foto,
la IA dice si es velutina, comprueba si ya hay un aviso cerca y prepara el aviso.
Proyecto del Hackathon ETSE (USC, 22/10/2026).

**Pruébala: https://ollo-velutina.streamlit.app**

La web se despliega sola desde `main` en Streamlit Community Cloud. Es una
demostración: la base de datos se reinicia con los avisos de ejemplo cuando la
app se reinicia, y la identificación es orientativa.

- Problema, especies, datasets y fuentes: [docs/contexto/02_contexto_velutina.md](docs/contexto/02_contexto_velutina.md)
- Especificación técnica: [docs/contexto/03_especificacion_tecnica.md](docs/contexto/03_especificacion_tecnica.md)
- Plan del día y pitch: [docs/contexto/05_plan_dia_y_pitch.md](docs/contexto/05_plan_dia_y_pitch.md)
- Reglas de trabajo (personas y agentes): [AGENTS.md](AGENTS.md)

## Arrancar

```bash
python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml   # y poner la clave
streamlit run app.py
```

`models/best.pt` (YOLO) es opcional: sin él, todo se clasifica con el LLM (plan B).

## Cómo trabajamos

Tablero: https://github.com/users/Vija97/projects/1

Issue pequeña → rama `feat/<n>-<slug>` → PR con `Closes #<n>` → **1 aprobación**
de otra persona → squash merge. `main` está protegida y siempre debe arrancar.
Desde las 17:45, solo arreglos que rompen la demo.

Skills (Claude Code en `.claude/skills/`, canónicas en `.agents/skills/`):

| Skill | Para qué |
|---|---|
| `start-task` | Issue → rama desde `main` actualizado + contexto de la spec |
| `semantic-commits-and-push` | Commits semánticos, push y PR (nunca a `main`) |
| `review-pr` | Revisión de ≤ 5 min con veredicto; aprueba la persona |
| `demo-check` | Recorre los criterios de la demo (spec §11) y dice qué recortar |

## Estructura

```
app.py                  Foto → resultado → aviso
pages/1_Mapa.py         Mapa de avisos
pages/2_Sobre_el_modelo.py  Métricas y datasets
core/                   classifier · llm · geo · db · pipeline (contratos entre roles)
models/best.pt          Pesos YOLO
data/seed_avisos.csv    Avisos de ejemplo
demo_images/            Fotos de la demo (+ FUENTES.md con licencias)
metrics/                Matriz de confusión y results.json
```
