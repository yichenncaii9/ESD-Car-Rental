<template>
  <div id="app">
    <NavBar />
    <main class="main-content">
      <RouterView />
    </main>
  </div>
</template>

<script setup>
import NavBar from './components/NavBar.vue'
</script>

<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Inter', system-ui, sans-serif; background: #f5f5f5; }
#app { min-height: 100vh; display: flex; flex-direction: column; }
.main-content { flex: 1; padding: 24px; }
</style>
