// js/supabase-client.js

// 1. Configuración de Supabase
const supabaseUrl = 'https://uhoqgarnbsbnxhcyzkhi.supabase.co';
const supabaseKey = 'sb_publishable_KkNhb7Yyj72M4soqA6utcQ_aLo1pg_F'; 

// 2. Inicializar el cliente de Supabase
let supabase;
if (typeof window.supabase !== 'undefined') {
    supabase = window.supabase.createClient(supabaseUrl, supabaseKey);
    console.log('✅ Supabase inicializado correctamente en Kiala Studio.');
} else {
    console.error('❌ Error: La librería de Supabase no se cargó.');
}

// 3. Inyectar Estilos del Portal de Clientes
const authStyles = document.createElement('style');
authStyles.textContent = `
  .auth-modal-backdrop {
    position: fixed;
    inset: 0;
    z-index: 150;
    background: rgba(5, 5, 5, 0.85);
    backdrop-filter: blur(12px);
    display: flex;
    align-items: center;
    justify-content: center;
    opacity: 0;
    transition: opacity 0.3s ease;
    pointer-events: none;
  }
  .auth-modal-backdrop.active {
    opacity: 1;
    pointer-events: auto;
  }
  .auth-modal-card {
    width: 100%;
    max-width: 420px;
    background: #0E0E13;
    border: 1px solid #22222E;
    border-radius: 1.5rem;
    padding: 2rem;
    box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
    transform: scale(0.95);
    transition: transform 0.3s ease;
  }
  .auth-modal-backdrop.active .auth-modal-card {
    transform: scale(1);
  }
  .auth-tab-btn {
    position: relative;
    padding-bottom: 0.5rem;
    color: #9CA3AF;
    font-weight: 500;
    font-size: 0.875rem;
    transition: color 0.2s;
  }
  .auth-tab-btn.active {
    color: #C4A77D;
  }
  .auth-tab-btn.active::after {
    content: '';
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    height: 2px;
    background: linear-gradient(90deg, #C4A77D, #8F7449);
    border-radius: 9999px;
  }
`;
document.head.appendChild(authStyles);

// 4. Crear e Inyectar el Modal en el DOM
let authModalBackdrop = null;

function createAuthModal() {
    if (authModalBackdrop) return;

    authModalBackdrop = document.createElement('div');
    authModalBackdrop.className = 'auth-modal-backdrop';
    authModalBackdrop.id = 'auth-modal-portal';
    
    authModalBackdrop.innerHTML = `
        <div class="auth-modal-card relative">
            <!-- Botón Cerrar -->
            <button onclick="closeAuthModal()" class="absolute top-4 right-4 text-neutral-500 hover:text-rose-400 transition">
                <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
            </button>

            <!-- Cabecera -->
            <div class="flex items-center gap-2.5 mb-6">
                <div class="w-8 h-8 rounded-lg bg-[#C4A77D]/10 border border-[#C4A77D]/20 flex items-center justify-center text-[#C4A77D]">
                    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path><circle cx="12" cy="7" r="4"></circle></svg>
                </div>
                <div>
                    <h3 class="text-lg font-bold text-neutral-100 tracking-wide">Portal de Clientes</h3>
                    <p class="text-xs text-neutral-500">Accede de forma segura a tu espacio</p>
                </div>
            </div>

            <!-- Tabs -->
            <div class="flex gap-4 border-b border-[#1E1E28] mb-6">
                <button onclick="switchAuthTab('login')" id="tab-login" class="auth-tab-btn active">Iniciar Sesión</button>
                <button onclick="switchAuthTab('register')" id="tab-register" class="auth-tab-btn">Registrarse</button>
            </div>

            <!-- Formulario -->
            <form id="auth-form" onsubmit="handleAuthSubmit(event)" class="space-y-4">
                <div>
                    <label class="block text-[10px] font-mono text-neutral-500 uppercase tracking-wider mb-1.5">Correo Electrónico</label>
                    <input type="email" id="auth-email" required class="w-full bg-[#0A0A0D] border border-[#1E1E28] rounded-xl px-4 py-2.5 text-sm text-neutral-200 outline-none focus:border-[#C4A77D]/50 transition shadow-inner" placeholder="ejemplo@correo.com">
                </div>
                <div>
                    <label class="block text-[10px] font-mono text-neutral-500 uppercase tracking-wider mb-1.5">Contraseña</label>
                    <input type="password" id="auth-password" required class="w-full bg-[#0A0A0D] border border-[#1E1E28] rounded-xl px-4 py-2.5 text-sm text-neutral-200 outline-none focus:border-[#C4A77D]/50 transition shadow-inner" placeholder="••••••••">
                </div>

                <button type="submit" id="auth-submit-btn" class="w-full mt-2 bg-gradient-to-r from-[#C4A77D] to-[#8F7449] hover:from-[#D4B78D] hover:to-[#9F8459] text-[#0A0A0D] font-bold text-sm py-3 rounded-xl transition shadow-[0_0_20px_rgba(196,167,125,0.15)] flex items-center justify-center gap-2">
                    <span>Entrar al Portal</span>
                </button>

                <p id="auth-error" class="text-rose-400 text-xs text-center hidden mt-2 font-mono bg-rose-500/10 border border-rose-500/20 py-2 rounded-lg"></p>
                <p id="auth-success" class="text-emerald-400 text-xs text-center hidden mt-2 font-mono bg-emerald-500/10 border border-emerald-500/20 py-2 rounded-lg"></p>
            </form>

            <!-- Estado de Sesión Activa (Oculto por defecto) -->
            <div id="auth-logged-in-state" class="hidden space-y-4 text-center">
                <div class="p-4 bg-[#14141A] border border-[#22222E] rounded-2xl">
                    <div class="w-12 h-12 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center text-emerald-400 mx-auto mb-3">
                        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
                    </div>
                    <h4 class="text-sm font-semibold text-neutral-200">Sesión Iniciada</h4>
                    <p id="auth-user-email" class="text-xs text-neutral-400 mt-1 font-mono truncate"></p>
                </div>
                <button onclick="handleLogout()" class="w-full bg-rose-500/10 hover:bg-rose-500/20 border border-rose-500/30 text-rose-400 font-semibold text-sm py-2.5 rounded-xl transition">
                    Cerrar Sesión
                </button>
            </div>
        </div>
    `;
    document.body.appendChild(authModalBackdrop);
}

