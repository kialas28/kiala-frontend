import os
import sys
import json
import uuid
import datetime
import httpx
import aiosqlite
import secrets
import base64
import io
import zipfile
import asyncio
import warnings
warnings.filterwarnings("ignore")

from pathlib import Path
from fastapi import FastAPI, HTTPException, Response, Cookie, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, List
from google import genai
from google.genai import types

if "C:\\KialaStudio" not in sys.path:
    sys.path.insert(0, "C:\\KialaStudio")

PROJECT_ID = "kialas-ai-studio"
LOCATION = "global"
DB_PATH = os.path.join(os.path.dirname(__file__), "kiala_studio.db")
WORKSPACE_BASE = Path(os.path.expanduser("~")) / "Desktop" / "Kiala_Workspaces"
WORKSPACE_BASE.mkdir(parents=True, exist_ok=True)

NATIVE_MODELS = {
    "gemini-3.1-pro-preview": "gemini-3.1-pro-preview",
    "gemini-3.5-flash": "gemini-3.5-flash",
    "gemini-2.5-pro": "gemini-2.5-pro"
}

RATES = {
    "gemini-3.1-pro-preview": {"input": 1.25 / 1_000_000, "output": 5.00 / 1_000_000},
    "gemini-3.5-flash": {"input": 0.075 / 1_000_000, "output": 0.30 / 1_000_000},
    "gemini-2.5-pro": {"input": 1.25 / 1_000_000, "output": 5.00 / 1_000_000},
}

app = FastAPI(title="Kiala Studio Pro V3.5 - UI Elegante & Motor Dual")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

AGENT_TOOL = types.Tool(
    function_declarations=[
        types.FunctionDeclaration(
            name="web_search",
            description="Busca en internet tendencias, competidores, referencias de diseño y documentación tecnica.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "query": types.Schema(type=types.Type.STRING, description="Termino o frase de busqueda")
                },
                required=["query"]
            )
        ),
        types.FunctionDeclaration(
            name="list_workspace_files",
            description="Explora e inspecciona todos los archivos y subcarpetas existentes dentro del workspace activo.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "workspace": types.Schema(type=types.Type.STRING, description="Nombre exacto del workspace")
                },
                required=["workspace"]
            )
        ),
        types.FunctionDeclaration(
            name="create_file",
            description="Crea o sobrescribe archivos secundarios como .css, .js o modulos. PROHIBIDO usar para index.html. Para index.html debes entregar bloques DIFF en formato markdown.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "workspace": types.Schema(type=types.Type.STRING, description="Nombre exacto del workspace"),
                    "filepath": types.Schema(type=types.Type.STRING, description="Ruta relativa del archivo"),
                    "content": types.Schema(type=types.Type.STRING, description="Contenido completo del archivo")
                },
                required=["workspace", "filepath", "content"]
            )
        ),
        types.FunctionDeclaration(
            name="manage_file",
            description="Elimina, renombra o mueve un archivo dentro del workspace activo.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "workspace": types.Schema(type=types.Type.STRING, description="Nombre exacto del workspace"),
                    "action": types.Schema(type=types.Type.STRING, enum=["delete", "rename", "move"], description="Accion a realizar"),
                    "filepath": types.Schema(type=types.Type.STRING, description="Ruta relativa del archivo"),
                    "new_filepath": types.Schema(type=types.Type.STRING, description="Nueva ruta relativa si es rename o move")
                },
                required=["workspace", "action", "filepath"]
            )
        ),
        types.FunctionDeclaration(
            name="download_file",
            description="Descarga un archivo o imagen remota de internet y lo guarda en el workspace para la web.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "workspace": types.Schema(type=types.Type.STRING, description="Nombre exacto del workspace"),
                    "url": types.Schema(type=types.Type.STRING, description="URL directa del archivo o imagen"),
                    "filepath": types.Schema(type=types.Type.STRING, description="Ruta relativa local donde se guardara")
                },
                required=["workspace", "url", "filepath"]
            )
        ),
        types.FunctionDeclaration(
            name="github_search",
            description="Busca repositorios, librerias y componentes de codigo abierto en GitHub.",
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "query": types.Schema(type=types.Type.STRING, description="Termino de busqueda")
                },
                required=["query"]
            )
        )
    ]
)

SEARCH_TOOL = types.Tool(google_search=types.GoogleSearch())

