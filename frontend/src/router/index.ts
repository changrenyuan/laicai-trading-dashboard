import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(import.meta.env.BASE_URL),
  routes: [
    {
      path: '/',
      redirect: '/dashboard',
    },
    {
      path: '/dashboard',
      name: 'Dashboard',
      component: () => import('@/views/Dashboard.vue'),
    },
    {
      path: '/strategies',
      name: 'Strategies',
      component: () => import('@/views/Strategies.vue'),
    },
    {
      path: '/strategies/:id',
      name: 'StrategyDetail',
      component: () => import('@/views/Strategies.vue'),
    },
    {
      path: '/positions',
      name: 'Positions',
      component: () => import('@/views/Positions.vue'),
    },
    {
      path: '/orders',
      name: 'Orders',
      component: () => import('@/views/Orders.vue'),
    },
    {
      path: '/pnl',
      name: 'PnL',
      component: () => import('@/views/PnL.vue'),
    },
    {
      path: '/backtest',
      name: 'Backtest',
      component: () => import('@/views/Backtest.vue'),
    },
    {
      path: '/logs',
      name: 'Logs',
      component: () => import('@/views/Logs.vue'),
    },
    {
      path: '/settings',
      name: 'Settings',
      component: () => import('@/views/Settings.vue'),
    },
  ],
})

export default router