// 5. Controladores de la Interfaz del Modal
let currentAuthMode = 'login'; // 'login' o 'register'

window.openAuthModal = function() {
    createAuthModal();
    checkCurrentUser();
    authModalBackdrop.classList.add('active');
};

window.closeAuthModal = function() {
    if (authModalBackdrop) {
        authModalBackdrop.classList.remove('active');
    }
};

window.switchAuthTab = function(mode) {
    currentAuthMode = mode;
    const tabLogin = document.getElementById('tab-login');
    const tabRegister = document.getElementById('tab-register');
    const submitBtn = document.getElementById('auth-submit-btn');
    const errEl = document.getElementById('auth-error');
    const succEl = document.getElementById('auth-success');

    if (errEl) errEl.classList.add('hidden');
    if (succEl) succEl.classList.add('hidden');

    if (mode === 'login') {
        tabLogin.classList.add('active');
        tabRegister.classList.remove('active');
        submitBtn.querySelector('span').textContent = 'Entrar al Portal';
    } else {
        tabRegister.classList.add('active');
        tabLogin.classList.remove('active');
        submitBtn.querySelector('span').textContent = 'Crear Cuenta Nueva';
    }
};

// 6. Lógica de Autenticación con Supabase
async function checkCurrentUser() {
    const form = document.getElementById('auth-form');
    const loggedInState = document.getElementById('auth-logged-in-state');
    const userEmailEl = document.getElementById('auth-user-email');
    const portalBtn = document.getElementById('btn-portal-cliente');

    const { data: { user } } = await supabase.auth.getUser();

    if (user) {
        if (form) form.classList.add('hidden');
        if (loggedInState) loggedInState.classList.remove('hidden');
        if (userEmailEl) userEmailEl.textContent = user.email;
        if (portalBtn) {
            portalBtn.innerHTML = `<i data-lucide="user-check" class="w-4 h-4 text-emerald-400"></i><span class="hidden sm:inline">Mi Cuenta</span>`;
            if (window.lucide) lucide.createIcons();
        }
    } else {
        if (form) form.classList.remove('hidden');
        if (loggedInState) loggedInState.classList.add('hidden');
        if (portalBtn) {
            portalBtn.innerHTML = `<i data-lucide="user" class="w-4 h-4 text-neutral-400"></i><span class="hidden sm:inline">Portal Cliente</span>`;
            if (window.lucide) lucide.createIcons();
        }
    }
}

window.handleAuthSubmit = async function(e) {
    e.preventDefault();
    const email = document.getElementById('auth-email').value;
    const password = document.getElementById('auth-password').value;
    const errEl = document.getElementById('auth-error');
    const succEl = document.getElementById('auth-success');
    const submitBtn = document.getElementById('auth-submit-btn');

    errEl.classList.add('hidden');
    succEl.classList.add('hidden');
    submitBtn.disabled = true;
    submitBtn.classList.add('opacity-50');

    try {
        if (currentAuthMode === 'login') {
            // Iniciar Sesión
            const { data, error } = await supabase.auth.signInWithPassword({ email, password });
            if (error) throw error;
            
            succEl.textContent = '¡Sesión iniciada con éxito!';
            succEl.classList.remove('hidden');
            setTimeout(() => {
                checkCurrentUser();
                closeAuthModal();
            }, 1000);
        } else {
            // Registrarse
            const { data, error } = await supabase.auth.signUp({ email, password });
            if (error) throw error;
            
            succEl.textContent = '¡Registro exitoso! Revisa tu correo para confirmar.';
            succEl.classList.remove('hidden');
        }
    } catch (error) {
        errEl.textContent = error.message || 'Ocurrió un error inesperado.';
        errEl.classList.remove('hidden');
    } finally {
        submitBtn.disabled = false;
        submitBtn.classList.remove('opacity-50');
    }
};

window.handleLogout = async function() {
    await supabase.auth.signOut();
    checkCurrentUser();
    closeAuthModal();
};

// Reemplazar la función de clic original para abrir nuestro modal
window.handleClientPortalClick = function() {
    window.openAuthModal();
};

// Verificar sesión al cargar la página
window.addEventListener('DOMContentLoaded', () => {
    setTimeout(checkCurrentUser, 500);
});