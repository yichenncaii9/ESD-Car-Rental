<template>
  <div id="app">
    <NavBar />
    <main class="main-content" :class="{ 'main-content--landing': isLanding }">
      <RouterView />
    </main>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import NavBar from './components/NavBar.vue'

const route = useRoute()
const isLanding = computed(() => route.path === '/')
</script>

<style>
/* ── Design tokens ──────────────────────────────────────────── */
:root {
  --c-primary:   #1E293B;
  --c-accent:    #DC2626;
  --c-accent-h:  #b91c1c;
  --c-bg:        #F1F5F9;
  --c-surface:   #FFFFFF;
  --c-border:    #E2E8F0;
  --c-muted:     #64748B;
  --c-dark:      #0F172A;
  --c-success:   #16a34a;
  --c-success-bg:#dcfce7;
  --c-error:     #dc2626;
  --c-error-bg:  #fee2e2;
  --c-warn-bg:   #fef3c7;
  --c-warn:      #92400e;
  --font:        'DM Sans', system-ui, sans-serif;
  --radius:      12px;
  --radius-sm:   8px;
  --shadow:      0 1px 3px rgba(0,0,0,0.07), 0 4px 16px rgba(0,0,0,0.06);
  --shadow-md:   0 4px 24px rgba(0,0,0,0.10), 0 1px 4px rgba(0,0,0,0.06);
}

/* ── Reset ──────────────────────────────────────────────────── */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: var(--font); background: var(--c-bg); color: var(--c-dark); line-height: 1.6; }
#app { min-height: 100vh; display: flex; flex-direction: column; }
.main-content { flex: 1; padding: 32px 24px; padding-top: 96px; }
.main-content--landing { padding: 0; }

/* ── Shared utility classes (used across all views) ─────────── */
.view-container { max-width: 900px; margin: 0 auto; }

.page-title {
  font-size: 26px;
  font-weight: 800;
  color: var(--c-dark);
  letter-spacing: -0.4px;
  margin-bottom: 4px;
}
.page-subtitle {
  font-size: 14px;
  color: var(--c-muted);
  margin-bottom: 28px;
}

/* Cards */
.card {
  background: var(--c-surface);
  border: 1px solid var(--c-border);
  border-radius: var(--radius);
  box-shadow: var(--shadow);
  margin-bottom: 20px;
  overflow: hidden;
}
.card-header {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 16px 20px;
  border-bottom: 1px solid var(--c-border);
}
.card-header h3 { font-size: 15px; font-weight: 700; color: var(--c-dark); margin: 0; }
.card-body { padding: 20px; }

/* Forms */
.form-group { margin-bottom: 16px; }
.form-group label {
  display: block;
  font-size: 13px;
  font-weight: 600;
  color: var(--c-primary);
  margin-bottom: 6px;
}
.form-group input,
.form-group textarea,
.form-group select {
  width: 100%;
  padding: 10px 12px;
  border: 1.5px solid var(--c-border);
  border-radius: var(--radius-sm);
  font-size: 14px;
  font-family: var(--font);
  color: var(--c-dark);
  background: var(--c-surface);
  outline: none;
  transition: border-color 0.15s;
}
.form-group input:focus,
.form-group textarea:focus { border-color: var(--c-accent); }
.form-group input:disabled,
.form-group textarea:disabled { background: var(--c-bg); color: var(--c-muted); cursor: not-allowed; }

/* Buttons */
.btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-family: var(--font);
  font-size: 14px;
  font-weight: 600;
  padding: 10px 20px;
  border-radius: var(--radius-sm);
  border: none;
  cursor: pointer;
  text-decoration: none;
  transition: all 0.15s;
  white-space: nowrap;
}
.btn-primary {
  background: var(--c-accent);
  color: #fff;
  border: none;
  border-radius: var(--radius-sm);
  font-family: var(--font);
  font-size: 14px;
  font-weight: 600;
  padding: 10px 20px;
  cursor: pointer;
  transition: background 0.15s, transform 0.15s;
}
.btn-primary:hover:not(:disabled) { background: var(--c-accent-h); transform: translateY(-1px); }
.btn-primary:disabled { background: var(--c-muted); cursor: not-allowed; transform: none; }
.btn-danger {
  background: var(--c-error-bg);
  color: var(--c-error);
  border: 1.5px solid #fca5a5;
  border-radius: var(--radius-sm);
  font-family: var(--font);
  font-size: 14px;
  font-weight: 600;
  padding: 10px 20px;
  cursor: pointer;
  transition: background 0.15s;
}
.btn-danger:hover:not(:disabled) { background: #fecaca; }
.btn-danger:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-outline {
  background: transparent;
  color: var(--c-primary);
  border: 1.5px solid var(--c-border);
  border-radius: var(--radius-sm);
  font-family: var(--font);
  font-size: 14px;
  font-weight: 600;
  padding: 10px 20px;
  cursor: pointer;
  transition: border-color 0.15s, background 0.15s;
}
.btn-outline:hover:not(:disabled) { border-color: var(--c-primary); background: rgba(0,0,0,0.03); }

/* Feedback */
.error-msg {
  font-size: 13px;
  color: var(--c-error);
  background: var(--c-error-bg);
  border: 1px solid #fca5a5;
  border-radius: var(--radius-sm);
  padding: 10px 14px;
  margin-bottom: 12px;
}
.success-msg {
  font-size: 13px;
  color: var(--c-success);
  background: var(--c-success-bg);
  border: 1px solid #86efac;
  border-radius: var(--radius-sm);
  padding: 10px 14px;
  margin-bottom: 12px;
}

/* Badges */
.badge {
  display: inline-block;
  font-size: 11px;
  font-weight: 700;
  padding: 3px 9px;
  border-radius: 9999px;
  letter-spacing: 0.2px;
}
.badge-green  { background: var(--c-success-bg); color: var(--c-success); }
.badge-red    { background: var(--c-error-bg);   color: var(--c-error); }
.badge-amber  { background: var(--c-warn-bg);    color: var(--c-warn); }
.badge-slate  { background: #f1f5f9;             color: var(--c-muted); }
</style>
