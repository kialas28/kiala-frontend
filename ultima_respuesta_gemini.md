<div class="mb-3 inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-[11px] font-medium text-indigo-300">⚡ Gemini 3.1 Pro Preview <span class="text-indigo-400/40">|</span> Arquitectura & Código</div>

El problema radica en que la función `openArtifact` (que es llamada internamente por `loadWorkspaceFiles`) ejecuta por defecto `switchArtifactTab('preview')`. Esta acción oculta completamente el contenedor del código (`artifact-view-code`) y le asigna el 100% del ancho (`w-full`) a la vista previa, impidiendo que se muestre el modo "Split-View 50/50" que está preparado en la estructura HTML.

Para solucionarlo, inyectaremos la lógica de **Split-View (50/50)** directamente dentro de `loadWorkspaceFiles` justo después de cargar el artefacto. Además, parchearemos `switchArtifactTab` para que, si el usuario decide hacer clic en las pestañas posteriormente, las vistas restauren correctamente su ancho completo (`w-full`) sin romper la cuadrícula Flexbox.

Aquí tienes el parche quirúrgico para aplicarlo en `index.html`:

```diff
<<<<<<< SEARCH
    function switchArtifactTab(tab) {
        const btnCode = document.getElementById('btn-tab-code');
        const btnPrev = document.getElementById('btn-tab-preview');
        const viewCode = document.getElementById('artifact-view-code');
        const viewPrev = document.getElementById('artifact-view-preview');

        if (tab === 'code') {
            btnCode.className = 'px-3 py-1 rounded-lg bg-[#252534] text-white';
            btnPrev.className = 'px-3 py-1 rounded-lg text-neutral-400 hover:text-white';
            viewCode.classList.remove('hidden'); viewCode.classList.add('flex');
            viewPrev.classList.add('hidden');
        } else {
            btnPrev.className = 'px-3 py-1 rounded-lg bg-[#252534] text-white';
            btnCode.className = 'px-3 py-1 rounded-lg text-neutral-400 hover:text-white';
            viewPrev.classList.remove('hidden');
            viewCode.classList.add('hidden'); viewCode.classList.remove('flex');
        }
    }
=======
    function switchArtifactTab(tab) {
        const btnCode = document.getElementById('btn-tab-code');
        const btnPrev = document.getElementById('btn-tab-preview');
        const viewCode = document.getElementById('artifact-view-code');
        const viewPrev = document.getElementById('artifact-view-preview');

        if (tab === 'code') {
            btnCode.className = 'px-3 py-1 rounded-lg bg-[#252534] text-white';
            btnPrev.className = 'px-3 py-1 rounded-lg text-neutral-400 hover:text-white';
            viewCode.classList.remove('hidden', 'w-1/2'); viewCode.classList.add('flex', 'w-full');
            viewPrev.classList.add('hidden'); viewPrev.classList.remove('w-1/2');
        } else {
            btnPrev.className = 'px-3 py-1 rounded-lg bg-[#252534] text-white';
            btnCode.className = 'px-3 py-1 rounded-lg text-neutral-400 hover:text-white';
            viewPrev.classList.remove('hidden', 'w-1/2'); viewPrev.classList.add('w-full');
            viewCode.classList.add('hidden'); viewCode.classList.remove('flex', 'w-1/2');
        }
    }
>>>>>>> REPLACE
```

```diff
<<<<<<< SEARCH
    // --- CARGAR AUTOMÁTICAMENTE EL INDEX.HTML DEL WORKSPACE AL SELECCIONARLO ---
    async function loadWorkspaceFiles(wsName) {
    if (!wsName) return;
    // Extraer unicamente caracteres alfanumericos limpios eliminando emojis como 📁
    let cleanName = wsName.replace(/[^a-zA-Z0-9_-]/g, '').trim();
    if (!cleanName) return;
    try {
        const res = await fetch('/workspaces/' + cleanName + '/index.html?t=' + Date.now());
        if (res.ok) {
            const content = await res.text();
            openArtifact('html', content, cleanName + '/index.html');
            const panel = document.getElementById('artifact-panel');
            if (panel) {
                panel.classList.remove('hidden');
                panel.classList.add('flex');
                panel.style.display = 'flex';
            }
            console.log('[Kiala Studio] Artifact Panel abierto con exito para:', cleanName);
        } else {
            console.warn('[Kiala Studio] No se encontro index.html en:', cleanName, '(Status ' + res.status + ')');
        }
    } catch(e) {
        console.error('[Kiala Studio] Error cargando workspace:', e);
    }
}
=======
    // --- CARGAR AUTOMÁTICAMENTE EL INDEX.HTML DEL WORKSPACE AL SELECCIONARLO ---
    async function loadWorkspaceFiles(wsName) {
    if (!wsName) return;
    // Extraer unicamente caracteres alfanumericos limpios eliminando emojis como 📁
    let cleanName = wsName.replace(/[^a-zA-Z0-9_-]/g, '').trim();
    if (!cleanName) return;
    try {
        const res = await fetch('/workspaces/' + cleanName + '/index.html?t=' + Date.now());
        if (res.ok) {
            const content = await res.text();
            openArtifact('html', content, cleanName + '/index.html');
            const panel = document.getElementById('artifact-panel');
            if (panel) {
                panel.classList.remove('hidden');
                panel.classList.add('flex');
                panel.style.display = 'flex';
                
                // Forzar Split-View 50/50 (Código + Preview) sin romper Flexbox
                const viewCode = document.getElementById('artifact-view-code');
                const viewPrev = document.getElementById('artifact-view-preview');
                if (viewCode && viewPrev) {
                    viewCode.classList.remove('hidden', 'w-full');
                    viewCode.classList.add('flex', 'w-1/2');
                    viewPrev.classList.remove('hidden', 'w-full');
                    viewPrev.classList.add('flex', 'w-1/2');
                    
                    // Actualizar botones de tab para reflejar el estado mixto
                    const btnCode = document.getElementById('btn-tab-code');
                    const btnPrev = document.getElementById('btn-tab-preview');
                    if (btnCode) btnCode.className = 'px-3 py-1 rounded-lg bg-[#252534] text-white';
                    if (btnPrev) btnPrev.className = 'px-3 py-1 rounded-lg bg-[#252534] text-white';
                }
            }
            console.log('[Kiala Studio] Artifact Panel abierto con exito en Split-View para:', cleanName);
        } else {
            console.warn('[Kiala Studio] No se encontro index.html en:', cleanName, '(Status ' + res.status + ')');
        }
    } catch(e) {
        console.error('[Kiala Studio] Error cargando workspace:', e);
    }
}
>>>>>>> REPLACE
```

### ¿Qué hace esta corrección?
1. **Fuerza el Split-View:** Al cargar el workspace, en lugar de dejar que `openArtifact` oculte el código, inyectamos clases de Tailwind (`w-1/2` y `flex`) a ambos contenedores. Esto hace que compartan el 50% del espacio de la pantalla de forma nativa.
2. **Estilos de Pestañas:** Ilumina ambas pestañas ("Vista Previa" y "Código") para indicar visualmente que el modo mixto está activo.
3. **Protección de Tabs:** Se actualizó `switchArtifactTab` para que, si el usuario decide enfocarse en una sola vista haciendo clic en los botones, se elimine el `w-1/2` y se restaure el `w-full`, manteniendo la integridad del diseño.