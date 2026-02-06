import { describe, it, expect, vi, beforeEach } from 'vitest';

// Mock useAuth before importing router
vi.mock('../../composables/useAuth', () => ({
  useAuth: vi.fn(() => ({
    isAuthenticated: { value: false },
    checkAndRefreshToken: vi.fn().mockResolvedValue(false),
    user: { value: null },
  })),
}));

// Mock lazy-loaded view components to avoid import errors in test environment
vi.mock('../../views/LandingView.vue', () => ({ default: { template: '<div />' } }));
vi.mock('../../views/UnauthorizedView.vue', () => ({ default: { template: '<div />' } }));
vi.mock('../../views/UnifiedYardView.vue', () => ({ default: { template: '<div />' } }));
vi.mock('../../views/GateCameraTestView.vue', () => ({ default: { template: '<div />' } }));
vi.mock('../../views/ExecutiveDashboard.vue', () => ({ default: { template: '<div />' } }));
vi.mock('../../views/WorkOrdersPage.vue', () => ({ default: { template: '<div />' } }));
vi.mock('../../views/TelegramBotSettings.vue', () => ({ default: { template: '<div />' } }));
vi.mock('../../views/Tariffs.vue', () => ({ default: { template: '<div />' } }));
vi.mock('../../views/TerminalVehicles.vue', () => ({ default: { template: '<div />' } }));

describe('router configuration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('dev-only routes', () => {
    it('should conditionally include /yard-test-dev based on DEV flag', async () => {
      // In vitest, import.meta.env.DEV is true by default
      const { default: router } = await import('../index');
      const routes = router.getRoutes();
      const yardTestRoute = routes.find((r) => r.path === '/yard-test-dev');

      if (import.meta.env.DEV) {
        expect(yardTestRoute).toBeDefined();
        expect(yardTestRoute?.name).toBe('YardTestDev');
      } else {
        expect(yardTestRoute).toBeUndefined();
      }
    });

    it('should conditionally include /gate-test based on DEV flag', async () => {
      const { default: router } = await import('../index');
      const routes = router.getRoutes();
      const gateTestRoute = routes.find((r) => r.path === '/gate-test');

      if (import.meta.env.DEV) {
        expect(gateTestRoute).toBeDefined();
        expect(gateTestRoute?.name).toBe('GateCameraTest');
      } else {
        expect(gateTestRoute).toBeUndefined();
      }
    });

    it('dev test routes should not require auth', async () => {
      // Only relevant when DEV is true (which it is in vitest)
      if (!import.meta.env.DEV) return;

      const { default: router } = await import('../index');
      const routes = router.getRoutes();

      const yardTestRoute = routes.find((r) => r.path === '/yard-test-dev');
      const gateTestRoute = routes.find((r) => r.path === '/gate-test');

      expect(yardTestRoute?.meta.requiresAuth).toBe(false);
      expect(gateTestRoute?.meta.requiresAuth).toBe(false);
    });
  });

  describe('route structure', () => {
    it('should have login route that does not require auth', async () => {
      const { default: router } = await import('../index');
      const routes = router.getRoutes();
      const loginRoute = routes.find((r) => r.name === 'Login');

      expect(loginRoute).toBeDefined();
      expect(loginRoute?.meta.requiresAuth).toBe(false);
    });

    it('should define Dashboard route as child of app layout', async () => {
      const { default: router } = await import('../index');
      const routes = router.getRoutes();

      // Dashboard is a child of /app which requires auth
      const dashboardRoute = routes.find((r) => r.name === 'Dashboard');
      expect(dashboardRoute).toBeDefined();
      expect(dashboardRoute?.meta.title).toBe('Главная - МТТ');
      expect(dashboardRoute?.meta.roles).toContain('admin');
    });

    it('should define admin-only routes with roles', async () => {
      const { default: router } = await import('../index');
      const routes = router.getRoutes();

      const containersRoute = routes.find((r) => r.name === 'Containers');
      expect(containersRoute).toBeDefined();
      expect(containersRoute?.meta.roles).toContain('admin');
    });

    it('should define customer routes with customer role', async () => {
      const { default: router } = await import('../index');
      const routes = router.getRoutes();

      const customerDashboard = routes.find((r) => r.name === 'CustomerDashboard');
      expect(customerDashboard).toBeDefined();
      expect(customerDashboard?.meta.roles).toContain('customer');
    });
  });
});
