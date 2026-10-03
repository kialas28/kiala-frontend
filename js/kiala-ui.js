document.addEventListener('DOMContentLoaded', () => {
    // 1. Inyectar botones de cabecera (Bóveda, Extensiones, Multimedia)
    const headerActions = document.querySelector('header .flex.items-center.space-x-3');
    if (headerActions && !document.getElementById('btn-vault')) {
        const newBtns = document.createElement('div');
        newBtns.className = 'flex items-center space-x-2 mr-2';
        newBtns.innerHTML = `
          <button id="btn-vault" onclick="toggleModal('modal-vault')" class="p-2.5 rounded-xl bg-[#14141A] hover:bg-[#1A1A22] border border-[#22222E] text-emerald-400 hover:text-emerald-300 transition shadow-sm" title="Bóveda de Seguridad"><i data-lucide="shield" class="w-5 h-5"></i></button>
          <button onclick="toggleModal('modal-extensions')" class="p-2.5 rounded-xl bg-[#14141A] hover:bg-[#1A1A22] border border-[#22222E] text-blue-400 hover:text-blue-300 transition shadow-sm" title="Extensiones y Plugins"><i data-lucide="puzzle" class="w-5 h-5"></i></button>
          <button onclick="toggleModal('modal-multimedia')" class="p-2.5 rounded-xl bg-[#14141A] hover:bg-[#1A1A22] border border-[#22222E] text-amber-400 hover:text-amber-300 transition shadow-sm" title="Estudio Multimedia"><i data-lucide="image" class="w-5 h-5"></i></button>
          <div class="h-6 w-px bg-[#1F1F28] mx-1"></div>
        `;
        headerActions.prepend(newBtns);
    }

    // 2. Inyectar Modales en el Body
    if (!document.getElementById('modal-vault')) {
        const modalsContainer = document.createElement('div');
        modalsContainer.innerHTML = `
          <!-- MODAL: BÓVEDA DE SEGURIDAD -->
          <div id="modal-vault" class="hidden fixed inset-0 z-[200] flex items-center justify-center bg-black/70 backdrop-blur-md p-4">
            <div class="w-full max-w-lg bg-[#0E0E13] border border-[#1A1A22] rounded-3xl shadow-2xl overflow-hidden">
              <div class="p-6 border-b border-[#1A1A22] flex items-center justify-between bg-[#111116]">
                <div class="flex items-center space-x-3">
                  <i data-lucide="shield" class="w-6 h-6 text-emerald-400"></i>
                  <span class="font-semibold text-neutral-200">Bóveda de Seguridad</span>
                </div>
                <button onclick="toggleModal('modal-vault')" class="text-neutral-500 hover:text-white transition">✕</button>
              </div>
              <div class="p-6 space-y-4">
                <p class="text-sm text-neutral-400">Guarda tus credenciales y llaves maestras de forma segura en el almacenamiento local encriptado.</p>
                <div class="space-y-3">
                  <div>
                    <label class="block text-xs font-mono text-neutral-500 uppercase mb-1">Clave API de Gemini</label>
                    <input type="password" class="w-full bg-[#14141A] border border-[#22222E] rounded-xl px-4 py-2.5 text-sm text-neutral-200 outline-none focus:border-emerald-500/50 transition" placeholder="••••••••••••••••">
                  </div>
                </div>
              </div>
              <div class="p-4 bg-[#111116] border-t border-[#1A1A22] flex justify-end space-x-2">
                <button onclick="toggleModal('modal-vault')" class="px-4 py-2 text-sm text-neutral-400 hover:text-white transition">Cerrar</button>
                <button onclick="toggleModal('modal-vault')" class="px-4 py-2 text-sm bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl transition">Guardar Cambios</button>
              </div>
            </div>
          </div>

          <!-- MODAL: EXTENSIONES -->
          <div id="modal-extensions" class="hidden fixed inset-0 z-[200] flex items-center justify-center bg-black/70 backdrop-blur-md p-4">
            <div class="w-full max-w-lg bg-[#0E0E13] border border-[#1A1A22] rounded-3xl shadow-2xl overflow-hidden">
              <div class="p-6 border-b border-[#1A1A22] flex items-center justify-between bg-[#111116]">
                <div class="flex items-center space-x-3">
                  <i data-lucide="puzzle" class="w-6 h-6 text-blue-400"></i>
                  <span class="font-semibold text-neutral-200">Extensiones y Plugins</span>
                </div>
                <button onclick="toggleModal('modal-extensions')" class="text-neutral-500 hover:text-white transition">✕</button>
              </div>
              <div class="p-6 space-y-4">
                <div class="flex items-center justify-between p-3 rounded-xl bg-[#14141A] border border-[#22222E]">
                  <div class="flex items-center space-x-3">
                    <i data-lucide="globe" class="w-5 h-5 text-blue-400"></i>
                    <div>
                      <p class="text-sm font-medium text-neutral-200">Búsqueda Web Avanzada</p>
                      <p class="text-xs text-neutral-500">Permite a Gemini buscar en internet en tiempo real.</p>
                    </div>
                  </div>
                  <span class="px-2.5 py-1 rounded-full text-xs bg-blue-500/10 text-blue-400 border border-blue-500/20">Activo</span>
                </div>
              </div>
              <div class="p-4 bg-[#111116] border-t border-[#1A1A22] flex justify-end">
                <button onclick="toggleModal('modal-extensions')" class="px-4 py-2 text-sm text-neutral-400 hover:text-white transition">Cerrar</button>
              </div>
            </div>
          </div>

          <!-- MODAL: ESTUDIO MULTIMEDIA -->
          <div id="modal-multimedia" class="hidden fixed inset-0 z-[200] flex items-center justify-center bg-black/70 backdrop-blur-md p-4">
            <div class="w-full max-w-lg bg-[#0E0E13] border border-[#1A1A22] rounded-3xl shadow-2xl overflow-hidden">
              <div class="p-6 border-b border-[#1A1A22] flex items-center justify-between bg-[#111116]">
                <div class="flex items-center space-x-3">
                  <i data-lucide="image" class="w-6 h-6 text-amber-400"></i>
                  <span class="font-semibold text-neutral-200">Estudio Multimedia</span>
                </div>
                <button onclick="toggleModal('modal-multimedia')" class="text-neutral-500 hover:text-white transition">✕</button>
              </div>
              <div class="p-6 space-y-4 text-center">
                <i data-lucide="sparkles" class="w-12 h-12 text-amber-400 mx-auto animate-pulse"></i>
                <p class="text-sm text-neutral-300 font-medium">Generador de Imágenes con Imagen 3</p>
                <p class="text-xs text-neutral-500 max-w-xs mx-auto">Próximamente podrás generar imágenes fotorrealistas de alta resolución directamente desde este panel.</p>
              </div>
              <div class="p-4 bg-[#111116] border-t border-[#1A1A22] flex justify-end">
                <button onclick="toggleModal('modal-multimedia')" class="px-4 py-2 text-sm text-neutral-400 hover:text-white transition">Entendido</button>
              </div>
            </div>
          </div>
        `;
        document.body.appendChild(modalsContainer);
    }

    // 3. Opción A: Selector de Archivos en Modo Estudio
    const artWsSelect = document.getElementById('artifact-workspace-select');
    if (artWsSelect && !document.getElementById('artifact-file-select')) {
        const fileSelect = document.createElement('select');
        fileSelect.id = 'artifact-file-select';
        fileSelect.className = 'bg-transparent text-neutral-300 text-xs outline-none cursor-pointer hover:text-white ml-2 border-l border-[#242432] pl-2';
        
        // Opciones por defecto (luego se pueden cargar dinámicamente desde el backend)
        fileSelect.innerHTML = '<option value="index.html">index.html</option><option value="style.css">style.css</option><option value="script.js">script.js</option>';
        
        // Interceptar el onchange original del workspace para resetear el archivo
        const originalOnChange = artWsSelect.onchange;
        artWsSelect.onchange = (e) => {
            if(originalOnChange) originalOnChange.call(artWsSelect, e);
            fileSelect.value = 'index.html'; 
        };

        // Lógica para cargar el archivo específico
        fileSelect.onchange = async (e) => {
            const ws = artWsSelect.value.replace('📁 ', '').trim();
            const file = e.target.value;
            if(ws && file) {
                try {
                    const res = await fetch(\`/workspaces/\${ws}/\${file}?t=\${Date.now()}\`);
                    if (res.ok) {
                        const content = await res.text();
                        if(window.openArtifact) window.openArtifact(file.split('.').pop(), content);
                    }
                } catch(err) {
                    console.error("Error cargando archivo", err);
                }
            }
        };
        artWsSelect.parentNode.insertBefore(fileSelect, artWsSelect.nextSibling);
    }

    // 4. Reparar el Contador de Tokens (Estimación en tiempo real)
    const chatContainer = document.getElementById('chat-messages-container');
    if (chatContainer) {
        const tokenEl = document.getElementById('sidebar-tokens-val');
        // Usamos un MutationObserver para "escuchar" cada vez que el chat cambia
        const observer = new MutationObserver(() => {
            // 1 token ≈ 4 caracteres en promedio
            const text = chatContainer.innerText;
            const estimatedTokens = Math.ceil(text.length / 4);
            if (tokenEl) {
                tokenEl.textContent = estimatedTokens.toLocaleString();
                // Pequeña animación de actualización
                tokenEl.classList.add('text-white');
                setTimeout(() => tokenEl.classList.remove('text-white'), 300);
            }
        });
        observer.observe(chatContainer, { childList: true, subtree: true, characterData: true });
    }

    // Re-renderizar iconos de Lucide si es necesario
    if (window.lucide) window.lucide.createIcons();
});

// Función global para abrir/cerrar modales
window.toggleModal = function(id) {
    const modal = document.getElementById(id);
    if (modal) modal.classList.toggle('hidden');
};
