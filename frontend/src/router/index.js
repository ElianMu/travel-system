import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/', redirect: '/chat' },
  { path: '/chat', component: () => import('../views/ChatView.vue') },
  { path: '/attractions', component: () => import('../views/AttractionSearch.vue') },
  { path: '/routes', component: () => import('../views/RouteSearch.vue') },
  { path: '/info', component: () => import('../views/InfoSearch.vue') },
  { path: '/admin/import', component: () => import('../views/ImportView.vue') },
  { path: '/admin/documents', component: () => import('../views/DocumentView.vue') },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
