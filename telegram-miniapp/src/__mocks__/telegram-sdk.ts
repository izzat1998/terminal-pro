import { vi } from 'vitest';

// Mock Telegram Web App SDK
export const mockWebApp = {
  version: '7.0',
  platform: 'unknown',
  colorScheme: 'light' as const,
  themeParams: {
    bg_color: '#ffffff',
    text_color: '#000000',
    hint_color: '#999999',
    link_color: '#2481cc',
    button_color: '#2481cc',
    button_text_color: '#ffffff',
  },
  isExpanded: true,
  viewportHeight: 667,
  viewportStableHeight: 667,
  headerColor: '#ffffff',
  backgroundColor: '#ffffff',
  isClosingConfirmationEnabled: false,
  BackButton: {
    isVisible: false,
    show: vi.fn(),
    hide: vi.fn(),
    onClick: vi.fn(),
    offClick: vi.fn(),
  },
  MainButton: {
    text: '',
    color: '#2481cc',
    textColor: '#ffffff',
    isVisible: false,
    isActive: true,
    isProgressVisible: false,
    setText: vi.fn(),
    onClick: vi.fn(),
    offClick: vi.fn(),
    show: vi.fn(),
    hide: vi.fn(),
    enable: vi.fn(),
    disable: vi.fn(),
    showProgress: vi.fn(),
    hideProgress: vi.fn(),
    setParams: vi.fn(),
  },
  HapticFeedback: {
    impactOccurred: vi.fn(),
    notificationOccurred: vi.fn(),
    selectionChanged: vi.fn(),
  },
  initData: 'query_id=mock&user=%7B%22id%22%3A123456%2C%22first_name%22%3A%22Test%22%2C%22last_name%22%3A%22User%22%2C%22username%22%3A%22testuser%22%2C%22language_code%22%3A%22en%22%7D',
  initDataUnsafe: {
    query_id: 'mock',
    user: {
      id: 123456,
      first_name: 'Test',
      last_name: 'User',
      username: 'testuser',
      language_code: 'en',
      is_premium: false,
      allows_write_to_pm: true,
    },
    auth_date: Date.now(),
    hash: 'mock-hash',
  },
  ready: vi.fn(),
  expand: vi.fn(),
  close: vi.fn(),
  enableClosingConfirmation: vi.fn(),
  disableClosingConfirmation: vi.fn(),
  onEvent: vi.fn(),
  offEvent: vi.fn(),
  sendData: vi.fn(),
  openLink: vi.fn(),
  openTelegramLink: vi.fn(),
  openInvoice: vi.fn(),
  showPopup: vi.fn(),
  showAlert: vi.fn(),
  showConfirm: vi.fn(),
  showScanQrPopup: vi.fn(),
  closeScanQrPopup: vi.fn(),
  readTextFromClipboard: vi.fn(),
  requestWriteAccess: vi.fn(),
  requestContact: vi.fn(),
  setHeaderColor: vi.fn(),
  setBackgroundColor: vi.fn(),
};

// Mock window.Telegram
Object.defineProperty(window, 'Telegram', {
  writable: true,
  value: {
    WebApp: mockWebApp,
  },
});

// Mock @tma.js/sdk-react hooks
export const mockUseLaunchParams = vi.fn().mockReturnValue({
  initData: mockWebApp.initData,
  initDataRaw: mockWebApp.initData,
  startParam: null,
  platform: 'unknown',
  version: '7.0',
});

export const mockUseInitData = vi.fn().mockReturnValue(mockWebApp.initDataUnsafe);

export const mockUseMiniApp = vi.fn().mockReturnValue({
  ready: mockWebApp.ready,
  close: mockWebApp.close,
  expand: mockWebApp.expand,
  version: mockWebApp.version,
});

export const mockUseThemeParams = vi.fn().mockReturnValue(mockWebApp.themeParams);

export const mockUseBackButton = vi.fn().mockReturnValue({
  show: mockWebApp.BackButton.show,
  hide: mockWebApp.BackButton.hide,
  on: mockWebApp.BackButton.onClick,
  off: mockWebApp.BackButton.offClick,
});

// Export reset function for tests
export function resetTelegramMock(): void {
  vi.clearAllMocks();
  mockWebApp.BackButton.isVisible = false;
  mockWebApp.MainButton.isVisible = false;
  mockWebApp.colorScheme = 'light';
}

// Default export for module replacement
export default {
  mockWebApp,
  mockUseLaunchParams,
  mockUseInitData,
  mockUseMiniApp,
  mockUseThemeParams,
  mockUseBackButton,
  resetTelegramMock,
};