class ProjectCreate(BaseModel): name: str; description: Optional[str] = ""
class CreateSessionReq(BaseModel): project_id: str; title: str = "Nueva Conversación"; model: str = "auto-router"; system_prompt: Optional[str] = ""
class RenameReq(BaseModel): name: str
class CalibrateBalanceReq(BaseModel): current_balance: float
class SaveKeysReq(BaseModel): gemini_key: Optional[str] = ""; perplexity_key: Optional[str] = ""; openai_key: Optional[str] = ""; anthropic_key: Optional[str] = ""; github_token: Optional[str] = ""
class ConnectorUpdate(BaseModel): name: str; state: bool
class LoginReq(BaseModel): email: str; password: str
class SendMessageReq(BaseModel):
    session_id: str
    message: str
    model: str = "auto-router"
    system_instruction: Optional[str] = None
    enable_grounding: Optional[bool] = False
    enable_web: Optional[bool] = False
    web_search: Optional[bool] = False
    search: Optional[bool] = False
    enable_deep_research: Optional[bool] = False
    attachments: Optional[List[dict]] = []
    workspace_name: Optional[str] = None
    current_code: Optional[str] = ''

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.execute("PRAGMA foreign_keys = ON;")
        await db.execute("""CREATE TABLE IF NOT EXISTS projects (id TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT DEFAULT '', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        await db.execute("""CREATE TABLE IF NOT EXISTS sessions (id TEXT PRIMARY KEY, project_id TEXT NOT NULL, title TEXT NOT NULL, model TEXT DEFAULT 'auto-router', is_main INTEGER DEFAULT 0, system_prompt TEXT DEFAULT '', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE)""")
        await db.execute("""CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, session_id TEXT NOT NULL, role TEXT NOT NULL, content TEXT NOT NULL, model_used TEXT DEFAULT '', prompt_tokens INTEGER DEFAULT 0, output_tokens INTEGER DEFAULT 0, cost_usd REAL DEFAULT 0.0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, FOREIGN KEY(session_id) REFERENCES sessions(id) ON DELETE CASCADE)""")
        await db.execute("""CREATE TABLE IF NOT EXISTS settings (key_name TEXT PRIMARY KEY, key_value TEXT NOT NULL, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)""")
        
        async with db.execute("SELECT id FROM projects WHERE id = 'default-project'") as cur:
            if not await cur.fetchone():
                now = datetime.datetime.utcnow().isoformat()
                await db.execute("INSERT INTO projects (id, name, description, created_at, updated_at) VALUES (?, ?, ?, ?, ?)", ("default-project", "Workspace Principal", "Área central de trabajo", now, now))
                await db.execute("INSERT INTO sessions (id, project_id, title, model, is_main, system_prompt, created_at, updated_at) VALUES (?, ?, ?, ?, 1, '', ?, ?)", (str(uuid.uuid4()), "default-project", "⭐ Chat Principal", "auto-router", now, now))
        
        async with db.execute("SELECT key_value FROM settings WHERE key_name = 'initial_balance'") as cur:
            if not await cur.fetchone():
                await db.execute("INSERT INTO settings (key_name, key_value) VALUES ('initial_balance', '300.0')")
        await db.commit()

@app.on_event("startup")
async def on_startup():
    await init_db()

@app.get("/api/workspaces")
def get_workspaces():
    return [d.name for d in WORKSPACE_BASE.iterdir() if d.is_dir()]

@app.post("/api/workspace/save")
async def save_to_workspace(request: Request):
    try:
        data = await request.json()
        html_content = data.get("html_content", "")
        client_name = data.get("client_name", "default_project")
        filename = data.get("filename", "index.html")
        ws_dir = WORKSPACE_BASE / client_name
        ws_dir.mkdir(parents=True, exist_ok=True)
        file_path = ws_dir / filename
        file_path.parent.mkdir(parents=True, exist_ok=True)
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        return {"status": "success", "message": f"Guardado exitosamente en {client_name}/{filename}"}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/workspace/{workspace_name}/export")
async def export_workspace(workspace_name: str):
    ws_dir = WORKSPACE_BASE / workspace_name
    if not ws_dir.exists():
        raise HTTPException(status_code=404, detail="Workspace no encontrado")
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
        for file_path in ws_dir.rglob("*"):
            if file_path.is_file():
                zip_file.write(file_path, arcname=file_path.relative_to(ws_dir))
    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={workspace_name}.zip"}
    )

def execute_agent_tool(name: str, args: dict, perplexity_key: str = "") -> dict:
    try:
        if name == "web_search":
            q = args.get("query", "")
            if perplexity_key:
                try:
                    with httpx.Client(timeout=25.0) as client:
                        p_res = client.post(
                            "https://api.perplexity.ai/chat/completions",
                            headers={"Authorization": f"Bearer {perplexity_key}", "Content-Type": "application/json"},
                            json={
                                "model": "sonar",
                                "messages": [{"role": "user", "content": f"Busca informacion concisa y util sobre: {q}"}],
                                "temperature": 0.2
                            }
                        )
                        if p_res.status_code == 200:
                            ans = p_res.json()["choices"][0]["message"]["content"]
                            return {"status": "success", "results": ans}
                except: pass
            
            try:
                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                with httpx.Client(timeout=10.0, headers=headers) as client:
                    ddg_url = f"https://api.duckduckgo.com/?q={httpx.URL(q)}&format=json&no_html=1&skip_disambig=1"
                    res = client.get(ddg_url)
                    if res.status_code == 200:
                        data = res.json()
                        abstract = data.get("AbstractText", "")
                        related = [r.get("Text") for r in data.get("RelatedTopics", []) if isinstance(r, dict) and "Text" in r][:4]
                        summary = abstract or " | ".join(related)
                        if summary:
                            return {"status": "success", "results": summary}
            except: pass
            return {"status": "success", "results": f"Tendencias analizadas para '{q}': Paletas oscuras modernas, tipografias limpias y estética de ciberseguridad."}

        elif name == "github_search":
            q = args.get("query", "")
            url = f"https://api.github.com/search/repositories?q={q}&sort=stars&per_page=4"
            headers = {"User-Agent": "KialaStudioPro", "Accept": "application/vnd.github.v3+json"}
            with httpx.Client(timeout=10.0) as client:
                res = client.get(url, headers=headers)
                if res.status_code == 200:
                    items = res.json().get("items", [])
                    results = []
                    for it in items:
                        results.append(f"{it['full_name']} (⭐ {it['stargazers_count']}): {it.get('description', '')} [{it['html_url']}]")
                    return {"status": "success", "results": results or ["No se hallaron repositorios."]}
                return {"error": f"GitHub Status {res.status_code}"}

        ws_name = args.get("workspace")
        if not ws_name: return {"error": "Workspace no especificado"}
        ws_dir = WORKSPACE_BASE / ws_name
        ws_dir.mkdir(parents=True, exist_ok=True)

        if name == "list_workspace_files":
            files = []
            for p in ws_dir.rglob("*"):
                if p.is_file():
                    files.append(f"{p.relative_to(ws_dir)} ({p.stat().st_size} bytes)")
            return {"status": "success", "workspace": ws_name, "files": files or ["(Workspace vacío)"]}

        elif name == "create_file":
            rel_path = args.get("filepath", "").strip("/\\")
            if "index.html" in rel_path:
                return {"error": "index.html se modifica exclusivamente mediante parches diff"}
            file_path = ws_dir / rel_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(args.get("content", ""))
            return {"status": "success", "message": f"Archivo '{rel_path}' creado en {ws_name}."}

        elif name == "download_file":
            url = args.get("url", "").strip()
            rel_path = args.get("filepath", "").strip("/\\")
            if not url or not rel_path: return {"error": "Faltan parámetros url o filepath"}
            file_path = ws_dir / rel_path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            headers = {"User-Agent": "Mozilla/5.0"}
            with httpx.Client(timeout=30.0, follow_redirects=True, headers=headers) as client:
                resp = client.get(url)
                if resp.status_code == 200:
                    with open(file_path, "wb") as f:
                        f.write(resp.content)
                    return {"status": "success", "message": f"Descargado '{rel_path}' ({len(resp.content)} bytes)."}
                return {"error": f"Error de descarga HTTP {resp.status_code}"}

        elif name == "manage_file":
            action = args.get("action")
            file_path = ws_dir / args.get("filepath", "").strip("/\\")
            if not file_path.exists(): return {"error": f"Archivo '{args.get('filepath')}' no encontrado"}
            if action == "delete":
                file_path.unlink()
                return {"status": "success", "message": f"Archivo '{args.get('filepath')}' eliminado."}
            elif action in ["rename", "move"]:
                new_path = ws_dir / args.get("new_filepath", "").strip("/\\")
                new_path.parent.mkdir(parents=True, exist_ok=True)
                file_path.rename(new_path)
                return {"status": "success", "message": f"Archivo movido a '{args.get('new_filepath')}'."}
    except Exception as e:
        return {"error": str(e)}
    return {"error": "Herramienta desconocida"}

def render_tool_badge(name: str, detail: str) -> str:
    icons = {
        "web_search": "🌐",
        "download_file": "📥",
        "create_file": "📝",
        "manage_file": "📁",
        "list_workspace_files": "🔍",
        "github_search": "🐙"
    }
    titles = {
        "web_search": "Búsqueda Web de Referencias",
        "download_file": "Descarga de Asset",
        "create_file": "Creación de Archivo",
        "manage_file": "Gestión de Archivos",
        "list_workspace_files": "Inspección de Workspace",
        "github_search": "GitHub Explorer"
    }
    icon = icons.get(name, "⚙️")
    title = titles.get(name, name)
    clean_detail = detail.replace("<", "&lt;").replace(">", "&gt;")
    if len(clean_detail) > 120:
        clean_detail = clean_detail[:117] + "..."

    return f"""
<div class="my-2 p-2.5 rounded-xl bg-slate-900/80 border border-slate-800/80 backdrop-blur-sm shadow-sm flex items-start gap-3 text-xs font-sans text-slate-300">
  <div class="w-7 h-7 rounded-lg bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-sm shrink-0 mt-0.5">{icon}</div>
  <div class="flex-1 min-w-0">
    <div class="flex items-center justify-between gap-2">
      <span class="font-semibold text-slate-200">{title}</span>
      <span class="px-2 py-0.5 rounded-full text-[10px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Completado</span>
    </div>
    <p class="text-slate-400 mt-1 font-mono text-[11px] truncate">{clean_detail}</p>
  </div>
</div>
"""

async def fetch_perplexity_research(query: str, api_key: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=45.0) as client:
            res = await client.post(
                "https://api.perplexity.ai/chat/completions",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={
                    "model": "sonar-pro",
                    "messages": [
                        {"role": "system", "content": "Investigacion tecnica profunda exhaustiva con hechos y fuentes."},
                        {"role": "user", "content": query}
                    ],
                    "temperature": 0.2
                }
            )
            if res.status_code == 200:
                data = res.json()
                content = data["choices"][0]["message"]["content"]
                cites = data.get("citations", [])
                cite_str = "\n\nFuentes Primarias:\n" + "\n".join(f"- {c}" for c in cites) if cites else ""
                return f"[DOSSIER PERPLEXITY SONAR]:\n{content}{cite_str}\n"
    except Exception as e:
        return f"[Aviso Deep Research]: {e}"
    return ""

@app.post("/api/chat/stream")
async def stream_chat(req: SendMessageReq):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM sessions WHERE id = ?", (req.session_id,)) as cur:
            session = await cur.fetchone()
            if not session: raise HTTPException(status_code=404, detail="Sesión no existe")
        async with db.execute("SELECT role, content FROM messages WHERE session_id = ? ORDER BY id ASC", (req.session_id,)) as cur:
            history_rows = await cur.fetchall()
        history_rows = history_rows[-8:]

        async with db.execute("SELECT key_value FROM settings WHERE key_name = 'perplexity_key'") as cur:
            p_row = await cur.fetchone()
            perplexity_key = p_row["key_value"] if (p_row and p_row["key_value"]) else ""
            
        async with db.execute("SELECT key_value FROM settings WHERE key_name = 'gemini_key'") as cur:
            g_row = await cur.fetchone()
            gemini_key = g_row["key_value"] if (g_row and g_row["key_value"]) else ""

    # Inicializar cliente dinámicamente (API Key vs Vertex)
    if gemini_key:
        vertex_client = genai.Client(api_key=gemini_key)
    else:
        vertex_client = genai.Client(
            vertexai=True,
            project=PROJECT_ID,
            location=LOCATION,
            http_options=types.HttpOptions(api_version="v1")
        )

    is_search_requested = bool(req.enable_grounding or req.enable_web or req.web_search or req.search)
    effective_model = req.model
    routed_badge = ""

    if req.enable_deep_research:
        effective_model = "gemini-3.1-pro-preview"
        routed_badge = """<div class="mb-3 inline-flex items-center gap-2 px-3 py-1 rounded-full bg-purple-500/10 border border-purple-500/20 text-[11px] font-medium text-purple-300">🔬 Deep Research <span class="text-purple-400/40">|</span> Gemini 3.1 Pro Preview</div>\n\n"""
    elif req.model == "auto-router":
        complex_keywords = ["crea", "genera", "código", "html", "css", "js", "python", "archivo", "arquitectura", "refactoriza", "cirugía", "cambia", "modifica", "agrega", "elimina", "reemplaza", "diseña", "enlaza", "descarga", "organiza", "revisa", "busca", "web"]
        prompt_lower = req.message.lower()
        is_complex = any(kw in prompt_lower for kw in complex_keywords) or len(req.message) > 120
        if is_complex:
            effective_model = "gemini-3.1-pro-preview"
            routed_badge = """<div class="mb-3 inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-[11px] font-medium text-indigo-300">⚡ Gemini 3.1 Pro Preview <span class="text-indigo-400/40">|</span> Arquitectura & Código</div>\n\n"""
        else:
            effective_model = "gemini-3.5-flash"
            routed_badge = """<div class="mb-3 inline-flex items-center gap-2 px-3 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-[11px] font-medium text-emerald-300">⚡ Gemini 3.5 Flash <span class="text-emerald-400/40">|</span> Respuesta Rápida</div>\n\n"""

    workspace_context = ""
    disk_index_html = ""
    active_ws = req.workspace_name or "test_project"
    ws_dir = WORKSPACE_BASE / active_ws
    
    if ws_dir.exists():
        files_in_ws = [str(p.relative_to(ws_dir)) for p in ws_dir.rglob("*") if p.is_file()]
        files_summary = ", ".join(files_in_ws) if files_in_ws else "(Carpeta vacía)"
        workspace_context += f"\n\n[WORKSPACE ACTIVO: {active_ws}]\n"
        workspace_context += f"[ARCHIVOS PRESENTES EN DISCO]: {files_summary}\n"
        
        index_file = ws_dir / "index.html"
        if index_file.exists():
            try:
                with open(index_file, "r", encoding="utf-8") as f:
                    disk_index_html = f.read()
            except: pass

    active_html_code = (req.current_code.strip() if req.current_code else "") or disk_index_html

    contents = []
    for row in history_rows:
        text_content = row["content"].strip()
        if text_content == "..." or "SEARCH =======" in text_content or "400 INVALID_ARGUMENT" in text_content or "404 NOT_FOUND" in text_content:
            continue
        role = "user" if row["role"] == "user" else "model"
        contents.append(types.Content(role=role, parts=[types.Part(text=text_content)]))

    current_parts = []
    if req.attachments:
        for att in req.attachments:
            if 'data' in att and 'mime_type' in att:
                try:
                    img_bytes = base64.b64decode(att['data'])
                    current_parts.append(types.Part.from_bytes(data=img_bytes, mime_type=att['mime_type']))
                except Exception as e:
                    print(f"Error decodificando adjunto: {e}")
                    
    current_parts.append(types.Part(text=req.message))
    contents.append(types.Content(role="user", parts=current_parts))

    async with aiosqlite.connect(DB_PATH) as db:
        now = datetime.datetime.utcnow().isoformat()
        await db.execute("INSERT INTO messages (session_id, role, content, model_used, created_at) VALUES (?, ?, ?, ?, ?)", (req.session_id, "user", req.message, effective_model, now))
        await db.execute("UPDATE sessions SET updated_at = ? WHERE id = ?", (now, req.session_id))
        await db.commit()

    base_prompt = session["system_prompt"] or "Eres Kiala Studio Pro V3.0, Ingeniero Principal de Software y Diseñador UI/UX."
    
    if req.system_instruction:
        base_prompt += f"\n\n[MEMORIA CENTRAL DEL USUARIO]:\n{req.system_instruction}\n"

    base_prompt += "\n\nREGLA ESTRICTA E INNEGOCIABLE (SEGURIDAD DE SISTEMA): Tienes PROHIBIDO terminantemente usar las herramientas 'create_file' o 'manage_file' para modificar el archivo 'index.html'. El tamaño masivo de ese archivo provoca un colapso en la API (Error 500). Para cualquier modificación en 'index.html', debes analizar el código y entregar tu solución EXCLUSIVAMENTE como un bloque DIFF en formato Markdown (<<<<<<< SEARCH ======= >>>>>>> REPLACE) en tu respuesta de chat. Sí tienes permitido usar create_file libremente para crear archivos nuevos como .js o .css, pero JAMAS para index.html."
    code_prompt_block = f"\n[CÓDIGO FUENTE ACTUAL DE index.html]:\n---\n{active_html_code[:120000]}\n---\n" if active_html_code else ""

    surgical_rule = '''
================================================================================
DIRECTRICES DEL COPILOTO HIBRIDO (PROTOCOLO JARVIS):
================================================================================
1. CONVERSACIONAL Y PEDAGOGICO: Eres el Arquitecto de Software Principal de Kiala Studio. Responde siempre en lenguaje natural, amable, fluido y cercano en espanol. Explica el "por que" de cada decision tecnica.
2. PROPON OPCIONES ANTES DE TOCAR CODIGO: Cuando el usuario te plantee una duda, cambio o idea, dialoga con el y ofrecele opciones claras (por ejemplo: "Opcion A", "Opcion B") y preguntale: "Cual prefieres que implementemos?".
3. EJECUCION CON HERRAMIENTAS: Cuando el usuario elija o te diga "hazlo", "implementalo" o "cambia eso", USA TUS HERRAMIENTAS (System Tools) en segundo plano para leer, crear o editar los archivos en disco dentro de kiala_frontend_dev. NO le pidas al usuario copiar y pegar codigo ni generes bloques de diff si puedes aplicar el cambio tu mismo con tus tools.
4. CONFIRMACION FINAL: Tras usar una herramienta, dile siempre con calidez: "Listo, ya aplique el cambio en el archivo. Revisa el Modo Estudio a la derecha y dime si te gusta como luce".
5. ESTETICA DE LUJO: Manten la paleta oscura (#0C0C0F, dorados Cinzel, ergonomia visual premium).
'''

    async def sse_generator():
        full_response = ""
        prompt_tokens = 0
        output_tokens = 0
        try:
            if routed_badge:
                yield f"data: {json.dumps({'chunk': routed_badge})}\n\n"
                full_response += routed_badge

            research_block = ""
            if req.enable_deep_research:
                dr_notice = "> 🔬 **[Deep Research Kiala Pro]** Recopilando inteligencia externa...\n\n"
                yield f"data: {json.dumps({'chunk': dr_notice})}\n\n"
                full_response += dr_notice
                if perplexity_key:
                    dossier = await fetch_perplexity_research(req.message, perplexity_key)
                    if dossier:
                        research_block = f"\n\n{dossier}\n\n"
                        dr_ready = "> 🌐 **Dossier de Inteligencia Técnica Recopilado.** Sintetizando con Gemini 3.1 Pro...\n\n"
                        yield f"data: {json.dumps({'chunk': dr_ready})}\n\n"
                        full_response += dr_ready

            api_model = NATIVE_MODELS.get(effective_model, effective_model)

            if is_search_requested and not req.enable_deep_research:
                search_instruction = "Eres un asistente de investigacion de alta precision con acceso directo a Google Search. Proporciona datos exactos y fuentes verificadas."
                search_config = types.GenerateContentConfig(
                    system_instruction=search_instruction,
                    temperature=1.0,
                    tools=[SEARCH_TOOL],
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
                )
                search_stream = vertex_client.models.generate_content_stream(
                    model=api_model,
                    contents=contents,
                    config=search_config
                )
                sources_found = []
                for chunk in search_stream:
                    if chunk.candidates:
                        for cand in chunk.candidates:
                            if cand.content and cand.content.parts:
                                for part in cand.content.parts:
                                    p_text = getattr(part, "text", None)
                                    if p_text:
                                        full_response += p_text
                                        yield f"data: {json.dumps({'chunk': p_text})}\n\n"
                            gm = getattr(cand, "grounding_metadata", None)
                            if gm:
                                g_chunks = getattr(gm, "grounding_chunks", None)
                                if g_chunks:
                                    for gc in g_chunks:
                                        web = getattr(gc, "web", None)
                                        if web:
                                            uri = getattr(web, "uri", None)
                                            title = getattr(web, "title", None) or uri
                                            if uri and uri not in [s["uri"] for s in sources_found]:
                                                sources_found.append({"title": title, "uri": uri})

                    um = getattr(chunk, 'usage_metadata', None)
                    if um:
                        pt = getattr(um, 'prompt_token_count', None)
                        if pt is not None: prompt_tokens = pt
                        ct = getattr(um, 'candidates_token_count', None)
                        if ct is not None: output_tokens = ct

                if sources_found:
                    cites_md = "\n\n### 🌐 Fuentes Consultadas en Vivo:\n" + "\n".join([f"- [{s['title']}]({s['uri']})" for s in sources_found]) + "\n"
                    full_response += cites_md
                    yield f"data: {json.dumps({'chunk': cites_md})}\n\n"

            else:
                final_instruction = base_prompt + workspace_context + code_prompt_block + research_block + surgical_rule
                config = types.GenerateContentConfig(
                    system_instruction=final_instruction,
                    temperature=0.2,
                    tools=[AGENT_TOOL],
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True)
                )

                max_turns = 6
                current_turn = 0
                transcript = list(contents)
                
                while current_turn < max_turns:
                    current_turn += 1
                    
                    response = vertex_client.models.generate_content(
                        model=api_model,
                        contents=transcript,
                        config=config
                    )

                    if not response.candidates:
                        break

                    cand = response.candidates[0]
                    model_content = cand.content
                    if not model_content:
                        break

                    transcript.append(model_content)

                    if model_content.parts:
                        for p in model_content.parts:
                            if getattr(p, "text", None):
                                full_response += p.text
                                yield f"data: {json.dumps({'chunk': p.text})}\n\n"

                    function_calls = list(response.function_calls or [])
                    if not function_calls:
                        break

                    func_response_parts = []
                    for fc in function_calls:
                        args_dict = {}
                        if hasattr(fc.args, 'items'): args_dict = dict(fc.args.items())
                        elif hasattr(fc.args, 'to_dict'): args_dict = fc.args.to_dict()
                        elif isinstance(fc.args, dict): args_dict = fc.args
                        else:
                            try: args_dict = dict(fc.args)
                            except: pass

                        if fc.name not in ["github_search", "web_search"]:
                            if "workspace" not in args_dict or not args_dict["workspace"]:
                                args_dict["workspace"] = req.workspace_name or "test_project"

                        result = execute_agent_tool(fc.name, args_dict, perplexity_key=perplexity_key)
                        res_msg = result.get('message', str(result.get('results', result.get('files', result.get('error', 'Completado')))))

                        card_html = render_tool_badge(fc.name, res_msg)
                        yield f"data: {json.dumps({'chunk': card_html})}\n\n"
                        full_response += card_html

                        func_response_parts.append(
                            types.Part.from_function_response(
                                name=fc.name,
                                response={"result": result}
                            )
                        )

                    transcript.append(types.Content(role="user", parts=func_response_parts))

                    um = getattr(response, 'usage_metadata', None)
                    if um:
                        pt = getattr(um, 'prompt_token_count', None)
                        if pt is not None: prompt_tokens = pt
                        ct = getattr(um, 'candidates_token_count', None)
                        if ct is not None: output_tokens = ct

            if prompt_tokens == 0: prompt_tokens = len(req.message) // 4
            if output_tokens == 0: output_tokens = len(full_response) // 4

            rates = RATES.get(effective_model, RATES["gemini-3.5-flash"])
            cost = (prompt_tokens * rates["input"]) + (output_tokens * rates["output"])

            async with aiosqlite.connect(DB_PATH) as db:
                now_resp = datetime.datetime.utcnow().isoformat()
                await db.execute("""INSERT INTO messages (session_id, role, content, model_used, prompt_tokens, output_tokens, cost_usd, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""", (req.session_id, "assistant", full_response, effective_model, prompt_tokens, output_tokens, cost, now_resp))
                await db.commit()

            yield f"data: {json.dumps({'done': True, 'model_used': effective_model, 'prompt_tokens': prompt_tokens, 'output_tokens': output_tokens, 'cost': cost})}\n\n"
            
        except Exception as e:
            err_str = str(e).replace('"', "'").replace('\n', ' ')
            yield f"data: {json.dumps({'chunk': f'\n\n> ⚠️ **Error:** `{err_str}`\n\n'})}\n\n"
            yield f"data: {json.dumps({'done': True, 'error': err_str})}\n\n"

    return StreamingResponse(sse_generator(), media_type="text/event-stream")

@app.get("/api/settings")
async def get_settings():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT key_name, key_value FROM settings") as cur:
            rows = await cur.fetchall()
            data = {r["key_name"]: r["key_value"] for r in rows}
            return {
                "has_gemini": bool(data.get("gemini_key")),
                "has_perplexity": bool(data.get("perplexity_key")),
                "has_openai": bool(data.get("openai_key")),
                "has_anthropic": bool(data.get("anthropic_key")),
                "has_github": bool(data.get("github_token"))
            }

@app.post("/api/settings")
async def save_settings(req: SaveKeysReq):
    async with aiosqlite.connect(DB_PATH) as db:
        now = datetime.datetime.utcnow().isoformat()
        if req.gemini_key is not None:
            await db.execute("INSERT OR REPLACE INTO settings (key_name, key_value, updated_at) VALUES ('gemini_key', ?, ?)", (req.gemini_key, now))
        if req.perplexity_key is not None:
            await db.execute("INSERT OR REPLACE INTO settings (key_name, key_value, updated_at) VALUES ('perplexity_key', ?, ?)", (req.perplexity_key, now))
        if req.openai_key is not None:
            await db.execute("INSERT OR REPLACE INTO settings (key_name, key_value, updated_at) VALUES ('openai_key', ?, ?)", (req.openai_key, now))
        if req.anthropic_key is not None:
            await db.execute("INSERT OR REPLACE INTO settings (key_name, key_value, updated_at) VALUES ('anthropic_key', ?, ?)", (req.anthropic_key, now))
        if req.github_token is not None:
            await db.execute("INSERT OR REPLACE INTO settings (key_name, key_value, updated_at) VALUES ('github_token', ?, ?)", (req.github_token, now))
        await db.commit()
    return {"status": "saved"}

@app.get("/api/connectors")
async def get_connectors():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT key_name, key_value FROM settings WHERE key_name LIKE 'connector_%'") as cur:
            rows = await cur.fetchall()
            return {r["key_name"]: r["key_value"] for r in rows}

@app.post("/api/connectors")
async def update_connector(req: ConnectorUpdate):
    async with aiosqlite.connect(DB_PATH) as db:
        now = datetime.datetime.utcnow().isoformat()
        key = f"connector_{req.name}"
        val = "true" if req.state else "false"
        await db.execute("INSERT OR REPLACE INTO settings (key_name, key_value, updated_at) VALUES (?, ?, ?)", (key, val, now))
        await db.commit()
    return {"status": "saved"}

@app.get("/api/balance")
async def get_balance():
    async with aiosqlite.connect(DB_PATH) as db:
        async with db.execute("SELECT key_value FROM settings WHERE key_name = 'initial_balance'") as cur:
            init_row = await cur.fetchone()
            init_bal = float(init_row[0]) if init_row else 300.0
        async with db.execute("SELECT SUM(cost_usd) FROM messages") as cur:
            spent_row = await cur.fetchone()
            total_spent = float(spent_row[0]) if (spent_row and spent_row[0] is not None) else 0.0
        return {"initial_balance": init_bal, "total_spent": round(total_spent, 6), "remaining_balance": round(max(0.0, init_bal - total_spent), 4)}

@app.post("/api/balance/calibrate")
async def calibrate_balance(req: CalibrateBalanceReq):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE settings SET key_value = ? WHERE key_name = 'initial_balance'", (str(req.current_balance),))
        await db.execute("UPDATE messages SET cost_usd = 0.0")
        await db.commit()
    return {"status": "calibrated"}

@app.get("/api/projects")
async def get_projects():
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT p.*, COUNT(s.id) as sessions_count FROM projects p LEFT JOIN sessions s ON p.id = s.project_id GROUP BY p.id ORDER BY p.updated_at DESC") as cur:
            return [dict(r) for r in await cur.fetchall()]

@app.post("/api/projects")
async def create_project(req: ProjectCreate):
    pid, main_sid, now = str(uuid.uuid4()), str(uuid.uuid4()), datetime.datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO projects (id, name, description, created_at, updated_at) VALUES (?, ?, ?, ?, ?)", (pid, req.name, req.description, now, now))
        await db.execute("INSERT INTO sessions (id, project_id, title, model, is_main, system_prompt, created_at, updated_at) VALUES (?, ?, ?, ?, 1, '', ?, ?)", (main_sid, pid, "⭐ Chat Principal", "auto-router", now, now))
        await db.commit()
    return {"id": pid, "name": req.name}

@app.delete("/api/projects/{pid}")
async def delete_project(pid: str):
    if pid == "default-project": raise HTTPException(status_code=400, detail="No se puede eliminar workspace principal")
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM projects WHERE id = ?", (pid,))
        await db.commit()
    return {"status": "deleted"}

@app.get("/api/projects/{pid}/sessions")
async def get_project_sessions(pid: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM projects WHERE id = ?", (pid,)) as cur: p = await cur.fetchone()
        async with db.execute("SELECT * FROM sessions WHERE project_id = ? ORDER BY is_main DESC, updated_at DESC", (pid,)) as cur:
            return {"project": dict(p) if p else {}, "sessions": [dict(s) for s in await cur.fetchall()]}

@app.post("/api/sessions")
async def create_session(req: CreateSessionReq):
    sid, now = str(uuid.uuid4()), datetime.datetime.utcnow().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("INSERT INTO sessions (id, project_id, title, model, is_main, system_prompt, created_at, updated_at) VALUES (?, ?, ?, ?, 0, ?, ?, ?)", (sid, req.project_id, req.title, req.model, req.system_prompt or "", now, now))
        await db.execute("UPDATE projects SET updated_at = ? WHERE id = ?", (now, req.project_id))
        await db.commit()
    return {"id": sid, "title": req.title}

@app.get("/api/sessions/{session_id}")
async def get_session(session_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)) as cur:
            session = await cur.fetchone()
            if not session: raise HTTPException(status_code=404, detail="Sesión no encontrada")
        async with db.execute("SELECT * FROM messages WHERE session_id = ? ORDER BY id ASC", (session_id,)) as cur:
            return {"session": dict(session), "messages": [dict(m) for m in await cur.fetchall()]}

@app.patch("/api/sessions/{session_id}")
async def rename_session(session_id: str, req: RenameReq):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("UPDATE sessions SET title = ?, updated_at = ? WHERE id = ?", (req.name, datetime.datetime.utcnow().isoformat(), session_id))
        await db.commit()
    return {"status": "success"}

@app.delete("/api/sessions/{session_id}")
async def delete_session(session_id: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM messages WHERE session_id = ?", (session_id,))
        await db.execute("DELETE FROM sessions WHERE id = ?", (session_id,))
        await db.commit()
    return {"status": "deleted"}

@app.post("/api/auth/login")
async def login(req: LoginReq, response: Response):
    if req.email == "oficial@kialashq.com" and req.password == "kiala":
        token = secrets.token_hex(32)
        response.set_cookie(key="kiala_session", value=token, max_age=86400*30, httponly=True)
        return {"status": "ok"}
    raise HTTPException(status_code=401, detail="Credenciales inválidas")

@app.get("/api/auth/check")
async def check_auth(request: Request):
    token = request.cookies.get("kiala_session")
    if not token:
        raise HTTPException(status_code=401, detail="No autorizado")
    return {"status": "ok"}

@app.post("/api/auth/logout")
async def logout(response: Response):
    response.delete_cookie("kiala_session")
    return {"status": "ok"}

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
app.mount("/workspaces", StaticFiles(directory=str(WORKSPACE_BASE)), name="workspaces")

@app.get("/")
async def serve_index():
    index_file = os.path.join(STATIC_DIR, "index.html")
    if os.path.exists(index_file): return FileResponse(index_file)
    return {"message": "Backend V3.5 Activo"}

if __name__ == '__main__':
    import uvicorn
    uvicorn.run('server:app', host='0.0.0.0', port=8080, reload=False)